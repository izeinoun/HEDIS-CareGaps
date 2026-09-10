# Build prompt — HEDIS care-gap review app from the skills

Copy-paste one of the prompts below to build a fresh app that reuses these skills. The
skills supply the domain logic, the operational layer, the reference-data model, the
audit/scope rules, and the visual style — so a new build comes out **functionally and
visually very similar** (not byte-identical; see *What varies* below).

The skills live in `.claude/skills/`:
`hedis-spec-to-rules`, `hedis-rules-to-findings`, `hedis-gap-workflow`, `hedis-vsd`,
`penguin-style`, `hedis-demo-seed`.

---

## Prompt (recommended)

> Build a payer-side **HEDIS care-gap review** web app (Flask, server-rendered
> templates). Use my skills: **hedis-spec-to-rules** + **hedis-rules-to-findings** to
> locate each measure's data and candidate exclusions in an uploaded chart, each with a
> page-anchored evidence quote and confidence — **proposal-only, never decide
> compliance**; **hedis-gap-workflow** for a prioritized reviewer worklist, an
> independent blind over-read, the 4-role RBAC (Reviewer / Over-reader / Administrator /
> Auditor) with separation-of-duties, and a full append-only audit trail; **hedis-vsd**
> for the licensed value-set directory; and **penguin-style** for the entire UI (light
> theme, left sidebar, clean tables, lifecycle stepper, summary header card).
>
> Flow: a reviewer uploads a patient chart (PDF) together with the identified measures
> and gaps → the app locates the measure data and gap-filling evidence → human review
> with confirm / modify / reject → measure sign-off → independent over-read → a
> prioritized worklist and process analytics. Honor the **audit requirements (A1–A12)**
> and the **scope boundaries** defined in the skills (proposal-only; no automated code
> selection; no reliability statistics). Load the Anthropic key from the project's
> `anthropickey` file and default to Claude Opus 4.8.
>
> Use **hedis-demo-seed** to rebuild the curated demo state (Victor / Priya / Derek, with
> Grace staged for a live upload) and expose it as a CLI + an Administrator-only reset
> button, so it's demo-ready.

## Prompt (shortest — if you've copied `data/packs` and `data/vsd` into the new project)

> Build a Flask HEDIS care-gap review app using my hedis-* skills for the logic and
> penguin-style for the UI: upload chart → locate measure data with page-anchored
> evidence (proposal-only) → human review → sign-off → over-read → prioritized worklist
> → audit trail. Reuse the rules pack and VSD in `data/`. Key in `anthropickey`. Add
> seed data + a demo script.

---

## Which skill covers what

| Capability in the app | Skill |
|---|---|
| Spec PDF → machine-usable rules pack (data elements, exclusions, timing) | `hedis-spec-to-rules` |
| Chart → findings: element extraction, page-anchored evidence, negation-aware exclusions | `hedis-rules-to-findings` |
| Gap outcome, per-measure valid-data + recommended next step (CC 2.4/2.5) | `hedis-rules-to-findings` |
| Member-match gate, measure-alignment / legibility validation (GC 2.1/2.2) | `hedis-rules-to-findings` |
| Prioritized worklist (retrieval triage) | `hedis-gap-workflow` |
| AI-vs-final concordance, over-read / double-read **agreement capture** | `hedis-gap-workflow` |
| 4-role RBAC + permission matrix + separation-of-duties | `hedis-gap-workflow` |
| Value-set directory (codes, effective year, licensed/internal) | `hedis-vsd` |
| Look & feel (shell, tables, chips, lifecycle stepper, summary card, KPIs, timeline) | `penguin-style` |
| Curated demo state (chart fixtures + reproducible reseed + reset button) | `hedis-demo-seed` |

## Guardrails the skills already encode (carry over for free)

- **Proposal-only** — the app never determines member compliance, numerator status, or
  final exclusion application; a human signs off.
- **Audit A1–A12** — immutable source + stable id, page-anchored citations, actor +
  timestamp, rules + VSD version stamping, escalation, human approval, confidence
  retention, provider credential, retention of all values, no fabrication, multi-patient
  flag. (A11 user-management logging is the platform's RBAC.)
- **Out of scope** — no automated ICD/CPT/LOINC **code selection**; no
  inter-rater-reliability **statistics** (agreement is captured, not scored); no QMRM
  write-back or provider contact; no claims/eligibility processing.
- **Vocabulary** — reviewer outcomes are `gap_closed` / `gap_open` / `exclusion_applied`
  / `needs_more_info` (never "compliant/non-compliant" as a member determination).
- **Licensing** — the VSD (NCQA value sets) stays internal; value-set **names** may be
  exported, never the code lists.

## What comes back the same vs. what varies

**Same:** the domain behavior, the operational features, the audit/scope rules above, and
the Penguin visual style — because they are pinned in the skill docs and stylesheet.

**Varies run-to-run (application glue the skills don't dictate):** exact route/URL set,
storage layout, template composition, the audit/lifecycle wiring, the specific seed/demo
data and demo users, and minor UX-flow choices. To minimize drift: **reuse the existing
`data/packs/*.json` and `data/vsd/*.json`** rather than regenerating, and **name the page
set** you want (Patients, Case detail, Review, Worklist, QA queue, Analytics, Rules, VSD,
Audit) in the prompt.

## Optional: pin the page set (paste after the prompt for a closer match)

> Pages: Patients list · Case detail (summary card + lifecycle stepper) · Review
> (split panel: chart with highlighted evidence on the left, proposals with
> confirm/modify/reject + sign-off on the right) · Prioritized worklist · QA queue ·
> Analytics · Rules admin · VSD browser · per-case Audit trail (newest first, UTC).
