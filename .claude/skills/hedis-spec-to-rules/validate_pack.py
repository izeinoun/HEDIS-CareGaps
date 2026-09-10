#!/usr/bin/env python3
"""Validate a HEDIS rules pack against the shared contract.

Structural + sanity checks only (no network, no deps). Exit code is non-zero if
any ERROR is found; WARN lines are advisory. Checks the pack against the shared
contract in rules-pack-schema.md (schema_version 1.0).

Usage:  python validate_pack.py <pack.json>
"""
import json
import sys

ELEMENT_TYPES = {"date", "numeric", "text", "code", "boolean", "result"}
SCOPES = {"required", "optional"}
SOURCE_HINTS = {"medical_record", "administrative", "both", "unstated"}


def main(path: str) -> int:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            pack = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read/parse {path}: {exc}")
        return 2

    errors: list[str] = []
    warns: list[str] = []

    if not isinstance(pack, dict):
        print("ERROR: top level must be a JSON object")
        return 2

    src = pack.get("source") or {}
    if not src.get("measurement_year"):
        errors.append("source.measurement_year is required (measure codes are not stable across years)")
    if not src.get("disclaimer"):
        warns.append("source.disclaimer missing — add the 'not a certified compliance engine' note")

    measures = pack.get("measures")
    if not isinstance(measures, list) or not measures:
        errors.append("measures[] is required and must be non-empty")
        measures = []

    def check_exclusion(ex, where):
        for req in ("key", "label", "scope", "value_sets"):
            if req not in ex:
                errors.append(f"{where}: exclusion missing '{req}'")
        if ex.get("scope") not in SCOPES:
            errors.append(f"{where}: exclusion scope must be one of {sorted(SCOPES)}")
        if not ex.get("value_sets"):
            errors.append(f"{where}: exclusion '{ex.get('key')}' has no value_sets (the durable NCQA link)")
        if not ex.get("keywords") and not ex.get("codes"):
            warns.append(f"{where}: exclusion '{ex.get('key')}' has neither keywords nor inline codes — "
                         "a downstream text scan will not be able to match it")
        sh = ex.get("source_hint")
        if sh is not None and sh not in SOURCE_HINTS:
            errors.append(f"{where}: exclusion '{ex.get('key')}' source_hint must be one of {sorted(SOURCE_HINTS)}")
        th = ex.get("threshold")
        if th is not None:
            if not isinstance(th, dict) or not isinstance(th.get("count"), int):
                errors.append(f"{where}: exclusion '{ex.get('key')}' threshold must be null or "
                              "{'count': <int>, 'distinct': <str>}")
        if "timing" in ex and not isinstance(ex.get("timing"), str):
            errors.append(f"{where}: exclusion '{ex.get('key')}' timing must be a string (the window)")
        cp = ex.get("compound")
        if cp is not None and not isinstance(cp, bool):
            errors.append(f"{where}: exclusion '{ex.get('key')}' compound must be true/false")
        if cp is True and not ex.get("note"):
            warns.append(f"{where}: exclusion '{ex.get('key')}' is compound but has no note — a reviewer "
                         "cannot tell what the multiple required findings are")

    for ex in pack.get("universal_exclusions", []) or []:
        check_exclusion(ex, "universal_exclusions")
        if str(ex.get("key")).lower() == "death" or "death" in str(ex.get("label")).lower():
            errors.append("death must NOT be a chart exclusion — it comes from eligibility data, not a value set")

    seen_ids = set()
    for i, m in enumerate(measures):
        where = f"measures[{i}] ({m.get('measure_id', '?')})"
        for req in ("measure_id", "measure_name", "hybrid", "data_elements"):
            if req not in m:
                errors.append(f"{where}: missing '{req}'")
        mid = m.get("measure_id")
        if mid in seen_ids:
            errors.append(f"{where}: duplicate measure_id '{mid}'")
        seen_ids.add(mid)

        elements = m.get("data_elements") or []
        if not elements:
            errors.append(f"{where}: data_elements[] is empty")
        keys = set()
        has_required = False
        for e in elements:
            for req in ("key", "label", "type", "required"):
                if req not in e:
                    errors.append(f"{where}: element {e.get('key', '?')} missing '{req}'")
            if e.get("type") not in ELEMENT_TYPES:
                errors.append(f"{where}: element '{e.get('key')}' type must be one of {sorted(ELEMENT_TYPES)}")
            if e.get("key") in keys:
                errors.append(f"{where}: duplicate element key '{e.get('key')}'")
            keys.add(e.get("key"))
            if e.get("required"):
                has_required = True
            if not e.get("keywords"):
                warns.append(f"{where}: element '{e.get('key')}' has no keywords — harder to locate in text")
        if elements and not has_required:
            warns.append(f"{where}: no element marked required — abstraction completeness cannot be judged")

        for ex in m.get("exclusions", []) or []:
            check_exclusion(ex, where)

    for w in warns:
        print(f"WARN: {w}")
    for e in errors:
        print(f"ERROR: {e}")

    ny = src.get("measurement_year", "?")
    print(f"\n{path}: {len(measures)} measures, {len(errors)} errors, {len(warns)} warnings "
          f"(measurement year {ny}).")
    return 1 if errors else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
