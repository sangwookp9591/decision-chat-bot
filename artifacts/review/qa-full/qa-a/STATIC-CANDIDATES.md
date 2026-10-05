# 복구 대기 중 정적 점검 — 미확정 후보

아래는 실행으로 결함을 확정하지 않았다. 제품 코드 수정 없음.

| 후보 | 코드 근거 | 재현 시험 |
|---|---|---|
| 업무 상세 Escape/초점 관리 | Tasks.tsx의 role=dialog aside에 공용 Overlay나 Escape key handler/focus trap 없음 | journeys: task detail Escape |
| 다른 탭 업무 전이 미반영 | Tasks.tsx useEffect는 필터 변경만 구독하고 SSE 연결 없음 | journeys: task update in second tab |
| 검토 목록 신규 검토 미반영 | Review.tsx refresh는 초기/필터/결정/수동 새로고침에서만 실행, SSE 구독 없음 | journeys: reviewer queue receives other role |
| 팀 필터 이름/ID 불일치 | Tasks.tsx option value는 IT팀/AI팀/현업이고 tasks/api.py는 저장 lead_org와 문자 동일성 비교 | journeys: team filter retains IT |
| 정확히 0px 전환 | 기존 p7 시험은 4px까지 허용하여 0px 요구의 증거가 아님 | layout.spec.ts: 0px 실측 추가 |

직접 생성한 actor context에도 pageerror, console error, HTTP 4xx/5xx, requestfailed, 5초 이상 요청 계측을 연결했다. 요청/응답 본문과 쿠키는 기록하지 않는다. Playwright --list로 TypeScript 로딩을 확인하지만 이는 동작 통과와 다르다.
