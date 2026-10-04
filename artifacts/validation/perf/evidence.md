# PERF-3: evidence linking

Measured 2026-10-04 with live Jev. No `final.jsonl` samples were used. The quality comparison used the first 20 records in `eval/candidates/tuning.jsonl`, split into two source units at the first sentence boundary. Each record used its proposed classification labels as fixed decisions, so all candidates evaluated the same 80 decision–record pairs and 160 decision–unit pairs. The baseline and candidates ran sequentially by record against the same model. Evidence content and submitted text are omitted from this report.

## Cause and reproduction

The original `link_evidence` sent one synchronous Jev Noul request for every selected unit and each of four decisions. At the policy maximum this is 12 × 4 = 48 serial requests. Each request repeats the unit and a roughly 210-character question. One instrumented two-unit live example made 8 calls, 3,016 input tokens and 184 output tokens in total, with 8 attempts (no retries). State payloads were 97–161 characters and question payloads 210–214 characters in that example. `JevClient` retries only rate limit, overload and timeout classes; the 20-case comparisons below completed without observed retries in the recorded candidate calls. The baseline [PERF-1 trace](after.md) measured evidence-linking p50 943 ms and p95 1,039 ms for one-unit requests; the two-unit tuning baseline here took p50 1,852.5 ms and p95 2,110 ms.

Before implementation, `test_evidence_questions_are_batched_per_source_unit` failed with 8 calls versus its expected 2. The per-unit batch candidate was then implemented and passed that test. The quality comparison rejected it, so the test and implementation were replaced by `test_evidence_questions_run_concurrently_and_keep_source_order`. That test failed against the batch implementation with 2 calls versus its expected 8, then passed after the parallel change; it also proves overlapping calls and stable source order.

## Candidate comparison

Jaccard is the mean per-decision overlap of selected unit IDs with the serial baseline; both-empty sets score 1. “No evidence” counts empty decision sets out of 80. “Evidence review proxy” counts records with at least one empty decision set out of 20. The actual automatic-assignment review gate checks `evidence_complete` from presence of input units, not the selected evidence links; with fixed classification and policy, the evidence change cannot alter that gate's review outcome.

| Candidate | Two-unit latency p50 / p95 (ms) | Mean Jaccard | No evidence | Evidence review proxy | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| Serial original | 1,852.5 / 2,110 | reference | 29/80 | 20/20 | Baseline |
| Four decisions batched per unit | 462 / 528 | 0.869 | 27/80 | 18/20 | Rejected: two review-proxy transitions and lower overlap |
| Same questions and state, four parallel calls | 686 / 1,209 | 0.981 | 29/80 | 20/20 | Adopted |
| Shorter question text, serial calls | 1,811.5 / 2,169 | 0.850 | 22/80 | 19/20 | Rejected: altered evidence and review proxy |
| Two-unit lexical prefilter, top 1 per decision | no Jev timing run | 0.506 projected from baseline sets | 66/80 projected | 20/20 | Rejected: large evidence loss |
| Tenant-scoped text-hash cache | no live timing run | unchanged for cache hits | unchanged for cache hits | unchanged for cache hits | Deferred: 0 repeated texts among the 20 tuning inputs; no observed hit benefit |

The lexical projection ranked each unit by character-bigram overlap with the decision key/value, then intersected that single unit with the observed baseline evidence. It did not issue Jev calls for excluded units. Its quality loss is already decisive, so no top-1 implementation was added. Top-2 on this two-unit set performs no reduction and would need a larger representative corpus before choosing `k`. The parallel candidate retains the original request body, question text and threshold; the remaining 0.019 average Jaccard difference is consistent with observed nondeterminism from repeating live model calls, not a changed prompt. The same 20 records had no change in empty sets or evidence review proxy.

## Live end-to-end result

After implementation, 20 sequential live text requests were created with unique keys, then directly claimed with `Worker.process_job` using a dedicated benchmark tenant. All 20 reached `judgment_saved`. Timings use `Request.first_received_at`, the final Judgment commit timestamp and the `근거 연결` RunStep timestamps from Neo4j. The benchmark tenant was removed afterward.

| Metric | p50 (ms) | p95 (ms, nearest rank) | Range (ms) |
| --- | ---: | ---: | ---: |
| Receipt → final Judgment | 951.5 | 1,248 | 882–1,739 |
| Evidence linking RunStep | 514.5 | 628 | 475–1,256 |

The earlier [PERF-1 after](after.md) 20-run sample reported receipt→final 1,391/1,586 ms and evidence 943/1,039 ms (p50/p95). Those runs used the same direct worker topology but may differ in prompt and external-service conditions, so the comparison is directional. The direct-claim setup excludes idle queue polling and Redis notification delay. Four concurrent Jev calls also raise instantaneous Jev request concurrency per judgment, which may matter under service rate limits.

Verification: focused judgment/progressive tests passed (20 passed), including the previously failing concurrency test. Full backend `pytest -q`: 444 passed, 1 skipped. `ruff check jevtriage tests`: passed with zero findings.
