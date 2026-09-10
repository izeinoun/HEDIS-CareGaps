# HEDIS Care-Gap Analysis (payer side)

A payer-side web app for HEDIS measure data extraction and care-gap analysis. You
upload a patient profile (a PDF of the member's medical records) together with the
HEDIS measures assigned to that member and their gap status. The app parses the
chart, **locates the data for each measure and the evidence needed to close the
gap — each with a source anchor (page + character range)** — and hands you anchored,
proposal-only findings to confirm, modify, or reject.

Everything is a proposal for a human reviewer. The app never decides compliance,
numerator status, or final exclusion application, and never emits a rate.

## How it uses the two skills

The app is a thin application layer over the two bundled skills in
`../.claude/skills/`; it imports their code directly so its behaviour stays in sync:

- **`hedis-spec-to-rules`** — the *Rules admin* screen. It renders a rules pack
  (measures, data elements, exclusions, value sets) and offers an **upload → generate**
  intake: drop in an NCQA spec PDF and the app builds a pack with Claude, then runs the
  skill's bundled `validate_pack.py` and shows the coverage report. Seeded with the
  skill's MY2027 example pack (CBP + BCS-E).
- **`hedis-rules-to-findings`** — the analysis engine. **Pass 1** (data-element
  extraction, the judgement half) runs against Claude; **Pass 2** (the deterministic,
  negation-aware exclusion scan) and all anchoring reuse the skill's authoritative
  `anchor_findings.py` unchanged. Supports both `chase` (plan pulls the record) and
  `gap_closure` (provider submits — adds a member-match gate and a proposed gap outcome).

## Running

```bash
cd hedis-app
../.venv/bin/python app.py       # http://127.0.0.1:5001
```

The Anthropic API key is read automatically from the project-root `anthropickey`
file (or the `ANTHROPIC_API_KEY` env var). Model: `claude-opus-4-8`.

**No key?** The app still runs end to end: Pass-1 falls back to a built-in,
dependency-free *heuristic* extractor (keyword + type scan) so you can exercise the
full pipeline offline. The deterministic exclusion scan and anchoring are identical
either way. The header pill shows which Pass-1 provider is active.

## Flow

1. **Rules** (`/rules`) — confirm a pack is loaded (or generate one from a spec PDF).
2. **Upload profile** (`/upload`) — chart PDF + member details + the assigned measures
   and their gap status + workflow (chase / gap closure).
3. **Patient** (`/case/<id>`) — analyze open measures (gap-closed/excluded are skipped
   unless you Force a re-review).
4. **Review** (`/review/<id>/<measure>`) — split panel: the chart on the left with
   clickable evidence highlights, the proposals on the right. Confirm / modify / reject
   each finding; decisions are stored for the AI-vs-final audit.

## Layout

```
app.py                     Flask routes + storage + key loading
engine/pdf_extract.py      PDF/txt -> text + page-offset map
engine/extract_elements.py Pass 1 (Anthropic + offline heuristic)
engine/findings_engine.py  wraps the skill's anchor_findings.py
engine/generate_pack.py    upload -> rules pack (wraps validate_pack.py)
templates/ static/         UI
data/packs|cases|charts|findings   file-based storage
```

## What this is not

Not a certified compliance engine and not the NCQA Value Set Directory. Rules packs
are derived from published specs for locating chart evidence; findings are proposals
for review. Data is stored unencrypted on the local filesystem — do not load real PHI.
