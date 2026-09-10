#!/usr/bin/env python3
"""Query helpers over a value-set pack — the reference + code-membership-validation API.

Deterministic, no dependencies. The app (and the reviewer UI) use these to resolve a
value-set NAME to its codes, to validate that a code a reviewer captured belongs to the
named value set, and to reverse-look-up which value sets contain a code. This never
selects a code for submission — it answers membership/reference questions for a human.
"""
import re


def _codes(pack, value_set_name):
    return ((pack.get("value_sets") or {}).get(value_set_name) or {}).get("codes") or []


def codes_for(pack, value_set_name):
    """All codes in a named value set (reference display)."""
    return list(_codes(pack, value_set_name))


def oid_for(pack, value_set_name):
    return ((pack.get("value_sets") or {}).get(value_set_name) or {}).get("oid")


def _norm_code(s):
    return re.sub(r"[.\s-]", "", (s or "")).upper()


def contains_code(pack, value_set_name, code, system=None):
    """Membership validation: does `code` (optionally in `system`) belong to the value set?
    Code comparison ignores dots/dashes/whitespace and case (N18.6 == n186)."""
    target = _norm_code(code)
    sys_l = (system or "").strip().lower()
    for c in _codes(pack, value_set_name):
        if _norm_code(c.get("code")) == target and (not sys_l or (c.get("system") or "").lower() == sys_l):
            return True
    return False


def find_value_sets_for_code(pack, code, system=None):
    """Reverse lookup: which value sets contain this code."""
    target = _norm_code(code)
    sys_l = (system or "").strip().lower()
    hits = []
    for name, body in (pack.get("value_sets") or {}).items():
        for c in body.get("codes") or []:
            if _norm_code(c.get("code")) == target and (not sys_l or (c.get("system") or "").lower() == sys_l):
                hits.append(name)
                break
    return sorted(hits)


def summary(pack):
    vs = pack.get("value_sets") or {}
    return {
        "measurement_year": (pack.get("source") or {}).get("measurement_year"),
        "value_sets": len(vs),
        "codes": sum(len(v.get("codes") or []) for v in vs.values()),
    }


def search(pack, query, limit=200):
    """Free-text search across value-set names, codes, and descriptions."""
    q = (query or "").strip().lower()
    if not q:
        return []
    out = []
    for name, body in (pack.get("value_sets") or {}).items():
        codes = body.get("codes") or []
        name_hit = q in name.lower()
        code_hits = [c for c in codes
                     if q in (c.get("code") or "").lower() or q in (c.get("description") or "").lower()
                     or q == _norm_code(c.get("code")).lower()]
        if name_hit or code_hits:
            out.append({"value_set": name, "oid": body.get("oid"),
                        "code_count": len(codes),
                        "matched_codes": (codes if name_hit else code_hits)[:limit]})
    return out
