# T22 장애 시험 결과

실행: 2026-10-04T00:50:29.913720+00:00 UTC
증거: `/Users/psw/Projects/decision-chat-bot/artifacts/validation/t22/20261004T004711Z`

| 시나리오 | 판정 | 증거 |
| --- | --- | --- |
| Jev 장애 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 파서·Neo4j 장애 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| worker 인계·재시작 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| API 재시작·SSE | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 정책 도중 변경 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 동시 승인 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 관측 장애 | 실패 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 보완·120초 뒤 회복 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |

## 기록된 실행 값

```json
{"scenario": "jev_timeout", "status": "pass", "request_id": "req_bb118f3951774b3ea9c5848c656a30cb", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_429", "status": "pass", "request_id": "req_98838469e1c44b8ea970456811faf52a", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_529", "status": "pass", "request_id": "req_297328a72c8144a79a3b4ae54464c08c", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_schema", "status": "pass", "request_id": "req_b9fff64dec134bbc8526e26cf8f00be7", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "parser_db_outage", "status": "pass", "damaged_request": "req_5f7a8df9b6c8435bb1792a8d61f91c89", "recovered_request": "req_916da9ea560849ed81f7ac53c72aeaac", "http_status": 503, "unknown_validity": 1}
{"scenario": "worker_sigstop_handoff", "status": "pass", "run_id": "run_429aed0d5b754010a5ee11199255c171", "generations": [1, 2], "judgments": 1}
{"scenario": "worker_sigkill_recovery", "status": "pass", "run_id": "run_c36d946ab4774cee95383bba86784b3e"}
{"scenario": "api_restart_sse", "status": "pass", "run_id": "run_91f5f68c90b74500874fdbfc5dfa20af", "cursor_before": 1, "cursor_after": 2, "recovery_ms": 752, "startup_ms": 683, "terminal_ms": 10648, "sample_size": 1, "slo_threshold_ms": 5000}
{"scenario": "policy_during_run", "status": "pass", "versions": [1, 2, 3], "run_ids": ["run_19f75b98818c4cec9123cf3220ecfa85", "run_1e5c25d9761740a89d0310569a110534", "run_c2a36ba1d99c4c62aceb337f5e5f4d64"]}
{"scenario": "parallel_review", "status": "pass", "request_id": "req_4801a9a2c74c40ee8ca39e8de6f5221e", "statuses": [200, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409], "counts": {"assignments": 1, "tasks": 1, "distinct_drafts": 1}, "retry_status": 200, "stale_approval_status": 409}
{"scenario": "information_wait", "status": "pass", "request_id": "req_1be5ff640c11415d832699382d908331", "judgment_id": "jdg_e08a17cbd6f846ac90d1100fcfb2d356", "outputs": 11}
{"scenario": "late_recovery", "status": "pass", "request_id": "req_4c9cd2f6899e4921801902162f755eb0", "first_run": "run_449c72ef6dab4b40913521ace5edaae1", "recovery_run": "run_bedf6c3db8c841ef9898a50129c90be8", "failed_120s": 6, "late_recoveries": 1, "request_metrics": {"eligible_requests": 1, "within_120s": 0, "failed_120s": 1, "pending_120s": 0, "ratio": 0.0, "candidate_commits": 1, "failed_runs": 1, "late_recoveries": 1, "unconfirmed_samples": 0}, "wait_seconds": 121}
{"scenario": "process_cleanup", "status": "pass", "remaining": {}}
```

SSE 재연결 p95: 752ms / 기준 5000ms, 표본 1건. 단일 로컬 표본은 운영 성능 달성 판정으로 사용하지 않는다.
Jev 장애 주입 결과는 JEV_MODE=mock이며 실연동 품질 게이트를 대체하지 않는다.
