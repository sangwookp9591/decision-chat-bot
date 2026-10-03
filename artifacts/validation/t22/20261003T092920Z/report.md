# T22 장애 시험 결과

실행: 2026-10-03T09:32:43.705761+00:00 UTC
증거: `/Users/psw/Projects/decision-chat-bot/artifacts/validation/t22/20261003T092920Z`

| 시나리오 | 판정 | 증거 |
| --- | --- | --- |
| Jev 장애 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 파서·Neo4j 장애 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| worker 인계·재시작 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| API 재시작·SSE | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 정책 도중 변경 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 동시 승인 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 관측 장애 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 보완·120초 뒤 회복 | 실패 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |

## 기록된 실행 값

```json
{"scenario": "jev_timeout", "status": "pass", "request_id": "req_8d4042b00e1b4c33abdcf79148c8f4fd", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_429", "status": "pass", "request_id": "req_8b8b0ba7dcc9402ab46f02b01859f811", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_529", "status": "pass", "request_id": "req_9a340e189eb5417380f574646844383a", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_schema", "status": "pass", "request_id": "req_c76156615ff544d190c0cb5d20745ee8", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "parser_db_outage", "status": "pass", "damaged_request": "req_3f7bd8b817c14e8fa2971281650f72bf", "recovered_request": "req_fc40d83e553944e2a121ead165cb34b2", "http_status": 503, "unknown_validity": 1}
{"scenario": "worker_sigstop_handoff", "status": "pass", "run_id": "run_8f0f961a4fe649248925214a5c749408", "generations": [1, 2], "judgments": 1}
{"scenario": "worker_sigkill_recovery", "status": "pass", "run_id": "run_efbe712c56f446fc97ea287bb750f469"}
{"scenario": "api_restart_sse", "status": "pass", "run_id": "run_a677788ecea045528a8b672cf464e9b5", "cursor_before": 1, "cursor_after": 2, "recovery_ms": 14252, "sample_size": 1, "slo_threshold_ms": 5000}
{"scenario": "policy_during_run", "status": "pass", "versions": [1, 2, 3], "run_ids": ["run_9c68071e7e3d46018fe497da0fcb0f16", "run_371eaaf1c8c74150aaa2d14ab929072a", "run_a64d81c0fbfa4c8ba29a694fe32bb4b5"]}
{"scenario": "parallel_review", "status": "pass", "request_id": "req_6fb7739f88c041b99086aff717dec9a3", "statuses": [200, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409], "counts": {"assignments": 1, "tasks": 1, "distinct_drafts": 1}, "retry_status": 200}
{"scenario": "observation_outages", "status": "pass", "collector_alert": true, "journal_write_alert": true, "duplicate_ids": 0, "collected_before": 269, "collected_after": 269, "reconciliation": {"request_commits_missing_journal": [], "journal_success_missing_db": [], "run_commits_missing_journal": ["run_3c22a135b60243c4a3c81775162de1c8"], "run_status_mismatch": []}}
{"scenario": "information_wait", "status": "pass", "request_id": "req_110c33a5a9d34fa58a3efb38bca21165", "judgment_id": "jdg_84d1defcd85b4c6c950d5f7fe8057e75", "outputs": 11}
{"scenario": "process_cleanup", "status": "pass", "remaining": {}}
```

SSE 5초 p95 기준은 표본 1건으로 운영 달성을 판정하지 않는다.
