# UI direction — Rules admin screen

How an application should surface a rules pack. The pack (`rules-pack-schema.md`) is
the single source of truth for this screen — every field below reads straight from
it, so the screen needs no other data source. **The screen is read-only:** a pack is
*generated* from a published spec by the `hedis-spec-to-rules` skill and regenerated
when a new spec is published — it is never hand-edited in the UI (editing would break
traceability to the source document).

## Purpose

A quality/compliance admin views the abstraction rules currently loaded for a
measurement year: which measures are covered, and for each, the data elements a
reviewer must find and the exclusions that retire a member. It answers "what is the
system looking for, and which published spec does it come from."

## Layout

**1. Pack header (the version + date banner).** From `source`:
- **Version** — `measurement_year` (e.g. "MY2027"). This is the version users reason
  about; packs are one-per-year and never merged, so if several are loaded, offer a
  **year selector** and make the active year obvious.
- **Build date** — `extracted_at` (when this pack was generated from the spec).
- **Contract** — `schema_version` (the pack format version; secondary).
- Also show `document_title`, `publisher`, `pages`, and the standing `disclaimer`
  ("derived from published specs… not a certified compliance engine") — keep the
  disclaimer visible, since these are derived rules, not published values.
- **View source** (a plus) — if `document_url` is present, a link to the original
  NCQA spec (or the stored uploaded PDF). Hide the control when it is absent.

**2. Measures list.** One row per entry in `measures[]`:
- `measure_id`, `measure_name`, `hybrid` (chart-review allowed vs admin-only),
  counts of `data_elements` and `exclusions`, and `source_pages` (traceability).
- Row expands / drills into the measure detail.

**3. Measure detail.** For the selected measure:
- **Population & timing** (context, prose): `eligible_population`,
  `measurement_period`, `numerator`.
- **Data elements** (`data_elements[]`) — a table: `label`, `type`, `required`,
  `unit`, `options`, `timing`, `compliance_hint`, `keywords`. Mark `required` rows.
- **Exclusions** (`exclusions[]`) — per rule: `label`, `scope` (required/optional),
  `value_sets` (the named NCQA sets), any inline `codes`, `keywords`, `timing`,
  `applies_when`, and the flags that change how a hit is read — `compound`,
  `source_hint`, `threshold`. Surface `note`.

**4. Universal exclusions.** Render `universal_exclusions[]` in its own section
(hospice, palliative, advanced-illness+frailty) — these apply across measures.

## Search

Full-text search across the pack, matching and jumping to:
- measure `measure_id` / `measure_name`,
- exclusion `label` and `value_sets` names (a common lookup: "which measures exclude
  Dialysis?"),
- data-element `label` / `key`,
- `keywords` anywhere.
Useful filters: by measurement year, hybrid vs admin-only, exclusion scope
(required/optional), and "has inline codes" vs "value-set name only".

## Upload → generate (a plus, and the logical intake)

Because a pack is generated, not authored, give the admin an **upload** control:

1. Admin uploads the **NCQA spec PDF** (e.g. "HEDIS MY2027 Volume 2").
2. The app runs the `hedis-spec-to-rules` skill on it to build the pack, then
   `validate_pack.py` to check structure.
3. Store the resulting pack keyed by `measurement_year`, set `document_url` to the
   stored PDF (or the NCQA URL), and display it via this screen.
4. Report what was captured and, honestly, anything partial (see the skill's
   "Report coverage honestly" step) — surface that in the upload result, not buried.

Never merge measures across years — a new year's upload is a new pack, selectable via
the year selector, not a mutation of an existing one.

## House UI style guides (optional — use if present, ignore if not)

If this environment provides the Gwen/Penguin `ui-*` style guides, follow them for
this screen; they define the house look and interactions. If they are absent, the
direction above stands — **never block or fail for their absence, and never copy
their content into the pack.** Most relevant here:
- `ui-patterns` and `ui-progressive-disclosure` — the measures list → measure-detail
  drill-down (elements/exclusions revealed on demand).
- `ui-split-panel` — measures list on one side, selected-measure detail on the other.
- `ui-tooltip-preview` — hover a value-set name or an inline code to preview it.
- `ui-inline-citations` — link a measure/rule to its `source_pages` and the
  `source.document_url`.

Other `ui-*` guides apply as the screen grows; reference them by name only.

## Read-only, and why

The UI shows rules; it does not let users edit thresholds, value sets, or keywords.
Corrections happen by fixing the source or regenerating from a corrected spec, so the
pack always traces to a published document. This mirrors the skill's guardrail that
every rule is traceable to a spec page and nothing is invented in the UI.
