#!/usr/bin/env python3
"""Workflow role model — the review process's roles and what each may do.

This is *policy*, not *mechanism*. It defines the domain roles the HEDIS review
workflow assumes, the action→role permission matrix, and the separation-of-duties
(SoD) rules that plain RBAC cannot express (identity-level, not role-level). A host
platform's RBAC module is *configured to satisfy this contract* — it owns users,
authentication, group→role mapping, enforcement, and user-management audit; it does
not define these domain roles. Deterministic and dependency-free.

See `workflow-roles.md` for the contract and the platform-RBAC mapping guidance.
"""
import argparse
import json
import sys

ROLES = ("reviewer", "over_reader", "administrator", "auditor")

ROLE_LABELS = {
    "reviewer": "Reviewer",
    "over_reader": "Over-reader",
    "administrator": "Administrator",
    "auditor": "Auditor",
}
ROLE_DESC = {
    "reviewer": "Abstractor — locate/confirm findings and sign off the first read.",
    "over_reader": "Independent QA over-read and blind second read; must differ from the primary signer.",
    "administrator": "Manage rules packs, priority config, and assignments; may perform all review actions.",
    "auditor": "Read-only — view findings, audit trail, and analytics; takes no actions.",
}

# action -> the set of roles permitted to perform it.
PERMISSIONS = {
    "view":                 {"reviewer", "over_reader", "administrator", "auditor"},
    "analyze":              {"reviewer", "over_reader", "administrator"},
    "decide_finding":       {"reviewer", "over_reader", "administrator"},
    "sign_off":             {"reviewer", "over_reader", "administrator"},
    "escalate":             {"reviewer", "over_reader", "administrator"},
    "blind_second_read":    {"over_reader", "administrator"},
    "qa_over_read":         {"over_reader", "administrator"},
    "assign":               {"administrator"},
    "generate_pack":        {"administrator"},
    "edit_priority_config": {"administrator"},
    "manage_vsd":           {"administrator"},   # load/replace the Value Set Directory
    "manage_users":         {"administrator"},   # platform-enforced; listed for completeness
}

# Actions that additionally require the actor to be a DIFFERENT person than whoever
# performed the primary read being checked — the review-integrity guarantee RBAC alone
# cannot make (it is role-based, not identity-relationship-based).
SEPARATION_OF_DUTIES = {"blind_second_read", "qa_over_read"}


def normalize_role(role):
    """Accept a display name ('Over-reader') or an id ('over_reader')."""
    return (role or "").strip().lower().replace("-", "_").replace(" ", "_")


def can(role, action):
    """Is `role` permitted to perform `action`?"""
    return normalize_role(role) in PERMISSIONS.get(action, set())


def requires_sod(action):
    return action in SEPARATION_OF_DUTIES


def sod_ok(actor_id, prior_actor_ids):
    """Separation of duties: the actor must not be among those who performed the primary
    read being over-read / second-read. Returns True when the actor is independent."""
    return actor_id not in set(prior_actor_ids or ())


def authorize(role, action, actor_id=None, prior_actor_ids=None):
    """One-call gate: returns (ok, reason). Enforces both the permission matrix and,
    for SoD actions, the different-person rule."""
    if not can(role, action):
        return False, f"role '{normalize_role(role)}' may not perform '{action}'"
    if requires_sod(action) and not sod_ok(actor_id, prior_actor_ids):
        return False, f"separation of duties: '{action}' must be done by a different person than the primary reviewer"
    return True, "ok"


ROLE_MODEL = {
    "roles": {r: {"label": ROLE_LABELS[r], "description": ROLE_DESC[r]} for r in ROLES},
    "permissions": {a: sorted(rs) for a, rs in PERMISSIONS.items()},
    "separation_of_duties": sorted(SEPARATION_OF_DUTIES),
    "note": ("Policy for a platform RBAC module to configure to; the platform owns users, "
             "auth, group→role mapping, and user-management audit."),
}


def main():
    ap = argparse.ArgumentParser(description="Print the workflow role model, or check one action.")
    ap.add_argument("--check", nargs=2, metavar=("ROLE", "ACTION"), help="print whether ROLE can do ACTION")
    args = ap.parse_args()
    if args.check:
        role, action = args.check
        print(json.dumps({"role": role, "action": action, "allowed": can(role, action),
                          "requires_sod": requires_sod(action)}, indent=2))
    else:
        print(json.dumps(ROLE_MODEL, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
