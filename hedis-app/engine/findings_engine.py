"""Assemble anchored, proposal-only findings for one chart + measure.

This is a thin orchestration layer over the *authoritative* deterministic engine
that ships inside the `hedis-rules-to-findings` skill (`anchor_findings.py`). We
import that module directly and call its functions — anchoring, the negation-aware
exclusion scan, submission validation, and the proposed gap outcome — so the app's
behaviour is exactly the skill's and stays in sync with it. We only add the Pass-1
element extraction (extract_elements.py) and the JSON plumbing around it.

Nothing here decides compliance; every element and exclusion is a proposal the
reviewer rules on.
"""
from __future__ import annotations

import importlib.util
import re
from datetime import datetime, timezone
from pathlib import Path

from .extract_elements import extract_elements

# --- Load the skill's authoritative deterministic engine -------------------
_SKILL_DIR = (
    Path(__file__).resolve().parents[2]
    / ".claude" / "skills" / "hedis-rules-to-findings"
)
_ANCHOR_PATH = _SKILL_DIR / "anchor_findings.py"
_spec = importlib.util.spec_from_file_location("anchor_findings", _ANCHOR_PATH)
anchor = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(anchor)  # type: ignore[union-attr]

DISCLAIMER = anchor.DISCLAIMER
detect_multiple_members = anchor.detect_multiple_members  # A12: multi-patient screen


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# The compliance advisory, compound-component tracker, needs_review flag, and timing
# reconciliation now live in the skill's anchor_findings.py (attached on build_elements /
# find_exclusions), so the app consumes them rather than recomputing.


def broad(pack: dict, text: str, offsets: list[dict], case: dict | None = None,
          source_measure: str | None = None) -> dict:
    """Cross-measure 'broad' pass — which gaps this one chart could also close.

    Delegates to the skill's deterministic `broad_scan`. Marks each scanned measure
    with the member's admin state (from the case) so the UI can highlight the *open*
    gaps the chart has evidence for.
    """
    member_age = ((case or {}).get("member") or {}).get("age")
    applied = {mid: st.get("admin_exclusions_applied") or []
               for mid, st in ((case or {}).get("measure_state") or {}).items()}
    scan = anchor.broad_scan(text, offsets, pack, member_age=member_age,
                             exclude_measure=source_measure, applied_by_measure=applied)
    state = (case or {}).get("measure_state") or {}
    assigned = set((case or {}).get("assigned_measures") or [])
    for row in scan:
        mid = row["measure_id"]
        row["admin_status"] = state.get(mid, {}).get("admin_status")
        row["assigned"] = mid in assigned
    return {
        "mode": "broad",
        "source_measure_id": source_measure,
        "measurement_year": (pack.get("source") or {}).get("measurement_year"),
        "broad_scan": scan,
        "summary": {"measures_scanned": len(scan),
                    "measures_with_evidence": sum(1 for r in scan if r["has_evidence"])},
        "disclaimer": DISCLAIMER,
    }


def analyze(
    pack: dict,
    measure_id: str,
    text: str,
    offsets: list[dict],
    case: dict | None = None,
    workflow: str = "chase",
    force: bool = False,
    prefer_provider: str | None = None,
    ts: str | None = None,
) -> dict:
    """Run the full review for one measure against one chart.

    Mirrors `anchor_findings.main()` but keeps everything in-process so the app
    can hold the Pass-1 provider, timings, and results together. Also emits the
    skill's measure_result + audit_log review envelope and the app's advisory aids.
    """
    ts = ts or _now_iso()
    measures = {m["measure_id"]: m for m in pack.get("measures", [])}
    measure = measures.get(measure_id)
    if not measure:
        return {"status": "error", "reason": f"measure '{measure_id}' not in pack",
                "measure_id": measure_id, "disclaimer": DISCLAIMER}

    py = (pack.get("source") or {}).get("measurement_year")
    rv = anchor.rules_version(pack)  # A4: applied NCQA rules version, stamped on every result

    # --- Case context (age gate, admin state, skip-if-resolved) ------------
    member_age, applied_keys, case_ctx = None, set(), None
    member_obj, admin_status = {}, None
    if case:
        member = member_obj = case.get("member") or {}
        member_age = member.get("age")
        st = (case.get("measure_state") or {}).get(measure_id, {})
        admin_status = st.get("admin_status")
        applied_keys = set(st.get("admin_exclusions_applied") or [])
        resolved = admin_status in ("gap_closed", "excluded") or bool(applied_keys)
        case_ctx = {
            "member_id": member.get("id"),
            "member_age": member_age,
            "admin_status": admin_status,
            "admin_exclusions_applied": sorted(applied_keys),
            "last_dos": st.get("last_dos"),
            "chased": True,
        }
        if resolved and not force:
            reason = ("already gap-closed" if admin_status == "gap_closed"
                      else f"admin exclusion already applied ({', '.join(sorted(applied_keys))})"
                      if applied_keys else "already excluded administratively")
            case_ctx["chased"] = False
            mr, log = anchor._stub_review(measure_id, "targeted", workflow, "skipped_admin_resolved", ts)
            return {
                "workflow": workflow, "mode": "targeted", "measure_id": measure_id,
                "measure_name": measure.get("measure_name"), "measurement_year": py, "rules_version": rv,
                "status": "skipped_admin_resolved",
                "reason": f"{reason}; re-review with Force to chase anyway",
                "case_context": case_ctx, "provider": None,
                "measure_result": mr, "audit_log": log, "disclaimer": DISCLAIMER,
            }

    # --- Gap-closure submission gate (hard stop on wrong-member) -----------
    validation = None
    if workflow == "gap_closure":
        validation = anchor.validate_submission(text, measure, member_obj)
        if validation["verdict"] == "failed_member_mismatch":
            mr, log = anchor._stub_review(measure_id, "targeted", workflow, "validation_failed", ts)
            return {
                "workflow": "gap_closure", "mode": "targeted", "measure_id": measure_id,
                "measure_name": measure.get("measure_name"), "measurement_year": py, "rules_version": rv,
                "status": "validation_failed",
                "reason": "neither the member name nor DOB could be located in the chart — "
                          "likely a wrong-member or wrong-document submission",
                "validation": validation, "case_context": case_ctx,
                "provider": None, "measure_result": mr, "audit_log": log, "disclaimer": DISCLAIMER,
            }

    # --- Pass 1 (model/heuristic) + Pass 2 (deterministic) -----------------
    pass1, provider = extract_elements(measure, text, prefer=prefer_provider, measurement_year=py)
    elements = anchor.build_elements(text, offsets, measure, pass1)
    exclusions = anchor.find_exclusions(text, pack, measure,
                                        member_age=member_age, applied_keys=applied_keys)
    for ex in exclusions:
        ex["page_number"] = anchor.page_for_offset(offsets, ex["char_start"])
    # The skill now attaches the compliance advisory, needs_review, timing
    # reconciliation, and compound components directly on build_elements /
    # find_exclusions — the app just consumes them.

    found = [e for e in elements if e["ai_value"]]
    required_missing = [e for e in elements if e["required"] and not e["ai_value"]]
    fresh = [x for x in exclusions if not x.get("already_applied")]
    outcome = anchor.gap_outcome(elements, exclusions, admin_status) if workflow == "gap_closure" else None
    measure_result, audit_log = anchor.build_review(
        measure_id, "targeted", workflow, elements, exclusions, outcome, ts)

    return {
        "workflow": workflow, "mode": "targeted", "measure_id": measure_id,
        "measure_name": measure.get("measure_name"), "measurement_year": py, "rules_version": rv,
        "provider": provider,
        "case_context": case_ctx, "validation": validation,
        "elements": elements, "exclusions": exclusions, "gap_outcome": outcome,
        "substantiation": anchor.substantiation(elements, exclusions),
        "measure_result": measure_result, "audit_log": audit_log,
        "summary": {
            "elements_total": len(elements),
            "elements_found": len(found),
            "required_missing": len(required_missing),
            "required_missing_keys": [e["element_key"] for e in required_missing],
            "exclusions_proposed": len(fresh),
            "exclusions_already_applied": len(exclusions) - len(fresh),
            "mean_confidence": round(sum(e["ai_confidence"] for e in found) / len(found), 3) if found else 0.0,
            "anchored_evidence": sum(1 for e in elements if e.get("evidence_anchored")),
            "needs_review": sum(1 for e in elements if e.get("needs_review"))
                            + sum(1 for x in exclusions if x.get("needs_review")),
            "out_of_window_required": sum(1 for e in elements
                                          if e.get("required") and e.get("in_window") is False),
        },
        "disclaimer": DISCLAIMER,
    }
