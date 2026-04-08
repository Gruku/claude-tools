# Reality Reprojection — Composition Recipes

> How to compose components into pages. Spacing rhythm, voice hierarchy, layout conventions.

## Page Shell

```html
<html lang="en" data-polarity="dark">
<head>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@800&family=DM+Sans:ital,wght@0,400;0,600;0,700&family=JetBrains+Mono:wght@600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="reality-reprojection.css">
</head>
<body>
  <header class="header header--sticky header--frost">...</header>
  <main>...</main>
  <footer class="footer">...</footer>
</body>
</html>
```

## Hero Section

Centered, full-width intro with declaration title and optional CTAs.

```html
<section style="padding: var(--space-3xl) 0; text-align: center;">
  <div style="max-width: var(--container-max); margin: 0 auto; padding: 0 var(--container-padding);">
    <h1 class="declaration declaration--hero mat-chromatic-text">TITLE</h1>
    <p class="narrator narrator--large" style="color: var(--foreground-subtle); max-width: 600px; margin: var(--space-md) auto 0;">Tagline text.</p>
    <div style="display: flex; gap: var(--space-md); justify-content: center; margin-top: var(--space-xl); flex-wrap: wrap;">
      <button class="btn btn--primary btn--lg">Primary CTA</button>
      <button class="btn btn--secondary btn--lg">Secondary CTA</button>
    </div>
  </div>
</section>
```

**Key:** `text-align: center` on section, `margin: auto` on description, `justify-content: center` + `flex-wrap: wrap` on CTAs for mobile.

## Section Rhythm

Every content section follows: **label → title → description → content**.

```html
<section style="padding: var(--space-3xl) 0; border-top: 1px solid var(--border-subtle);">
  <div style="max-width: var(--container-max); margin: 0 auto; padding: 0 var(--container-padding);">
    <span class="technical technical--label" style="text-transform: uppercase; letter-spacing: var(--tracking-ultra); color: var(--signature-text);">LABEL</span>
    <h2 class="declaration declaration--h2" style="margin-top: var(--space-sm);">TITLE</h2>
    <p class="narrator" style="margin-top: var(--space-sm); color: var(--foreground-subtle); max-width: 600px;">Description.</p>
    <div style="margin-top: var(--space-xl);"><!-- content --></div>
  </div>
</section>
```

## Grids

```html
<!-- Responsive cards -->
<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: var(--space-lg);">

<!-- 2-column -->
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-lg);">

<!-- 3-column -->
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-lg);">

<!-- Content + sidebar -->
<div style="display: grid; grid-template-columns: 1fr 260px; gap: var(--space-2xl);">
```

## Recipe 1: Dashboard

Sidebar nav + main content with stat cards + data table.

```html
<div style="display: flex; min-height: 100vh;">
  <!-- Sidebar: 220px, surface-raised, border-right -->
  <aside style="width: 220px; background: var(--surface-raised); border-right: 1px solid var(--border-default); padding: var(--space-lg); display: flex; flex-direction: column;">
    <div style="margin-bottom: var(--space-xl);">
      <span class="declaration declaration--h5">BRAND</span>
      <span class="technical technical--label" style="display: block; color: var(--foreground-disabled);">Subtitle</span>
    </div>
    <nav class="nav nav--vertical">
      <a class="nav-item is-active" href="#">Overview</a>
      <a class="nav-item" href="#">Settings</a>
    </nav>
  </aside>

  <!-- Main: flex-1, space-xl padding -->
  <main style="flex: 1; padding: var(--space-xl);">
    <!-- Header row: declaration title + badge -->
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-xl);">
      <h3 class="declaration declaration--h4">PAGE TITLE</h3>
      <span class="badge badge--success">Status</span>
    </div>

    <!-- Stat cards: auto-fit grid, card--compact, center-aligned -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: var(--space-md); margin-bottom: var(--space-xl);">
      <div class="card card--compact" style="text-align: center; padding: var(--space-lg);">
        <div class="declaration declaration--h3" style="color: var(--signature-text);">42</div>
        <div class="technical technical--small" style="color: var(--foreground-subtle);">Label</div>
        <div class="technical technical--label" style="color: var(--color-success);">+5 trend</div>
      </div>
      <!-- more stat cards... -->
    </div>

    <!-- Data table -->
    <div class="table-wrap">
      <table class="table table--striped table--hoverable table--compact">
        <thead><tr><th>Name</th><th>Status</th><th style="text-align: right;">Time</th></tr></thead>
        <tbody>
          <tr>
            <td><code class="technical technical--small">item.css</code></td>
            <td><span class="badge badge--success badge--sm">OK</span></td>
            <td style="text-align: right;">2m ago</td>
          </tr>
        </tbody>
      </table>
    </div>
  </main>
</div>
```

**Stat card voice:** Declaration value → Technical label → Technical trend (colored by semantic).

## Recipe 2: Settings Panel

Content + side configuration panel.

```html
<div style="display: flex; gap: 0; background: var(--surface-ground); border: 1px solid var(--border-default); border-radius: var(--radius-lg); overflow: hidden;">
  <!-- Main content -->
  <div style="flex: 1; padding: var(--space-xl);">
    <h3 class="declaration declaration--h4">PAGE TITLE</h3>
    <p class="narrator narrator--small" style="color: var(--foreground-subtle);">Description.</p>

    <!-- Item cards: card--compact, title+badge row, narrator body, optional progress -->
    <div class="card card--compact mat-grain-fine" style="margin-top: var(--space-lg);">
      <div class="card__body">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-sm);">
          <span class="declaration declaration--h5">ITEM NAME</span>
          <span class="badge badge--success badge--sm">Active</span>
        </div>
        <p class="narrator narrator--whisper">Description text.</p>
        <!-- Optional progress bar -->
      </div>
    </div>
  </div>

  <!-- Side panel: 280px, surface-raised, flex-column -->
  <aside style="width: 280px; background: var(--surface-raised); border-left: 1px solid var(--border-default); padding: var(--space-lg); display: flex; flex-direction: column;">
    <h4 class="declaration declaration--h5">CONFIG</h4>

    <!-- Form section: technical label header → form fields -->
    <div style="margin-top: var(--space-lg);">
      <span class="technical technical--label" style="text-transform: uppercase; letter-spacing: var(--tracking-ultra); color: var(--foreground-subtle);">SECTION</span>
      <div class="form-group" style="margin-top: var(--space-sm);">
        <label class="form-label">Field</label>
        <input class="input" type="text" value="#00d3fa">
      </div>
    </div>

    <!-- Toggle rows -->
    <div style="margin-top: var(--space-lg);">
      <span class="technical technical--label" style="text-transform: uppercase; letter-spacing: var(--tracking-ultra); color: var(--foreground-subtle);">BEHAVIOR</span>
      <div style="display: flex; align-items: center; justify-content: space-between; margin-top: var(--space-sm); padding: var(--space-xs) 0;">
        <span class="narrator narrator--whisper">Option</span>
        <label class="toggle toggle--sm is-active"><div class="toggle__track"><div class="toggle__thumb"></div></div></label>
      </div>
    </div>

    <!-- Actions pinned to bottom -->
    <div style="margin-top: auto; display: flex; gap: var(--space-sm);">
      <button class="btn btn--primary btn--sm" style="flex: 1;">Save</button>
      <button class="btn btn--ghost btn--sm">Reset</button>
    </div>
  </aside>
</div>
```

## Recipe 3: Article Page

Header + breadcrumbs + article content + sticky sidebar.

```html
<header class="header header--sticky header--frost">
  <div class="header__brand"><span class="header__brand-name">Docs</span></div>
  <nav class="header__nav">
    <a class="nav-item is-active" href="/">Guide</a>
    <a class="nav-item" href="/api">API</a>
  </nav>
</header>

<main style="max-width: var(--container-max); margin: 0 auto; padding: var(--space-xl) var(--container-padding);">
  <nav class="breadcrumbs" style="margin-bottom: var(--space-lg);">
    <span class="breadcrumb"><a class="breadcrumb__link" href="/">Home</a></span>
    <span class="breadcrumb is-current">Current Page</span>
  </nav>

  <div style="display: grid; grid-template-columns: 1fr 260px; gap: var(--space-2xl);">
    <article>
      <h1 class="declaration declaration--h1">PAGE TITLE</h1>
      <p class="narrator narrator--large" style="color: var(--foreground-subtle); margin: var(--space-md) 0 var(--space-2xl);">Lead paragraph.</p>

      <h2 class="declaration declaration--h3" style="margin-bottom: var(--space-md);">SECTION</h2>
      <p class="narrator" style="margin-bottom: var(--space-lg);">Body text.</p>

      <!-- Callouts via alerts -->
      <div class="alert alert--info" style="margin-bottom: var(--space-xl);">
        <div class="alert__icon"></div>
        <div class="alert__content">
          <div class="alert__title">Note</div>
          <div class="alert__body">Callout content.</div>
        </div>
      </div>

      <!-- Collapsible detail via accordion -->
      <div class="accordion" style="margin-bottom: var(--space-xl);">
        <div class="accordion__item">
          <button class="accordion__header"><span>Details</span><div class="accordion__caret"></div></button>
          <div class="accordion__content"><div class="accordion__body"><div class="accordion__body-inner">
            <p class="narrator narrator--small">Expanded content.</p>
          </div></div></div>
        </div>
      </div>
    </article>

    <!-- Sticky sidebar -->
    <aside>
      <div class="card card--compact" style="position: sticky; top: 80px;">
        <div class="card__body">
          <span class="technical technical--label" style="text-transform: uppercase; letter-spacing: var(--tracking-ultra); color: var(--foreground-subtle);">ON THIS PAGE</span>
          <nav class="nav nav--vertical" style="margin-top: var(--space-sm);">
            <a class="nav-item" href="#s1" style="font-size: var(--size-narrator-small);">Section 1</a>
            <a class="nav-item" href="#s2" style="font-size: var(--size-narrator-small);">Section 2</a>
          </nav>
          <!-- Tags -->
          <div style="margin-top: var(--space-md); display: flex; flex-wrap: wrap; gap: var(--space-xs);">
            <span class="tag tag--signature">Topic</span>
            <span class="tag tag--default">Category</span>
          </div>
        </div>
      </div>
    </aside>
  </div>
</main>
```

## Recipe 4: Form Page

Narrow container, tabs, avatar, multi-section form with actions.

```html
<main style="max-width: var(--container-narrow); margin: 0 auto; padding: var(--space-2xl) var(--container-padding);">
  <h1 class="declaration declaration--h2">SETTINGS</h1>
  <p class="narrator narrator--small" style="color: var(--foreground-subtle); margin-bottom: var(--space-2xl);">Description.</p>

  <div class="tabs" role="tablist" style="margin-bottom: var(--space-xl);">
    <button class="tab is-active" role="tab">Profile</button>
    <button class="tab" role="tab">Security</button>
  </div>

  <div class="tab-panel is-active">
    <!-- Identity row: avatar + name -->
    <div style="display: flex; align-items: center; gap: var(--space-lg); margin-bottom: var(--space-xl);">
      <div class="avatar avatar--xl avatar--initials">JD</div>
      <div>
        <h3 class="declaration declaration--h5">USER NAME</h3>
        <p class="narrator narrator--whisper" style="color: var(--foreground-subtle);">user@email.com</p>
      </div>
    </div>

    <!-- Fieldset: technical label → fields -->
    <span class="technical technical--label" style="text-transform: uppercase; letter-spacing: var(--tracking-ultra); color: var(--foreground-subtle); display: block; margin-bottom: var(--space-md);">SECTION</span>

    <!-- 2-col for short related fields -->
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-md);">
      <div class="form-group">
        <label class="form-label">First Name</label>
        <input class="input" type="text">
      </div>
      <div class="form-group">
        <label class="form-label">Last Name</label>
        <input class="input" type="text">
      </div>
    </div>

    <!-- Full-width with help -->
    <div class="form-group">
      <label class="form-label">Email</label>
      <input class="input" type="email">
      <span class="form-help">Help text.</span>
    </div>

    <!-- Checkboxes -->
    <div style="display: flex; flex-direction: column; gap: var(--space-sm); margin-top: var(--space-md);">
      <label class="checkbox"><input type="checkbox" checked><span>Option A</span></label>
      <label class="checkbox"><input type="checkbox"><span>Option B</span></label>
    </div>

    <!-- Action bar: destructive left, confirm right -->
    <div style="display: flex; justify-content: space-between; border-top: 1px solid var(--border-subtle); padding-top: var(--space-lg); margin-top: var(--space-xl);">
      <button class="btn btn--ghost btn--critical">Delete</button>
      <div style="display: flex; gap: var(--space-sm);">
        <button class="btn btn--secondary">Cancel</button>
        <button class="btn btn--primary">Save</button>
      </div>
    </div>
  </div>
</main>
```

## Spacing Cheatsheet

| Between | Token | px |
|---------|-------|----|
| Label → heading | `--space-sm` | 12 |
| Heading → description | `--space-sm` | 12 |
| Description → content | `--space-xl` | 32 |
| Cards in grid | `--space-lg` | 24 |
| Form groups (stacked) | `--space-md` | 16 |
| Fieldset sections | `--space-xl` | 32 |
| Page sections (padding) | `--space-3xl` | 64 |
| Action bar top border gap | `--space-lg` | 24 |

## Voice-in-Context Table

| Position | Voice | Size | Extra |
|----------|-------|------|-------|
| Page title | Declaration h1-h2 | 48-36px | |
| Section label | Technical label | 10-11px | uppercase, ultra tracking, signature color |
| Section heading | Declaration h3-h4 | 28-22px | |
| Description | Narrator default | 16px | subtle color, max-width ~600px |
| Card title | Declaration h5 | 18px | |
| Card body | Narrator small-whisper | 14-13px | |
| Stat value | Declaration h3 | 28px | signature color |
| Stat label | Technical small | 12px | subtle color |
| Form label | Technical (form-label) | 14px | |
| Form input | Narrator default | 16px | |
| Form help/error | Narrator whisper | 13px | |
| Table header | Technical | 12px | uppercase, ultra tracking |
| Metadata | Narrator whisper + Technical small | 13px + 12px | label : value pair |
| Sidebar nav | Narrator small | 14px | |
| Breadcrumbs | Technical small | 12px | uppercase |

## Recipe 5: Frost Arena

Atmospheric section with tri-color gradient backdrop for showcasing cards.

```html
<section class="section-frost-bg" style="padding: var(--space-3xl) 0;">
  <div style="max-width: var(--container-max); margin: 0 auto; padding: 0 var(--container-padding);">
    <span class="technical technical--label" style="text-transform: uppercase; letter-spacing: var(--tracking-ultra); color: var(--signature-text);">SHOWCASE</span>
    <h2 class="declaration declaration--h2" style="margin-top: var(--space-sm);">SECTION TITLE</h2>

    <!-- Cards inside frost backdrop -->
    <div class="frost-backdrop" style="margin-top: var(--space-xl);">
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: var(--space-lg);">
        <div class="card card--elevated mat-frost-medium mat-frost-grain card-glow" style="position: relative;">
          <div class="card-glow__light"></div>
          <div class="card-glow__border"></div>
          <div class="card__body">
            <span class="chip chip--signature">Label</span>
            <h3 class="declaration declaration--h5" style="margin-top: var(--space-sm);">Card Title</h3>
            <p class="narrator narrator--small" style="margin-top: var(--space-xs);">Description text.</p>
          </div>
        </div>
        <!-- more cards... -->
      </div>
    </div>
  </div>
</section>
```

**Key patterns:** `.frost-backdrop` for tri-color gradient, `.card-glow` for mouse-tracking glow, `.chip` for accent labels, `.mat-frost-medium` + `.mat-frost-grain` material stack (gold standard).

## Micro-Patterns

```html
<!-- Status row: title + badge -->
<div style="display: flex; align-items: center; justify-content: space-between;">
  <span class="declaration declaration--h5">TITLE</span>
  <span class="badge badge--success badge--sm">Status</span>
</div>

<!-- Key-value pair -->
<div style="display: flex; justify-content: space-between; padding: var(--space-micro) 0;">
  <span class="narrator narrator--whisper" style="color: var(--foreground-subtle);">Label</span>
  <span class="technical technical--small">Value</span>
</div>

<!-- Toggle row -->
<div style="display: flex; align-items: center; justify-content: space-between; padding: var(--space-xs) 0;">
  <span class="narrator narrator--whisper">Setting</span>
  <label class="toggle toggle--sm"><div class="toggle__track"><div class="toggle__thumb"></div></div></label>
</div>

<!-- Action buttons: primary + secondary -->
<div style="display: flex; gap: var(--space-sm);">
  <button class="btn btn--primary">Save</button>
  <button class="btn btn--secondary">Cancel</button>
</div>

<!-- Tag cluster -->
<div style="display: flex; flex-wrap: wrap; gap: var(--space-xs);">
  <span class="tag tag--signature">Tag</span>
  <span class="tag tag--default">Tag</span>
</div>
```
