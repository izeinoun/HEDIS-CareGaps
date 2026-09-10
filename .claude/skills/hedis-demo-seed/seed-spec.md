# Demo seed — declarative spec

The exact end-state to reproduce. `reseed_reference.py` produces this; use this doc to
verify a build reached it. Measure is **CBP** for every member. Workflow `chase`.
Actors: `u_reviewer` (Reviewer), `u_overreader` (Over-reader), `u_admin` (Administrator),
`u_auditor` (Auditor, read-only).

## The cast (four demo members + one live)

| Member | MRN / DOB / age / sex | Chart | End state | Purpose |
|---|---|---|---|---|
| **Grace Whitman** | M-7001 / 1958-05-12 / 69 / F | `charts/grace_whitman.txt` | **NOT seeded** — chart staged for live upload | The hero the presenter runs start-to-end (Act 1) |
| **Victor Nolan** | M-7002 / 1956-09-03 / 70 / M | `charts/victor_nolan.txt` | primary sign-off `gap_closed`; blind 2nd read `gap_open`; QA `needs rework`; assigned to Over-reader | Double-read **disagreement** + a reviewer edit that drives gate-tuning |
| **Priya Anand** | M-7003 / 1955-02-20 / 72 / F | `charts/priya_anand.txt` | primary sign-off `exclusion_applied`; blind 2nd read `exclusion_applied`; QA `qa passed` | The **exclusion** path + double-read **agreement** |
| **Derek Cole** | M-7004 / 1959-11-01 / 67 / M | `charts/derek_cole.txt` | analyzed, **escalated** (timing), not signed off | Out-of-window reading (BP dated 05/2025 vs MY2027) |

## Operation order (per member)

**Victor** — `analyze` → confirm all (Reviewer) → **edit** `diastolic` 88→**90** (Reviewer)
→ sign off *accepted* (→`gap_closed`) → confirm all (Over-reader, **second** pass) → sign
off *modified* `gap_open` (Over-reader, second) → QA *needs rework* → assign to Over-reader.

**Priya** — `analyze` → confirm all (Reviewer) → sign off *modified* `exclusion_applied`
(Reviewer) → confirm all (Over-reader, second) → sign off *modified* `exclusion_applied`
(Over-reader, second) → QA *qa passed*.

**Derek** — `analyze` → escalate (Reviewer), reason: *"BP reading dated 05/2025 — outside
MY2027; confirm timing / request current record"*. No sign-off.

Every operation is stamped with the acting user + timestamp into the append-only audit log
(audit A3). The two sign-offs each (primary + blind second) create the independent
double-read pair the Analytics page reports.

## Expected signals after seeding (sanity checks)

- **Double-read agreement:** 2 pairs — Victor `gap_closed` vs `gap_open` (**disagree**),
  Priya `exclusion_applied` vs `exclusion_applied` (**agree**) → 50% agreement. No kappa
  (out of scope, X-9).
- **AI-vs-final concordance:** ~91% agreement with **1 edit** (Victor's diastolic) → the
  confidence-gate suggestion recommends **raise** (a high-confidence value was corrected).
- **QA / over-read:** 1 concur (Priya), 1 rework (Victor).
- **Worklist / substantiation:** Victor `ready_for_manual_entry`, Priya `review_required`
  (exclusion to rule on), Derek `review_required` (out-of-window → indeterminate).
- **Escalation badge** on Derek; **out-of-window timing** banner on his review.

## Notes

- Grace's chart is written to the app's sample/upload directory so Act 1's live upload is
  one click. If a build wants her pre-seeded instead, run the same sequence as a
  gap-closure case (`workflow=gap_closure`, `admin_status=gap`) through analyze → review →
  sign off → blind read → QA.
- Reviewer outcomes use **gap_closed / gap_open / exclusion_applied / needs_more_info** —
  never "compliant/non-compliant".
