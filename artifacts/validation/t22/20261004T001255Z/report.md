# T22 장애 시험 결과

실행: 2026-10-04T00:16:17.441779+00:00 UTC
증거: `/Users/psw/Projects/decision-chat-bot/artifacts/validation/t22/20261004T001255Z`

| 시나리오 | 판정 | 증거 |
| --- | --- | --- |
| Jev 장애 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 파서·Neo4j 장애 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| worker 인계·재시작 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| API 재시작·SSE | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 정책 도중 변경 | 실패 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 동시 승인 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 관측 장애 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 보완·120초 뒤 회복 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |

## 기록된 실행 값

```json
{"scenario": "jev_timeout", "status": "pass", "request_id": "req_3f0f66c2022f4c2799dc4b60eb521c69", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_429", "status": "pass", "request_id": "req_d5fe6c94c2f94dcca6877d2e994a943b", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_529", "status": "pass", "request_id": "req_03d0c7e531294ab880cd953ff7704c05", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_schema", "status": "pass", "request_id": "req_8126550448814dcf997bb6797264a032", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "parser_db_outage", "status": "pass", "damaged_request": "req_05d78168e6614de9a29f109e75f7ca0e", "recovered_request": "req_7b5ecfef0ae342a3b0de8c9e52ceda4c", "http_status": 503, "unknown_validity": 1}
{"scenario": "worker_sigstop_handoff", "status": "pass", "run_id": "run_52ce5c6d033b4ce0a53e27bdcff26528", "generations": [1, 2], "judgments": 1}
{"scenario": "worker_sigkill_recovery", "status": "pass", "run_id": "run_d9d2427b354b49f9a8313bba48c9594d"}
{"scenario": "api_restart_sse", "status": "pass", "run_id": "run_cec1a2e85c9e47e980f4528c2898e6a3", "cursor_before": 1, "cursor_after": 2, "recovery_ms": 874, "startup_ms": 798, "terminal_ms": 10863, "sample_size": 1, "slo_threshold_ms": 5000}
{"scenario": "parallel_review", "status": "pass", "request_id": "req_e22e12e33cdb474c81b8c5c4e3db41ed", "statuses": [200, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409], "counts": {"assignments": 1, "tasks": 1, "distinct_drafts": 1}, "retry_status": 200, "stale_approval_status": 409}
{"scenario": "observation_outages", "status": "pass", "collector_alert": true, "journal_write_alert": true, "duplicate_ids": 0, "collected_before": 315, "collected_after": 315, "reconciliation": {"request_commits_missing_journal": [], "journal_success_missing_db": [], "run_commits_missing_journal": [], "run_status_mismatch": []}}
{"scenario": "information_wait", "status": "pass", "request_id": "req_62a4cd94da714c92a996be99ad993ee5", "judgment_id": "jdg_38e82c6dea25479381a9b23f3e48927d", "outputs": 11}
{"scenario": "late_recovery", "status": "pass", "request_id": "req_1f11c256df5e4688989413719522f8cb", "first_run": "run_f4c4efc1e33d471b9d734e6cc2e37117", "recovery_run": "run_d8e067453cfc481f8f2269f92547098c", "failed_120s": 5, "late_recoveries": 1, "request_metrics": {"eligible_requests": 1, "within_120s": 0, "failed_120s": 1, "pending_120s": 0, "ratio": 0.0, "candidate_commits": 1, "failed_runs": 1, "late_recoveries": 1, "unconfirmed_samples": 0}, "wait_seconds": 121}
{"scenario": "process_cleanup", "status": "pass", "remaining": {}}
```

SSE 재연결 p95: 874ms / 기준 5000ms, 표본 1건. 단일 로컬 표본은 운영 성능 달성 판정으로 사용하지 않는다.
Jev 장애 주입 결과는 JEV_MODE=mock이며 실연동 품질 게이트를 대체하지 않는다.
