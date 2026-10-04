# Evaluation label workflow

Frozen tuning and final samples are read from `eval/candidates/*.jsonl`; source candidate files remain unchanged. `labeler` and `reviewer` roles pass the `eval_label` action. Label decisions are append-only `EvalLabel` nodes, each paired with an `AuditEvent`, so independent reviewers can be compared without overwriting prior decisions.

The evaluation API suppresses model output fields for final samples. A sample with multiple distinct labels is marked `consensus_required`. The export command writes confirmed rows to `eval/candidates/confirmed.jsonl` and refreshes the confirmed artifact hash and count in the manifest. The runner prefers those confirmed labels and continues to report unconfirmed rows as provisional. Final samples remain segregated from tuning.
