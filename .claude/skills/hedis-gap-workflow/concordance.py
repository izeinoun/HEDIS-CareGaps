#!/usr/bin/env python3
"""Over-read & AI-vs-final concordance analytics — QA of the review process.

Deterministic and cross-case: given a collection of REVIEWED findings (each = a
`hedis-rules-to-findings` output plus the application's recorded `decisions`,
`measure_result`, and `qa`), compute how often the human confirmed the AI vs. edited
or rejected it, how often the measure-level sign-off overrode the proposal, and how
often the QA over-read concurred with the first reviewer. It also proposes an
adjustment to the analysis skill's `needs_review` confidence threshold based on where
disagreements actually cluster.

These are QA/process metrics (reviewer behavior), not member-compliance rates — that
is why they live in the workflow skill, not the proposal-only analysis skill.

Note: this captures reviewer↔QA *over-read concurrence* (sequential) and, separately,
*agreement* on independent blind double-reads (`double_read_agreement`). Both are plain
agreement counts — not inter-rater-reliability statistics (Cohen's kappa and the like are
out of scope, X-9).

Usage:
  python concordance.py --records REVIEWED.json [--gate 0.7] [--out OUT.json]
"""
import argparse
import json
import statistics
import sys

DISCLAIMER = (
    "QA/process analytics on reviewer behavior (AI-vs-final agreement and over-read "
    "concurrence). Not a member-compliance rate and not a clinical determination."
)


def _rate(n, d):
    return round(n / d, 3) if d else None


def double_read_agreement(pairs):
    """Agreement capture on INDEPENDENT blind double-reads (CC 3.1): two reviewers each
    independently signed off the same case×measure. Reports how often their final
    dispositions agreed, overall and per measure, and lists the disagreements so a lead
    can adjudicate.

    A plain agreement count — deliberately NOT an inter-rater-reliability statistic
    (Cohen's kappa and other reliability coefficients are out of scope, X-9). The
    requirement is that agreement/disagreement is *captured*, not that a reliability
    coefficient is produced.
    """
    pairs = [p for p in pairs if p.get("a") and p.get("b")]
    n = len(pairs)
    agree = sum(1 for p in pairs if p["a"] == p["b"])
    by_measure = {}
    disagreements = []
    for p in pairs:
        d = by_measure.setdefault(p.get("measure_id"), {"pairs": 0, "agree": 0})
        d["pairs"] += 1
        d["agree"] += 1 if p["a"] == p["b"] else 0
        if p["a"] != p["b"]:
            disagreements.append({"measure_id": p.get("measure_id"),
                                  "read_1": p["a"], "read_2": p["b"]})
    return {
        "pairs": n,
        "agree": agree,
        "disagree": n - agree,
        "agreement_rate": _rate(agree, n),
        "by_measure": {m: {**d, "agreement_rate": _rate(d["agree"], d["pairs"])}
                       for m, d in sorted(by_measure.items())},
        "disagreements": disagreements,
        "disclaimer": ("Agreement capture on independent blind double-reads. A QA/process "
                       "signal, not an inter-rater-reliability statistic or a compliance rate."),
    }


def concordance(records, gate=0.7):
    el_agree = el_edit = el_reject = value_changes = 0
    signed = accepted = overridden = 0
    qa_total = concur = rework = 0
    conf_confirmed, conf_disagreed = [], []
    by_measure, by_element = {}, {}

    for f in records:
        if f.get("status") in ("skipped_admin_resolved", "validation_failed"):
            continue
        mid = f.get("measure_id")
        conf_by = {}
        for e in f.get("elements", []):
            conf_by["el:" + e["element_key"]] = e.get("ai_confidence")
        for x in f.get("exclusions", []):
            conf_by["ex:" + x["rule_key"]] = x.get("ai_confidence")

        for key, dec in (f.get("decisions") or {}).items():
            act = dec.get("action")
            bm = by_measure.setdefault(mid, {"agree": 0, "edit": 0, "reject": 0})
            be = by_element.setdefault(key.split(":", 1)[-1], {"agree": 0, "edit": 0, "reject": 0}) \
                if key.startswith("el:") else None
            conf = conf_by.get(key)
            if act == "confirm":
                el_agree += 1; bm["agree"] += 1
                if be: be["agree"] += 1
                if conf is not None: conf_confirmed.append(conf)
            elif act == "modify":
                el_edit += 1; bm["edit"] += 1; value_changes += 1
                if be: be["edit"] += 1
                if conf is not None: conf_disagreed.append(conf)
            elif act == "reject":
                el_reject += 1; bm["reject"] += 1
                if be: be["reject"] += 1
                if conf is not None: conf_disagreed.append(conf)

        mr = f.get("measure_result") or {}
        rd = mr.get("reviewer_decision")
        if rd in ("accepted", "rejected", "modified"):
            signed += 1
            if rd == "accepted":
                accepted += 1
            else:
                overridden += 1

        qa = (f.get("qa") or {}).get("state")
        if qa:
            qa_total += 1
            qa_ok = qa == "qa passed"
            if qa_ok:
                concur += 1
            elif qa == "needs rework":
                rework += 1

    total_dec = el_agree + el_edit + el_reject

    # Gate suggestion: if edits/rejects cluster at HIGH confidence, the needs_review
    # threshold is too low (weak values slip past); recommend raising it.
    suggestion = None
    if conf_disagreed:
        med_dis = round(statistics.median(conf_disagreed), 3)
        high_conf_disagreements = sum(1 for c in conf_disagreed if c > gate)
        rec = "raise" if high_conf_disagreements >= max(1, len(conf_disagreed) // 2) else "hold"
        suggestion = {
            "current_gate": gate,
            "disagreements": len(conf_disagreed),
            "disagreement_median_confidence": med_dis,
            "high_confidence_disagreements": high_conf_disagreements,
            "recommendation": rec,
            "suggested_gate": round(min(0.95, med_dis + 0.05), 3) if rec == "raise" else gate,
            "note": ("Edits/rejects cluster above the current gate — high-confidence AI values are being "
                     "changed, so raise the needs_review threshold to force more of them into review."
                     if rec == "raise" else
                     "Disagreements sit at or below the current gate — the threshold is catching the weak "
                     "proposals; hold it."),
        }

    def with_rate(d):
        t = d["agree"] + d["edit"] + d["reject"]
        return {**d, "agreement_rate": _rate(d["agree"], t)}

    return {
        "ai_vs_final": {
            "decisions": total_dec, "agree": el_agree, "edited": el_edit, "rejected": el_reject,
            "agreement_rate": _rate(el_agree, total_dec),
            "value_change_rate": _rate(value_changes, total_dec),
        },
        "measure_result": {
            "signed_off": signed, "accepted": accepted, "overridden": overridden,
            "override_rate": _rate(overridden, signed),
        },
        "over_read": {
            "qa_reviewed": qa_total, "concur": concur, "rework": rework,
            "concurrence_rate": _rate(concur, qa_total),
        },
        "by_measure": {m: with_rate(d) for m, d in sorted(by_measure.items())},
        "by_element": dict(sorted(by_element.items(), key=lambda kv: -(kv[1]["edit"] + kv[1]["reject"]))),
        "gate_suggestion": suggestion,
        "disclaimer": DISCLAIMER,
    }


def main():
    ap = argparse.ArgumentParser(description="Over-read & AI-vs-final concordance analytics.")
    ap.add_argument("--records", required=True, help="JSON array of reviewed findings objects")
    ap.add_argument("--gate", type=float, default=0.7, help="current needs_review confidence gate")
    ap.add_argument("--out")
    args = ap.parse_args()
    with open(args.records, encoding="utf-8") as fh:
        records = json.load(fh)
    result = concordance(records, gate=args.gate)
    out_json = json.dumps(result, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(out_json)
        print(f"Wrote {args.out}: agreement {result['ai_vs_final']['agreement_rate']}, "
              f"over-read concurrence {result['over_read']['concurrence_rate']}.")
    else:
        print(out_json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
