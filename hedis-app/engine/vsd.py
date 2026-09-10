"""Bridge to the `hedis-vsd` skill — the Value Set Directory (code lists).

Loads the skill's deterministic builder + lookup helpers, and manages the app's
year-scoped value-set packs (licensed, internal). Exports the reference / code-membership
validation API the Rules screen, the reviewer, and the VSD browser consume.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_SKILL_DIR = (
    Path(__file__).resolve().parents[2] / ".claude" / "skills" / "hedis-vsd"
)


def _load(name):
    spec = importlib.util.spec_from_file_location(name, _SKILL_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_builder = _load("build_vsd_pack")
lookup = _load("vsd_lookup")

build = _builder.build
validate = _builder.validate
rows_from_csv = _builder._rows_from_csv
rows_from_xlsx = _builder._rows_from_xlsx
