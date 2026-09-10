# Priority-config contract

A small, plan-owned JSON that assigns a **priority weight** to each measure for
review triage. It is **reference data like the rules pack, but a different source of
truth**: measure weights are CMS Star-Ratings / plan policy, *not* anything in the
NCQA Volume 2 spec — so they live here, never in the rules pack.

```jsonc
{
  "config_version": "1.0",
  "source": {
    "basis": "CMS Star Ratings weighting as defaults — plan-overridable",
    "measurement_year": "MY2027",
    "updated_at": "2026-09-10",
    "disclaimer": "Operational priority weights for review triage; plan/Star policy, not an NCQA value."
  },
  "defaults": { "weight": 1.0 },          // weight for any measure not listed
  "measures": {
    "CBP":   { "weight": 3.0, "domain": "intermediate_outcome", "label": "...", "star_measure": true },
    "BCS-E": { "weight": 1.0, "domain": "process",              "label": "...", "star_measure": true }
  },
  "scoring": {                            // knobs for prioritize.py (all optional; defaults shown)
    "closable_bonus": 0.6,                // +bonus when required_missing == 0 (near-certain close)
    "partial_bonus": 0.25,               // +bonus when 0 < required_missing <= partial_missing_max
    "partial_missing_max": 2,
    "needs_review_penalty": 0.1,         // per unresolved weak finding (capped at 3)
    "urgency_window_days": 90,           // urgency starts ramping this many days before the deadline
    "urgency_per_30d": 0.5,
    "urgency_cap": 1.5
  }
}
```

## Weighting guidance (defaults)

CMS Star Ratings weight measure *types* differently; use these as sensible defaults
and let the plan override per its own contract:

| Domain | Typical Star weight | Examples |
|---|---|---|
| `intermediate_outcome` / `outcome` | 3 | Controlling High Blood Pressure (CBP), glycemic status |
| `patient_experience` | 2–4 | CAHPS-derived |
| `process` | 1 | Breast Cancer Screening (BCS-E), screenings/immunizations |

Weights are relative — only their ratio matters for ranking. A plan may raise a
measure it is behind on regardless of Star weight; that is exactly what `measures[].weight`
is for. Keep one config per measurement year (weights and measure IDs are year-scoped).

## Rules

- **Read-only policy artifact.** The app surfaces it; edits are a deliberate plan action.
- **Never conflate with the rules pack.** The rules pack says *what to look for*; this
  says *what to prioritize*. Different owners, different lifecycles.
- **Missing measures fall back to `defaults.weight`.** An unlisted measure is still
  rankable (at weight 1.0), so a new measure is never silently dropped from the worklist.
