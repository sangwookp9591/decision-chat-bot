# T22 장애 시험 결과

실행: 2026-10-03T09:33:58.794189+00:00 UTC
증거: `/Users/psw/Projects/decision-chat-bot/artifacts/validation/t22/20261003T093317Z`

| 시나리오 | 판정 | 증거 |
| --- | --- | --- |
| Jev 장애 | 미검증 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 파서·Neo4j 장애 | 미검증 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| worker 인계·재시작 | 미검증 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| API 재시작·SSE | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 정책 도중 변경 | 미검증 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 동시 승인 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 관측 장애 | 미검증 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 보완·120초 뒤 회복 | 미검증 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |

## 기록된 실행 값

```json
{"scenario": "api_restart_sse", "status": "pass", "run_id": "run_02b515efdac24742bbe06021f87131bc", "cursor_before": 1, "cursor_after": 2, "recovery_ms": 17426, "sample_size": 1, "slo_threshold_ms": 5000}
{"scenario": "parallel_review", "status": "pass", "request_id": "req_39f36957d64c42f38bc36da312aacc8a", "statuses": [200, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409, 409], "counts": {"assignments": 1, "tasks": 1, "distinct_drafts": 1}, "retry_status": 200, "stale_approval_status": 409}
{"scenario": "process_cleanup", "status": "pass", "remaining": {}}
```

SSE 5초 p95 기준은 표본 1건으로 운영 달성을 판정하지 않는다.
