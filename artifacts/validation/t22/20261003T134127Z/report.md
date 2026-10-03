# T22 장애 시험 결과

실행: 2026-10-03T13:44:49.319219+00:00 UTC
증거: `/Users/psw/Projects/decision-chat-bot/artifacts/validation/t22/20261003T134127Z`

| 시나리오 | 판정 | 증거 |
| --- | --- | --- |
| Jev 장애 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 파서·Neo4j 장애 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| worker 인계·재시작 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| API 재시작·SSE | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 정책 도중 변경 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 동시 승인 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 관측 장애 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 보완·120초 뒤 회복 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |

## 기록된 실행 값

```json
{"scenario": "jev_timeout", "status": "pass", "request_id": "req_c970142dc60a42e9a68908f374870c39", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_429", "status": "pass", "request_id": "req_67189916010b4db3adb5db43e8a2d253", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_529", "status": "pass", "request_id": "req_5c7430761c254983aa39ba549b2720c6", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_schema", "status": "pass", "request_id": "req_19d9cfdbf4844e819e9b5c56b5b53b94", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "parser_db_outage", "status": "pass", "damaged_request": "req_993f5a5eee8b48e982a59348e9d86793", "recovered_request": "req_ead1993ee4894ad4a845d3f991d544a3", "http_status": 503, "unknown_validity": 1}
{"scenario": "worker_sigstop_handoff", "status": "pass", "run_id": "run_85480a53302a4ac68e95702dfac4dc46", "generations": [1, 2], "judgments": 1}
{"scenario": "worker_sigkill_recovery", "status": "pass", "run_id": "run_7ba2c66c219b4048b51abb6900103e37"}
{"scenario": "api_restart_sse", "status": "pass", "run_id": "run_197fd99135224a1a8d6eca554da1c474", "cursor_before": 1, "cursor_after": 2, "recovery_ms": 780, "startup_ms": 697, "terminal_ms": 12746, "sample_size": 1, "slo_threshold_ms": 5000}
{"scenario": "policy_during_run", "status": "pass", "versions": [1, 2, 3], "run_ids": ["run_2c9891e3da6544fc83dbdb761f6fb570", "run_2d19e38707144bbd8f8e264b678cfd55", "run_07f31178dea34cdab545f1dfa28cf68b"]}
{"scenario": "parallel_review", "status": "pass", "request_id": "req_d757f9841a2e4323845f8f2c6370ad56", "statuses": [200, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409], "counts": {"assignments": 1, "tasks": 1, "distinct_drafts": 1}, "retry_status": 200, "stale_approval_status": 409}
{"scenario": "observation_outages", "status": "pass", "collector_alert": true, "journal_write_alert": true, "duplicate_ids": 0, "collected_before": 290, "collected_after": 290, "reconciliation": {"request_commits_missing_journal": [], "journal_success_missing_db": [], "run_commits_missing_journal": [], "run_status_mismatch": []}}
{"scenario": "information_wait", "status": "pass", "request_id": "req_e589c61bc83e4687b0e8f70f3f6fa0e8", "judgment_id": "jdg_2156f58893354f8bb674e3ebc8d23ac4", "outputs": 11}
{"scenario": "late_recovery", "status": "pass", "request_id": "req_e08a5088538b419b8ba1b80334269170", "first_run": "run_ea8500b32eee4117a7864f133e6694e8", "recovery_run": "run_3a823f09c1b14887b5ad6609f06df58e", "failed_120s": 5, "late_recoveries": 1, "request_metrics": {"eligible_requests": 1, "within_120s": 0, "failed_120s": 1, "pending_120s": 0, "ratio": 0.0, "candidate_commits": 1, "failed_runs": 1, "late_recoveries": 1, "unconfirmed_samples": 0}, "wait_seconds": 121}
{"scenario": "process_cleanup", "status": "pass", "remaining": {}}
```

SSE 재연결 p95: 780ms / 기준 5000ms, 표본 1건. 단일 로컬 표본은 운영 성능 달성 판정으로 사용하지 않는다.
Jev 장애 주입 결과는 JEV_MODE=mock이며 실연동 품질 게이트를 대체하지 않는다.
