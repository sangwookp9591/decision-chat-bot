# Jev Triage 현재 제품 흐름 시연

- 실행: `bash scripts/demo/record.sh`
- 기준 commit: b497d9524901bc21dc7effa1a69a0de632618dcf
- 전용 API 10291 · Vite 7591 · tenant `t-demo-20261004t143022z` · tenant 제한 worker
- JEV_MODE=live. .env는 Settings가 읽으며 키는 출력하거나 녹화하지 않습니다.
- 1440×900 · 30 fps · H.264 · 한국어 자막 · reduced-motion 해제. 시스템 다크 모드는 장면 14에서 켭니다.
- 로그인부터 마무리까지 하나의 연속 브라우저 녹화입니다. 실제 응답 및 애니메이션을 조작하지 않습니다.
- 녹화 전 실제 LIVE 요청 3건을 수정 승인하고 학습 후보와 규칙 초안을 공개 API로 생성했습니다. 운영 게시하지 않았습니다.
- 백엔드 판단 결과와 제품 코드는 변경하지 않았습니다.
- 콘솔 오류: 9건 · 부분 실패: 0장면
- 재현 시험: 변경 전 REC-2 계약 시험 2건 실패(기존 포트·13개 장면), 변경 후 통과.

## 영상

[walkthrough.mp4](walkthrough.mp4) · 170.97초 · 4.78 MiB

[타임코드](chapters.md) · [검증 manifest](manifest.json)

## 장면 PNG 목록

- [scene-01-login.png](scene-01-login.png)
- [scene-01.png](scene-01.png)
- [scene-02-greeting.png](scene-02-greeting.png)
- [scene-02-typing.png](scene-02-typing.png)
- [scene-02.png](scene-02.png)
- [scene-03-provisional.png](scene-03-provisional.png)
- [scene-03-summary.png](scene-03-summary.png)
- [scene-03.png](scene-03.png)
- [scene-04-cancelled.png](scene-04-cancelled.png)
- [scene-04.png](scene-04.png)
- [scene-05.png](scene-05.png)
- [scene-06-original.png](scene-06-original.png)
- [scene-06.png](scene-06.png)
- [scene-07.png](scene-07.png)
- [scene-08-trace.png](scene-08-trace.png)
- [scene-08.png](scene-08.png)
- [scene-09-glow.png](scene-09-glow.png)
- [scene-09.png](scene-09.png)
- [scene-10.png](scene-10.png)
- [scene-11-confirmed.png](scene-11-confirmed.png)
- [scene-11.png](scene-11.png)
- [scene-12-counts.png](scene-12-counts.png)
- [scene-12.png](scene-12.png)
- [scene-13.png](scene-13.png)
- [scene-14.png](scene-14.png)
- [scene-15.png](scene-15.png)

## 한계 및 오류

장면 실행 오류 없음.

- console, 장면 1: Failed to load resource: the server responded with a status of 401 (Unauthorized)
- console, 장면 1: Failed to load resource: the server responded with a status of 401 (Unauthorized)
- console, 장면 2: Failed to load resource: the server responded with a status of 404 (Not Found)
- console, 장면 4: Failed to load resource: the server responded with a status of 404 (Not Found)
- console, 장면 4: Failed to load resource: the server responded with a status of 404 (Not Found)
- console, 장면 4: Failed to load resource: the server responded with a status of 404 (Not Found)
- console, 장면 4: Failed to load resource: the server responded with a status of 404 (Not Found)
- console, 장면 4: Failed to load resource: the server responded with a status of 404 (Not Found)
- console, 장면 10: Failed to load resource: the server responded with a status of 404 (Not Found)

## 콘솔 응답 해석

로그인 전 인증 확인 401, 저장 전 판단 조회 404, 미게시 초안의 효과 조회 404는 예상된 HTTP 응답이지만 브라우저 콘솔에 오류로 찍힙니다. 각 위치는 manifest의 consoleErrors에 보존합니다. React 경고와 pageerror가 있으면 별도 제품 결함으로 다룹니다.

## 실측 표시 시간

{"start":1791124247849,"typing":165,"preliminary":777,"final":2146}

클릭 직전 관찰자 설치부터 해당 DOM 최초 표시까지의 밀리초이며 서버 지연과 다릅니다.

## 종료 확인

소유한 API·worker·collector·watchdog·Vite 자식 프로세스 종료 확인.

```text
decision-chat-bot-neo4j-1 Up 13 hours (healthy)
decision-chat-bot-redis-1 Up 12 hours (healthy)
```

## REC-2 검증 결과와 재현 기록

최종 `bash scripts/demo/record.sh` 실행은 종료 코드 0으로 15개 장면을 모두 완주했습니다. 영상은 **170.966667초 (2분 50.97초), 5,015,313 bytes (4.78 MiB)**이며 PNG **26장**을 생성했습니다. 위 PNG 전부를 모아보기 이미지로 직접 확인했고 실제 MP4 프레임도 추출해 한국어 자막·다크 모드가 인코딩에 포함됐음을 확인했습니다.

| 재현 시험 / 문제 | 수정 전 실패 증거 | 수정 및 최종 확인 |
|---|---|---|
| REC-2 계약 | 기존 포트 9191/6491, 13개 장면으로 계약 시험 2건 실패 | 10291/7591, 새 tenant, 15개 장면, motion 활성화; 시험 2건 통과 |
| 데스크톱 새 대화 | 첫 실행 장면 4: 숨겨진 `새 요청 시작` 아이콘 대기 실패 | 표시되는 `.request-list .new-chat` 사용; 장면 4 완료 |
| 정책 폼 | 첫 실행 장면 13: label이 폼 그룹과 JSON 편집기 2개에 매칭 | 이름이 일치하는 `group`으로 범위 지정; 장면 13 완료 |
| 빠른 잠정 결과 | 두 번째 실행 장면 3: 고정 대기 동안 잠정 화면이 최종으로 전환 | 전송 후 고정 최소 대기를 제거; 잠정 PNG와 최종 PNG 모두 캡처 |
| 재분석 확인 | 두 번째 실행 장면 4: Playwright 기본 confirm 취소로 새 실행 없음 | 확인 대화상자를 명시 수락; 취소 후 새 LIVE 결과 표시 확인 |
| 요약 스크롤 | 세 번째 실행 장면 3: 요약·업무 카드가 함께 매칭 | 첫 요약 카드로 범위 지정; 최종 장면 3 완료 |
| 산출물 검사 | 초기 실패 영상에 `verify.mjs` 실행 시 `All scenes must complete` 실패 | 최종 검사 통과: 15장면, 26 PNG, 규격·타임코드·단계 표시 순서·취소 증거 |

초기 실행 3개는 `raw/attempts/`에 보관했습니다. 최종 영상에 실패 장면이나 이전 화면을 합성하지 않았습니다.

- `cd backend && .venv/bin/pytest -q`: **466 passed, 1 skipped** (102.02초).
- `cd backend && .venv/bin/ruff check jevtriage tests`: **All checks passed**.
- `node --test scripts/demo/contract.test.mjs`: **2 passed**.
- `node scripts/demo/verify.mjs artifacts/demo/20261004T143022Z`: **통과**.
- 제품/프런트 소스는 수정하지 않아 프런트 typecheck/test/build는 이 작업에서 생략했습니다.
- 기존 docs에서 시연 안내 절을 찾지 못해 제품 아키텍처 문서는 수정하지 않았습니다. 재녹화 안내는 [scripts/demo/README.md](../../../scripts/demo/README.md)에 추가했습니다.
- 실제 API 키가 스크립트·산출물 193개 파일에 포함되지 않았음을 바이트 검색으로 확인했습니다. 키 값 자체는 출력하지 않았습니다.
- API 10291·Vite 7591 포트가 닫혔음을 확인했습니다. 소유한 worker·collector·watchdog도 종료했고, 공유 Neo4j·Redis는 healthy 상태입니다.

### 콘솔 9건 분류

콘솔 0건 조건은 달성하지 못했습니다. 다만 사용자 지시에 따라 아래 예상 HTTP 응답을 모두 기록했으며 숨기거나 필터링하지 않았습니다.

| 종류 | 건수 | 해석 |
|---|---:|---|
| `/api/auth/me` 401 | 2 | 로그인 전 인증 상태 확인 |
| `/api/requests/.../judgment` 404 | 6 | 최초 저장 전·취소된 실행의 판단 조회 |
| `/api/learning/rules/R-DEMO-01/effects` 404 | 1 | 아직 게시하지 않은 규칙 초안의 효과 없음 |
| React 경고 / pageerror | 0 | 첫 실행의 중복 버전 key 경고는 코디네이터 수정 b497d95 반영 후 사라짐 |

표시 시간은 타이핑 **165ms**, 잠정 **777ms**, 최종 **2,146ms**였습니다. 실제 LIVE 실행의 DOM 표시 실측으로, 별도의 성능 보장은 아닙니다.
