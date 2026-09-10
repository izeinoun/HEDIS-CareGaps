# Rules-pack schema (the shared contract)

> **Contract version: `schema_version` 1.1.** (1.1 is additive over 1.0 — it only adds the
> optional `evidence_role` field on data elements; 1.0 packs stay valid and consumers should
> accept both.) This file is the **canonical**
> definition of the rules pack. It is bundled **identically** in both skills:
> - `hedis-spec-to-rules/rules-pack-schema.md` (canonical source), and
> - `hedis-rules-to-findings/rules-pack-schema.md` (verbatim copy).
>
> The two skills complement each other only while both copies match. If you edit
> this file, bump `schema_version` and update the copy in the other skill in the
> same change. A quick check: `diff` the two files — they must be identical.

A rules pack is one JSON object. It is the **output** of `hedis-spec-to-rules`
and the **input** of `hedis-rules-to-findings`. It is fully self-contained — a
downstream reader needs nothing but the pack.

## Top-level shape

```jsonc
{
  "schema_version": "1.1",
  "source": {
    "document_title": "HEDIS MY2027 Volume 2: Technical Specifications for Health Plans",
    "measurement_year": "MY2027",   // never merge measures from different years — this is the pack's "version"
    "publisher": "NCQA",
    "document_url": "https://store.ncqa.org/...",  // OPTIONAL. link to the source spec, or a stored reference to the uploaded PDF; powers the admin screen's "view source" link
    "pages": "13-420",              // overall range covered
    "extracted_at": "2026-09-08",   // pass the date in; do not guess it — this is the pack's build date
    "disclaimer": "Derived from published NCQA HEDIS technical specifications to locate chart evidence. Not a certified compliance engine; all findings are proposals for human review."
  },
  "universal_exclusions": [ /* Exclusion objects, see below */ ],
  "measures": [ /* Measure objects, see below */ ]
}
```

## Measure object

```jsonc
{
  "measure_id": "CBP",                 // NCQA abbreviation; the stable key WITHIN a year
  "measure_name": "Controlling High Blood Pressure",
  "hybrid": true,                       // true = chart review allowed; false = admin-only
  "source_pages": "pp. 120-128",       // traceability back to the spec
  "eligible_population": {
    "ages": "18-85",
    "event_or_diagnosis": "At least one outpatient/telephone/e-visit with a hypertension diagnosis...",
    "continuous_enrollment": "The measurement year",
    "anchor_date": "December 31 of the measurement year"
  },
  "measurement_period": {
    "window": "The measurement year (Jan 1 - Dec 31)",
    "lookback": "None"                  // or e.g. "Colonoscopy: 10 years; FIT-DNA: 3 years"
  },
  "numerator": "The most recent BP reading in the measurement year is < 140/90 mmHg.",
  "data_elements": [ /* DataElement objects */ ],
  "exclusions": [ /* Exclusion objects specific to this measure */ ]
}
```

## DataElement object

The structured fields a reviewer keys in — not prose.

```jsonc
{
  "key": "systolic",                   // snake_case, unique within the measure
  "label": "Systolic",
  "type": "numeric",                   // date | numeric | text | code | boolean | result
  "required": true,
  "unit": "mmHg",                      // or null
  "options": null,                     // or ["Screening","Diagnostic",...] for enumerated text
  "timing": "Most recent reading in the measurement year",
  "compliance_hint": "Meets threshold when < 140",   // descriptive only — never executed
  "keywords": ["blood pressure", "BP", "systolic"],  // phrases likely to appear in a chart
  "evidence_role": null                 // OPTIONAL. null | "provider_credential" | "provider_signature" — marks an element whose value is a performing-provider credential/signature captured as evidence where the measure requires it (A8). Default null = an ordinary clinical value.
}
```

Rules for elements:
- Pick the minimum set of fields that, once located, let a human decide the
  measure — a BP is `date` + `systolic` + `diastolic`, not a paragraph.
- `required` marks the fields without which the abstraction is incomplete.
- `compliance_hint` records the threshold for the reviewer; it is **not** a
  decision rule and must never be auto-applied.
- `evidence_role` (optional) marks a **credential/signature evidence** element for measures
  that require the performing provider's signature or credential. Set `"provider_credential"`
  or `"provider_signature"`; the downstream finding carries the role so the reviewer sees it
  as credential evidence, with the same citation/anchor as any element. Omit / `null` for
  ordinary clinical values.

## Exclusion object

The findings that remove a member from the denominator, plus inline codes/keywords
so a text scan can run without the VSD.

```jsonc
{
  "key": "esrd_dialysis",
  "label": "ESRD, dialysis, or kidney transplant",
  "scope": "required",                 // required = mandatory exclusion; optional = optional
  "value_sets": ["ESRD Diagnosis", "Dialysis", "Dialysis Procedure", "Kidney Transplant"],
  "codes": [                            // ONLY codes the PDF actually prints; else []
    { "system": "ICD-10-CM", "code": "N18.6", "description": "End stage renal disease" }
  ],
  "keywords": ["end stage renal disease", "esrd", "dialysis", "kidney transplant"],
  "applies_when": null,                 // OPTIONAL. An age / eligibility gate the SCAN does not enforce — surfaced for the reviewer. e.g. "Age 66 or older".
  "note": "ESRD, chronic dialysis, or a functioning kidney transplant retires the member",
  "timing": "Any time in the member's history through the end of the measurement year",  // OPTIONAL. The window in which evidence must fall to count. Copy the spec's window intent verbatim (member history / the measurement year / as of the anchor date). The scan does NOT check dates — it surfaces this so the reviewer can.
  "compound": false,                    // OPTIONAL. true when a single documented mention is NOT sufficient — the criterion needs two or more distinct findings (e.g. advanced illness AND frailty; a bilateral mastectomy OR two unilateral mastectomies). A downstream hit on a compound rule is surfaced as partial, never as a settled exclusion; describe exactly what is required in `note`.
  "source_hint": "medical_record",      // OPTIONAL. Where the spec establishes this: "medical_record" | "administrative" | "both" | "unstated". "administrative" = an enrollment/claims/membership-file fact (e.g. a long-term-institutional criterion, or deceased status) that chart text alone cannot establish — a text hit is flagged for file confirmation, not proposed as sufficient. Omit when unknown; absence behaves like "medical_record".
  "threshold": null                     // OPTIONAL. null, or { "count": 2, "distinct": "date_of_service" } when a SINGLE concept must appear N times (e.g. two advanced-illness outpatient visits on different dates). For AND/OR logic across DIFFERENT concepts, use `compound` instead. A single text hit is then a PARTIAL match the reviewer must confirm, never a complete one.
}
```

- `value_sets` are copied **verbatim** from the spec — names are the durable link
  to the NCQA Value Set Directory even when no codes are printed inline.
- `keywords` are what the downstream deterministic scanner matches on, so they
  must be real clinical phrases (lowercase, ≥ ~4 chars to avoid noise).
- `timing` records the **window** the spec attaches to the exclusion. HEDIS windows
  vary per exclusion — some are "any time in the member's history" (transplant,
  bilateral mastectomy), some are "during the measurement year" (pregnancy,
  hospice), some are "as of the anchor date" (age-gated frailty). Capture it so the
  reviewer can check dates; the scan itself is date-blind.
- `compound` marks an exclusion that a **single mention cannot settle** because the
  spec requires two or more distinct findings — an AND across concepts (advanced
  illness *and* frailty), or an OR whose branches themselves need more than one hit
  (bilateral mastectomy *or* two unilateral). Set it `true` and spell out the full
  requirement in `note`; downstream surfaces such a hit as partial, never complete.
- `source_hint` records **where the spec says the criterion is established**, so a
  chart-text scanner does not propose an administrative fact (an enrollment- or
  claims-file lookup) as though a chart note settled it. Set `"administrative"`
  for criteria defined as a file value; a downstream chart hit is then surfaced
  only as "confirm via file". Leave it off for ordinary chart-findable exclusions.
- `threshold` records a **count requirement on one concept** the spec states (e.g.
  "at least two indications on different dates of service"). A single keyword hit
  cannot satisfy it, so downstream marks such a hit partial and defers the count to
  the reviewer. Use `compound` (not `threshold`) when the requirement spans two
  different concepts.
- Universal exclusions (hospice, palliative, advanced-illness-with-frailty) go in
  the top-level `universal_exclusions` array, not per measure. **Death is never a
  chart exclusion** — it comes from eligibility data.

## JSON Schema (structural validation)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["schema_version", "source", "measures"],
  "properties": {
    "schema_version": { "type": "string" },
    "source": {
      "type": "object",
      "required": ["measurement_year"],
      "properties": {
        "document_title": { "type": "string" },
        "measurement_year": { "type": "string" },
        "publisher": { "type": "string" },
        "document_url": { "type": "string" },
        "pages": { "type": "string" },
        "extracted_at": { "type": "string" },
        "disclaimer": { "type": "string" }
      }
    },
    "universal_exclusions": { "type": "array", "items": { "$ref": "#/$defs/exclusion" } },
    "measures": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["measure_id", "measure_name", "hybrid", "data_elements"],
        "properties": {
          "measure_id": { "type": "string" },
          "measure_name": { "type": "string" },
          "hybrid": { "type": "boolean" },
          "source_pages": { "type": "string" },
          "eligible_population": { "type": "object" },
          "measurement_period": { "type": "object" },
          "numerator": { "type": "string" },
          "data_elements": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["key", "label", "type", "required"],
              "properties": {
                "key": { "type": "string" },
                "label": { "type": "string" },
                "type": { "enum": ["date", "numeric", "text", "code", "boolean", "result"] },
                "required": { "type": "boolean" },
                "unit": { "type": ["string", "null"] },
                "options": { "type": ["array", "null"], "items": { "type": "string" } },
                "timing": { "type": "string" },
                "compliance_hint": { "type": "string" },
                "keywords": { "type": "array", "items": { "type": "string" } },
                "evidence_role": { "enum": ["provider_credential", "provider_signature", null] }
              }
            }
          },
          "exclusions": { "type": "array", "items": { "$ref": "#/$defs/exclusion" } }
        }
      }
    }
  },
  "$defs": {
    "exclusion": {
      "type": "object",
      "required": ["key", "label", "scope", "value_sets"],
      "properties": {
        "key": { "type": "string" },
        "label": { "type": "string" },
        "scope": { "enum": ["required", "optional"] },
        "value_sets": { "type": "array", "items": { "type": "string" } },
        "codes": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "system": { "type": "string" },
              "code": { "type": "string" },
              "description": { "type": "string" }
            }
          }
        },
        "keywords": { "type": "array", "items": { "type": "string" } },
        "applies_when": { "type": ["string", "null"] },
        "note": { "type": ["string", "null"] },
        "timing": { "type": "string" },
        "compound": { "type": "boolean" },
        "source_hint": { "enum": ["medical_record", "administrative", "both", "unstated"] },
        "threshold": {
          "type": ["object", "null"],
          "properties": {
            "count": { "type": "integer" },
            "distinct": { "type": "string" }
          }
        }
      }
    }
  }
}
```
