# T22 장애 시험 결과

실행: 2026-10-03T09:24:02.791912+00:00 UTC
증거: `/Users/psw/Projects/decision-chat-bot/artifacts/validation/t22/20261003T092332Z`

| 시나리오 | 판정 | 증거 |
| --- | --- | --- |
| Jev 장애 | 미검증 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 파서·Neo4j 장애 | 미검증 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| worker 인계·재시작 | 실패 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| API 재시작·SSE | 미검증 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 정책 도중 변경 | 미검증 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 동시 승인 | 미검증 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 관측 장애 | 미검증 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 보완·120초 뒤 회복 | 미검증 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |

## 기록된 실행 값

```json
{"scenario": "worker_sigstop_handoff", "status": "pass", "run_id": "run_7a49314e35884485b8256a52135a313c", "generations": [1, 2]}
{"scenario": "process_cleanup", "status": "pass", "remaining": {}}
```

SSE 5초 p95 기준은 표본 1건으로 운영 달성을 판정하지 않는다.
