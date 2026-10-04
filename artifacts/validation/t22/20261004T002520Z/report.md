# T22 장애 시험 결과

실행: 2026-10-04T00:29:06.243243+00:00 UTC
증거: `/Users/psw/Projects/decision-chat-bot/artifacts/validation/t22/20261004T002520Z`

| 시나리오 | 판정 | 증거 |
| --- | --- | --- |
| Jev 장애 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 파서·Neo4j 장애 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| worker 인계·재시작 | 실패 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| API 재시작·SSE | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 정책 도중 변경 | 실패 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 동시 승인 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 관측 장애 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 보완·120초 뒤 회복 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |

## 기록된 실행 값

```json
{"scenario": "jev_timeout", "status": "pass", "request_id": "req_8f08f413f95e4efaa6a5cecaac1e299a", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_429", "status": "pass", "request_id": "req_9d4e6de26f994b308e932c3a1525f872", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_529", "status": "pass", "request_id": "req_01e3e3994fa040f2bc12a802848882f7", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_schema", "status": "pass", "request_id": "req_52b65f1f4e6d4e9ea37944cbc4e435b0", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "parser_db_outage", "status": "pass", "damaged_request": "req_c8b11f4c985c48fbb3e9e2b81e22a377", "recovered_request": "req_a758f7384d394456baa346c1ae7843f2", "http_status": 503, "unknown_validity": 1}
{"scenario": "api_restart_sse", "status": "pass", "run_id": "run_3fe85708048347589db09eff6a01a8ca", "cursor_before": 1, "cursor_after": 2, "recovery_ms": 844, "startup_ms": 788, "terminal_ms": 11829, "sample_size": 1, "slo_threshold_ms": 5000}
{"scenario": "parallel_review", "status": "pass", "request_id": "req_e40e912878d64152a9bf61135bb04861", "statuses": [200, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409], "counts": {"assignments": 1, "tasks": 1, "distinct_drafts": 1}, "retry_status": 200, "stale_approval_status": 409}
{"scenario": "observation_outages", "status": "pass", "collector_alert": true, "journal_write_alert": true, "duplicate_ids": 0, "collected_before": 269, "collected_after": 269, "reconciliation": {"request_commits_missing_journal": ["req_2ea19444a273429f8cc4f25a7fe1257f"], "journal_success_missing_db": [], "run_commits_missing_journal": [], "run_status_mismatch": []}}
{"scenario": "information_wait", "status": "pass", "request_id": "req_f112aec6df324ad4ad3f124917d7447a", "judgment_id": "jdg_796abdc356a94bb39af56bbce2ba8f11", "outputs": 11}
{"scenario": "late_recovery", "status": "pass", "request_id": "req_1399885f8899471093fe4f8c3878b63c", "first_run": "run_8f3eb34494d5447e80bb57e67ba278dc", "recovery_run": "run_67daa437e36c4f469e0e97cabd761716", "failed_120s": 7, "late_recoveries": 1, "request_metrics": {"eligible_requests": 1, "within_120s": 0, "failed_120s": 1, "pending_120s": 0, "ratio": 0.0, "candidate_commits": 1, "failed_runs": 1, "late_recoveries": 1, "unconfirmed_samples": 0}, "wait_seconds": 121}
{"scenario": "process_cleanup", "status": "pass", "remaining": {}}
```

SSE 재연결 p95: 844ms / 기준 5000ms, 표본 1건. 단일 로컬 표본은 운영 성능 달성 판정으로 사용하지 않는다.
Jev 장애 주입 결과는 JEV_MODE=mock이며 실연동 품질 게이트를 대체하지 않는다.
