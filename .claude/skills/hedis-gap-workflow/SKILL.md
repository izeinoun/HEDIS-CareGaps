---
name: hedis-gap-workflow
description: >-
  The operations layer above HEDIS chart analysis: rank open care gaps for review
  triage (retrieval prioritization) and measure the review process itself
  (AI-vs-final agreement and over-read concordance). Consumes the per-chart findings
  emitted by `hedis-rules-to-findings` plus the application's recorded reviewer
  decisions/QA, and a plan priority-config. Deterministic and cross-case; it produces
  ranked worklists and QA analytics, never a member-compliance rate or a clinical
  determination. Use when triaging which gaps to chase first, or auditing reviewer/AI
  quality across many reviewed charts.
---

# HEDIS gap workflow (operations layer)

The two companion skills are the **analysis layer** — per-chart, evidentiary, and
strictly proposal-only:

- `hedis-spec-to-rules` → a rules pack (what to look for).
- `hedis-rules-to-findings` → per-chart findings + a review envelope
  (`measure_result`, `audit_log`, `needs_review`) — a proposal per member×measure.

This skill is the **workflow / operations layer** that sits *above* them. It is
deliberately a separate skill because it does the things the analysis skill refuses
to do by design — it is **cross-case and aggregate**:

- **Retrieval prioritization** — rank a population of open gaps so reviewers work the
  highest-value charts first.
- **Over-read & AI-vs-final concordance** — measure how the humans acted on the AI's
  proposals, and how a QA over-read concurred, to steer quality and tune the gate.

Where the analysis skill says *"never emit a rate; the queue, assignment, over-read,
QA and audit trail are the application's responsibility,"* this skill is the home for
exactly that operational, aggregate logic. It never re-derives evidence or decides
compliance — it consumes the analysis output and the human decisions recorded on top.

**Boundary (non-negotiable).** These are **operational** metrics (measure weight,
work rank, reviewer-agreement rates), never **member-compliance** figures. This skill
must not emit a HEDIS numerator/denominator rate, and never overrides an evidentiary
finding — it reads them.

## When to use

- "Which open gaps should the team chase first?" → **prioritize**.
- "How often is the AI right / how often does QA rework a sign-off / is our
  confidence gate set correctly?" → **concordance**.

## Retrieval prioritization (`prioritize.py`)

Input: a list of open **case×measure items** (the application builds these from its
cases and the findings), plus a **priority-config** (`priority-config.md`).

Each item carries at least `measure_id` and `admin_status`, and — when the measure
has been analyzed — `required_missing`, `needs_review`, and an optional
`days_to_deadline`. The score is transparent and every component is returned:

```
score = measure_weight * (1 + yield_bonus) + urgency
```

- `measure_weight` — from the priority-config. **CMS Star-informed defaults**
  (outcome/intermediate measures weighted above process measures), **plan-overridable**.
  This is Star/plan policy, *not* an NCQA spec value, which is why it is its own config
  and not part of the rules pack.
- `yield_bonus` — likelihood a review closes the gap: a bonus when the required data
  is already documented (`required_missing == 0`), a smaller bonus when partially
  documented, a penalty for unresolved weak (`needs_review`) findings.
- `urgency` — ramps up as the measurement-year deadline approaches.

Administratively resolved items (`gap_closed` / `excluded`) are dropped — you don't
chase a closed gap. Output is a ranked worklist (`worklist-schema.md`) with a
per-item `factors` breakdown so the ranking is explainable and the config is tunable.

```
python prioritize.py --items ITEMS.json [--config priority-config.json] [--out OUT.json]
```

## Over-read & concordance (`concordance.py`)

Input: a collection of **reviewed findings** — each a `hedis-rules-to-findings`
output *with the application's recorded* `decisions` (per-finding confirm/modify/
reject, keeping the AI baseline), `measure_result` (the sign-off), and `qa` (the
over-read state). Output (`concordance-schema.md`):

- **`ai_vs_final`** — agreement rate (confirm), edit rate (modify), reject rate, and
  value-change rate; overall and **by measure** and **by element** (which elements the
  AI gets edited on most — direct prompt-tuning targets).
- **`measure_result`** — sign-off override rate (accepted vs rejected/modified).
- **`over_read`** — reviewer↔QA **concurrence rate** (a plain agreement rate). Sequential
  over-read concurrence; no reliability coefficient is computed (kappa is out of scope, X-9).
- **`double_read_agreement(pairs)`** (separate function) — **agreement capture** on
  *independent blind double-reads*: two reviewers who each signed off the same case×measure
  without seeing the other (CC 3.1). Returns the agreement rate, per-measure agreement, and
  the list of disagreements to adjudicate — a plain count, **not** an IRR statistic. Valid
  only when the application enforces the blinding and supplies the paired final determinations.
- **`gate_suggestion`** — where disagreements cluster in AI confidence. If edits/
  rejects sit *above* the current `needs_review` gate, high-confidence values are being
  changed, so it recommends **raising** the gate; otherwise **hold**. A suggestion for a
  human to apply, not an automatic change.

```
python concordance.py --records REVIEWED.json [--gate 0.7] [--out OUT.json]
```

## Workflow roles (`roles.py`)

The review process's **role contract** — policy, not mechanism. It defines the domain
roles (`reviewer`, `over_reader`, `administrator`, `auditor`), the action→role permission
matrix, and the **separation-of-duties** rules that plain RBAC cannot express (the QA
over-read and blind second read must be done by a *different person* than the primary
signer). `can(role, action)` / `authorize(role, action, actor_id, prior_actor_ids)` are the
deterministic gate. A host platform's RBAC module owns users, auth, group→role mapping, and
user-management audit — it is **configured to satisfy this contract**, it does not define the
roles. See `workflow-roles.md` for the matrix and the platform-mapping guidance.

## Guardrails (non-negotiable)

- **Operational, never compliance.** No member numerator/denominator rate — ever. If
  asked for a compliance rate, decline and offer the per-chart findings (analysis skill)
  or these operational metrics instead.
- **Reads, never re-derives.** This skill consumes findings and human decisions; it
  never re-extracts evidence, re-scans exclusions, or changes an evidentiary finding.
- **Weights are policy, not spec.** The priority-config carries Star/plan weights;
  it is separate from the NCQA-derived rules pack and must not be conflated with it.
- **Suggestions, not automation.** The gate recommendation and the ranking are inputs
  for a human; nothing here auto-applies a threshold or auto-closes a gap.
- **Deterministic.** Both tools are dependency-free Python over structured input — no
  LLM call, so every number is explainable and reproducible.

## Grounding references

- `priority-config.md` — the priority-config contract (measure → weight) and scoring knobs.
- `example-priority-config.json` — Star-informed defaults for CBP + BCS-E.
- `worklist-schema.md` — the prioritized-worklist output contract.
- `concordance-schema.md` — the concordance-report output contract.
- `prioritize.py` / `concordance.py` — the bundled deterministic implementations.
- `workflow-roles.md` / `roles.py` — the role contract (roles, permission matrix,
  separation of duties) and the platform-RBAC mapping guidance.
