"""HEDIS payer-side data extraction & care-gap analysis app.

Flow:
  1. Rules admin  (/rules)      view rules packs; upload NCQA spec -> generate pack.
  2. Upload       (/upload)     upload a patient profile PDF + the identified
                                measures and gaps (the "case").
  3. Analyze      (/case/..)    per open measure: locate the measure's data and
                                gap-filling evidence, each with a source anchor.
  4. Review       (/review/..)  split-panel: chart on the left with highlighted
                                evidence, proposals on the right to confirm/edit/reject.

Everything is a proposal for a human reviewer; the app never decides compliance.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from flask import (Flask, Response, abort, jsonify, redirect, render_template,
                   request, send_file, url_for)
from werkzeug.utils import secure_filename

from engine.findings_engine import analyze, broad, detect_multiple_members, DISCLAIMER
from engine import pdf_extract, vsd
from engine.workflow import prioritize, concordance, double_read_agreement, authorize, can

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
DATA = BASE / "data"
PACKS, CASES, CHARTS, FINDINGS = DATA / "packs", DATA / "cases", DATA / "charts", DATA / "findings"
VSD = DATA / "vsd"
for d in (PACKS, CASES, CHARTS, FINDINGS, VSD):
    d.mkdir(parents=True, exist_ok=True)


# --- Load the Anthropic credential from the project's key file -------------
def _load_api_key() -> bool:
    if os.getenv("ANTHROPIC_API_KEY"):
        return True
    for name in ("anthropickey", "anthropicapi", "anthropic.key"):
        p = ROOT / name
        if p.exists():
            key = p.read_text(encoding="utf-8").strip()
            if key:
                os.environ["ANTHROPIC_API_KEY"] = key
                return True
    return False


HAS_KEY = _load_api_key()
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024  # 64 MB uploads
_now = lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")  # noqa: E731


# Two acting users with roles (no real auth — the header dropdown picks who is acting;
# every decision, sign-off, QA over-read, and assignment is stamped with this user).
USERS = [
    {"id": "u_reviewer", "name": "Dana Cole", "role": "Reviewer"},
    {"id": "u_overreader", "name": "Sam Ortiz", "role": "Over-reader"},
    {"id": "u_admin", "name": "Morgan Lee", "role": "Administrator"},
    {"id": "u_auditor", "name": "Riley Kim", "role": "Auditor"},
]
# The reviewer's HEDIS determination at sign-off (skill's canonical final_status set).
HEDIS_FINAL = {"gap_closed", "gap_open", "exclusion_applied", "needs_more_info"}
_ACCEPT_MAP = {
    "closable_on_documentation": "gap_closed", "numerator_evidence_found": "gap_closed",
    "previously_closed": "gap_closed",
    "exclusion_candidate": "exclusion_applied", "candidate_exclusion": "exclusion_applied",
    "partial_documentation": "gap_open", "partial_evidence": "gap_open",
    "no_evidence": "gap_open", "no_impact_to_gap": "gap_open",
}
GATE_CONF = 0.7  # confidence gate: findings below this (or unanchored) must be decided before sign-off


@app.context_processor
def _inject_globals():
    """Truthful provider pill on every page: a present key that the API later
    rejected flips to the offline extractor, and the header reflects that.
    Also injects the acting-user roster for the header selector."""
    from engine import extract_elements as _ee
    return {"has_key": HAS_KEY and not _ee._ANTHROPIC_DISABLED, "users": USERS}


def _resolve_user(uid: str | None) -> dict:
    for u in USERS:
        if u["id"] == uid:
            return u
    return {"id": uid or "unknown", "name": "Unknown user", "role": "Reviewer"}


@app.context_processor
def _nav_counts():
    """Sidebar badge counts: patients, open worklist items, QA-pending items."""
    try:
        cases = list_cases()
        patients = len(cases)
        worklist = qa = 0
        for c in cases:
            for mid in c.get("assigned_measures", []):
                fp = findings_path(c["id"], mid)
                f = _read_json(fp) if fp.exists() else None
                mr = (f or {}).get("measure_result") or {}
                decided = mr.get("reviewer_decision") in ("accepted", "rejected", "modified")
                if not decided:
                    worklist += 1
                elif not (f or {}).get("qa"):
                    qa += 1
        return {"nav_counts": {"patients": patients, "worklist": worklist, "qa": qa}}
    except Exception:  # noqa: BLE001
        return {"nav_counts": {}}


def _migrate_cases():
    """One-time backfill: give pre-existing cases a stable document_id + source_filename
    (A1) so older uploads match the current contract."""
    for p in CASES.glob("*.json"):
        if p.name == "example-case.json":
            continue
        try:
            case = _read_json(p)
        except Exception:  # noqa: BLE001
            continue
        changed = False
        if not case.get("document_id"):
            case["document_id"] = "doc_" + uuid.uuid4().hex[:12]
            changed = True
        if not case.get("source_filename") and case.get("chart_filename"):
            case["source_filename"] = f"{case['id']}__{case['chart_filename']}"
            changed = True
        if changed:
            _write_json(p, case)


def _primary_actors(f: dict) -> set:
    """User ids that performed the PRIMARY read (finding decisions + primary sign-off) —
    the people a QA over-read / blind second read must be independent of (SoD)."""
    ids = {(d.get("by") or {}).get("id") for d in (f.get("decisions") or {}).values()}
    for e in f.get("audit_log", []):
        if e.get("action", "").startswith("measure_result_") and "(2nd read)" not in (e.get("detail") or ""):
            ids.add((e.get("by") or {}).get("id"))
    ids.discard(None)
    return ids


def _deny(reason: str):
    return jsonify({"ok": False, "error": reason}), 403


def _append_audit(f: dict, actor: str, action: str, target: str, detail: str,
                  by: dict | None = None, ai_value=None):
    """Append one entry to a findings file's audit_log (append-only, never rewrites)."""
    log = f.setdefault("audit_log", [])
    entry = {"seq": len(log) + 1, "ts": _now(), "actor": actor,
             "action": action, "target": target, "detail": detail}
    if by:
        entry["by"] = {"id": by["id"], "name": by["name"], "role": by["role"]}
    if ai_value is not None:
        entry["ai_value"] = ai_value
    log.append(entry)


def _ensure_review(f: dict) -> dict:
    """Backfill measure_result / audit_log on findings written before the skill added
    them, so older files still drive the sign-off and audit views."""
    if "measure_result" not in f:
        proposed = (f.get("gap_outcome") or {}).get("status") or f.get("status") or "no_evidence"
        f["measure_result"] = {"proposed_status": proposed, "proposed_basis": None,
                               "reviewer_decision": "pending", "final_status": None,
                               "decided_by": None, "decided_at": None, "note": None}
    f.setdefault("audit_log", [])
    return f


# --- Storage helpers -------------------------------------------------------
def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def list_packs() -> list[dict]:
    packs = [_read_json(p) for p in sorted(PACKS.glob("*.json"))]
    packs.sort(key=lambda p: (p.get("source") or {}).get("measurement_year", ""), reverse=True)
    return packs


def get_pack(year: str | None):
    packs = list_packs()
    if not packs:
        return None
    if year:
        for p in packs:
            if (p.get("source") or {}).get("measurement_year") == year:
                return p
    return packs[0]


def list_vsd_packs() -> list[dict]:
    packs = [_read_json(p) for p in sorted(VSD.glob("*.json"))]
    packs.sort(key=lambda p: (p.get("source") or {}).get("measurement_year", ""), reverse=True)
    return packs


def get_vsd(year: str | None):
    packs = list_vsd_packs()
    if not packs:
        return None
    if year:
        for p in packs:
            if (p.get("source") or {}).get("measurement_year") == year:
                return p
    return packs[0]


def list_cases() -> list[dict]:
    cases = [_read_json(p) for p in CASES.glob("*.json") if p.name != "example-case.json"]
    cases.sort(key=lambda c: c.get("created_at", ""), reverse=True)
    return cases


def get_case(case_id: str):
    p = CASES / f"{case_id}.json"
    return _read_json(p) if p.exists() else None


def load_chart(case_id: str):
    txt = (CHARTS / f"{case_id}.txt")
    off = (CHARTS / f"{case_id}.offsets.json")
    if not txt.exists():
        return None, None
    return txt.read_text(encoding="utf-8"), _read_json(off)


def findings_path(case_id: str, measure_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", measure_id)
    return FINDINGS / f"{case_id}__{safe}.json"


def all_findings() -> list[dict]:
    """Every analyzed case×measure result, joined to its member — the queue's rows."""
    rows = []
    case_cache: dict[str, dict] = {}
    for p in sorted(FINDINGS.glob("*.json")):
        f = _read_json(p)
        cid = f.get("case_id")
        if not cid:
            continue
        case = case_cache.get(cid) or get_case(cid)
        if not case:
            continue
        case_cache[cid] = case
        f["_member"] = case.get("member", {})
        rows.append(f)
    rows.sort(key=lambda f: f.get("analyzed_at", ""), reverse=True)
    return rows


def _decision_status(f: dict) -> str:
    """Roll a findings file up to a QA state for the queue."""
    if f.get("status") in ("skipped_admin_resolved", "validation_failed"):
        return "n/a"
    qa = f.get("qa", {}).get("state")
    if qa:
        return qa
    if (f.get("measure_result") or {}).get("reviewer_decision") in ("accepted", "rejected", "modified"):
        return "signed off"
    reviewable = sum(1 for e in f.get("elements", []) if e.get("ai_value")) + \
        sum(1 for x in f.get("exclusions", []) if not x.get("already_applied"))
    decided = len(f.get("decisions", {}))
    if reviewable == 0:
        return "no proposals"
    if decided == 0:
        return "unreviewed"
    if decided < reviewable:
        return "in review"
    return "reviewed"


# --- Dashboard -------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html", cases=list_cases(), packs=list_packs())


# --- Upload a patient profile ---------------------------------------------
@app.route("/upload", methods=["GET", "POST"])
def upload():
    pack = get_pack(request.values.get("year"))
    if request.method == "GET":
        if not pack:
            return render_template("upload.html", pack=None, packs=list_packs())
        return render_template("upload.html", pack=pack, packs=list_packs())

    if not pack:
        abort(400, "No rules pack loaded — add one in the Rules admin first.")
    file = request.files.get("chart")
    if not file or not file.filename:
        abort(400, "A chart PDF (or .txt) is required.")

    case_id = uuid.uuid4().hex[:12]
    document_id = "doc_" + uuid.uuid4().hex[:12]     # A1: stable ID for the source document
    fname = secure_filename(file.filename)
    src_path = CHARTS / f"{case_id}__{fname}"
    file.save(src_path)
    try:
        os.chmod(src_path, 0o444)                    # A1: original is read-only (never overwritten/altered)
    except OSError:
        pass

    try:
        if fname.lower().endswith(".txt"):
            text, offsets, _ = pdf_extract.extract_text_file(str(src_path))
        else:
            text, offsets, _ = pdf_extract.extract_pdf(str(src_path))
    except Exception as exc:  # noqa: BLE001
        abort(400, f"Could not read the uploaded file: {exc}")

    (CHARTS / f"{case_id}.txt").write_text(text, encoding="utf-8")
    _write_json(CHARTS / f"{case_id}.offsets.json", offsets)
    multi = detect_multiple_members(text)  # A12: flag potential multi-member documents

    # Build the case (the "identified measures and the gap in care").
    year = (pack.get("source") or {}).get("measurement_year")
    assigned = request.form.getlist("measure")
    measure_state = {}
    for mid in assigned:
        measure_state[mid] = {
            "admin_status": request.form.get(f"status_{mid}", "open"),
            "admin_exclusions_applied": [],
            "last_dos": request.form.get(f"dos_{mid}") or None,
        }
    case = {
        "id": case_id,
        "created_at": _now(),
        "workflow": request.form.get("workflow", "chase"),
        "measurement_year": year,
        "pack_year": year,
        "chart_filename": fname,
        "document_id": document_id,
        "source_filename": f"{case_id}__{fname}",
        "multi_patient": multi,
        "member": {
            "id": request.form.get("member_id") or f"M-{case_id[:6]}",
            "name": request.form.get("member_name", "").strip(),
            "dob": request.form.get("member_dob") or None,
            "age": int(request.form["member_age"]) if request.form.get("member_age") else None,
            "sex": request.form.get("member_sex") or None,
        },
        "assigned_measures": assigned,
        "measure_state": measure_state,
    }
    _write_json(CASES / f"{case_id}.json", case)
    return redirect(url_for("case_view", case_id=case_id))


# --- Patient overview ------------------------------------------------------
@app.route("/case/<case_id>")
def case_view(case_id: str):
    case = get_case(case_id)
    if not case:
        abort(404)
    pack = get_pack(case.get("pack_year"))
    pack_measures = {m["measure_id"]: m for m in (pack.get("measures") if pack else [])}
    rows = []
    for mid in case.get("assigned_measures", []):
        fp = findings_path(case_id, mid)
        findings = _read_json(fp) if fp.exists() else None
        rows.append({
            "measure_id": mid,
            "measure": pack_measures.get(mid, {"measure_name": mid}),
            "state": case.get("measure_state", {}).get(mid, {}),
            "findings": findings,
        })
    return render_template("case.html", case=case, rows=rows)


@app.route("/case/<case_id>/analyze", methods=["POST"])
def case_analyze(case_id: str):
    if not can(_resolve_user(request.form.get("actor_id"))["role"], "analyze"):
        abort(403, "Running analysis requires a Reviewer, Over-reader, or Administrator (not Auditor).")
    case = get_case(case_id)
    if not case:
        abort(404)
    pack = get_pack(case.get("pack_year"))
    if not pack:
        abort(400, "Rules pack for this case is no longer loaded.")
    text, offsets = load_chart(case_id)
    if text is None:
        abort(400, "Chart text missing for this case.")

    force = request.form.get("force") == "1"
    only = request.form.get("measure")
    targets = [only] if only else list(case.get("assigned_measures", []))
    workflow = case.get("workflow", "chase")

    doc_id = case.get("document_id")
    vsd_pack = get_vsd(case.get("pack_year"))
    vsd_ver = {k: (vsd_pack.get("source") or {}).get(k) for k in ("measurement_year", "effective", "loaded_at")} \
        if vsd_pack else None
    for mid in targets:
        result = analyze(pack, mid, text, offsets, case=case,
                         workflow=workflow, force=force)
        result["case_id"] = case_id
        result["analyzed_at"] = _now()
        result["vsd_version"] = vsd_ver   # A4: VSD provenance alongside rules_version
        result["decisions"] = {}  # reviewer confirm/modify/reject audit
        # A1: bind every finding to the stable source-document ID.
        result["document_id"] = doc_id
        result["source_document"] = {"document_id": doc_id, "filename": case.get("chart_filename")}
        for e in result.get("elements", []):
            e["document_id"] = doc_id
        for x in result.get("exclusions", []):
            x["document_id"] = doc_id
        _write_json(findings_path(case_id, mid), result)

    if only:
        return redirect(url_for("review", case_id=case_id, measure_id=only))
    return redirect(url_for("case_view", case_id=case_id))


# --- Reviewer split-panel --------------------------------------------------
@app.route("/review/<case_id>/<path:measure_id>")
def review(case_id: str, measure_id: str):
    case = get_case(case_id)
    if not case:
        abort(404)
    fp = findings_path(case_id, measure_id)
    if not fp.exists():
        abort(404, "Run analysis for this measure first.")
    findings = _ensure_review(_read_json(fp))
    text, _ = load_chart(case_id)

    # Blind second read (independent double-read): show the AI proposals but NOT the first reviewer's
    # decisions or sign-off — reviewer 2 must decide independently. Their own second-read
    # decisions/result are shown so they can resume; writes go to the `second_read` slot.
    pass_ = request.args.get("pass")
    blind = pass_ == "second"
    if blind:
        import copy
        findings = copy.deepcopy(findings)
        sr = findings.get("second_read") or {}
        pm = findings.get("measure_result") or {}
        srmr = sr.get("measure_result") or {}
        findings["decisions"] = sr.get("decisions", {})
        findings["measure_result"] = {
            "proposed_status": pm.get("proposed_status"), "proposed_basis": pm.get("proposed_basis"),
            "reviewer_decision": srmr.get("reviewer_decision", "pending"),
            "final_status": srmr.get("final_status"), "decided_by": srmr.get("decided_by"),
            "decided_at": srmr.get("decided_at"), "note": srmr.get("note"),
        }
    return render_template("review.html", case=case, measure_id=measure_id,
                           findings=findings, chart_text=text or "",
                           review_pass=(pass_ or "primary"), blind=blind)


_AUDIT_ACTION = {"confirm": "finding_accepted", "modify": "finding_modified",
                 "reject": "finding_rejected"}


def _ai_baseline(f: dict, key: str):
    kind, k = key.split(":", 1) if ":" in key else ("", key)
    if kind == "el":
        return next((e.get("ai_value") for e in f.get("elements", []) if e["element_key"] == k), None)
    if kind == "ex":
        return next((x.get("rule_label") for x in f.get("exclusions", []) if x["rule_key"] == k), None)
    return None


def _review_slot(f: dict, pass_: str):
    """Return the (decisions, measure_result) slot for a review pass.

    'primary' is the first read; 'second' is the independent blind double-read, kept in
    its own `second_read` block so the two reads never overwrite each other (independent double-read)."""
    if pass_ == "second":
        sr = f.setdefault("second_read", {})
        sr.setdefault("decisions", {})
        if "measure_result" not in sr:
            proposed = (f.get("measure_result") or {}).get("proposed_status")
            sr["measure_result"] = {"proposed_status": proposed, "proposed_basis": None,
                                    "reviewer_decision": "pending", "final_status": None,
                                    "decided_by": None, "decided_at": None, "note": None}
        return sr["decisions"], sr["measure_result"], True
    return f.setdefault("decisions", {}), _ensure_review(f)["measure_result"], False


@app.route("/review/<case_id>/<path:measure_id>/decision", methods=["POST"])
def review_decision(case_id: str, measure_id: str):
    """Persist a reviewer decision (confirm / modify / reject) and append it to the audit log."""
    fp = findings_path(case_id, measure_id)
    if not fp.exists():
        abort(404)
    findings = _ensure_review(_read_json(fp))
    payload = request.get_json(force=True)
    key, action = payload.get("key"), payload.get("action")
    if not key or action not in _AUDIT_ACTION:
        abort(400)
    user = _resolve_user(payload.get("actor_id"))
    pass_ = payload.get("pass") or "primary"
    ok, why = authorize(user["role"], "blind_second_read" if pass_ == "second" else "decide_finding",
                        user["id"], _primary_actors(findings) if pass_ == "second" else None)
    if not ok:
        return _deny(why)
    final_value = payload.get("final_value")
    decisions, _mr, is_second = _review_slot(findings, pass_)
    decisions[key] = {
        "action": action, "final_value": final_value, "note": payload.get("note"),
        "by": {"id": user["id"], "name": user["name"], "role": user["role"]}, "at": _now(),
    }
    ai_val = _ai_baseline(findings, key)
    detail = (f"{ai_val} -> {final_value}" if action == "modify"
              else f"kept {ai_val}" if action == "confirm" else f"rejected {ai_val}")
    if is_second:
        detail += " (2nd read)"
    _append_audit(findings, "reviewer", _AUDIT_ACTION[action], key.split(":", 1)[-1],
                  detail, by=user, ai_value=ai_val)
    _write_json(fp, findings)
    return jsonify({"ok": True, "decisions": findings["decisions"]})


@app.route("/review/<case_id>/<path:measure_id>/escalate", methods=["POST"])
def review_escalate(case_id: str, measure_id: str):
    """A5: escalate a case×measure for review, logged with actor + server timestamp."""
    fp = findings_path(case_id, measure_id)
    if not fp.exists():
        abort(404)
    f = _ensure_review(_read_json(fp))
    payload = request.get_json(force=True)
    user = _resolve_user(payload.get("actor_id"))
    ok, why = authorize(user["role"], "escalate", user["id"])
    if not ok:
        return _deny(why)
    reason = (payload.get("reason") or "").strip() or "escalated for review"
    f.setdefault("escalations", []).append(
        {"by": {"id": user["id"], "name": user["name"], "role": user["role"]},
         "reason": reason, "at": _now()})
    _append_audit(f, "reviewer", "escalated", measure_id, reason, by=user)
    _write_json(fp, f)
    return jsonify({"ok": True, "escalations": f["escalations"]})


@app.route("/review/<case_id>/<path:measure_id>/signoff", methods=["POST"])
def review_signoff(case_id: str, measure_id: str):
    """Reviewer signs off the whole measure result (accept / reject / modify).

    Confidence gate: accepting is blocked while any low-confidence or unanchored
    proposal remains undecided — the reviewer must rule on weak AI first.
    """
    fp = findings_path(case_id, measure_id)
    if not fp.exists():
        abort(404)
    f = _ensure_review(_read_json(fp))
    payload = request.get_json(force=True)
    decision = payload.get("decision")
    if decision not in ("accepted", "rejected", "modified"):
        abort(400, "decision must be accepted/rejected/modified")
    user = _resolve_user(payload.get("actor_id"))
    pass_ = payload.get("pass") or "primary"
    ok, why = authorize(user["role"], "blind_second_read" if pass_ == "second" else "sign_off",
                        user["id"], _primary_actors(f) if pass_ == "second" else None)
    if not ok:
        return _deny(why)
    decisions, mr, is_second = _review_slot(f, pass_)

    if decision == "accepted":
        # Gate on the skill's needs_review flag plus out-of-window required elements —
        # weak or timing-suspect proposals must be ruled on before sign-off.
        blockers = []
        for e in f.get("elements", []):
            key = "el:" + e["element_key"]
            if not e.get("ai_value") or key in decisions:
                continue
            if e.get("needs_review"):
                blockers.append({"key": key, "label": e.get("element_label"),
                                 "why": "unanchored" if not e.get("evidence_anchored") else "low confidence"})
            elif e.get("required") and e.get("in_window") is False:
                blockers.append({"key": key, "label": e.get("element_label"), "why": "out of window (timing)"})
        for x in f.get("exclusions", []):
            key = "ex:" + x["rule_key"]
            if x.get("already_applied") or key in decisions:
                continue
            if x.get("needs_review"):
                blockers.append({"key": key, "label": x.get("rule_label"), "why": "exclusion needs review"})
        if blockers:
            return jsonify({"ok": False, "gate": "confidence",
                            "message": "Decide these weak or timing-suspect proposals before accepting the result.",
                            "blockers": blockers}), 409

    proposed = mr.get("proposed_status")
    if decision == "accepted":
        final_status = _ACCEPT_MAP.get(proposed, "gap_open")
    else:
        final_status = payload.get("final_status")
        if final_status not in HEDIS_FINAL:
            abort(400, f"final_status must be one of {sorted(HEDIS_FINAL)}")

    mr.update({
        "reviewer_decision": decision, "final_status": final_status,
        "decided_by": f"{user['name']} ({user['role']})", "decided_at": _now(),
        "note": payload.get("note"),
    })
    _append_audit(f, "reviewer", f"measure_result_{decision}", measure_id,
                  f"final_status={final_status}" + (" (2nd read)" if is_second else ""), by=user)
    _write_json(fp, f)
    return jsonify({"ok": True, "measure_result": mr})


# --- Broad cross-measure pass ---------------------------------------------
@app.route("/case/<case_id>/broad")
def case_broad(case_id: str):
    """One retrieved chart, every pack measure — which other open gaps it can close."""
    case = get_case(case_id)
    if not case:
        abort(404)
    pack = get_pack(case.get("pack_year"))
    text, offsets = load_chart(case_id)
    if not pack or text is None:
        abort(400, "Rules pack or chart missing for this case.")
    result = broad(pack, text, offsets, case=case, source_measure=None)
    return render_template("broad.html", case=case, result=result)


# --- QA / over-read queue, worklist & audit --------------------------------
@app.route("/queue")
def queue():
    assignee = request.args.get("assignee")   # filter by assigned user id
    state = request.args.get("state")          # filter by review state
    rows = []
    for f in all_findings():
        _ensure_review(f)
        rw = {"f": f, "state": _decision_status(f),
              "assignment": f.get("assignment"), "measure_result": f.get("measure_result")}
        if assignee and (f.get("assignment") or {}).get("assignee_id") != assignee:
            continue
        if state and rw["state"] != state:
            continue
        rows.append(rw)
    return render_template("queue.html", rows=rows,
                           filters={"assignee": assignee, "state": state})


@app.route("/queue/qa", methods=["POST"])
def queue_qa():
    """Second-reviewer over-read — Administrator role. Marks QA-passed / needs-rework."""
    payload = request.get_json(force=True)
    actor = _resolve_user(payload.get("actor_id"))
    fp = findings_path(payload["case_id"], payload["measure_id"])
    if not fp.exists():
        abort(404)
    f = _ensure_review(_read_json(fp))
    ok, why = authorize(actor["role"], "qa_over_read", actor["id"], _primary_actors(f))
    if not ok:
        return _deny(why)
    f["qa"] = {"state": payload.get("state"), "reviewer": f"{actor['name']} ({actor['role']})",
               "note": payload.get("note"), "at": _now()}
    _append_audit(f, "reviewer", "qa_over_read", payload["measure_id"],
                  f"QA {payload.get('state')}", by=actor)
    _write_json(fp, f)
    return jsonify({"ok": True, "state": f["qa"]["state"]})


@app.route("/queue/assign", methods=["POST"])
def queue_assign():
    """Assign a case×measure to a reviewer (worklist). Anyone may claim; recorded in the log."""
    payload = request.get_json(force=True)
    fp = findings_path(payload["case_id"], payload["measure_id"])
    if not fp.exists():
        abort(404)
    actor = _resolve_user(payload.get("actor_id"))
    ok, why = authorize(actor["role"], "assign", actor["id"])
    if not ok:
        return _deny(why)
    assignee = _resolve_user(payload.get("assignee_id"))
    f = _ensure_review(_read_json(fp))
    f["assignment"] = {"assignee_id": assignee["id"], "assignee_name": assignee["name"],
                       "role": assignee["role"], "assigned_by": f"{actor['name']} ({actor['role']})",
                       "at": _now()}
    _append_audit(f, "reviewer", "assigned", payload["measure_id"],
                  f"to {assignee['name']} ({assignee['role']})", by=actor)
    _write_json(fp, f)
    return jsonify({"ok": True, "assignment": f["assignment"]})


@app.route("/case/<case_id>/source")
def case_source(case_id: str):
    """A1: retrieve the unaltered original document, the system of record."""
    case = get_case(case_id)
    if not case:
        abort(404)
    fname = case.get("source_filename") or f"{case_id}__{case.get('chart_filename', '')}"
    src = CHARTS / fname
    if not src.exists():
        abort(404, "Original document not found for this case.")
    return send_file(src, as_attachment=False, download_name=case.get("chart_filename"))


@app.route("/case/<case_id>/audit")
def case_audit(case_id: str):
    """Per-case audit trail — concatenate every measure's append-only audit_log, by time."""
    case = get_case(case_id)
    if not case:
        abort(404)
    entries = []
    for mid in case.get("assigned_measures", []):
        fp = findings_path(case_id, mid)
        if fp.exists():
            for e in _read_json(fp).get("audit_log", []):
                entries.append({**e, "measure_id": mid})
    # Newest-first: a just-performed action shows at the top of the trail, not buried at
    # the bottom of a long list. Still time-ordered, just descending.
    entries.sort(key=lambda e: (e.get("ts") or "", e.get("measure_id", ""), e.get("seq", 0)),
                 reverse=True)
    return render_template("audit.html", case=case, entries=entries)


# --- Retrieval prioritization & concordance (hedis-gap-workflow skill) ------
def _priority_config() -> dict:
    p = DATA / "priority-config.json"
    if p.exists():
        return _read_json(p)
    return {"config_version": "default", "defaults": {"weight": 1.0}, "measures": {}, "scoring": {}}


def _days_to_deadline(measurement_year: str | None):
    m = re.search(r"(\d{4})", measurement_year or "")
    if not m:
        return None
    return (date(int(m.group(1)), 12, 31) - date.today()).days


def _worklist_items() -> list[dict]:
    """Build the open case×measure items the prioritizer ranks."""
    items = []
    for case in list_cases():
        cid, my = case["id"], case.get("measurement_year")
        dtd = _days_to_deadline(my)
        pack = get_pack(case.get("pack_year"))
        names = {m["measure_id"]: m.get("measure_name") for m in (pack.get("measures") if pack else [])}
        for mid in case.get("assigned_measures", []):
            st = case.get("measure_state", {}).get(mid, {})
            fp = findings_path(cid, mid)
            f = _read_json(fp) if fp.exists() else None
            summ = (f or {}).get("summary", {})
            mr = (f or {}).get("measure_result", {})
            items.append({
                "case_id": cid,
                "member_id": (case.get("member") or {}).get("id"),
                "member_name": (case.get("member") or {}).get("name"),
                "measure_id": mid,
                "measure_name": names.get(mid, mid),
                "admin_status": st.get("admin_status"),
                "analyzed": bool(f and f.get("status") not in ("skipped_admin_resolved", "validation_failed")),
                "required_missing": summ.get("required_missing"),
                "needs_review": summ.get("needs_review"),
                "days_to_deadline": dtd,
                "review_state": _decision_status(f) if f else "not analyzed",
                "signoff": mr.get("reviewer_decision") if mr else None,
            })
    return items


@app.route("/worklist")
def worklist():
    cfg = _priority_config()
    return render_template("worklist.html", result=prioritize(_worklist_items(), cfg), config=cfg)


def _double_read_pairs(records):
    """Independent blind double-read pairs: (read-1 final_status, read-2 final_status)."""
    pairs = []
    for f in records:
        mr = f.get("measure_result") or {}
        sr = (f.get("second_read") or {}).get("measure_result") or {}
        if mr.get("reviewer_decision") in ("accepted", "rejected", "modified") \
                and sr.get("reviewer_decision") in ("accepted", "rejected", "modified"):
            pairs.append({"a": mr.get("final_status"), "b": sr.get("final_status"),
                          "measure_id": f.get("measure_id"),
                          "member_id": (f.get("_member") or {}).get("id")})
    return pairs


@app.route("/analytics")
def analytics():
    records = all_findings()
    return render_template("analytics.html", report=concordance(records, gate=GATE_CONF),
                           double_read=double_read_agreement(_double_read_pairs(records)), gate=GATE_CONF)


# --- CSV export of confirmed findings --------------------------------------
_CSV_HEADER = ["member_id", "member_name", "measurement_year", "measure_id", "workflow",
               "measure_final_status", "measure_decision", "measure_decided_by",
               "valid_data_present", "recommended_next_step",
               "finding_type", "key", "label", "ai_value", "action", "final_value",
               "decided_by", "confidence", "page", "char_start", "char_end", "evidence_text",
               "reviewer_note", "decided_at", "qa_state"]


def _rows_for_export(findings_files, actions=("confirm", "modify")):
    for f in findings_files:
        if f.get("status") in ("skipped_admin_resolved", "validation_failed"):
            continue
        decisions = f.get("decisions", {})
        member = f.get("_member") or {}
        qa_state = (f.get("qa") or {}).get("state", "")
        mr = f.get("measure_result") or {}
        m_final, m_dec, m_by = mr.get("final_status"), mr.get("reviewer_decision"), mr.get("decided_by")
        sub = f.get("substantiation") or {}
        m_valid = ("" if sub.get("valid_data_present") is None else sub.get("valid_data_present"))
        m_next = sub.get("next_step")
        by_el = {"el:" + e["element_key"]: ("element", e) for e in f.get("elements", [])}
        by_ex = {"ex:" + x["rule_key"]: ("exclusion", x) for x in f.get("exclusions", [])}
        lookup = {**by_el, **by_ex}
        for key, dec in decisions.items():
            if dec.get("action") not in actions:
                continue
            kind, obj = lookup.get(key, (key.split(":")[0], {}))
            if kind == "element":
                ai_value, label = obj.get("ai_value"), obj.get("element_label")
                conf, ev = obj.get("ai_confidence"), obj.get("evidence_text")
            else:
                ai_value, label = obj.get("rule_label"), obj.get("rule_label")
                conf, ev = obj.get("ai_confidence"), obj.get("evidence_text")
            yield [
                member.get("id"), member.get("name"), f.get("measurement_year"),
                f.get("measure_id"), f.get("workflow"), m_final, m_dec, m_by,
                m_valid, m_next, kind,
                key.split(":", 1)[-1], label, ai_value, dec.get("action"),
                dec.get("final_value"), (dec.get("by") or {}).get("name"), conf,
                obj.get("page_number"), obj.get("char_start"), obj.get("char_end"),
                ev, dec.get("note"), dec.get("at"), qa_state,
            ]


def _csv_response(rows, filename):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(_CSV_HEADER)
    for r in rows:
        w.writerow(["" if c is None else c for c in r])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.route("/case/<case_id>/export.csv")
def export_case_csv(case_id: str):
    case = get_case(case_id)
    if not case:
        abort(404)
    files = []
    for mid in case.get("assigned_measures", []):
        fp = findings_path(case_id, mid)
        if fp.exists():
            f = _read_json(fp)
            f["_member"] = case.get("member", {})
            files.append(f)
    return _csv_response(_rows_for_export(files), f"confirmed_{case_id}.csv")


@app.route("/queue/export.csv")
def export_queue_csv():
    return _csv_response(_rows_for_export(all_findings()), "confirmed_findings.csv")


# --- Supplemental-data export (signed-off results; value-set names, no code selection) ---
_SUPP_HEADER = ["member_id", "last_name", "first_name", "dob", "measurement_year", "measure_id",
                "final_status", "reviewer_decision", "service_date", "confirmed_elements",
                "value_sets_referenced", "evidence_pages", "source_document",
                "reviewed_by", "decided_at", "note"]


def _supplemental_rows(findings_files):
    """One record per SIGNED-OFF measure result — the plan-side supplemental-data row.

    Honors the skill's guardrail: surfaces confirmed element values, referenced value-set
    NAMES, and evidence anchors, but never selects a diagnosis/procedure code.
    """
    for f in findings_files:
        mr = f.get("measure_result") or {}
        if mr.get("reviewer_decision", "pending") == "pending":
            continue
        member = f.get("_member") or {}
        name = (member.get("name") or "").strip()
        first, last = (name.split()[0] if name else ""), (name.split()[-1] if name else "")
        decisions = f.get("decisions", {})
        el_by = {"el:" + e["element_key"]: e for e in f.get("elements", [])}
        ex_by = {"ex:" + x["rule_key"]: x for x in f.get("exclusions", [])}
        confirmed_el, value_sets, pages, service_date = [], [], set(), None
        for key, dec in decisions.items():
            if dec.get("action") not in ("confirm", "modify"):
                continue
            if key in el_by:
                e = el_by[key]
                val = dec.get("final_value") or e.get("ai_value")
                confirmed_el.append(f"{e['element_key']}={val}")
                if e.get("page_number"):
                    pages.add(e["page_number"])
                if e.get("element_type") == "date" and not service_date:
                    service_date = val
            elif key in ex_by and ex_by[key].get("value_set_name"):
                value_sets.append(ex_by[key]["value_set_name"])
                if ex_by[key].get("page_number"):
                    pages.add(ex_by[key]["page_number"])
        yield [
            member.get("id"), last, first, member.get("dob"), f.get("measurement_year"),
            f.get("measure_id"), mr.get("final_status"), mr.get("reviewer_decision"),
            service_date or (f.get("case_context") or {}).get("last_dos"),
            "; ".join(confirmed_el), "; ".join(sorted(set(value_sets))),
            ",".join(str(p) for p in sorted(pages)), f.get("_chart"),
            mr.get("decided_by"), mr.get("decided_at"), mr.get("note"),
        ]


def _supp_response(rows, filename):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(_SUPP_HEADER)
    for r in rows:
        w.writerow(["" if c is None else c for c in r])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.route("/case/<case_id>/supplemental.csv")
def export_case_supplemental(case_id: str):
    case = get_case(case_id)
    if not case:
        abort(404)
    files = []
    for mid in case.get("assigned_measures", []):
        fp = findings_path(case_id, mid)
        if fp.exists():
            f = _read_json(fp)
            f["_member"], f["_chart"] = case.get("member", {}), case.get("chart_filename")
            files.append(f)
    return _supp_response(_supplemental_rows(files), f"supplemental_{case_id}.csv")


@app.route("/queue/supplemental.csv")
def export_queue_supplemental():
    rows = all_findings()
    case_cache = {}
    for f in rows:
        cid = f.get("case_id")
        case = case_cache.get(cid) or get_case(cid) or {}
        case_cache[cid] = case
        f["_chart"] = case.get("chart_filename")
    return _supp_response(_supplemental_rows(rows), "supplemental_data.csv")


# --- Demo reset & reseed (one in-process source of truth) ------------------
SAMPLE = BASE / "sample_charts"
_DEMO_CHARTS = {
    "grace": """RIVERSIDE INTERNAL MEDICINE — PROGRESS NOTE (provider-submitted)
Patient: Grace Whitman        DOB: 05/12/1958       MRN: M-7001      Sex: F
Date of service: 07/09/2027        Provider: T. Reyes, MD

VITALS
Blood pressure (BP) 134/82 mmHg, seated, left arm, outpatient office reading.

ASSESSMENT & PLAN
Essential hypertension, well controlled. Continue lisinopril. No hospice or palliative care.
Electronically signed by T. Reyes, MD.
""",
    "victor": """LAKESIDE CLINIC — PROGRESS NOTE
Patient: Victor Nolan        DOB: 09/03/1956       MRN: M-7002      Sex: M
Date of service: 06/22/2027        Provider: H. Park, DO

VITALS
Blood pressure (BP) 138/88 mmHg, seated, outpatient office reading.

ASSESSMENT
Essential hypertension. No evidence of ESRD or dialysis. Signed by H. Park, DO.
""",
    "priya": """VALLEY NEPHROLOGY — PROGRESS NOTE
Patient: Priya Anand        DOB: 02/20/1955       MRN: M-7003      Sex: F
Date of service: 08/14/2027        Provider: S. Iyer, MD

ASSESSMENT & PLAN
1. End stage renal disease. Patient receives hemodialysis three times weekly at the dialysis center.
2. Essential hypertension. Blood pressure (BP) 144/90 mmHg, outpatient. Signed by S. Iyer, MD.
""",
    "derek": """EASTGATE FAMILY MEDICINE — PROGRESS NOTE
Patient: Derek Cole        DOB: 11/01/1959       MRN: M-7004      Sex: M
Date of service: 05/16/2025        Provider: M. Lee, NP

VITALS
Blood pressure (BP) 130/80 mmHg recorded 05/16/2025, outpatient office reading.

ASSESSMENT
Essential hypertension. Follow-up. No hospice. Signed by M. Lee, NP.
""",
}


def _reset_demo_files():
    for p in CASES.glob("*.json"):
        if p.name != "example-case.json":
            p.unlink()
    for d, pat in ((FINDINGS, "*.json"), (CHARTS, "*")):
        for p in d.glob(pat):
            try:
                os.chmod(p, 0o644)
            except OSError:
                pass
            p.unlink()


def _demo_create_case(name, mrn, dob, age, sex, chart_text, workflow, status="gap"):
    case_id = uuid.uuid4().hex[:12]
    fname = secure_filename(name.lower().replace(" ", "_") + ".txt")
    src = CHARTS / f"{case_id}__{fname}"
    src.write_text(chart_text, encoding="utf-8")
    try:
        os.chmod(src, 0o444)
    except OSError:
        pass
    text, offsets, _ = pdf_extract.extract_text_file(str(src))
    (CHARTS / f"{case_id}.txt").write_text(text, encoding="utf-8")
    _write_json(CHARTS / f"{case_id}.offsets.json", offsets)
    year = ((get_pack(None) or {}).get("source") or {}).get("measurement_year")
    case = {
        "id": case_id, "created_at": _now(), "workflow": workflow,
        "measurement_year": year, "pack_year": year, "chart_filename": fname,
        "document_id": "doc_" + uuid.uuid4().hex[:12], "source_filename": f"{case_id}__{fname}",
        "multi_patient": detect_multiple_members(text),
        "member": {"id": mrn, "name": name, "dob": dob, "age": age, "sex": sex},
        "assigned_measures": ["CBP"],
        "measure_state": {"CBP": {"admin_status": status, "admin_exclusions_applied": [], "last_dos": None}},
    }
    _write_json(CASES / f"{case_id}.json", case)
    return case


def _demo_analyze(case):
    pack = get_pack(case.get("pack_year"))
    text, offsets = load_chart(case["id"])
    vsd_pack = get_vsd(case.get("pack_year"))
    vsd_ver = {k: (vsd_pack.get("source") or {}).get(k) for k in ("measurement_year", "effective", "loaded_at")} \
        if vsd_pack else None
    r = analyze(pack, "CBP", text, offsets, case=case, workflow=case["workflow"])
    r.update({"case_id": case["id"], "analyzed_at": _now(), "decisions": {}, "vsd_version": vsd_ver,
              "document_id": case["document_id"],
              "source_document": {"document_id": case["document_id"], "filename": case["chart_filename"]}})
    for e in r.get("elements", []):
        e["document_id"] = case["document_id"]
    for x in r.get("exclusions", []):
        x["document_id"] = case["document_id"]
    return r


def _demo_by(uid):
    u = _resolve_user(uid)
    return {"id": u["id"], "name": u["name"], "role": u["role"]}


def _demo_confirm_all(f, uid, pass_="primary"):
    user = _resolve_user(uid)
    decisions, _mr, _s = _review_slot(f, pass_)
    for e in f["elements"]:
        if e.get("ai_value"):
            decisions["el:" + e["element_key"]] = {"action": "confirm", "final_value": e["ai_value"],
                                                    "by": _demo_by(uid), "at": _now()}
            _append_audit(f, "reviewer", "finding_accepted", e["element_key"], f"kept {e['ai_value']}",
                          by=user, ai_value=e["ai_value"])
    for x in f["exclusions"]:
        if not x.get("already_applied"):
            decisions["ex:" + x["rule_key"]] = {"action": "confirm", "final_value": x.get("rule_label"),
                                                 "by": _demo_by(uid), "at": _now()}
            _append_audit(f, "reviewer", "finding_accepted", x["rule_key"], f"kept {x.get('rule_label')}",
                          by=user, ai_value=x.get("rule_label"))


def _demo_edit(f, uid, key, value):
    user = _resolve_user(uid)
    decisions, _mr, _s = _review_slot(f, "primary")
    ai = _ai_baseline(f, key)
    decisions[key] = {"action": "modify", "final_value": value, "by": _demo_by(uid), "at": _now()}
    _append_audit(f, "reviewer", "finding_modified", key.split(":", 1)[-1], f"{ai} -> {value}",
                  by=user, ai_value=ai)


def _demo_signoff(f, uid, decision, final_status=None, note=None, pass_="primary"):
    user = _resolve_user(uid)
    _dec, mr, is_second = _review_slot(f, pass_)
    fs = _ACCEPT_MAP.get(mr.get("proposed_status"), "gap_open") if decision == "accepted" else final_status
    mr.update({"reviewer_decision": decision, "final_status": fs,
               "decided_by": f"{user['name']} ({user['role']})", "decided_at": _now(), "note": note})
    _append_audit(f, "reviewer", f"measure_result_{decision}", f["measure_id"],
                  f"final_status={fs}" + (" (2nd read)" if is_second else ""), by=user)


def _demo_qa(f, uid, state):
    user = _resolve_user(uid)
    f["qa"] = {"state": state, "reviewer": f"{user['name']} ({user['role']})", "note": None, "at": _now()}
    _append_audit(f, "reviewer", "qa_over_read", f["measure_id"], f"QA {state}", by=user)


def _demo_escalate(f, uid, reason):
    user = _resolve_user(uid)
    f.setdefault("escalations", []).append({"by": _demo_by(uid), "reason": reason, "at": _now()})
    _append_audit(f, "reviewer", "escalated", f["measure_id"], reason, by=user)


def _demo_assign(f, uid, assignee_id):
    actor, a = _resolve_user(uid), _resolve_user(assignee_id)
    f["assignment"] = {"assignee_id": a["id"], "assignee_name": a["name"], "role": a["role"],
                       "assigned_by": f"{actor['name']} ({actor['role']})", "at": _now()}
    _append_audit(f, "reviewer", "assigned", f["measure_id"], f"to {a['name']} ({a['role']})", by=actor)


def reseed_demo():
    """Clear the case store and rebuild the curated demo state (in-process).

    Grace Whitman is intentionally NOT created — the presenter uploads her live
    (`sample_charts/grace_whitman.txt`) to show the full start-to-end flow.
    """
    _reset_demo_files()
    SAMPLE.mkdir(exist_ok=True)
    (SAMPLE / "grace_whitman.txt").write_text(_DEMO_CHARTS["grace"], encoding="utf-8")
    R, O, A = "u_reviewer", "u_overreader", "u_admin"
    out = []

    v = _demo_create_case("Victor Nolan", "M-7002", "1956-09-03", 70, "M", _DEMO_CHARTS["victor"], "chase")
    fv = _demo_analyze(v)
    _demo_confirm_all(fv, R)
    _demo_edit(fv, R, "el:diastolic", "90")                 # a reviewer edit (drives gate-tuning)
    _demo_signoff(fv, R, "accepted")                        # -> gap_closed
    _demo_confirm_all(fv, O, pass_="second")
    _demo_signoff(fv, O, "modified", final_status="gap_open",
                  note="2nd reviewer disagrees on control", pass_="second")
    _demo_qa(fv, O, "needs rework")
    _demo_assign(fv, A, O)
    _write_json(findings_path(v["id"], "CBP"), fv)
    out.append(("Victor Nolan", "signed off gap_closed; blind 2nd read gap_open; QA rework — double-read disagreement"))

    p = _demo_create_case("Priya Anand", "M-7003", "1955-02-20", 72, "F", _DEMO_CHARTS["priya"], "chase")
    fp = _demo_analyze(p)
    _demo_confirm_all(fp, R)
    _demo_signoff(fp, R, "modified", final_status="exclusion_applied",
                  note="Active dialysis / ESRD — exclusion applies")
    _demo_confirm_all(fp, O, pass_="second")
    _demo_signoff(fp, O, "modified", final_status="exclusion_applied", note="Concur — dialysis exclusion", pass_="second")
    _demo_qa(fp, O, "qa passed")
    _write_json(findings_path(p["id"], "CBP"), fp)
    out.append(("Priya Anand", "dialysis exclusion applied; 2nd read agrees; QA pass — double-read agreement"))

    d = _demo_create_case("Derek Cole", "M-7004", "1959-11-01", 67, "M", _DEMO_CHARTS["derek"], "chase")
    fd = _demo_analyze(d)
    _demo_escalate(fd, R, "BP reading dated 05/2025 — outside MY2027; confirm timing / request current record")
    _write_json(findings_path(d["id"], "CBP"), fd)
    out.append(("Derek Cole", "out-of-window reading; escalated"))
    return out


@app.route("/admin/reset-demo", methods=["POST"])
def admin_reset_demo():
    if not can(_resolve_user(request.form.get("actor_id"))["role"], "generate_pack"):
        abort(403, "Resetting the demo requires the Administrator role.")
    reseed_demo()
    return redirect(url_for("index"))


# --- Value Set Directory (read-only browser + admin load) ------------------
@app.route("/vsd")
def vsd_view():
    pack = get_vsd(request.args.get("year"))
    q = (request.args.get("q") or "").strip()
    results = vsd.lookup.search(pack, q) if (pack and q) else None
    return render_template("vsd.html", pack=pack, packs=list_vsd_packs(),
                           q=q, results=results, focus=request.args.get("vs"),
                           summary=(vsd.lookup.summary(pack) if pack else None))


@app.route("/vsd/upload", methods=["POST"])
def vsd_upload():
    if not can(_resolve_user(request.form.get("actor_id"))["role"], "manage_vsd"):
        abort(403, "Loading the Value Set Directory requires the Administrator role.")
    file = request.files.get("directory")
    year = (request.form.get("year") or "").strip()
    if not file or not file.filename or not year:
        abort(400, "A VSD export (.csv or .xlsx) and a measurement year are required.")
    fname = secure_filename(file.filename)
    tmp = VSD / f"_src__{fname}"
    file.save(tmp)
    try:
        rows = vsd.rows_from_xlsx(str(tmp)) if fname.lower().endswith(".xlsx") else vsd.rows_from_csv(str(tmp))
        pack = vsd.build(rows, year, directory_title=fname, loaded_at=_now()[:10])
        problems = vsd.validate(pack)
    except Exception as exc:  # noqa: BLE001
        tmp.unlink(missing_ok=True)
        abort(400, f"VSD load failed: {exc}")
    finally:
        tmp.unlink(missing_ok=True)
    out = VSD / f"value-set-pack.{secure_filename(year)}.json"
    _write_json(out, pack)
    report = problems + [f"{len(pack['value_sets'])} value sets, "
                         f"{sum(len(v['codes']) for v in pack['value_sets'].values())} codes loaded"]
    return render_template("vsd.html", pack=pack, packs=list_vsd_packs(), q="", results=None,
                           focus=None, summary=vsd.lookup.summary(pack), upload_report=report)


# --- Rules admin -----------------------------------------------------------
@app.route("/rules")
def rules():
    pack = get_pack(request.args.get("year"))
    return render_template("rules.html", pack=pack, packs=list_packs())


@app.route("/rules/upload", methods=["POST"])
def rules_upload():
    if not can(_resolve_user(request.form.get("actor_id"))["role"], "generate_pack"):
        abort(403, "Generating/replacing a rules pack requires the Administrator role.")
    if not HAS_KEY:
        abort(400, "Generating a pack from a spec PDF needs an Anthropic API key.")
    from engine.generate_pack import generate_pack

    file = request.files.get("spec")
    year = (request.form.get("year") or "").strip()
    if not file or not file.filename or not year:
        abort(400, "A spec PDF and a measurement year are required.")
    fname = secure_filename(file.filename)
    tmp = PACKS / f"_spec__{fname}"
    file.save(tmp)
    try:
        spec_text, _, _ = pdf_extract.extract_pdf(str(tmp))
        pack, val_lines = generate_pack(spec_text, year, document_title=fname)
    except Exception as exc:  # noqa: BLE001
        tmp.unlink(missing_ok=True)
        abort(400, f"Pack generation failed: {exc}")
    finally:
        tmp.unlink(missing_ok=True)

    out = PACKS / f"hedis-rules-pack.{secure_filename(year)}.json"
    _write_json(out, pack)
    return render_template("rules.html", pack=pack, packs=list_packs(),
                           upload_report=val_lines)


_migrate_cases()  # backfill document_id / source_filename on existing cases (A1)

if __name__ == "__main__":
    print(f"HEDIS app starting — Anthropic key {'loaded' if HAS_KEY else 'NOT found (offline heuristic extractor)'}.")
    app.run(host="127.0.0.1", port=5001, debug=True)
