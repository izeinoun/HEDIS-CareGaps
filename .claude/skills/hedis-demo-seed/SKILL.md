---
name: hedis-demo-seed
description: >-
  Reproduce the curated demo state for the HEDIS care-gap review app — the exact cast the
  presenter runbook (DEMO.md) follows: Victor Nolan (double-read disagreement + a reviewer
  edit), Priya Anand (dialysis exclusion, double-read agreement), Derek Cole (out-of-window,
  escalated), and Grace Whitman staged for a live upload. Ships the four chart fixtures, a
  declarative end-state spec, and an adapter-driven reference reseed. App-reproduction only
  — NOT a general-purpose data generator. Use when standing up a fresh build of this app and
  you want the same demo-ready state (worklist, analytics signals, escalation, audit trail).
---

# hedis-demo-seed

Rebuilds the **known, story-ready demo state** for the HEDIS care-gap app so a fresh build
is immediately demo-able and matches `DEMO.md`. This is intentionally narrow: it recreates
*this app's* curated cast, not arbitrary test data.

## When to use

- You rebuilt the app from the skills (see `BUILD_PROMPT.md`) and want the same demo state.
- You need to reset to a clean, curated baseline between run-throughs.

Do **not** use it as a general fixtures/factory tool — the members, stages, and expected
analytics are hand-tuned to tell the demo story.

## Files

- **`charts/*.txt`** — the four provider-submitted chart fixtures (Grace, Victor, Priya,
  Derek), verbatim. The single source of chart text.
- **`seed-spec.md`** — the declarative end-state: each member's identity, chart, target
  sign-off/QA/escalation state, the per-member operation order, and the **expected signals**
  to verify (double-read agreement, gate suggestion, substantiation, escalation).
- **`reseed_reference.py`** — the executable recipe. `reseed(adapter)` drives the seed
  through a small **adapter interface** (reset / create_case / analyze / confirm_all / edit
  / signoff / qa / escalate / assign / write_sample_chart), so it works against any build.

## How to apply

1. **Wire the adapter.** Implement the callables in `reseed_reference.py`'s docstring
   against your app's storage/routes. Two common shapes:
   - *In-process* — call your own analysis + review functions directly (fastest; how the
     reference app does it via `app.reseed_demo()`).
   - *Over HTTP* — POST to your upload/analyze/review/signoff/qa/escalate/assign routes.
2. **Run** `reseed(adapter)`; it clears the case store and rebuilds the four members
   (Grace is staged for live upload, not created).
3. **Verify** against the *Expected signals* in `seed-spec.md` (2 double-read pairs at 50%,
   the gate=raise suggestion from Victor's edit, Priya's exclusion path, Derek's escalation).
4. Expose it as a CLI (`seed_demo.py --reset`) and/or an **Administrator-only** in-app
   "Reset & reseed demo" button (server-gated to the Administrator role).

## Contract notes

- Actor ids `u_reviewer` / `u_overreader` / `u_admin` map to the four roles. **Separation
  of duties**: the blind second read and QA over-read must be a *different* identity than
  the primary signer — the reference assigns the Over-reader for those steps.
- Reviewer outcomes use the app vocabulary **gap_closed / gap_open / exclusion_applied /
  needs_more_info** — never "compliant/non-compliant".
- Every seeded action must land in the **append-only audit log** with actor + timestamp
  (audit A3), exactly as a real user action would — the seed is not a back door around the
  audit trail.
- Seeding **regenerates case ids** each run; reference members by name, not id.

## Related

Consumes `hedis-rules-to-findings` (analysis) and the app's review/RBAC layer
(`hedis-gap-workflow`). Pairs with `DEMO.md` (the runbook these members drive) and
`BUILD_PROMPT.md` (scaffolding a fresh app).
