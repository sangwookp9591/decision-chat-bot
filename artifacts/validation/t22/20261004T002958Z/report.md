# T22 장애 시험 결과

실행: 2026-10-04T00:30:37.686509+00:00 UTC
증거: `/Users/psw/Projects/decision-chat-bot/artifacts/validation/t22/20261004T002958Z`

| 시나리오 | 판정 | 증거 |
| --- | --- | --- |
| Jev 장애 | 미검증 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 파서·Neo4j 장애 | 미검증 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| worker 인계·재시작 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| API 재시작·SSE | 미검증 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 정책 도중 변경 | 통과 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 동시 승인 | 미검증 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 관측 장애 | 미검증 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |
| 보완·120초 뒤 회복 | 미검증 | `pytest.log`, `junit.xml`, `scenarios.jsonl` |

## 기록된 실행 값

```json
{"scenario": "worker_sigstop_handoff", "status": "pass", "run_id": "run_d302463a26e3443b8e53ff9dc746c44e", "generations": [1, 2], "judgments": 1}
{"scenario": "worker_sigkill_recovery", "status": "pass", "run_id": "run_e3b92ffe4cd64faab9b03c11ff6f1a0a"}
{"scenario": "policy_during_run", "status": "pass", "versions": [1, 2, 3], "run_ids": ["run_ffa4367aa1af4f5fb95d591a4b338dcd", "run_4f5b7cb588594d308ad4e141be5e8436", "run_5dc5f0231f724b27a367ee5c8e45c273"]}
{"scenario": "process_cleanup", "status": "pass", "remaining": {}}
```

SSE 재연결 p95: 미검증.
Jev 장애 주입 결과는 JEV_MODE=mock이며 실연동 품질 게이트를 대체하지 않는다.
