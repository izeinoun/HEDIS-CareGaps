# HEDIS Care‑Gap Analysis — Demo Runbook

A story-driven walkthrough. You follow **one member end‑to‑end** across all four actor
roles, then tour the admin foundations that prove this runs on **real** rules and codes.
Everything shown is proposal‑only and human‑in‑the‑loop; the app never decides compliance.

---

## 0 · Setup (2 minutes, before the audience)

```bash
cd hedis-app
../.venv/bin/python seed_demo.py --reset   # loads the curated demo state (no server needed)
../.venv/bin/python app.py                 # serves http://127.0.0.1:5001
```

The seed loads a clean, curated state: three members already at different stages, and it
leaves **Grace Whitman** for you to run live. Open **http://127.0.0.1:5001**.

> To re-arm between run-throughs, you don't need the shell: as **Morgan Lee ·
> Administrator**, the Patients screen has a **↻ Reset & reseed demo** button that clears
> the case store and rebuilds this exact state (packs, VSD and priority-config are kept).
> It's Administrator-only — hidden for the other roles and refused server-side (403).

**The cast** (switch via the user selector, top‑right — it stamps every action and the audit trail):

| Actor | Role | Does |
|---|---|---|
| **Dana Cole** | Reviewer (abstractor) | Locates/confirms findings, first sign‑off, escalates |
| **Sam Ortiz** | Over‑reader | Independent **blind** second read + QA over‑read (must differ from the signer) |
| **Morgan Lee** | Administrator | Loads rules packs & the VSD, assigns work, all review actions |
| **Riley Kim** | Auditor | **Read‑only** — findings, audit trail, analytics; no writes |

**The members** the seed created: **Victor Nolan** (signed off, disputed on over‑read),
**Priya Anand** (dialysis exclusion applied), **Derek Cole** (out‑of‑window, escalated).
You will add **Grace Whitman** live.

> One‑line pitch: *"Configured from published NCQA specs and the licensed Value Set
> Directory, this locates each measure's data in the chart with page‑anchored evidence,
> routes it through an independent human review with separation of duties, and keeps a
> complete audit trail — proposal‑only, never an automated determination."*

---

## Act 1 · Foundations — the Administrator (proves it runs on *real* rules)

> Switch user to **Morgan Lee · Administrator**.

### 1.1 Rules admin — `Rules`
- **Do:** open **Rules**. Expand **CBP — Controlling High Blood Pressure**.
- **Say:** "The abstraction rules come from the published **NCQA HEDIS spec**. Each measure
  lists the exact data elements a reviewer must find, the exclusions that retire a member,
  the **value‑set names**, and the timing windows — all traceable to the spec, version‑stamped
  by measurement year."
- **Point out:** the **upload → generate** control (an admin drops in the NCQA spec PDF and
  the `hedis-spec-to-rules` skill builds the pack, then validates it). This is how real years
  are loaded — **not** hand‑authored. Note the `Administrator`‑only badge.
- **Proves:** production‑ready rule sourcing, versioned per year, read‑only/traceable.

### 1.2 Value Set Directory — `VSD`
- **Do:** open **VSD**. Search `90935`, then `N18.6`.
- **Say:** "The spec references value sets **by name**; the exhaustive code lists live in the
  **licensed NCQA Value Set Directory**. We load it as a separate, year‑scoped artifact with an
  **effective date range** — never embedded in the shareable rules pack, never in exports."
- **Link it back:** on **Rules**, click a value‑set name (e.g. **Dialysis**) → it deep‑links
  into the VSD codes. That closes the "names → codes" loop.
- **Proves:** the licensed code dictionary, effective‑dated, admin‑loaded, cross‑linked, and
  kept internal.

### 1.3 One system, three reference inputs
- **Say:** "Three clean inputs, each from its own source of truth: the **rules pack** (what to
  look for, from the spec), the **VSD** (codes, licensed), and the **priority‑config** (Star/
  plan weights). Swappable per year without touching the app."

---

## Act 2 · Follow Grace Whitman, start to end

### 2.1 Upload — the Reviewer receives a provider‑submitted chart
> Switch to **Dana Cole · Reviewer**.
- **Do:** **Upload profile** → choose `sample_charts/grace_whitman.txt`, member **Grace Whitman**,
  DOB **1958‑05‑12**, age **69**, workflow **Gap closure**, measure **CBP** = *gap*. Submit.
- **Say:** "A provider submitted this chart to close an open BP gap. On intake we assign a
  **stable document ID**, store the original **read‑only** (system of record), extract the text
  with a **page‑offset map**, and screen for **multiple members** to prevent mis‑attribution."
- **Proves:** A1 (immutable source + stable ID), A12 (multi‑patient screen).

### 2.2 Analyze — locate the data + the exclusions
- **Do:** on Grace's page, **Analyze** CBP.
- **Say:** "Two passes. **Pass 1** (Claude Opus 4.8) extracts each data element with a *verbatim*
  quote and confidence. **Pass 2** is deterministic — a negation‑aware scan for exclusions,
  every hit traced to a named value set. Nothing is inferred; if it isn't documented, it's
  `null`, confidence 0."
- **Proves:** A7 (confidence), A9 (all values retained), A10 (no fabrication).

### 2.3 Review — the evidence workspace
- **Do:** **Review evidence →**. Walk the split panel.
- **Show, one by one:**
  - **Gap‑closure gate** banner — member name + DOB confirmed (wrong‑member charts hard‑stop).
  - **Proposed outcome** — *closable on documentation* (a suggestion, not a determination).
  - Click a finding → the chart **highlights** the exact sentence (page‑anchored citation).
  - **Compliance advisory** on Systolic — "Meets threshold — 134 < 140," clearly labeled
    *reviewer aid, not a determination*.
  - **Performing provider credential** — captured as evidence (T. Reyes, MD), cited to the note.
  - **View original ↗** — the untouched source PDF/text.
- **Do:** Confirm the readings; **Modify** one if you like; note the **confidence gate** would
  block sign‑off while any weak/unanchored finding is undecided.
- **Say:** "Every proposal is confirm / modify / reject, and every action is attributed and
  server‑timestamped to the audit log with the original AI value preserved."
- **Proves:** A2 (citations), A3 (actor+timestamp), A4 (rules + VSD version stamped), A8 (credential).

### 2.4 Sign off — the human determination
- **Do:** **Accept result** (or Override…). It records `final_status = gap_closed` and logs it.
- **Say:** "Nothing counts downstream until a human signs off. The reviewer's HEDIS
  determination — gap closed / gap open / exclusion applied / needs more info — is the
  record, never the AI's."
- **Proves:** A6 (human approval gate, logged).

### 2.5 Independent over‑read — the Over‑reader (separation of duties)
> Switch to **Sam Ortiz · Over‑reader**.
- **Do:** back on Grace's review, **Blind 2nd read →**.
- **Say:** "A *different* reviewer reads it **blind** — the first reviewer's decisions and
  sign‑off are hidden — and we **capture whether the two independent reads agree**. The system
  **enforces** that the over‑reader cannot be the person who signed off (separation of duties,
  which RBAC alone can't express)."
- **Do:** confirm independently, sign off; then in **QA queue**, mark Grace **QA pass**.
- **Proves:** independent blind double‑read + agreement capture + SoD + QA over‑read.
  *(We deliberately stop at agreement capture — computing a reliability statistic like Cohen's kappa is out of scope, X‑9.)*

---

## Act 3 · The rest of the panel (breadth, 90 seconds)

> Switch back to **Dana Cole** (or **Morgan Lee**). Open **Patients** / **QA queue**.

- **Priya Anand** — chart shows **active dialysis / ESRD**. Open her review: three
  **exclusion candidates**, each traced to the **Dialysis / ESRD** value sets (click → VSD codes).
  Signed off as **exclusion applied** — the exclusion retires the member even though a BP was
  documented. *The human chose the exclusion path.*
- **Derek Cole** — his BP is dated **05/2025**, outside MY2027. The reviewer sees the **⏱ timing
  banner** ("present but may not count"), and it's **⚑ escalated** for a current record. Sign‑off
  is gated until timing is resolved.
- **Victor Nolan** — signed off **gap-closed**, but the **blind second read** landed on
  **gap-open** — a real disagreement, surfaced (not hidden), and QA flagged **needs rework**.

---

## Act 4 · Operations & analytics — the lead / Administrator

### 4.1 Worklist — `Worklist`
- **Say:** "Open gaps ranked by **measure weight × evidence yield × deadline urgency**
  (Star‑informed, plan‑overridable). Reviewers work the highest‑value charts first — a ranked
  worklist, never a compliance rate."

### 4.2 Analytics — `Analytics`
- **Say:** "The review process measuring itself: **AI‑vs‑final agreement** (~91% here), the one
  **edit** that drove a **confidence‑gate recommendation** ('raise to catch high‑confidence
  values that get corrected'), **over‑read concurrence**, and **independent double‑read
  agreement** from the blind second reads — surfacing exactly where two reviewers diverged
  (Victor: gap‑closed vs gap‑open). Agreement is *captured*; we don't compute a reliability
  statistic (X‑9)."
- **Proves:** a closed quality loop that tunes the AI and the gate over time.

---

## Act 5 · Auditor & compliance — read‑only

> Switch to **Riley Kim · Auditor**. Notice **every write control disappears**.

- **Do:** open any member → **Audit trail ↗**.
- **Say:** "A complete, append‑only trail across the member's measures: who/what proposed each
  value, every human confirm/modify/reject, the sign‑off, the over‑read — each with the AI
  baseline preserved beside the final value, and the **rules + VSD version** applied."
- **Do:** **View original ↗** (immutable source); show **Export confirmed (CSV)** and
  **Supplemental data** — value‑set **names only**, never the licensed codes.
- **Proves the audit map (A1–A12):** immutability + stable IDs (A1), citations (A2), actor +
  timestamp (A3), evidence trace + rules/VSD version (A4), escalation logged (A5), human approval
  (A6), confidence retained (A7), provider credential (A8), gap-open (care gap remains) values kept (A9), no
  fabrication (A10), multi‑patient flag (A12). (User‑management logging, A11, is the platform's
  RBAC — this app defines the *roles*; the platform enforces users/auth.)

---

## Close · Why this is production‑ready

- **Real rules, real codes, versioned:** NCQA spec → rules pack, licensed VSD → codes, both
  year‑scoped and stamped on every finding.
- **Human‑in‑the‑loop, proposal‑only:** nothing counts without a sign‑off; the AI never decides
  compliance or selects a code.
- **Independent quality:** blind double‑read + QA over‑read with **enforced separation of
  duties**, plus double‑read agreement capture and gate‑tuning analytics.
- **RBAC:** four roles with a permission matrix and SoD — the contract a platform RBAC configures to.
- **Auditable end‑to‑end:** immutable source, page‑anchored citations, full actor/timestamp trail.
- **Portable skills:** the analysis, workflow, and VSD logic live in reusable skills, not buried in the app.

*Reset any time with the Administrator's **↻ Reset & reseed demo** button, or `python
seed_demo.py --reset`. Add a valid Anthropic key in the project
`anthropickey` file for live Pass‑1 extraction; without it the app falls back to an offline
heuristic and everything else is identical.*
