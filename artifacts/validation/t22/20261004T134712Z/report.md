# T22 장애 시험 결과

실행: 2026-10-04T13:50:51.811968+00:00 UTC
증거: `/Users/psw/Projects/decision-chat-bot/artifacts/validation/t22/20261004T134712Z`

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
{"scenario": "jev_timeout", "status": "pass", "request_id": "req_b736742af17b41fe8c8d7aaa49bc49c3", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_429", "status": "pass", "request_id": "req_8da1fbcf06434a39922bcc008743ed40", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_529", "status": "pass", "request_id": "req_fcca8ef248e44968a3417ec695e01ee0", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_schema", "status": "pass", "request_id": "req_6ef724f7b552401bba1e162b1c2facdf", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "parser_db_outage", "status": "pass", "damaged_request": "req_d06c36a1b0cb44a8b74ff84b66b28118", "recovered_request": "req_ca4cca1afc9b49cf8bf901adfae94e8b", "http_status": 503, "unknown_validity": 1}
{"scenario": "worker_sigstop_handoff", "status": "pass", "run_id": "run_64aec36cbdf14b84b16ab63c9bcd46c3", "generations": [1, 2], "judgments": 1}
{"scenario": "worker_sigkill_recovery", "status": "pass", "run_id": "run_fd6a6e8bd68d477ebd243e822485914a"}
{"scenario": "api_restart_sse", "status": "pass", "run_id": "run_355899c34f3245748f47d86d8ae5581f", "cursor_before": 1, "cursor_after": 2, "recovery_ms": 874, "startup_ms": 810, "terminal_ms": 5195, "sample_size": 1, "slo_threshold_ms": 5000}
{"scenario": "policy_during_run", "status": "pass", "versions": [1, 2, 3], "run_ids": ["run_cea9e87d56474bb58494e4330886e11b", "run_24e02168256342f397fe24c7edb2a5cc", "run_9e40f1507c154cf79c82dc0a6258252e"]}
{"scenario": "parallel_review", "status": "pass", "request_id": "req_1ea2e57c9a504c668f951eb5f6f21deb", "statuses": [200, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409], "counts": {"assignments": 1, "tasks": 1, "distinct_drafts": 1}, "retry_status": 200, "stale_approval_status": 409}
{"scenario": "observation_outages", "status": "pass", "collector_alert": true, "journal_write_alert": true, "duplicate_ids": 0, "collected_before": 315, "collected_after": 315, "reconciliation": {"request_commits_missing_journal": [], "journal_success_missing_db": [], "run_commits_missing_journal": [], "run_status_mismatch": []}}
{"scenario": "information_wait", "status": "pass", "request_id": "req_03db4fffff0e40d788959b0260383379", "judgment_id": "jdg_533010964d82428487afe24c831b8e8f", "outputs": 11}
{"scenario": "late_recovery", "status": "pass", "request_id": "req_a54b9c786ca14834964ad4d618c1c726", "first_run": "run_003adbf4efa142e7a9aefef22e3ec765", "recovery_run": "run_f46aaa2ef08e4b95acf125755ea3dacf", "failed_120s": 5, "late_recoveries": 1, "request_metrics": {"eligible_requests": 1, "within_120s": 0, "failed_120s": 1, "pending_120s": 0, "ratio": 0.0, "candidate_commits": 1, "failed_runs": 1, "late_recoveries": 1, "unconfirmed_samples": 0}, "wait_seconds": 121}
{"scenario": "process_cleanup", "status": "pass", "remaining": {}}
```

SSE 재연결 p95: 874ms / 기준 5000ms, 표본 1건. 단일 로컬 표본은 운영 성능 달성 판정으로 사용하지 않는다.
Jev 장애 주입 결과는 JEV_MODE=mock이며 실연동 품질 게이트를 대체하지 않는다.
