---
name: hedis-rules-to-findings
description: >-
  Locate HEDIS measure data in a medical record. Given a HEDIS "rules pack"
  (produced by `hedis-spec-to-rules`) and the extracted text of a chart/medical
  document (e.g. from Claude, Textract, or an OCR/PDF layer), find and propose the
  measure's structured data elements and candidate denominator exclusions — each
  with a verbatim evidence quote, a source anchor (page + character range), and a
  confidence — and never decide compliance. Use when locating measure-specific
  data in chart or medical-record text against a set of HEDIS rules.
---

# HEDIS rules pack → chart findings

Read a **rules pack** and use it as the instructions for what to look for in one
medical record's **extracted text**, then emit anchored, proposal-only findings.

This is the shared chart-analysis engine for the two ways a plan closes an open
care gap by finding evidence in a chart:

- **Chart chase** — the plan *pulls* records for open members and reviews them
  (`--workflow chase`, the default).
- **Gap closure** — a provider *submits* a chart in response to a gap report; the
  plan validates and reviews it (`--workflow gap_closure`).

Both run the same extraction/exclusion/anchoring; gap closure adds a
provider-submission **validation gate** and a proposed **gap outcome** (below). The
unit of work in both is a **case**, not a bare measure: a member with assigned
measures and their administrative state. Supply that case (see Inputs) and the skill
chases only the open measures, gates exclusions on the member's age, and skips
exclusions the plan already applied. Without a case it still runs plain
measure-plus-chart. The work queue, assignment, over-read, QA, and audit trail are
the application's responsibility, not this skill's.

Two passes with deliberately different trust models: the model extracts the
structured **data elements** (where judgement is genuinely required), while
**exclusions** are matched deterministically against the pack's keywords/codes so
every proposed exclusion traces to a named value set (no model judgement, so a hit
is always explainable). Everything is a proposal a human rules on — the skill never
determines numerator status, compliance, or final exclusion application.

**Shared contract.** The rules pack this skill reads MUST conform to
`rules-pack-schema.md` (`schema_version` 1.0) — the exact contract the
producer skill `hedis-spec-to-rules` emits (both skills bundle an identical copy
of this file). Before processing a pack, confirm its `schema_version` matches; if
it does not, stop and reconcile the schemas rather than guessing at fields. This
shared file is what lets the two skills complement each other.

## Inputs

1. **Rules pack** — JSON from `hedis-spec-to-rules` (see
   `rules-pack-input.md` for the fields consumed). Confirm the pack's
   `measurement_year` is the one intended; codes are not stable across years.
2. **Extracted chart text** — plain text of the medical record. Ideally with a
   **page-offset map**: a JSON array of `{page, start, end}` giving the character
   range of each page in the text, so findings can report a page number. If you
   only have per-page text, build offsets by concatenating pages and recording
   each page's start/end (the bundled script can do this from a pages JSON).
3. **Target measure(s)** — the `measure_id`(s) to abstract. If the case is for one
   measure, run that measure targeted; a "broad" pass can additionally scan for
   evidence of other measures in the pack.
4. **Case (optional; recommended for chart chase, required for gap closure)** — the
   pursuit-list record for one member (see `case-input.md`). It carries the member
   (`age` for the exclusion age-gate; `name` + `dob` for gap-closure member match),
   the `measurement_year`, the `assigned_measures`, and per-measure `measure_state`:
   `admin_status` (gap_closed / gap / open / excluded), `admin_exclusions_applied`,
   and `last_dos`. Given a case, **chase only the measures still open** — skip any
   the case marks gap_closed or already excluded (override with `--force` only when
   deliberately re-reviewing). The member's age turns the exclusion age-gate from
   surfaced into evaluated, and an exclusion already applied administratively is
   flagged rather than re-proposed. The case is a member-scoped input to *this*
   skill — it is never part of the rules pack, which stays member-agnostic.

## The two passes

### Pass 1 — Data elements (model extraction)

For the target measure, take its `data_elements[]` from the pack and extract each
from the chart text. Use exactly this discipline:

- Ask only for the measure's defined fields — `key`, `type`, `unit`, `label`,
  `timing`, `compliance_hint`, `options`. Do not invent fields.
- For every element return: the **value**, the **verbatim sentence** from the
  record supporting it (copied exactly, so it can be located), and a **confidence**
  0–1.
- If an element is **not documented, return value `null` and confidence `0`. Never
  guess or infer a value.**
- **Do not decide whether the member meets the measure.** Report only what the
  record says. `compliance_hint` is context for a human, not a rule to apply.
- Respect `timing`: note when a documented value falls outside the measure's
  window, but still report it (flagging out-of-window is the human's call).

Build one line per element from the pack — `key (type, unit): label — compliance_hint`
plus `Options: …` when enumerated — and use a prompt of this shape:

```
You are assisting a HEDIS chart abstractor. Extract ONLY the data elements below
from the medical record for the measure <MEASURE_ID> (<measure_name>).

DATA ELEMENTS TO FIND:
<one line per element as above>

RULES:
- For each element, return the value and the VERBATIM sentence from the record that supports it.
- The evidence must be copied exactly from the record so it can be located in the source.
- If an element is not documented, return it with value null and confidence 0. Do not guess.
- Do not decide whether the member meets the measure. Only report what the record says.

MEDICAL RECORD:
<chart text — cap at ~18000 chars per call; page through longer records>

Return findings where each has: measure_id, element_key, value, evidence_text, confidence (0-1).
```

Write the raw element findings to a JSON file, one object per element:
`[{ "element_key": "...", "value": ..., "evidence_text": "...", "confidence": 0.0 }]`

### Pass 2 — Exclusions (deterministic, grounded)

Do **not** ask the model to decide exclusions. Instead run the bundled scanner,
which matches each exclusion's `keywords` (and inline `code` descriptions) against
the chart text on whole-word boundaries, skips negated mentions ("no evidence of
hospice"), and returns each hit with its value-set name, the matched term, an
evidence window, and a source anchor. This is what keeps a proposed exclusion
traceable to a published value set.

Each hit also carries a **`disposition`** so a single keyword match is never
mistaken for a settled exclusion:
- `confirm_via_administrative_source` — an `"administrative"` criterion (a file
  value chart text cannot settle); routed to the enrollment/claims file, not proposed.
- `partial_needs_components` — a `compound` criterion needing 2+ distinct findings
  (advanced illness *and* frailty; bilateral *or* two unilateral mastectomy). Read
  `note` for the full requirement.
- `partial_needs_count` — a `threshold` criterion (one concept needed N times); the
  count is the reviewer's to confirm.
- `proposed` — an ordinary chart-findable candidate.

Two more things travel on every exclusion hit, both surfaced for the reviewer and
**not enforced by the date-blind scan**: `timing` (the window evidence must fall in)
and `origin` (`measure` vs `universal` — a `universal` hit must be confirmed against
the specific measure's exclusion list, since some universal exclusions apply only to
a subset of measures). Everything is surfaced — nothing is silently dropped.

## Assemble with the bundled script

Run the anchoring/exclusion tool — it anchors your Pass-1 quotes to page +
character offsets, downgrades any quote it cannot find in the text (an unlocatable
quote is unverified, not evidence), runs the deterministic exclusion scan, and
emits the final findings object with a summary and the standing disclaimer:

```
python anchor_findings.py \
  --pack <rules-pack.json> \
  --measure CBP \
  --text <chart.txt> \
  --elements <pass1-elements.json> \
  [--offsets <page-offsets.json>] \
  [--pages <pages.json>] \
  [--case <case.json>] [--force] \
  [--workflow chase|gap_closure] \
  [--mode targeted|broad] \
  [--broad-scan] \
  --out <findings.json>
```

- `--broad-scan` runs a **deterministic cross-measure pass**: one retrieved chart is
  screened against *every* measure in the pack (the targeted `--measure` is excluded),
  reporting which measures the chart shows keyword evidence for plus each measure's
  exclusion hits — the "read once, review many" primitive. It is a per-chart candidate
  screen, never a rate, and it does **not** extract element values (run the targeted
  Pass-1 for a measure the scan flags). Output carries `mode: "broad"` and
  `broad_scan[]` (per measure: `element_signals[]` with anchors, `required_signal` /
  `total_signal`, `exclusions[]`). Differs from `--mode broad`, which anchors
  *model-supplied* cross-measure findings (`--cross`).
- `--offsets` takes a `[{page,start,end}]` map; alternatively `--pages` takes a
  `["page 1 text", "page 2 text", ...]` array and the script derives offsets and
  the concatenated text for you (use one or the other).
- If you omit `--elements`, the script still runs the exclusion scan and returns
  an empty elements list — useful for an exclusions-only pass.
- `--case` supplies the chart-chase context. If the case marks this measure
  administratively resolved (gap_closed, or a required exclusion already applied),
  the script returns a `skipped_admin_resolved` result instead of chasing — pass
  `--force` to review it anyway. For a whole member, invoke once per open measure in
  the case's `assigned_measures` (a chart pulled once is reviewed for every open
  gap).

## Gap closure (`--workflow gap_closure`)

Gap closure is the same review as chart chase with two additions, because here a
**provider submits** the chart rather than the plan pulling it:

1. **Submission validation gate** (GC 2.1/2.2). Before extracting, the script checks
   that the chart belongs to the case: the member's **name and DOB** appear in it,
   the measure's own vocabulary appears (alignment), and the document has real,
   dated content. This is deterministic and reuses the pack. A **member-identity
   mismatch is a hard stop** — neither name nor DOB found returns a
   `validation_failed` record and *no extraction runs* (a wrong-member chart must
   not be abstracted). Weak measure alignment, low legibility, or a missing date are
   surfaced as `validation.warnings`, not blocks — extraction still runs.

2. **Proposed gap outcome** (GC 4.1/4.4). After extraction, the skill reconciles the
   findings against the case's `admin_status` and proposes one outcome:
   `closable_on_documentation` (all required elements documented — the service is
   evidenced), `partial_documentation` (some required elements still missing),
   `exclusion_candidate` (no numerator evidence but a candidate exclusion found),
   `previously_closed` (already gap_closed per admin), or `no_impact_to_gap`
   (nothing new). It is a **proposal for the reviewer**, never a determination.

Deliberately **not** included: automated **code selection** (ICD/CPT/LOINC — GC 4.3)
and any compliance/numerator determination. The skill surfaces value-set *names* and
any codes the pack prints, but never selects codes — that keeps it a proposal tool,
not the abstraction record of truth.

## Output

A findings object (see `findings-schema.md`) containing:
- `workflow` — `chase` or `gap_closure`.
- `validation` / `gap_outcome` — populated in gap-closure workflow (see above); `null`
  in chase. A failed member match returns a short `status: "validation_failed"` record
  with the `validation` report and no elements/exclusions.
- `substantiation` — emitted for **both** workflows: `valid_data_present`
  (true/false/null — is the substantiating data for this measure present, CC 2.4) plus a
  recommended `next_step` (`ready_for_manual_entry` / `follow_up_with_provider` /
  `review_required`, CC 2.5). A proposal the reviewer confirms; the skill never enters data
  or contacts a provider.
- `case_context` — when a case was supplied: member id/age, `admin_status`,
  `admin_exclusions_applied`, `last_dos`, and `chased`. `null` otherwise. (When a
  measure is skipped as admin-resolved, the object is instead a small
  `status: "skipped_admin_resolved"` record with a `reason` and this context.)
- `elements[]` — each with `ai_value`, `evidence_text`, `evidence_anchored`,
  `ai_confidence`, `status` (`proposed`/`not_found`), and `page_number` /
  `char_start` / `char_end`.
- `exclusions[]` — deterministic hits with `rule_key`, `value_set_name`,
  `matched_term`, `scope`, `origin`, `timing`, `disposition`, `age_check`,
  `already_applied`, evidence, and anchor.
- `summary` — counts (elements found, required missing, exclusions proposed,
  exclusions already applied, mean confidence, anchored-evidence count).
- `measure_result` — the completed measure result the reviewer accepts or rejects
  (a `proposed_status` plus a `reviewer_decision` that starts `pending`). Always
  present. See "Consuming the findings" below.
- `audit_log` — an append-only trail seeded with the system/AI events (analysis run,
  each proposal, the proposed result), preserving each `ai_value` baseline. Always
  present; the app appends reviewer actions.
- `disclaimer` — the fixed "AI proposals only; the reviewer decides" statement.

## Consuming the findings (reviewer UI)

The output is built to drive a human-in-the-loop review screen:
- **Highlighting** — every element and exclusion carries a source anchor
  (`page_number` + `char_start`/`char_end`); the UI renders these as clickable
  highlights so the reviewer lands on the sentence instead of scrolling the chart.
- **Confirm / modify / reject (per finding)** — each finding is a proposal with
  `ai_value` / `ai_confidence` and, for exclusions, a `disposition`; the UI lets the
  reviewer accept, edit, or reject, and should keep the original AI value for the
  AI-vs-final audit the application records.
- **Accept / reject the completed measure result** — separate from the per-finding
  controls, the UI must let the reviewer sign off the *whole* measure at
  `measure_result`: accept the `proposed_status`, or reject/override it and record a
  `final_status` and `note`. The skill emits `reviewer_decision: "pending"`; the app
  writes `accepted` / `rejected` / `modified` (plus `decided_by` / `decided_at`).
  Record `final_status` from the canonical set — `gap_closed` / `gap_open` /
  `exclusion_applied` / `needs_more_info` (see findings-schema.md → Review & audit
  fields) — so the sign-off is reportable and consistent across measures and years.
  Without this, a case can be fully reviewed finding-by-finding yet never actually
  signed off as a completed result.
- **Per-case audit log view** — surface `audit_log` as a chronological trail inside
  the case: who/what proposed each value, and every reviewer accept/reject/modify,
  including the measure-result sign-off. A case has several measures, so the view
  concatenates the `audit_log` of each measure analysed for the member, ordered by
  time. The log is append-only and keeps the AI `ai_value` beside the final value.
- **Gate + outcome (gap closure)** — surface the `validation` verdict/warnings before
  the findings, and the proposed `gap_outcome` as a suggestion the reviewer confirms —
  never as a closed gap. A `validation_failed` result should show the mismatch and
  offer no extraction to accept.
- **Read-once, review-many** — in a broad pass, show `cross_measure` hits so one
  retrieved chart closes every open gap it can.

The queue, assignment, over-read, QA capture, and audit trail are the application's
responsibility, not this skill's.

**House UI style guides (optional — use if present, ignore if not).** If this
environment provides the Gwen/Penguin `ui-*` style guides, follow them for this
screen; they define the house look and interactions and map directly onto what the
findings carry. If they are absent, the generic direction above stands — **never
block or fail for their absence, and never copy their content into a finding.** By
concern:
- Chart-vs-findings layout & navigation: `ui-split-panel`, `ui-minimap`,
  `ui-progressive-disclosure`, `ui-patterns`
- Evidence anchors → highlights / pins / citations: `ui-evidence-patterns`,
  `ui-evidence-pins`, `ui-inline-citations`, `ui-connected-lines`, `ui-xray-mode`,
  `ui-bounding-box`, `ui-tooltip-preview`
- `ai_confidence` display: `ui-confidence-heatmap`
- Image/clip evidence (scanned charts): `ui-clip-mosaic`, `ui-clip-zoom`,
  `ui-clip-comparison`, `ui-clip-accordion`, `ui-clip-badges`

## Guardrails (non-negotiable)

- **Inert without input.** No rules pack → stop and say what is needed; never
  produce findings from measure knowledge you happen to remember. Producing
  findings from memory is the primary failure mode this design exists to prevent —
  and it feels helpful in the moment, which is exactly why it is dangerous. Before
  processing, confirm the pack's `schema_version` matches and the target
  `measure_id` is present in the pack; if either fails, say precisely what is
  missing and stop rather than guessing.
- **Proposals only.** Never state a member is compliant/non-compliant, never apply
  an exclusion, never assert numerator status.
- **No aggregate figures.** Never emit a rate, percentage, or count of
  excluded/gap_closed members — not as an aside, not even when asked directly. It is
  a per-chart evidence tool. If asked for a rate, explain why it does not produce
  one and offer the per-chart findings instead.
- **Evidence or nothing.** No value without a verbatim quote; a quote that can't be
  located in the text is downgraded and marked unanchored.
- **No fabrication.** Absent → `null` / `not_found`, explicitly. A value that *is*
  documented but falls outside the timing window is different — report it with
  `in_window: false`, never collapse "absent" and "present-but-doesn't-count" into
  one. Never assert a code belongs to a value set you have not seen; the scanner
  matches only terms the pack actually carries (keywords / printed codes).
- **Traceability.** Every finding carries a source anchor and, for exclusions, the
  named value set it came from.
- **Chase what's open, not what's closed.** When a case is supplied, do not chase a
  measure it marks gap_closed or already-excluded (that member/measure is resolved by
  admin data); re-review only on an explicit `--force`. Never treat the case's
  administrative state as *your* determination — it is the starting context, and the
  chart evidence you surface remains a proposal for the reviewer.
- **Case gates inform, they don't drop.** `age_check`, `timing`, and `already_applied`
  annotate a finding so the reviewer can judge; an `out_of_band` or already-applied
  hit is still surfaced, never silently removed.
- **Wrong-member charts are not abstracted.** In gap closure, a member-identity
  mismatch (neither name nor DOB found) hard-stops before extraction — never extract
  clinical data from a chart that may belong to someone else. Other validation
  issues are warnings, not blocks.
- **Gap outcome is a proposal.** `closable_on_documentation` and the rest are
  proposed outcomes for the reviewer; the skill never closes a gap, determines
  compliance, or selects diagnosis/procedure codes.
- **Measure result awaits sign-off.** `measure_result` always ships with
  `reviewer_decision: "pending"` — the skill proposes the completed result but never
  accepts it. The reviewer's accept/reject is what finalizes a measure, and it is
  distinct from accepting the individual findings.
- **The audit log is append-only.** The skill seeds it with the system/AI events and
  preserves every `ai_value`; the app only ever appends reviewer actions, never
  edits or removes earlier entries — the trail is the evidence of who decided what.

### Language discipline

The structured output is unambiguous; determinations leak in through prose. Keep to
candidate language:

- "Documentation supports a **candidate** exclusion, pending reviewer validation" —
  not "the member is excluded."
- "**Evidence found** for the systolic reading" — not "the member is compliant."
- An `administrative` / `partial_needs_count` disposition is a routing note for the
  reviewer, never a conclusion.

## Grounding references

- `rules-pack-schema.md` — the canonical rules-pack contract (identical
  to the copy in `hedis-spec-to-rules`); the full input shape.
- `rules-pack-input.md` — the subset of pack fields this skill reads.
- `case-input.md` — the case object (member incl. name/dob, assigned measures, admin
  state) and how each field steers chart chase and gap closure.
- `example-case.json` — a worked case for the example pack (CBP gap + BCS-E gap_closed;
  member name/dob present for gap-closure validation).
- `findings-schema.md` — the output contract.
- `anchor_findings.py` — the bundled, dependency-free implementation of the
  deterministic half (anchoring + exclusion scan); the authoritative reference for
  the matching/negation/anchoring behaviour this skill relies on.

**Value-set codes (companion skill).** This skill scans on the pack's value-set *names*,
keywords, and any inline codes the pack prints — it does not carry the exhaustive code
lists. The companion skill `hedis-vsd` turns the licensed NCQA Value Set Directory into a
year-scoped code dictionary that resolves those names → codes and validates a captured
code's membership (reference only — it never selects a code). Use it when the reviewer
needs the codes behind a value-set name.
