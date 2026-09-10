"""Pass 1 of the `hedis-rules-to-findings` skill: extract the measure's
structured data elements from one chart's text.

This is the *judgement* half of the skill (SKILL.md "Pass 1 — Data elements").
It returns, per element: a value, the VERBATIM sentence supporting it, and a
confidence — or value null / confidence 0 when the element is not documented.
The output is handed to `anchor_findings.py`, which anchors each quote to a
page + char range, downgrades quotes it cannot locate, and runs the deterministic
exclusion scan. This module never decides compliance.

Two providers, same output shape:

* `anthropic`  — the real skill behaviour. Used when ANTHROPIC_API_KEY (or an
  `ant` profile) is available. Model: claude-opus-4-8, adaptive thinking,
  structured outputs so the findings array validates.
* `heuristic`  — a dependency-free, offline fallback that scans the chart for
  each element's keywords and pulls a candidate value by type. It is deliberately
  conservative and only proposes what it can quote; the deterministic anchoring
  and exclusion passes downstream are identical either way.
"""
from __future__ import annotations

import json
import os
import re

MODEL = "claude-opus-4-8"
MAX_CHART_CHARS = 18000  # SKILL.md caps a single extraction call at ~18k chars

# Once the credential is rejected in a process, stop retrying the API on every
# element extraction — fall straight through to the offline heuristic.
_ANTHROPIC_DISABLED = False
_DISABLED_REASON = ""

FINDINGS_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "element_key": {"type": "string"},
                    "value": {"type": ["string", "null"]},
                    "evidence_text": {"type": ["string", "null"]},
                    "confidence": {"type": "number"},
                    "in_window": {"type": ["boolean", "null"]},
                },
                "required": ["element_key", "value", "evidence_text", "confidence"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["findings"],
    "additionalProperties": False,
}


def _element_lines(measure: dict) -> str:
    lines = []
    for e in measure.get("data_elements", []):
        unit = f", {e['unit']}" if e.get("unit") else ""
        line = f"- {e['key']} ({e.get('type')}{unit}): {e.get('label')}"
        if e.get("compliance_hint"):
            line += f" — {e['compliance_hint']}"
        if e.get("timing"):
            line += f" [timing: {e['timing']}]"
        if e.get("options"):
            line += f" Options: {', '.join(e['options'])}"
        lines.append(line)
    return "\n".join(lines)


def _window_context(measure: dict, measurement_year: str | None) -> str:
    mp = measure.get("measurement_period") or {}
    ep = measure.get("eligible_population") or {}
    parts = []
    if measurement_year:
        parts.append(f"Measurement year: {measurement_year}.")
    if mp.get("window"):
        parts.append(f"Measurement window: {mp['window']}.")
    if mp.get("lookback") and mp["lookback"] != "None":
        parts.append(f"Look-back: {mp['lookback']}.")
    if ep.get("anchor_date"):
        parts.append(f"Anchor date: {ep['anchor_date']}.")
    return " ".join(parts) or "Measurement window: the measurement year."


def _build_prompt(measure: dict, chart_text: str, measurement_year: str | None = None) -> str:
    return f"""You are assisting a HEDIS chart abstractor. Extract ONLY the data elements below \
from the medical record for the measure {measure['measure_id']} ({measure.get('measure_name')}).

MEASUREMENT WINDOW (use this to judge timing):
{_window_context(measure, measurement_year)}

DATA ELEMENTS TO FIND:
{_element_lines(measure)}

RULES:
- For each element, return the value and the VERBATIM sentence from the record that supports it.
- The evidence must be copied exactly from the record so it can be located in the source.
- If an element is not documented, return it with value null and confidence 0. Do not guess.
- Do not decide whether the member meets the measure. Only report what the record says.
- Judge in_window against the MEASUREMENT WINDOW above: set in_window=true if the documented
  date falls inside it, and in_window=false if it falls OUTSIDE it (still report the value).

MEDICAL RECORD:
{chart_text[:MAX_CHART_CHARS]}

Return one finding per element listed above."""


# --- Provider: Anthropic (real skill behaviour) ---------------------------

def _extract_anthropic(measure: dict, chart_text: str, measurement_year: str | None = None) -> list[dict]:
    import anthropic

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        thinking={"type": "adaptive"},
        output_config={"format": {"type": "json_schema", "schema": FINDINGS_SCHEMA}},
        messages=[{"role": "user", "content": _build_prompt(measure, chart_text, measurement_year)}],
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    return json.loads(text).get("findings", [])


# --- Provider: heuristic (offline fallback) --------------------------------

_NUM = r"[-+]?\d+(?:\.\d+)?"
_DATE = r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b"


def _sentence_around(text: str, idx: int) -> str:
    """Grab the sentence-ish window around a match for use as evidence."""
    lo = max(text.rfind(".", 0, idx), text.rfind("\n", 0, idx)) + 1
    hi_dot = text.find(".", idx)
    hi_nl = text.find("\n", idx)
    candidates = [h for h in (hi_dot, hi_nl) if h != -1]
    hi = min(candidates) + 1 if candidates else min(len(text), idx + 120)
    return re.sub(r"\s+", " ", text[lo:hi]).strip()


def _first_keyword_hit(text: str, keywords: list[str]):
    low = text.lower()
    for kw in keywords or []:
        m = re.search(r"\b" + re.escape(kw.lower()) + r"\b", low)
        if m:
            return m.start()
    return None


def _extract_heuristic(measure: dict, chart_text: str) -> list[dict]:
    out = []
    for e in measure.get("data_elements", []):
        key, etype = e["key"], e.get("type")
        keywords = e.get("keywords", [])
        hit = _first_keyword_hit(chart_text, keywords)
        value = None
        evidence = None
        conf = 0.0
        if hit is not None:
            evidence = _sentence_around(chart_text, hit)
            window = chart_text[hit: hit + 160]
            if etype in ("numeric", "result"):
                m = re.search(_NUM, window)
                if m:
                    value, conf = m.group(0), 0.6
            elif etype == "date":
                m = re.search(_DATE, chart_text[max(0, hit - 80): hit + 160])
                if m:
                    value, conf = m.group(0), 0.55
            elif etype == "boolean":
                value, conf = "true", 0.5
            elif etype == "text":
                opts = e.get("options") or []
                low = window.lower()
                match = next((o for o in opts if o.lower() in low), None)
                value = match or (keywords[0] if keywords else None)
                conf = 0.55 if match else 0.4
            else:  # code, other
                value, conf = keywords[0] if keywords else None, 0.4
        out.append({
            "element_key": key,
            "value": value,
            "evidence_text": evidence if value else None,
            "confidence": round(conf, 2),
        })
    return out


# --- Public entry point ----------------------------------------------------

def extract_elements(measure: dict, chart_text: str, prefer: str | None = None,
                     measurement_year: str | None = None) -> tuple[list[dict], str]:
    """Return (findings, provider_used).

    Uses the Anthropic provider when a credential is present (or when
    prefer='anthropic'), otherwise the offline heuristic. Falls back to the
    heuristic if the API call errors, so the pipeline never hard-fails.
    """
    global _ANTHROPIC_DISABLED, _DISABLED_REASON
    want = prefer or ("anthropic" if (os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")) else "heuristic")
    if want == "anthropic" and _ANTHROPIC_DISABLED:
        return _extract_heuristic(measure, chart_text), f"heuristic ({_DISABLED_REASON})"
    if want == "anthropic":
        try:
            return _extract_anthropic(measure, chart_text, measurement_year), "anthropic"
        except Exception as exc:  # noqa: BLE001 - degrade gracefully
            import anthropic
            if isinstance(exc, anthropic.AuthenticationError):
                _ANTHROPIC_DISABLED, _DISABLED_REASON = True, "invalid API key"
                print("WARN: Anthropic API key rejected (401) — using the offline heuristic "
                      "extractor for the rest of this run. Fix the key and restart to use Claude.")
            else:
                _DISABLED_REASON = "anthropic error"
                print(f"WARN: Anthropic Pass-1 failed ({exc!r}); falling back to heuristic extractor")
            return _extract_heuristic(measure, chart_text), f"heuristic ({_DISABLED_REASON})"
    return _extract_heuristic(measure, chart_text), "heuristic"
