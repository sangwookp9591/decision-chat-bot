# T22 장애 시험 결과

실행: 2026-10-03T12:51:30.663498+00:00 UTC
증거: `/Users/psw/Projects/decision-chat-bot/artifacts/validation/t22/20261003T124810Z`

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
{"scenario": "jev_timeout", "status": "pass", "request_id": "req_1f788bbf38ed45709e9a6a18e6a601fd", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_429", "status": "pass", "request_id": "req_7b7ef2ccebdf497faecfbaa62d591f5c", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_529", "status": "pass", "request_id": "req_18aadfc43b974a6b9c841316cad75b89", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "jev_schema", "status": "pass", "request_id": "req_ed445edf1b3e43e6b7973a760f1b2005", "state": "failed", "assignments": 0, "mode": "mock"}
{"scenario": "parser_db_outage", "status": "pass", "damaged_request": "req_097eafb54e1c4d9fb2e19fedbb45801d", "recovered_request": "req_4f8db7cbd08949849a3886307c495b55", "http_status": 503, "unknown_validity": 1}
{"scenario": "worker_sigstop_handoff", "status": "pass", "run_id": "run_abedf8b9daa948d4ba0b47b523d30a6e", "generations": [1, 2], "judgments": 1}
{"scenario": "worker_sigkill_recovery", "status": "pass", "run_id": "run_54c228f0cd5d4a0d863be819d83bce53"}
{"scenario": "api_restart_sse", "status": "pass", "run_id": "run_1c977449498c45609f00c46310667f18", "cursor_before": 1, "cursor_after": 2, "recovery_ms": 755, "startup_ms": 685, "terminal_ms": 12749, "sample_size": 1, "slo_threshold_ms": 5000}
{"scenario": "policy_during_run", "status": "pass", "versions": [1, 2, 3], "run_ids": ["run_18e3326d5f0342d9ae5af59b24d0ccdc", "run_589ecd75e3914df0a2025de60f8d6ce1", "run_85910fabf190429e89b041bca4719959"]}
{"scenario": "parallel_review", "status": "pass", "request_id": "req_f0c2edc007ab4ee598d3f8bb5e4c80aa", "statuses": [200, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409], "counts": {"assignments": 1, "tasks": 1, "distinct_drafts": 1}, "retry_status": 200, "stale_approval_status": 409}
{"scenario": "observation_outages", "status": "pass", "collector_alert": true, "journal_write_alert": true, "duplicate_ids": 0, "collected_before": 302, "collected_after": 302, "reconciliation": {"request_commits_missing_journal": [], "journal_success_missing_db": [], "run_commits_missing_journal": [], "run_status_mismatch": []}}
{"scenario": "information_wait", "status": "pass", "request_id": "req_5b01f46be1a54cdea6df8fa92863cfc0", "judgment_id": "jdg_0bd4b35c72714fbf84736094a7e01540", "outputs": 11}
{"scenario": "late_recovery", "status": "pass", "request_id": "req_7385a1c022a34745a048abfdfa4c8094", "first_run": "run_ef29d589d150472fa8d99ca95d8930da", "recovery_run": "run_8cef49244a664b9cad3dfad99ceaf1db", "failed_120s": 5, "late_recoveries": 1, "request_metrics": {"eligible_requests": 1, "within_120s": 0, "failed_120s": 1, "pending_120s": 0, "ratio": 0.0, "candidate_commits": 1, "failed_runs": 1, "late_recoveries": 1, "unconfirmed_samples": 0}, "wait_seconds": 121}
{"scenario": "process_cleanup", "status": "pass", "remaining": {}}
```

SSE 재연결 p95: 755ms / 기준 5000ms, 표본 1건. 단일 로컬 표본은 운영 성능 달성 판정으로 사용하지 않는다.
Jev 장애 주입 결과는 JEV_MODE=mock이며 실연동 품질 게이트를 대체하지 않는다.
