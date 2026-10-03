# T22 장애 시험 결과

실행: 2026-10-03T13:52:05.440363+00:00 UTC
증거: `/Users/psw/Projects/decision-chat-bot/artifacts/validation/t22/20261003T134845Z`

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
{"scenario": "jev_timeout", "status": "pass", "request_id": "req_bcd23400a76f42b1b64ae422ef5cce4c", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_429", "status": "pass", "request_id": "req_a35d89582c9747d79fdfe3550db175d3", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_529", "status": "pass", "request_id": "req_ab17e46a220a40d09949718e3a9a5aa1", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_schema", "status": "pass", "request_id": "req_4d4fc0e94d0940dc8794d57a25830486", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "parser_db_outage", "status": "pass", "damaged_request": "req_b88d041289c2421789e2ecd903de7118", "recovered_request": "req_eabed93e0e5c45d0b53d406713a6b483", "http_status": 503, "unknown_validity": 1}
{"scenario": "worker_sigstop_handoff", "status": "pass", "run_id": "run_cdb32eb765574f63b646900844aa1c6e", "generations": [1, 2], "judgments": 1}
{"scenario": "worker_sigkill_recovery", "status": "pass", "run_id": "run_3d26aa42f55243ee9c6ad61ef54a24ae"}
{"scenario": "api_restart_sse", "status": "pass", "run_id": "run_56d303cee25943ec8948cbad4444fb01", "cursor_before": 1, "cursor_after": 2, "recovery_ms": 660, "startup_ms": 578, "terminal_ms": 12665, "sample_size": 1, "slo_threshold_ms": 5000}
{"scenario": "policy_during_run", "status": "pass", "versions": [1, 2, 3], "run_ids": ["run_b0d405b700734479b4209a2812b32370", "run_6aa0a7824f76418f83e75b1c008046d9", "run_b8e6e179d9a646629037bbffc9c744e6"]}
{"scenario": "parallel_review", "status": "pass", "request_id": "req_8b586d2f6a204c3ab3e3fe2668e07225", "statuses": [200, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409], "counts": {"assignments": 1, "tasks": 1, "distinct_drafts": 1}, "retry_status": 200, "stale_approval_status": 409}
{"scenario": "observation_outages", "status": "pass", "collector_alert": true, "journal_write_alert": true, "duplicate_ids": 0, "collected_before": 292, "collected_after": 292, "reconciliation": {"request_commits_missing_journal": [], "journal_success_missing_db": [], "run_commits_missing_journal": [], "run_status_mismatch": []}}
{"scenario": "information_wait", "status": "pass", "request_id": "req_4da115f3d4a34cc3aaea8670f2d9b5ed", "judgment_id": "jdg_43eba38089b14d2e867fe71007c9a103", "outputs": 11}
{"scenario": "late_recovery", "status": "pass", "request_id": "req_434bf2826b3e490d85d00cf4ce3b93b0", "first_run": "run_cbb73104368343c9bbb438eabf93e42f", "recovery_run": "run_8fdc310f568f4566af0f89971333dd3e", "failed_120s": 5, "late_recoveries": 1, "request_metrics": {"eligible_requests": 1, "within_120s": 0, "failed_120s": 1, "pending_120s": 0, "ratio": 0.0, "candidate_commits": 1, "failed_runs": 1, "late_recoveries": 1, "unconfirmed_samples": 0}, "wait_seconds": 121}
{"scenario": "process_cleanup", "status": "pass", "remaining": {}}
```

SSE 재연결 p95: 660ms / 기준 5000ms, 표본 1건. 단일 로컬 표본은 운영 성능 달성 판정으로 사용하지 않는다.
Jev 장애 주입 결과는 JEV_MODE=mock이며 실연동 품질 게이트를 대체하지 않는다.
