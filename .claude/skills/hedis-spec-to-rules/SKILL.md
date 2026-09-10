---
name: hedis-spec-to-rules
description: >-
  Convert a published NCQA HEDIS technical-specification PDF into a portable,
  machine-usable "rules pack" (JSON) — the structured data elements a chart
  abstractor must find per measure, plus the exclusion rules (named value sets +
  keywords) and timing/look-back windows. Use when the user supplies a HEDIS /
  NCQA measure specification PDF (or its extracted text) and wants abstraction
  rules extracted for locating measure data in medical records. The output is the
  input to the companion skill `hedis-rules-to-findings`.
---

# HEDIS spec → rules pack

Turn a **published, publicly available NCQA HEDIS technical specification** for
health plans into a **rules pack**: a self-contained JSON file that tells a
downstream reader exactly what to look for in a medical record, without needing
the original PDF or any database.

The pack is standalone and provider-agnostic: it carries everything a downstream
reader needs (data elements, exclusion rules, value-set names, timing windows) so
it can be consumed with no database and no access to the original PDF.

**Shared contract.** The pack you emit MUST conform to
`rules-pack-schema.md` (`schema_version` 1.0). That file is the
**canonical** contract; the companion skill `hedis-rules-to-findings` bundles a
verbatim copy and reads packs against it. The two skills complement each other
only while both copies of the schema are identical — read the schema before
producing a pack, and if you change it, bump the version and update the copy in
the other skill.

## When to use

- The user hands you a HEDIS/NCQA measure spec PDF (e.g. "HEDIS MY2027 Volume 2")
  and wants the rules for one or more measures.
- The user wants to refresh a set of abstraction rules from a newly published
  measurement year.
- The user has spec *text* already extracted and wants it structured into rules.

## What a rules pack is NOT

- Not a compliance engine and not certified. It captures *what to locate*, not a
  numerator determination. Downstream logic must always treat findings as
  proposals for a human to rule on.
- Not the NCQA Value Set Directory. Spec PDFs reference value sets **by name**;
  the exhaustive code lists live in a separate VSD. Capture value-set **names**
  always, and inline any codes the PDF actually prints (plus plain-language
  **keywords**) so a downstream text scan has something to match.

## Procedure

1. **Read the source.** If given a PDF, read it with the Read tool (use the
   `pages` parameter for large specs; process one measure's page range at a
   time). If given extracted text, use it directly. Record the document title,
   measurement year, publisher, the page range each measure came from, and — when
   available — a `document_url` link to the source spec (or the stored uploaded PDF),
   so an admin screen can link back to it. Every rule must be traceable to its
   source page.

2. **For each measure, extract these fields** (see
   `rules-pack-schema.md` for the full field list and types):
   - **Identity**: `measure_id` (the NCQA abbreviation, e.g. `CBP`, `BCS-E`),
     `measure_name`, and whether it is `hybrid` (chart review permitted) or
     administrative-only.
   - **Eligible population**: ages, event/diagnosis criteria, continuous
     enrollment, anchor date — as concise prose. This scopes who the measure
     applies to.
   - **Measurement period & look-back**: the reporting window and any modality-
     specific look-back (e.g. colonoscopy = 10 years).
   - **Numerator (in plain language)**: what closes the care gap (numerator met). Keep it
     descriptive, never as executable logic.
   - **`data_elements[]`** — the heart of the pack: the structured fields a
     reviewer keys in, not prose. Each element has `key`, `label`,
     `type` (one of `date`, `numeric`, `text`, `code`, `boolean`, `result`),
     `required`, optional `unit`, `options`, a `timing` note (the window that
     makes it count), a `compliance_hint` (e.g. "Gap closed when < 140"), and
     `keywords` (phrases likely to appear in a chart: "blood pressure", "BP").
     When a measure **requires the performing provider's signature or credential**
     as evidence, add it as a data element with `evidence_role: "provider_credential"`
     (or `"provider_signature"`) and credential keywords (e.g. "MD", "DO", "NP", "PA",
     "electronically signed", "signed by"). It is then captured with a citation like any
     element — no special machinery — satisfying the "credential where required" rule.
   - **`exclusions[]`** — the highest-value findings, because they retire the
     case. Each has `key`, `label`, `scope` (`required` mandatory or `optional`),
     the referenced `value_sets` (**by name, verbatim from the spec**), any
     `codes` the PDF prints inline (`{system, code, description}`), `keywords`
     (plain-language terms for a text scan), `applies_when` (e.g. "Age 66+"), and
     a `note`. Optional fields worth capturing when the spec states them, because
     they are what keep a downstream chart hit from reading as a settled exclusion:
     - `timing` — the **window** the exclusion attaches to (member history / the
       measurement year / as of the anchor date). HEDIS windows differ per
       exclusion; capture the spec's window so the reviewer can check dates.
     - `compound` — set `true` when a **single mention is not sufficient** because
       the spec requires two or more distinct findings: an AND across concepts
       (advanced illness *and* frailty for members 66+) or an OR whose branches
       each need more than one (bilateral mastectomy *or* two unilateral). Spell
       out the full requirement in `note`.
     - `source_hint` — set `"administrative"` when the criterion is a file value
       (an enrollment/claims/membership-file lookup, e.g. a long-term-institutional
       criterion, or deceased status) that chart text cannot settle, so a chart hit
       is flagged for file confirmation rather than proposed.
     - `threshold` — `{ "count": N, "distinct": "date_of_service" }` when a *single*
       concept must appear N times (e.g. two advanced-illness outpatient visits on
       different dates). For AND/OR logic across different concepts use `compound`.

3. **One candidate per distinct exclusion.** When the spec groups several
   exclusions under a single "Denominator Exclusions" heading — e.g. deceased
   members, hospice, palliative care, an institutional criterion, and frailty in
   one block — that is *five* exclusions, not one. They differ in value sets,
   scope, and how they are established. Split them; never collapse a heading into a
   single rule.

4. **Capture universal exclusions once — but only what is genuinely broad.** Put an
   exclusion in the top-level `universal_exclusions` array (instead of repeating it
   per measure) when the spec applies it across measures with only window/age
   variation. Deceased members and hospice are the broadly-required cases; **death
   is never a chart exclusion** (it is established from enrollment/eligibility data,
   not a chart value set, so it has no place in a pack meant for locating chart
   evidence). Be careful with **palliative care** and **advanced illness + frailty**:
   NCQA applies these only to a *defined subset* of measures, so mark their real
   `applies_when` (e.g. "Age 66 or older") and know that downstream will still tag
   any universal hit with a "confirm this measure lists it" caveat. When an
   exclusion truly belongs to one measure's clinical logic, keep it under that
   measure's `exclusions[]`, not in `universal_exclusions`.

5. **Derive keywords, don't invent codes.** Keywords are plain-language phrases a
   clinician would write; derive them from the spec's own descriptions and value-
   set names. Never fabricate a specific ICD/CPT/LOINC code — only record codes
   the PDF actually prints. If the spec only names a value set, record the name
   and leave `codes` empty (the downstream VSD supplies them).

6. **Validate and emit.** Write the pack as JSON. Run the bundled validator to
   check structure and flag empties:
   `python validate_pack.py <pack.json>` (run it from this skill's
   directory, or pass an absolute path to the script). Fix anything it reports.

7. **Report coverage honestly.** Report measures captured, element and exclusion
   counts, any value sets referenced by name only (no inline codes), and the source
   pages. **If the extraction is partial — some measures or sections not processed,
   a truncated table, a value set you could not locate — say so explicitly.** A
   partial pack that is labelled partial is useful; a partial pack presented as
   complete is a liability. State plainly that the pack is derived from published
   specs for locating chart evidence and is not a certified compliance artifact.

## Guardrails (non-negotiable)

- **Read the document; never recall it.** Every rule must be traceable to a page
  of the supplied spec. Never state a requirement, age band, value set, or code
  the document does not contain, and never carry knowledge forward from a prior
  year — an extraction is *of one document*, and contamination across years is
  silent and hard to detect.
- **Year-agnostic instructions.** This skill knows the *anatomy* of a HEDIS spec,
  not the *content* of any measure or year. A useful test: if a sentence in this
  skill file would become false when a new measurement year is published, it does
  not belong here. Measure IDs, ages, value-set names, and code lists live only in
  the pack you emit, never in the instructions.
- **Restate prose; copy codes verbatim.** Put `label`, `numerator`, and population
  text in your own words (spec prose is copyrighted). Codes are facts — transcribe
  them exactly, and only the ones the PDF prints.
- **Internal artifact.** A rules pack is derived from a spec the organization has
  licensed; do not embed full value-set contents, and treat the pack as an internal
  artifact, not something to publish or use to produce a reportable rate.

## Output location

Default to writing `hedis-rules-pack.<measurement-year>.json` in the directory
the user is working in (or a path they specify). Keep one pack per measurement
year — measure codes are **not stable across years**, so never merge years.

## Consuming the pack (admin UI)

The pack is meant to be surfaced in a **read-only Rules admin screen**: a version/date
header (from `source.measurement_year` + `extracted_at`), the measures with their data
elements and exclusions, full-text search, a view-source link (`source.document_url`),
and an **upload→generate** intake where an admin uploads the NCQA PDF and this skill
builds the pack. `rules-admin-screen.md` has the field-by-field build direction. The
screen never edits the pack — corrections come from regenerating off the source.

## Grounding references

- `rules-pack-schema.md` — the complete field-by-field contract and a
  JSON Schema. This is the authoritative definition of the output.
- `example-rules-pack.json` — a worked example (CBP + BCS-E). Use it as
  the shape to follow.
- `validate_pack.py` — the bundled structural + sanity validator; run it on
  every pack before reporting.
- `rules-admin-screen.md` — UI-build direction for the read-only Rules admin screen
  the pack feeds (version/date header, measures + exclusions, search, view-source
  link, and the upload→generate intake). Read this when building or reviewing that
  screen.
