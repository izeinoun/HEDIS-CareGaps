---
name: penguin-style
description: >-
  The Penguin visual style for internal review/operations web apps — a light,
  operational design system: white surfaces, a single hot-pink accent, a left
  sidebar app shell, clean data tables, a lifecycle stepper, a summary header card,
  KPI rows, and an activity timeline. Ships a drop-in stylesheet (`penguin.css`), a
  design-token reference, and copy-paste component markup. Use when building or
  restyling a server-rendered or SPA web UI that should look like the Penguin
  product family (reviewer worklists, case/record detail pages, admin screens).
---

# Penguin style

A light, calm, operational look for review-and-approval tools. It is deliberately
restrained: **white surfaces, one accent (hot pink), state carried by small tinted
badges, and generous whitespace.** The frame is a **left sidebar + content** shell;
records get a **summary header card** and a **lifecycle stepper** that shows where the
record sits in its process.

## When to use

- Building a new internal web app in this product family (reviewer worklists, case
  detail, QA queues, admin/reference screens).
- Restyling an existing UI to the Penguin look.
- You want a consistent token set + components rather than ad-hoc CSS.

Not for: marketing pages, data-viz-heavy dashboards, or anything that wants a dark or
high-chroma theme. This system is monochrome-plus-one-accent by design.

## Files in this skill

- **`penguin.css`** — the drop-in stylesheet: tokens, the app shell, and every core
  component. Include it and (optionally) Open Sans; nothing else is required.
- **`tokens.md`** — the color/space/shape tokens and the **semantic tint recipe** for
  adding your own domain status classes.
- **`components.md`** — copy-paste HTML for each component (sidebar, page header, cards,
  data table, chips/badges, buttons, summary card, lifecycle stepper, KPI row, timeline).
- **`example-page.html`** — a self-contained page wiring the shell + a few components,
  so you can see it render immediately.

## How to apply

1. Serve `penguin.css` and load it after a CSS reset. Add Open Sans (400/600/700/800):
   `<link href="https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">`.
2. Wrap the page in the **app shell** (`.app > .sidebar + .content > .main`). Copy the
   sidebar markup from `components.md`; set `.nav-item.active` on the current route and
   add optional `.nav-count` badges.
3. Build pages from the components in `components.md`. For record detail pages, lead with
   a **`.summary-card`** then a **`.lifecycle`** stepper.
4. For domain state (statuses, outcomes, roles), **don't invent new colors** — attach a
   tint utility (`tint-ok`, `tint-warn`, `tint-danger`, `tint-brand`, `tint-info`,
   `tint-purple`, `tint-muted`) to a `.chip`/`.badge`, or map a domain class to the tint
   recipe in `tokens.md`.

## Design principles

- **Light and quiet.** `--bg` is a near-white gray; content sits on white `--surface`
  cards with a hairline `--line` border and a barely-there shadow. Never fill large areas
  with the accent.
- **One accent.** Hot pink (`--brand`) is for the active nav item, primary buttons, the
  current lifecycle step, links, and small emphasis — nothing else. If two things are
  pink, ask whether one should be neutral.
- **State = a small tinted badge**, never body text color. Every semantic color comes as
  a trio: `--x` (solid, for filled dots/steps), `--x-ink` (text on white), `--x-tint`
  (badge background). Badges are `tint-bg + ink-text + transparent border`.
- **Type.** Open Sans. Weights: 400 body, 600 controls/labels, 700 headings, 800 for the
  big numbers (summary id, KPI value, stat). Section/eyebrow labels are 10px uppercase,
  `.08em` tracking, `--muted`.
- **Restraint over decoration.** No gradients on surfaces (the `--grad` exists only for
  thin progress fills), no heavy shadows, no motion beyond hover/active feedback.

## The shell

```
.app  (flex row)
├─ .sidebar  (sticky, full height, white, right border)
│  ├─ .side-top   → brand + « Collapse button
│  ├─ .side-nav   → .nav-section headers + .nav-item rows (icon · label · .nav-count)
│  └─ .side-foot  → user/context controls
└─ .content
   ├─ .main   → page content (max-width 1260, centered)
   └─ .foot   → provenance / colophon
```

Collapse toggles `body.side-collapsed` (persist it); the sidebar shrinks to icons. The
`@media(max-width:1000px)` rule auto-collapses on narrow screens. Active route:
`class="nav-item active"` → pink pill + left accent bar + pink count.

## Core components (see `components.md`)

Summary header card · lifecycle stepper · data table (`.grid`) · cards (`.card`) ·
chips/badges with tint utilities · buttons (`.btn`, `.btn.primary`, `.btn.ghost`) ·
notices (`.notice.ok/.warn/.brand`) · KPI row (`.kpis`) · activity timeline (`.timeline`)
· forms (`.field`).

### Lifecycle stepper

A horizontal row of numbered steps for a record's process (e.g. Received → Reviewed →
Approved → Delivered → Outcome). Each `.lc-step` is `done` (green check + green connector),
`current` (pink outline + pink label), or neither (gray). Keep it to 4–7 steps with short
labels and an optional one-line `.lc-sub`. Compute the stage from the record's state and
stamp the class per step.

## Do / Don't

- **Do** keep one accent, tint badges for state, and lead detail pages with the summary
  card + stepper.
- **Do** add domain classes via the tint recipe so new statuses match automatically.
- **Don't** introduce a second bright color, fill cards/headers with the accent, use dark
  surfaces, or color body text to signal state (use a badge).
- **Don't** hardcode hex values in components — reference the tokens.

## Adapting to a new domain

Define your status/outcome vocabulary, then map each value to one tint. Example:

```css
.status-open       { } /* use class="chip tint-brand" or map here */
.status-approved   { background:var(--ok-tint);    color:var(--ok-ink); }
.status-blocked    { background:var(--danger-tint); color:var(--danger-ink); }
.status-in_review  { background:var(--info-tint);   color:var(--info-ink); }
```

That is the whole extension model: the framework is generic; your domain adds a thin
layer of status→tint mappings and the page markup.
