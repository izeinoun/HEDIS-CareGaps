# Value-set-pack schema (`vsd_version` 1.0)

A value-set pack is one JSON object: the code lists behind the rules pack's value-set
names, for **one measurement year**. It is a **licensed, internal** artifact — kept
separate from the shareable rules pack and never redistributed.

```jsonc
{
  "vsd_version": "1.0",                       // this schema's contract version
  "source": {
    "publisher": "NCQA",
    "directory_title": "HEDIS MY2027 Value Set Directory",
    "measurement_year": "MY2027",             // links to the rules pack by year; never merge years
    "effective": { "start": "2027-01-01", "end": "2027-12-31" },  // the effective date range
    "loaded_at": "2026-09-10",                // pass in; not guessed
    "license": "Licensed NCQA VSD content — internal use only, not for redistribution."
  },
  "value_sets": {
    "Dialysis": {                             // key = value-set NAME, verbatim (matches the rules pack)
      "oid": "2.16.840.1.113883.3.464.1004.9001",  // NCQA/VSAC OID, or null
      "codes": [
        { "system": "CPT", "code": "90935", "description": "Hemodialysis, single evaluation" }
      ]
    }
  }
}
```

## Rules

- **Keys are value-set names, verbatim** — they must match the names the rules pack carries
  in `exclusions[].value_sets` (and any `data_elements` that reference a set), so a name
  resolves to codes by exact string.
- **`measurement_year` is the version.** One pack per year; codes are not stable across years.
- **`effective`** carries the date range the directory applies to — used to check a service
  date against the applicable year and for audit provenance (`vsd_version` stamped on findings).
- **Codes are `{system, code, description}`**, transcribed verbatim. `system` uses the
  directory's code-system label (ICD10CM, CPT, HCPCS, LOINC, SNOMED, CVX, ICD10PCS, REV…).
- **`oid`** is the NCQA/VSAC value-set OID when the directory provides it (enables interop and
  dedup); otherwise `null`.
- **Licensed & internal.** Never embed this in the rules pack, never redistribute, and never
  include these codes in reviewer/plan exports (those stay value-set-*names* only).

## JSON Schema (structural)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["vsd_version", "source", "value_sets"],
  "properties": {
    "vsd_version": { "type": "string" },
    "source": {
      "type": "object",
      "required": ["measurement_year"],
      "properties": {
        "publisher": { "type": "string" },
        "directory_title": { "type": "string" },
        "measurement_year": { "type": "string" },
        "effective": {
          "type": ["object", "null"],
          "properties": { "start": { "type": "string" }, "end": { "type": "string" } }
        },
        "loaded_at": { "type": ["string", "null"] },
        "license": { "type": "string" }
      }
    },
    "value_sets": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "required": ["codes"],
        "properties": {
          "oid": { "type": ["string", "null"] },
          "codes": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["system", "code"],
              "properties": {
                "system": { "type": "string" },
                "code": { "type": "string" },
                "description": { "type": ["string", "null"] }
              }
            }
          }
        }
      }
    }
  }
}
```
