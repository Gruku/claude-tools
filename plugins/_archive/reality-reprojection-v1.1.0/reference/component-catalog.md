# Reality Reprojection — Component Catalog

> Every component with its exact classes, variants, states, and HTML patterns. Use these classes — don't invent new ones.

## 1. Buttons `.btn`

**Variants:** `.btn--primary`, `.btn--secondary`, `.btn--ghost`, `.btn--critical`, `.btn--sm`, `.btn--lg`, `.btn--icon`
**States:** `[disabled]`, `:disabled`, `:hover`, `:active`

```html
<button class="btn btn--primary">Primary Action</button>
<button class="btn btn--secondary">Secondary</button>
<button class="btn btn--ghost">Ghost</button>
<button class="btn btn--critical">Delete</button>
<button class="btn btn--primary btn--sm">Small</button>
<button class="btn btn--primary btn--lg">Large</button>
<button class="btn btn--icon" aria-label="Close">X</button>
<button class="btn btn--primary" disabled>Disabled</button>
```

**Hover:** `translateY(-1px)` (suppressed on `.btn--sm`)
**Active:** `translateY(0)`, `--shadow-inset`, `--dur-micro`
**Key tokens:** `--signature-fill`, `--on-signature`, `--signature-fill-hover`, `--highlight-inner`, `--shadow-hover-signature`

## 2. Cards `.card`

**Variants:** `.card--compact`, `.card--spacious`, `.card--flat`, `.card--elevated`, `.card--tilt`, `.card--signature`, `.card--interactive`
**Sub-elements:** `.card__header`, `.card__body`, `.card__footer`
**States:** `:hover`

```html
<div class="card card--elevated">
  <div class="card__header"><h3 class="declaration declaration--h5">Title</h3></div>
  <div class="card__body"><p class="narrator">Content here.</p></div>
  <div class="card__footer"><button class="btn btn--secondary">Action</button></div>
</div>
<div class="card card--signature">Left accent border card</div>
<div class="card card--interactive">Clickable card with glow</div>
```

**Hover:** Border strengthens, shadow deepens. Tilt: `perspective(1000px) rotateY(2deg) translateY(-3px)`
**Key tokens:** `--surface-raised`, `--border-default`, `--shadow-sm`, `--radius-lg`

## 3. Badges `.badge`

**Variants:** `.badge--success`, `.badge--warning`, `.badge--critical`, `.badge--info`, `.badge--accent`, `.badge--lime`, `.badge--pink`, `.badge--sm`, `.badge--lg`, `.badge--pill`, `.badge--pulse`
**States:** Pulse is infinite animation

```html
<span class="badge badge--success">Active</span>
<span class="badge badge--warning">Pending</span>
<span class="badge badge--critical">Error</span>
<span class="badge badge--info">Info</span>
<span class="badge badge--accent">New</span>
<span class="badge badge--pill badge--pulse">Live</span>
```

**Pulse:** Clockwork rhythm (step-like, not sinusoidal) — 2s loop, `--ease-pendulum`
**Key tokens:** `--color-success-subtle`, `--font-technical`, `--size-technical-small`, `--radius-sm`

## 4. Forms `.form-group` `.input` `.select` `.textarea` `.checkbox` `.radio`

**Sub-elements:** `.form-group`, `.form-label`, `.form-help`, `.form-error`, `.select-wrap`
**Variants:** `.input--error`, `.select--error`, `.textarea--error`, `.input--shake`
**States:** `:focus`, `:hover`, `:disabled`, `:checked`

```html
<div class="form-group">
  <label class="form-label" for="email">Email</label>
  <input id="email" class="input" type="email" placeholder="you@example.com">
  <span class="form-help">We'll never share your email.</span>
</div>

<div class="form-group">
  <label class="form-label">Role</label>
  <div class="select-wrap">
    <select class="select">
      <option>Designer</option>
      <option>Developer</option>
    </select>
  </div>
</div>

<label class="checkbox"><input type="checkbox"><span>Accept terms</span></label>
<label class="radio"><input type="radio" name="plan"><span>Free</span></label>
<textarea class="textarea" placeholder="Message..."></textarea>
```

**Focus:** Surface lifts from recessed to ground, signature glow ring
**Key tokens:** `--surface-recessed`, `--shadow-recessed`, `--border-focus`, `--signature-glow-strong`

## 5. Navigation `.nav`

**Variants:** `.nav--horizontal` (default), `.nav--vertical`
**Sub-elements:** `.nav-item`, `.nav-divider`, `.nav-label`
**States:** `.is-active`

```html
<nav class="nav nav--horizontal">
  <a class="nav-item is-active" href="/">Home</a>
  <a class="nav-item" href="/docs">Docs</a>
  <div class="nav-divider"></div>
  <a class="nav-item" href="/about">About</a>
</nav>

<nav class="nav nav--vertical">
  <span class="nav-label">Section</span>
  <a class="nav-item is-active" href="#">Overview</a>
  <a class="nav-item" href="#">Settings</a>
</nav>
```

**Hover:** `translateX(2px)`, background lift to `--ground-15`
**Active (vertical):** Left 2px signature bar via `::before`
**Key tokens:** `--signature`, `--signature-glow`, `--foreground-subtle`

## 6. Modals `.modal-overlay` `.modal`

**Variants:** `.modal--sm` (400px), `.modal--lg` (720px), `.modal--full`
**Sub-elements:** `.modal__header`, `.modal__body`, `.modal__footer`
**States:** `.is-active` on `.modal-overlay`

```html
<div class="modal-overlay is-active">
  <div class="modal modal--lg">
    <div class="modal__header">
      <h2 class="declaration declaration--h4">Confirm</h2>
      <button class="btn btn--icon">X</button>
    </div>
    <div class="modal__body"><p class="narrator">Are you sure?</p></div>
    <div class="modal__footer">
      <button class="btn btn--ghost">Cancel</button>
      <button class="btn btn--critical">Delete</button>
    </div>
  </div>
</div>
```

**Enter:** `translateY(16px) -> 0`, opacity fade, `--ease-hourglass`, `--dur-macro`
**Key tokens:** `--overlay-bg`, `--surface-raised`, `--shadow-elevated`, `--radius-xl`

## 7. Tables `.table`

**Variants:** `.table--striped`, `.table--hoverable`, `.table--compact`, `.table--bordered`
**Wrapper:** `.table-wrap` (horizontal scroll)

```html
<div class="table-wrap">
  <table class="table table--striped table--hoverable">
    <thead><tr><th>Name</th><th>Status</th></tr></thead>
    <tbody><tr><td>Item</td><td><span class="badge badge--success">Active</span></td></tr></tbody>
  </table>
</div>
```

**Hover (hoverable):** Row background to `--ground-15`
**Key tokens:** `--font-technical` (headers), `--tracking-ultra`, `--border-subtle`

## 8. Lists `.list`

**Variants:** `.list--compact`, `.list--bordered`, `.list--flush`
**Sub-elements:** `.list-item`, `.list-item--with-icon`, `.list-item__action`

```html
<ul class="list list--bordered">
  <li class="list-item list-item--with-icon">
    <span>Item content</span>
    <button class="list-item__action btn btn--icon">...</button>
  </li>
</ul>
```

**Hover:** Background to `--ground-10`
**Key tokens:** `--border-subtle`, `--space-md`, `--emitter-narrator`

## 9. Toggles `.toggle`

**Sub-elements:** `.toggle__track`, `.toggle__thumb`, `.toggle__label`
**Variants:** `.toggle--sm` (28x16px track, 10x10px thumb)
**States:** `.is-active`, `.is-disabled`

```html
<label class="toggle is-active">
  <div class="toggle__track"></div>
  <div class="toggle__thumb"></div>
  <span class="toggle__label">Dark Mode</span>
</label>
```

**Active:** Thumb slides `translateX(16px)` with `--ease-hourglass-settle` (elastic snap)
**Track:** `--shadow-recessed`; active: `--signature-dim` background + inner signature glow
**Thumb active:** `--signature-vivid`, `--highlight-inner`

## 10. Tags `.tag`

**Variants:** `.tag--default`, `.tag--signature`, `.tag--success`, `.tag--warning`, `.tag--critical`, `.tag--interactive`, `.tag--pill`
**Sub-elements:** `.tag__dismiss`
**States:** `.is-active`, `.is-disabled`

```html
<span class="tag tag--signature tag--interactive">
  React <button class="tag__dismiss">X</button>
</span>
<span class="tag tag--success tag--pill">Verified</span>
```

**Hover (interactive):** `translateX(2px)`, background lift
**Key tokens:** `--font-technical`, `--size-technical-small`, `--signature-glow`

## 11. Tabs `.tabs` `.tab` `.tab-panel`

**Variants:** `.tabs--vertical`
**States:** `.tab.is-active`, `.tab-panel.is-active`, `.tab:disabled`

```html
<div class="tabs" role="tablist">
  <button class="tab is-active" role="tab">Overview</button>
  <button class="tab" role="tab">Details</button>
</div>
<div class="tab-panel is-active">Overview content</div>
<div class="tab-panel">Details content</div>
```

**Active:** `--signature-glow` background, signature underline (2px) via `::after`
**Underline animation:** `--ease-pendulum`
**Key tokens:** `--font-narrator`, `--border-subtle`

## 12. Tooltips `.tooltip`

**Sub-elements:** `.tooltip__content`, `.tooltip__content::after` (arrow)
**Variants:** `.tooltip--top` (default), `.tooltip--bottom`, `.tooltip--left`, `.tooltip--right`
**States:** `:hover .tooltip__content`, `:focus-within .tooltip__content`

```html
<div class="tooltip tooltip--top">
  <button class="btn btn--secondary">Hover me</button>
  <div class="tooltip__content">Helpful hint text</div>
</div>
```

**Enter:** Pendulum: opacity + `translateY(4px -> 0)`, `--dur-standard`
**Arrow:** 6x6px rotated 45deg square
**Key tokens:** `--surface-overlay`, `--shadow-md`, `--font-narrator` (whisper, weight-light)

## 13. Dropdowns `.dropdown`

**Sub-elements:** `.dropdown__menu`, `.dropdown__item`, `.dropdown__separator`, `.dropdown__header`, `.dropdown__shortcut`
**Variants:** `.dropdown--right`
**States:** `.dropdown.is-open`, `.dropdown__item.is-active`, `.dropdown__item--has-children`, `.dropdown__item[disabled]`

```html
<div class="dropdown is-open">
  <button class="btn btn--secondary">Menu</button>
  <div class="dropdown__menu">
    <div class="dropdown__header">Actions</div>
    <button class="dropdown__item">Edit <span class="dropdown__shortcut">Ctrl+E</span></button>
    <button class="dropdown__item is-active">View</button>
    <div class="dropdown__separator"></div>
    <button class="dropdown__item dropdown__item--has-children">Export</button>
  </div>
</div>
```

**Open:** Flip Clock: `scaleY(0) -> scaleY(1)`, transform-origin: top, `--ease-hourglass`
**Item hover:** `translateX(2px)`, background `--ground-15`
**Has-children:** `::after { content: '>' }`
**Key tokens:** `--surface-overlay`, `--shadow-elevated`, `--font-narrator` (items), `--font-technical` (shortcuts)

## 14. Progress `.progress`

**Sub-elements:** `.progress__fill`, `.progress__label`, `.progress__value`
**Variants:** `.progress--success`, `.progress--warning`, `.progress--critical`, `.progress--sm` (4px), `.progress--lg` (12px), `.progress--indeterminate`
**Container:** `.progress-group`, `.progress-group__header`

```html
<div class="progress-group">
  <div class="progress-group__header">
    <span class="progress__label">Upload</span>
    <span class="progress__value">75%</span>
  </div>
  <div class="progress">
    <div class="progress__fill" style="width: 75%;"></div>
  </div>
</div>
<div class="progress progress--indeterminate"><div class="progress__fill"></div></div>
```

**Track:** `--ground-10` bg, `--shadow-recessed`, `--radius-xs`, 8px height
**Fill:** Signature gradient (muted -> base -> vivid), `--shadow-inner-glow`, grain overlay
**Indeterminate:** Pendulum sweep `translateX(-100% -> 300%)`
**Key tokens:** `--font-technical`, `--size-technical-small`

## 15. Alerts `.alert`

**Sub-elements:** `.alert__icon`, `.alert__content`, `.alert__title`, `.alert__body`, `.alert__meta`, `.alert__dismiss`
**Variants:** `.alert--success`, `.alert--warning`, `.alert--critical`, `.alert--info`, `.alert--toast`
**States:** `.alert--toast.is-exiting`

```html
<div class="alert alert--success">
  <div class="alert__icon"></div>
  <div class="alert__content">
    <div class="alert__title">Success!</div>
    <div class="alert__body">Changes saved.</div>
    <div class="alert__meta">2:30 PM</div>
  </div>
  <button class="alert__dismiss">X</button>
</div>
```

**Enter:** Bell: `translateY(-8px) -> 0` + opacity, `--ease-bell`, `--dur-standard`
**Semantic shapes:** Success: circle, Warning: triangle, Critical: diamond, Info: info-i
**Left border:** 3px in semantic color
**Toast exit:** `translateX(100%)` + opacity
**Key tokens:** `--surface-raised`, `--font-narrator` (body), `--font-technical` (meta)

## 16. Breadcrumbs `.breadcrumbs`

**Sub-elements:** `.breadcrumb`, `.breadcrumb__link`
**States:** `.is-current`, `:last-child`

```html
<nav class="breadcrumbs">
  <span class="breadcrumb"><a class="breadcrumb__link" href="/">Home</a></span>
  <span class="breadcrumb"><a class="breadcrumb__link" href="/docs">Docs</a></span>
  <span class="breadcrumb is-current">Components</span>
</nav>
```

**Separator:** `::after { content: '>' }` in `--ground-40`
**Link hover:** Color -> `--signature`, `--dur-micro`
**Key tokens:** `--font-technical`, `--size-technical-small`, `--tracking-wide`

## 17. Pagination `.pagination`

**Sub-elements:** `.pagination__item`, `.pagination__link`, `.pagination__prev`, `.pagination__next`, `.pagination__ellipsis`
**States:** `.is-current`, `:disabled`, `.is-disabled`

```html
<nav class="pagination">
  <span class="pagination__prev">←</span>
  <button class="pagination__link">1</button>
  <button class="pagination__link is-current">2</button>
  <button class="pagination__link">3</button>
  <span class="pagination__ellipsis">...</span>
  <button class="pagination__link">10</button>
  <span class="pagination__next">→</span>
</nav>
```

**Hover:** `translateY(-1px)`, background `--ground-15`
**Current:** `--signature` bg, `--foreground-on-accent`, `--highlight-inner`
**Key tokens:** `--font-technical`, `--radius-sm`, `--border-default`

## 18. Accordion `.accordion`

**Sub-elements:** `.accordion__item`, `.accordion__header`, `.accordion__caret`, `.accordion__content`, `.accordion__body`, `.accordion__body-inner`
**Variants:** `.accordion--flush`
**States:** `.accordion__item.is-expanded`

```html
<div class="accordion">
  <div class="accordion__item is-expanded">
    <button class="accordion__header">
      <span>Section One</span>
      <div class="accordion__caret"></div>
    </button>
    <div class="accordion__content">
      <div class="accordion__body">
        <div class="accordion__body-inner"><p>Content here.</p></div>
      </div>
    </div>
  </div>
  <div class="accordion__item">
    <button class="accordion__header">
      <span>Section Two</span>
      <div class="accordion__caret"></div>
    </button>
    <div class="accordion__content">
      <div class="accordion__body"><div class="accordion__body-inner">...</div></div>
    </div>
  </div>
</div>
```

**Expand:** `grid-template-rows: 0fr -> 1fr` (Flip Clock progressive reveal), `--ease-hourglass`
**Caret:** Rotates 90deg, `--signature-dim` bg on expanded
**Header hover:** Background `--ground-10`
**Key tokens:** `--font-narrator` (semi), `--border-subtle`

## 19. Avatar `.avatar`

**Variants:** `.avatar--initials`, `.avatar--placeholder`, `.avatar--sm` (24px), `.avatar--lg` (48px), `.avatar--xl` (64px)
**Sub-elements:** `.avatar__status`, `.avatar__status--online`, `.avatar__status--away`, `.avatar__status--busy`, `.avatar__status--offline`
**Group:** `.avatar-group`

```html
<div class="avatar avatar--lg">
  <img src="user.jpg" alt="User">
  <div class="avatar__status avatar__status--online"></div>
</div>
<div class="avatar avatar--initials">JD</div>
<div class="avatar avatar--placeholder"></div>
<div class="avatar-group">
  <div class="avatar avatar--sm"><img src="u1.jpg" alt="User 1"></div>
  <div class="avatar avatar--sm"><img src="u2.jpg" alt="User 2"></div>
</div>
```

**Shape:** `--radius-md` (manufactured, NOT circle — unless avatar--placeholder uses radius-full)
**Initials:** `--signature` bg, `--foreground-on-accent`, Declaration voice
**Group:** Overlapping -8px margin, z-index stacking (5 -> 1)
**Status:** Semantic colors: online=success, away=warning, busy=critical, offline=ground

## 20. Skeleton Loaders `.skeleton`

**Shape variants:** `.skeleton--text`, `.skeleton--text-full`, `.skeleton--text-medium`, `.skeleton--text-short`, `.skeleton--circle`, `.skeleton--avatar`, `.skeleton--avatar-sm`, `.skeleton--avatar-lg`, `.skeleton--card`, `.skeleton--heading`, `.skeleton--button`
**Groups:** `.skeleton-group`, `.skeleton-group--article`, `.skeleton-group--profile`, `.skeleton-group__text`

```html
<div class="skeleton-group skeleton-group--article">
  <div class="skeleton skeleton--heading"></div>
  <div class="skeleton skeleton--text skeleton--text-full"></div>
  <div class="skeleton skeleton--text skeleton--text-full"></div>
  <div class="skeleton skeleton--text skeleton--text-short"></div>
</div>
<div class="skeleton-group skeleton-group--profile">
  <div class="skeleton skeleton--avatar"></div>
  <div class="skeleton-group__text">
    <div class="skeleton skeleton--text skeleton--text-medium"></div>
    <div class="skeleton skeleton--text skeleton--text-short"></div>
  </div>
</div>
```

**Shimmer:** Pendulum sweep gradient, 1.8s infinite, `--ease-pendulum`
**Base:** `--ground-15` bg, `--radius-sm`
**Reduced motion:** Shimmer disabled, solid fill

## 21. Headers `.header`

**Variants:** `.header--transparent`, `.header--sticky`, `.header--frost`
**Sub-elements:** `.header__brand`, `.header__brand-name`, `.header__nav`, `.header__actions`, `.polarity-toggle`

```html
<header class="header header--sticky header--frost">
  <div class="header__brand">
    <span class="header__brand-name">App</span>
  </div>
  <nav class="header__nav">
    <a class="nav-item is-active" href="/">Home</a>
    <a class="nav-item" href="/docs">Docs</a>
  </nav>
  <div class="header__actions">
    <button class="polarity-toggle">Toggle</button>
  </div>
</header>
```

**Sticky:** `position: sticky; top: 0; z-index: 50`
**Frost:** `--frost-bg-medium` + backdrop blur
**Key tokens:** `--surface-raised`, `--border-default`, `--font-declaration` (brand)

## 22. Footers `.footer`

**Variants:** `.footer--minimal`, `.footer--stacked`
**Sub-elements:** `.footer__content`, `.footer__meta`, `.footer__links`, `.footer__link`

```html
<footer class="footer">
  <div class="footer__content">
    <span class="footer__meta">2026 Company. All rights reserved.</span>
    <nav class="footer__links">
      <a class="footer__link" href="/privacy">Privacy</a>
      <a class="footer__link" href="/terms">Terms</a>
    </nav>
  </div>
</footer>
```

**Link hover:** Color -> `--signature`
**Accent border:** `1px solid rgba(0, 211, 250, 0.12)` + `::before` gradient glow (60px)
**Key tokens:** `--font-technical` (meta), `--font-narrator` (links), `--space-xl`

## 23. Card Glow `.card-glow`

**Sub-elements:** `.card-glow__light`, `.card-glow__border`
**Custom properties:** `--glow-x`, `--glow-y` (position), `--glow-opacity` (visibility)
**JS required:** Mouse events set `--glow-x`/`--glow-y` in px, mouseenter/leave toggles `--glow-opacity`

```html
<div class="card card--elevated card-glow" style="position: relative;">
  <div class="card-glow__light"></div>
  <div class="card-glow__border"></div>
  <div class="card__body">Content</div>
</div>
```

**Light mode:** `__light` uses `rgba(0, 182, 214, 0.05)`, `__border` uses `rgba(0, 182, 214, 0.4)`
**__light:** Full-area radial gradient following cursor, `--dur-standard` transition
**__border:** Border-only glow using mask-composite trick, `--dur-micro` snap transition
**Key tokens:** `--signature`, `--dur-standard`, `--dur-micro`, `--ease-hourglass`, `--ease-bell`

## 24. Chips `.chip`

**Variants:** `.chip--signature`, `.chip--lime`, `.chip--pink`

```html
<div style="display: flex; gap: 8px;">
  <span class="chip chip--signature">Signature</span>
  <span class="chip chip--lime">Lime</span>
  <span class="chip chip--pink">Pink</span>
</div>
```

**Style:** Solid-fill colored labels with dark text (`#0d0d0c`) on bright backgrounds
**Voice:** Technical, 12px, weight 700, uppercase, `--tracking-wide`
**Size:** `min-height: 28px`, `padding: 0 10px`, `--radius-sm`

## 25. Frost Backdrop `.frost-backdrop`

**Variants:** `.section-frost-bg` (subtle section-level version)

```html
<div class="frost-backdrop">
  <div class="card card--elevated">Content within atmospheric container</div>
</div>
```

**Effect:** Tri-color radial gradient (cyan 0.32, pink 0.26, lime 0.2) + grain overlay
**Children:** Automatically `z-index: 2` above gradient
**Key tokens:** `--radius-lg`, `--space-xl`, `--grain-texture`

## 26. Frost Material Utilities `.mat-frost-*`

**Variants:** `.mat-frost-light`, `.mat-frost-medium`, `.mat-frost-heavy`

```html
<div class="mat-frost-light">Light frost panel</div>
<div class="mat-frost-medium">Standard frost — headers, navs</div>
<div class="mat-frost-heavy">Dense frost — modals, overlays</div>
```

| Class | Blur | Background Opacity | Use For |
|-------|------|-------------------|---------|
| `.mat-frost-light` | `8px` | `0.6` | Subtle depth, floating panels |
| `.mat-frost-medium` | `16px` | `0.75` | Headers, navigation bars |
| `.mat-frost-heavy` | `24px` | `0.85` | Modals, full overlays |
