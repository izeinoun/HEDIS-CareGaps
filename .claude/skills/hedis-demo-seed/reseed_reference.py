#!/usr/bin/env python3
"""Reference reseed for the HEDIS care-gap demo — reproduce THIS app's demo state.

Not a general-purpose tool: it rebuilds the exact curated cast the runbook (DEMO.md)
follows. It is written against a small **adapter interface** so a fresh build can wire
it to its own storage/routes without depending on any particular app internals.

The host supplies an object `a` with these callables (actor ids are strings the host
resolves to users with the four roles):

    a.reset()                                              # clear cases/findings/charts
    a.write_sample_chart(name, text)                       # stage a chart for live upload
    a.create_case(name, mrn, dob, age, sex, chart_text,
                  workflow, admin_status) -> case_id       # + run intake (doc id, offsets, multi-patient)
    a.analyze(case_id)                                     # Pass-1 + Pass-2 -> findings written
    a.confirm_all(case_id, actor, pass_="primary")         # confirm every found element + fresh exclusion
    a.edit(case_id, actor, element_key, value)             # modify one element (primary pass)
    a.signoff(case_id, actor, decision,
              final_status=None, note=None, pass_="primary")
    a.qa(case_id, actor, state)                            # "qa passed" | "needs rework"
    a.escalate(case_id, actor, reason)
    a.assign(case_id, actor, assignee)

Every write must be stamped with the acting user + timestamp into the append-only audit
log (that is the app's job, per audit A3). Reviewer outcomes use the vocabulary
gap_closed / gap_open / exclusion_applied / needs_more_info — never "compliant".

Run `reseed(app_adapter)` and it returns a list of (member, note) for a summary line.
"""
from pathlib import Path

# Actor ids (host maps to the four roles: Reviewer / Over-reader / Administrator / Auditor)
R, O, A = "u_reviewer", "u_overreader", "u_admin"

_CHARTS_DIR = Path(__file__).resolve().parent / "charts"


def _chart(name):
    return (_CHARTS_DIR / name).read_text(encoding="utf-8")


def reseed(a):
    """Rebuild the curated demo state through the host adapter `a`. See module docstring."""
    a.reset()

    # Grace Whitman is NOT seeded — the presenter uploads her live (Act 1) to show the
    # full start-to-end flow. Stage her chart so the upload is one click away.
    a.write_sample_chart("grace_whitman.txt", _chart("grace_whitman.txt"))

    out = []

    # 1) Victor Nolan — primary signs off gap_closed; the blind second read disagrees
    #    (gap_open); QA flags rework. Produces the double-read DISAGREEMENT + a reviewer
    #    edit that drives the confidence-gate-tuning suggestion on Analytics.
    v = a.create_case("Victor Nolan", "M-7002", "1956-09-03", 70, "M",
                      _chart("victor_nolan.txt"), workflow="chase", admin_status="gap")
    a.analyze(v)
    a.confirm_all(v, R)
    a.edit(v, R, "diastolic", "90")                       # a high-confidence value the reviewer corrects
    a.signoff(v, R, "accepted")                           # -> gap_closed
    a.confirm_all(v, O, pass_="second")                   # independent blind read
    a.signoff(v, O, "modified", final_status="gap_open",
              note="2nd reviewer disagrees on control", pass_="second")
    a.qa(v, O, "needs rework")
    a.assign(v, A, O)                                     # Administrator assigns to the Over-reader
    out.append(("Victor Nolan", "signed off gap_closed; blind 2nd read gap_open; QA rework — double-read disagreement"))

    # 2) Priya Anand — documented dialysis/ESRD. Reviewer applies the exclusion; the
    #    blind second read AGREES; QA passes. The exclusion path + double-read agreement.
    p = a.create_case("Priya Anand", "M-7003", "1955-02-20", 72, "F",
                      _chart("priya_anand.txt"), workflow="chase", admin_status="gap")
    a.analyze(p)
    a.confirm_all(p, R)
    a.signoff(p, R, "modified", final_status="exclusion_applied",
              note="Active dialysis / ESRD — exclusion applies")
    a.confirm_all(p, O, pass_="second")
    a.signoff(p, O, "modified", final_status="exclusion_applied",
              note="Concur — dialysis exclusion", pass_="second")
    a.qa(p, O, "qa passed")
    out.append(("Priya Anand", "dialysis exclusion applied; 2nd read agrees; QA pass — double-read agreement"))

    # 3) Derek Cole — BP dated 05/2025, outside MY2027. Reviewer ESCALATES on timing;
    #    left un-signed so the escalation + out-of-window banner show live.
    d = a.create_case("Derek Cole", "M-7004", "1959-11-01", 67, "M",
                      _chart("derek_cole.txt"), workflow="chase", admin_status="gap")
    a.analyze(d)
    a.escalate(d, R, "BP reading dated 05/2025 — outside MY2027; confirm timing / request current record")
    out.append(("Derek Cole", "out-of-window reading; escalated"))

    return out
