# Findings output contract

The output is one self-contained JSON object per analysed chart. It is emitted by
the bundled `anchor_findings.py`, so its shape is fixed by that script.

```jsonc
{
  "mode": "targeted",                  // "targeted" (elements + exclusions) or "broad" (adds cross_measure)
  "measure_id": "CBP",
  "measure_name": "Controlling High Blood Pressure",
  "measurement_year": "MY2027",        // echoed from the pack
  "case_context": {                    // present when a chart-chase case was supplied; null otherwise
    "member_id": "M-1029",
    "member_age": 71,
    "admin_status": "gap",             // why this measure was chased
    "admin_exclusions_applied": [],
    "last_dos": "2027-08-01",
    "chased": true                     // false only in the skipped record below
  },
  "elements": [
    {
      "element_key": "systolic",
      "element_label": "Systolic",
      "element_type": "numeric",
      "required": true,
      "unit": "mmHg",
      "options": null,
      "timing": "Most recent reading in the measurement year",
      "ai_value": "138",               // string, or null if not documented
      "ai_confidence": 0.91,           // 0-1, clamped
      "evidence_text": "BP 138/86 mmHg at 03/14 visit",   // verbatim from the chart, or null
      "evidence_anchored": true,       // false => quote could not be located; confidence downgraded
      "status": "proposed",            // "proposed" if a value was found, else "not_found"
      "in_window": true,               // null if timing unknown; false = documented but outside the window
      "document_id": null,
      "page_number": 2,
      "char_start": 4120,
      "char_end": 4152
    }
  ],
  "exclusions": [
    {
      "rule_key": "esrd_dialysis",
      "rule_label": "ESRD, dialysis, or kidney transplant",
      "scope": "required",             // required | optional
      "origin": "measure",             // "measure" (from this measure's exclusions) | "universal" (confirm the measure lists it)
      "note": "ESRD, chronic dialysis, or a functioning kidney transplant retires the member",
      "timing": "Any time in the member's history through the end of the measurement year",  // the window; echoed from the pack, not enforced by the scan
      "applies_when": null,            // age/eligibility gate from the pack
      "age_check": "not_applicable",   // in_band | out_of_band | not_applicable | unknown — evaluated only when a case gives member age
      "already_applied": false,        // true when rule_key is in the case's admin_exclusions_applied
      "value_set_name": "Dialysis",    // which named value set produced the hit
      "matched_term": "hemodialysis",  // the phrase found in the chart
      "ai_confidence": 0.73,
      "evidence_text": "...started hemodialysis in March...",
      "source_hint": "medical_record",  // echoed from the pack; null if unset
      "needs_file_confirmation": false, // true when source_hint == "administrative"
      "compound": false,                // true = needs 2+ distinct findings; a single hit is partial
      "threshold": null,                // echoed from the pack; {count, distinct} or null
      "threshold_note": null,           // set when threshold present: one hit can't meet the count
      "disposition": "proposed",        // see disposition note below
      "document_id": null,
      "page_number": 5,
      "char_start": 9812,
      "char_end": 9824
    }
  ],
  "cross_measure": [                    // present only in broad mode
    {
      "found_measure_id": "GSD/GSD-E",
      "found_measure_name": "Glycemic Status Assessment for Patients With Diabetes",
      "element_key": "result_value",
      "value": "7.2",
      "confidence": 0.8,
      "evidence_text": "HbA1c 7.2% on 05/02",
      "page_number": 3, "char_start": 5210, "char_end": 5240
    }
  ],
  "summary": {
    "elements_total": 4,
    "elements_found": 3,
    "required_missing": 0,
    "required_missing_keys": [],
    "exclusions_proposed": 1,             // excludes any tagged already_applied
    "exclusions_already_applied": 0,      // hits for exclusions the case already applied
    "cross_measure_found": 0,
    "mean_confidence": 0.88,
    "anchored_evidence": 3
  },
  "disclaimer": "AI proposals only. Measure compliance, numerator status, and final exclusion application are determined by the reviewer, not by this analysis."
}
```

## Skipped record (chart chase, admin-resolved)

When a case marks the measure gap_closed or already-excluded and `--force` is not
given, the skill emits a short record instead of chasing:

```jsonc
{
  "mode": "targeted",
  "measure_id": "BCS-E",
  "measure_name": "Breast Cancer Screening",
  "measurement_year": "MY2027",
  "status": "skipped_admin_resolved",
  "reason": "already gap-closed; pass --force to chase anyway",
  "case_context": { "member_id": "M-1029", "member_age": 71, "admin_status": "gap_closed",
                    "admin_exclusions_applied": [], "last_dos": "2026-11-15", "chased": false },
  "disclaimer": "AI proposals only. ..."
}
```

## Gap-closure fields (`--workflow gap_closure`)

In gap closure the object also carries `workflow: "gap_closure"`, a `validation`
block, and a `gap_outcome` block (all `null` in chart chase):

```jsonc
  "workflow": "gap_closure",
  "validation": {                        // the submission gate (GC 2.1/2.2)
    "verdict": "passed",                 // "passed" | "failed_member_mismatch"
    "member_match": "confirmed",         // "confirmed" (name+DOB) | "partial" | "not_found"
    "name_found": true,
    "dob_found": true,
    "measure_alignment": "aligned",      // "aligned" (≥2 kw) | "weak" (1) | "absent"
    "content_present": true,
    "service_date_present": true,
    "warnings": []                       // advisory issues; do not block extraction
  },
  "gap_outcome": {                       // proposed outcome (GC 4.1/4.4) — reviewer confirms
    "status": "closable_on_documentation",
    // closable_on_documentation | partial_documentation | exclusion_candidate | previously_closed | no_impact_to_gap
    "rationale": "All required data elements are documented with anchored evidence in the chart.",
    "required_found": ["bp_date", "systolic", "diastolic"],
    "required_missing": [],
    "note": "Proposed outcome for reviewer confirmation; not a compliance determination."
  },
  "substantiation": {                    // CC 2.4 / CC 2.5 — emitted for BOTH workflows
    "valid_data_present": true,          // true | false | null (indeterminate — present but flagged)
    "substantiating_elements": ["bp_date", "systolic", "diastolic"],
    "missing_elements": [],
    "next_step": "ready_for_manual_entry",  // ready_for_manual_entry | follow_up_with_provider | review_required
    "note": "Proposed substantiation and next step for reviewer confirmation; QMRM entry and provider contact out of scope."
  },
```

A **member-identity mismatch is a hard stop**: instead of the full object the skill
returns a short record and runs no extraction —

```jsonc
{
  "workflow": "gap_closure",
  "measure_id": "CBP",
  "status": "validation_failed",
  "reason": "neither the member name nor DOB could be located in the chart — likely a wrong-member or wrong-document submission",
  "validation": { "verdict": "failed_member_mismatch", "member_match": "not_found", ... },
  "case_context": { ... },
  "disclaimer": "AI proposals only. ..."
}
```

Not emitted at all: diagnosis/procedure **code selection** and any compliance
determination — the skill surfaces value-set names and pack-printed codes only.

## Broad cross-measure scan (`--broad-scan`)

A deterministic, model-free pass over the whole pack for one chart. Instead of the
element/exclusion object it returns `mode: "broad"`, `source_measure_id` (the targeted
measure, excluded from the scan), and `broad_scan[]` — one entry per measure with
`element_signals[]` (keyword-evidence hits with anchors — *not* extracted values),
`required_signal` / `required_total` / `total_signal`, `exclusions[]`, and `has_evidence`.
Signals mark that a measure's vocabulary *appears* in the chart — a candidate to chase —
not that a value was abstracted; run the targeted Pass-1 to get values. Counts are
per-chart candidate signals, never member rates.

## Review & audit fields (always present)

Every result carries a measure-level review envelope and an audit log, so the app
always has a consistent place to record the reviewer's sign-off on the *whole*
measure result and the trail of who did what.

```jsonc
  "measure_result": {                    // the completed measure result the reviewer accepts/rejects
    "proposed_status": "closable_on_documentation",  // gap_closure: the gap_outcome; chase: numerator_evidence_found | partial_evidence | candidate_exclusion | no_evidence
    "proposed_basis": "All required data elements are documented with anchored evidence.",
    "reviewer_decision": "pending",      // pending | accepted | rejected | modified  (the app sets this)
    "final_status": null,                // the reviewer's status when decided; may differ from proposed
    "decided_by": null,                  // reviewer id (app-filled)
    "decided_at": null,                  // ISO timestamp (app-filled)
    "note": null                         // reviewer's reason on accept/reject/modify
  },
  "audit_log": [                         // seeded with system/AI events; the app APPENDS reviewer actions
    { "seq": 1, "ts": "2027-07-16T09:30:00", "actor": "system", "action": "analysis_run",
      "target": "CBP", "detail": "targeted analysis, gap_closure workflow" },
    { "seq": 2, "ts": "2027-07-16T09:30:00", "actor": "ai", "action": "element_proposed",
      "target": "systolic", "detail": "value=132 confidence=0.93 anchored=True", "ai_value": "132" },
    { "seq": 5, "ts": "2027-07-16T09:30:00", "actor": "ai", "action": "measure_result_proposed",
      "target": "CBP", "detail": "closable_on_documentation" }
    // app appends, e.g.:
    // { "seq": 6, "actor": "reviewer", "action": "finding_modified", "target": "systolic", "detail": "132 -> 134", "ai_value": "132" }
    // { "seq": 7, "actor": "reviewer", "action": "measure_result_accepted", "target": "CBP", "detail": "final_status=gap_closed" }
  ]
```

- **`measure_result`** is the completed-result sign-off — parallel to accepting or
  rejecting each finding, but for the measure as a whole. The skill always emits it
  with `reviewer_decision: "pending"`; the tool proposes, the human decides. It is a
  proposal, never a determination.
- **`final_status` controlled vocabulary.** When the reviewer signs off (accepts or
  overrides the `proposed_status`), the app records the human's HEDIS determination in
  `final_status` using this canonical set — the *reviewer's* call, never the tool's:
  - `gap_closed` — the numerator is met on the reviewed evidence.
  - `gap_open` — the gap remains open after review.
  - `exclusion_applied` — a denominator exclusion is confirmed and the member is retired.
  - `needs_more_info` — the chart is insufficient; route for another document or over-read.

  On `reviewer_decision: "accepted"` the app maps the `proposed_status` to the matching
  `final_status` (e.g. `closable_on_documentation` / `numerator_evidence_found` →
  `gap_closed`; `exclusion_candidate` / `candidate_exclusion` → `exclusion_applied`;
  `partial_documentation` / `partial_evidence` / `no_evidence` / `no_impact_to_gap` →
  `gap_open`). On `rejected` / `modified` the reviewer picks the `final_status`
  explicitly. Keep the set stable across measures and measurement years so the sign-off
  is reportable and aggregatable.
- **`audit_log`** is append-only. The skill seeds the system/AI events (analysis run,
  each proposed element/exclusion, the proposed measure result), each preserving the
  original `ai_value` so an AI-vs-final comparison survives even after a reviewer edit.
  The application appends reviewer events (`finding_accepted` / `finding_rejected` /
  `finding_modified` / `measure_result_accepted` / `measure_result_rejected`) — it
  never rewrites earlier entries. A per-case audit view concatenates the `audit_log`
  of every measure analysed for that member.
- Both are present on `skipped_admin_resolved` and `validation_failed` records too, so
  no case-measure is ever without a review envelope and a trail.

## Field notes

- **`ai_value` is always a string or `null`.** Empty, `"null"`, `"N/A"` normalize
  to `null` with `status: "not_found"`.
- **Anchoring**: a value's `evidence_text` is located in the chart to produce
  `char_start`/`char_end` and `page_number`. If it cannot be located,
  `evidence_anchored` is `false` and `ai_confidence` is capped (0.4) — an
  unlocatable quote is unverified, not evidence.
- **`in_window`** is a lightweight flag set when a documented date/value falls
  outside the element's `timing` window. It never
  removes a finding — the reviewer decides. Leave `null` when timing can't be
  evaluated.
- **`evidence_role`** (A8) echoes the element's role from the pack: `null` for an
  ordinary clinical value, or `"provider_credential"` / `"provider_signature"` when the
  element captures the performing provider's credential/signature required by the measure.
  The value carries the same citation/anchor as any element, so the credential is auditable
  evidence — the skill never selects or infers a credential, it locates what the chart states.
- **`compliance`** (advisory, never a determination) reconciles a numeric `ai_value`
  against the element's `compliance_hint`: `{checkable, meets (true/false/null), hint,
  basis}` — e.g. `{checkable:true, meets:true, basis:"138 < 140"}` for a hint of
  "Gap closed when < 140". Descriptive hints ("Screening or diagnostic qualify") return
  `checkable:false`. It is a reviewer aid to speed sign-off; the human still decides.
- **`needs_review`** flags a *found* value that is unanchored or at/below 0.7
  confidence (for exclusions: any partial/administrative disposition or low-confidence
  hit). A consumer can use it as a review gate — require these to be ruled on before the
  `measure_result` is accepted. It never drops a finding.
- **`substantiation`** answers the customer's step-6 question — *is substantiating data
  present for this measure, yes or no* (CC 2.4) — and proposes the step-6 next step (CC 2.5).
  `valid_data_present` is `true` when every required element is documented with anchored
  evidence, `false` when a required element is missing, and `null` when a required element
  is present but flagged (`needs_review`), so presence is indeterminate. `next_step` is a
  recommendation only — `ready_for_manual_entry` (present & clean), `follow_up_with_provider`
  (missing data), or `review_required` (flagged, or a candidate exclusion to rule on). The
  reviewer confirms it at sign-off; the skill never enters data (X-5) or contacts a provider (X-8).
- **`out_of_window_required`** (on `gap_outcome`, and counted in `summary`) lists
  required elements that are documented but dated **outside** the measurement window.
  The proposed status is unchanged, but the `rationale`/basis carries a timing caveat so
  the reviewer confirms the date counts — closing the "present but doesn't count" gap.
- **`components`** on a `compound` exclusion lists each keyword concept and whether it
  is `present` (non-negated) in the chart, so a single partial hit shows what is still
  missing (e.g. bilateral vs. two-unilateral mastectomy).
- **Exclusions never carry a compliance meaning.** They are *candidates* the
  reviewer confirms; `scope` records whether the measure treats the exclusion as
  required or optional, not whether to apply it.
- **`disposition`** grades how a hit should be read. `"proposed"` — an ordinary
  chart-findable candidate. `"confirm_via_administrative_source"` — the pack marked
  this criterion `source_hint: "administrative"` (a file value), so a chart mention
  is *not* sufficient; route it to the enrollment/claims file rather than treat it
  as evidence. `"partial_needs_components"` — the pack marked the rule `compound`
  (needs two or more distinct findings, e.g. advanced illness AND frailty, or a
  bilateral vs. two-unilateral mastectomy); a single hit cannot settle it — read
  `note` for the full requirement. `"partial_needs_count"` — the pack set a
  `threshold` (one concept needed N times); a single text hit is partial and the
  count is the reviewer's to confirm. All are surfaced, never silently dropped.
- **`origin`** is `"measure"` when the exclusion came from the target measure's own
  `exclusions[]`, or `"universal"` when it came from the pack's `universal_exclusions`.
  Universal rules (hospice, palliative, advanced-illness+frailty) are scanned for
  every measure, but NCQA applies some of them only to a measure-defined subset — so
  a `"universal"` hit carries an implicit "confirm this measure actually lists this
  exclusion" before the reviewer relies on it.
- **`timing`** echoes the exclusion's window from the pack (member history / the
  measurement year / as of the anchor date). The scan is **date-blind**: it never
  drops a hit for being out of window — it surfaces `timing` so the reviewer checks
  the dates.
- **`age_check`** is evaluated only when a case supplies `member.age`: `in_band` /
  `out_of_band` against the exclusion's `applies_when`, `not_applicable` when the
  gate is not age-based, `unknown` when no age was given. An `out_of_band` hit is
  still surfaced — the reviewer decides — never auto-removed.
- **`already_applied`** is `true` when the exclusion's key is in the case's
  `admin_exclusions_applied`; the hit is a duplicate of an administratively captured
  exclusion (disposition `already_applied`) and does not count toward
  `exclusions_proposed`.
- **`case_context`** is present (non-null) only when a case was supplied, and echoes
  the member/admin state that drove the chase. It is context, never a determination.
