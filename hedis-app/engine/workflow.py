"""Thin bridge to the `hedis-gap-workflow` skill (operations layer).

Imports the skill's deterministic scripts directly — retrieval prioritization and
over-read / AI-vs-final concordance — so the app's behaviour is exactly the skill's.
The app only assembles the inputs (open items; reviewed findings) and renders the
outputs.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_SKILL_DIR = (
    Path(__file__).resolve().parents[2] / ".claude" / "skills" / "hedis-gap-workflow"
)


def _load(name):
    spec = importlib.util.spec_from_file_location(name, _SKILL_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_prioritize = _load("prioritize")
_concordance = _load("concordance")
_roles = _load("roles")

prioritize = _prioritize.prioritize
concordance = _concordance.concordance
double_read_agreement = _concordance.double_read_agreement

# Role contract (policy the app enforces until a platform RBAC takes over).
can = _roles.can
authorize = _roles.authorize
sod_ok = _roles.sod_ok
normalize_role = _roles.normalize_role
ROLE_MODEL = _roles.ROLE_MODEL
