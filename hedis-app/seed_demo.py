#!/usr/bin/env python3
"""Seed the app into the known, story-ready demo state used by DEMO.md.

This is a thin CLI over the app's in-process `reseed_demo()` — the SAME routine the
Administrator's "Reset & reseed demo" button calls — so there is one source of truth.
No running server is required.

    ../.venv/bin/python seed_demo.py            # reseed (always clears first)
    ../.venv/bin/python seed_demo.py --reset    # explicit; identical behaviour

It rebuilds three members at distinct stages and leaves Grace Whitman for the presenter
to upload live (sample_charts/grace_whitman.txt):

  * Victor Nolan  — signed off gap-closed; blind 2nd read gap-open; QA rework (double-read disagreement)
  * Priya Anand   — dialysis exclusion applied; 2nd read agrees; QA passed (double-read agreement)
  * Derek Cole    — out-of-window reading; escalated
"""
from __future__ import annotations

import argparse
import sys

import app  # importing runs no server; just loads storage + the reseed routine


def main():
    ap = argparse.ArgumentParser(description="Reseed the curated demo state (in-process).")
    ap.add_argument("--reset", action="store_true",
                    help="explicit no-op flag; reseed always clears cases/findings/charts first")
    ap.parse_args()

    print("Reseeding demo state (clears cases/findings/charts; keeps packs / VSD / priority-config)…")
    results = app.reseed_demo()
    print("  Grace Whitman   (NOT seeded — upload sample_charts/grace_whitman.txt LIVE in Act 1)")
    for name, note in results:
        print(f"  {name:<15} {note}")
    print("\nDone. Start the server (python app.py) and follow DEMO.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
