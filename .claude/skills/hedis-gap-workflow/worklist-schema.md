# Prioritized-worklist output contract

Emitted by `prioritize.py`. A ranked, explainable list of open case×measure items —
work management, never a compliance rate.

```jsonc
{
  "config_version": "1.0",
  "measurement_year": "MY2027",
  "items": [
    {
      // --- echoed from the input item (the app builds these) ---
      "member_id": "M-1029",
      "member_name": "Jane A. Doe",
      "measure_id": "CBP",
      "measure_name": "Controlling High Blood Pressure",
      "admin_status": "gap",
      "analyzed": true,
      "required_missing": 0,
      "needs_review": 0,
      "days_to_deadline": 112,
      "review_state": "unreviewed",       // optional, for display/filtering
      // --- added by prioritize.py ---
      "priority_score": 4.8,
      "rank": 1,
      "factors": {
        "measure_weight": 3.0,
        "measure_domain": "intermediate_outcome",
        "yield_bonus": 0.6,               // closable → +closable_bonus, minus needs_review penalty
        "urgency": 0.0,
        "closability": "closable"         // closable | partial | sparse | unknown
      }
    }
  ],
  "summary": { "items": 12, "measures": ["BCS-E", "CBP"], "top_score": 4.8 },
  "disclaimer": "Operational worklist prioritization ... not member compliance."
}
```

## Input item fields

The application supplies a JSON array of items. Only `measure_id` is required; the
rest default neutrally so a not-yet-analyzed gap is still rankable by measure weight.

| Field | Meaning |
|---|---|
| `measure_id` | **Required.** Keys into the priority-config for the weight. |
| `admin_status` | `gap`/`open`/`gap_closed`/`excluded`. Gap closed/excluded are dropped. |
| `analyzed` | Whether the measure has findings yet (enables the yield bonus). |
| `required_missing` | From the findings summary — drives closability. |
| `needs_review` | From the findings summary — weak proposals penalize the score. |
| `days_to_deadline` | Days to the measurement-year deadline — drives urgency. |
| any others (`member_id`, `member_name`, `review_state`, …) | Echoed through for display. |

## Notes

- **`priority_score` is relative**, for ordering only — not a percentage or a rate.
- **`factors` makes the score explainable** so a plan can tune the config with evidence.
- Ties break by `measure_id` for stable ordering.
