"""Upload -> generate: build a rules pack from an NCQA HEDIS spec PDF.

Implements the `hedis-spec-to-rules` intake for the admin screen. The spec text
is sent to Claude with the rules-pack JSON schema (structured outputs) so the
result conforms to `schema_version` 1.0, then the bundled `validate_pack.py`
checks structure and flags empties. Requires an Anthropic credential.

Guardrails carried from the skill: restate prose in our own words, transcribe
only codes the PDF prints, capture value-set NAMES verbatim, and report coverage
honestly (the validator's warnings are surfaced to the admin, not buried).
"""
from __future__ import annotations

import importlib.util
import io
import json
import contextlib
from pathlib import Path

MODEL = "claude-opus-4-8"
MAX_SPEC_CHARS = 60000  # one measure range at a time; large specs should be split

_SPEC_SKILL_DIR = (
    Path(__file__).resolve().parents[2] / ".claude" / "skills" / "hedis-spec-to-rules"
)
_spec = importlib.util.spec_from_file_location(
    "validate_pack", _SPEC_SKILL_DIR / "validate_pack.py"
)
_validator = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_validator)  # type: ignore[union-attr]

# Rules-pack schema (schema_version 1.0) as a JSON Schema for structured output.
PACK_SCHEMA = {
    "type": "object",
    "properties": {
        "schema_version": {"type": "string"},
        "source": {
            "type": "object",
            "properties": {
                "document_title": {"type": "string"},
                "measurement_year": {"type": "string"},
                "publisher": {"type": "string"},
                "pages": {"type": "string"},
                "disclaimer": {"type": "string"},
            },
            "required": ["measurement_year"],
            "additionalProperties": False,
        },
        "universal_exclusions": {"type": "array", "items": {"$ref": "#/$defs/exclusion"}},
        "measures": {"type": "array", "items": {"$ref": "#/$defs/measure"}},
    },
    "required": ["schema_version", "source", "measures"],
    "additionalProperties": False,
    "$defs": {
        "element": {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "label": {"type": "string"},
                "type": {"enum": ["date", "numeric", "text", "code", "boolean", "result"]},
                "required": {"type": "boolean"},
                "unit": {"type": ["string", "null"]},
                "options": {"type": ["array", "null"], "items": {"type": "string"}},
                "timing": {"type": "string"},
                "compliance_hint": {"type": "string"},
                "keywords": {"type": "array", "items": {"type": "string"}},
                "evidence_role": {"type": ["string", "null"],
                                  "enum": ["provider_credential", "provider_signature", None]},
            },
            "required": ["key", "label", "type", "required", "keywords"],
            "additionalProperties": False,
        },
        "exclusion": {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "label": {"type": "string"},
                "scope": {"enum": ["required", "optional"]},
                "value_sets": {"type": "array", "items": {"type": "string"}},
                "codes": {"type": "array", "items": {
                    "type": "object",
                    "properties": {"system": {"type": "string"}, "code": {"type": "string"},
                                   "description": {"type": "string"}},
                    "required": ["system", "code", "description"],
                    "additionalProperties": False,
                }},
                "keywords": {"type": "array", "items": {"type": "string"}},
                "applies_when": {"type": ["string", "null"]},
                "note": {"type": ["string", "null"]},
                "timing": {"type": "string"},
                "compound": {"type": "boolean"},
                "source_hint": {"enum": ["medical_record", "administrative", "both", "unstated"]},
            },
            "required": ["key", "label", "scope", "value_sets", "keywords"],
            "additionalProperties": False,
        },
        "measure": {
            "type": "object",
            "properties": {
                "measure_id": {"type": "string"},
                "measure_name": {"type": "string"},
                "hybrid": {"type": "boolean"},
                "source_pages": {"type": "string"},
                "eligible_population": {"type": "object", "properties": {
                    "ages": {"type": "string"}, "event_or_diagnosis": {"type": "string"},
                    "continuous_enrollment": {"type": "string"}, "anchor_date": {"type": "string"}},
                    "additionalProperties": False},
                "measurement_period": {"type": "object", "properties": {
                    "window": {"type": "string"}, "lookback": {"type": "string"}},
                    "additionalProperties": False},
                "numerator": {"type": "string"},
                "data_elements": {"type": "array", "items": {"$ref": "#/$defs/element"}},
                "exclusions": {"type": "array", "items": {"$ref": "#/$defs/exclusion"}},
            },
            "required": ["measure_id", "measure_name", "hybrid", "data_elements", "exclusions"],
            "additionalProperties": False,
        },
    },
}

PROMPT = """You are converting a published NCQA HEDIS technical specification into a machine-usable \
"rules pack" for locating chart evidence. Follow these rules exactly:

- Extract every measure present in the text below. For each: measure_id (NCQA abbreviation), \
measure_name, whether it is hybrid (chart review permitted), eligible_population, measurement_period, \
a plain-language numerator, the structured data_elements a reviewer must find, and the exclusions.
- data_elements are the minimal structured fields (date/numeric/text/code/boolean/result), not prose. \
Give each a compliance_hint (descriptive, never a decision rule), a timing note, and real clinical keywords.
- exclusions: one candidate per DISTINCT exclusion (never collapse a "Denominator Exclusions" heading into \
one rule). Capture value_sets by NAME verbatim from the spec, any codes the PDF actually prints (else empty), \
plain-language keywords, applies_when, timing (the window), compound (true when >=2 findings are needed), and \
source_hint ("administrative" for enrollment/claims-file facts a chart cannot settle).
- Put broadly-applied exclusions (hospice, palliative, advanced illness + frailty) in universal_exclusions. \
Death is NEVER a chart exclusion.
- Restate prose in your own words; transcribe only codes the document prints; never fabricate a code or value set.
- schema_version must be "1.1". Set source.measurement_year to the year in the document. When a measure requires the performing provider's signature/credential as evidence, add a data element with evidence_role "provider_credential" (or "provider_signature") and credential keywords.

SPEC TEXT (measurement year: {year}):
{spec}
"""


def generate_pack(spec_text: str, measurement_year: str, document_title: str,
                  publisher: str = "NCQA") -> tuple[dict, list[str]]:
    """Return (pack, validator_lines). Raises on API/parse failure."""
    import anthropic

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"format": {"type": "json_schema", "schema": PACK_SCHEMA}},
        messages=[{"role": "user", "content": PROMPT.format(
            year=measurement_year, spec=spec_text[:MAX_SPEC_CHARS])}],
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    pack = json.loads(text)

    # Fill in source metadata the app knows authoritatively.
    src = pack.setdefault("source", {})
    src.setdefault("measurement_year", measurement_year)
    src["document_title"] = document_title
    src["publisher"] = publisher
    src.setdefault("disclaimer", "Derived from published NCQA HEDIS technical specifications to "
                                 "locate chart evidence. Not a certified compliance engine; all "
                                 "findings are proposals for human review.")
    pack.setdefault("schema_version", "1.1")
    pack.setdefault("universal_exclusions", [])
    return pack, validate_pack_dict(pack)


def validate_pack_dict(pack: dict) -> list[str]:
    """Run the bundled validator on a pack dict; return its stdout lines."""
    import tempfile
    buf = io.StringIO()
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=True) as tf:
        json.dump(pack, tf)
        tf.flush()
        with contextlib.redirect_stdout(buf):
            _validator.main(tf.name)
    return [ln for ln in buf.getvalue().splitlines() if ln.strip()]
