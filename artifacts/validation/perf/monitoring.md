# Monitoring API latency, 2026-10-04

## Data and method

- Shared `.data/metrics/metrics.db`: 33,521,664 bytes, 49,730 `events` rows at measurement. The largest kinds were `sse_deliver` (18,007), `api_boundary_received` (13,157), and `api_boundary_completed` (13,157). Tenant `t-alpha` had 22,360 explicitly attributed events; 26,316 lacked a tenant ID.
- Six calls per API, in the backend process with `DATA_DIR` set to the absolute shared `.data` path, operator tenant `t-alpha`, default filters. Wall time includes SQLite decoding, Python aggregation, Neo4j, and alert file reading but excludes HTTP transport and browser rendering. p95 is the highest of six samples (nearest rank). Shared Neo4j and concurrent tests can cause variance.
- Before: the prechange `_rows` implementation was replayed against the same data, including its range query and scoping logic. Summary then ran the current calculations and Neo4j calls; its journal work was precompleted to reproduce the old sequential ordering. After cold: the snapshot cache was cleared before **each** call. After warm: sequential calls reused the snapshot. This is a process benchmark, not a browser timing.

| API | Before p50 / p95 ms | After cold p50 / p95 ms | After warm p50 / p95 ms |
| --- | ---: | ---: | ---: |
| summary | 524 / 676 | 485 / 517 | 153 / 167 |
| slo | 544 / 582 | 540 / 564 | 133 / 249 |
| failures | 488 / 501 | 493 / 522 | 82 / 88 |
| alerts | 0.3 / 2.6 | 0.3 / 0.9 | 0.3 / 0.3 |

All measured cold calls met the 1-second target at this data size. The main gain is in the common first-page group: summary, SLO, and failures reuse one completed or in-flight SQLite read. The first member still pays the full read and aggregate cost. The separate WebKit 7.8–8.8 second first-page observation includes client behavior and transport, so this process benchmark does not claim to reproduce that latency.

## Query plans and dependencies

- Before the change, `EXPLAIN QUERY PLAN` for `events_between` showed `SEARCH events USING INDEX events_ts (ts>? AND ts<?)` followed by a temporary B-tree for the last sort term. The same query after the new index shows `MULTI-INDEX OR`, two `SEARCH events USING INDEX events_tenant_ts (<expr>=? AND ts>? AND ts<?)` branches, and a temporary B-tree for ordering. The query fetched 48,676 rows for `t-alpha` plus unattributed events in the measured broad window. The index helps selective tenant/time windows; broad history still has to read most of the database.
- Standalone Neo4j `business_counts` calls measured 89, 42, and 39 ms; `review_wait` measured 7, 5, and 6 ms. `SHOW INDEXES` confirmed `request_tenant_created`, `review_tenant_status`, `review_tenant_request_status`, and `assignment_request_unique` were ONLINE. No schema change was needed.
- The collector remains the source of truth. The cache is process local, keyed by event loop, data directory, and tenant, with a five-second lifetime. It stores raw events, so each endpoint retains its own time window, filters, SLO denominator, and legacy SSE attribution rules. A failed fetch is evicted and can be retried.

## Reproduction and validation

- Added `test_monitoring_rows_share_one_snapshot_for_concurrent_windows` and `test_metrics_store_has_tenant_time_index`; both failed before the fix (two reads instead of one, missing index), then passed. Added tenant isolation, expiry, and windowed legacy SSE attribution tests after the fix. Existing collector and SLO samples still pass.
- `cd backend && .venv/bin/pytest -q`: 457 passed, 1 skipped in the final full run. `ruff check jevtriage tests` and `lint-imports` passed.
- No rollup table was added: retaining raw events in a short shared snapshot preserves the existing per-attempt SLO and 120-second judgment calculations without a second aggregation representation.
