# T22 장애 시험 결과

실행: 2026-10-04T00:39:11.062645+00:00 UTC
증거: `/Users/psw/Projects/decision-chat-bot/artifacts/validation/t22/20261004T003529Z`

| 시나리오 | 판정 | 증거 |
| --- | --- | --- |
| Jev 장애 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 파서·Neo4j 장애 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| worker 인계·재시작 | 실패 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| API 재시작·SSE | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 정책 도중 변경 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 동시 승인 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 관측 장애 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 보완·120초 뒤 회복 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |

## 기록된 실행 값

```json
{"scenario": "jev_timeout", "status": "pass", "request_id": "req_5fdbd1c93e524cd78868a5d84673d97a", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_429", "status": "pass", "request_id": "req_304f703429394ba892a08055b0921fdd", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_529", "status": "pass", "request_id": "req_929ad2d55f1546dc811d53d5114641a7", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_schema", "status": "pass", "request_id": "req_f10d9de022434129a2f315b713208278", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "parser_db_outage", "status": "pass", "damaged_request": "req_052023ae09bc4bcdab135a6decc6d4c4", "recovered_request": "req_5a99798a3b6c4b92a2924391582f6a20", "http_status": 503, "unknown_validity": 1}
{"scenario": "api_restart_sse", "status": "pass", "run_id": "run_81421e67f6904d459ea8cda3dbf713ec", "cursor_before": 1, "cursor_after": 2, "recovery_ms": 743, "startup_ms": 685, "terminal_ms": 11510, "sample_size": 1, "slo_threshold_ms": 5000}
{"scenario": "policy_during_run", "status": "pass", "versions": [1, 2, 3], "run_ids": ["run_f835807df503423aa0c3940f7d2d19d4", "run_6c27583e2b594b6bb1b4da7bcebc1af5", "run_0d12fc1e98d5416da513c233b5f87fc7"]}
{"scenario": "parallel_review", "status": "pass", "request_id": "req_5c05823a2da64778a63aad505fea2cb3", "statuses": [200, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409], "counts": {"assignments": 1, "tasks": 1, "distinct_drafts": 1}, "retry_status": 200, "stale_approval_status": 409}
{"scenario": "observation_outages", "status": "pass", "collector_alert": true, "journal_write_alert": true, "duplicate_ids": 0, "collected_before": 269, "collected_after": 269, "reconciliation": {"request_commits_missing_journal": ["req_7aae4f42609f4fd7b5e4ca2ff1294095"], "journal_success_missing_db": [], "run_commits_missing_journal": [], "run_status_mismatch": []}}
{"scenario": "information_wait", "status": "pass", "request_id": "req_ffe631ea756842b08684e4f7f17e04a5", "judgment_id": "jdg_2aad03eb9a0041c49c794512b6633e66", "outputs": 11}
{"scenario": "late_recovery", "status": "pass", "request_id": "req_1311532147614a71bf4d4f8c0e6a275b", "first_run": "run_c25f6ae8e6554123a76fc3073f2adbf6", "recovery_run": "run_36e54f6d25b44a2c9af42545a1bcd2bc", "failed_120s": 7, "late_recoveries": 1, "request_metrics": {"eligible_requests": 1, "within_120s": 0, "failed_120s": 1, "pending_120s": 0, "ratio": 0.0, "candidate_commits": 1, "failed_runs": 1, "late_recoveries": 1, "unconfirmed_samples": 0}, "wait_seconds": 121}
{"scenario": "process_cleanup", "status": "pass", "remaining": {}}
```

SSE 재연결 p95: 743ms / 기준 5000ms, 표본 1건. 단일 로컬 표본은 운영 성능 달성 판정으로 사용하지 않는다.
Jev 장애 주입 결과는 JEV_MODE=mock이며 실연동 품질 게이트를 대체하지 않는다.
