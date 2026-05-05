# V3 Edit-in-UI — Phase A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the foundation primitives (modal shell, inline-field wrapper, field renderers, concurrency layer) and ship full Task editing — both inline click-to-edit on Task Detail and modal create/edit — end to end.

**Architecture:** Vanilla ESM JS in the v3 viewer using the existing `h(tag, attrs, children)` factory pattern. Field renderers are entity-agnostic; per-entity composition lives in `forms/*-form.js` files. Server side adds `do_PATCH` and per-file write locks; write primitives live in `taskmaster_v3.py` and are shared with future MCP write tools. Concurrency is optimistic ETag/If-Match with field-level conflict resolution.

**Tech Stack:** Vanilla ESM JS · `node --test` + `jsdom` for unit tests · Playwright for E2E · Python `http.server` + pytest · `taskmaster_v3.py` for write primitives.

**Spec:** `docs/superpowers/specs/2026-05-04-v3-edit-in-ui-design.md` (commit `7685adf`)

**Backlog tasks covered:** `v3-edit-001` through `v3-edit-009` (filed as part of Phase A once the epic is created).

---

## File Structure

### New files

| Path | Responsibility |
|---|---|
| `viewer/js/components/edit/fields/text-field.js` | Single-line text renderer; read-mode + edit-mode |
| `viewer/js/components/edit/fields/md-field.js` | Markdown textarea; Cmd/Ctrl+Enter saves |
| `viewer/js/components/edit/fields/enum-select.js` | Dropdown for enum fields (status, priority, kind, severity) |
| `viewer/js/components/edit/fields/number-field.js` | Numeric input with coercion |
| `viewer/js/components/edit/fields/date-field.js` | ISO-8601 date input |
| `viewer/js/components/edit/fields/chip-input.js` | Autocomplete chip-input — workhorse for relations |
| `viewer/js/components/edit/fields/relation-picker.js` | Chip-input variant pre-wired to a relation source (tasks/epics/phases) |
| `viewer/js/components/edit/inline-field.js` | Read↔edit swap, autosave debounce, lifecycle |
| `viewer/js/components/edit/entity-modal.js` | Centered overlay, dirty/save/error UX, focus trap |
| `viewer/js/components/edit/conflict-banner.js` | Surfaces 409 responses; field-level diff resolution |
| `viewer/js/components/edit/schema.js` | Schema definition helpers + client-side validation runner |
| `viewer/js/components/edit/forms/task-form.js` | Task field schema + modal layout |
| `viewer/css/components/edit-fields.css` | Field renderer styling (dotted underline, hover pencil, edit mode) |
| `viewer/css/components/entity-modal.css` | Modal overlay styling |
| `viewer/css/components/conflict-banner.css` | Conflict banner styling |
| `viewer/tests/unit/text-field.test.js` | Node test runner unit test |
| `viewer/tests/unit/md-field.test.js` | … |
| `viewer/tests/unit/enum-select.test.js` | … |
| `viewer/tests/unit/number-field.test.js` | … |
| `viewer/tests/unit/date-field.test.js` | … |
| `viewer/tests/unit/chip-input.test.js` | … |
| `viewer/tests/unit/relation-picker.test.js` | … |
| `viewer/tests/unit/inline-field.test.js` | … |
| `viewer/tests/unit/entity-modal.test.js` | … |
| `viewer/tests/unit/conflict-banner.test.js` | … |
| `viewer/tests/unit/schema.test.js` | … |
| `viewer/tests/unit/task-form.test.js` | … |
| `viewer/tests/edit-task.spec.js` | Playwright E2E covering create/inline/conflict |
| `plugins/taskmaster/tests/test_server_task_write.py` | HTTP write API integration tests |
| `plugins/taskmaster/tests/test_v3_task_writes.py` | `taskmaster_v3.update_task` / `create_task` tests |
| `plugins/taskmaster/tests/test_server_etag.py` | Concurrency tests — ETag generation + 409 path |

### Modified files

| Path | Change |
|---|---|
| `viewer/js/api.js` | Add `patchTask`, `putTask`, `createTask`, `archiveTask`, `validateTask` HTTP methods |
| `viewer/js/store.js` | Add optimistic-update helpers + ETag tracking per entity |
| `viewer/js/main.js` | Mount `entity-modal-host` element into shell on boot |
| `viewer/js/screens/kanban.js:149-154` | `+ Task` button opens modal instead of navigating to `#/task/new` |
| `viewer/js/screens/table.js:68-74` | Same — open modal |
| `viewer/js/components/task-detail-document.js:34-36` | `✎ Edit` button opens modal in edit mode (currently disabled) |
| `viewer/js/components/task-detail-document.js:60-91` | Wrap each editable field with `inline-field.js` |
| `viewer/index.html` | Add `<div id="entity-modal-host">` and `<div id="conflict-banner-host">` mounts |
| `viewer/css/shell.css` | Import the three new component CSS files |
| `plugins/taskmaster/backlog_server.py` | Add `do_PATCH`, write endpoints, ETag emission, write lock helper |
| `plugins/taskmaster/taskmaster_v3.py` | Add `update_task`, `create_task`, `archive_task`, `compute_etag`, `with_file_lock` |

### Conventions used throughout this plan

- **`h(tag, attrs, children)`** — DOM factory already used across the v3 viewer (see `right-rail.js`, `task-detail-document.js`). All new components import a copy or share via `viewer/js/util/h.js` if it exists. We'll create `viewer/js/util/h.js` in Task 1 if not present, since seven new files would otherwise re-declare it.
- **Test runner** — `node --test` with `jsdom`. Tests use `import { test } from 'node:test'` + `assert from 'node:assert/strict'`. Each test file boots a minimal jsdom `window`/`document` before importing the component under test.
- **Server tests** — pytest fixture `running_server` (already in `tests/test_server_api.py`) — copy the pattern when adding new test files.
- **Commit cadence** — every task ends with a commit. Keep messages in the existing convention: `feat(taskmaster): …`, `test(taskmaster): …`, `refactor(taskmaster): …`.

---

## Task 1: Set up shared `h()` factory + Storybook-style demo page

**Files:**
- Create: `viewer/js/util/h.js`
- Create: `viewer/js/dev/edit-demo.js`
- Create: `viewer/dev/edit-demo.html`
- Create: `viewer/tests/unit/h.test.js`

The `h()` helper is duplicated in `right-rail.js`, `task-detail-document.js`, and `task-detail-graph.js`. Hoisting it to a shared module before adding seven new files prevents ten copies of the same 12-line function. The demo page is a dev-only static HTML that imports each new field renderer with sample data — useful when iterating on appearance without spinning up the full viewer.

- [ ] **Step 1: Write the failing test for `h()`**

```js
// viewer/tests/unit/h.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';

const dom = new JSDOM('<!doctype html><html><body></body></html>');
globalThis.document = dom.window.document;
globalThis.window = dom.window;

const { h } = await import('../../js/util/h.js');

test('h() creates element with class and text child', () => {
  const el = h('div', { class: 'foo' }, 'hello');
  assert.equal(el.tagName, 'DIV');
  assert.equal(el.className, 'foo');
  assert.equal(el.textContent, 'hello');
});

test('h() attaches event listeners via on:{}', () => {
  let clicked = false;
  const el = h('button', { on: { click: () => { clicked = true; } } }, 'go');
  el.click();
  assert.equal(clicked, true);
});

test('h() supports html: for raw innerHTML', () => {
  const el = h('div', { html: '<span>raw</span>' });
  assert.equal(el.firstElementChild.tagName, 'SPAN');
});

test('h() filters null/false children', () => {
  const el = h('div', {}, [h('span', {}, 'a'), null, false, h('span', {}, 'b')]);
  assert.equal(el.children.length, 2);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd plugins/taskmaster/viewer && npm run test:unit -- tests/unit/h.test.js`
Expected: FAIL — `Cannot find module '../../js/util/h.js'`

- [ ] **Step 3: Implement `h()`**

```js
// viewer/js/util/h.js
// Shared DOM factory. Mirrors the per-component copies in right-rail.js,
// task-detail-document.js, task-detail-graph.js — those will migrate to this.
export function h(tag, attrs = {}, children = []) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') el.className = v;
    else if (k === 'on') for (const [evt, fn] of Object.entries(v)) el.addEventListener(evt, fn);
    else if (k === 'html') el.innerHTML = v;
    else if (v !== false && v != null) el.setAttribute(k, v);
  }
  for (const c of [].concat(children)) {
    if (c == null || c === false) continue;
    el.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
  }
  return el;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd plugins/taskmaster/viewer && npm run test:unit -- tests/unit/h.test.js`
Expected: PASS — 4/4

- [ ] **Step 5: Create the demo page shell (HTML + JS bootstrap)**

```html
<!-- viewer/dev/edit-demo.html -->
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Edit components — demo</title>
  <link rel="stylesheet" href="/static/v3/css/tokens.css">
  <link rel="stylesheet" href="/static/v3/css/shell.css">
  <style>
    body { font-family: var(--font-sans); padding: 24px; max-width: 720px; }
    section { margin-bottom: 32px; padding: 16px; border: 1px solid var(--border); border-radius: 6px; }
    h2 { font-size: var(--text-md); margin-bottom: 12px; color: var(--ink-2); }
  </style>
</head>
<body>
  <h1>Edit components</h1>
  <div id="demo-mount"></div>
  <script type="module" src="/static/v3/dev/edit-demo.js"></script>
</body>
</html>
```

```js
// viewer/js/dev/edit-demo.js
// Dev-only page — wires up each field renderer with sample data.
// Components register themselves into the demo via registerDemo(name, fn).
import { h } from '../util/h.js';

const sections = [];
export function registerDemo(name, mountFn) {
  sections.push({ name, mountFn });
}

const mount = document.getElementById('demo-mount');
for (const { name, mountFn } of sections) {
  const sec = h('section', {}, [h('h2', {}, name)]);
  mount.appendChild(sec);
  mountFn(sec);
}
// Subsequent tasks add `import './fields/text-field-demo.js'` etc. above.
```

- [ ] **Step 6: Add a route for the demo page in `backlog_server.py`**

The viewer is served from `/v3/...`. The demo lives at `/v3/dev/edit-demo` (no trailing slash, served by the existing static handler if we put it under `viewer/dev/`).

Find the existing static-file branch in `do_GET` (`elif clean_path.startswith("/static/v3/")` near line 4341 of `backlog_server.py`) and add a sibling branch right after:

```python
elif clean_path == "/v3/dev/edit-demo" or clean_path == "/v3/dev/edit-demo/":
    viewer_root = Path(__file__).parent / "viewer"
    self._serve_file(viewer_root / "dev" / "edit-demo.html", "text/html")
```

(Read 5-10 lines around `viewer_root` resolution to make sure the new branch matches the existing pattern.)

- [ ] **Step 7: Manually verify**

Restart server. Navigate to `http://127.0.0.1:8765/v3/dev/edit-demo`. Expect: empty page with "Edit components" heading and `#demo-mount` div. (Sections appear as later tasks register demos.)

- [ ] **Step 8: Commit**

```bash
git add plugins/taskmaster/viewer/js/util/h.js \
        plugins/taskmaster/viewer/js/dev/edit-demo.js \
        plugins/taskmaster/viewer/dev/edit-demo.html \
        plugins/taskmaster/viewer/tests/unit/h.test.js \
        plugins/taskmaster/backlog_server.py
git commit -m "feat(taskmaster): shared h() factory + edit-components demo page (v3-edit-001)"
```

---

## Task 2: TextField renderer

**Files:**
- Create: `viewer/js/components/edit/fields/text-field.js`
- Create: `viewer/js/components/edit/fields/text-field-demo.js`
- Create: `viewer/css/components/edit-fields.css`
- Create: `viewer/tests/unit/text-field.test.js`
- Modify: `viewer/css/shell.css` (import the new CSS)
- Modify: `viewer/js/dev/edit-demo.js` (import the demo registration)

A TextField has two visual modes: **read** (rendered as a span; dotted underline if editable, no chrome if read-only) and **edit** (rendered as an `<input type="text">` with same width). The renderer doesn't manage its own state — it exposes `render(mode, props)` and lets the wrapper (`inline-field.js`, `entity-modal.js`) drive transitions.

Public API:
```js
TextField.read({ value, readOnly, placeholder })   // → DOM node
TextField.edit({ value, onChange, onCommit, onCancel, maxLength, required })  // → DOM node
TextField.coerce(rawValue)  // → string (trim + null-empty)
TextField.validate(value, { required, maxLength })  // → null | string error message
```

- [ ] **Step 1: Write the failing test**

```js
// viewer/tests/unit/text-field.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';

const dom = new JSDOM('<!doctype html><html><body></body></html>');
globalThis.document = dom.window.document;
globalThis.window = dom.window;
globalThis.HTMLElement = dom.window.HTMLElement;

const { TextField } = await import('../../js/components/edit/fields/text-field.js');

test('read mode renders value as span with editable class when not readOnly', () => {
  const el = TextField.read({ value: 'hello', readOnly: false });
  assert.equal(el.tagName, 'SPAN');
  assert.equal(el.textContent, 'hello');
  assert.ok(el.classList.contains('ef-text'));
  assert.ok(el.classList.contains('ef-editable'));
});

test('read mode without value renders placeholder italics', () => {
  const el = TextField.read({ value: '', readOnly: false, placeholder: 'no title' });
  assert.equal(el.textContent, 'no title');
  assert.ok(el.classList.contains('ef-placeholder'));
});

test('read mode readOnly=true omits ef-editable class', () => {
  const el = TextField.read({ value: 'x', readOnly: true });
  assert.ok(!el.classList.contains('ef-editable'));
});

test('edit mode renders input with value preselected', () => {
  const el = TextField.edit({ value: 'hello', onChange: () => {}, onCommit: () => {}, onCancel: () => {} });
  assert.equal(el.tagName, 'INPUT');
  assert.equal(el.value, 'hello');
  assert.equal(el.type, 'text');
});

test('edit mode Enter calls onCommit with current value', () => {
  let committed = null;
  const el = TextField.edit({ value: 'a', onChange: () => {}, onCommit: (v) => { committed = v; }, onCancel: () => {} });
  el.value = 'b';
  el.dispatchEvent(new dom.window.KeyboardEvent('keydown', { key: 'Enter' }));
  assert.equal(committed, 'b');
});

test('edit mode Escape calls onCancel', () => {
  let cancelled = false;
  const el = TextField.edit({ value: 'a', onChange: () => {}, onCommit: () => {}, onCancel: () => { cancelled = true; } });
  el.dispatchEvent(new dom.window.KeyboardEvent('keydown', { key: 'Escape' }));
  assert.equal(cancelled, true);
});

test('edit mode input event calls onChange with current value', () => {
  let lastChange = null;
  const el = TextField.edit({ value: 'a', onChange: (v) => { lastChange = v; }, onCommit: () => {}, onCancel: () => {} });
  el.value = 'ab';
  el.dispatchEvent(new dom.window.Event('input'));
  assert.equal(lastChange, 'ab');
});

test('coerce trims and returns null for empty', () => {
  assert.equal(TextField.coerce('  hi  '), 'hi');
  assert.equal(TextField.coerce('   '), null);
  assert.equal(TextField.coerce(''), null);
});

test('validate enforces required', () => {
  assert.equal(TextField.validate(null, { required: true }), 'required');
  assert.equal(TextField.validate('x', { required: true }), null);
});

test('validate enforces maxLength', () => {
  assert.equal(TextField.validate('abcdef', { maxLength: 3 }), 'too long (max 3)');
  assert.equal(TextField.validate('abc', { maxLength: 3 }), null);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd plugins/taskmaster/viewer && npm run test:unit -- tests/unit/text-field.test.js`
Expected: FAIL — module not found

- [ ] **Step 3: Implement TextField**

```js
// viewer/js/components/edit/fields/text-field.js
import { h } from '../../../util/h.js';

export const TextField = {
  read({ value, readOnly = false, placeholder = '' }) {
    const empty = value == null || value === '';
    const text = empty ? (placeholder || '—') : String(value);
    const cls = ['ef-text'];
    if (!readOnly) cls.push('ef-editable');
    if (empty) cls.push('ef-placeholder');
    return h('span', { class: cls.join(' ') }, text);
  },

  edit({ value, onChange, onCommit, onCancel, maxLength, required }) {
    const input = h('input', {
      type: 'text',
      class: 'ef-text-input',
      value: value == null ? '' : String(value),
    });
    if (maxLength != null) input.setAttribute('maxlength', String(maxLength));
    if (required) input.setAttribute('required', '');
    input.addEventListener('input', () => onChange?.(input.value));
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); onCommit?.(input.value); }
      else if (e.key === 'Escape') { e.preventDefault(); onCancel?.(); }
    });
    input.addEventListener('blur', () => onCommit?.(input.value));
    queueMicrotask(() => { input.focus(); input.select(); });
    return input;
  },

  coerce(raw) {
    if (raw == null) return null;
    const trimmed = String(raw).trim();
    return trimmed === '' ? null : trimmed;
  },

  validate(value, { required = false, maxLength = null } = {}) {
    if (required && (value == null || value === '')) return 'required';
    if (maxLength != null && value != null && String(value).length > maxLength) {
      return `too long (max ${maxLength})`;
    }
    return null;
  },
};
```

- [ ] **Step 4: Add edit-fields.css**

```css
/* viewer/css/components/edit-fields.css
   Shared styling for all field renderers. Per spec §UX patterns: dotted
   underline at all times for editable fields, hover solidifies + reveals
   pencil. Read-only fields get no underline. */

.ef-text {
  color: var(--ink);
  font-size: inherit;
}
.ef-text.ef-placeholder {
  color: var(--ink-3);
  font-style: italic;
}
.ef-editable {
  border-bottom: 1px dotted var(--border-soft);
  padding-bottom: 1px;
  cursor: text;
  position: relative;
  display: inline-block;
}
.ef-editable:hover {
  border-bottom-style: solid;
  border-bottom-color: var(--border);
}
.ef-editable:hover::after {
  content: '✎';
  position: absolute;
  right: -16px;
  top: 0;
  font-size: var(--text-xs);
  color: var(--ink-3);
  opacity: 0.7;
}

.ef-text-input {
  font: inherit;
  color: var(--ink);
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 3px;
  padding: 2px 6px;
  min-width: 120px;
  outline: none;
}
.ef-text-input:focus {
  border-color: var(--accent);
}
```

- [ ] **Step 5: Wire CSS into the shell**

Find the existing `@import` block at the top of `viewer/css/shell.css` (or, if shell.css imports per-component CSS via `<link>` tags in `index.html` instead, find the link list). Add after the last existing component CSS:

```css
@import './components/edit-fields.css';
```

(If shell.css has no `@import` block, instead add `<link rel="stylesheet" href="/static/v3/css/components/edit-fields.css">` to `viewer/index.html` after the existing component-CSS link tags.)

- [ ] **Step 6: Wire the demo registration**

```js
// viewer/js/components/edit/fields/text-field-demo.js
import { h } from '../../../util/h.js';
import { registerDemo } from '../../../dev/edit-demo.js';
import { TextField } from './text-field.js';

registerDemo('TextField', (root) => {
  // Read mode — populated
  root.appendChild(h('div', { style: 'margin-bottom:8px' }, [
    h('strong', {}, 'Read (editable, populated): '),
    TextField.read({ value: 'A task title', readOnly: false }),
  ]));
  // Read mode — empty
  root.appendChild(h('div', { style: 'margin-bottom:8px' }, [
    h('strong', {}, 'Read (editable, empty): '),
    TextField.read({ value: '', readOnly: false, placeholder: 'no title yet' }),
  ]));
  // Read mode — read-only
  root.appendChild(h('div', { style: 'margin-bottom:8px' }, [
    h('strong', {}, 'Read (read-only): '),
    TextField.read({ value: 'task-id-123', readOnly: true }),
  ]));
  // Edit mode (live)
  const editHost = h('div', {}, [h('strong', {}, 'Edit (live): ')]);
  editHost.appendChild(TextField.edit({
    value: 'click to edit',
    onChange: (v) => console.log('change', v),
    onCommit: (v) => console.log('commit', v),
    onCancel: () => console.log('cancel'),
  }));
  root.appendChild(editHost);
});
```

Then add this import to `viewer/js/dev/edit-demo.js` (above the mount loop):

```js
import './../components/edit/fields/text-field-demo.js';
```

- [ ] **Step 7: Run unit tests**

Run: `cd plugins/taskmaster/viewer && npm run test:unit -- tests/unit/text-field.test.js`
Expected: PASS — 10/10

- [ ] **Step 8: Manually verify**

Restart server (CSS-only change does NOT need restart, but JS module imports do, since browser caches modules). Open `http://127.0.0.1:8765/v3/dev/edit-demo`. Expect: a "TextField" section with three read-mode samples (one with dotted underline + pencil on hover, one italic placeholder, one no underline) and a focused live edit input.

- [ ] **Step 9: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/edit/fields/text-field.js \
        plugins/taskmaster/viewer/js/components/edit/fields/text-field-demo.js \
        plugins/taskmaster/viewer/css/components/edit-fields.css \
        plugins/taskmaster/viewer/css/shell.css \
        plugins/taskmaster/viewer/js/dev/edit-demo.js \
        plugins/taskmaster/viewer/tests/unit/text-field.test.js
git commit -m "feat(taskmaster): TextField field renderer + demo wiring (v3-edit-001)"
```

---

## Task 3: MdField, EnumSelect, NumberField, DateField renderers

**Files:**
- Create: `viewer/js/components/edit/fields/md-field.js` (+ demo + test)
- Create: `viewer/js/components/edit/fields/enum-select.js` (+ demo + test)
- Create: `viewer/js/components/edit/fields/number-field.js` (+ demo + test)
- Create: `viewer/js/components/edit/fields/date-field.js` (+ demo + test)
- Modify: `viewer/css/components/edit-fields.css` (add per-renderer rules)
- Modify: `viewer/js/dev/edit-demo.js` (4 new imports)

These four share the TextField pattern: read mode → span/div, edit mode → input/textarea/select, public API of `read/edit/coerce/validate`. The plan compresses common steps; each renderer gets its own test file using the same scaffold as `text-field.test.js`.

### Task 3a: MdField

- [ ] **Step 1: Write the failing test**

```js
// viewer/tests/unit/md-field.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';

const dom = new JSDOM('<!doctype html><html><body></body></html>');
globalThis.document = dom.window.document;
globalThis.window = dom.window;

const { MdField } = await import('../../js/components/edit/fields/md-field.js');

test('read mode renders value (newlines preserved as <br>)', () => {
  const el = MdField.read({ value: 'line1\nline2', readOnly: false });
  assert.match(el.innerHTML, /line1.*<br.*line2/s);
  assert.ok(el.classList.contains('ef-md'));
  assert.ok(el.classList.contains('ef-editable'));
});

test('edit mode renders textarea with value', () => {
  const el = MdField.edit({ value: 'hi', onChange: () => {}, onCommit: () => {}, onCancel: () => {} });
  assert.equal(el.tagName, 'TEXTAREA');
  assert.equal(el.value, 'hi');
});

test('edit mode plain Enter inserts newline (does not commit)', () => {
  let committed = false;
  const el = MdField.edit({ value: 'a', onChange: () => {}, onCommit: () => { committed = true; }, onCancel: () => {} });
  const ev = new dom.window.KeyboardEvent('keydown', { key: 'Enter' });
  // jsdom does not auto-insert newlines from synthetic keydown — we only assert
  // that the onCommit handler did NOT fire on plain Enter.
  el.dispatchEvent(ev);
  assert.equal(committed, false);
});

test('edit mode Cmd/Ctrl+Enter commits', () => {
  let committed = null;
  const el = MdField.edit({ value: 'a', onChange: () => {}, onCommit: (v) => { committed = v; }, onCancel: () => {} });
  el.value = 'b';
  el.dispatchEvent(new dom.window.KeyboardEvent('keydown', { key: 'Enter', ctrlKey: true }));
  assert.equal(committed, 'b');
});

test('edit mode Escape cancels', () => {
  let cancelled = false;
  const el = MdField.edit({ value: 'a', onChange: () => {}, onCommit: () => {}, onCancel: () => { cancelled = true; } });
  el.dispatchEvent(new dom.window.KeyboardEvent('keydown', { key: 'Escape' }));
  assert.equal(cancelled, true);
});

test('coerce returns null for empty/whitespace', () => {
  assert.equal(MdField.coerce(''), null);
  assert.equal(MdField.coerce('   \n\n  '), null);
  assert.equal(MdField.coerce('hello\n'), 'hello');
});

test('validate enforces required', () => {
  assert.equal(MdField.validate(null, { required: true }), 'required');
  assert.equal(MdField.validate('x', { required: true }), null);
});
```

- [ ] **Step 2: Run test (fails — module missing)**

Run: `cd plugins/taskmaster/viewer && npm run test:unit -- tests/unit/md-field.test.js`

- [ ] **Step 3: Implement MdField**

```js
// viewer/js/components/edit/fields/md-field.js
import { h } from '../../../util/h.js';

export const MdField = {
  read({ value, readOnly = false, placeholder = '' }) {
    const empty = value == null || String(value).trim() === '';
    const text = empty ? (placeholder || 'no content') : String(value);
    const cls = ['ef-md'];
    if (!readOnly) cls.push('ef-editable');
    if (empty) cls.push('ef-placeholder');
    const div = h('div', { class: cls.join(' ') });
    if (empty) {
      div.textContent = text;
    } else {
      // Minimal: replace newlines with <br>. The full md renderer used in
      // task-detail-document.js's renderMdSection stays for the non-edit
      // read view; this is the in-place inline read form.
      div.innerHTML = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\n/g, '<br>');
    }
    return div;
  },

  edit({ value, onChange, onCommit, onCancel, rows = 6, maxLength, required }) {
    const ta = h('textarea', {
      class: 'ef-md-textarea',
      rows: String(rows),
    });
    ta.value = value == null ? '' : String(value);
    if (maxLength != null) ta.setAttribute('maxlength', String(maxLength));
    if (required) ta.setAttribute('required', '');
    ta.addEventListener('input', () => onChange?.(ta.value));
    ta.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        onCommit?.(ta.value);
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onCancel?.();
      }
    });
    ta.addEventListener('blur', () => onCommit?.(ta.value));
    queueMicrotask(() => { ta.focus(); ta.select(); });
    return ta;
  },

  coerce(raw) {
    if (raw == null) return null;
    const trimmed = String(raw).replace(/[\s\n]+$/, '').replace(/^[\s\n]+/, '');
    return trimmed === '' ? null : trimmed;
  },

  validate(value, { required = false } = {}) {
    if (required && (value == null || value === '')) return 'required';
    return null;
  },
};
```

- [ ] **Step 4: CSS additions**

Append to `viewer/css/components/edit-fields.css`:

```css
.ef-md {
  color: var(--ink);
  line-height: 1.55;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.ef-md-textarea {
  font: inherit;
  color: var(--ink);
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 8px 10px;
  width: 100%;
  resize: vertical;
  outline: none;
  font-family: var(--font-sans);
}
.ef-md-textarea:focus {
  border-color: var(--accent);
}
```

- [ ] **Step 5: Demo registration**

```js
// viewer/js/components/edit/fields/md-field-demo.js
import { h } from '../../../util/h.js';
import { registerDemo } from '../../../dev/edit-demo.js';
import { MdField } from './md-field.js';

registerDemo('MdField', (root) => {
  root.appendChild(h('div', { style: 'margin-bottom:8px' }, [
    h('strong', {}, 'Read: '),
    MdField.read({ value: 'Line one.\nLine two with `code`.', readOnly: false }),
  ]));
  root.appendChild(h('div', { style: 'margin-bottom:8px' }, [
    h('strong', {}, 'Empty placeholder: '),
    MdField.read({ value: '', readOnly: false, placeholder: 'no notes yet' }),
  ]));
  const editHost = h('div', {}, [h('strong', {}, 'Edit (Ctrl+Enter to commit): ')]);
  editHost.appendChild(MdField.edit({
    value: 'Multi-line\nedit here.',
    onChange: (v) => console.log('md change', v.length),
    onCommit: (v) => console.log('md commit', v),
    onCancel: () => console.log('md cancel'),
  }));
  root.appendChild(editHost);
});
```

Add to `viewer/js/dev/edit-demo.js`:

```js
import './../components/edit/fields/md-field-demo.js';
```

- [ ] **Step 6: Run + commit**

```bash
cd plugins/taskmaster/viewer && npm run test:unit -- tests/unit/md-field.test.js
# Expected: PASS — 7/7
git add plugins/taskmaster/viewer/js/components/edit/fields/md-field.js \
        plugins/taskmaster/viewer/js/components/edit/fields/md-field-demo.js \
        plugins/taskmaster/viewer/css/components/edit-fields.css \
        plugins/taskmaster/viewer/js/dev/edit-demo.js \
        plugins/taskmaster/viewer/tests/unit/md-field.test.js
git commit -m "feat(taskmaster): MdField field renderer (v3-edit-001)"
```

### Task 3b: EnumSelect

- [ ] **Step 1: Write the failing test**

```js
// viewer/tests/unit/enum-select.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';

const dom = new JSDOM('<!doctype html><html><body></body></html>');
globalThis.document = dom.window.document;
globalThis.window = dom.window;

const { EnumSelect } = await import('../../js/components/edit/fields/enum-select.js');

const STATUSES = [
  { value: 'todo', label: 'Todo' },
  { value: 'in-progress', label: 'In Progress' },
  { value: 'done', label: 'Done' },
];

test('read renders label for current value with editable class', () => {
  const el = EnumSelect.read({ value: 'in-progress', options: STATUSES, readOnly: false });
  assert.equal(el.textContent, 'In Progress');
  assert.ok(el.classList.contains('ef-enum'));
  assert.ok(el.classList.contains('ef-editable'));
});

test('read renders raw value when no matching option', () => {
  const el = EnumSelect.read({ value: 'unknown', options: STATUSES, readOnly: false });
  assert.equal(el.textContent, 'unknown');
});

test('edit renders <select> with options + current value selected', () => {
  const el = EnumSelect.edit({ value: 'done', options: STATUSES, onChange: () => {}, onCommit: () => {}, onCancel: () => {} });
  assert.equal(el.tagName, 'SELECT');
  assert.equal(el.options.length, 3);
  assert.equal(el.value, 'done');
});

test('edit change event commits the new value', () => {
  let committed = null;
  const el = EnumSelect.edit({ value: 'todo', options: STATUSES, onChange: () => {}, onCommit: (v) => { committed = v; }, onCancel: () => {} });
  el.value = 'in-progress';
  el.dispatchEvent(new dom.window.Event('change'));
  assert.equal(committed, 'in-progress');
});

test('validate enforces value-in-options', () => {
  assert.equal(EnumSelect.validate('done', { options: STATUSES }), null);
  assert.equal(EnumSelect.validate('bogus', { options: STATUSES }), 'invalid value');
  assert.equal(EnumSelect.validate(null, { options: STATUSES, required: true }), 'required');
});
```

- [ ] **Step 2: Run (fail) → Step 3: Implement EnumSelect**

```js
// viewer/js/components/edit/fields/enum-select.js
import { h } from '../../../util/h.js';

export const EnumSelect = {
  read({ value, options = [], readOnly = false, placeholder = '' }) {
    const match = options.find(o => o.value === value);
    const label = match ? match.label : (value == null || value === '' ? (placeholder || '—') : String(value));
    const cls = ['ef-enum'];
    if (!readOnly) cls.push('ef-editable');
    if (value == null || value === '') cls.push('ef-placeholder');
    return h('span', { class: cls.join(' ') }, label);
  },

  edit({ value, options = [], onChange, onCommit, onCancel }) {
    const sel = h('select', { class: 'ef-enum-select' });
    for (const opt of options) {
      const o = h('option', { value: opt.value }, opt.label);
      if (opt.value === value) o.selected = true;
      sel.appendChild(o);
    }
    sel.addEventListener('change', () => {
      onChange?.(sel.value);
      onCommit?.(sel.value);
    });
    sel.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') { e.preventDefault(); onCancel?.(); }
    });
    queueMicrotask(() => sel.focus());
    return sel;
  },

  coerce(raw) {
    if (raw == null) return null;
    const v = String(raw).trim();
    return v === '' ? null : v;
  },

  validate(value, { required = false, options = [] } = {}) {
    if (required && (value == null || value === '')) return 'required';
    if (value != null && value !== '' && !options.some(o => o.value === value)) {
      return 'invalid value';
    }
    return null;
  },
};
```

- [ ] **Step 4: CSS** — append to `edit-fields.css`:

```css
.ef-enum-select {
  font: inherit;
  color: var(--ink);
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 3px;
  padding: 1px 6px;
  outline: none;
}
.ef-enum-select:focus { border-color: var(--accent); }
```

- [ ] **Step 5: Demo + Step 6: Test/commit**

```js
// viewer/js/components/edit/fields/enum-select-demo.js
import { h } from '../../../util/h.js';
import { registerDemo } from '../../../dev/edit-demo.js';
import { EnumSelect } from './enum-select.js';

const STATUSES = [
  { value: 'todo', label: 'Todo' },
  { value: 'in-progress', label: 'In Progress' },
  { value: 'in-review', label: 'In Review' },
  { value: 'done', label: 'Done' },
  { value: 'blocked', label: 'Blocked' },
];

registerDemo('EnumSelect', (root) => {
  root.appendChild(h('div', { style: 'margin-bottom:8px' }, [
    h('strong', {}, 'Read: '),
    EnumSelect.read({ value: 'in-progress', options: STATUSES, readOnly: false }),
  ]));
  const editHost = h('div', {}, [h('strong', {}, 'Edit (changes commit immediately): ')]);
  editHost.appendChild(EnumSelect.edit({
    value: 'todo', options: STATUSES,
    onChange: (v) => console.log('enum change', v),
    onCommit: (v) => console.log('enum commit', v),
    onCancel: () => console.log('enum cancel'),
  }));
  root.appendChild(editHost);
});
```

Add `import './../components/edit/fields/enum-select-demo.js';` to `edit-demo.js`.

```bash
cd plugins/taskmaster/viewer && npm run test:unit -- tests/unit/enum-select.test.js
# Expected: PASS — 5/5
git add plugins/taskmaster/viewer/js/components/edit/fields/enum-select.js \
        plugins/taskmaster/viewer/js/components/edit/fields/enum-select-demo.js \
        plugins/taskmaster/viewer/css/components/edit-fields.css \
        plugins/taskmaster/viewer/js/dev/edit-demo.js \
        plugins/taskmaster/viewer/tests/unit/enum-select.test.js
git commit -m "feat(taskmaster): EnumSelect field renderer (v3-edit-001)"
```

### Task 3c: NumberField

Same scaffold. Coerce parses to integer; validate enforces min/max; edit mode is `<input type="number">`.

- [ ] **Steps 1–6: Mirror Task 3b** — file paths `number-field.{js,test,demo}`. Test cases:

```js
// viewer/tests/unit/number-field.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';

const dom = new JSDOM('<!doctype html><html><body></body></html>');
globalThis.document = dom.window.document;
globalThis.window = dom.window;

const { NumberField } = await import('../../js/components/edit/fields/number-field.js');

test('read renders integer or em-dash for null', () => {
  assert.equal(NumberField.read({ value: 5, readOnly: false }).textContent, '5');
  assert.equal(NumberField.read({ value: null, readOnly: false }).textContent, '—');
});

test('edit renders type=number input', () => {
  const el = NumberField.edit({ value: 3, onChange: () => {}, onCommit: () => {}, onCancel: () => {} });
  assert.equal(el.type, 'number');
  assert.equal(el.value, '3');
});

test('coerce returns integer or null', () => {
  assert.equal(NumberField.coerce('7'), 7);
  assert.equal(NumberField.coerce(''), null);
  assert.equal(NumberField.coerce('abc'), null);
});

test('validate min/max', () => {
  assert.equal(NumberField.validate(5, { min: 1, max: 10 }), null);
  assert.equal(NumberField.validate(0, { min: 1 }), 'must be ≥ 1');
  assert.equal(NumberField.validate(11, { max: 10 }), 'must be ≤ 10');
});
```

Implementation:

```js
// viewer/js/components/edit/fields/number-field.js
import { h } from '../../../util/h.js';

export const NumberField = {
  read({ value, readOnly = false }) {
    const cls = ['ef-num']; if (!readOnly) cls.push('ef-editable');
    return h('span', { class: cls.join(' ') }, value == null ? '—' : String(value));
  },
  edit({ value, onChange, onCommit, onCancel, min, max }) {
    const inp = h('input', { type: 'number', class: 'ef-num-input', value: value == null ? '' : String(value) });
    if (min != null) inp.setAttribute('min', String(min));
    if (max != null) inp.setAttribute('max', String(max));
    inp.addEventListener('input', () => onChange?.(inp.value));
    inp.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); onCommit?.(inp.value); }
      else if (e.key === 'Escape') { e.preventDefault(); onCancel?.(); }
    });
    inp.addEventListener('blur', () => onCommit?.(inp.value));
    queueMicrotask(() => { inp.focus(); inp.select(); });
    return inp;
  },
  coerce(raw) {
    if (raw == null || raw === '') return null;
    const n = Number(raw); return Number.isFinite(n) ? Math.trunc(n) : null;
  },
  validate(value, { required = false, min = null, max = null } = {}) {
    if (required && value == null) return 'required';
    if (value != null) {
      if (min != null && value < min) return `must be ≥ ${min}`;
      if (max != null && value > max) return `must be ≤ ${max}`;
    }
    return null;
  },
};
```

CSS append:

```css
.ef-num-input { font: inherit; color: var(--ink); background: var(--bg-card); border: 1px solid var(--border); border-radius: 3px; padding: 1px 6px; width: 80px; outline: none; }
.ef-num-input:focus { border-color: var(--accent); }
```

Demo + commit follow Task 3b's shape.

```bash
git commit -m "feat(taskmaster): NumberField field renderer (v3-edit-001)"
```

### Task 3d: DateField

Edit mode is `<input type="date">` for browser-native picker. Coerce normalizes to `YYYY-MM-DD`. Validate parses against `Date.parse`.

- [ ] **Steps 1–6: Mirror Task 3c** — file paths `date-field.{js,test,demo}`.

Test cases:

```js
// viewer/tests/unit/date-field.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';

const dom = new JSDOM('<!doctype html><html><body></body></html>');
globalThis.document = dom.window.document;
globalThis.window = dom.window;

const { DateField } = await import('../../js/components/edit/fields/date-field.js');

test('read renders ISO date or em-dash', () => {
  assert.equal(DateField.read({ value: '2026-05-04', readOnly: false }).textContent, '2026-05-04');
  assert.equal(DateField.read({ value: null, readOnly: false }).textContent, '—');
});

test('edit renders type=date with value', () => {
  const el = DateField.edit({ value: '2026-05-04', onChange: () => {}, onCommit: () => {}, onCancel: () => {} });
  assert.equal(el.type, 'date');
  assert.equal(el.value, '2026-05-04');
});

test('coerce extracts YYYY-MM-DD from full ISO string', () => {
  assert.equal(DateField.coerce('2026-05-04T16:30:00Z'), '2026-05-04');
  assert.equal(DateField.coerce('2026-05-04'), '2026-05-04');
  assert.equal(DateField.coerce(''), null);
  assert.equal(DateField.coerce('garbage'), null);
});
```

Implementation:

```js
// viewer/js/components/edit/fields/date-field.js
import { h } from '../../../util/h.js';

const ISO_DATE_RE = /^(\d{4}-\d{2}-\d{2})/;

export const DateField = {
  read({ value, readOnly = false }) {
    const cls = ['ef-date']; if (!readOnly) cls.push('ef-editable');
    return h('span', { class: cls.join(' ') }, value == null ? '—' : String(value).slice(0, 10));
  },
  edit({ value, onChange, onCommit, onCancel }) {
    const inp = h('input', { type: 'date', class: 'ef-date-input' });
    if (value) inp.value = String(value).slice(0, 10);
    inp.addEventListener('input', () => onChange?.(inp.value));
    inp.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); onCommit?.(inp.value); }
      else if (e.key === 'Escape') { e.preventDefault(); onCancel?.(); }
    });
    inp.addEventListener('blur', () => onCommit?.(inp.value));
    queueMicrotask(() => inp.focus());
    return inp;
  },
  coerce(raw) {
    if (raw == null || raw === '') return null;
    const m = ISO_DATE_RE.exec(String(raw));
    if (!m) return null;
    const d = new Date(m[1] + 'T00:00:00Z');
    return Number.isFinite(d.getTime()) ? m[1] : null;
  },
  validate(value, { required = false } = {}) {
    if (required && (value == null || value === '')) return 'required';
    if (value != null && value !== '' && DateField.coerce(value) == null) return 'invalid date';
    return null;
  },
};
```

CSS append:

```css
.ef-date-input { font: inherit; color: var(--ink); background: var(--bg-card); border: 1px solid var(--border); border-radius: 3px; padding: 1px 6px; outline: none; }
.ef-date-input:focus { border-color: var(--accent); }
```

```bash
git commit -m "feat(taskmaster): DateField field renderer (v3-edit-001)"
```

---

## Task 4: ChipInput renderer (workhorse for relations)

**Files:**
- Create: `viewer/js/components/edit/fields/chip-input.js`
- Create: `viewer/js/components/edit/fields/chip-input-demo.js`
- Create: `viewer/tests/unit/chip-input.test.js`
- Modify: `viewer/css/components/edit-fields.css`
- Modify: `viewer/js/dev/edit-demo.js`

ChipInput accepts a list of string values (or `{value, label}` objects). It renders existing items as chips with ✕ on hover, plus an autocomplete input. The `source` prop is a function `(query: string) => Promise<{value, label, hint?}[]>` — async because future relation pickers (`tasks`, `epics`) will fetch from the backlog store. For free-text inputs (e.g. `components`, `docs` keys), `source` simply returns `[]` and Enter commits the typed string verbatim.

Public API:
```js
ChipInput.read({ value: string[], readOnly })
ChipInput.edit({ value: string[], source, onChange, onCommit, onCancel, allowFree, placeholder })
ChipInput.coerce(rawValue)         // → string[] | null
ChipInput.validate(value, props)    // → null | error
```

Note: ChipInput's `edit` is **stateful** — unlike text/enum/number where edit is a single DOM input, ChipInput needs to track its own draft list of chips while the user adds/removes them. The wrapper (`inline-field.js` / `entity-modal.js`) only sees `onCommit(currentChips)` when the user blurs/commits.

- [ ] **Step 1: Write the failing test**

```js
// viewer/tests/unit/chip-input.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';

const dom = new JSDOM('<!doctype html><html><body></body></html>');
globalThis.document = dom.window.document;
globalThis.window = dom.window;
globalThis.HTMLElement = dom.window.HTMLElement;

const { ChipInput } = await import('../../js/components/edit/fields/chip-input.js');

test('read renders one chip per value with comma separator class', () => {
  const el = ChipInput.read({ value: ['a', 'b', 'c'], readOnly: false });
  const chips = el.querySelectorAll('.ef-chip');
  assert.equal(chips.length, 3);
  assert.equal(chips[0].textContent, 'a');
});

test('read with empty value renders placeholder', () => {
  const el = ChipInput.read({ value: [], readOnly: false, placeholder: 'no tags' });
  assert.match(el.textContent, /no tags/);
  assert.ok(el.classList.contains('ef-placeholder'));
});

test('edit renders chip-list + autocomplete input', () => {
  const el = ChipInput.edit({
    value: ['x', 'y'],
    source: async () => [],
    onChange: () => {}, onCommit: () => {}, onCancel: () => {},
  });
  assert.equal(el.querySelectorAll('.ef-chip').length, 2);
  assert.ok(el.querySelector('input.ef-chip-input-text'));
});

test('clicking ✕ on a chip removes it from draft', async () => {
  let lastDraft = null;
  const el = ChipInput.edit({
    value: ['a', 'b'],
    source: async () => [],
    onChange: (v) => { lastDraft = v; },
    onCommit: () => {}, onCancel: () => {},
  });
  document.body.appendChild(el);
  const removeBtn = el.querySelectorAll('.ef-chip-x')[0];
  removeBtn.click();
  assert.deepEqual(lastDraft, ['b']);
  assert.equal(el.querySelectorAll('.ef-chip').length, 1);
});

test('typing + Enter with allowFree commits a free-text chip', async () => {
  let drafts = [];
  const el = ChipInput.edit({
    value: ['a'],
    source: async () => [],
    allowFree: true,
    onChange: (v) => { drafts.push([...v]); },
    onCommit: () => {}, onCancel: () => {},
  });
  document.body.appendChild(el);
  const input = el.querySelector('input.ef-chip-input-text');
  input.value = 'b';
  input.dispatchEvent(new dom.window.Event('input'));
  input.dispatchEvent(new dom.window.KeyboardEvent('keydown', { key: 'Enter' }));
  assert.deepEqual(drafts.at(-1), ['a', 'b']);
});

test('Enter without allowFree and no autocomplete match does nothing', () => {
  let changes = 0;
  const el = ChipInput.edit({
    value: ['a'],
    source: async () => [],
    allowFree: false,
    onChange: () => { changes++; },
    onCommit: () => {}, onCancel: () => {},
  });
  document.body.appendChild(el);
  const input = el.querySelector('input.ef-chip-input-text');
  input.value = 'b';
  input.dispatchEvent(new dom.window.Event('input'));
  input.dispatchEvent(new dom.window.KeyboardEvent('keydown', { key: 'Enter' }));
  // Should not have committed a chip — no autocomplete match and free-text disabled.
  assert.equal(el.querySelectorAll('.ef-chip').length, 1);
});

test('coerce dedupes and trims', () => {
  assert.deepEqual(ChipInput.coerce(['a', 'a', 'b ']), ['a', 'b']);
  assert.deepEqual(ChipInput.coerce(null), []);
});

test('validate enforces required + min count', () => {
  assert.equal(ChipInput.validate([], { required: true }), 'required');
  assert.equal(ChipInput.validate(['a'], { required: true }), null);
  assert.equal(ChipInput.validate([], { minCount: 2 }), 'need at least 2');
});
```

- [ ] **Step 2: Run test (fails)**

Run: `cd plugins/taskmaster/viewer && npm run test:unit -- tests/unit/chip-input.test.js`

- [ ] **Step 3: Implement ChipInput**

```js
// viewer/js/components/edit/fields/chip-input.js
import { h } from '../../../util/h.js';

const MAX_DROPDOWN = 8;

export const ChipInput = {
  read({ value, readOnly = false, placeholder = '' }) {
    const items = Array.isArray(value) ? value : [];
    if (items.length === 0) {
      const cls = ['ef-chips', 'ef-placeholder'];
      if (!readOnly) cls.push('ef-editable');
      return h('span', { class: cls.join(' ') }, placeholder || 'none');
    }
    const cls = ['ef-chips']; if (!readOnly) cls.push('ef-editable');
    const wrap = h('span', { class: cls.join(' ') });
    for (const v of items) {
      wrap.appendChild(h('span', { class: 'ef-chip' }, _displayLabel(v)));
    }
    return wrap;
  },

  edit({ value, source, onChange, onCommit, onCancel, allowFree = false, placeholder = 'add…' }) {
    const draft = Array.isArray(value) ? [...value] : [];
    const wrap = h('div', { class: 'ef-chip-input' });
    const chipsBox = h('div', { class: 'ef-chip-list' });
    const inputBox = h('div', { class: 'ef-chip-input-row' });
    const input = h('input', { type: 'text', class: 'ef-chip-input-text', placeholder });
    const dropdown = h('div', { class: 'ef-chip-dropdown', style: 'display:none' });
    inputBox.appendChild(input);
    inputBox.appendChild(dropdown);
    wrap.appendChild(chipsBox);
    wrap.appendChild(inputBox);

    let highlighted = -1;
    let suggestions = [];

    function paintChips() {
      chipsBox.replaceChildren(...draft.map((v) => {
        const chip = h('span', { class: 'ef-chip' });
        chip.appendChild(h('span', { class: 'ef-chip-label' }, _displayLabel(v)));
        const x = h('button', { type: 'button', class: 'ef-chip-x', 'aria-label': 'remove' }, '✕');
        x.addEventListener('click', (e) => {
          e.preventDefault();
          const i = draft.indexOf(v);
          if (i >= 0) {
            draft.splice(i, 1);
            paintChips();
            onChange?.([...draft]);
          }
        });
        chip.appendChild(x);
        return chip;
      }));
    }
    paintChips();

    async function refreshDropdown() {
      const q = input.value.trim();
      if (!q) { dropdown.style.display = 'none'; suggestions = []; return; }
      let raw = [];
      try { raw = (await source(q)) || []; } catch (e) { raw = []; }
      // Filter out already-chosen items.
      suggestions = raw.filter(s => !draft.some(d => _val(d) === _val(s))).slice(0, MAX_DROPDOWN);
      if (!suggestions.length) { dropdown.style.display = 'none'; return; }
      dropdown.replaceChildren(...suggestions.map((s, i) => {
        const row = h('div', { class: 'ef-chip-dd-row' + (i === 0 ? ' ef-chip-dd-active' : '') });
        row.appendChild(h('span', { class: 'ef-chip-dd-val' }, _displayLabel(s)));
        if (s.hint) row.appendChild(h('span', { class: 'ef-chip-dd-hint' }, s.hint));
        row.addEventListener('mousedown', (e) => { e.preventDefault(); commitChoice(s); });
        return row;
      }));
      highlighted = 0;
      dropdown.style.display = '';
    }

    function commitChoice(s) {
      draft.push(_val(s));
      paintChips();
      input.value = '';
      dropdown.style.display = 'none';
      suggestions = [];
      onChange?.([...draft]);
      input.focus();
    }

    function commitFree() {
      const v = input.value.trim();
      if (!v) return;
      if (draft.includes(v)) { input.value = ''; return; }
      draft.push(v);
      paintChips();
      input.value = '';
      onChange?.([...draft]);
    }

    input.addEventListener('input', refreshDropdown);
    input.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowDown' && suggestions.length) {
        e.preventDefault();
        highlighted = Math.min(highlighted + 1, suggestions.length - 1);
        _paintHighlight(dropdown, highlighted);
      } else if (e.key === 'ArrowUp' && suggestions.length) {
        e.preventDefault();
        highlighted = Math.max(highlighted - 1, 0);
        _paintHighlight(dropdown, highlighted);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (highlighted >= 0 && suggestions[highlighted]) commitChoice(suggestions[highlighted]);
        else if (allowFree) commitFree();
      } else if (e.key === 'Tab' && suggestions.length) {
        e.preventDefault();
        commitChoice(suggestions[highlighted >= 0 ? highlighted : 0]);
      } else if (e.key === 'Escape') {
        e.preventDefault();
        if (input.value) { input.value = ''; dropdown.style.display = 'none'; }
        else onCancel?.();
      } else if (e.key === 'Backspace' && !input.value && draft.length) {
        e.preventDefault();
        draft.pop();
        paintChips();
        onChange?.([...draft]);
      }
    });
    input.addEventListener('blur', () => {
      // Slight delay so a mousedown on dropdown row still fires.
      setTimeout(() => onCommit?.([...draft]), 80);
    });
    queueMicrotask(() => input.focus());
    return wrap;
  },

  coerce(raw) {
    if (!Array.isArray(raw)) return [];
    const out = [];
    const seen = new Set();
    for (const v of raw) {
      const t = typeof v === 'string' ? v.trim() : _val(v);
      if (t && !seen.has(t)) { seen.add(t); out.push(t); }
    }
    return out;
  },

  validate(value, { required = false, minCount = null } = {}) {
    const arr = Array.isArray(value) ? value : [];
    if (required && arr.length === 0) return 'required';
    if (minCount != null && arr.length < minCount) return `need at least ${minCount}`;
    return null;
  },
};

function _val(s) { return typeof s === 'string' ? s : (s && s.value); }
function _displayLabel(s) { return typeof s === 'string' ? s : (s && (s.label || s.value)) || ''; }
function _paintHighlight(dropdown, i) {
  const rows = dropdown.querySelectorAll('.ef-chip-dd-row');
  rows.forEach((r, idx) => r.classList.toggle('ef-chip-dd-active', idx === i));
}
```

- [ ] **Step 4: CSS additions**

Append to `viewer/css/components/edit-fields.css`:

```css
.ef-chips { display: inline-flex; flex-wrap: wrap; gap: 4px; align-items: center; }
.ef-chip {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 1px 6px; font-size: var(--text-sm);
  background: var(--bg-card); border: 1px solid var(--border-soft);
  border-radius: 10px; color: var(--ink-2);
}
.ef-chip-label { font-family: var(--font-mono); }
.ef-chip-x {
  background: none; border: none; color: var(--ink-3);
  cursor: pointer; padding: 0; font-size: var(--text-xs);
  opacity: 0; transition: opacity 0.15s;
}
.ef-chip:hover .ef-chip-x { opacity: 1; }
.ef-chip-x:hover { color: var(--red); }

.ef-chip-input { display: flex; flex-direction: column; gap: 4px; min-width: 200px; }
.ef-chip-list { display: flex; flex-wrap: wrap; gap: 4px; }
.ef-chip-input-row { position: relative; }
.ef-chip-input-text {
  font: inherit; color: var(--ink); background: var(--bg-card);
  border: 1px solid var(--border); border-radius: 3px;
  padding: 2px 6px; width: 100%; outline: none;
}
.ef-chip-input-text:focus { border-color: var(--accent); }
.ef-chip-dropdown {
  position: absolute; left: 0; top: 100%; margin-top: 2px;
  background: var(--bg-deep); border: 1px solid var(--border);
  border-radius: 4px; min-width: 240px; max-width: 360px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.3); z-index: 10;
  max-height: 240px; overflow-y: auto;
}
.ef-chip-dd-row {
  padding: 4px 8px; cursor: pointer;
  display: flex; gap: 8px; align-items: center;
  font-size: var(--text-sm); color: var(--ink-2);
}
.ef-chip-dd-row.ef-chip-dd-active { background: color-mix(in oklch, var(--accent) 20%, transparent); color: var(--ink); }
.ef-chip-dd-row:hover { background: var(--bg-card); }
.ef-chip-dd-hint { color: var(--ink-3); font-size: var(--text-xs); margin-left: auto; }
```

- [ ] **Step 5: Demo**

```js
// viewer/js/components/edit/fields/chip-input-demo.js
import { h } from '../../../util/h.js';
import { registerDemo } from '../../../dev/edit-demo.js';
import { ChipInput } from './chip-input.js';

const SAMPLE = ['frontend', 'backend', 'css', 'tests', 'viewer', 'mcp', 'docs'];
const fakeSource = async (q) => SAMPLE
  .filter(s => s.includes(q.toLowerCase()))
  .map(s => ({ value: s, label: s }));

registerDemo('ChipInput (free-text)', (root) => {
  root.appendChild(h('div', { style: 'margin-bottom:8px' }, [
    h('strong', {}, 'Read: '),
    ChipInput.read({ value: ['frontend', 'css'], readOnly: false }),
  ]));
  const editHost = h('div', {}, [h('strong', {}, 'Edit (free-text + autocomplete): ')]);
  editHost.appendChild(ChipInput.edit({
    value: ['css'], source: fakeSource, allowFree: true,
    onChange: (v) => console.log('chip change', v),
    onCommit: (v) => console.log('chip commit', v),
    onCancel: () => console.log('chip cancel'),
  }));
  root.appendChild(editHost);
});
```

Add `import './../components/edit/fields/chip-input-demo.js';` to `edit-demo.js`.

- [ ] **Step 6: Run + commit**

```bash
cd plugins/taskmaster/viewer && npm run test:unit -- tests/unit/chip-input.test.js
# Expected: PASS — 8/8
git add plugins/taskmaster/viewer/js/components/edit/fields/chip-input.js \
        plugins/taskmaster/viewer/js/components/edit/fields/chip-input-demo.js \
        plugins/taskmaster/viewer/css/components/edit-fields.css \
        plugins/taskmaster/viewer/js/dev/edit-demo.js \
        plugins/taskmaster/viewer/tests/unit/chip-input.test.js
git commit -m "feat(taskmaster): ChipInput field renderer (v3-edit-001)"
```

---

## Task 5: RelationPicker (ChipInput pre-wired to backlog sources)

**Files:**
- Create: `viewer/js/components/edit/fields/relation-picker.js`
- Create: `viewer/js/components/edit/fields/relation-picker-demo.js`
- Create: `viewer/tests/unit/relation-picker.test.js`
- Modify: `viewer/js/dev/edit-demo.js`

RelationPicker wraps ChipInput with a built-in `source` that queries the live backlog (via `store.getBacklog()`) for tasks/epics/phases — so callers don't have to wire fake sources every time. For task-id pickers, dropdown rows show `id · title (status)` — labels live in `s.label`, status badge as `s.hint`.

Sources supported: `'tasks'`, `'epics'`, `'phases'`. For free-text fields (`components`, `docs`), the form uses `ChipInput` directly with `allowFree: true`; RelationPicker is only for backlog references.

- [ ] **Step 1: Test**

```js
// viewer/tests/unit/relation-picker.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';

const dom = new JSDOM('<!doctype html><html><body></body></html>');
globalThis.document = dom.window.document;
globalThis.window = dom.window;

const FAKE_BACKLOG = {
  tasks: [
    { id: 'v3-edit-001', title: 'Field renderers', status: 'todo' },
    { id: 'v3-edit-002', title: 'Modal shell', status: 'todo' },
    { id: 'v3-polish-029', title: 'Flat tasks fix', status: 'in-review' },
  ],
  epics: [
    { id: 'v3-edit', name: 'V3 Edit-in-UI' },
    { id: 'v3-polish', name: 'V3 Polish' },
  ],
  phases: [
    { id: 'ship-v3', name: 'Ship V3' },
  ],
};

const { makeRelationSource } = await import('../../js/components/edit/fields/relation-picker.js');

test('tasks source filters by id substring', async () => {
  const src = makeRelationSource('tasks', () => FAKE_BACKLOG);
  const out = await src('edit');
  assert.equal(out.length, 2);
  assert.equal(out[0].value, 'v3-edit-001');
  assert.match(out[0].label, /Field renderers/);
});

test('tasks source filters by title substring', async () => {
  const src = makeRelationSource('tasks', () => FAKE_BACKLOG);
  const out = await src('flat');
  assert.equal(out.length, 1);
  assert.equal(out[0].value, 'v3-polish-029');
});

test('epics source returns id+name pairs', async () => {
  const src = makeRelationSource('epics', () => FAKE_BACKLOG);
  const out = await src('polish');
  assert.equal(out.length, 1);
  assert.equal(out[0].value, 'v3-polish');
  assert.match(out[0].label, /V3 Polish/);
});

test('unknown source kind throws', () => {
  assert.throws(() => makeRelationSource('bogus', () => FAKE_BACKLOG));
});
```

- [ ] **Step 2: Run (fails)**

- [ ] **Step 3: Implement**

```js
// viewer/js/components/edit/fields/relation-picker.js
// Builds source functions for ChipInput that query the live backlog.
// Used by Task.depends_on, Issue.task_ids, Handover.task_ids, and any
// other field that links to a backlog entity.

import { ChipInput } from './chip-input.js';

const STATUS_BADGE = {
  todo: 'todo', 'in-progress': '▶', 'in-review': 'rev', done: '✓', blocked: '⛔',
};

export function makeRelationSource(kind, getBacklog) {
  if (kind === 'tasks') {
    return async (q) => {
      const b = getBacklog() || {};
      const tasks = Array.isArray(b.tasks) ? b.tasks : [];
      const ql = q.toLowerCase();
      return tasks
        .filter(t => (t.id && t.id.toLowerCase().includes(ql)) ||
                     (t.title && t.title.toLowerCase().includes(ql)))
        .map(t => ({
          value: t.id,
          label: `${t.id} · ${t.title || ''}`,
          hint: STATUS_BADGE[t.status] || t.status || '',
        }));
    };
  }
  if (kind === 'epics') {
    return async (q) => {
      const b = getBacklog() || {};
      const epics = Array.isArray(b.epics) ? b.epics : [];
      const ql = q.toLowerCase();
      return epics
        .filter(e => (e.id && e.id.toLowerCase().includes(ql)) ||
                     (e.name && e.name.toLowerCase().includes(ql)))
        .map(e => ({ value: e.id, label: `${e.id} · ${e.name || ''}` }));
    };
  }
  if (kind === 'phases') {
    return async (q) => {
      const b = getBacklog() || {};
      const phases = Array.isArray(b.phases) ? b.phases : [];
      const ql = q.toLowerCase();
      return phases
        .filter(p => (p.id && p.id.toLowerCase().includes(ql)) ||
                     (p.name && p.name.toLowerCase().includes(ql)))
        .map(p => ({ value: p.id, label: `${p.id} · ${p.name || ''}` }));
    };
  }
  throw new Error(`unknown relation kind: ${kind}`);
}

// Convenience renderer that combines makeRelationSource with ChipInput.
// Forms can use ChipInput directly + makeRelationSource OR call this helper.
export const RelationPicker = {
  read: ChipInput.read,
  edit({ value, kind, getBacklog, onChange, onCommit, onCancel, placeholder }) {
    const source = makeRelationSource(kind, getBacklog);
    return ChipInput.edit({
      value, source, allowFree: false,
      onChange, onCommit, onCancel,
      placeholder: placeholder || `add ${kind.slice(0, -1)}…`,
    });
  },
  coerce: ChipInput.coerce,
  validate: ChipInput.validate,
};
```

- [ ] **Step 4: Demo**

```js
// viewer/js/components/edit/fields/relation-picker-demo.js
import { h } from '../../../util/h.js';
import { registerDemo } from '../../../dev/edit-demo.js';
import { RelationPicker } from './relation-picker.js';

const FAKE_BACKLOG = () => ({
  tasks: [
    { id: 'v3-edit-001', title: 'Field renderers', status: 'todo' },
    { id: 'v3-edit-002', title: 'Modal shell', status: 'todo' },
    { id: 'v3-polish-029', title: 'Flat tasks fix', status: 'in-review' },
  ],
  epics: [
    { id: 'v3-edit', name: 'V3 Edit-in-UI' },
    { id: 'v3-polish', name: 'V3 Polish' },
  ],
});

registerDemo('RelationPicker (tasks)', (root) => {
  const editHost = h('div', {}, [h('strong', {}, 'Add task deps: ')]);
  editHost.appendChild(RelationPicker.edit({
    value: ['v3-polish-029'], kind: 'tasks', getBacklog: FAKE_BACKLOG,
    onChange: (v) => console.log('rel change', v),
    onCommit: (v) => console.log('rel commit', v),
    onCancel: () => console.log('rel cancel'),
  }));
  root.appendChild(editHost);
});
```

Add `import './../components/edit/fields/relation-picker-demo.js';` to `edit-demo.js`.

- [ ] **Step 5: Test/commit**

```bash
cd plugins/taskmaster/viewer && npm run test:unit -- tests/unit/relation-picker.test.js
# Expected: PASS — 4/4
git add plugins/taskmaster/viewer/js/components/edit/fields/relation-picker.js \
        plugins/taskmaster/viewer/js/components/edit/fields/relation-picker-demo.js \
        plugins/taskmaster/viewer/js/dev/edit-demo.js \
        plugins/taskmaster/viewer/tests/unit/relation-picker.test.js
git commit -m "feat(taskmaster): RelationPicker over ChipInput + backlog sources (v3-edit-001)"
```

---

## Task 6: Schema definition + client-side validation runner

**Files:**
- Create: `viewer/js/components/edit/schema.js`
- Create: `viewer/tests/unit/schema.test.js`

A schema describes one entity type as an array of field-spec objects. The runner takes an entity + schema and returns `{ valid, errors }` where `errors` is `{ fieldKey: errorMessage }`. Each field spec also carries a `renderer` (one of the 7 we built) — both the modal and inline-field consume the same spec.

Schema format:
```js
{
  entity: 'task',
  fields: [
    { key: 'title', label: 'Title', renderer: TextField, required: true, maxLength: 140 },
    { key: 'status', label: 'Status', renderer: EnumSelect, required: true, options: [...] },
    { key: 'depends_on', label: 'Depends on', renderer: RelationPicker, kind: 'tasks' },
    ...
  ],
  systemManaged: ['id', 'created', 'started', 'completed', 'last_referenced', ...],
}
```

The `runValidation(entity, schema)` returns errors for fields where:
1. `renderer.validate(value, fieldSpec)` returns a non-null string, OR
2. cross-field rules (declared on the schema as `crossField: [(entity) => null|{key, error}]`) return errors.

- [ ] **Step 1: Test**

```js
// viewer/tests/unit/schema.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';

const dom = new JSDOM('<!doctype html><html><body></body></html>');
globalThis.document = dom.window.document;
globalThis.window = dom.window;

const { TextField } = await import('../../js/components/edit/fields/text-field.js');
const { EnumSelect } = await import('../../js/components/edit/fields/enum-select.js');
const { runValidation, isSystemManaged } = await import('../../js/components/edit/schema.js');

const SCHEMA = {
  entity: 'task',
  fields: [
    { key: 'title', label: 'Title', renderer: TextField, required: true, maxLength: 140 },
    { key: 'status', label: 'Status', renderer: EnumSelect, required: true,
      options: [{ value: 'todo', label: 'Todo' }, { value: 'done', label: 'Done' }] },
  ],
  systemManaged: ['id', 'created'],
  crossField: [
    (e) => e.title === 'forbidden' ? { key: 'title', error: 'reserved word' } : null,
  ],
};

test('runValidation passes when all fields valid', () => {
  const r = runValidation({ title: 'hi', status: 'todo' }, SCHEMA);
  assert.equal(r.valid, true);
  assert.deepEqual(r.errors, {});
});

test('runValidation collects per-field errors', () => {
  const r = runValidation({ title: '', status: 'bogus' }, SCHEMA);
  assert.equal(r.valid, false);
  assert.equal(r.errors.title, 'required');
  assert.equal(r.errors.status, 'invalid value');
});

test('runValidation runs cross-field rules', () => {
  const r = runValidation({ title: 'forbidden', status: 'todo' }, SCHEMA);
  assert.equal(r.valid, false);
  assert.equal(r.errors.title, 'reserved word');
});

test('isSystemManaged reads schema list', () => {
  assert.equal(isSystemManaged('id', SCHEMA), true);
  assert.equal(isSystemManaged('title', SCHEMA), false);
});
```

- [ ] **Step 2: Run (fails)**

- [ ] **Step 3: Implement**

```js
// viewer/js/components/edit/schema.js
// Shared validation runner. Each field's renderer.validate(value, spec)
// is the source of truth for its own field rules. Cross-field rules live
// on the schema itself.

export function runValidation(entity, schema) {
  const errors = {};
  for (const f of schema.fields || []) {
    const value = entity[f.key];
    const err = f.renderer?.validate?.(value, f);
    if (err) errors[f.key] = err;
  }
  for (const rule of schema.crossField || []) {
    const r = rule(entity);
    if (r && r.key && r.error && !errors[r.key]) errors[r.key] = r.error;
  }
  return { valid: Object.keys(errors).length === 0, errors };
}

export function isSystemManaged(key, schema) {
  return Array.isArray(schema.systemManaged) && schema.systemManaged.includes(key);
}

export function fieldByKey(schema, key) {
  return (schema.fields || []).find(f => f.key === key) || null;
}
```

- [ ] **Step 4: Run + commit**

```bash
cd plugins/taskmaster/viewer && npm run test:unit -- tests/unit/schema.test.js
# Expected: PASS — 4/4
git add plugins/taskmaster/viewer/js/components/edit/schema.js \
        plugins/taskmaster/viewer/tests/unit/schema.test.js
git commit -m "feat(taskmaster): schema validation runner (v3-edit-001)"
```

---

## Task 7: entity-modal shell

**Files:**
- Create: `viewer/js/components/edit/entity-modal.js`
- Create: `viewer/css/components/entity-modal.css`
- Create: `viewer/tests/unit/entity-modal.test.js`
- Modify: `viewer/index.html` (add `<div id="entity-modal-host">`)
- Modify: `viewer/css/shell.css` (import the new CSS)

The modal is the centered-overlay form used for entity creation and full-edit (per spec §UX patterns — modal lifecycle). It accepts `{ schema, mode, initialEntity, onSave, onCancel }` and renders:
- Header: entity-type label + mode label (Create / Edit) + close ✕
- Body: field list grouped by `schema.layout` (Task 13 will define a real layout; this task uses a flat field list as the default)
- Footer: error summary on the left, Cancel + Save buttons on the right

Save is enabled iff (dirty AND valid). Errors display per field below each renderer.

Public API:
```js
const close = openEntityModal({
  schema, mode: 'create' | 'edit',
  initialEntity, // {} for create
  onSave: async (entity) => undefined | { error: 'message' },
  onCancel: () => void,
});
// `close()` programmatically dismisses the modal.
```

- [ ] **Step 1: Test**

```js
// viewer/tests/unit/entity-modal.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';

const dom = new JSDOM('<!doctype html><html><body><div id="entity-modal-host"></div></body></html>');
globalThis.document = dom.window.document;
globalThis.window = dom.window;
globalThis.HTMLElement = dom.window.HTMLElement;
globalThis.queueMicrotask = queueMicrotask;

const { TextField } = await import('../../js/components/edit/fields/text-field.js');
const { EnumSelect } = await import('../../js/components/edit/fields/enum-select.js');
const { openEntityModal } = await import('../../js/components/edit/entity-modal.js');

const STATUSES = [{ value: 'todo', label: 'Todo' }, { value: 'done', label: 'Done' }];
const SCHEMA = {
  entity: 'task',
  label: 'Task',
  fields: [
    { key: 'title', label: 'Title', renderer: TextField, required: true, maxLength: 140 },
    { key: 'status', label: 'Status', renderer: EnumSelect, required: true, options: STATUSES },
  ],
};

test('opens modal in create mode with empty fields and disabled Save', () => {
  const close = openEntityModal({ schema: SCHEMA, mode: 'create', initialEntity: {}, onSave: async () => {}, onCancel: () => {} });
  const modal = document.querySelector('.em-modal');
  assert.ok(modal, 'modal mounted');
  assert.match(modal.querySelector('.em-header').textContent, /Create.*Task/);
  const saveBtn = modal.querySelector('.em-save');
  assert.equal(saveBtn.disabled, true);
  close();
  assert.equal(document.querySelector('.em-modal'), null);
});

test('Save enables when required fields are filled and valid', () => {
  let savedEntity = null;
  const close = openEntityModal({
    schema: SCHEMA, mode: 'create', initialEntity: {},
    onSave: async (e) => { savedEntity = e; },
    onCancel: () => {},
  });
  const titleInput = document.querySelector('.em-field[data-key="title"] input');
  titleInput.value = 'hi'; titleInput.dispatchEvent(new dom.window.Event('input'));
  const statusSel = document.querySelector('.em-field[data-key="status"] select');
  statusSel.value = 'todo'; statusSel.dispatchEvent(new dom.window.Event('change'));
  const saveBtn = document.querySelector('.em-save');
  assert.equal(saveBtn.disabled, false);
  close();
});

test('Cancel closes without firing onSave', () => {
  let saveCalled = false;
  let cancelled = false;
  const close = openEntityModal({
    schema: SCHEMA, mode: 'create', initialEntity: {},
    onSave: async () => { saveCalled = true; },
    onCancel: () => { cancelled = true; },
  });
  document.querySelector('.em-cancel').click();
  assert.equal(saveCalled, false);
  assert.equal(cancelled, true);
  assert.equal(document.querySelector('.em-modal'), null);
});

test('edit mode prefills initialEntity values', () => {
  const close = openEntityModal({
    schema: SCHEMA, mode: 'edit',
    initialEntity: { title: 'existing', status: 'done' },
    onSave: async () => {}, onCancel: () => {},
  });
  const titleInput = document.querySelector('.em-field[data-key="title"] input');
  assert.equal(titleInput.value, 'existing');
  const statusSel = document.querySelector('.em-field[data-key="status"] select');
  assert.equal(statusSel.value, 'done');
  close();
});

test('Save calls onSave with current draft and closes on success', async () => {
  let savedEntity = null;
  const close = openEntityModal({
    schema: SCHEMA, mode: 'create', initialEntity: {},
    onSave: async (e) => { savedEntity = e; return undefined; },
    onCancel: () => {},
  });
  const titleInput = document.querySelector('.em-field[data-key="title"] input');
  titleInput.value = 'hi'; titleInput.dispatchEvent(new dom.window.Event('input'));
  const statusSel = document.querySelector('.em-field[data-key="status"] select');
  statusSel.value = 'todo'; statusSel.dispatchEvent(new dom.window.Event('change'));
  document.querySelector('.em-save').click();
  // Wait for microtask chain.
  await new Promise(r => setTimeout(r, 10));
  assert.deepEqual(savedEntity, { title: 'hi', status: 'todo' });
  assert.equal(document.querySelector('.em-modal'), null);
});
```

- [ ] **Step 2: Run (fails)**

- [ ] **Step 3: Implement entity-modal**

```js
// viewer/js/components/edit/entity-modal.js
// Centered-overlay modal for entity creation + full-edit. See spec §UX patterns
// for lifecycle. Mounts into #entity-modal-host (added to viewer/index.html).

import { h } from '../../util/h.js';
import { runValidation } from './schema.js';

const HOST_ID = 'entity-modal-host';

export function openEntityModal({ schema, mode, initialEntity, onSave, onCancel }) {
  const host = document.getElementById(HOST_ID);
  if (!host) throw new Error(`#${HOST_ID} not found in DOM`);

  // Local draft buffer (modal flow = NO autosave per field).
  const draft = { ...(initialEntity || {}) };
  let saving = false;
  let serverError = null;

  const root = h('div', { class: 'em-overlay', tabindex: '-1' });
  const modal = h('div', { class: 'em-modal', role: 'dialog', 'aria-modal': 'true' });

  // Header
  const header = h('div', { class: 'em-header' }, [
    h('span', { class: 'em-title' }, `${mode === 'create' ? 'Create' : 'Edit'} ${schema.label || schema.entity}`),
    h('button', { type: 'button', class: 'em-close', 'aria-label': 'close',
                  on: { click: () => doCancel() } }, '✕'),
  ]);

  // Body — flat field list for now; Task 13 introduces grouped layouts.
  const body = h('div', { class: 'em-body' });
  const fieldEls = new Map(); // key → { wrap, errEl }

  for (const f of schema.fields || []) {
    const wrap = h('div', { class: 'em-field', 'data-key': f.key }, [
      h('label', { class: 'em-label' }, f.label || f.key),
    ]);
    const renderer = f.renderer;
    const editEl = renderer.edit({
      value: draft[f.key],
      onChange: (v) => { draft[f.key] = renderer.coerce ? renderer.coerce(v) : v; repaintFooter(); },
      onCommit: (v) => { draft[f.key] = renderer.coerce ? renderer.coerce(v) : v; repaintFooter(); },
      onCancel: () => {},
      ...f, // pass through options/min/max/maxLength/etc.
      getBacklog: f.getBacklog, // for relation pickers
    });
    wrap.appendChild(editEl);
    const errEl = h('div', { class: 'em-field-error' });
    wrap.appendChild(errEl);
    body.appendChild(wrap);
    fieldEls.set(f.key, { wrap, errEl });
  }

  // Footer
  const errSummary = h('div', { class: 'em-error-summary' });
  const cancelBtn = h('button', { type: 'button', class: 'em-cancel',
                                  on: { click: () => doCancel() } }, 'Cancel');
  const saveBtn = h('button', { type: 'button', class: 'em-save', disabled: '',
                                on: { click: () => doSave() } }, 'Save');
  const footer = h('div', { class: 'em-footer' }, [
    errSummary,
    h('div', { class: 'em-footer-actions' }, [cancelBtn, saveBtn]),
  ]);

  modal.appendChild(header);
  modal.appendChild(body);
  modal.appendChild(footer);
  root.appendChild(modal);
  host.appendChild(root);
  document.body.classList.add('em-open');

  function repaintFooter() {
    const { valid, errors } = runValidation(draft, schema);
    serverError = null;
    saveBtn.disabled = saving || !valid || !isDirty();
    // Per-field error rendering
    for (const [key, { errEl }] of fieldEls.entries()) {
      errEl.textContent = errors[key] || '';
      errEl.style.display = errors[key] ? '' : 'none';
    }
    const errCount = Object.keys(errors).length;
    errSummary.textContent = errCount === 0 ? '' : `${errCount} field${errCount > 1 ? 's' : ''} need attention`;
  }

  function isDirty() {
    const init = initialEntity || {};
    for (const f of schema.fields || []) {
      const a = init[f.key];
      const b = draft[f.key];
      if (JSON.stringify(a ?? null) !== JSON.stringify(b ?? null)) return true;
    }
    return false;
  }

  async function doSave() {
    if (saving) return;
    const { valid } = runValidation(draft, schema);
    if (!valid) return;
    saving = true; saveBtn.disabled = true; saveBtn.textContent = 'Saving…';
    try {
      const result = await onSave({ ...draft });
      if (result && result.error) {
        serverError = result.error;
        errSummary.textContent = result.error;
        saving = false; saveBtn.disabled = false; saveBtn.textContent = 'Save';
        return;
      }
      doClose();
    } catch (e) {
      serverError = e.message || String(e);
      errSummary.textContent = serverError;
      saving = false; saveBtn.disabled = false; saveBtn.textContent = 'Save';
    }
  }

  function doCancel() {
    if (isDirty() && !window.confirm('Discard changes?')) return;
    onCancel?.();
    doClose();
  }

  function doClose() {
    root.remove();
    document.body.classList.remove('em-open');
    document.removeEventListener('keydown', onKeyDown);
  }

  function onKeyDown(e) {
    if (e.key === 'Escape') { e.preventDefault(); doCancel(); }
  }

  // Backdrop click cancels (with confirm if dirty).
  root.addEventListener('click', (e) => { if (e.target === root) doCancel(); });
  document.addEventListener('keydown', onKeyDown);

  // Focus first input after mount.
  queueMicrotask(() => {
    const firstInput = body.querySelector('input, textarea, select');
    firstInput?.focus();
    repaintFooter();
  });

  return doClose;
}
```

- [ ] **Step 4: CSS**

```css
/* viewer/css/components/entity-modal.css */
body.em-open { overflow: hidden; }

.em-overlay {
  position: fixed; inset: 0; z-index: 100;
  background: rgba(0, 0, 0, 0.55);
  display: flex; align-items: center; justify-content: center;
  animation: em-fade-in 0.18s ease-out;
}
@keyframes em-fade-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}

.em-modal {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  width: min(640px, calc(100vw - 32px));
  max-height: calc(100vh - 64px);
  display: flex; flex-direction: column;
  animation: em-scale-in 0.18s ease-out;
}
@keyframes em-scale-in {
  from { transform: scale(0.96); opacity: 0; }
  to   { transform: scale(1); opacity: 1; }
}

.em-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-soft);
}
.em-title { font-size: var(--text-lg); font-weight: 600; color: var(--ink); }
.em-close {
  background: none; border: none; color: var(--ink-3);
  cursor: pointer; font-size: var(--text-md); padding: 4px;
}
.em-close:hover { color: var(--ink); }

.em-body {
  padding: 16px;
  overflow-y: auto;
  flex: 1;
  display: flex; flex-direction: column; gap: 14px;
}
.em-field { display: flex; flex-direction: column; gap: 4px; }
.em-label {
  font-size: var(--text-xs); text-transform: uppercase;
  letter-spacing: 0.08em; color: var(--ink-3);
}
.em-field-error {
  font-size: var(--text-xs); color: var(--red); display: none;
}

.em-footer {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px;
  border-top: 1px solid var(--border-soft);
  background: var(--bg-deep);
}
.em-error-summary { font-size: var(--text-xs); color: var(--red); }
.em-footer-actions { display: flex; gap: 8px; }
.em-cancel, .em-save {
  font: inherit; padding: 5px 14px; border-radius: 4px; cursor: pointer;
  border: 1px solid var(--border);
}
.em-cancel { background: transparent; color: var(--ink-2); }
.em-cancel:hover { background: var(--bg-card); color: var(--ink); }
.em-save {
  background: var(--accent); color: white; border-color: var(--accent);
}
.em-save:disabled {
  opacity: 0.5; cursor: not-allowed;
  background: var(--bg-card); color: var(--ink-3); border-color: var(--border);
}
```

- [ ] **Step 5: HTML mount**

Edit `viewer/index.html` — find the `<div id="screen-mount">` element. Add a sibling immediately after the closing `</div>` of the shell (right before `</body>` or alongside other top-level mounts):

```html
<div id="entity-modal-host"></div>
<div id="conflict-banner-host"></div>
```

(`conflict-banner-host` is added now even though Task 12 implements the banner; saves a touchpoint later.)

Add to the `<link>` block in `viewer/index.html` (or shell.css `@import` block):

```html
<link rel="stylesheet" href="/static/v3/css/components/entity-modal.css">
```

- [ ] **Step 6: Run + commit**

```bash
cd plugins/taskmaster/viewer && npm run test:unit -- tests/unit/entity-modal.test.js
# Expected: PASS — 5/5
git add plugins/taskmaster/viewer/js/components/edit/entity-modal.js \
        plugins/taskmaster/viewer/css/components/entity-modal.css \
        plugins/taskmaster/viewer/index.html \
        plugins/taskmaster/viewer/tests/unit/entity-modal.test.js
git commit -m "feat(taskmaster): entity-modal shell with dirty/save/cancel UX (v3-edit-002)"
```

---

## Task 8: inline-field wrapper

**Files:**
- Create: `viewer/js/components/edit/inline-field.js`
- Create: `viewer/tests/unit/inline-field.test.js`
- Modify: `viewer/css/components/edit-fields.css`

`inline-field.js` is what detail screens use: it owns the read↔edit swap, the autosave debounce, and the in-flight indicator. Each instance handles ONE field on ONE entity.

Public API:
```js
mountInlineField(parentEl, {
  schema,        // entity schema (for the field's renderer + options)
  fieldKey,      // which field
  entity,        // current value source — read entity[fieldKey]
  onSave: async (newValue) => undefined | { error: 'message' },
  readOnly,      // forces read-only display even if schema says editable
});
// returns a controller: { update(newEntity), destroy() }
```

Lifecycle:
- Mount → render in `read` mode using the field's renderer.
- Click on the read element (when not read-only) → swap to `edit` mode.
- In edit mode, on `onChange` → debounced save after 600ms idle.
- On `onCommit` (Enter/blur for text, change for enums, blur for chip) → flush + swap back to read.
- On `onCancel` (Esc) → revert to last-known-good + swap back.
- Pulsing dot (●) appears next to the field while a save is in flight; ✓ briefly on success; ✕ persists on error with tooltip.

- [ ] **Step 1: Test**

```js
// viewer/tests/unit/inline-field.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';

const dom = new JSDOM('<!doctype html><html><body></body></html>');
globalThis.document = dom.window.document;
globalThis.window = dom.window;
globalThis.queueMicrotask = queueMicrotask;

const { TextField } = await import('../../js/components/edit/fields/text-field.js');
const { mountInlineField } = await import('../../js/components/edit/inline-field.js');

const SCHEMA = {
  entity: 'task',
  fields: [{ key: 'title', label: 'Title', renderer: TextField, required: true, maxLength: 140 }],
};

test('mounts in read mode with editable affordance', () => {
  const root = document.createElement('div');
  document.body.appendChild(root);
  const ctrl = mountInlineField(root, {
    schema: SCHEMA, fieldKey: 'title', entity: { title: 'hello' },
    onSave: async () => {},
  });
  const span = root.querySelector('.ef-text');
  assert.equal(span.textContent, 'hello');
  assert.ok(span.classList.contains('ef-editable'));
  ctrl.destroy();
});

test('click swaps to edit mode', () => {
  const root = document.createElement('div');
  document.body.appendChild(root);
  const ctrl = mountInlineField(root, {
    schema: SCHEMA, fieldKey: 'title', entity: { title: 'hi' },
    onSave: async () => {},
  });
  root.querySelector('.ef-text').click();
  const inp = root.querySelector('input.ef-text-input');
  assert.ok(inp);
  assert.equal(inp.value, 'hi');
  ctrl.destroy();
});

test('Enter triggers onSave with new value and reverts to read mode', async () => {
  const root = document.createElement('div');
  document.body.appendChild(root);
  let saved = null;
  const ctrl = mountInlineField(root, {
    schema: SCHEMA, fieldKey: 'title', entity: { title: 'old' },
    onSave: async (v) => { saved = v; },
  });
  root.querySelector('.ef-text').click();
  const inp = root.querySelector('input.ef-text-input');
  inp.value = 'new';
  inp.dispatchEvent(new dom.window.KeyboardEvent('keydown', { key: 'Enter' }));
  await new Promise(r => setTimeout(r, 30));
  assert.equal(saved, 'new');
  // After save, swap back to read mode.
  await new Promise(r => setTimeout(r, 30));
  assert.ok(root.querySelector('.ef-text'));
  ctrl.destroy();
});

test('Escape reverts without calling onSave', async () => {
  const root = document.createElement('div');
  document.body.appendChild(root);
  let called = false;
  const ctrl = mountInlineField(root, {
    schema: SCHEMA, fieldKey: 'title', entity: { title: 'old' },
    onSave: async () => { called = true; },
  });
  root.querySelector('.ef-text').click();
  const inp = root.querySelector('input.ef-text-input');
  inp.value = 'changed';
  inp.dispatchEvent(new dom.window.KeyboardEvent('keydown', { key: 'Escape' }));
  await new Promise(r => setTimeout(r, 20));
  assert.equal(called, false);
  // Read view shows the ORIGINAL value, not the typed one.
  assert.equal(root.querySelector('.ef-text').textContent, 'old');
  ctrl.destroy();
});

test('readOnly skips edit mode entirely', () => {
  const root = document.createElement('div');
  document.body.appendChild(root);
  const ctrl = mountInlineField(root, {
    schema: SCHEMA, fieldKey: 'title', entity: { title: 'x' }, readOnly: true,
    onSave: async () => {},
  });
  root.querySelector('.ef-text').click();
  // Should still be read-mode after click.
  assert.ok(root.querySelector('.ef-text'));
  assert.equal(root.querySelector('input.ef-text-input'), null);
  ctrl.destroy();
});

test('save error shows ✕ indicator', async () => {
  const root = document.createElement('div');
  document.body.appendChild(root);
  const ctrl = mountInlineField(root, {
    schema: SCHEMA, fieldKey: 'title', entity: { title: 'old' },
    onSave: async () => ({ error: 'server hated it' }),
  });
  root.querySelector('.ef-text').click();
  const inp = root.querySelector('input.ef-text-input');
  inp.value = 'new';
  inp.dispatchEvent(new dom.window.KeyboardEvent('keydown', { key: 'Enter' }));
  await new Promise(r => setTimeout(r, 50));
  const err = root.querySelector('.if-status-error');
  assert.ok(err, 'error indicator visible');
  ctrl.destroy();
});
```

- [ ] **Step 2: Run (fails)**

- [ ] **Step 3: Implement**

```js
// viewer/js/components/edit/inline-field.js
// Read↔edit wrapper for one field on one entity. Used by detail screens.

import { h } from '../../util/h.js';
import { fieldByKey, isSystemManaged } from './schema.js';

const DEBOUNCE_MS = 600;

export function mountInlineField(parent, {
  schema, fieldKey, entity, onSave,
  readOnly = false, getBacklog,
}) {
  const fieldSpec = fieldByKey(schema, fieldKey);
  if (!fieldSpec) throw new Error(`field ${fieldKey} not in schema`);
  const renderer = fieldSpec.renderer;
  // System-managed fields never get an edit affordance.
  const ro = readOnly || isSystemManaged(fieldKey, schema);

  let currentEntity = { ...(entity || {}) };
  let mode = 'read';
  let pendingValue = currentEntity[fieldKey];
  let saveTimer = null;
  let inFlight = false;

  const wrap = h('span', { class: 'if-wrap', 'data-key': fieldKey });
  parent.appendChild(wrap);

  const status = h('span', { class: 'if-status' });
  parent.appendChild(status);

  paint();

  function paint() {
    wrap.replaceChildren();
    if (mode === 'read') {
      const el = renderer.read({
        value: currentEntity[fieldKey],
        readOnly: ro,
        placeholder: fieldSpec.placeholder,
        ...fieldSpec,
      });
      if (!ro) el.addEventListener('click', enterEdit);
      wrap.appendChild(el);
    } else {
      const el = renderer.edit({
        value: currentEntity[fieldKey],
        onChange: (v) => {
          pendingValue = renderer.coerce ? renderer.coerce(v) : v;
          scheduleSave();
        },
        onCommit: (v) => {
          pendingValue = renderer.coerce ? renderer.coerce(v) : v;
          flushSave().then(() => {
            mode = 'read';
            currentEntity[fieldKey] = pendingValue;
            paint();
          });
        },
        onCancel: () => {
          if (saveTimer) { clearTimeout(saveTimer); saveTimer = null; }
          pendingValue = currentEntity[fieldKey];
          mode = 'read';
          paint();
        },
        getBacklog,
        ...fieldSpec,
      });
      wrap.appendChild(el);
    }
  }

  function enterEdit() {
    if (ro) return;
    pendingValue = currentEntity[fieldKey];
    mode = 'edit';
    paint();
  }

  function scheduleSave() {
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(flushSave, DEBOUNCE_MS);
  }

  async function flushSave() {
    if (saveTimer) { clearTimeout(saveTimer); saveTimer = null; }
    const v = pendingValue;
    if (sameValue(v, currentEntity[fieldKey])) return;
    inFlight = true;
    setStatus('saving');
    try {
      const result = await onSave(v);
      if (result && result.error) {
        setStatus('error', result.error);
        return;
      }
      currentEntity[fieldKey] = v;
      setStatus('ok');
      setTimeout(() => setStatus(''), 800);
    } catch (e) {
      setStatus('error', e.message || String(e));
    } finally {
      inFlight = false;
    }
  }

  function setStatus(kind, msg) {
    status.replaceChildren();
    status.className = 'if-status';
    if (!kind) return;
    if (kind === 'saving')  status.appendChild(h('span', { class: 'if-status-saving' }, '●'));
    if (kind === 'ok')      status.appendChild(h('span', { class: 'if-status-ok' }, '✓'));
    if (kind === 'error') {
      const x = h('span', { class: 'if-status-error', title: msg || 'save failed' }, '✕');
      status.appendChild(x);
    }
  }

  function sameValue(a, b) {
    return JSON.stringify(a ?? null) === JSON.stringify(b ?? null);
  }

  return {
    update(newEntity) {
      currentEntity = { ...(newEntity || {}) };
      if (mode === 'read') paint();
    },
    destroy() {
      if (saveTimer) clearTimeout(saveTimer);
      wrap.remove();
      status.remove();
    },
  };
}
```

- [ ] **Step 4: CSS — append to `edit-fields.css`**

```css
.if-wrap { display: inline-block; }
.if-status {
  display: inline-block; margin-left: 6px;
  font-size: var(--text-xs); vertical-align: middle;
}
.if-status-saving {
  color: var(--accent);
  animation: if-pulse 0.9s ease-in-out infinite;
}
@keyframes if-pulse {
  0%, 100% { opacity: 0.4; }
  50%      { opacity: 1.0; }
}
.if-status-ok    { color: var(--green); }
.if-status-error { color: var(--red); cursor: help; }
```

- [ ] **Step 5: Run + commit**

```bash
cd plugins/taskmaster/viewer && npm run test:unit -- tests/unit/inline-field.test.js
# Expected: PASS — 6/6
git add plugins/taskmaster/viewer/js/components/edit/inline-field.js \
        plugins/taskmaster/viewer/css/components/edit-fields.css \
        plugins/taskmaster/viewer/tests/unit/inline-field.test.js
git commit -m "feat(taskmaster): inline-field wrapper with autosave + status indicator (v3-edit-003)"
```

---

## Task 9: HTTP write API for tasks + Python write primitives

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py` — add `update_task`, `create_task`, `archive_task`, `with_file_lock` (etag added in Task 10)
- Modify: `plugins/taskmaster/backlog_server.py` — add `do_PATCH`, `POST /api/tasks`, `POST /api/tasks/<id>/archive`, `PUT /api/tasks/<id>`
- Modify: `plugins/taskmaster/viewer/js/api.js` — add `createTask`, `patchTask`, `putTask`, `archiveTask`
- Create: `plugins/taskmaster/tests/test_v3_task_writes.py`
- Create: `plugins/taskmaster/tests/test_server_task_write.py`

The v2-nested-tasks layout is the canonical storage today (per the spec's notes on `v3-polish-029`). Write primitives MUST handle both v2 (nested under epics) and v3 (flat tasks index + per-task .md files) so they keep working through migration. Implementation strategy: read the YAML, locate the task by id, mutate, write back via `atomic_write`.

- [ ] **Step 1: Test the Python primitives**

```python
# plugins/taskmaster/tests/test_v3_task_writes.py
import pytest
import yaml
from pathlib import Path


@pytest.fixture
def v2_backlog(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    bp = tmp_path / "backlog.yaml"
    bp.write_text(yaml.safe_dump({
        "meta": {"project": "test"},
        "epics": [
            {"id": "e1", "name": "E1", "status": "active",
             "tasks": [
                 {"id": "e1-001", "title": "Existing task", "status": "todo",
                  "priority": "medium", "depends_on": []},
             ]},
        ],
        "phases": [{"id": "p1", "name": "P1", "status": "active"}],
    }))
    return bp


def test_update_task_patches_existing_field(v2_backlog):
    from taskmaster_v3 import update_task
    update_task("e1-001", {"title": "Renamed"}, backlog_path=v2_backlog)
    data = yaml.safe_load(v2_backlog.read_text())
    assert data["epics"][0]["tasks"][0]["title"] == "Renamed"


def test_update_task_unknown_id_raises(v2_backlog):
    from taskmaster_v3 import update_task
    with pytest.raises(KeyError):
        update_task("nope", {"title": "x"}, backlog_path=v2_backlog)


def test_update_task_status_transition_stamps_started(v2_backlog):
    """When status moves to in-progress for the first time, started is set."""
    from taskmaster_v3 import update_task
    update_task("e1-001", {"status": "in-progress"}, backlog_path=v2_backlog)
    data = yaml.safe_load(v2_backlog.read_text())
    assert data["epics"][0]["tasks"][0]["status"] == "in-progress"
    started = data["epics"][0]["tasks"][0].get("started")
    assert started is not None
    assert len(started) >= 10  # at least YYYY-MM-DD


def test_update_task_status_transition_stamps_completed(v2_backlog):
    from taskmaster_v3 import update_task
    update_task("e1-001", {"status": "done"}, backlog_path=v2_backlog)
    data = yaml.safe_load(v2_backlog.read_text())
    assert data["epics"][0]["tasks"][0]["status"] == "done"
    assert data["epics"][0]["tasks"][0].get("completed") is not None


def test_update_task_does_not_overwrite_existing_started(v2_backlog):
    from taskmaster_v3 import update_task
    update_task("e1-001", {"status": "in-progress", "started": "2026-01-01"},
                backlog_path=v2_backlog)
    update_task("e1-001", {"status": "in-review"}, backlog_path=v2_backlog)
    data = yaml.safe_load(v2_backlog.read_text())
    assert data["epics"][0]["tasks"][0]["started"] == "2026-01-01"


def test_create_task_assigns_id_under_epic(v2_backlog):
    from taskmaster_v3 import create_task
    new_id = create_task({"title": "New", "epic": "e1", "priority": "low"},
                          backlog_path=v2_backlog)
    assert new_id == "e1-002"
    data = yaml.safe_load(v2_backlog.read_text())
    titles = [t["title"] for t in data["epics"][0]["tasks"]]
    assert "New" in titles


def test_create_task_unknown_epic_raises(v2_backlog):
    from taskmaster_v3 import create_task
    with pytest.raises(KeyError):
        create_task({"title": "x", "epic": "missing"}, backlog_path=v2_backlog)


def test_archive_task_moves_to_archived_status(v2_backlog):
    from taskmaster_v3 import archive_task
    archive_task("e1-001", backlog_path=v2_backlog)
    data = yaml.safe_load(v2_backlog.read_text())
    assert data["epics"][0]["tasks"][0]["status"] == "archived"
```

- [ ] **Step 2: Run (fails — functions don't exist)**

Run: `cd plugins/taskmaster && pytest tests/test_v3_task_writes.py -x -v`

- [ ] **Step 3: Implement primitives in `taskmaster_v3.py`**

Add at the bottom of `taskmaster_v3.py` (after the existing exports):

```python
# ── Edit-in-UI write primitives (v3-edit Phase A) ──────────────────

import contextlib
import filelock as _filelock_mod  # may not be installed; see fallback below
from datetime import datetime, timezone


@contextlib.contextmanager
def with_file_lock(path: Path):
    """Per-file mutex for write paths.

    Uses a `.lock` sidecar adjacent to the target file. Falls back to a
    threading-local lock if the `filelock` package isn't available — local
    use is single-process so this is acceptable; future cross-process
    safety lands when filelock becomes a hard dep.
    """
    try:
        from filelock import FileLock
        lock = FileLock(str(path) + ".lock", timeout=5)
        with lock:
            yield
    except ImportError:
        import threading
        lock = _threadlocal_locks.setdefault(str(path), threading.Lock())
        with lock:
            yield


_threadlocal_locks: dict[str, "threading.Lock"] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _find_task_in_yaml(data: dict, task_id: str) -> tuple[dict, dict] | None:
    """Return (epic_dict, task_dict) for a v2-nested layout, or None."""
    for epic in data.get("epics") or []:
        for t in epic.get("tasks") or []:
            if t.get("id") == task_id:
                return epic, t
    return None


def update_task(task_id: str, patch: dict, backlog_path: Path | None = None) -> dict:
    """Apply a partial update to a task. Returns the new task dict.

    - Auto-stamps `started` on first transition into `in-progress` (or any
      non-todo state from `todo`).
    - Auto-stamps `completed` on transition into `done`.
    - Never overwrites `started`/`completed` once set.
    """
    bp = backlog_path or _resolve_backlog_path()
    with with_file_lock(bp):
        data = yaml.safe_load(bp.read_text(encoding="utf-8")) or {}
        found = _find_task_in_yaml(data, task_id)
        if found is None:
            raise KeyError(f"task {task_id} not found")
        epic, task = found
        before_status = task.get("status")
        for k, v in patch.items():
            task[k] = v
        after_status = task.get("status")
        if after_status != before_status:
            if after_status == "in-progress" and not task.get("started"):
                task["started"] = _now_iso()
            if after_status == "done" and not task.get("completed"):
                task["completed"] = _now_iso()
        task["last_referenced"] = _now_iso()
        atomic_write(bp, yaml.safe_dump(data, sort_keys=False))
        return dict(task)


def create_task(payload: dict, backlog_path: Path | None = None) -> str:
    """Create a new task under the given epic. Returns assigned id."""
    bp = backlog_path or _resolve_backlog_path()
    epic_id = payload.get("epic")
    if not epic_id:
        raise ValueError("epic is required")
    with with_file_lock(bp):
        data = yaml.safe_load(bp.read_text(encoding="utf-8")) or {}
        epic = next((e for e in (data.get("epics") or []) if e.get("id") == epic_id), None)
        if epic is None:
            raise KeyError(f"epic {epic_id} not found")
        existing_ids = {t.get("id") for t in (epic.get("tasks") or [])}
        # Generate next id like e1-002.
        n = 1
        while f"{epic_id}-{n:03d}" in existing_ids:
            n += 1
        new_id = f"{epic_id}-{n:03d}"
        new_task = {
            "id": new_id,
            "title": payload.get("title", ""),
            "status": payload.get("status", "todo"),
            "priority": payload.get("priority", "medium"),
            "created": _now_iso(),
            "last_referenced": _now_iso(),
        }
        # Pass through other supplied fields (phase, anchors, depends_on, etc).
        for k, v in payload.items():
            if k not in ("epic", "id"):
                new_task[k] = v
        epic.setdefault("tasks", []).append(new_task)
        atomic_write(bp, yaml.safe_dump(data, sort_keys=False))
        return new_id


def archive_task(task_id: str, backlog_path: Path | None = None) -> None:
    """Soft-delete: set status to 'archived'. The existing
    backlog_archive_task MCP tool already does this for v2 backlogs;
    we mirror the behavior here so HTTP shares the code path."""
    update_task(task_id, {"status": "archived"}, backlog_path=backlog_path)


def _resolve_backlog_path() -> Path:
    """Lazy import of backlog_server's resolver to avoid circular import."""
    from backlog_server import _backlog_path
    return _backlog_path()
```

(If `taskmaster_v3.py` doesn't already import `yaml` at module top, add `import yaml`. Same for `Path`. Same for `atomic_write` — check existing imports first; the function is referenced elsewhere in this file per the spec.)

- [ ] **Step 4: Run primitives tests**

Run: `cd plugins/taskmaster && pytest tests/test_v3_task_writes.py -x -v`
Expected: PASS — 8/8

- [ ] **Step 5: Test HTTP write endpoints**

```python
# plugins/taskmaster/tests/test_server_task_write.py
"""HTTP tests for /api/tasks PATCH/PUT/POST."""
import json
import threading
import time
import urllib.request
import urllib.error
import pytest
import yaml


@pytest.fixture
def server_with_backlog(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    bp = tmp_path / "backlog.yaml"
    bp.write_text(yaml.safe_dump({
        "meta": {"project": "test"},
        "epics": [{"id": "e1", "name": "E1", "status": "active",
                   "tasks": [{"id": "e1-001", "title": "X", "status": "todo",
                              "priority": "medium"}]}],
        "phases": [],
    }))
    from backlog_server import _make_server
    server, port = _make_server(host="127.0.0.1", port=0)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    base = f"http://127.0.0.1:{port}"
    for _ in range(20):
        try:
            urllib.request.urlopen(f"{base}/api/identity", timeout=0.5).read()
            break
        except Exception:
            time.sleep(0.1)
    yield base
    server.shutdown()


def _request(method, url, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                  headers={"Content-Type": "application/json"})
    try:
        return urllib.request.urlopen(req, timeout=2)
    except urllib.error.HTTPError as e:
        return e


def test_patch_task_updates_field(server_with_backlog):
    base = server_with_backlog
    resp = _request("PATCH", f"{base}/api/tasks/e1-001", {"title": "Renamed"})
    assert resp.status == 200
    body = json.loads(resp.read())
    assert body["task"]["title"] == "Renamed"


def test_patch_unknown_id_returns_404(server_with_backlog):
    base = server_with_backlog
    resp = _request("PATCH", f"{base}/api/tasks/nope", {"title": "x"})
    assert resp.status == 404


def test_patch_invalid_json_returns_400(server_with_backlog):
    base = server_with_backlog
    req = urllib.request.Request(f"{base}/api/tasks/e1-001",
                                  data=b"not-json", method="PATCH",
                                  headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=2)
        assert False, "expected 400"
    except urllib.error.HTTPError as e:
        assert e.code == 400


def test_post_creates_task(server_with_backlog):
    base = server_with_backlog
    resp = _request("POST", f"{base}/api/tasks",
                     {"epic": "e1", "title": "New", "priority": "high"})
    assert resp.status == 201
    body = json.loads(resp.read())
    assert body["task"]["id"] == "e1-002"
    assert body["task"]["title"] == "New"


def test_post_archive_sets_status(server_with_backlog):
    base = server_with_backlog
    resp = _request("POST", f"{base}/api/tasks/e1-001/archive", {})
    assert resp.status == 200
    # Verify
    detail = urllib.request.urlopen(f"{base}/api/task/e1-001").read()
    assert json.loads(detail)["status"] == "archived"
```

- [ ] **Step 6: Run (fails — endpoints don't exist)**

- [ ] **Step 7: Implement HTTP handlers**

In `backlog_server.py`, add `do_PATCH` after `do_PUT` (search for `def do_PUT(self):` to find location):

```python
    def do_PATCH(self):
        import json
        import re
        if m := re.fullmatch(r"/api/tasks/([A-Za-z0-9_\-]+)", self.path):
            task_id = m.group(1)
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode("utf-8") if length else ""
            try:
                patch = json.loads(raw)
            except Exception as e:
                self._send_json(400, {"ok": False, "error": f"invalid JSON: {e}"})
                return
            if not isinstance(patch, dict):
                self._send_json(400, {"ok": False, "error": "patch must be object"})
                return
            try:
                from taskmaster_v3 import update_task
                task = update_task(task_id, patch)
                self._send_json(200, {"ok": True, "task": task})
            except KeyError as e:
                self._send_json(404, {"ok": False, "error": str(e)})
            except Exception as e:
                self._send_json(500, {"ok": False, "error": str(e)})
            return

        self.send_error(404)
```

In the existing `do_POST`, add a new branch (before the existing fallback):

```python
        # Edit-in-UI: create task, archive task
        import re
        if self.path == "/api/tasks":
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode("utf-8") if length else ""
            try:
                payload = json.loads(raw)
            except Exception as e:
                self._send_json(400, {"ok": False, "error": f"invalid JSON: {e}"})
                return
            try:
                from taskmaster_v3 import create_task, _resolve_backlog_path
                new_id = create_task(payload)
                # Look up the new task to return.
                from backlog_server import _load_task_full
                task = _load_task_full(new_id) or {"id": new_id}
                self._send_json(201, {"ok": True, "task": task})
            except (KeyError, ValueError) as e:
                self._send_json(400, {"ok": False, "error": str(e)})
            except Exception as e:
                self._send_json(500, {"ok": False, "error": str(e)})
            return

        if m := re.fullmatch(r"/api/tasks/([A-Za-z0-9_\-]+)/archive", self.path):
            task_id = m.group(1)
            try:
                from taskmaster_v3 import archive_task
                archive_task(task_id)
                self._send_json(200, {"ok": True})
            except KeyError as e:
                self._send_json(404, {"ok": False, "error": str(e)})
            except Exception as e:
                self._send_json(500, {"ok": False, "error": str(e)})
            return
```

In `do_PUT`, add a branch after the existing recap branch:

```python
        if m := re.fullmatch(r"/api/tasks/([A-Za-z0-9_\-]+)", self.path):
            task_id = m.group(1)
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode("utf-8") if length else ""
            try:
                full = json.loads(raw)
            except Exception as e:
                self._send_json(400, {"ok": False, "error": f"invalid JSON: {e}"})
                return
            if not isinstance(full, dict):
                self._send_json(400, {"ok": False, "error": "body must be object"})
                return
            try:
                from taskmaster_v3 import update_task
                task = update_task(task_id, full)
                self._send_json(200, {"ok": True, "task": task})
            except KeyError as e:
                self._send_json(404, {"ok": False, "error": str(e)})
            return
```

(`PUT` and `PATCH` both call `update_task`. Difference for tasks is purely client semantics — PUT carries the full draft, PATCH carries one field. Server-side they're equivalent for v2 nested storage. Once the schema-version-aware writer lands, PUT will replace the per-task .md body wholesale while PATCH merges fields; for Phase A both behave the same.)

- [ ] **Step 8: Wire up viewer api.js**

Modify `viewer/js/api.js`. Find the `export const api = { ... }` block and add the new methods alongside the existing ones:

```js
  patchTask:    (id, patch) => http('PATCH', `/api/tasks/${encodeURIComponent(id)}`, patch),
  putTask:      (id, full)  => http('PUT',   `/api/tasks/${encodeURIComponent(id)}`, full),
  createTask:   (payload)   => http('POST',  '/api/tasks', payload),
  archiveTask:  (id)        => http('POST',  `/api/tasks/${encodeURIComponent(id)}/archive`, {}),
```

If `http()` doesn't already accept a body for PATCH/PUT/POST, check its existing implementation (top of api.js) — if it does (which the existing `savePrefs` PUT path implies) you're done. If it doesn't, extend it:

```js
async function http(method, path, body) {
  const init = {
    method,
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : {},
    body: body !== undefined ? JSON.stringify(body) : undefined,
  };
  const resp = await fetch(BASE + path, init);
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`${resp.status} ${resp.statusText}: ${text}`);
  }
  return resp.json();
}
```

- [ ] **Step 9: Run all tests**

```bash
cd plugins/taskmaster && pytest tests/test_v3_task_writes.py tests/test_server_task_write.py -x -v
# Expected: PASS — 13/13
```

- [ ] **Step 10: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py \
        plugins/taskmaster/backlog_server.py \
        plugins/taskmaster/viewer/js/api.js \
        plugins/taskmaster/tests/test_v3_task_writes.py \
        plugins/taskmaster/tests/test_server_task_write.py
git commit -m "feat(taskmaster): task write API (PATCH/PUT/POST/archive) + v3 primitives (v3-edit-004)"
```

---

## Task 10: ETag/If-Match concurrency

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py` — add `compute_etag`
- Modify: `plugins/taskmaster/backlog_server.py` — emit ETag on GET, validate If-Match on PATCH/PUT/POST-archive, return 409 with current state on mismatch
- Modify: `plugins/taskmaster/viewer/js/api.js` — capture/send ETags
- Create: `plugins/taskmaster/tests/test_server_etag.py`

ETag is computed as `sha1(file_mtime + file_sha1)[:16]` — fast, stable, changes whenever the file changes. Server emits it on `GET /api/task/<id>` and `GET /api/backlog`. Client stores it in `store.js` keyed by `task:<id>` and sends `If-Match` on PATCH/PUT/POST-archive. Mismatch → 409 with `{ ok: false, error: "stale", current_etag, current: <full task> }`.

- [ ] **Step 1: Test ETag computation**

```python
# plugins/taskmaster/tests/test_server_etag.py
import json
import threading
import time
import urllib.request
import urllib.error
import pytest
import yaml


@pytest.fixture
def server_etag(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    bp = tmp_path / "backlog.yaml"
    bp.write_text(yaml.safe_dump({
        "meta": {"project": "test"},
        "epics": [{"id": "e1", "name": "E1", "status": "active",
                   "tasks": [{"id": "e1-001", "title": "X", "status": "todo",
                              "priority": "medium"}]}],
        "phases": [],
    }))
    from backlog_server import _make_server
    server, port = _make_server(host="127.0.0.1", port=0)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    base = f"http://127.0.0.1:{port}"
    for _ in range(20):
        try:
            urllib.request.urlopen(f"{base}/api/identity", timeout=0.5).read()
            break
        except Exception:
            time.sleep(0.1)
    yield base
    server.shutdown()


def _request(method, url, body=None, headers=None):
    h = headers or {}
    if body is not None:
        h["Content-Type"] = "application/json"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        return urllib.request.urlopen(req, timeout=2)
    except urllib.error.HTTPError as e:
        return e


def test_get_task_emits_etag(server_etag):
    resp = urllib.request.urlopen(f"{server_etag}/api/task/e1-001", timeout=2)
    etag = resp.headers.get("ETag")
    assert etag, "ETag header missing"
    assert len(etag) >= 8


def test_patch_with_correct_etag_succeeds(server_etag):
    get_resp = urllib.request.urlopen(f"{server_etag}/api/task/e1-001", timeout=2)
    etag = get_resp.headers.get("ETag")
    resp = _request("PATCH", f"{server_etag}/api/tasks/e1-001",
                    {"title": "Renamed"}, headers={"If-Match": etag})
    assert resp.status == 200


def test_patch_with_stale_etag_returns_409(server_etag):
    # Read once to capture an etag, then mutate via a separate PATCH
    # without If-Match, then try PATCH with the OLD etag.
    get_resp = urllib.request.urlopen(f"{server_etag}/api/task/e1-001", timeout=2)
    old_etag = get_resp.headers.get("ETag")
    # Bypass If-Match by issuing without the header (server allows missing
    # If-Match for backwards compat — see implementation note in Step 3).
    # To force a real change, call update_task directly:
    from taskmaster_v3 import update_task
    update_task("e1-001", {"title": "Changed by other"})
    resp = _request("PATCH", f"{server_etag}/api/tasks/e1-001",
                    {"title": "My change"}, headers={"If-Match": old_etag})
    assert resp.status == 409
    body = json.loads(resp.read())
    assert body["ok"] is False
    assert body.get("error") == "stale"
    assert "current" in body
    assert "current_etag" in body


def test_patch_without_if_match_proceeds(server_etag):
    """For backward compat with non-edit-aware clients (e.g. existing MCP
    tools that don't speak ETags), PATCH without If-Match goes through.
    The viewer always sends If-Match; this only matters for legacy callers."""
    resp = _request("PATCH", f"{server_etag}/api/tasks/e1-001",
                    {"title": "no etag"})
    assert resp.status == 200
```

- [ ] **Step 2: Run (fails)**

- [ ] **Step 3: Implement `compute_etag`**

Append to `taskmaster_v3.py`:

```python
import hashlib


def compute_etag(path: Path) -> str:
    """Stable, cheap ETag derived from file mtime + content hash.

    Returns an 16-hex-char string suitable for HTTP ETag headers.
    """
    if not path.exists():
        return ""
    st = path.stat()
    h = hashlib.sha1()
    h.update(str(st.st_mtime_ns).encode())
    # Also hash content so two writes with identical content (e.g. same byte
    # body) collapse to the same etag — desirable for cache stability.
    h.update(path.read_bytes())
    return h.hexdigest()[:16]
```

- [ ] **Step 4: Emit ETag from server GETs**

In `backlog_server.py`, find the `_send_json` helper. We need an option to attach an ETag header:

Find the existing `_send_json(self, status, data)` method and replace with:

```python
    def _send_json(self, status, data, etag=None):
        import json
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if etag:
            self.send_header("ETag", f'"{etag}"')
        self.end_headers()
        self.wfile.write(body)
```

Now in the `/api/task/<id>` GET branch (in `do_GET`, search for `if "/" not in rest and rest:` near line 4470), add ETag emission:

```python
            if "/" not in rest and rest:
                full = _load_task_full(rest)
                if full is None:
                    self._send_json(404, {"ok": False, "error": f"task {rest} not found"})
                    return
                from taskmaster_v3 import compute_etag
                etag = compute_etag(_backlog_path())
                self._send_json(200, full, etag=etag)
                return
```

Same treatment for `/api/backlog` (`_serve_json`):

```python
    def _serve_json(self) -> None:
        try:
            data = yaml.safe_load(_backlog_path().read_text(encoding="utf-8"))
            data.setdefault("meta", {})["_version"] = VERSION
            if not isinstance(data.get("tasks"), list):
                data["tasks"] = [
                    {**t, "epic": t.get("epic", e.get("id"))}
                    for e in (data.get("epics") or [])
                    for t in (e.get("tasks") or [])
                ]
            from taskmaster_v3 import compute_etag
            etag = compute_etag(_backlog_path())
            self._send_json(200, data, etag=etag)
        except Exception as e:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))
```

- [ ] **Step 5: Validate If-Match on writes**

In the `do_PATCH` branch (just added in Task 9), wrap the write with an If-Match check:

```python
    def do_PATCH(self):
        import json
        import re
        from taskmaster_v3 import compute_etag, update_task
        if m := re.fullmatch(r"/api/tasks/([A-Za-z0-9_\-]+)", self.path):
            task_id = m.group(1)
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode("utf-8") if length else ""
            try:
                patch = json.loads(raw)
            except Exception as e:
                self._send_json(400, {"ok": False, "error": f"invalid JSON: {e}"})
                return
            if not isinstance(patch, dict):
                self._send_json(400, {"ok": False, "error": "patch must be object"})
                return
            # If-Match check
            if_match = self.headers.get("If-Match")
            if if_match:
                if_match = if_match.strip('"')
                current_etag = compute_etag(_backlog_path())
                if if_match != current_etag:
                    from backlog_server import _load_task_full
                    current = _load_task_full(task_id)
                    self._send_json(409, {
                        "ok": False, "error": "stale",
                        "current_etag": current_etag,
                        "current": current,
                    })
                    return
            try:
                task = update_task(task_id, patch)
                new_etag = compute_etag(_backlog_path())
                self._send_json(200, {"ok": True, "task": task}, etag=new_etag)
            except KeyError as e:
                self._send_json(404, {"ok": False, "error": str(e)})
            except Exception as e:
                self._send_json(500, {"ok": False, "error": str(e)})
            return
        self.send_error(404)
```

Apply the same If-Match wrap to:
- The PUT branch in `do_PUT` (`/api/tasks/<id>`)
- The POST `/api/tasks/<id>/archive` branch in `do_POST`

For brevity the plan shows one occurrence; copy the If-Match block (8 lines from `if_match = self.headers.get(...)` through the 409 emission) to each.

- [ ] **Step 6: Wire api.js to capture + send ETags**

Modify `viewer/js/store.js` to track etags. Find the `state` object near the top:

```js
const state = {
  identity: null, prefs: null, backlog: null, autoState: null,
  etags: {},  // ← add this. keyed by `task:<id>` or `backlog`.
};
```

Add a setter/getter:

```js
export const store = {
  // … existing exports …
  setEtag: (key, etag) => { state.etags[key] = etag; },
  getEtag: (key) => state.etags[key] || null,
};
```

Modify `viewer/js/api.js`. Update the response handler to capture ETag:

```js
async function http(method, path, body) {
  const init = {
    method,
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : {},
    body: body !== undefined ? JSON.stringify(body) : undefined,
  };
  // Attach If-Match for write methods if we have an etag for this resource.
  if (method === 'PATCH' || method === 'PUT') {
    const m = path.match(/^\/api\/tasks\/([^/]+)/);
    if (m) {
      const { store } = await import('./store.js');
      const et = store.getEtag(`task:${decodeURIComponent(m[1])}`);
      if (et) init.headers['If-Match'] = et;
    }
  }
  const resp = await fetch(BASE + path, init);
  // Capture returned ETag for next time.
  const et = resp.headers.get('ETag');
  if (et) {
    const { store } = await import('./store.js');
    const m1 = path.match(/^\/api\/task\/([^/]+)$/);  // GET single task
    const m2 = path.match(/^\/api\/tasks\/([^/]+)/);   // PATCH/PUT
    const id = (m1 || m2)?.[1];
    if (id) store.setEtag(`task:${decodeURIComponent(id)}`, et.replace(/^"|"$/g, ''));
    if (path === '/api/backlog') store.setEtag('backlog', et.replace(/^"|"$/g, ''));
  }
  if (resp.status === 409) {
    const j = await resp.json();
    const err = new Error('stale');
    err.code = 409;
    err.current = j.current;
    err.current_etag = j.current_etag;
    throw err;
  }
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`${resp.status} ${resp.statusText}: ${text}`);
  }
  return resp.json();
}
```

- [ ] **Step 7: Run + commit**

```bash
cd plugins/taskmaster && pytest tests/test_server_etag.py -x -v
# Expected: PASS — 4/4
git add plugins/taskmaster/taskmaster_v3.py \
        plugins/taskmaster/backlog_server.py \
        plugins/taskmaster/viewer/js/api.js \
        plugins/taskmaster/viewer/js/store.js \
        plugins/taskmaster/tests/test_server_etag.py
git commit -m "feat(taskmaster): ETag/If-Match concurrency for task writes (v3-edit-005)"
```

---

## Task 11: Conflict banner + Show-diff component

**Files:**
- Create: `viewer/js/components/edit/conflict-banner.js`
- Create: `viewer/css/components/conflict-banner.css`
- Create: `viewer/tests/unit/conflict-banner.test.js`
- Modify: `viewer/index.html` (already mounted `#conflict-banner-host` in Task 7)
- Modify: `viewer/js/components/edit/inline-field.js` — surface 409s by calling `showConflict(...)`

When `inline-field.js` sees a 409 from `onSave`, it calls `showConflict({ entityKind, entityId, localValue, currentValue, currentEtag, onResolve })`. The banner mounts into `#conflict-banner-host`, shows the diff for THIS field (just this one — the inline path only patches one field at a time), and offers two buttons: **Keep mine** (re-PATCH with the new etag, overwriting) and **Use server**.

For modal flow (multiple fields dirty at once, only relevant once Task 13 wires the task modal to PUT), the banner shows a multi-row diff of all changed fields with per-field choice. That code path is included here even though Task 13 is what triggers it — the banner is the same component.

Public API:
```js
showFieldConflict({
  entityKind, entityId, fieldKey, fieldLabel,
  localValue, currentValue, currentEtag,
  onKeepMine: async () => {},
  onUseServer: () => {},
});
showFullConflict({
  entityKind, entityId,
  localDraft, currentValue, currentEtag,
  fieldDecisions, // { [key]: 'mine' | 'server' }
  onResolve: async (mergedDraft) => {},
});
```

- [ ] **Step 1: Test**

```js
// viewer/tests/unit/conflict-banner.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';

const dom = new JSDOM('<!doctype html><html><body><div id="conflict-banner-host"></div></body></html>');
globalThis.document = dom.window.document;
globalThis.window = dom.window;

const { showFieldConflict } = await import('../../js/components/edit/conflict-banner.js');

test('field conflict shows local + server values', () => {
  const close = showFieldConflict({
    entityKind: 'task', entityId: 'e1-001',
    fieldKey: 'title', fieldLabel: 'Title',
    localValue: 'My version', currentValue: 'Server version',
    currentEtag: 'abc', onKeepMine: async () => {}, onUseServer: () => {},
  });
  const banner = document.querySelector('.cb-banner');
  assert.ok(banner);
  assert.match(banner.textContent, /My version/);
  assert.match(banner.textContent, /Server version/);
  close();
  assert.equal(document.querySelector('.cb-banner'), null);
});

test('Keep mine button calls onKeepMine and dismisses', async () => {
  let called = false;
  showFieldConflict({
    entityKind: 'task', entityId: 'e1-001',
    fieldKey: 'title', fieldLabel: 'Title',
    localValue: 'a', currentValue: 'b', currentEtag: 'x',
    onKeepMine: async () => { called = true; },
    onUseServer: () => {},
  });
  document.querySelector('.cb-keep-mine').click();
  await new Promise(r => setTimeout(r, 5));
  assert.equal(called, true);
  assert.equal(document.querySelector('.cb-banner'), null);
});

test('Use server button calls onUseServer and dismisses', () => {
  let called = false;
  showFieldConflict({
    entityKind: 'task', entityId: 'e1-001',
    fieldKey: 'title', fieldLabel: 'Title',
    localValue: 'a', currentValue: 'b', currentEtag: 'x',
    onKeepMine: async () => {},
    onUseServer: () => { called = true; },
  });
  document.querySelector('.cb-use-server').click();
  assert.equal(called, true);
  assert.equal(document.querySelector('.cb-banner'), null);
});
```

- [ ] **Step 2: Run (fails)**

- [ ] **Step 3: Implement**

```js
// viewer/js/components/edit/conflict-banner.js
// Surfaces 409 conflicts. Two flavors:
//   showFieldConflict — single-field, used by inline-field.js
//   showFullConflict  — multi-field diff, used by entity-modal.js

import { h } from '../../util/h.js';

const HOST_ID = 'conflict-banner-host';

function getHost() {
  const host = document.getElementById(HOST_ID);
  if (!host) throw new Error(`#${HOST_ID} not found`);
  return host;
}

function dismiss(banner) {
  banner.remove();
}

export function showFieldConflict({
  entityKind, entityId, fieldKey, fieldLabel,
  localValue, currentValue, currentEtag,
  onKeepMine, onUseServer,
}) {
  const host = getHost();
  // Replace any existing banner — only one at a time.
  host.replaceChildren();
  const banner = h('div', { class: 'cb-banner cb-field' }, [
    h('div', { class: 'cb-headline' },
      `${entityKind} ${entityId} — "${fieldLabel}" updated by another writer`),
    h('div', { class: 'cb-diff' }, [
      h('div', { class: 'cb-row' }, [
        h('span', { class: 'cb-label' }, 'You: '),
        h('span', { class: 'cb-val cb-val-mine' }, _stringify(localValue)),
      ]),
      h('div', { class: 'cb-row' }, [
        h('span', { class: 'cb-label' }, 'Server: '),
        h('span', { class: 'cb-val cb-val-server' }, _stringify(currentValue)),
      ]),
    ]),
    h('div', { class: 'cb-actions' }, [
      h('button', { type: 'button', class: 'cb-use-server',
                    on: { click: () => { onUseServer(); dismiss(banner); } } },
        'Use server'),
      h('button', { type: 'button', class: 'cb-keep-mine',
                    on: { click: async () => { await onKeepMine(); dismiss(banner); } } },
        'Keep mine'),
    ]),
  ]);
  host.appendChild(banner);
  return () => dismiss(banner);
}

export function showFullConflict({
  entityKind, entityId, localDraft, currentValue, currentEtag, onResolve,
}) {
  const host = getHost();
  host.replaceChildren();
  // Compute per-field diffs.
  const allKeys = new Set([...Object.keys(localDraft || {}), ...Object.keys(currentValue || {})]);
  const decisions = {};
  for (const k of allKeys) {
    if (JSON.stringify(localDraft?.[k] ?? null) === JSON.stringify(currentValue?.[k] ?? null)) continue;
    decisions[k] = 'mine'; // default to keeping local
  }
  const rows = h('div', { class: 'cb-rows' });
  for (const k of Object.keys(decisions)) {
    const row = h('div', { class: 'cb-multi-row' }, [
      h('div', { class: 'cb-key' }, k),
      h('div', { class: 'cb-val cb-val-mine' }, _stringify(localDraft[k])),
      h('div', { class: 'cb-val cb-val-server' }, _stringify(currentValue[k])),
      h('div', { class: 'cb-multi-actions' }, [
        _radio(`cb-d-${k}`, 'mine', 'Keep mine', decisions[k] === 'mine',
               () => { decisions[k] = 'mine'; }),
        _radio(`cb-d-${k}`, 'server', 'Use server', decisions[k] === 'server',
               () => { decisions[k] = 'server'; }),
      ]),
    ]);
    rows.appendChild(row);
  }
  const banner = h('div', { class: 'cb-banner cb-full' }, [
    h('div', { class: 'cb-headline' },
      `${entityKind} ${entityId} updated by another writer — pick fields to keep`),
    rows,
    h('div', { class: 'cb-actions' }, [
      h('button', { type: 'button', class: 'cb-resolve',
                    on: { click: async () => {
                      const merged = { ...currentValue };
                      for (const [k, choice] of Object.entries(decisions)) {
                        merged[k] = choice === 'mine' ? localDraft[k] : currentValue[k];
                      }
                      await onResolve(merged);
                      dismiss(banner);
                    } } }, 'Apply choices'),
    ]),
  ]);
  host.appendChild(banner);
  return () => dismiss(banner);
}

function _stringify(v) {
  if (v == null) return '—';
  if (Array.isArray(v)) return v.join(', ');
  if (typeof v === 'object') return JSON.stringify(v);
  return String(v);
}

function _radio(name, value, label, checked, onChange) {
  const id = `${name}-${value}`;
  const lbl = h('label', { for: id, class: 'cb-radio' }, [
    h('input', { type: 'radio', name, id, value }),
    h('span', {}, label),
  ]);
  const input = lbl.querySelector('input');
  input.checked = checked;
  input.addEventListener('change', () => { if (input.checked) onChange(); });
  return lbl;
}
```

- [ ] **Step 4: CSS**

```css
/* viewer/css/components/conflict-banner.css */
.cb-banner {
  position: fixed; top: 0; left: 0; right: 0; z-index: 90;
  background: color-mix(in oklch, var(--amber) 15%, var(--bg-deep));
  border-bottom: 1px solid var(--amber);
  color: var(--ink);
  padding: 10px 16px;
  font-size: var(--text-sm);
}
.cb-headline { font-weight: 600; margin-bottom: 6px; color: var(--amber); }
.cb-diff, .cb-rows { display: flex; flex-direction: column; gap: 4px; margin-bottom: 8px; }
.cb-row, .cb-multi-row { display: flex; gap: 8px; align-items: baseline; }
.cb-label, .cb-key { color: var(--ink-3); min-width: 60px; }
.cb-val { color: var(--ink); overflow-wrap: anywhere; }
.cb-val-mine   { background: color-mix(in oklch, var(--green) 20%, transparent); padding: 1px 6px; border-radius: 3px; }
.cb-val-server { background: color-mix(in oklch, var(--red)   20%, transparent); padding: 1px 6px; border-radius: 3px; }
.cb-multi-actions { display: flex; gap: 12px; margin-left: auto; }
.cb-radio { display: inline-flex; gap: 4px; align-items: center; cursor: pointer; }
.cb-actions { display: flex; gap: 8px; justify-content: flex-end; }
.cb-actions button {
  font: inherit; padding: 4px 12px; border-radius: 3px; cursor: pointer;
  border: 1px solid var(--border);
}
.cb-keep-mine, .cb-resolve { background: var(--accent); color: white; border-color: var(--accent); }
.cb-use-server { background: transparent; color: var(--ink-2); }
```

Add `<link rel="stylesheet" href="/static/v3/css/components/conflict-banner.css">` to `viewer/index.html`.

- [ ] **Step 5: Wire `inline-field.js` to use it**

Modify `viewer/js/components/edit/inline-field.js`. In `flushSave()`, replace the `setStatus('error', result.error)` path with conflict-aware handling. Update the catch block to detect `e.code === 409`:

```js
    async function flushSave() {
      if (saveTimer) { clearTimeout(saveTimer); saveTimer = null; }
      const v = pendingValue;
      if (sameValue(v, currentEntity[fieldKey])) return;
      inFlight = true;
      setStatus('saving');
      try {
        const result = await onSave(v);
        if (result && result.error) {
          setStatus('error', result.error);
          return;
        }
        currentEntity[fieldKey] = v;
        setStatus('ok');
        setTimeout(() => setStatus(''), 800);
      } catch (e) {
        if (e && e.code === 409) {
          // Stale write — surface conflict banner.
          const { showFieldConflict } = await import('./conflict-banner.js');
          showFieldConflict({
            entityKind: schema.entity || 'entity',
            entityId: currentEntity.id || '?',
            fieldKey, fieldLabel: fieldSpec.label || fieldKey,
            localValue: v,
            currentValue: e.current?.[fieldKey],
            currentEtag: e.current_etag,
            onKeepMine: async () => {
              // Update local etag and re-PATCH.
              const { store } = await import('../../store.js');
              store.setEtag(`task:${currentEntity.id}`, e.current_etag);
              try { await onSave(v); } catch (e2) { setStatus('error', e2.message); return; }
              currentEntity[fieldKey] = v;
              paint();
            },
            onUseServer: () => {
              currentEntity[fieldKey] = e.current?.[fieldKey];
              const { store } = await import('../../store.js');
              store.setEtag(`task:${currentEntity.id}`, e.current_etag);
              paint();
            },
          });
          setStatus('error', 'stale — see banner');
          return;
        }
        setStatus('error', e.message || String(e));
      } finally {
        inFlight = false;
      }
    }
```

(Note: dynamic `import('./conflict-banner.js')` is fine; the modal/bundler-less ESM will resolve it on demand.)

- [ ] **Step 6: Run + commit**

```bash
cd plugins/taskmaster/viewer && npm run test:unit -- tests/unit/conflict-banner.test.js
# Expected: PASS — 3/3
git add plugins/taskmaster/viewer/js/components/edit/conflict-banner.js \
        plugins/taskmaster/viewer/css/components/conflict-banner.css \
        plugins/taskmaster/viewer/index.html \
        plugins/taskmaster/viewer/js/components/edit/inline-field.js \
        plugins/taskmaster/viewer/tests/unit/conflict-banner.test.js
git commit -m "feat(taskmaster): conflict banner + inline-field 409 handling (v3-edit-006)"
```

---

## Task 12: Task form composition

**Files:**
- Create: `viewer/js/components/edit/forms/task-form.js`
- Create: `viewer/tests/unit/task-form.test.js`

`task-form.js` is the per-entity composition (per spec §Architecture). It exports `taskSchema(deps)` — a function that returns the schema given runtime deps (the backlog accessor, the list of valid epics/phases). Pure data + a few cross-field rules.

The schema covers all editable Task fields per spec §Per-entity field maps.

- [ ] **Step 1: Test**

```js
// viewer/tests/unit/task-form.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';

const dom = new JSDOM('<!doctype html><html><body></body></html>');
globalThis.document = dom.window.document;
globalThis.window = dom.window;

const { taskSchema } = await import('../../js/components/edit/forms/task-form.js');
const { runValidation } = await import('../../js/components/edit/schema.js');

const FAKE = () => ({
  epics: [{ id: 'v3-edit', name: 'V3 Edit' }],
  phases: [{ id: 'ship-v3', name: 'Ship V3' }],
  tasks: [{ id: 'v3-edit-001', title: 'Renderers', status: 'todo' }],
});

test('schema includes all editable task fields', () => {
  const s = taskSchema({ getBacklog: FAKE });
  const keys = s.fields.map(f => f.key);
  for (const k of ['title', 'status', 'priority', 'epic', 'phase', 'estimate',
                    'depends_on', 'docs', 'anchors', 'description', 'notes',
                    'specification', 'plan', 'review_instructions']) {
    assert.ok(keys.includes(k), `missing ${k}`);
  }
});

test('systemManaged covers id/created/started/completed/etc', () => {
  const s = taskSchema({ getBacklog: FAKE });
  for (const k of ['id', 'created', 'started', 'completed', 'last_referenced',
                    'activity', 'spec_review', 'auto_mode', 'locked_by']) {
    assert.ok(s.systemManaged.includes(k), `missing systemManaged: ${k}`);
  }
});

test('valid task passes validation', () => {
  const s = taskSchema({ getBacklog: FAKE });
  const r = runValidation({ title: 'New task', status: 'todo', priority: 'medium', epic: 'v3-edit' }, s);
  assert.equal(r.valid, true);
});

test('invalid epic is flagged', () => {
  const s = taskSchema({ getBacklog: FAKE });
  const r = runValidation({ title: 'x', status: 'todo', priority: 'medium', epic: 'bogus' }, s);
  assert.equal(r.valid, false);
  assert.match(r.errors.epic, /unknown epic/);
});

test('depends_on with self id is rejected', () => {
  const s = taskSchema({ getBacklog: FAKE });
  const r = runValidation({
    id: 'v3-edit-001', title: 'x', status: 'todo', priority: 'medium',
    epic: 'v3-edit', depends_on: ['v3-edit-001'],
  }, s);
  assert.equal(r.valid, false);
  assert.match(r.errors.depends_on, /cannot depend on itself/);
});

test('priority must be in enum', () => {
  const s = taskSchema({ getBacklog: FAKE });
  const r = runValidation({ title: 'x', status: 'todo', priority: 'urgent', epic: 'v3-edit' }, s);
  assert.equal(r.valid, false);
  assert.equal(r.errors.priority, 'invalid value');
});
```

- [ ] **Step 2: Run (fails)**

- [ ] **Step 3: Implement**

```js
// viewer/js/components/edit/forms/task-form.js
// Schema for the Task entity. Drives both the task creation/edit modal
// and the inline-field wrappers on Task Detail.
//
// `getBacklog: () => backlog` is required so enum options for epic/phase
// can resolve dynamically against the live backlog.

import { TextField }     from '../fields/text-field.js';
import { MdField }       from '../fields/md-field.js';
import { EnumSelect }    from '../fields/enum-select.js';
import { NumberField }   from '../fields/number-field.js';
import { ChipInput }     from '../fields/chip-input.js';
import { RelationPicker } from '../fields/relation-picker.js';

const STATUS_OPTIONS = [
  { value: 'todo',        label: 'Todo' },
  { value: 'in-progress', label: 'In Progress' },
  { value: 'in-review',   label: 'In Review' },
  { value: 'done',        label: 'Done' },
  { value: 'blocked',     label: 'Blocked' },
  { value: 'archived',    label: 'Archived' },
];

const PRIORITY_OPTIONS = [
  { value: 'critical', label: 'Critical' },
  { value: 'high',     label: 'High' },
  { value: 'medium',   label: 'Medium' },
  { value: 'low',      label: 'Low' },
];

export function taskSchema({ getBacklog }) {
  const epicOptions = () => (getBacklog()?.epics || []).map(e => ({ value: e.id, label: e.id }));
  const phaseOptions = () => [{ value: '', label: '—' }].concat(
    (getBacklog()?.phases || []).map(p => ({ value: p.id, label: p.id })));

  return {
    entity: 'task',
    label: 'Task',
    fields: [
      { key: 'title',    label: 'Title',    renderer: TextField,
        required: true, maxLength: 140 },
      { key: 'status',   label: 'Status',   renderer: EnumSelect,
        required: true, options: STATUS_OPTIONS },
      { key: 'priority', label: 'Priority', renderer: EnumSelect,
        required: true, options: PRIORITY_OPTIONS },
      { key: 'epic',     label: 'Epic',     renderer: EnumSelect,
        required: true,
        // Dynamic options — resolved at validation/edit time.
        get options() { return epicOptions(); },
        validate(value, { required }) {
          if (required && !value) return 'required';
          if (value && !(getBacklog()?.epics || []).some(e => e.id === value)) return 'unknown epic';
          return null;
        }},
      { key: 'phase',    label: 'Phase',    renderer: EnumSelect,
        get options() { return phaseOptions(); },
        validate(value) {
          if (!value) return null;
          if (!(getBacklog()?.phases || []).some(p => p.id === value)) return 'unknown phase';
          return null;
        }},
      { key: 'estimate', label: 'Estimate (S/M/L or "Nd")', renderer: TextField,
        maxLength: 16 },
      { key: 'stage',    label: 'Stage',    renderer: NumberField, min: 0 },
      { key: 'sub_repo', label: 'Sub-repo', renderer: TextField, maxLength: 64 },
      { key: 'branch',   label: 'Branch',   renderer: TextField, maxLength: 200 },
      { key: 'worktree', label: 'Worktree', renderer: TextField, maxLength: 200 },
      { key: 'release',  label: 'Release',  renderer: TextField, maxLength: 32 },
      { key: 'depends_on', label: 'Depends on', renderer: RelationPicker,
        kind: 'tasks', getBacklog,
        validate(value, spec) {
          // Self-dep guard. Cycle detection is server-side via backlog_validate.
          if (!Array.isArray(value)) return null;
          // The owning task's id is passed via crossField (see below).
          return null;
        }},
      { key: 'docs',     label: 'Docs',     renderer: ChipInput,
        allowFree: true,
        // Stored as object { type: url } in YAML; the form treats it as an
        // array of "type:url" strings on the wire and the form layout is
        // responsible for serializing back. For Phase A we keep it as the
        // already-flat chip-input view — Task 13 wires the round-trip.
      },
      { key: 'anchors',  label: 'Anchors',  renderer: ChipInput,
        allowFree: true },
      { key: 'description', label: 'Description', renderer: MdField },
      { key: 'specification', label: 'Specification', renderer: MdField },
      { key: 'plan', label: 'Plan', renderer: MdField },
      { key: 'notes', label: 'Notes', renderer: MdField },
      { key: 'review_instructions', label: 'Review instructions', renderer: MdField },
      { key: 'patchnote', label: 'Patchnote', renderer: MdField },
    ],
    systemManaged: [
      'id', 'created', 'started', 'completed', 'last_referenced',
      'activity', 'spec_review', 'auto_mode', 'locked_by',
    ],
    crossField: [
      // Self-dep guard.
      (entity) => {
        const id = entity.id;
        const deps = entity.depends_on || [];
        if (id && Array.isArray(deps) && deps.includes(id)) {
          return { key: 'depends_on', error: 'cannot depend on itself' };
        }
        return null;
      },
    ],
  };
}
```

- [ ] **Step 4: Run + commit**

```bash
cd plugins/taskmaster/viewer && npm run test:unit -- tests/unit/task-form.test.js
# Expected: PASS — 6/6
git add plugins/taskmaster/viewer/js/components/edit/forms/task-form.js \
        plugins/taskmaster/viewer/tests/unit/task-form.test.js
git commit -m "feat(taskmaster): task entity schema (v3-edit-007)"
```

---

## Task 13: Wire Task creation modal + Task edit modal

**Files:**
- Modify: `viewer/js/screens/kanban.js` (lines 149–154 — replace `location.hash = '#/task/new'`)
- Modify: `viewer/js/screens/table.js` (lines 68–74 — same)
- Modify: `viewer/js/components/task-detail-document.js` (line 34 — wire `✎ Edit` button)
- Create: `viewer/tests/edit-task.spec.js` (Playwright E2E)

`+ Task` button on kanban/table now opens `entity-modal` in `mode: 'create'` with the task schema. On save, it calls `api.createTask(payload)`, then triggers a backlog poll refresh so the new task appears in the kanban.

`✎ Edit` button on Task Detail opens the same modal in `mode: 'edit'` with the current task as `initialEntity`. On save, it calls `api.putTask(id, draft)` (or really, only the changed-since-mount fields — but PUT-with-full-entity is simpler and the server treats both PATCH and PUT the same).

- [ ] **Step 1: Modify kanban.js `+ Task` handler**

In `viewer/js/screens/kanban.js`, find the `+ Task` button block (lines 149–154 per current file):

```js
  // BEFORE:
  const addBtn = tmAction({
    icon: '+', label: 'Task', variant: 'primary', title: 'Add task',
    onClick: () => { location.hash = '#/task/new'; },
  });
```

Replace with:

```js
  // AFTER:
  const addBtn = tmAction({
    icon: '+', label: 'Task', variant: 'primary', title: 'Add task',
    onClick: () => openTaskCreateModal({ store, api }),
  });
```

Add at the top of `kanban.js` (after existing imports):

```js
import { openEntityModal } from '../components/edit/entity-modal.js';
import { taskSchema } from '../components/edit/forms/task-form.js';

function openTaskCreateModal({ store, api }) {
  const schema = taskSchema({ getBacklog: () => store.getBacklog() });
  openEntityModal({
    schema, mode: 'create',
    initialEntity: {
      // Prefill the active epic if any.
      epic: store.getBacklog()?.context?.active_epic || '',
      status: 'todo',
      priority: 'medium',
    },
    onSave: async (draft) => {
      try {
        await api.createTask(draft);
        // Trigger immediate backlog refresh so the new task shows up.
        store.setBacklog(await api.backlog());
      } catch (e) {
        return { error: e.message || String(e) };
      }
    },
    onCancel: () => {},
  });
}
```

- [ ] **Step 2: Same change in table.js**

In `viewer/js/screens/table.js` (around lines 68–74), apply the same import + `openTaskCreateModal` helper. To avoid duplicating the helper, hoist it to a new file:

Create `viewer/js/components/edit/task-actions.js`:

```js
// viewer/js/components/edit/task-actions.js
// Shared wrappers for opening the task modal in create/edit mode.

import { openEntityModal } from './entity-modal.js';
import { taskSchema } from './forms/task-form.js';

export function openTaskCreateModal({ store, api, prefillEpic }) {
  const schema = taskSchema({ getBacklog: () => store.getBacklog() });
  openEntityModal({
    schema, mode: 'create',
    initialEntity: {
      epic: prefillEpic || store.getBacklog()?.context?.active_epic || '',
      status: 'todo',
      priority: 'medium',
    },
    onSave: async (draft) => {
      try {
        await api.createTask(draft);
        store.setBacklog(await api.backlog());
      } catch (e) {
        return { error: e.message || String(e) };
      }
    },
    onCancel: () => {},
  });
}

export function openTaskEditModal({ store, api, task }) {
  const schema = taskSchema({ getBacklog: () => store.getBacklog() });
  openEntityModal({
    schema, mode: 'edit',
    initialEntity: { ...task },
    onSave: async (draft) => {
      try {
        // Only send changed fields (not systemManaged ones).
        const patch = {};
        for (const f of schema.fields) {
          if (JSON.stringify(draft[f.key] ?? null) !== JSON.stringify(task[f.key] ?? null)) {
            patch[f.key] = draft[f.key];
          }
        }
        if (Object.keys(patch).length) await api.patchTask(task.id, patch);
        store.setBacklog(await api.backlog());
      } catch (e) {
        if (e && e.code === 409) {
          // Surface full conflict; user can pick fields to keep.
          const { showFullConflict } = await import('./conflict-banner.js');
          showFullConflict({
            entityKind: 'task', entityId: task.id,
            localDraft: draft, currentValue: e.current,
            currentEtag: e.current_etag,
            onResolve: async (merged) => {
              const { store: s } = await import('../../store.js');
              s.setEtag(`task:${task.id}`, e.current_etag);
              await api.patchTask(task.id, merged);
              s.setBacklog(await api.backlog());
            },
          });
          return { error: 'Conflict — see banner' };
        }
        return { error: e.message || String(e) };
      }
    },
    onCancel: () => {},
  });
}
```

Now in both `kanban.js` and `table.js`:

```js
import { openTaskCreateModal } from '../components/edit/task-actions.js';
// ... in the button handler:
onClick: () => openTaskCreateModal({ store, api }),
```

- [ ] **Step 3: Wire `✎ Edit` button on task-detail**

In `viewer/js/components/task-detail-document.js`, find `mountTopbar` (line 23):

```js
// BEFORE:
function mountTopbar({ prefs, onToggleVariant }) {
  const topbar = claimTopbar();
  if (!topbar) return;
  const view = prefs?.screens?.task_detail?.view === 'B' ? 'B' : 'A';
  const seg = tmSegmented(...);
  const editBtn = tmAction({ icon: '✎', label: 'Edit', title: 'Edit task — coming soon', disabled: true });
  ...
}
```

Update to receive task + handlers and wire the button:

```js
// AFTER:
function mountTopbar({ prefs, onToggleVariant, task, onEdit }) {
  const topbar = claimTopbar();
  if (!topbar) return;
  const view = prefs?.screens?.task_detail?.view === 'B' ? 'B' : 'A';
  const seg = tmSegmented(
    [
      { key: 'A', label: 'Document' },
      { key: 'B', label: 'Graph' },
    ],
    { value: view, onChange: (v) => onToggleVariant?.(v) },
  );
  const editBtn = tmAction({
    icon: '✎', label: 'Edit', title: 'Edit task',
    onClick: () => onEdit?.(),
  });
  const archiveBtn = tmAction({ icon: '✕', label: 'Archive', title: 'Archive task — coming soon', disabled: true });
  topbar.append(seg, editBtn, archiveBtn);
}
```

In `mountTaskDetailDocument` (line 9), pass the new props through:

```js
export function mountTaskDetailDocument(root, ctx) {
  root.innerHTML = '';
  root.classList.add('td-page', 'td-page-A');

  mountTopbar({
    ...ctx,
    onEdit: () => {
      // Late-imports to avoid loading edit code on every viewer boot.
      import('./edit/task-actions.js').then(({ openTaskEditModal }) => {
        openTaskEditModal({ store: ctx.store || globalStoreShim(), api: ctx.api, task: ctx.task });
      });
    },
  });
  // ... rest unchanged
}
```

(Note: `ctx` from `task-detail.js` already includes `store, api, prefs` — verify by reading `task-detail.js:62-63`. If it doesn't, add `store, api` to the ctx in `task-detail.js:62`.)

Verify by reading `task-detail.js:32-65`:

```js
// viewer/js/screens/task-detail.js — at line 62 should look like:
cleanup = mountTaskDetailDocument(root, { task, related, prefs: prefsData, onNavigate, onToggleVariant });
```

Update to pass store + api:

```js
cleanup = mountTaskDetailDocument(root, { task, related, prefs: prefsData, store, api, onNavigate, onToggleVariant });
```

The `store, api` are already available because `mount(root, { store, api, prefs })` receives them in line 6. Same change for the variant-B branch around line 60.

Move `task-actions.js` so the import path matches: it's currently at `viewer/js/components/edit/task-actions.js`. From `task-detail-document.js` (in `viewer/js/components/`), the import is `./edit/task-actions.js`. ✓

- [ ] **Step 4: Playwright E2E test**

```js
// viewer/tests/edit-task.spec.js
import { test, expect } from '@playwright/test';

// Assumes the backlog server is running with use_v3=true and at least one
// epic exists. The dev test harness sets this up; for ad-hoc runs make
// sure `.taskmaster/viewer.json` has `"use_v3": true`.

test('Create task via + button opens modal and persists', async ({ page }) => {
  await page.goto('/#/kanban');
  await page.waitForSelector('.kanban-page', { timeout: 5000 });
  // Click + Task
  await page.locator('.tm-action--primary', { hasText: 'Task' }).click();
  await expect(page.locator('.em-modal')).toBeVisible();
  // Fill required fields
  await page.locator('.em-field[data-key="title"] input').fill('Playwright created');
  // Status defaults to 'todo'; priority defaults to 'medium'; epic prefilled if active.
  // If epic not prefilled, choose first available.
  const epicSelect = page.locator('.em-field[data-key="epic"] select');
  if ((await epicSelect.inputValue()) === '') {
    const firstOption = await epicSelect.locator('option').nth(0).getAttribute('value');
    await epicSelect.selectOption(firstOption);
  }
  // Save
  await page.locator('.em-save').click();
  // Modal closes, task appears
  await expect(page.locator('.em-modal')).not.toBeVisible({ timeout: 3000 });
  await expect(page.locator('.kanban-page')).toContainText('Playwright created');
});

test('Edit task via ✎ button opens prefilled modal', async ({ page }) => {
  await page.goto('/#/kanban');
  // Click first card to open detail
  await page.locator('.tm-card').first().click();
  await page.waitForSelector('.td-page', { timeout: 5000 });
  // Click Edit
  await page.locator('button:has-text("Edit")').click();
  await expect(page.locator('.em-modal')).toBeVisible();
  const title = await page.locator('.em-field[data-key="title"] input').inputValue();
  expect(title.length).toBeGreaterThan(0);
  // Cancel
  await page.locator('.em-cancel').click();
});
```

- [ ] **Step 5: Run + commit**

```bash
# Make sure the dev server is up first (start_server.py running).
cd plugins/taskmaster/viewer && npx playwright test tests/edit-task.spec.js --headed=false
# Expected: PASS — 2/2

git add plugins/taskmaster/viewer/js/screens/kanban.js \
        plugins/taskmaster/viewer/js/screens/table.js \
        plugins/taskmaster/viewer/js/components/edit/task-actions.js \
        plugins/taskmaster/viewer/js/components/task-detail-document.js \
        plugins/taskmaster/viewer/js/screens/task-detail.js \
        plugins/taskmaster/viewer/tests/edit-task.spec.js
git commit -m "feat(taskmaster): wire + Task / ✎ Edit buttons to entity modal (v3-edit-007)"
```

---

## Task 14: Inline-edit retrofit on Task Detail (Variant A)

**Files:**
- Modify: `viewer/js/components/task-detail-document.js` — wrap editable fields with `mountInlineField`
- Create: `viewer/tests/inline-edit-task.spec.js` (Playwright)

The existing `task-detail-document.js` renders fields as plain DOM (title as `<h1>`, chips as static spans, md-sections as rendered markdown). The retrofit replaces the static rendering of editable fields with `mountInlineField` calls. Read-mode stays visually similar (the inline-field's `read` mode produces a span/div that looks like the existing render, plus the dotted underline for editable fields).

Strategy: don't replace EVERY field at once — start with title, status, priority, notes (the most-edited fields). Cover the rest in a follow-up task within Phase A's polish.

The `started`/`completed` auto-stamping (folding in `v3-polish-033`) is verified end-to-end here: making a status change via inline edit must show the new timestamp on the dates row immediately after save (the backlog poller will re-fetch and re-render).

- [ ] **Step 1: Add inline-edit imports + helper to task-detail-document.js**

Add at the top of `task-detail-document.js` (after existing imports):

```js
import { mountInlineField } from './edit/inline-field.js';
import { taskSchema } from './edit/forms/task-form.js';
```

Add a helper near the top of the file:

```js
// Inline-edit save callback. Returns either undefined (success) or { error }.
function inlineSave(taskId, fieldKey, ctx) {
  return async (newValue) => {
    try {
      await ctx.api.patchTask(taskId, { [fieldKey]: newValue });
      // Refresh backlog so the change is reflected in store + other screens.
      ctx.store.setBacklog(await ctx.api.backlog());
    } catch (e) {
      if (e && e.code === 409) throw e; // re-throw so inline-field can show conflict banner
      return { error: e.message || String(e) };
    }
  };
}
```

- [ ] **Step 2: Replace `renderTitle` with inline-field**

```js
// BEFORE:
function renderTitle(task) {
  return h('h1', { class: 'td-title', 'data-test': 'title' }, task.title || '');
}

// AFTER:
function renderTitle(task, ctx) {
  const wrap = h('h1', { class: 'td-title', 'data-test': 'title' });
  const schema = taskSchema({ getBacklog: () => ctx.store?.getBacklog() });
  mountInlineField(wrap, {
    schema, fieldKey: 'title', entity: task,
    onSave: inlineSave(task.id, 'title', ctx),
  });
  return wrap;
}
```

Update the call site in `renderBody`:

```js
// BEFORE:
children.push(renderTitle(task));

// AFTER:
children.push(renderTitle(task, ctx));
```

- [ ] **Step 3: Inline-edit for status, priority chips**

Currently `renderChips()` returns static chip elements (line 173 area). Replace the status pill and priority pill with inline-field wrappers:

```js
function renderChips(task, ctx) {
  const epicColorVar = `--epic-1`;
  const priClass = (task.priority || '').toLowerCase();

  const schema = taskSchema({ getBacklog: () => ctx.store?.getBacklog() });

  // Status pill — now editable via EnumSelect inline
  const statusWrap = h('span', { class: 'td-status-pill td-inline-host' });
  mountInlineField(statusWrap, {
    schema, fieldKey: 'status', entity: task,
    onSave: inlineSave(task.id, 'status', ctx),
  });

  // Priority pill — same pattern
  const priWrap = h('span', { class: `td-pri-pill ${priClass === 'critical' ? 'crit' : priClass} td-inline-host` });
  mountInlineField(priWrap, {
    schema, fieldKey: 'priority', entity: task,
    onSave: inlineSave(task.id, 'priority', ctx),
  });

  const chips = [
    statusWrap,
    priWrap,
    task.estimate ? h('span', { class: 'td-size-chip' }, task.estimate) : null,
    task.epic ? h('span', { class: 'td-epic-chip', style: `--epic-1: var(${epicColorVar})` },
      [h('span', { class: 'td-swatch' }), h('span', {}, task.epic)]) : null,
    task.branch ? h('span', { class: 'td-branch', 'data-test': 'branch', on: { click: (e) => copyToChip(e.currentTarget, task.branch) } },
      [h('span', { class: 'td-id-text' }, `⎇ ${task.branch}`)]) : null,
    task.worktree ? h('span', { class: 'td-worktree', on: { click: (e) => copyToChip(e.currentTarget, task.worktree) } },
      [h('span', { class: 'td-id-text' }, `⌂ ${task.worktree}`)]) : null,
    task.release ? h('span', { class: 'td-release' }, task.release) : null,
    task.sub_repo ? h('span', { class: 'td-subrepo' }, `· ${task.sub_repo}`) : null,
  ].filter(Boolean);
  return h('div', { class: 'td-chips', 'data-test': 'chips' }, chips);
}
```

Update the call site in `renderBody`:

```js
// BEFORE:
children.push(renderChips(task));

// AFTER:
children.push(renderChips(task, ctx));
```

- [ ] **Step 4: Inline-edit for `notes` (proves md-field path works inline)**

Find `renderMdSection`:

```js
// BEFORE:
function renderMdSection(label, body, dataTest) {
  if (!body || !String(body).trim()) return null;
  return h('section', { class: 'td-section', 'data-test': dataTest }, [
    h('div', { class: 'td-section-h' }, label),
    h('div', { class: 'md-body', html: renderMarkdown(body) }),
  ]);
}
```

Add a sibling `renderMdSectionEditable`:

```js
function renderMdSectionEditable(label, fieldKey, task, ctx, dataTest) {
  const schema = taskSchema({ getBacklog: () => ctx.store?.getBacklog() });
  const wrap = h('section', { class: 'td-section td-inline-host', 'data-test': dataTest });
  wrap.appendChild(h('div', { class: 'td-section-h' }, label));
  mountInlineField(wrap, {
    schema, fieldKey, entity: task,
    onSave: inlineSave(task.id, fieldKey, ctx),
  });
  return wrap;
}
```

Update the four md sections in `renderBody`:

```js
// BEFORE:
children.push(renderMdSection('Specification', task.specification || task.description, 'sec-spec'));
children.push(renderMdSection('Plan', task.plan, 'sec-plan'));
children.push(renderMdSection('Notes', task.notes, 'sec-notes'));
if (task.status === 'in-review') {
  children.push(renderMdSection('Review instructions', task.review_instructions, 'sec-review-instructions'));
}

// AFTER:
children.push(renderMdSectionEditable('Specification', 'specification', task, ctx, 'sec-spec'));
children.push(renderMdSectionEditable('Plan', 'plan', task, ctx, 'sec-plan'));
children.push(renderMdSectionEditable('Notes', 'notes', task, ctx, 'sec-notes'));
if (task.status === 'in-review') {
  children.push(renderMdSectionEditable('Review instructions', 'review_instructions', task, ctx, 'sec-review-instructions'));
}
```

(Note: `description` was previously merged with `specification` for display. Inline editing forces them apart — `specification` and `description` become separately editable. The schema covers both.)

Update `renderBody` signature to accept ctx:

```js
// BEFORE:
function renderBody({ task }) { ... }

// AFTER:
function renderBody(ctx) {
  const { task } = ctx;
  // ... use task as before, pass ctx to children that need it ...
}
```

And in `renderGrid`:

```js
// BEFORE:
function renderGrid(ctx) {
  return h('div', { class: 'td-grid' }, [
    renderBody(ctx),
    renderRail(ctx),
  ]);
}
```

Already passes ctx — no change.

- [ ] **Step 5: Playwright test for inline edit + status auto-stamp**

```js
// viewer/tests/inline-edit-task.spec.js
import { test, expect } from '@playwright/test';

test('Inline edit title persists on Enter', async ({ page }) => {
  await page.goto('/#/kanban');
  await page.locator('.tm-card').first().click();
  await page.waitForSelector('.td-page', { timeout: 5000 });

  const titleSpan = page.locator('.td-title .ef-text');
  await titleSpan.click();
  const input = page.locator('.td-title input.ef-text-input');
  await input.fill('Renamed via inline');
  await input.press('Enter');

  // Wait for save to complete and read-mode swap.
  await expect(page.locator('.td-title .ef-text')).toContainText('Renamed via inline', { timeout: 3000 });
});

test('Inline status change auto-stamps started date', async ({ page }) => {
  await page.goto('/#/kanban');
  // Find a task that's currently 'todo'.
  // (Test harness should ensure one exists.)
  await page.locator('.tm-card[data-status="todo"]').first().click();
  await page.waitForSelector('.td-page');

  // Capture started cell value before
  const startedBefore = await page.locator('[data-test="dates"] .td-date-cell:nth-child(2) .abs').textContent();
  expect(startedBefore?.trim()).toBe('—');

  // Inline-edit status from todo → in-progress
  await page.locator('.td-status-pill .ef-text').click();
  await page.locator('.td-status-pill select').selectOption('in-progress');
  // EnumSelect commits on change, so save fires immediately.
  await page.waitForTimeout(800); // allow save + backlog poll

  const startedAfter = await page.locator('[data-test="dates"] .td-date-cell:nth-child(2) .abs').textContent();
  expect(startedAfter?.trim()).not.toBe('—');
});
```

- [ ] **Step 6: Run + commit**

```bash
cd plugins/taskmaster/viewer && npx playwright test tests/inline-edit-task.spec.js --headed=false
# Expected: PASS — 2/2

git add plugins/taskmaster/viewer/js/components/task-detail-document.js \
        plugins/taskmaster/viewer/tests/inline-edit-task.spec.js
git commit -m "feat(taskmaster): inline-edit retrofit on Task Detail (title, status, priority, md sections) (v3-edit-008)"
```

---

## Task 15: Server-side validation pipeline

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py` — add `validate_task_write` that runs `backlog_validate` rules on a proposed write
- Modify: `plugins/taskmaster/backlog_server.py` — call `validate_task_write` before commit; on rejection return 422 with errors
- Modify: `plugins/taskmaster/viewer/js/api.js` — add `validateTask` method
- Create: `plugins/taskmaster/tests/test_v3_task_validate.py`

The client-side schema runner (Task 6) catches required-field/format issues. The server is authoritative for cross-entity rules:
- `epic` must exist
- `phase` must exist (if set)
- `depends_on` ids must exist
- No dependency cycles
- No self-deps (also caught client-side)

The existing `backlog_validate()` MCP tool already implements these checks against the whole backlog. We need a per-task variant that takes the proposed-state task and runs the same rules in isolation — without persisting.

- [ ] **Step 1: Test**

```python
# plugins/taskmaster/tests/test_v3_task_validate.py
import pytest
import yaml
from pathlib import Path


@pytest.fixture
def populated_backlog(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    bp = tmp_path / "backlog.yaml"
    bp.write_text(yaml.safe_dump({
        "meta": {"project": "test"},
        "epics": [
            {"id": "e1", "name": "E1", "status": "active",
             "tasks": [
                 {"id": "e1-001", "title": "A", "status": "todo", "priority": "medium"},
                 {"id": "e1-002", "title": "B", "status": "todo", "priority": "medium",
                  "depends_on": ["e1-001"]},
             ]},
        ],
        "phases": [{"id": "p1", "name": "P1", "status": "active"}],
    }))
    return bp


def test_validate_passes_for_clean_patch(populated_backlog):
    from taskmaster_v3 import validate_task_write
    errors = validate_task_write("e1-001", {"title": "Renamed"}, backlog_path=populated_backlog)
    assert errors == {}


def test_validate_rejects_unknown_epic(populated_backlog):
    from taskmaster_v3 import validate_task_write
    errors = validate_task_write("e1-001", {"epic": "missing"}, backlog_path=populated_backlog)
    assert "epic" in errors


def test_validate_rejects_unknown_phase(populated_backlog):
    from taskmaster_v3 import validate_task_write
    errors = validate_task_write("e1-001", {"phase": "p-missing"}, backlog_path=populated_backlog)
    assert "phase" in errors


def test_validate_rejects_unknown_dep(populated_backlog):
    from taskmaster_v3 import validate_task_write
    errors = validate_task_write("e1-001", {"depends_on": ["e1-999"]}, backlog_path=populated_backlog)
    assert "depends_on" in errors


def test_validate_rejects_self_dep(populated_backlog):
    from taskmaster_v3 import validate_task_write
    errors = validate_task_write("e1-001", {"depends_on": ["e1-001"]}, backlog_path=populated_backlog)
    assert "depends_on" in errors


def test_validate_rejects_dep_cycle(populated_backlog):
    """e1-002 depends on e1-001. Adding e1-002 to e1-001's deps creates a cycle."""
    from taskmaster_v3 import validate_task_write
    errors = validate_task_write("e1-001", {"depends_on": ["e1-002"]}, backlog_path=populated_backlog)
    assert "depends_on" in errors
    assert "cycle" in errors["depends_on"].lower()
```

- [ ] **Step 2: Run (fails — function missing)**

- [ ] **Step 3: Implement `validate_task_write`**

Append to `taskmaster_v3.py`:

```python
def validate_task_write(task_id: str, patch: dict, backlog_path: Path | None = None) -> dict[str, str]:
    """Run cross-entity validation for a proposed task write.

    Returns a dict { field: error_message }. Empty dict means valid.
    Pure function — does not persist.
    """
    bp = backlog_path or _resolve_backlog_path()
    data = yaml.safe_load(bp.read_text(encoding="utf-8")) or {}
    errors: dict[str, str] = {}

    # Build helper maps.
    epic_ids = {e.get("id") for e in (data.get("epics") or []) if e.get("id")}
    phase_ids = {p.get("id") for p in (data.get("phases") or []) if p.get("id")}
    all_tasks: list[dict] = []
    for e in data.get("epics") or []:
        for t in e.get("tasks") or []:
            all_tasks.append(t)
    task_ids = {t.get("id") for t in all_tasks if t.get("id")}

    # Locate the task being patched.
    me = next((t for t in all_tasks if t.get("id") == task_id), None)
    if me is None and task_id != "<new>":
        errors["_task"] = f"task {task_id} not found"
        return errors

    # Compose the proposed state.
    proposed = {**(me or {}), **patch}

    # Epic must exist.
    if "epic" in patch and patch["epic"] and patch["epic"] not in epic_ids:
        errors["epic"] = f"unknown epic: {patch['epic']}"

    # Phase must exist if set.
    if "phase" in patch and patch["phase"] and patch["phase"] not in phase_ids:
        errors["phase"] = f"unknown phase: {patch['phase']}"

    # Deps: each must exist; no self-dep; no cycle.
    if "depends_on" in patch:
        deps = patch["depends_on"] or []
        for d in deps:
            if d == task_id:
                errors["depends_on"] = "cannot depend on itself"
                break
            if d not in task_ids:
                errors["depends_on"] = f"unknown task in depends_on: {d}"
                break
        if "depends_on" not in errors:
            # Cycle detection: BFS from each dep — if any path reaches task_id, cycle.
            adj = {t.get("id"): list(t.get("depends_on") or []) for t in all_tasks if t.get("id")}
            adj[task_id] = list(deps)  # simulate the proposed state
            if _has_cycle_to(adj, task_id):
                errors["depends_on"] = "introduces a dependency cycle"

    return errors


def _has_cycle_to(adj: dict, target: str) -> bool:
    """True if `target` is reachable from any of its own deps under `adj`."""
    seen = set()
    stack = list(adj.get(target, []))
    while stack:
        cur = stack.pop()
        if cur == target:
            return True
        if cur in seen:
            continue
        seen.add(cur)
        stack.extend(adj.get(cur, []))
    return False
```

- [ ] **Step 4: Wire into HTTP handlers**

In `do_PATCH` (and `do_PUT` for tasks, and `do_POST` `/api/tasks`), insert a validation step before calling `update_task`:

```python
            try:
                from taskmaster_v3 import validate_task_write, update_task
                errors = validate_task_write(task_id, patch)
                if errors:
                    self._send_json(422, {"ok": False, "errors": errors})
                    return
                task = update_task(task_id, patch)
                # ... existing success path ...
```

For `POST /api/tasks` (create), use `task_id="<new>"` and run only the field-level checks (epic existence is the main one):

```python
            from taskmaster_v3 import validate_task_write, create_task
            errors = validate_task_write("<new>", payload)
            if errors:
                self._send_json(422, {"ok": False, "errors": errors})
                return
            new_id = create_task(payload)
            # ...
```

Also add a standalone validate endpoint in `do_POST`:

```python
        if self.path == "/api/tasks/validate":
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode("utf-8") if length else ""
            try:
                payload = json.loads(raw)
            except Exception as e:
                self._send_json(400, {"ok": False, "error": f"invalid JSON: {e}"})
                return
            tid = payload.get("task_id") or "<new>"
            patch = payload.get("patch") or {}
            from taskmaster_v3 import validate_task_write
            errors = validate_task_write(tid, patch)
            self._send_json(200, {"ok": len(errors) == 0, "errors": errors})
            return
```

- [ ] **Step 5: Wire client api.js**

Add to `viewer/js/api.js`:

```js
  validateTask: (taskId, patch) =>
    http('POST', '/api/tasks/validate', { task_id: taskId, patch }),
```

The entity-modal can call this on Save before the actual write to surface server-side errors in the modal footer (purely UX nicety; the write would 422 anyway).

Update `task-actions.js` `openTaskCreateModal` and `openTaskEditModal` `onSave` to handle 422:

```js
// inside onSave:
try {
  await api.createTask(draft);
  store.setBacklog(await api.backlog());
} catch (e) {
  if (e && e.code === 422 && e.errors) {
    // Map server errors to per-field display.
    const msgs = Object.entries(e.errors).map(([k, v]) => `${k}: ${v}`).join(' · ');
    return { error: msgs };
  }
  return { error: e.message || String(e) };
}
```

Update `http()` in `api.js` to surface 422 the same way it surfaces 409:

```js
  if (resp.status === 422) {
    const j = await resp.json();
    const err = new Error('validation failed');
    err.code = 422;
    err.errors = j.errors || {};
    throw err;
  }
```

- [ ] **Step 6: Run all tests**

```bash
cd plugins/taskmaster && pytest tests/test_v3_task_validate.py -x -v
# Expected: PASS — 6/6
cd plugins/taskmaster && pytest tests/ -x -v
# Expected: ALL PASS — full suite green
cd plugins/taskmaster/viewer && npm run test:unit
# Expected: ALL PASS
```

- [ ] **Step 7: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py \
        plugins/taskmaster/backlog_server.py \
        plugins/taskmaster/viewer/js/api.js \
        plugins/taskmaster/viewer/js/components/edit/task-actions.js \
        plugins/taskmaster/tests/test_v3_task_validate.py
git commit -m "feat(taskmaster): server-side validation pipeline + 422 surface (v3-edit-009)"
```

---

## Self-review

**Spec coverage** — every Phase A task in the spec maps to a numbered task above:

| Spec ID | Plan Tasks |
|---|---|
| `v3-edit-001` Field renderer primitives | Tasks 1, 2, 3, 4, 5, 6 |
| `v3-edit-002` entity-modal shell | Task 7 |
| `v3-edit-003` inline-field wrapper | Task 8 |
| `v3-edit-004` HTTP write surface + write primitives | Task 9 |
| `v3-edit-005` ETag/If-Match concurrency | Task 10 |
| `v3-edit-006` Conflict banner + Show-diff | Task 11 |
| `v3-edit-007` Task form composition + modal wiring | Tasks 12, 13 |
| `v3-edit-008` Inline-edit retrofit + started/completed stamps | Task 14 (started/completed in Task 9) |
| `v3-edit-009` Validation pipeline | Task 15 |

**Spec-flagged dependencies** — `v3-polish-029` (flat tasks API) and `v3-polish-030` (task-detail loaders) are already patched on this branch in uncommitted state; the plan assumes they're committed before Phase A starts. `v3-polish-033` (started/completed stamping) is folded into Task 9's `update_task` implementation.

**Architectural consistency** — schema → renderer → field-component flow holds end-to-end. Same field renderers serve modal (Task 7) and inline (Task 8) consumers. Server write primitive (`update_task`) is shared across HTTP and (future) MCP. ETag/409 path goes through both inline-field (single field) and modal (full draft).

**Out-of-scope sweep** (spec §Out of scope) — confirmed not in plan: bulk operations, comments, file uploads, undo/redo, permissions, real-time collab.

**Field coverage** — the task schema in Task 12 covers every editable field listed in the spec's Per-entity field map for Task. SystemManaged list matches.

**Known limits of Phase A** carried into Phase B/C:
- Only Task entity is modal/inline-editable. Issues/lessons/handovers/epics/phases stay read-only until Phase B+.
- The `docs` field is rendered as a plain chip-input — round-trip serialization to YAML's `{type: url}` map is incomplete (the plan flags this in Task 12 Step 3 with a comment). A focused fix lives in Phase B if any users rely on docs editing before then.
- AnchorEditor is built in Phase B (only consumer is Lesson form).

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-04-v3-edit-phase-a.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Good fit here because Phase A has 15 numbered tasks and each one is bounded and testable. Subagents can run unit tests independently and report green/red without polluting main context with full diffs.

**2. Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints for review. Slower per-task because the main context grows with each commit, but lets you redirect strategy mid-task without spinning up a new agent.

Which approach?

