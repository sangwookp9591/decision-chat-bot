# T22 장애 시험 결과

실행: 2026-10-04T02:34:13.856081+00:00 UTC
증거: `/Users/psw/Projects/decision-chat-bot/artifacts/validation/t22/20261004T023056Z`

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
{"scenario": "jev_timeout", "status": "pass", "request_id": "req_a2efccc9b81f4cfbadfeeaa729d238a9", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_429", "status": "pass", "request_id": "req_9b61a5d321044fb8baa56cd0e001e6ba", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_529", "status": "pass", "request_id": "req_caec2d6684c74367b0fcdc6327bfabf1", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_schema", "status": "pass", "request_id": "req_2244e6e9d91b4eb9a05b83f7a5c9fabf", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "parser_db_outage", "status": "pass", "damaged_request": "req_d471522e1e9a43aeb01dc0eda619552c", "recovered_request": "req_d752fabf6e8e4154ac7fa23e43f13aed", "http_status": 503, "unknown_validity": 1}
{"scenario": "worker_sigstop_handoff", "status": "pass", "run_id": "run_fdd2d41ea5604f33894295dcaf678c81", "generations": [1, 2], "judgments": 1}
{"scenario": "worker_sigkill_recovery", "status": "pass", "run_id": "run_0ad6d250819f4e61b7d5e82c41f477c1"}
{"scenario": "api_restart_sse", "status": "pass", "run_id": "run_db5a3da9fad640dbadcdd3b14ece3f8d", "cursor_before": 1, "cursor_after": 2, "recovery_ms": 773, "startup_ms": 694, "terminal_ms": 4748, "sample_size": 1, "slo_threshold_ms": 5000}
{"scenario": "policy_during_run", "status": "pass", "versions": [1, 2, 3], "run_ids": ["run_50405f9771294a8daa3aa93011174f98", "run_e301cd49c81c433a893f51bfaabb731e", "run_8ba82903c29a4a6697ebffe84aafd01c"]}
{"scenario": "parallel_review", "status": "pass", "request_id": "req_1bb8c344e9494512bfd9663fd28960d8", "statuses": [200, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409], "counts": {"assignments": 1, "tasks": 1, "distinct_drafts": 1}, "retry_status": 200, "stale_approval_status": 409}
{"scenario": "observation_outages", "status": "pass", "collector_alert": true, "journal_write_alert": true, "duplicate_ids": 0, "collected_before": 313, "collected_after": 313, "reconciliation": {"request_commits_missing_journal": [], "journal_success_missing_db": [], "run_commits_missing_journal": [], "run_status_mismatch": []}}
{"scenario": "information_wait", "status": "pass", "request_id": "req_3494a0284c1f44ccb254a7c89d53c69e", "judgment_id": "jdg_da17203937054215964dffb8ddae2798", "outputs": 11}
{"scenario": "late_recovery", "status": "pass", "request_id": "req_005bc89a15e54f07b187111131c108e2", "first_run": "run_5afa9de09b5b453b8290ab19f4a85c0c", "recovery_run": "run_f5a1ac93a6564f7cbda21d1eecc6344f", "failed_120s": 5, "late_recoveries": 1, "request_metrics": {"eligible_requests": 1, "within_120s": 0, "failed_120s": 1, "pending_120s": 0, "ratio": 0.0, "candidate_commits": 1, "failed_runs": 1, "late_recoveries": 1, "unconfirmed_samples": 0}, "wait_seconds": 121}
{"scenario": "process_cleanup", "status": "pass", "remaining": {}}
```

SSE 재연결 p95: 773ms / 기준 5000ms, 표본 1건. 단일 로컬 표본은 운영 성능 달성 판정으로 사용하지 않는다.
Jev 장애 주입 결과는 JEV_MODE=mock이며 실연동 품질 게이트를 대체하지 않는다.
