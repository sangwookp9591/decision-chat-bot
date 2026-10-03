# T22 장애 시험 결과

실행: 2026-10-03T09:40:26.982758+00:00 UTC
증거: `/Users/psw/Projects/decision-chat-bot/artifacts/validation/t22/20261003T094002Z`

| 시나리오 | 판정 | 증거 |
| --- | --- | --- |
| Jev 장애 | 미검증 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 파서·Neo4j 장애 | 미검증 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| worker 인계·재시작 | 미검증 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| API 재시작·SSE | 미검증 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 정책 도중 변경 | 미검증 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 동시 승인 | 미검증 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 관측 장애 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 보완·120초 뒤 회복 | 미검증 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |

## 기록된 실행 값

```json
{"scenario": "observation_outages", "status": "pass", "collector_alert": true, "journal_write_alert": true, "duplicate_ids": 0, "collected_before": 8, "collected_after": 8, "reconciliation": {"request_commits_missing_journal": [], "journal_success_missing_db": [], "run_commits_missing_journal": [], "run_status_mismatch": []}}
{"scenario": "process_cleanup", "status": "pass", "remaining": {}}
```

SSE 재연결 p95: 미검증.
Jev 장애 주입 결과는 JEV_MODE=mock이며 실연동 품질 게이트를 대체하지 않는다.
