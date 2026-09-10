# Rules-pack fields this skill consumes

The rules pack is produced by the companion skill `hedis-spec-to-rules` and both
skills conform to the **same contract** (`schema_version` 1.0). The full,
canonical field-by-field definition is bundled **in this skill** at
`rules-pack-schema.md` (a verbatim copy of the producer skill's
canonical file — they must stay identical for the two skills to complement each
other). Read that file for the complete shape; this note lists only the subset
this skill actually reads. Fields not listed (eligible population, numerator
prose, etc.) are useful human context but are **not** applied as logic — this
skill locates data, it does not adjudicate.

## Per target measure (`measures[]` where `measure_id` matches)

- `measure_id`, `measure_name` — identity, echoed onto findings.
- `data_elements[]` — the fields to extract in Pass 1. Per element the skill uses:
  - `key` — the finding's `element_key`.
  - `label`, `type`, `unit`, `options` — shown to the model to constrain the value.
  - `required` — drives the `required_missing` summary.
  - `timing` — the window a value must fall in to count; report out-of-window
    values, don't drop them.
  - `compliance_hint` — human context only; never applied as a decision.
  - `keywords` — hints for locating the element in text (optional).
- `exclusions[]` — scanned deterministically in Pass 2. Per exclusion the skill
  uses:
  - `key` → `rule_key`, `label` → `rule_label`, `scope`, `note`, `applies_when`.
  - `value_sets[]` — reported as the source of a hit (`value_set_name`).
  - `keywords[]` and `codes[].description` — the phrases matched against the text
    (whole-word, negation-aware). An exclusion with neither cannot be matched and
    is skipped with a warning.
  - `timing` (optional) — the exclusion's window; echoed onto the finding for the
    reviewer to check dates against. The scan itself is date-blind (never drops a
    hit for being out of window).
  - `compound` (optional) — `true` marks a rule a single mention cannot settle
    (needs 2+ distinct findings); a hit is dispositioned `partial_needs_components`,
    with the full requirement carried in `note`.
  - `source_hint` (optional) — `"administrative"` marks a criterion chart text
    cannot settle; a hit is then dispositioned `confirm_via_administrative_source`
    (routed to the file, not proposed). Other values / absence behave normally.
  - `threshold` (optional) — a count requirement on one concept (e.g. two findings
    on different dates); a single text hit is dispositioned `partial_needs_count`,
    with the count left to the reviewer.

Each exclusion finding is also tagged `origin` (`measure` vs `universal`).
Universal rules are scanned for every measure; a `universal` hit should be
confirmed against the specific measure's exclusion list, since NCQA applies some
universal exclusions (palliative, advanced-illness+frailty) only to a defined
subset of measures.

## Top level

- `source.measurement_year` — confirm it is the intended year before running.
- `universal_exclusions[]` — hospice, palliative, advanced-illness-with-frailty.
  Scanned for **every** measure in addition to the measure's own `exclusions[]`
  (measure-specific rules first, then universal).

## Not consumed as logic

`eligible_population`, `measurement_period`, `numerator`, `hybrid` — these frame
the measure for the reviewer but are never turned into automated eligibility or
compliance decisions. Determining who is eligible and whether a member is
the gap-closure determination is out of scope by design.
