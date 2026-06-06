# Agent-Driven UI Testing — A Portable Two-Harness Playbook

**Status:** v1, 2026-06-06. Distilled from the CodeMaestro desktop `ui-e2e` suite and `cm-drive-app` exploratory harness.
**Audience:** AI agents (Claude Code or similar) setting up UI testing in a fresh project. A session in a new repo should be able to implement either harness from this document alone. Humans welcome too.
**Applies to:** any project with a web-rendered UI — plain web apps, Electron apps, local tool dashboards (e.g. a Taskmaster kanban viewer in claude-tools).

> **Worked example (CM):** blockquotes like this one carry CodeMaestro-specific evidence. They are
> illustrations, never load-bearing — skip them all and the playbook still works.

---

## 1. The Two-Harness Model

One harness cannot do both jobs. Build two:

| | Harness 1: Deterministic E2E | Harness 2: Agent-driven exploratory |
|---|---|---|
| **Stack** | UI only; everything else mocked | The real, full stack |
| **Driver** | `@playwright/test` specs | An AI agent with `@playwright/cli` |
| **Determinism** | Total — same result every run | None — it's a human-tester surrogate |
| **What it proves** | "Known flows still work" (regression gate) | "A tester clicked through and here's the friction" |
| **What it can NEVER prove** | The real stack integrates | The absence of bugs |
| **Runs** | CI / pre-merge loop, every change | On demand, before marking work verified |
| **Cost profile** | Cheap per run, expensive to build | Cheap to build, costs agent tokens per run |
| **Failure meaning** | Regression (or stale baseline) — always actionable | A finding to triage, not a gate verdict |

**Order of construction:** if the project has CI and an existing test culture, build Harness 1 first.
If the immediate need is "let the agent QA in-progress features," Harness 2 is days cheaper and
delivers value immediately — build it first, add Harness 1 when flows stabilize.

**The complementarity is the point.** The deterministic suite certifies; the exploratory harness
discovers. Treating exploratory findings as a pass/fail gate, or trying to make the deterministic
suite "explore," collapses both into something worse than either.

> **Worked example (CM):** `ui-e2e` (epic, 8 renderer specs + 1 Electron boot smoke) is the gate;
> `cm-drive-app` (a Skill) drives the real Electron app over CDP to test the in-review pile.
> Specs: `docs/superpowers/specs/2026-05-29-ui-e2e-testing-harness-design.md` and
> `2026-06-01-claude-driven-exploratory-app-harness-design.md`.

---

## 2. Decision Framework

Answer these about the target app **before writing any harness code**. Each answer selects
patterns from §3/§4 (see the adaptation matrix in §5).

1. **How does the UI get served?**
   - A plain dev server / static files → Harness 1 can drive it directly.
   - A combined dev script that boots a host process (Electron, a daemon, a backend) → you need a
     *renderer-only serving strategy* (§3.1). Check what `npm run dev` actually launches before
     assuming.
2. **Is there a privileged bridge?** (Electron `contextBridge`/IPC, browser-extension APIs, a
   WebSocket to a local host process.) If yes → bridge shim (§3.2) for Harness 1, and find or add
   a debug entry point (§4.2) for Harness 2.
3. **What are the external boundaries?** Enumerate every network origin the UI calls. These are
   your `page.route` mock surface (§3.3) and your guard surface (§4.3).
4. **Are there paid, destructive, or externally-visible actions?** (LLM calls that spend credits,
   deletes, emails, posts.) Enumerate the exact endpoints **from source code, not from memory or
   guesswork** — then guard them (§4.3).
5. **What is the auth model?** Token in localStorage? Cookie? None (local dashboard)? This decides
   the auth-seeding strategy (§3.4) and whether Harness 2 can reuse a live session (§4.4).
6. **Does the agent run where a browser can run?** Headless CI vs. a dev machine with a display
   changes nothing architecturally but decides default `headless` flags.

---

## 3. Harness 1 — Deterministic E2E Suite

### 3.1 Renderer-only serving strategy

Decouple the UI from its host process so Playwright can drive a plain Chromium against a plain
web server.

- **Do not reuse the project's dev script blindly.** Combined dev scripts often boot the host
  process (Electron, backend) as a side effect and have no standalone-UI mode.
- Create a dedicated serving config (e.g. `vite.config.e2e.ts`) that serves **only the renderer**:
  strip host-process plugins, pin a dedicated port, keep aliases/transformations identical to the
  real config.
- Keep this config in `e2e/` or clearly named at root; it is test infrastructure, not product code.

> **Worked example (CM):** `npm run dev` launches Electron via the vite-electron plugin's
> `onstart` hook — there is NO standalone renderer server. `vite.config.e2e.ts` (port 7800, no
> electron plugin) exists solely for the harness.

**HARD RULE — test production builds, not dev servers, for anything code-split.**
A dev server's dependency optimizer discovers a lazy chunk's deps on *first navigation*, then
fires a forced full-page reload that aborts the in-flight spec (`net::ERR_ABORTED`, wiped roots).
This is architectural: warming, retries, `optimizeDeps.include`, worker limits, and `hmr:false`
all merely move the flake. If the app has heavy lazy-loaded surfaces, run specs against
`vite build && vite preview` (or equivalent). A dev-server harness is acceptable only for small
apps with no code splitting — and even then, warm the server in `globalSetup` before specs run.

> **Worked example (CM):** the `ui-e2e-008` wall. Suite green from a worktree (small dep graph,
> isolated `.vite` cache) but flaky from the full checkout on the 3 heaviest code-split surfaces.
> Six config-level fixes failed; the durable fix is testing a prod build.

### 3.2 Bridge shim — fake the privileged surface

If the UI expects a privileged bridge (`window.ipcRenderer`, `window.electronAPI`, an injected
object), specs must inject a fake **before any app code runs**, via `addInitScript`.

Rules learned the hard way:

- **Satisfy startup gates with plausible values, not stubs.** If boot code blocks awaiting a
  value from the bridge (a port number, a config object), the shim must return a *realistic*
  value (a real integer port, a well-formed object), or the app hangs pre-render and every spec
  times out identically.
- **Cover module-level consumers.** Code that calls the bridge at import time (top-level `await`
  in an i18n loader, a config module) executes before your test code — the shim must already be
  in place and must implement those calls.
- **Add a drift guard:** a *unit* test (vitest/jest) that imports the real preload/bridge type
  and asserts the shim implements the same method surface. Without it, a renamed IPC channel
  silently turns every E2E green-on-a-broken-app or red-for-the-wrong-reason.
- **Never edit product source to accommodate the shim** — with one sanctioned exception: a
  single env-gated guard in the host process for boot smokes (§3.6). Hold this discipline; it
  keeps the harness honest about what it tests.

> **Worked example (CM):** `bridgeShim` fakes `onReceivePort`/`port()` with port `39817` (the
> renderer blocks on this gate in `main.tsx`), and `getResourcesPath` for i18n's module-level
> top-level await. The drift guard is a vitest spec under `e2e/harness/`.

### 3.3 Network mocking at the HTTP boundary

Mock at the network layer with `page.route`, not inside app code.

- **Glob carefully when baseURL is absolute.** If the app calls `https://api.example.com/projects`,
  the pattern `**/projects` matches — `**` spans scheme+host. Verify your patterns against the
  app's *actual* configured base URL, not the relative paths in source.
- Centralize mocks in one fixture (e.g. `mockCloud`) that specs opt into; per-spec ad-hoc routes
  rot fast.
- Mock the *response shapes the UI actually consumes*. Pull shapes from the app's API types or a
  recorded real response — never invent them.
- Anything NOT mocked should fail loudly. Consider a catch-all route that 500s unexpected
  origins, so a new unmocked endpoint breaks the spec instead of silently hitting production.

### 3.4 Auth seeding

Skip login flows; seed authenticated state directly.

- For localStorage-token apps: write the exact storage blob the state library expects (e.g. a
  zustand `persist` envelope — match its serialization, including version fields and whether
  `partialize` is configured) via `addInitScript` or `storageState`.
- Keep one spec that exercises the *real* login UI against mocks; seed everywhere else.
- Local dashboards with no auth: skip this section entirely.

### 3.5 Navigation & stability

- **`page.goto(url, { waitUntil: 'commit' })`** when the app has background fetches that never
  settle (polling, reconnecting sockets to a fake port) — waiting for `load` deadlocks.
- Use a `globalSetup` that performs one throwaway navigation to each entry route before specs
  run (server warm-up; also pre-triggers any one-time work).
- **Screenshot baselines:** pin the viewport explicitly in the Playwright config and scope
  baseline files per-OS from day one. An unpinned viewport makes baselines machine-specific —
  they pass where recorded and pre-fail everywhere else.

> **Worked example (CM):** `gdd-rendered.png` was recorded without a pinned viewport and is
> permanently pre-red on one Windows host (1230px vs 930px rendering).

### 3.6 Host-process boot smoke (optional, for bridged apps)

One smoke test that launches the *real* host process (`_electron.launch` for Electron) proves
the boot path the renderer-only suite can't. Pattern:

- A single env-gated guard in the host entry (e.g. `if (process.env.MY_E2E) { …stub the heavy
  service… }`) — env-gated no-op in production, and the only product-source edit the harness is
  allowed.
- Generous timeout (cold host boots are slow; CM uses 90s).
- Assert only "window appeared, renderer reached first paint." Everything functional belongs in
  the renderer suite.

### 3.7 Repo & runner hygiene

- **Spec-glob collision:** if the repo also runs vitest/jest, keep its `include` narrow
  (e.g. `e2e/harness/**/*.test.ts`), never a broad `e2e/**` — pulling Playwright `.spec.ts`
  files into a unit runner breaks on the `@playwright/test` import.
- **npm script arg-forwarding:** a script ending in `--project foo` mis-parses a trailing
  filename arg (`npm run test:e2e -- smoke` → "smoke" read as a project name). Document the
  full `npx playwright test <file> --config … --project …` form for filtered runs.
- **Git worktrees share the parent's `node_modules`** (Node walks up). Two consequences:
  (a) resolve tool deps with `createRequire` from the config file, not `__dirname/node_modules`;
  (b) **never `npm install` inside a worktree** — it writes the dependency into the *parent
  checkout's* `package.json`.

---

## 4. Harness 2 — Agent-Driven Exploratory Harness

### 4.1 Tooling: `@playwright/cli`, not MCP

Use **`@playwright/cli`** (the agent CLI — a separate, actively-maintained package from
`@playwright/test`): `npm install -g @playwright/cli@latest`.

- **Token economics:** a typical browser task costs ~4× fewer tokens via CLI than via the
  Playwright MCP server (lean invocations vs. big tool schemas + verbose a11y trees). Microsoft
  itself recommends CLI + skills over MCP for coding agents.
- **Persistent named sessions** (`-s=<name>`) hold cookies/storage *across CLI invocations* —
  this natively solves "an agent can't hold a `page` object between tool calls." No custom
  server needed.
- Selectors are not ref-only: `getByRole('button', {name: 'X'})`, `getByTestId`, and CSS all
  work alongside snapshot refs.
- Useful surface: `snapshot [--boxes]` (boxes = x,y,w,h → overlap/clipping detection),
  `eval` / `run-code` (preconditions, REST-as-the-app), `console`, `requests`, `route` (mock/
  block), `show --annotate` (user draws boxes + notes on the live page → annotated feedback).
- The bundled `SKILL.md` inside the package is the canonical usage reference; read it on first
  setup rather than trusting recalled flags.

### 4.2 Attaching to the app

**Plain web app / local dashboard:** just launch — `playwright-cli -s=qa open <url>`. Done.

**Electron (or any app you can't launch headlessly):** attach over CDP.

1. Add an **env-gated debug-port switch** to the host entry, *before* app-ready:
   `if (process.env.MY_DEBUG_PORT) appendSwitch('remote-debugging-port', …)` plus
   `remote-debugging-address 127.0.0.1`. Env-gated no-op in production. (This mirrors the §3.6
   guard — the two together are the only product edits either harness makes.)
2. Launch the app with the env var; attach:
   `playwright-cli -s=qa attach --cdp=http://127.0.0.1:<port>` — then run commands with the same
   `-s`. `detach` leaves the app running; the launcher owns the app's lifecycle, not the CLI.
3. **Tab-select gotcha:** in dev mode, auto-opened DevTools is itself a `type:page` CDP target —
   a naive attach can land on the *DevTools* tab. Always `tab-list`, identify the renderer by
   URL, `tab-select` it before snapshotting, or you'll be driving DevTools.
4. **Single-instance locks:** apps using `requestSingleInstanceLock` refuse a second launch —
   any already-running instance must be closed before launching the debuggable one.
5. **Auth for free:** launching with the debug port does not change the user-data dir, so the
   real logged-in session rehydrates. No fake tokens; the agent tests as the real user.

### 4.3 Guardrails on paid / destructive actions

The exploratory harness drives the **real** stack — real money, real deletions.

- **Enumerate the dangerous endpoints from source code.** Do not guess REST shapes; the actual
  paths are often not what you'd assume (tool-invoke RPC paths, not `/image/generate`).
- Block them with synthetic failures *before* exploring:
  `playwright-cli route "<pattern>" --status=403 --body='{"blocked":"qa-guard"}'`.
  (No `--abort` flag exists in current versions; a synthetic 403 is the block. The UI gets a
  clean failure it already knows how to render.)
- To intentionally fire ONE real action: `unroute <pattern>` → act → re-`route`. Confirm with
  the user first for anything that spends or destroys.
- Reads (GETs) on the same prefixes stay unguarded — observing real data is the point.

### 4.4 The exploration loop & findings discipline

The loop, per surface under test:

```
snapshot → act (click/fill) → observe (snapshot --boxes / screenshot / console / requests)
→ judge against the project's design system & UX intent → record finding → next
```

- **Judge against written standards** (design-system tokens, hard rules, copy guidelines) when
  they exist — "looks off" becomes "violates rule X," which is actionable.
- `eval`/`run-code` for preconditions (seed state, read stores) — but *click* through the
  actual flows; UX friction is the deliverable, and `evaluate`-driving past the UI hides it.
- **Findings → tracker, never silent fixes.** Each finding becomes a user-confirmed bug/idea in
  the project's task system, with screenshot evidence. The harness reports; humans (or a
  separate, scoped task) fix. An exploratory session that quietly patches code has destroyed
  its own evidence.
- State the negative honestly: a clean run means "no friction found on the paths driven," never
  "this feature is verified."

---

## 5. Adaptation Matrix

| Pattern | Plain web app | Electron / bridged app | Local tool dashboard (e.g. claude-tools kanban) |
|---|---|---|---|
| Renderer-only config (§3.1) | Usually free — dev server already standalone | **Required** — extract from combined dev script | Free — it's already a static/local server |
| Prod-build rule (§3.1) | Required if code-split | Required if code-split | Usually skippable (small, no lazy chunks) |
| Bridge shim (§3.2) | Skip | **Required** + drift guard | Skip (unless it talks to a local daemon — then shim that) |
| Network mocks (§3.3) | Required | Required | Often skippable — backend IS local; mock only true externals |
| Auth seeding (§3.4) | Required if authed | Required | Usually none |
| Boot smoke (§3.6) | Skip | **Required** (env-gated guard) | Optional — smoke the CLI/server boot instead |
| CDP attach (§4.2) | Skip — CLI launches directly | **Required** (debug-port switch, tab-select, instance lock) | Skip — CLI launches directly |
| Paid/destructive guards (§4.3) | Per app | Per app | Usually none → harness 2 becomes trivially safe |
| Session reuse (§4.4) | Cookie/profile dependent | Free via real user-data dir | N/A |

**Reading for claude-tools specifically:** a dashboard served locally with no auth and no paid
actions needs only: a Playwright config pointed at the local server + specs (§3.3 mocks only if
it calls external APIs), and `playwright-cli -s=qa open http://localhost:<port>` for exploratory
runs. Most of the Electron weight in §3–§4 drops away — that's the matrix working as intended.

---

## 6. Pitfalls — Hard Rules Index

Each cost real debugging time. Treat as rules, not suggestions.

| # | Rule | Why |
|---|---|---|
| 1 | Test prod builds for code-split apps | Dev-server dep-optimizer reload aborts specs; config fixes only relocate the flake |
| 2 | Check what the dev script launches before reusing it | Combined scripts boot host processes; there may be no standalone-UI mode |
| 3 | Shim must return plausible values for boot gates | Stub values hang the app pre-render; every spec times out identically |
| 4 | Pin viewport + per-OS screenshot baselines from day one | Unpinned baselines pre-fail on every other machine |
| 5 | `waitUntil: 'commit'` when background fetches never settle | Waiting for `load` deadlocks against fake/polling endpoints |
| 6 | Verify `page.route` globs against the real absolute baseURL | `**` spans scheme+host; relative-path reasoning misleads |
| 7 | Keep unit-runner globs away from Playwright specs | `@playwright/test` imports break under jsdom |
| 8 | Never `npm install` in a git worktree | Dep leaks into the parent checkout's package.json |
| 9 | `tab-list` → `tab-select` after CDP attach in dev mode | DevTools is a CDP page target; you may be driving DevTools |
| 10 | Close existing instances before a debuggable launch | Single-instance locks refuse the second launch |
| 11 | Enumerate paid/destructive endpoints from source | Real paths are often RPC-style, not the REST you'd guess |
| 12 | Guard = `route --status=403`; unroute → act → re-route for one real call | No `--abort`/`--continue` flags exist |
| 13 | Findings go to the tracker; the exploratory harness never silently fixes | Silent fixes destroy the evidence and the audit trail |
| 14 | Drift-guard the shim against the real bridge | Renamed IPC channels otherwise fail invisibly |
| 15 | Exploratory clean run ≠ verified feature | It proves absence of *found* friction on *driven* paths only |

---

## 7. Provenance (CM deep-detail pointers)

This playbook distills — for full archaeology, see the originals in the CodeMaestro monorepo:

- **Specs:** `docs/superpowers/specs/2026-05-29-ui-e2e-testing-harness-design.md` (deterministic),
  `docs/superpowers/specs/2026-06-01-claude-driven-exploratory-app-harness-design.md` (exploratory)
- **Plans:** `docs/superpowers/plans/2026-05-29-ui-e2e-testing-harness.md`,
  `docs/superpowers/plans/2026-06-01-cm-drive-app-exploratory-harness.md`
- **Memories:** `memory/ui-e2e-harness.md` (incl. the full optimizer-race failure log),
  `memory/playwright-cli-agent-harness.md` (CLI surface confirmations, spike findings)
- **Live artifacts:** `code-maestro-app-desktop/e2e/` (harness, specs, drive utilities,
  `SPIKE-FINDINGS.md`), `.claude/skills/cm-drive-app/SKILL.md`, `.claude/skills/cm-test-ui-loop/`
- **External:** `github.com/microsoft/playwright-cli` (the agent CLI), and the bundled SKILL.md
  inside the `@playwright/cli` package (canonical command reference)
