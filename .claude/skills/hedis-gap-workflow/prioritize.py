#!/usr/bin/env python3
"""Rank open care gaps for review triage — the retrieval-prioritization step.

Deterministic, dependency-free, and cross-case: given a list of open case×measure
items (built by the application from its cases + the findings the analysis skill
produced) and a plan priority-config, emit a ranked worklist with a fully transparent
per-item score breakdown.

The score is operational, NOT a clinical or compliance determination:

    score = measure_weight * (1 + yield_bonus) + urgency

  * measure_weight — from the priority-config (CMS Star-informed defaults, plan-
    overridable). Star/plan policy, never an NCQA spec value.
  * yield_bonus    — how likely a chart review closes the gap: a bonus when the
    required data is already documented (near-certain close), a smaller bonus when
    partially documented, a penalty for unresolved weak (needs_review) findings.
  * urgency        — ramps up as the measurement-year deadline approaches.

This never emits a member-compliance rate. A ranked worklist is work management, not
a reportable rate.

Usage:
  python prioritize.py --items ITEMS.json [--config priority-config.json] [--out OUT.json]
"""
import argparse
import json
import sys

DISCLAIMER = (
    "Operational worklist prioritization for review triage. Scores reflect measure "
    "weight and evidence yield, not member compliance; not a clinical or NCQA determination."
)


def _urgency(days_to_deadline, s):
    if days_to_deadline is None:
        return 0.0
    d = max(0, int(days_to_deadline))
    window = s.get("urgency_window_days", 90)
    if d >= window:
        return 0.0
    pts = s.get("urgency_per_30d", 0.5) * ((window - d) / 30.0)
    return round(min(s.get("urgency_cap", 1.5), pts), 3)


def score_item(item, config):
    measures = config.get("measures", {})
    default_w = (config.get("defaults") or {}).get("weight", 1.0)
    s = config.get("scoring", {})
    mid = item.get("measure_id")
    mcfg = measures.get(mid, {})
    weight = float(mcfg.get("weight", default_w))

    analyzed = bool(item.get("analyzed"))
    req_missing = item.get("required_missing")
    needs_review = int(item.get("needs_review") or 0)

    yield_bonus, closability = 0.0, "unknown"
    if analyzed and req_missing is not None:
        if req_missing == 0:
            yield_bonus += s.get("closable_bonus", 0.6)
            closability = "closable"
        elif 0 < req_missing <= s.get("partial_missing_max", 2):
            yield_bonus += s.get("partial_bonus", 0.25)
            closability = "partial"
        else:
            closability = "sparse"
        yield_bonus -= s.get("needs_review_penalty", 0.1) * min(needs_review, 3)

    urgency = _urgency(item.get("days_to_deadline"), s)
    base = weight * (1.0 + yield_bonus)
    score = round(base + urgency, 3)
    return score, {
        "measure_weight": weight,
        "measure_domain": mcfg.get("domain"),
        "yield_bonus": round(yield_bonus, 3),
        "urgency": urgency,
        "closability": closability,
    }


def prioritize(items, config):
    """Return a ranked worklist. Items already administratively resolved
    (gap_closed / excluded) are dropped — you don't chase a closed gap."""
    scored = []
    for it in items:
        if it.get("admin_status") in ("gap_closed", "excluded"):
            continue
        sc, factors = score_item(it, config)
        scored.append({**it, "priority_score": sc, "factors": factors})
    scored.sort(key=lambda x: (-x["priority_score"], x.get("measure_id") or ""))
    for i, x in enumerate(scored, start=1):
        x["rank"] = i
    return {
        "config_version": config.get("config_version"),
        "measurement_year": (config.get("source") or {}).get("measurement_year"),
        "items": scored,
        "summary": {
            "items": len(scored),
            "measures": sorted({x["measure_id"] for x in scored if x.get("measure_id")}),
            "top_score": scored[0]["priority_score"] if scored else 0.0,
        },
        "disclaimer": DISCLAIMER,
    }


def main():
    ap = argparse.ArgumentParser(description="Rank open care gaps for review triage.")
    ap.add_argument("--items", required=True, help="JSON array of open case×measure items")
    ap.add_argument("--config", help="priority-config JSON (defaults to a weight of 1.0 for all)")
    ap.add_argument("--out")
    args = ap.parse_args()
    with open(args.items, encoding="utf-8") as fh:
        items = json.load(fh)
    config = {"config_version": "default", "defaults": {"weight": 1.0}, "measures": {}, "scoring": {}}
    if args.config:
        with open(args.config, encoding="utf-8") as fh:
            config = json.load(fh)
    result = prioritize(items, config)
    out_json = json.dumps(result, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(out_json)
        print(f"Wrote {args.out}: {result['summary']['items']} items ranked.")
    else:
        print(out_json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
