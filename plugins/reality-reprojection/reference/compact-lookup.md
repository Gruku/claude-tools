# Reality Reprojection — Compact Component Lookup

> Load this file when doing UI generation work. It replaces bulk reference loading for standard components.
> ~1.5k tokens. Sufficient for 80% of generation requests without loading any other reference file.

## Component Quick Reference

```
btn          <button class="btn btn--{v}">{LABEL}</button>
             v: primary secondary ghost outline | sm lg
             tokens: --btn-bg --btn-color --btn-border --btn-hover-bg --btn-radius

card         <div class="card {v}">{children}</div>
             v: card--elevated card--interactive card--tilt card--compact
             tokens: --card-bg --card-border --card-radius --card-shadow --card-padding

badge        <span class="badge badge--{v}">{text}</span>
             v: signature success warning critical info | sm lg
             tokens: --badge-bg --badge-color --badge-border --badge-radius

tag          <span class="tag tag--{v}">{text}</span>
             v: signature success warning critical
             tokens: --tag-bg --tag-color --tag-border

chip         <span class="chip chip--{v}">{text}</span>
             v: signature lime pink
             tokens: --chip-bg --chip-color

alert        <div class="alert alert--{v}"><div class="alert__body">...</div></div>
             v: info success warning critical
             tokens: --alert-bg --alert-border --alert-color --alert-icon-color

form-group   <div class="form-group"><label class="form-label">..</label><input class="form-input">..</div>
             tokens: --input-bg --input-border --input-color --input-focus-border --input-radius

toggle       <label class="toggle"><input type="checkbox"><span class="toggle__track"><span class="toggle__thumb"></span></span></label>
             tokens: --toggle-track-bg --toggle-active-bg --toggle-thumb-bg

tabs         <div class="tabs"><button class="tab is-active">Tab</button>...</div>
             tokens: --tab-bg --tab-color --tab-active-bg --tab-active-color --tab-border

modal        <div class="modal-overlay"><div class="modal">..</div></div>
             tokens: --modal-bg --modal-border --modal-radius --modal-shadow --modal-overlay-bg

table        <table class="table {v}">...</table>
             v: table--striped table--hoverable table--compact
             tokens: --table-bg --table-border --table-header-bg --table-row-hover

accordion    <div class="accordion"><div class="accordion__item is-expanded">...</div></div>
             tokens: --accordion-bg --accordion-border --accordion-header-bg

tooltip      <div class="tooltip">{text}</div>
             tokens: --tooltip-bg --tooltip-color --tooltip-radius

dropdown     <div class="dropdown is-open"><div class="dropdown__menu">...</div></div>
             tokens: --dropdown-bg --dropdown-border --dropdown-shadow

progress     <div class="progress"><div class="progress__fill" style="width:60%"></div></div>
             tokens: --progress-bg --progress-fill --progress-radius --progress-height

avatar       <div class="avatar avatar--{size}">{initials or img}</div>
             tokens: --avatar-bg --avatar-color --avatar-border --avatar-size

skeleton     <div class="skeleton skeleton--{v}"></div>
             v: text heading avatar circle
             tokens: --skeleton-bg --skeleton-shine

header       <header class="header header--sticky header--frost">...</header>
             tokens: --header-bg --header-border --header-blur

nav          <nav class="nav"><a class="nav__link is-active">...</a></nav>
             tokens: --nav-link-color --nav-active-color --nav-active-border

breadcrumb   <nav class="breadcrumb">...</nav>
             tokens: --breadcrumb-color --breadcrumb-active-color --breadcrumb-separator

pagination   <nav class="pagination">...</nav>
             tokens: --page-bg --page-color --page-active-bg --page-active-color

list         <ul class="list {v}">...</ul>
             v: list--bordered list--hoverable
             tokens: --list-bg --list-border --list-hover-bg

footer       <footer class="footer">...</footer>
             tokens: --footer-bg --footer-border --footer-color
```

## Override Patterns

```html
<!-- Inline (one-off) -->
<button class="btn btn--primary" style="--btn-bg: var(--accent-lime)">GO</button>

<!-- Class (reusable preset) -->
<button class="btn btn--lime">GO</button>

<!-- Scope (section-wide) -->
<div class="admin-panel" style="--btn-bg: var(--accent-pink); --card-border: var(--accent-pink)">
```

## Typographic Voices

- Headlines/titles → `.declaration`, `.declaration--h2`, `.declaration--h3`
- Body text → `.narrator`, `.narrator--small`
- Labels/metadata/code → `.technical`, `.technical--small`

## Non-Negotiable Rules

- Colors: `var(--token)` only. Never hardcode hex.
- Easing: `var(--ease-hourglass)`, `var(--ease-pendulum)`, `var(--ease-bell)`, `var(--ease-hourglass-settle)` only.
- Hover: `translateY(-1px)` for buttons, `translateX(2px)` for tags/nav. Never `scale()`.
- Radii: {2, 3, 4, 6, 8, 9999}px via tokens only.
- Font sizes: whole pixels only.
- Both polarities: include `[data-polarity="light"]` overrides for custom colors.
- Reduced motion: `@media (prefers-reduced-motion: reduce)` for animations.

## Need More?

Load ONE of these on-demand (~2-5k tokens each):
- `material-treatments.md` — grain, frost, shimmer (chromatic removed from system)
- `composition-recipes.md` — full page layouts (dashboard, article, settings)
- `component-catalog.md` — detailed component docs, all variants, full HTML
- `design-tokens.md` — every CSS custom property and its value
- `design-rules.md` — comprehensive rule set
- `typography.md` — voice assignments per component
