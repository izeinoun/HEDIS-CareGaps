# Penguin components — markup reference

Copy-paste HTML for each component. All styling comes from `penguin.css`; add only the
`active` / state classes noted. Framework-agnostic (shown as plain HTML; adapt to your
template engine).

## App shell

```html
<body>
  <div class="app">
    <aside class="sidebar">
      <div class="side-top">
        <a class="brand" href="/"><span class="wordmark">ACME</span> <span class="brand-dim">Reviewer</span></a>
        <button class="collapse-btn" id="collapse-btn" type="button">« <span class="lbl">Collapse</span></button>
      </div>
      <nav class="side-nav">
        <div class="nav-section">Review</div>
        <a class="nav-item active" href="/worklist">
          <svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><circle cx="3.5" cy="6" r="1.2"/><circle cx="3.5" cy="12" r="1.2"/><circle cx="3.5" cy="18" r="1.2"/></svg>
          <span class="lbl">Worklist</span><b class="nav-count">79</b>
        </a>
        <a class="nav-item" href="/queue">
          <svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5"/></svg>
          <span class="lbl">QA queue</span><b class="nav-count">12</b>
        </a>
        <div class="nav-section">Reference</div>
        <a class="nav-item" href="/rules">
          <svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16v4H4z"/><path d="M4 12h10"/><path d="M4 17h7"/></svg>
          <span class="lbl">Rules</span>
        </a>
      </nav>
      <div class="side-foot">
        <!-- context controls (user picker, environment pill, etc.) -->
        <span class="provider-pill on no-collapse"><i class="dot"></i><span>Signed in</span></span>
      </div>
    </aside>
    <div class="content">
      <main class="main"><!-- page --></main>
      <footer class="foot"><p class="muted xsmall">© ACME</p></footer>
    </div>
  </div>
  <script>
    // collapse toggle (persisted)
    const cb = document.getElementById('collapse-btn');
    if (localStorage.getItem('side') === '1') document.body.classList.add('side-collapsed');
    cb.addEventListener('click', () => {
      const on = document.body.classList.toggle('side-collapsed');
      localStorage.setItem('side', on ? '1' : '0');
    });
  </script>
</body>
```

- Icons: inline 24×24 SVG, `stroke="currentColor"`, ~17px rendered. Reuse a small line-icon set.
- Set `active` on the current route's `.nav-item`. `.nav-count` is optional.

## Page header

```html
<div class="crumbs"><a href="/worklist">Worklist</a> / CLM-24571</div>
<div class="page-head">
  <div>
    <h1>Worklist</h1>
    <p class="muted small">Items requiring disposition, ranked by deadline then risk.</p>
  </div>
  <div class="page-head-actions">
    <button class="btn">Filter</button>
    <a class="btn primary" href="/new">+ New</a>
  </div>
</div>
```

## Summary header card (record detail)

```html
<div class="summary-card">
  <div class="sc-top">
    <div>
      <div class="sc-title">
        <span class="sc-id">CLM-24571</span>
        <span class="pill tint-info">In review</span>
        <span class="pill pill-outline-danger">4 days overdue</span>
      </div>
      <p class="sc-meta">Ellis Ndiaye · CarePoint · Humana · Professional claim · service Mar 10, 2026</p>
    </div>
    <div class="head-actions">
      <a class="btn" href="#">History ↗</a>
      <button class="btn primary">Work this item</button>
    </div>
  </div>
  <div class="sc-why"><b>Why it's ranked here:</b> the filing window closed four days ago…</div>
</div>
```

## Lifecycle stepper

Render one `.lc-step` per stage; class is `done` (past), `current` (active), or omitted
(future). Put a `.lc-conn` between steps; give it `done` when the step before it is done.

```html
<div class="lifecycle">
  <div class="lc-step done"><div class="lc-num">✓</div>
    <div class="lc-text"><span class="lc-label">Received</span><span class="lc-sub">intake validated</span></div></div>
  <div class="lc-conn done"></div>
  <div class="lc-step done"><div class="lc-num">✓</div>
    <div class="lc-text"><span class="lc-label">Checked</span><span class="lc-sub">1 finding</span></div></div>
  <div class="lc-conn done"></div>
  <div class="lc-step current"><div class="lc-num">3</div>
    <div class="lc-text"><span class="lc-label">Reviewed</span><span class="lc-sub">items open</span></div></div>
  <div class="lc-conn"></div>
  <div class="lc-step"><div class="lc-num">4</div>
    <div class="lc-text"><span class="lc-label">Approved</span></div></div>
  <div class="lc-conn"></div>
  <div class="lc-step"><div class="lc-num">5</div>
    <div class="lc-text"><span class="lc-label">Outcome</span></div></div>
</div>
```

## Data table

```html
<table class="grid">
  <thead><tr><th>Item</th><th>Client</th><th>State</th><th>Amount</th><th>Deadline</th><th></th></tr></thead>
  <tbody>
    <tr>
      <td><b>CLM-24571</b><div class="muted small">DME · CGM</div></td>
      <td>CarePoint</td>
      <td><span class="badge tint-danger">Blocked</span></td>
      <td>$2,940</td>
      <td><span class="tint-warn" style="padding:2px 8px;border-radius:6px;font-weight:700">4 days overdue</span></td>
      <td><a class="btn small" href="#">Open →</a></td>
    </tr>
  </tbody>
</table>
```

Add `class="grid compact"` for a denser table (used in analytics/sub-tables).

## Chips, badges & pills

```html
<span class="chip">neutral</span>
<span class="chip tint-ok">passed</span>
<span class="badge tint-warn">out of window</span>
<span class="pill tint-info">In review</span>
<span class="pill pill-outline-danger">overdue</span>
```

Pick the tint by meaning (see `tokens.md`): ok=success, danger=blocked, warn=deadline/
caveat, info=neutral status, purple=taxonomy/actor, brand=primary/open, muted=inactive.

## Buttons

```html
<button class="btn">Secondary</button>
<button class="btn primary">Primary</button>
<button class="btn small">Small</button>
<a class="btn ghost">Text link →</a>
```

## Notices

```html
<div class="notice warn">Timing check — value present but may not count.</div>
<div class="notice ok">All checks passed.</div>
<div class="notice brand">Action required before sign-off.</div>
```

## KPI row

```html
<div class="kpis">
  <div class="kpi"><div class="kpi-v">91%</div><div class="kpi-l">agreement</div></div>
  <div class="kpi"><div class="kpi-v">50%</div><div class="kpi-l">override rate</div></div>
</div>
```

## Activity timeline (newest first)

```html
<div class="timeline">
  <div class="tl-row actor-reviewer">
    <div class="tl-when">2026-09-10 22:49 <span class="muted xsmall">UTC</span></div>
    <div class="tl-dot"></div>
    <div class="tl-body">
      <span class="tl-actor tint-brand">reviewer</span>
      <span class="tl-action">accepted</span>
      <div class="muted small">final = approved <span class="tl-by">— Dana Cole</span></div>
    </div>
  </div>
</div>
```

## Form field

```html
<label class="field"><span>Member DOB</span><input type="date"></label>
<div class="form-actions"><button class="btn">Cancel</button><button class="btn primary">Save</button></div>
```
