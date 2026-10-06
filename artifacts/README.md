# artifacts

과거 실행 산출물(시험 결과·로그·보고서)입니다. 당시 명령과 출력 그대로 보존하므로 옛 이름이 남아 있습니다.

2026-10-06 이름 변경 이후 대응:

| 기록 속 이름 | 현재 이름 |
| --- | --- |
| Jev Triage | 일동이 |
| `jevtriage` (Python 패키지·모듈 경로) | `ildongi` |
| Jev (판단 모델 표시명) | `AI_NAME` 설정값 (기본 Decision AI) |
| `JEV_API_KEY`, `JEV_MODE`, `JEV_MOCK_*` | `AI_API_KEY`, `AI_MODE`, `AI_MOCK_*` |
| `JEVTRIAGE_*` | `ILDONGI_*` |
| `JevClient`, `jev_client.py` | `AiClient`, `ai_client.py` |
| `jev_csrf`, `jev_session` 쿠키 | `ildongi_csrf`, `ildongi_session` |
| `scripts/jev_probe.py`, `docs/architecture/JEV_CONTRACT.md` | `scripts/ai_probe.py`, `docs/architecture/AI_CONTRACT.md` |

모델 ID `jev-1.13.0`은 제공자 API의 실제 ID라 바뀌지 않았습니다(`AI_MODEL`).
