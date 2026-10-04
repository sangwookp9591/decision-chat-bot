# T22 장애 시험 결과

실행: 2026-10-04T00:34:23.488813+00:00 UTC
증거: `/Users/psw/Projects/decision-chat-bot/artifacts/validation/t22/20261004T003042Z`

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
{"scenario": "jev_timeout", "status": "pass", "request_id": "req_76324be7047a42dc93ed778df73f8809", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_429", "status": "pass", "request_id": "req_e42dddd7b0bb46df8f2759387f8a7ab2", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_529", "status": "pass", "request_id": "req_5d3f695fdcbb4fd2a12c701b0eb2860a", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_schema", "status": "pass", "request_id": "req_dbbdae63cd11461fa064c22d37e8ed00", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "parser_db_outage", "status": "pass", "damaged_request": "req_b575c41e0ec34586b7810f9b445135e0", "recovered_request": "req_938ab43821d241ac854a7b0fd08d5ea3", "http_status": 503, "unknown_validity": 1}
{"scenario": "api_restart_sse", "status": "pass", "run_id": "run_3e837440d02f4f939982724e12a315df", "cursor_before": 1, "cursor_after": 2, "recovery_ms": 720, "startup_ms": 672, "terminal_ms": 11417, "sample_size": 1, "slo_threshold_ms": 5000}
{"scenario": "policy_during_run", "status": "pass", "versions": [1, 2, 3], "run_ids": ["run_158009fe8c09498fa2a8cd637e7084e1", "run_115bb9bff5414c7e965bb9500c2efa67", "run_7aa693deca744e548efaaac377469d59"]}
{"scenario": "parallel_review", "status": "pass", "request_id": "req_26f9ec153a1f45ef95668994a0f98656", "statuses": [200, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409], "counts": {"assignments": 1, "tasks": 1, "distinct_drafts": 1}, "retry_status": 200, "stale_approval_status": 409}
{"scenario": "observation_outages", "status": "pass", "collector_alert": true, "journal_write_alert": true, "duplicate_ids": 0, "collected_before": 269, "collected_after": 269, "reconciliation": {"request_commits_missing_journal": ["req_369e40cd2f764109a44013c2c502d052"], "journal_success_missing_db": [], "run_commits_missing_journal": [], "run_status_mismatch": []}}
{"scenario": "information_wait", "status": "pass", "request_id": "req_5af09e99ebca4f0081e03d91b435bf67", "judgment_id": "jdg_83abec785a154ca98b6ae36746cd01d5", "outputs": 11}
{"scenario": "late_recovery", "status": "pass", "request_id": "req_bcca4d2f53a744b1b227aa0a2eb91433", "first_run": "run_f9175ec1fa2941a89f9c63b2289a0bdc", "recovery_run": "run_c10b223bc2e14b52a0070e0882eb00fc", "failed_120s": 7, "late_recoveries": 1, "request_metrics": {"eligible_requests": 1, "within_120s": 0, "failed_120s": 1, "pending_120s": 0, "ratio": 0.0, "candidate_commits": 1, "failed_runs": 1, "late_recoveries": 1, "unconfirmed_samples": 0}, "wait_seconds": 121}
{"scenario": "process_cleanup", "status": "pass", "remaining": {}}
```

SSE 재연결 p95: 720ms / 기준 5000ms, 표본 1건. 단일 로컬 표본은 운영 성능 달성 판정으로 사용하지 않는다.
Jev 장애 주입 결과는 JEV_MODE=mock이며 실연동 품질 게이트를 대체하지 않는다.
