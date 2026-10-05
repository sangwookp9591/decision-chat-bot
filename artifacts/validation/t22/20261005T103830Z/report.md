# T22 장애 시험 결과

실행: 2026-10-05T10:42:12.877729+00:00 UTC
증거: `/Users/psw/Projects/decision-chat-bot/artifacts/validation/t22/20261005T103830Z`

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
{"scenario": "jev_timeout", "status": "pass", "request_id": "req_b2a6b9ebb28e48bea4c65076ce8789d9", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_429", "status": "pass", "request_id": "req_aca91ca786f34e64936dc4a8bf8c9107", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_529", "status": "pass", "request_id": "req_87c90613d7e6464fb11b40103e5c905f", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_schema", "status": "pass", "request_id": "req_b614b9d85ffc49e1ac10ae1359058b6c", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "parser_db_outage", "status": "pass", "damaged_request": "req_a7f71fc41f5e4f22b35d2e79c4d416dd", "recovered_request": "req_2a218fef33af49d583c4fc1ffee51c69", "http_status": 503, "unknown_validity": 1}
{"scenario": "worker_sigstop_handoff", "status": "pass", "run_id": "run_1003f730422f460096def69cb7c55304", "generations": [1, 2], "judgments": 1}
{"scenario": "worker_sigkill_recovery", "status": "pass", "run_id": "run_598be2a99cc943e082a155bc6693175d"}
{"scenario": "api_restart_sse", "status": "pass", "run_id": "run_4e10f9b8ed684ba08ed565546c2ac207", "cursor_before": 1, "cursor_after": 2, "recovery_ms": 1090, "startup_ms": 1021, "terminal_ms": 5144, "sample_size": 1, "slo_threshold_ms": 5000}
{"scenario": "policy_during_run", "status": "pass", "versions": [1, 2, 3], "run_ids": ["run_cbbf33c7329f483895f8c778faeb7db2", "run_9647d86611cc45ff8732f251e93595e0", "run_e0d369c76fbf4576b071277d605aa432"]}
{"scenario": "parallel_review", "status": "pass", "request_id": "req_cf2fd69bb9f24146acebca29a14a83da", "statuses": [200, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409], "winner_index": 0, "counts": {"assignments": 1, "tasks": 1, "distinct_drafts": 1}, "retry_status": 200, "stale_approval_status": 409}
{"scenario": "observation_outages", "status": "pass", "collector_alert": true, "journal_write_alert": true, "duplicate_ids": 0, "collected_before": 315, "collected_after": 315, "reconciliation": {"request_commits_missing_journal": [], "journal_success_missing_db": [], "run_commits_missing_journal": [], "run_status_mismatch": []}}
{"scenario": "information_wait", "status": "pass", "request_id": "req_8622721709094c6ca093e691376accf1", "judgment_id": "jdg_1b0bb7179864422cac0bf8368bc3a227", "outputs": 11}
{"scenario": "late_recovery", "status": "pass", "request_id": "req_6bb15bce4d3143e89bc21dedd89138de", "first_run": "run_cab8b550d36747839deaecabc2dc11a5", "recovery_run": "run_018a1d063bcd4096b36e4fb386e76e02", "failed_120s": 5, "late_recoveries": 1, "request_metrics": {"eligible_requests": 1, "within_120s": 0, "failed_120s": 1, "pending_120s": 0, "ratio": 0.0, "candidate_commits": 1, "failed_runs": 1, "late_recoveries": 1, "unconfirmed_samples": 0}, "wait_seconds": 121}
{"scenario": "process_cleanup", "status": "pass", "remaining": {}}
```

SSE 재연결 p95: 1090ms / 기준 5000ms, 표본 1건. 단일 로컬 표본은 운영 성능 달성 판정으로 사용하지 않는다.
Jev 장애 주입 결과는 JEV_MODE=mock이며 실연동 품질 게이트를 대체하지 않는다.
