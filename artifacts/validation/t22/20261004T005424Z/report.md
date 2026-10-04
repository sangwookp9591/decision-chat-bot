# T22 장애 시험 결과

실행: 2026-10-04T00:57:46.979666+00:00 UTC
증거: `/Users/psw/Projects/decision-chat-bot/artifacts/validation/t22/20261004T005424Z`

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
{"scenario": "jev_timeout", "status": "pass", "request_id": "req_5234bda53a454dfdbf505f79cf383f1b", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_429", "status": "pass", "request_id": "req_0078fdbf7640490a8c6179e75ed33799", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_529", "status": "pass", "request_id": "req_bd26d986b5cf4eb69551963ede989125", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_schema", "status": "pass", "request_id": "req_61aa8e6c694f49cfb0b4a09c2830a3d0", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "parser_db_outage", "status": "pass", "damaged_request": "req_508de51df8c947d6ab34291d386a52d0", "recovered_request": "req_34b87ffda361444294a1eabb8e8e295e", "http_status": 503, "unknown_validity": 1}
{"scenario": "worker_sigstop_handoff", "status": "pass", "run_id": "run_3a51c155c1064c5d8615ab44c56ad51a", "generations": [1, 2], "judgments": 1}
{"scenario": "worker_sigkill_recovery", "status": "pass", "run_id": "run_974ee095d7134137bf397f757e516e1d"}
{"scenario": "api_restart_sse", "status": "pass", "run_id": "run_78ece500f4b94a729799ff4b850d183f", "cursor_before": 1, "cursor_after": 2, "recovery_ms": 748, "startup_ms": 680, "terminal_ms": 10725, "sample_size": 1, "slo_threshold_ms": 5000}
{"scenario": "policy_during_run", "status": "pass", "versions": [1, 2, 3], "run_ids": ["run_5a379761175f423cb6d94c207a2a91d9", "run_5006d21cf85b467f93235d56c588d129", "run_3bca4c5c4a824843a9da5e6f78fe80f9"]}
{"scenario": "parallel_review", "status": "pass", "request_id": "req_c06273546a704e1bace78ef6953efb55", "statuses": [200, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409], "counts": {"assignments": 1, "tasks": 1, "distinct_drafts": 1}, "retry_status": 200, "stale_approval_status": 409}
{"scenario": "observation_outages", "status": "pass", "collector_alert": true, "journal_write_alert": true, "duplicate_ids": 0, "collected_before": 325, "collected_after": 325, "reconciliation": {"request_commits_missing_journal": [], "journal_success_missing_db": [], "run_commits_missing_journal": [], "run_status_mismatch": []}}
{"scenario": "information_wait", "status": "pass", "request_id": "req_f792312073fb454b9be341a3c39a340e", "judgment_id": "jdg_12d1dfc1c2144b3ba3e216bb99f21b66", "outputs": 11}
{"scenario": "late_recovery", "status": "pass", "request_id": "req_5dc8fc9a38144968b34b642d5bca6983", "first_run": "run_51c13365bf0c4f4ea5af088963479088", "recovery_run": "run_0a11763f39164a4cb14c571ab74a7c60", "failed_120s": 5, "late_recoveries": 1, "request_metrics": {"eligible_requests": 1, "within_120s": 0, "failed_120s": 1, "pending_120s": 0, "ratio": 0.0, "candidate_commits": 1, "failed_runs": 1, "late_recoveries": 1, "unconfirmed_samples": 0}, "wait_seconds": 121}
{"scenario": "process_cleanup", "status": "pass", "remaining": {}}
```

SSE 재연결 p95: 748ms / 기준 5000ms, 표본 1건. 단일 로컬 표본은 운영 성능 달성 판정으로 사용하지 않는다.
Jev 장애 주입 결과는 JEV_MODE=mock이며 실연동 품질 게이트를 대체하지 않는다.
