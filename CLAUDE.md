# HEDIS Care-Gap Review — project guide

A payer-side **HEDIS measure data-extraction & care-gap review** app, built on top of
composable **skills**. The app locates each HEDIS measure's data in an uploaded medical
chart with page-anchored evidence, surfaces candidate exclusions, and routes everything
through a human review workflow (sign-off → independent over-read) with a full audit
trail. It is **proposal-only**: the AI never decides compliance.

## Layout

```
.claude/skills/        the reusable skills (domain logic + style) — see below
hedis-app/             the Flask app that composes them
  app.py               routes, storage, RBAC, audit, reseed
  engine/              bridges to the skills (findings_engine, workflow, vsd, pdf_extract, extract_elements)
  templates/           Jinja server-rendered pages (base.html = Penguin sidebar shell)
  static/app.css       the Penguin light stylesheet
  data/                packs/ (rules), vsd/ (value sets), cases/ findings/ charts/ (state)
  seed_demo.py         thin CLI over app.reseed_demo()
  DEMO.md              story-driven presenter runbook
  ChartChase-requirements · GapsInCare-requirements · OutOfScope   (customer scope docs)
anthropickey           Anthropic API key (loaded at startup; never print its value)
BUILD_PROMPT.md        copy-paste prompt to scaffold a fresh app from the skills
```

## The skills (`.claude/skills/`)

- **hedis-spec-to-rules** — NCQA spec PDF → machine-usable rules pack (data elements,
  exclusions by value-set name, timing windows).
- **hedis-rules-to-findings** — chart text + rules pack → findings: element extraction,
  page-anchored evidence, negation-aware exclusions, gap outcome, `substantiation`
  (valid-data + next step). Proposal-only. **This is the analysis core.**
- **hedis-gap-workflow** — cross-case operations: prioritized worklist, AI-vs-final +
  over-read/double-read **agreement** analytics, and the 4-role RBAC model.
- **hedis-vsd** — value-set directory (codes, effective year, licensed/internal).
- **penguin-style** — the UI design system (drop-in `penguin.css` + tokens + components).
- **hedis-demo-seed** — reproduce this app's curated demo state (chart fixtures + spec +
  adapter-driven reference reseed). App-reproduction only, not a general fixtures tool.

Skill boundary: **analysis** (per-chart, proposal-only, no aggregates) vs **workflow**
(cross-case, aggregates OK) vs **reference-data producers** (rules pack, VSD) vs **style**.
Keep skills standalone.

## Run / demo

```bash
cd hedis-app
../.venv/bin/python seed_demo.py --reset   # rebuild curated demo state (no server needed)
../.venv/bin/python app.py                 # serves http://127.0.0.1:5001
```
Demo members: Victor Nolan (signed off, double-read disagreement, QA rework), Priya Anand
(dialysis exclusion), Derek Cole (out-of-window, escalated); Grace Whitman is uploaded
**live** in Act 1 (`sample_charts/grace_whitman.txt`). Reseed anytime from the **Reset &
reseed demo** button (Administrator only) or the CLI. Four demo users: Dana Cole
(Reviewer), Sam Ortiz (Over-reader), Morgan Lee (Administrator), Riley Kim (Auditor).

## Hard rules — do NOT violate

- **Proposal-only.** Never make the app determine member compliance, numerator status, or
  final exclusion application. A human signs off; the AI proposes.
- **Outcome vocabulary:** reviewer `final_status` ∈ `gap_closed` / `gap_open` /
  `exclusion_applied` / `needs_more_info`. **Never surface "compliant/non-compliant"** as a
  member determination (the word "compliance" is fine only as "the app never *decides*
  compliance"). The guardrail lines in the skills that name the forbidden words stay.
- **Out of scope** (`OutOfScope` doc, X-1…X-15): no automated ICD/CPT/LOINC **code
  selection**; no inter-rater-reliability **statistics** (capture agreement, don't score
  it — kappa was removed); no QMRM write-back or provider contact; no claims/eligibility.
  Don't build these into the skills.
- **Audit A1–A12** must hold: immutable read-only source + stable `document_id`,
  page-anchored citations, actor + timestamp on every action, rules + VSD version stamping,
  escalation, human sign-off, confidence retention, provider credential, retention of all
  values, no fabrication, multi-patient flag. (A11 user-mgmt logging = platform RBAC.)
- **VSD licensing:** NCQA value sets stay internal — export value-set **names** only,
  never the code lists.
- **UI = Penguin light style** (via `penguin-style`). Do NOT revert to the old **Gwen
  dark** theme or a top-bar nav.

## Conventions & gotchas

- **Model:** default to Claude Opus 4.8 (`claude-opus-4-8`), adaptive thinking. Key is in
  the root `anthropickey` file; if absent/invalid the extractor falls back to an offline
  heuristic (everything else identical). Never print the key.
- **RBAC / separation-of-duties:** the over-reader/blind-second-read must differ from the
  primary signer (enforced at identity level; server 403s). Auditor is read-only.
- **Audit trail:** append-only, rendered **newest-first**, timestamps in **UTC**.
- **Templates are cached** (debug off): **restart the server after editing templates or
  CSS**. Jinja gotcha: `dict.items` collides with an `"items"` key — use `result['items']`.
- **Seeding regenerates case ids** every run; the UI links by stable member name.
- Use the scratchpad dir for throwaway test cases and **clean them up** (the review-page
  guard, `_double_read_pairs`, etc. were validated with self-cleaning HTTP tests).

## To build a fresh app from these skills

See **`BUILD_PROMPT.md`** (repo root) — a minimal prompt + a skill→capability checklist.
Result is functionally and visually **similar**, not byte-identical; the app's
routes/storage/seed vary unless pinned. Reuse `data/packs/*.json` + `data/vsd/*.json` and
name the page set for the closest match.
