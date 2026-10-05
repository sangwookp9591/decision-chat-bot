# T22 장애 시험 결과

실행: 2026-10-05T10:38:23.429957+00:00 UTC
증거: `/Users/psw/Projects/decision-chat-bot/artifacts/validation/t22/20261005T103458Z`

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
{"scenario": "jev_timeout", "status": "pass", "request_id": "req_fc65cb249d2546869fe32fb9614b1e66", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_429", "status": "pass", "request_id": "req_9c7add86f768455f948b38d3247d7b2e", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_529", "status": "pass", "request_id": "req_fd69fdc1767340f2bf84bcdbcdc9985a", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_schema", "status": "pass", "request_id": "req_6ad401add97442589f609af924a55686", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "parser_db_outage", "status": "pass", "damaged_request": "req_4b227bab3fdd420c9fdd1337d71a3bf7", "recovered_request": "req_79f5270b8b6e43179527e860cfb9e43c", "http_status": 503, "unknown_validity": 1}
{"scenario": "worker_sigstop_handoff", "status": "pass", "run_id": "run_29945516564c4942a0b399c8a651c806", "generations": [1, 2], "judgments": 1}
{"scenario": "worker_sigkill_recovery", "status": "pass", "run_id": "run_f9efcae08b0945798619108d84f3ef3a"}
{"scenario": "api_restart_sse", "status": "pass", "run_id": "run_dc5e7cccd47c4669a189b7de5db24807", "cursor_before": 1, "cursor_after": 2, "recovery_ms": 848, "startup_ms": 789, "terminal_ms": 5336, "sample_size": 1, "slo_threshold_ms": 5000}
{"scenario": "policy_during_run", "status": "pass", "versions": [1, 2, 3], "run_ids": ["run_d5773676ca8e4cd2b0a76260d84b850b", "run_78c45a9e3b7d4604885d05d5a7ac78c7", "run_14dfdc86b9a540a092f258bfcec54147"]}
{"scenario": "parallel_review", "status": "pass", "request_id": "req_e51a61f06bc749e6934a08b19cb2d682", "statuses": [200, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409], "winner_index": 0, "counts": {"assignments": 1, "tasks": 1, "distinct_drafts": 1}, "retry_status": 200, "stale_approval_status": 409}
{"scenario": "observation_outages", "status": "pass", "collector_alert": true, "journal_write_alert": true, "duplicate_ids": 0, "collected_before": 327, "collected_after": 327, "reconciliation": {"request_commits_missing_journal": [], "journal_success_missing_db": [], "run_commits_missing_journal": [], "run_status_mismatch": []}}
{"scenario": "information_wait", "status": "pass", "request_id": "req_46b0032f21684bf8872a6aa7ee542abb", "judgment_id": "jdg_833580b464404807b5babdab542c8260", "outputs": 11}
{"scenario": "late_recovery", "status": "pass", "request_id": "req_160993d7ff294c3997dba5a2b7f67557", "first_run": "run_bbf960eb35b84f0186af31e2172f98d7", "recovery_run": "run_5ce7e3aa597147c6ae9619db29ecd65f", "failed_120s": 5, "late_recoveries": 1, "request_metrics": {"eligible_requests": 1, "within_120s": 0, "failed_120s": 1, "pending_120s": 0, "ratio": 0.0, "candidate_commits": 1, "failed_runs": 1, "late_recoveries": 1, "unconfirmed_samples": 0}, "wait_seconds": 121}
{"scenario": "process_cleanup", "status": "pass", "remaining": {}}
```

SSE 재연결 p95: 848ms / 기준 5000ms, 표본 1건. 단일 로컬 표본은 운영 성능 달성 판정으로 사용하지 않는다.
Jev 장애 주입 결과는 JEV_MODE=mock이며 실연동 품질 게이트를 대체하지 않는다.
