---
name: hedis-vsd
description: >-
  Turn the licensed NCQA HEDIS Value Set Directory (VSD) workbook into a portable,
  year-scoped "value-set pack" (JSON) that maps each value-set NAME to its exhaustive
  code list. The rules pack from `hedis-spec-to-rules` carries value sets by name only;
  this is the companion code dictionary that resolves those names to codes and validates
  a captured code's membership. Deterministic ingestion (CSV/XLSX), effective-year scoped,
  and an internal licensed artifact kept separate from the shareable rules pack. Use when
  a user supplies an NCQA VSD export and wants the code lists behind the rules pack's value
  sets, or a read-only directory to browse and validate codes against.
---

# HEDIS Value Set Directory → value-set pack

The third reference-data producer in the HEDIS toolset, alongside `hedis-spec-to-rules`
(the rules pack — *what to look for*) and `hedis-gap-workflow` (priority/weights):

```
hedis-spec-to-rules  → rules pack       (value sets by NAME + inline codes the PDF prints)
hedis-vsd  (this)    → value-set pack   (value-set NAME → exhaustive codes, per year)
                       consumed by the analysis skill / reviewer to resolve names → codes
```

The `hedis-spec-to-rules` skill is explicit that the rules pack is **not** the VSD:
value sets are referenced by name, and *"the exhaustive code lists live in a separate
VSD."* This skill produces that separate artifact.

## Why it is its own skill (and separate from the rules pack)

- **Different source, deterministic.** The VSD is a structured **workbook (Excel/CSV)**,
  not a spec PDF — ingestion is deterministic parsing (`build_vsd_pack.py`), no LLM.
- **Licensed content.** The VSD is licensed by NCQA. Keeping it a **separate, internal
  artifact** (never embedded in the shareable rules pack, never redistributed) honors the
  rules-pack guardrail *"do not embed full value-set contents; treat the pack as internal."*
- **Year-scoped.** Codes change per measurement year — **one value-set pack per year**,
  carrying an explicit `effective` date range, linked to the rules pack by `measurement_year`.

## Procedure

1. **Ingest.** Point `build_vsd_pack.py` at a VSD export (`.csv` or `.xlsx`). It maps the
   common column headers (value set name, code system, code, description, OID) tolerantly,
   groups rows by value-set name, and transcribes codes **verbatim** — nothing inferred.
   ```
   python build_vsd_pack.py --input VSD.csv --year MY2027 --loaded-at 2026-09-10 --out value-set-pack.MY2027.json
   ```
2. **Validate.** The builder runs structural + sanity checks (measurement year present,
   every code has a system+code, value sets non-empty) and reports them; fix and re-run.
3. **Store one per year**, keyed by `measurement_year`. Never merge years.

## Consuming it (`vsd_lookup.py`)

The query API the app and reviewer use — reference and **code-membership validation**,
never code selection for submission:
- `codes_for(pack, name)` — the code list behind a value-set name (reviewer reference).
- `contains_code(pack, name, code, system)` — does a captured code belong to the named set?
  (dot/dash/case-insensitive; `N18.6` == `n186`).
- `find_value_sets_for_code(pack, code, system)` — reverse lookup ("which set has CPT 90935?").
- `search(pack, q)` / `summary(pack)`.

## How it fits the analysis skill

The rules pack keeps carrying value sets by **name**; at review time the app resolves those
names to codes via the value-set pack — to show the reviewer the candidate codes and to
**validate** a code they capture (e.g. for a `provider_credential` or an exclusion). It does
**not** change the analysis skill's stance: no automated code selection, proposals only. On
narrative charts codes are rare (they live in claims), so start with reference + validation;
code *matching* in text is a secondary signal for later, once claims are ingested.

## Guardrails (non-negotiable)

- **Licensed, internal, never redistributed.** The value-set pack is not shared, not
  embedded in the rules pack, and its codes are **never included in reviewer/plan exports**
  (exports stay value-set-*names* only).
- **Transcribe, never infer.** Copy codes exactly from the directory; never fabricate a code
  or guess a value set's contents.
- **One pack per measurement year.** Codes are not stable across years — never merge.
- **Reference & validation, not determination.** Answers membership/reference questions for a
  human; it does not select codes or decide compliance.

## Grounding references

- `value-set-pack-schema.md` — the value-set-pack contract.
- `example-value-set-pack.json` — an ILLUSTRATIVE sample (a few codes per set) for the
  rules-pack example's value sets.
- `build_vsd_pack.py` — the deterministic ingester + validator.
- `vsd_lookup.py` — the reference / code-membership-validation query API.
- `vsd-admin-screen.md` — the read-only VSD admin screen build direction.
