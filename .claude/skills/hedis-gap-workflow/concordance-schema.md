# Concordance-report output contract

Emitted by `concordance.py`. QA/process analytics on how humans acted on the AI's
proposals and how the over-read concurred — reviewer-behavior metrics, **not**
member-compliance rates.

```jsonc
{
  "ai_vs_final": {                        // per-finding confirm/modify/reject across all reviewed charts
    "decisions": 240, "agree": 198, "edited": 30, "rejected": 12,
    "agreement_rate": 0.825,             // confirm / total
    "value_change_rate": 0.125           // modify / total (the AI value was corrected)
  },
  "measure_result": {                     // the measure-level sign-off
    "signed_off": 60, "accepted": 51, "overridden": 9,
    "override_rate": 0.15
  },
  "over_read": {                          // reviewer ↔ QA over-read (sequential agreement capture)
    "qa_reviewed": 40, "concur": 36, "rework": 4,
    "concurrence_rate": 0.9
  },
  "by_measure": {                         // agreement per measure — where the AI is weak
    "CBP":  { "agree": 120, "edit": 10, "reject": 2, "agreement_rate": 0.909 },
    "BCS-E":{ "agree": 78,  "edit": 20, "reject": 10, "agreement_rate": 0.722 }
  },
  "by_element": {                         // sorted by (edit+reject) desc — prompt-tuning targets
    "diastolic": { "agree": 40, "edit": 12, "reject": 1 },
    "systolic":  { "agree": 55, "edit": 3,  "reject": 0 }
  },
  "gate_suggestion": {                    // tune the analysis skill's needs_review threshold
    "current_gate": 0.7,
    "disagreements": 42,
    "disagreement_median_confidence": 0.78,
    "high_confidence_disagreements": 27,  // edits/rejects with AI confidence > current_gate
    "recommendation": "raise",           // raise | hold
    "suggested_gate": 0.83,
    "note": "Edits/rejects cluster above the gate — raise it so more high-confidence values are reviewed."
  },
  "disclaimer": "QA/process analytics ... not a member-compliance rate."
}
```

## How to read it

- **`agreement_rate`** is the headline: how often the reviewer kept the AI value. A
  falling rate on a measure/element points at where extraction (or the pack) needs work.
- **`value_change_rate`** isolates *edits* (the AI was present but wrong) from rejects.
- **`over_read.concurrence_rate`** is a plain agreement rate (how often the QA over-read
  concurred with the first reviewer). No chance-correction coefficient is computed —
  reliability statistics such as Cohen's kappa are out of scope (X-9).
- **`gate_suggestion`** is the feedback loop into the analysis skill: disagreements
  clustering *above* the `needs_review` confidence gate mean weak-but-high-confidence
  values are slipping past review — raise the gate. It is a recommendation for a human.

## Double-read agreement (`double_read_agreement(pairs)`)

A separate function that **captures agreement** on *independent blind double-reads* — two
reviewers who each signed off the same case×measure without seeing the other (CC 3.1's
"agreement/disagreement captured"). Input is a list of pairs
`{a: final_status_1, b: final_status_2, measure_id, member_id}`; output:

```jsonc
{
  "pairs": 40,
  "agree": 36, "disagree": 4,
  "agreement_rate": 0.9,                 // exact final_status match
  "by_measure": { "CBP": {"pairs": 25, "agree": 24, "agreement_rate": 0.96}, ... },
  "disagreements": [ { "measure_id": "CBP", "read_1": "gap_closed", "read_2": "gap_open" }, ... ],
  "disclaimer": "Agreement capture on independent blind double-reads ..."
}
```

This is a **plain agreement count**, deliberately not an inter-rater-reliability statistic
(kappa and other reliability coefficients are out of scope, X-9). It is meaningful only
when the second read was blind — the application enforces the blinding (hides reviewer 1's
decisions), then supplies the paired final determinations here. Distinct from
`concordance().over_read`, which is **sequential** reviewer→QA concurrence.

## Input

A JSON array of **reviewed findings** — each is a `hedis-rules-to-findings` output
plus the application-recorded `decisions` (per-finding, with the AI baseline),
`measure_result` (the sign-off), and `qa` (the over-read). Records without decisions
contribute nothing; `skipped_admin_resolved` / `validation_failed` records are ignored.
