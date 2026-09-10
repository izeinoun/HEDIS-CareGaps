#!/usr/bin/env python3
"""Assemble anchored, proposal-only HEDIS chart findings from a rules pack.

The deterministic half of the skill — no dependencies and no LLM call:

  * anchors the model's Pass-1 element quotes to page + character offsets,
    downgrading any quote that cannot be located in the chart text;
  * scans the chart deterministically for the measure's exclusions using the
    pack's keywords + inline code descriptions (whole-word, negation-aware), so
    every proposed exclusion traces to a named value set;
  * emits the findings object described in findings-schema.md.

The LLM element extraction (Pass 1) is done by the skill following SKILL.md and
handed to this script via --elements. This script never decides compliance.

An optional --case supplies chart-chase context (the pursuit-list record for one
member): it skips a measure already resolved administratively (unless --force),
gates exclusions on the member's age, and flags exclusions the plan already applied.

--workflow gap_closure adds the two things gap closure needs over chart chase: a
provider-submission validation gate (member name + DOB, measure alignment, content
/ date — a member-identity mismatch is a hard stop) and a proposed gap_outcome
(closable_on_documentation / partial_documentation / exclusion_candidate /
previously_closed / no_impact_to_gap). Chart chase (the default) skips both.

Usage:
  python anchor_findings.py --pack PACK --measure ID --text CHART.txt \
      [--elements PASS1.json] [--offsets OFFSETS.json | --pages PAGES.json] \
      [--cross CROSS.json] [--mode targeted|broad] [--case CASE.json] [--force] \
      [--workflow chase|gap_closure] [--out OUT.json]
"""
import argparse
import datetime
import json
import re
import sys

MIN_TERM_LENGTH = 6
CONTEXT_CHARS = 160
MAX_PER_RULE = 3
NEGATION_CUES = (
    "no evidence of", "not on", "denies", "no history of", "ruled out",
    "negative for", "without", "declined", "not a candidate for", "no ",
)
DISCLAIMER = (
    "AI proposals only. Measure compliance, numerator status, and final exclusion "
    "application are determined by the reviewer, not by this analysis."
)
REVIEW_CONFIDENCE = 0.7  # at/below this (or unanchored) a found value is flagged needs_review

# Numeric-threshold parser for the compliance-threshold ADVISORY (a reviewer aid,
# never a determination). Only hints like "Gap closed when < 140" are checkable.
_THRESHOLD_RE = re.compile(
    r"(<=|>=|<|>|≤|≥|less than or equal to|greater than or equal to|no more than|"
    r"at least|less than|greater than|under|over|below|above)\s*(\d+(?:\.\d+)?)", re.I)
_THRESHOLD_SYM = {"less than": "<", "under": "<", "below": "<", "greater than": ">",
                  "over": ">", "above": ">", "at least": "≥", "no more than": "≤",
                  "less than or equal to": "≤", "greater than or equal to": "≥"}


def compliance_advisory(value, hint):
    """Advisory ONLY: does a numeric value satisfy the pack's compliance_hint threshold?

    A reviewer aid to speed sign-off — it never decides compliance. `compliance_hint`
    is context for a human (schema 1.0), so this just parses a numeric threshold from
    it and compares. Descriptive hints ("Screening or diagnostic both qualify") return
    checkable=False. Returns {checkable, meets (True/False/None), hint, basis}.
    """
    out = {"checkable": False, "meets": None, "hint": hint, "basis": None}
    if not hint:
        return out
    try:
        v = float(str(value))
    except (TypeError, ValueError):
        return out
    m = _THRESHOLD_RE.search(hint)
    if not m:
        return out
    op, num = m.group(1).lower(), float(m.group(2))
    lt = op in ("<", "less than", "under", "below")
    le = op in ("<=", "≤", "no more than", "less than or equal to")
    gt = op in (">", "greater than", "over", "above")
    ge = op in (">=", "≥", "at least", "greater than or equal to")
    meets = (v < num) if lt else (v <= num) if le else (v > num) if gt else (v >= num) if ge else None
    sym = _THRESHOLD_SYM.get(op, op)
    return {"checkable": meets is not None, "meets": meets, "hint": hint,
            "basis": f"{value} {sym} {m.group(2)}" if meets is not None else None}


def compound_components(text, rule):
    """For a `compound` exclusion, which keyword components appear (non-negated).

    A single hit on a compound rule is partial, never settled — this makes the
    present-vs-missing components explicit so the reviewer can see what is still needed.
    """
    hay = text.lower()
    comps = []
    for kw in rule.get("keywords") or []:
        term = (kw or "").lower().strip()
        if len(term) < 3:
            continue
        m = re.search(r"\b" + re.escape(term) + r"\b", hay)
        comps.append({"term": kw, "present": bool(m) and not _is_negated(text, m.start())})
    return comps


def _age_check(applies_when, member_age):
    """Evaluate an exclusion's age gate against the case member's age.

    Returns "in_band" | "out_of_band" | "not_applicable" | "unknown". Still only a
    proposal aid — an out_of_band finding is surfaced, never auto-dropped.
    """
    if not applies_when:
        return "not_applicable"
    aw = applies_when.lower()
    ranges = []                                   # union of admissible [lo, hi] bands
    # Explicit ranges: "66-80", "66 to 80", "18–85".
    for lo, hi in re.findall(r"(\d+)\s*(?:-|–|to)\s*(\d+)", aw):
        ranges.append((int(lo), int(hi)))
    # Lower bounds: "81+", "66 or older", "66 and older", "at least 66".
    for m in re.finditer(r"(\d+)\s*\+|at least\s+(\d+)|(\d+)\s*(?:or|and)\s+older", aw):
        n = next(g for g in m.groups() if g)
        ranges.append((int(n), 200))
    # Upper bounds: "under 18", "younger than 18", "up to 18".
    for m in re.finditer(r"(?:under|younger than|up to)\s+(\d+)", aw):
        ranges.append((0, int(m.group(1))))
    if not ranges:                                # a bare number with no direction
        nums = [int(n) for n in re.findall(r"\d+", aw)]
        if not nums:
            return "not_applicable"               # a non-age gate (e.g. product line)
        ranges.append((nums[0], 200))             # most HEDIS gates are "N or older"
    if member_age is None:
        return "unknown"
    return "in_band" if any(lo <= member_age <= hi for lo, hi in ranges) else "out_of_band"


def _normalize(text):
    return re.sub(r"\s+", " ", (text or "")).strip()


def _load(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def page_for_offset(offsets, char_index):
    for entry in offsets:
        if entry["start"] <= char_index < entry["end"]:
            return entry["page"]
    return offsets[-1]["page"] if offsets else None


def offsets_from_pages(pages):
    """Concatenate per-page text (\n\n separated) and record each page's span."""
    text_parts, offsets, cursor = [], [], 0
    for i, page in enumerate(pages, start=1):
        page = page or ""
        start = cursor
        text_parts.append(page)
        cursor += len(page)
        offsets.append({"page": i, "start": start, "end": cursor})
        if i < len(pages):
            text_parts.append("\n\n")
            cursor += 2
    return "".join(text_parts), offsets


def _locate(text, needle):
    """Find a quote in the chart, tolerating whitespace differences."""
    if not needle or not text:
        return None
    direct = text.lower().find(needle.lower())
    if direct >= 0:
        return direct, direct + len(needle)
    words = [w for w in re.split(r"\s+", needle) if len(w) > 3]
    for size in (8, 6, 4, 3):
        for i in range(0, max(0, len(words) - size + 1)):
            fragment = " ".join(words[i:i + size])
            pattern = r"\s+".join(re.escape(w) for w in fragment.split())
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.span()
    return None


def _anchor(text, evidence, offsets):
    span = _locate(text, evidence)
    if not span:
        return {"page_number": None, "char_start": None, "char_end": None, "anchored": False}
    start, end = span
    return {"page_number": page_for_offset(offsets, start),
            "char_start": start, "char_end": end, "anchored": True}


def _is_negated(text, start):
    window = text[max(0, start - 60):start].lower()
    return any(cue in window for cue in NEGATION_CUES)


def _exclusion_rules_for(pack, measure):
    """Measure-specific exclusions first, then universal, each tagged with origin.

    Origin matters downstream: a universal exclusion (hospice, palliative,
    advanced-illness+frailty) is scanned against every measure, but NCQA applies
    some of them only to a measure-defined subset — so a universal hit is surfaced
    with a "confirm this measure lists it" caveat rather than as a plain candidate.
    """
    own = [(r, "measure") for r in (measure.get("exclusions") or [])]
    universal = [(r, "universal") for r in (pack.get("universal_exclusions") or [])]
    return own + universal


def _terms_for_rule(rule):
    """Distinct clinical phrases to match: keywords + inline code descriptions."""
    terms = set()
    for kw in rule.get("keywords") or []:
        d = _normalize(kw).lower()
        if len(d) >= 3:                       # keywords are curated, allow short ones
            terms.add(d)
    for code in rule.get("codes") or []:
        d = _normalize(code.get("description")).lower()
        d = re.sub(r"^\[[^\]]+\]\s*", "", d)  # strip "[N18.6] " prefixes
        if len(d) >= MIN_TERM_LENGTH:
            terms.add(d)
    return sorted(terms, key=len, reverse=True)


def find_exclusions(text, pack, measure, member_age=None, applied_keys=()):
    if not text:
        return []
    applied_keys = set(applied_keys or ())
    haystack = text.lower()
    findings = []
    for rule, origin in _exclusion_rules_for(pack, measure):
        terms = _terms_for_rule(rule)
        if not terms:
            print(f"WARN: exclusion '{rule.get('key')}' has no keywords/codes to match — skipped",
                  file=sys.stderr)
            continue
        value_sets = rule.get("value_sets") or [None]
        hits = []
        for term in terms:
            if len(hits) >= MAX_PER_RULE:
                break
            match = re.search(r"\b" + re.escape(term) + r"\b", haystack)
            if not match:
                continue
            start, end = match.span()
            if _is_negated(text, start):
                continue
            confidence = 0.62 + min(0.33, len(term) / 120)
            # source_hint / compound / threshold (all optional, schema_version 1.0)
            # shape how a hit is dispositioned. Precedence, most-constraining first:
            #   administrative  — a file value chart text cannot settle: route to the file.
            #   compound        — needs 2+ distinct findings (AND/OR across concepts): a
            #                     single mention is partial, never a settled exclusion.
            #   threshold       — one concept needed N times: partial until the count holds.
            #   else            — an ordinary chart-findable candidate.
            source_hint = rule.get("source_hint")
            threshold = rule.get("threshold")
            compound = bool(rule.get("compound"))
            needs_file = source_hint == "administrative"
            already_applied = rule.get("key") in applied_keys
            age_check = _age_check(rule.get("applies_when"), member_age)
            threshold_note = None
            if isinstance(threshold, dict) and threshold.get("count"):
                dist = threshold.get("distinct") or "occurrence"
                threshold_note = (f"Requires {threshold['count']} findings on different {dist}; a single "
                                  "text match cannot satisfy this — the reviewer must confirm the count.")
            # already_applied (from the case) wins: the plan already captured this
            # exclusion administratively, so a chart hit is a duplicate, not a new
            # candidate. Otherwise fall back to the source/compound/threshold ladder.
            if already_applied:
                disposition = "already_applied"
            elif needs_file:
                disposition = "confirm_via_administrative_source"
            elif compound:
                disposition = "partial_needs_components"
            elif threshold_note:
                disposition = "partial_needs_count"
            else:
                disposition = "proposed"
            hits.append({
                "rule_key": rule.get("key"),
                "rule_label": rule.get("label"),
                "scope": rule.get("scope", "required"),
                "origin": origin,
                "note": rule.get("note"),
                "timing": rule.get("timing"),
                "applies_when": rule.get("applies_when"),
                "age_check": age_check,
                "already_applied": already_applied,
                "value_set_name": value_sets[0],
                "matched_term": text[start:end],
                "ai_confidence": round(confidence, 3),
                "evidence_text": _normalize(
                    text[max(0, start - CONTEXT_CHARS):min(len(text), end + CONTEXT_CHARS)]),
                "source_hint": source_hint,
                "needs_file_confirmation": needs_file,
                "compound": compound,
                # For a compound rule, the present/missing components of the requirement.
                "components": compound_components(text, rule) if compound else None,
                "threshold": threshold if isinstance(threshold, dict) else None,
                "threshold_note": threshold_note,
                "disposition": disposition,
                # Every fresh (non-duplicate) exclusion candidate warrants a look; partial /
                # administrative dispositions and low-confidence hits especially so.
                "needs_review": (not already_applied) and (
                    disposition != "proposed" or confidence <= REVIEW_CONFIDENCE),
                "document_id": None,
                "page_number": page_for_offset([], start),
                "char_start": start,
                "char_end": end,
            })
        findings.extend(hits)
    findings.sort(key=lambda f: -f["ai_confidence"])
    return findings


def _element_signal(text, offsets, element):
    """Deterministic 'evidence present' screen for one data element.

    Not a value extraction (that is Pass 1's job) — just a whole-word scan of the
    element's keywords so a broad pass can flag which measures a retrieved chart
    has *any* signal for. Returns an anchored hit dict or None.
    """
    haystack = text.lower()
    for kw in element.get("keywords") or []:
        term = _normalize(kw).lower()
        if len(term) < 3:
            continue
        m = re.search(r"\b" + re.escape(term) + r"\b", haystack)
        if not m:
            continue
        start, end = m.span()
        return {
            "element_key": element.get("key"),
            "element_label": element.get("label"),
            "required": bool(element.get("required")),
            "matched_term": text[start:end],
            "evidence_text": _normalize(
                text[max(0, start - CONTEXT_CHARS):min(len(text), end + CONTEXT_CHARS)]),
            "page_number": page_for_offset(offsets, start),
            "char_start": start, "char_end": end,
        }
    return None


def broad_scan(text, offsets, pack, member_age=None, exclude_measure=None, applied_by_measure=None):
    """Cross-measure 'broad' pass — one retrieved chart, every measure in the pack.

    For each measure, report which data elements show keyword evidence in the chart
    and run the deterministic exclusion scan. This is the 'read once, review many'
    primitive: a chart pulled for one gap surfaces the *other* gaps it could also
    close. Everything is a per-chart candidate signal for a human — never a rate,
    never a compliance call. Element *values* still require the Pass-1 targeted run.
    """
    applied_by_measure = applied_by_measure or {}
    results = []
    for measure in pack.get("measures", []):
        mid = measure.get("measure_id")
        if exclude_measure and mid == exclude_measure:
            continue
        signals = [s for s in (_element_signal(text, offsets, e)
                               for e in measure.get("data_elements") or []) if s]
        exclusions = find_exclusions(text, pack, measure, member_age=member_age,
                                     applied_keys=applied_by_measure.get(mid, ()))
        for ex in exclusions:
            ex["page_number"] = page_for_offset(offsets, ex["char_start"])
        required_total = sum(1 for e in measure.get("data_elements") or [] if e.get("required"))
        required_hit = sum(1 for s in signals if s["required"])
        results.append({
            "measure_id": mid,
            "measure_name": measure.get("measure_name"),
            "hybrid": measure.get("hybrid"),
            "element_signals": signals,
            "required_signal": required_hit,
            "required_total": required_total,
            "total_signal": len(signals),
            "exclusions": [x for x in exclusions if not x.get("already_applied")],
            "has_evidence": bool(signals) or any(not x.get("already_applied") for x in exclusions),
        })
    results.sort(key=lambda r: (r["required_signal"], r["total_signal"], len(r["exclusions"])), reverse=True)
    return results


def build_elements(text, offsets, measure, pass1):
    by_key = {}
    for f in pass1 or []:
        if not isinstance(f, dict):
            continue
        key = str(f.get("element_key") or f.get("element") or "").strip()
        if key and key not in by_key:
            by_key[key] = f
    out = []
    for e in measure.get("data_elements") or []:
        found = by_key.get(e["key"], {})
        raw = found.get("value")
        value = None if raw in (None, "", "null", "N/A") else str(raw)
        evidence = _normalize(str(found.get("evidence_text") or found.get("evidence") or "")) or None
        try:
            confidence = float(found.get("confidence") or 0.0)
        except (TypeError, ValueError):
            confidence = 0.0
        anchor = _anchor(text, evidence, offsets) if evidence else {
            "page_number": None, "char_start": None, "char_end": None, "anchored": False}
        if evidence and not anchor["anchored"]:
            confidence = min(confidence, 0.4)
        iw = found.get("in_window")
        conf = round(min(1.0, max(0.0, confidence)), 3)
        out.append({
            "element_key": e["key"],
            "element_label": e.get("label"),
            "element_type": e.get("type"),
            "required": bool(e.get("required")),
            "unit": e.get("unit"),
            "options": e.get("options"),
            "timing": e.get("timing"),
            "compliance_hint": e.get("compliance_hint"),
            "evidence_role": e.get("evidence_role"),   # A8: provider credential/signature, if the measure requires it
            "ai_value": value,
            "ai_confidence": conf,
            "evidence_text": evidence,
            "evidence_anchored": anchor["anchored"],
            "status": "proposed" if value else "not_found",
            "in_window": iw if isinstance(iw, bool) else None,
            # Advisory (reviewer aid, never a determination): does the value meet the hint?
            "compliance": compliance_advisory(value, e.get("compliance_hint")),
            # Weak-proposal flag for a consumer's review gate: a found value that is
            # unanchored or low-confidence should be ruled on before the measure is signed off.
            "needs_review": bool(value) and (not anchor["anchored"] or conf <= REVIEW_CONFIDENCE),
            "document_id": None,
            "page_number": anchor["page_number"],
            "char_start": anchor["char_start"],
            "char_end": anchor["char_end"],
        })
    return out


def build_cross(text, offsets, pack, source_id, cross_in):
    known = {m["measure_id"]: m for m in pack.get("measures", [])}
    out, seen = [], set()
    for f in cross_in or []:
        mid = str(f.get("found_measure_id") or f.get("measure_id") or "").strip()
        if mid not in known or mid == source_id or mid in seen:
            continue
        evidence = _normalize(str(f.get("evidence_text") or "")) or None
        if not evidence:
            continue
        anchor = _anchor(text, evidence, offsets)
        if not anchor["anchored"]:
            continue  # unverifiable cross-measure claims are dropped
        try:
            conf = float(f.get("confidence") or 0.0)
        except (TypeError, ValueError):
            conf = 0.0
        seen.add(mid)
        out.append({
            "found_measure_id": mid,
            "found_measure_name": known[mid].get("measure_name"),
            "element_key": str(f.get("element_key") or "") or None,
            "value": None if f.get("value") in (None, "", "null") else str(f.get("value")),
            "confidence": round(min(1.0, max(0.0, conf)), 3),
            "evidence_text": evidence,
            "page_number": anchor["page_number"],
            "char_start": anchor["char_start"], "char_end": anchor["char_end"],
        })
    return out


def _dob_variants(dob):
    """Common ways an ISO dob (YYYY-MM-DD) can appear in a chart."""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", dob or "")
    if not m:
        return [dob] if dob else []
    y, mo, d = m.group(1), m.group(2), m.group(3)
    mi, di = str(int(mo)), str(int(d))
    months = ["", "january", "february", "march", "april", "may", "june", "july",
              "august", "september", "october", "november", "december"]
    mon = months[int(mo)]
    return [f"{y}-{mo}-{d}", f"{mo}/{d}/{y}", f"{mi}/{di}/{y}", f"{mo}-{d}-{y}",
            f"{mi}-{di}-{y}", f"{mon} {di}, {y}", f"{mon} {di} {y}", f"{di} {mon} {y}"]


def _keywords_for_measure(measure):
    kws = set()
    for e in measure.get("data_elements") or []:
        for k in e.get("keywords") or []:
            kws.add(k.lower())
    for ex in measure.get("exclusions") or []:
        for k in ex.get("keywords") or []:
            kws.add(k.lower())
    return kws


def detect_multiple_members(text):
    """Deterministic multi-patient screen (A12): does one document appear to contain
    more than one member? Flags for manual review to prevent mis-attribution.

    Conservative and evidence-based — it counts *distinct* identity anchors (DOBs,
    MRNs, labelled patient names). More than one distinct value on any anchor raises
    the flag. It never segments or guesses which data belongs to whom; that is the
    reviewer's call — this only says "do not auto-attribute; a human must confirm."
    """
    hay = text or ""
    dobs = set()
    for m in re.finditer(r"(?:dob|date of birth)\s*[:#]?\s*"
                         r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})", hay, re.I):
        dobs.add(m.group(1))
    mrns = set()
    for m in re.finditer(r"\bmrn\s*[:#]?\s*([A-Za-z0-9-]{3,})", hay, re.I):
        mrns.add(m.group(1).lower())
    names = set()
    for m in re.finditer(r"(?:^|\n)\s*(?:patient|member|name)\s*[:#]\s*([A-Za-z][A-Za-z.'\- ]{2,40})", hay, re.I):
        names.add(_normalize(m.group(1)).lower())

    reasons = []
    if len(dobs) > 1:
        reasons.append(f"{len(dobs)} distinct dates of birth")
    if len(mrns) > 1:
        reasons.append(f"{len(mrns)} distinct MRNs")
    if len(names) > 1:
        reasons.append(f"{len(names)} distinct patient-name labels")
    return {
        "multi_patient": bool(reasons),
        "distinct_dobs": sorted(dobs),
        "distinct_mrns": sorted(mrns),
        "distinct_patient_names": sorted(names),
        "reasons": reasons,
        "note": ("Possible multiple members in one document — flagged for manual review; "
                 "do not auto-attribute data until a reviewer confirms identity."
                 if reasons else "Single-member document (no conflicting identity anchors detected)."),
    }


def validate_submission(text, measure, member):
    """Gap-closure gate: does this provider-submitted chart belong to this case?

    Deterministic and reusing the pack — checks member identity (name + DOB),
    measure alignment (does any of the measure's vocabulary appear), and that the
    document has real, dated content. Hard failure is reserved for a member-identity
    mismatch (wrong-member PHI risk); everything else is a surfaced warning.
    """
    hay = (text or "").lower()
    member = member or {}
    name = (member.get("name") or "").strip()
    family = (member.get("family") or (name.split()[-1] if name else "")).lower()
    dob = member.get("dob") or ""

    name_found = bool(family) and re.search(r"\b" + re.escape(family) + r"\b", hay) is not None
    dob_found = any(v and v.lower() in hay for v in _dob_variants(dob))
    if name_found and dob_found:
        member_match = "confirmed"
    elif name_found or dob_found:
        member_match = "partial"
    else:
        member_match = "not_found"

    kws = _keywords_for_measure(measure)
    hits = sum(1 for k in kws if k and re.search(r"\b" + re.escape(k) + r"\b", hay))
    alignment = "aligned" if hits >= 2 else "weak" if hits == 1 else "absent"
    content_present = len(_normalize(text)) >= 40 and bool(re.search(r"[a-z]{3,}", hay))
    date_present = re.search(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})\b", hay) is not None

    warnings = []
    if member_match == "partial":
        warnings.append(f"only one of name/DOB confirmed (name={name_found}, dob={dob_found})")
    if alignment != "aligned":
        warnings.append(f"measure vocabulary {alignment} in the chart")
    if not content_present:
        warnings.append("little or no readable text (legibility / OCR?)")
    if not date_present:
        warnings.append("no service date found in the chart")

    verdict = "failed_member_mismatch" if member_match == "not_found" else "passed"
    return {
        "verdict": verdict,
        "member_match": member_match,
        "name_found": name_found,
        "dob_found": dob_found,
        "measure_alignment": alignment,
        "content_present": content_present,
        "service_date_present": date_present,
        "warnings": warnings,
    }


def gap_outcome(elements, exclusions, admin_status):
    """Propose a gap-closure outcome by reconciling findings with the admin gap state.

    Proposal only — the reviewer confirms. Maps to the customer's outcomes:
    closable_on_documentation (service documented), exclusion_candidate,
    previously_closed, or no_impact_to_gap.
    """
    required = [e for e in elements if e.get("required")]
    required_found = [e for e in required if e.get("ai_value")]
    required_missing = [e for e in required if not e.get("ai_value")]
    fresh_excl = [x for x in exclusions if not x.get("already_applied")]
    out_of_window = [e["element_key"] for e in required_found if e.get("in_window") is False]
    timing_caveat = (f" Timing check: {', '.join(out_of_window)} documented but dated OUTSIDE the "
                     "measurement window — the reviewer must confirm the date counts." if out_of_window else "")

    if required and not required_missing:
        status = "closable_on_documentation"
        rationale = ("All required data elements are documented with anchored evidence in the chart."
                     + timing_caveat)
    elif required_found:
        status = "partial_documentation"
        rationale = ("Some required elements are documented but not all; the rest are still "
                     f"missing ({', '.join(e['element_key'] for e in required_missing)}).")
    elif fresh_excl:
        status = "exclusion_candidate"
        rationale = "No numerator evidence, but a candidate exclusion was found that may retire the member."
    elif admin_status == "gap_closed":
        status = "previously_closed"
        rationale = "No new numerator evidence; the case was already administratively gap-closed."
    else:
        status = "no_impact_to_gap"
        rationale = "No new valid data and no exclusion found in the chart; the gap is unchanged."

    return {
        "status": status,
        "rationale": rationale,
        "required_found": [e["element_key"] for e in required_found],
        "required_missing": [e["element_key"] for e in required_missing],
        "out_of_window_required": out_of_window,
        "note": "Proposed outcome for reviewer confirmation; not a compliance determination.",
    }


def substantiation(elements, exclusions):
    """Per-measure valid-data determination + next-step recommendation (CC 2.4 / CC 2.5).

    Proposal only — the reviewer confirms it at sign-off; this is never a compliance
    determination, and it enters data nowhere (QMRM entry is out of scope, X-5; provider
    contact is out of scope, X-8 — `next_step` is only a suggested label).

    `valid_data_present` answers the customer's step-6 question "is substantiating data
    present, yes or no" for this measure:
      True  — every required element is documented with anchored evidence,
      False — at least one required element is missing from the chart,
      None  — required elements are present but at least one is flagged for review
              (unanchored / low-confidence / out-of-window), so presence is indeterminate.
    """
    required = [e for e in elements if e.get("required")]
    present = [e for e in required if e.get("ai_value")]
    missing = [e for e in required if not e.get("ai_value")]
    # "flagged" = a present value the reviewer must still rule on: unanchored / low
    # confidence (needs_review) OR documented but dated outside the measurement window.
    weak = [e for e in present if e.get("needs_review") or e.get("in_window") is False]
    fresh_excl = [x for x in exclusions if not x.get("already_applied")]

    if not required:
        valid = None
    elif missing:
        valid = False
    elif weak:
        valid = None
    else:
        valid = True

    # CC 2.5 — recommended next step (a label only; the app does not act on it).
    if fresh_excl:
        next_step = "review_required"          # a candidate exclusion needs a human ruling
    elif valid is True:
        next_step = "ready_for_manual_entry"   # substantiating data present and clean
    elif valid is False:
        next_step = "follow_up_with_provider"  # required data missing from the chart
    else:
        next_step = "review_required"          # present but flagged — a reviewer must look

    return {
        "valid_data_present": valid,
        "substantiating_elements": [e["element_key"] for e in present],
        "missing_elements": [e["element_key"] for e in missing],
        "next_step": next_step,
        "note": ("Proposed substantiation and next step for reviewer confirmation; not a "
                 "compliance determination. QMRM entry (X-5) and provider contact (X-8) are out of scope."),
    }


def rules_version(pack):
    """The NCQA rules version applied, stamped onto every result for audit (A4).

    With more than one measurement year in scope, this is load-bearing: it records
    exactly which pack (year + schema + source) produced a determination, so a finding
    can never be misattributed to the wrong year's rules.
    """
    src = pack.get("source") or {}
    return {
        "measurement_year": src.get("measurement_year"),
        "schema_version": pack.get("schema_version"),
        "extracted_at": src.get("extracted_at"),
        "document_title": src.get("document_title"),
        "document_url": src.get("document_url"),
    }


def _now(args):
    if getattr(args, "now", None):
        return args.now
    try:
        return datetime.datetime.now().isoformat(timespec="seconds")
    except Exception:
        return None


def _proposed_measure_status(elements, exclusions, outcome):
    """Roll the per-finding proposals up to one proposed measure-level status.

    In gap closure this is the gap_outcome; in chart chase it is derived the same
    way. It is a PROPOSAL — the reviewer accepts or rejects it (measure_result).
    """
    if outcome:
        return outcome.get("status"), outcome.get("rationale")
    required = [e for e in elements if e.get("required")]
    required_found = [e for e in required if e.get("ai_value")]
    fresh = [x for x in exclusions if not x.get("already_applied")]
    oow = [e["element_key"] for e in required_found if e.get("in_window") is False]
    caveat = (f" Timing check: {', '.join(oow)} dated outside the measurement window — "
              "reviewer confirms the date counts." if oow else "")
    if required and len(required_found) == len(required):
        return ("numerator_evidence_found",
                "All required data elements are documented with anchored evidence." + caveat)
    if required_found:
        return "partial_evidence", "Some required data elements are documented; others are still missing."
    if fresh:
        return "candidate_exclusion", "No numerator evidence, but a candidate exclusion was found."
    return "no_evidence", "No supporting numerator evidence or exclusion found in the chart."


def build_review(measure_id, mode, workflow, elements, exclusions, outcome, ts):
    """Emit the measure-level review envelope + a seeded, append-only audit log.

    - measure_result: the proposed measure status plus a reviewer_decision the app
      sets to accepted/rejected/modified when the reviewer signs off the whole
      result (parallel to accepting/rejecting each finding). Defaults to "pending".
    - audit_log: the system/AI events (analysis run, each proposal, the proposed
      result), each preserving the ai_value baseline for AI-vs-final comparison. The
      app APPENDS reviewer actions to this list; it is never rewritten.
    """
    status, basis = _proposed_measure_status(elements, exclusions, outcome)
    log = []

    def add(actor, action, target, detail, ai_value=None):
        entry = {"seq": len(log) + 1, "ts": ts, "actor": actor, "action": action,
                 "target": target, "detail": detail}
        if ai_value is not None:
            entry["ai_value"] = ai_value
        log.append(entry)

    add("system", "analysis_run", measure_id, f"{mode} analysis, {workflow} workflow")
    for e in elements:
        if e.get("ai_value"):
            add("ai", "element_proposed", e["element_key"],
                f"value={e['ai_value']} confidence={e['ai_confidence']} anchored={e.get('evidence_anchored')}",
                ai_value=e["ai_value"])
    for x in exclusions:
        add("ai", "exclusion_proposed", x["rule_key"],
            f"disposition={x['disposition']} matched='{x.get('matched_term')}'")
    add("ai", "measure_result_proposed", measure_id, status)

    measure_result = {
        "proposed_status": status,
        "proposed_basis": basis,
        "reviewer_decision": "pending",     # pending | accepted | rejected | modified
        "final_status": None,               # reviewer's status when decided (may differ from proposed)
        "decided_by": None,
        "decided_at": None,
        "note": None,
    }
    return measure_result, log


def _stub_review(measure_id, mode, workflow, status, ts):
    """Minimal review envelope + audit log for a skipped / validation_failed record."""
    return (
        {"proposed_status": status, "proposed_basis": None, "reviewer_decision": "pending",
         "final_status": None, "decided_by": None, "decided_at": None, "note": None},
        [{"seq": 1, "ts": ts, "actor": "system", "action": "analysis_run",
          "target": measure_id, "detail": f"{mode} analysis, {workflow} workflow -> {status}"}],
    )


def main():
    ap = argparse.ArgumentParser(description="Assemble anchored HEDIS chart findings.")
    ap.add_argument("--pack", required=True)
    ap.add_argument("--measure", required=True)
    ap.add_argument("--text")
    ap.add_argument("--pages", help="JSON array of per-page text; derives text + offsets")
    ap.add_argument("--offsets", help="JSON array of {page,start,end}")
    ap.add_argument("--elements", help="Pass-1 model element findings JSON")
    ap.add_argument("--cross", help="Cross-measure model findings JSON (broad mode)")
    ap.add_argument("--mode", default="targeted", choices=["targeted", "broad"])
    ap.add_argument("--case", help="Chart-chase case JSON: member (age), measurement_year, "
                                   "assigned_measures, measure_state{admin_status, "
                                   "admin_exclusions_applied, last_dos}")
    ap.add_argument("--force", action="store_true",
                    help="Chase even if the case marks this measure administratively resolved")
    ap.add_argument("--workflow", default="chase", choices=["chase", "gap_closure"],
                    help="gap_closure adds provider-submission validation and a proposed gap outcome")
    ap.add_argument("--now", help="ISO timestamp for audit-log events (default: current time)")
    ap.add_argument("--broad-scan", action="store_true",
                    help="Cross-measure pass: report every pack measure the chart shows evidence for "
                         "(the source --measure is excluded). A per-chart candidate screen, not a rate.")
    ap.add_argument("--out")
    args = ap.parse_args()

    pack = _load(args.pack)
    measures = {m["measure_id"]: m for m in pack.get("measures", [])}
    measure = measures.get(args.measure)
    if not measure:
        print(f"ERROR: measure '{args.measure}' not in pack. Available: {sorted(measures)}",
              file=sys.stderr)
        return 2

    # --- Chart-chase case context (optional) -------------------------------
    # A "case" is the pursuit-list record for one member: assigned measures and
    # their administrative state. It lets the chase skip measures already resolved
    # by admin data, gate exclusions on the member's age, and flag exclusions the
    # plan already applied. Absent a case, the tool runs measure+chart as before.
    member_age, applied_keys, case_ctx = None, set(), None
    member_obj, admin_status = {}, None
    if args.case:
        case = _load(args.case)
        member = member_obj = case.get("member") or {}
        member_age = member.get("age")
        st = (case.get("measure_state") or {}).get(args.measure, {})
        admin_status = st.get("admin_status")
        applied_keys = set(st.get("admin_exclusions_applied") or [])
        cy, py = case.get("measurement_year"), (pack.get("source") or {}).get("measurement_year")
        if cy and py and cy != py:
            print(f"WARN: case measurement_year {cy} != pack {py} — codes are not stable across years",
                  file=sys.stderr)
        assigned = case.get("assigned_measures") or []
        if assigned and args.measure not in assigned:
            print(f"WARN: '{args.measure}' is not in case.assigned_measures {assigned}", file=sys.stderr)
        resolved = admin_status in ("gap_closed", "excluded") or bool(applied_keys)
        case_ctx = {
            "member_id": member.get("id"),
            "member_age": member_age,
            "admin_status": admin_status,
            "admin_exclusions_applied": sorted(applied_keys),
            "last_dos": st.get("last_dos"),
            "chased": True,
        }
        if resolved and not args.force:
            reason = ("already gap-closed" if admin_status == "gap_closed"
                      else f"admin exclusion already applied ({', '.join(sorted(applied_keys))})"
                      if applied_keys else "already excluded administratively")
            case_ctx["chased"] = False
            sr_result, sr_log = _stub_review(args.measure, args.mode, args.workflow,
                                             "skipped_admin_resolved", _now(args))
            result = {
                "mode": args.mode, "measure_id": args.measure,
                "measure_name": measure.get("measure_name"),
                "measurement_year": py,
                "status": "skipped_admin_resolved",
                "reason": f"{reason}; pass --force to chase anyway",
                "case_context": case_ctx,
                "measure_result": sr_result,
                "audit_log": sr_log,
                "disclaimer": DISCLAIMER,
            }
            out_json = json.dumps(result, indent=2)
            if args.out:
                with open(args.out, "w", encoding="utf-8") as fh:
                    fh.write(out_json)
                print(f"Wrote {args.out}: skipped {args.measure} — {reason} (admin-resolved).")
            else:
                print(out_json)
            return 0

    if args.pages:
        text, offsets = offsets_from_pages(_load(args.pages))
    else:
        if not args.text:
            print("ERROR: provide --text (or --pages).", file=sys.stderr)
            return 2
        with open(args.text, "r", encoding="utf-8") as fh:
            text = fh.read()
        offsets = _load(args.offsets) if args.offsets else [{"page": 1, "start": 0, "end": len(text)}]

    # --- Gap-closure submission gate (optional) ----------------------------
    # In gap closure a provider submits the chart, so validate it belongs to the
    # case member/measure before trusting it. A member-identity mismatch is a hard
    # stop (wrong-member PHI risk) — return the validation report and do not extract.
    validation = None
    py = (pack.get("source") or {}).get("measurement_year")
    if args.workflow == "gap_closure":
        validation = validate_submission(text, measure, member_obj)
        if validation["verdict"] == "failed_member_mismatch":
            vf_result, vf_log = _stub_review(args.measure, args.mode, args.workflow,
                                             "validation_failed", _now(args))
            result = {
                "workflow": "gap_closure", "mode": args.mode, "measure_id": args.measure,
                "measure_name": measure.get("measure_name"), "measurement_year": py,
                "status": "validation_failed",
                "reason": "neither the member name nor DOB could be located in the chart — "
                          "likely a wrong-member or wrong-document submission",
                "validation": validation,
                "case_context": case_ctx,
                "measure_result": vf_result,
                "audit_log": vf_log,
                "disclaimer": DISCLAIMER,
            }
            out_json = json.dumps(result, indent=2)
            if args.out:
                with open(args.out, "w", encoding="utf-8") as fh:
                    fh.write(out_json)
                print(f"Wrote {args.out}: validation_failed for {args.measure} (member mismatch).")
            else:
                print(out_json)
            return 0

    # --- Broad cross-measure pass (optional) -------------------------------
    # One retrieved chart, every measure in the pack: which other open gaps could
    # this chart also close. Emitted on its own; targeted extraction is separate.
    if args.broad_scan:
        scan = broad_scan(text, offsets, pack, member_age=member_age, exclude_measure=args.measure)
        result = {
            "mode": "broad", "source_measure_id": args.measure,
            "measurement_year": (pack.get("source") or {}).get("measurement_year"),
            "case_context": case_ctx,
            "broad_scan": scan,
            "summary": {"measures_scanned": len(scan),
                        "measures_with_evidence": sum(1 for r in scan if r["has_evidence"])},
            "disclaimer": DISCLAIMER,
        }
        out_json = json.dumps(result, indent=2)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(out_json)
            print(f"Wrote {args.out}: broad scan of {len(scan)} measures, "
                  f"{result['summary']['measures_with_evidence']} with chart evidence.")
        else:
            print(out_json)
        return 0

    pass1 = _load(args.elements) if args.elements else []
    cross_in = _load(args.cross) if args.cross else []

    elements = build_elements(text, offsets, measure, pass1)
    # exclusion scan needs page mapping; rebind page_for_offset via offsets
    exclusions = find_exclusions(text, pack, measure, member_age=member_age, applied_keys=applied_keys)
    for ex in exclusions:
        ex["page_number"] = page_for_offset(offsets, ex["char_start"])
    cross = build_cross(text, offsets, pack, args.measure, cross_in) if args.mode == "broad" else []

    found = [e for e in elements if e["ai_value"]]
    required_missing = [e for e in elements if e["required"] and not e["ai_value"]]
    fresh_exclusions = [x for x in exclusions if not x.get("already_applied")]
    outcome = gap_outcome(elements, exclusions, admin_status) if args.workflow == "gap_closure" else None
    measure_result, audit_log = build_review(
        args.measure, args.mode, args.workflow, elements, exclusions, outcome, _now(args))

    result = {
        "workflow": args.workflow,
        "mode": args.mode,
        "measure_id": args.measure,
        "measure_name": measure.get("measure_name"),
        "measurement_year": py,
        "rules_version": rules_version(pack),
        "case_context": case_ctx,
        "validation": validation,
        "elements": elements,
        "exclusions": exclusions,
        "cross_measure": cross,
        "gap_outcome": outcome,
        "substantiation": substantiation(elements, exclusions),
        "measure_result": measure_result,
        "audit_log": audit_log,
        "summary": {
            "elements_total": len(elements),
            "elements_found": len(found),
            "required_missing": len(required_missing),
            "required_missing_keys": [e["element_key"] for e in required_missing],
            "exclusions_proposed": len(fresh_exclusions),
            "exclusions_already_applied": len(exclusions) - len(fresh_exclusions),
            "cross_measure_found": len(cross),
            "mean_confidence": round(sum(e["ai_confidence"] for e in found) / len(found), 3) if found else 0.0,
            "anchored_evidence": sum(1 for e in elements if e.get("evidence_anchored")),
            "needs_review": sum(1 for e in elements if e.get("needs_review"))
                            + sum(1 for x in exclusions if x.get("needs_review")),
            "out_of_window_required": sum(1 for e in elements
                                          if e.get("required") and e.get("in_window") is False),
        },
        "disclaimer": DISCLAIMER,
    }

    out_json = json.dumps(result, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(out_json)
        s = result["summary"]
        print(f"Wrote {args.out}: {s['elements_found']}/{s['elements_total']} elements found, "
              f"{s['required_missing']} required missing, {s['exclusions_proposed']} exclusions proposed.")
    else:
        print(out_json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
