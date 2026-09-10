# Penguin design tokens

All values are CSS custom properties on `:root` in `penguin.css`. Reference the tokens;
never hardcode hex in components.

## Surfaces & ink

| Token | Value | Use |
|---|---|---|
| `--bg` | `#F4F5F7` | app background (behind cards) |
| `--surface` | `#FFFFFF` | cards, tables, sidebar |
| `--surface2` | `#F5F6F8` | table headers, insets, hover, neutral chips |
| `--inset` | `#FAFBFC` | table row hover |
| `--fg` | `#1B2431` | primary text (near-black navy) |
| `--fg-soft` | `#3B4453` | secondary text, controls |
| `--muted` | `#6A7381` | labels, meta, captions |
| `--line` | `#E7EAEE` | hairline borders |
| `--line-strong` | `#D7DCE3` | input borders, dividers |

## Brand (the one accent)

| Token | Value | Use |
|---|---|---|
| `--brand` | `#E1147F` | active nav, primary buttons, current step, filled dots |
| `--brand-ink` | `#C10E6E` | pink text on white (links, active labels) |
| `--brand-tint` | `#FCE7F1` | pink badge/active-pill background |
| `--brand2` | `#8A4FE6` | secondary accent (rare — e.g. a distinct actor/category) |
| `--grad` | pink→purple | **thin fills only** (progress/confidence bars), never surfaces |

## Semantic trio pattern

Every state color comes as three tokens: **solid** (`--x`), **ink** (`--x-ink`, text on
white), **tint** (`--x-tint`, badge background).

| Meaning | solid | ink | tint |
|---|---|---|---|
| success / done | `--ok` `#12885A` | `--ok-ink` `#0C6B46` | `--ok-tint` `#E7F5EE` |
| danger / blocked | `--danger` `#D24545` | `--danger-ink` `#B23636` | `--danger-tint` `#FBEAEA` |
| warning / timing | `--warn` `#B5730B` | `--warn-ink` `#8F5A06` | `--warn-tint` `#FBF1E1` |
| info / in-review | `--info` `#2A62C4` | `--info-ink` `#234FA0` | `--info-tint` `#EAF0FB` |
| category / actor | — | `--purple-ink` `#6E3FD1` | `--purple-tint` `#F0EBFC` |

## Shape & depth

| Token | Value |
|---|---|
| `--radius` | `12px` (cards, tables, notices) |
| `--radius-sm` | `8px` (buttons, inputs, small chips-of-boxes) |
| `--shadow` | `0 1px 2px …/.04, 0 2px 6px …/.05` (cards) |
| `--shadow-lg` | `0 6px 22px …/.09` (popovers/modals) |
| `--side-w` | `238px` (sidebar width) |

## Type scale

Open Sans. `h1` 23/700 · `h2` 18/700 · `h3` 16/700 · eyebrow/`h4` 10px uppercase
`.08em`/700 muted · body 15/400 · small 12.5 · xsmall 10.5. Big numbers (summary id, KPI,
stat) use **800** with `-0.02em` tracking.

## The tint recipe (adding a domain status class)

A state badge is always: **tint background · ink text · transparent border.** Either use a
utility on a `.chip`/`.badge`:

```html
<span class="chip tint-ok">gap closed</span>
<span class="badge tint-warn">out of window</span>
```

…or map a domain class to the trio:

```css
.final-gap_closed { background:var(--ok-tint);    color:var(--ok-ink); }
.final-gap_open   { background:var(--brand-tint);  color:var(--brand-ink); }
.final-excluded   { background:var(--purple-tint); color:var(--purple-ink); }
```

Available utilities: `tint-brand`, `tint-ok`, `tint-danger`, `tint-warn`, `tint-info`,
`tint-purple`, `tint-muted`. Pick by **meaning**, not by hue: success→ok, blocked/error→
danger, deadline/caveat→warn, neutral status→info, taxonomy/actor→purple, inactive→muted,
the primary/open state→brand.
