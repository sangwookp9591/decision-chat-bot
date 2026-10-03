# T22 장애 시험 결과

실행: 2026-10-03T09:39:52.137941+00:00 UTC
증거: `/Users/psw/Projects/decision-chat-bot/artifacts/validation/t22/20261003T093629Z`

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
{"scenario": "jev_timeout", "status": "pass", "request_id": "req_c8baa577060c4b179824b97ee84b97a2", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_429", "status": "pass", "request_id": "req_325be00db59249ef9f22e86ed98da225", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_529", "status": "pass", "request_id": "req_f8e185e2836942aebce95a56f174d393", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_schema", "status": "pass", "request_id": "req_81b2d5c8d5c043f98e168bcc69535376", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "parser_db_outage", "status": "pass", "damaged_request": "req_553daf29106b45509d2b5e2263c5cdbc", "recovered_request": "req_23ce4b5dfba8479594d2927fd7f8ee79", "http_status": 503, "unknown_validity": 1}
{"scenario": "worker_sigstop_handoff", "status": "pass", "run_id": "run_bc65508126f34553b20d44eeac7d299f", "generations": [1, 2], "judgments": 1}
{"scenario": "worker_sigkill_recovery", "status": "pass", "run_id": "run_f489226f7c0d4adeb143bfc5c6e4940f"}
{"scenario": "api_restart_sse", "status": "pass", "run_id": "run_8fb9f6ac62834b09b6568130d3e70eb6", "cursor_before": 1, "cursor_after": 2, "recovery_ms": 1004, "startup_ms": 695, "terminal_ms": 12364, "sample_size": 1, "slo_threshold_ms": 5000}
{"scenario": "policy_during_run", "status": "pass", "versions": [1, 2, 3], "run_ids": ["run_5d6396a672c44f728664dd35657f7eb1", "run_73100b55a3cd48a1b84d018680a775d2", "run_793182b921c7469d9e8dcc3fc8b7c6d1"]}
{"scenario": "parallel_review", "status": "pass", "request_id": "req_ff70358912de4560a826b7ebabf958ca", "statuses": [200, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409], "counts": {"assignments": 1, "tasks": 1, "distinct_drafts": 1}, "retry_status": 200, "stale_approval_status": 409}
{"scenario": "observation_outages", "status": "pass", "collector_alert": true, "journal_write_alert": true, "duplicate_ids": 0, "collected_before": 292, "collected_after": 292, "reconciliation": {"request_commits_missing_journal": [], "journal_success_missing_db": [], "run_commits_missing_journal": ["run_1e799a2a42504638a4cb75863c370881", "run_931d30d4b9ed43e3aa1106fc867f5c7e"], "run_status_mismatch": []}}
{"scenario": "information_wait", "status": "pass", "request_id": "req_dd90ed88981544c7a97e544852a187a8", "judgment_id": "jdg_6cf4f649de82498e9638694c7b3ee7d2", "outputs": 11}
{"scenario": "late_recovery", "status": "pass", "request_id": "req_71461a54f87a4956aa7b77ee748be0fc", "first_run": "run_1eae18d581fc4aca98b3f54c121091a8", "recovery_run": "run_88bbf1e3f47f4575a7fc0b30eead35a5", "failed_120s": 5, "late_recoveries": 1, "request_metrics": {"eligible_requests": 1, "within_120s": 0, "failed_120s": 1, "pending_120s": 0, "ratio": 0.0, "candidate_commits": 1, "failed_runs": 1, "late_recoveries": 1, "unconfirmed_samples": 0}, "wait_seconds": 121}
{"scenario": "process_cleanup", "status": "pass", "remaining": {}}
```

SSE 재연결 p95: 1004ms / 기준 5000ms, 표본 1건. 단일 로컬 표본은 운영 성능 달성 판정으로 사용하지 않는다.
Jev 장애 주입 결과는 JEV_MODE=mock이며 실연동 품질 게이트를 대체하지 않는다.

## 후속 대조 수정과 검증

위 실행의 관측 대조는 미처리 Run 2건을 journal 누락으로 잘못 표시했다. 종료 상태 Run만 대조하도록 수정한 후 [재시험](../20261003T094002Z/report.md)에서 `run_commits_missing_journal=[]`, 다른 누락·불일치 배열도 모두 빈 값, 중복 ID 0건을 확인했다(1 passed, 10 deselected). `docker ps --filter name=jevtriage-fault-neo4j`와 T22 tenant worker/API/collector/watchdog 대상 `ps` 조회 결과 잔여 프로세스는 없었다.
