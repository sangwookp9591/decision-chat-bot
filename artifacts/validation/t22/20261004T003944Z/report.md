# T22 장애 시험 결과

실행: 2026-10-04T00:43:00.347099+00:00 UTC
증거: `/Users/psw/Projects/decision-chat-bot/artifacts/validation/t22/20261004T003944Z`

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
{"scenario": "jev_timeout", "status": "pass", "request_id": "req_d80e19157a374140980a7134a1a3eb6f", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_429", "status": "pass", "request_id": "req_3ba76963eb1e4c4f92de880ef9ecbaf6", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_529", "status": "pass", "request_id": "req_093da720a66b46faa271a49045fc45ad", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_schema", "status": "pass", "request_id": "req_aa29dd299919425ca4de18c95dcd3499", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "parser_db_outage", "status": "pass", "damaged_request": "req_ad683c330a0e40d58938b36888fc215b", "recovered_request": "req_89e18be4a63a4170937a005d4541894c", "http_status": 503, "unknown_validity": 1}
{"scenario": "worker_sigstop_handoff", "status": "pass", "run_id": "run_f077aa05d2aa43bdbec112f37a1f5f35", "generations": [1, 2], "judgments": 1}
{"scenario": "worker_sigkill_recovery", "status": "pass", "run_id": "run_19231a94ea2b4ce9b51cb0a10fe7a6c3"}
{"scenario": "api_restart_sse", "status": "pass", "run_id": "run_f68d501df316421eb7ab4199939ec72b", "cursor_before": 1, "cursor_after": 2, "recovery_ms": 747, "startup_ms": 686, "terminal_ms": 10661, "sample_size": 1, "slo_threshold_ms": 5000}
{"scenario": "policy_during_run", "status": "pass", "versions": [1, 2, 3], "run_ids": ["run_780e05c87bba43c188ff7f2394c191f9", "run_85bf771addb94011ba3f0951e8295c26", "run_91be263a779f450f8d3ad58d78827eba"]}
{"scenario": "parallel_review", "status": "pass", "request_id": "req_58d2a786515d458d8918e5001fc5cb9b", "statuses": [200, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409], "counts": {"assignments": 1, "tasks": 1, "distinct_drafts": 1}, "retry_status": 200, "stale_approval_status": 409}
{"scenario": "observation_outages", "status": "pass", "collector_alert": true, "journal_write_alert": true, "duplicate_ids": 0, "collected_before": 315, "collected_after": 315, "reconciliation": {"request_commits_missing_journal": ["req_645ca76785ca4ce6889d3e99c8c54a06"], "journal_success_missing_db": [], "run_commits_missing_journal": [], "run_status_mismatch": []}}
{"scenario": "information_wait", "status": "pass", "request_id": "req_c9756f00a0c14a7da2b825fa1023d9c9", "judgment_id": "jdg_0dc634edcc23408c863c27473316be9d", "outputs": 11}
{"scenario": "late_recovery", "status": "pass", "request_id": "req_d7cfd0e9b0a2438ca3393ce6ff85bef0", "first_run": "run_de05f8f5ce864bf2ad8ce038dc1bda55", "recovery_run": "run_4354040039274d3aa9857d0515443b72", "failed_120s": 5, "late_recoveries": 1, "request_metrics": {"eligible_requests": 1, "within_120s": 0, "failed_120s": 1, "pending_120s": 0, "ratio": 0.0, "candidate_commits": 1, "failed_runs": 1, "late_recoveries": 1, "unconfirmed_samples": 0}, "wait_seconds": 121}
{"scenario": "process_cleanup", "status": "pass", "remaining": {}}
```

SSE 재연결 p95: 747ms / 기준 5000ms, 표본 1건. 단일 로컬 표본은 운영 성능 달성 판정으로 사용하지 않는다.
Jev 장애 주입 결과는 JEV_MODE=mock이며 실연동 품질 게이트를 대체하지 않는다.
