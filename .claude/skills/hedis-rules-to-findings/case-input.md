# Chart-chase case input

A **case** is the pursuit-list record for **one member**: the assigned measures and
their administrative state. It is the industry unit of chart chase — a plan resolves
what it can from claims/enrollment, then chases charts only for the members still
open. Supplying a case lets this skill chase the right measures, gate exclusions on
the member's age, and avoid re-proposing exclusions the plan already applied.

The case is a **member-scoped input to this skill only**. It is never part of the
rules pack (which is measure knowledge, member-agnostic and year-scoped).

## Shape

```jsonc
{
  "member": {
    "id": "M-1029",
    "name": "Jane A. Doe",     // required for gap-closure member match (also accepts a "family" field)
    "age": 71,                 // turns the exclusion age-gate from surfaced into evaluated
    "dob": "1954-03-02",       // used for the age-gate and (with name) the gap-closure member match
    "sex": "F"                 // optional context
  },
  "measurement_year": "MY2027", // cross-checked against the pack; a mismatch warns (codes are not stable across years)
  "assigned_measures": ["CBP", "BCS-E"],   // this member's measures; also scopes the broad cross-measure scan

  "measure_state": {            // per-measure administrative state, keyed by measure_id
    "CBP": {
      "admin_status": "gap",    // "gap_closed" | "gap" | "open" | "excluded" — see below
      "admin_exclusions_applied": [],       // exclusion keys the plan already applied administratively
      "last_dos": "2027-08-01"  // most recent claims date of service; recency anchor for the reviewer
    },
    "BCS-E": {
      "admin_status": "gap_closed",
      "admin_exclusions_applied": [],
      "last_dos": "2026-11-15"
    }
  }
}
```

## How each field steers the chase

- **`member.name` + `member.dob`** — in `--workflow gap_closure`, checked against the
  submitted chart for the member match (GC 2.1). If neither is found the submission
  hard-stops as `validation_failed` (likely wrong member/document); one-of-two is a
  warning. `name` may be a full name or a `family` field. Not used in chart chase.
- **`member.age`** — evaluated against each exclusion's `applies_when` to emit
  `age_check: in_band | out_of_band | not_applicable | unknown` on the finding. Still
  proposal-only: an `out_of_band` hit is surfaced, never auto-dropped.
- **`measurement_year`** — compared with the pack's `source.measurement_year`; a
  mismatch is a warning, since a pack must match the case's year.
- **`assigned_measures`** — the measures to chase for this member. Run the skill once
  per open measure (a chart pulled once is reviewed for every open gap). Also the set
  the broad-mode cross-measure scan should consider.
- **`admin_status`** — drives whether to chase:
  - `gap` / `open` → **chase** (the reason the chart was pulled).
  - `gap_closed` → **skip** (already gap-closed administratively).
  - `excluded` → **skip** (already retired from the denominator).
  A skipped measure returns a `status: "skipped_admin_resolved"` record; pass
  `--force` to review it anyway (e.g. an audit or an overread).
- **`admin_exclusions_applied`** — any exclusion key here is treated as **already
  captured**: a chart hit for it is tagged `already_applied` (disposition
  `already_applied`) rather than proposed as a new candidate, and it does not count
  toward `exclusions_proposed`. A member with an exclusion already applied is
  administratively resolved, so the measure is skipped unless `--force`.
- **`last_dos`** — recency context for the reviewer; not used to drop findings.

## What the case does NOT do

- It does not make a compliance or exclusion **determination** — the chart evidence
  the skill surfaces remains a proposal for the reviewer, and the case's admin state
  is starting context, not a verdict.
- It does not enforce **date windows**. `timing` is surfaced for the reviewer; the
  scan is date-blind and never drops a hit for falling outside a window.
- It is **optional**. With no case, the skill runs plain measure-plus-chart exactly
  as before.
