# PERF-1 after

Measured 2026-10-04 on the final implementation with 20 sequential live Jev text requests using the same prompt as [before.md](before.md), unique idempotency keys and run IDs, tenant `perf1_after_e4e5dbe513bc489fbfd90dc752c5bcc8`. Each request was created then directly claimed by `Worker.process_job`, so these figures isolate the judgment pipeline and exclude empty-poll wait. All 20 runs reached `judgment_saved`; journal contains 20 `judgment_preliminary` records with `time_to_preliminary_ms`. Times use `Request.first_received_at` and Run commit timestamps from Neo4j.

| Receipt to | p50 (ms) | p95 (ms; nearest-rank) | min–max (ms) |
| --- | ---: | ---: | ---: |
| preliminary | 331.5 | 439 | 294–540 |
| final Judgment | 1391 | 1586 | 1218–1671 |

| RunStep | p50 (ms) | p95 (ms) |
| --- | ---: | ---: |
| input preparation | 9.5 | 15 |
| core Jev classification | 245 | 321 |
| evidence linking | 943 | 1039 |
| task decomposition | 242 | 304 |
| rules | 8 | 13 |
| eligibility | 8 | 14 |
| final save and events | 41.5 | 72 |

Evidence linking and task decomposition overlap; their durations must not be summed. Compared with the single baseline live request, the 20-run final p50 is 673 ms lower than its 2064 ms wall-clock result, but this is a directional comparison only: the baseline has n=1 and its combined `Jev 판단` step prevents per-call attribution. Preliminary visibility is new and arrives around 0.33 s at the median. Production worker arrival latency still depends on transport; no empty-poll or Redis notification latency benchmark was included in this direct-processing sample.

## Reproduction and verification

The new `test_progressive_judgment.py` failed before implementation at import with `ModuleNotFoundError: jevtriage.judgment.progress`. Its completed version proves that the preliminary snapshot and event exist while both downstream Jev calls are blocked, that those calls start concurrently, and that no formal Judgment or Assignment exists at that point. It also checks staged evidence/tasks, final classification payload, idempotent `request.received`, progress visibility, and the in-process worker wake. The original code had no preliminary fields/events and used an idle polling backoff of up to 8 s; the fallback bound is now 250 ms. Final checks: backend `pytest -q` 411 passed, 1 skipped; `ruff check jevtriage tests` passed. RT-1 owns SSE payload filtering and was asked to pass the new bounded progress fields; PERF-1 did not edit that router. Queue delay under a real Redis notification topology remains unmeasured because this benchmark called `process_job` directly.
