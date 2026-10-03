# P6 최종 확인

- 대상: HEAD `37db831`, 2026-10-04 02:08–02:19 KST. Chromium 153.0.8010.12 / WebKit 26.6 실제 Playwright 브라우저.
- API 8791, Vite 5991, `JEV_MODE=live`, worker `--tenant t-alpha --tenant t-beta`, collector·watchdog을 시작부터 함께 기동. 모든 backend 프로세스는 같은 절대 DATA_DIR을 사용. OrbStack 공유 Neo4j 유지.
- PRD/TASK, spec 00–08 및 실행·데이터·검토·학습 계약, 운영 RUNBOOK, GATE_REPORT의 관련 기준을 대조한 제한적 최종 확인이다. 전체 제품 재인수 판정은 아니다. 코드·문서·설정 변경 없이 이 보고서와 `p6-*.png`만 저장했다.

## 판정 표

| 확인 | Chromium / WebKit | 판정·증거 |
|---|---|---|
| Learning 신호 이름 | 동일 | 해결: AI팀 참여 확률, 현업 참여 확률, 임상·안전 위험 확률 등. [C](p6-c-Learning.png) / [W](p6-w-Learning.png) |
| Learning APPLIED / shadow | 동일 | 부분 해결: `APPLIED used/out_of_scope`는 `적용 적용됨/범위 밖(미적용)`으로 치환되나 `shadow 제외` 잔존. |
| JudgmentMap 개별 노드 제목 | 동일 | 해결: 펼친 반환값의 `Jev · AI 필요성`, `Jev · 담당 조직 · 주관`, `검토 결정 · 승인/정보 요청`, `규칙 결정 · 승인`. [C](p6-c-map-expanded.png) / [W](p6-w-map-expanded.png) |
| Tasks 정책 임계값 | 동일 | 해결: `정책 임계값(위험 없음 확인 상한)`. [C](p6-c-Tasks.png) / [W](p6-w-Tasks.png) |
| Main 신뢰도 | 동일 | 해결: `선택 신뢰도 99%` 등. [C](p6-c-result-after-approval.png) / [W](p6-w-result-after-approval.png) |
| 다른 화면 코드 노출 훑기 | 동일 | 판단 맵 묶음에 `ModelOutput 외 22개` 추가 관찰. Review·Tasks·로드 완료 Monitoring·Observatory의 상태/사유에서 새로운 원시 열거값은 발견하지 못함. 정책의 JSON 편집기·기술 식별자/UUID는 별도 기술 화면 범위로 구분했다. |
| 반응형 전체 | 첫 실행 27/28 → 재실행 28/28 | 7화면 × 375/520px × 2브라우저. 재실행은 Monitoring 포함 전부 통과, skip 0. 아래 설명 참조. |
| 요청 제출 → 결과 → 원문 | 통과(표본 제한) | 새 LIVE 요청 2건 결과 저장. 인용이 있는 두 번째 요청을 양쪽 source_reader로 열어 원문 3단위와 `문단 1 · 문장 3` 강조 확인. [C](p6-c-source.png) / [W](p6-w-source.png) |
| 검토 수정 승인 → 업무 | 핵심 흐름 통과, 표시 결함 있음 | 양쪽에서 AI 필요성 불필요→혼합 수정 승인, 감사 이력과 실제 업무 각 1개 확인. 미해결 개발 가능성 차단 유지. [C 승인](p6-c-approved.png) / [W 승인](p6-w-approved.png), [C 업무](p6-c-task.png) / [W 업무](p6-w-task.png). Main 초안 표시 중복은 P6-01. |
| 규칙 학습 게시 상태 조회 | 통과 | `R-PFOUR-01@1` UI/API 모두 중단, 게시 Config v14, 활성 v17, 적용 기록 0. 게시·중단 이력과 게시 후 관찰을 조회. 신규 게시 쓰기는 수행하지 않음. |

## 반응형 시험의 실패 판정

요청한 명령을 frontend에서 실행했다:

```sh
E2E_BASE_URL=http://127.0.0.1:5991 npx playwright test -c playwright.config.ts e2e/responsive-overflow.spec.ts --output=/tmp/p6-retest/retest-results
```

첫 실행은 같은 설정/스펙을 저장소 루트에서 지정했고 **27 passed, 1 failed (1.7m)**였다. 실패는 Chromium 375px Monitoring의 `핵심 지표` heading 5초 대기 초과이며, 가로 너비 assertion까지 도달하지 않았다. trace에는 alerts 200과 아직 종료되지 않은 summary/slo/failures 요청, 화면에는 “모니터링 집계 불러오는 중”이 기록됐다. collector/watchdog은 당시 실행 중이었다.

동일 기본 2 workers로 변경 없이 재실행한 위 명령은 **28 passed (1.7m)**. 이후 실화면 추가 확인은 Chromium 1,881ms / WebKit 6,041ms에 로드 완료, 관련 집계 응답 모두 200, 둘 다 375px에서 scrollWidth 375였다. 따라서 **이번 실패는 로컬 집계 지연과 5초 assertion의 환경·타이밍 문제로 분류하며 레이아웃 제품 결함으로 세지 않는다**. 지연의 상세 근본 원인(부하/집계 성능)은 불확실하고, 6초 관측이 있으므로 플래키 가능성은 남는다. 개선은 집계 완료를 충분한 명시적 timeout으로 기다린 후 overflow를 검사하고, 실제 집계 성능은 별도 측정하는 방식(S). 수집기 부재 탓으로 판정하지 않았다.

## 결함

### P4-05/P3-13 잔여 [심각도 낮음] — 일반 화면의 일부 내부 표현 — S

- **위치:** `frontend/src/lib/labels.ts:25`, `frontend/src/pages/learning/sections.tsx:105`, `backend/jevtriage/learning/effects.py:128`; `frontend/src/pages/judgment-map/logic.ts:72`.
- **문제·근거:** C/W `/learning?rule_id=R-PFOUR-01` 기본 설명에 `실제 Run; 게시 후 적용 적용됨/범위 밖(미적용) 집단; shadow 제외`가 남는다. `displayCodeLabel`에 shadow 매핑이 없다. C/W `/judgment-map?request_id=req_e83022236db54a85950d9c5de402171d&view=list`에 `ModelOutput 외 22개`가 표시된다([C](p6-c-JudgmentMap.png) / [W](p6-w-JudgmentMap.png)); 묶음 label이 원형 `${kind}`를 사용한다. 개별 노드 수정은 통과했지만 묶음은 빠졌다.
- **제안 수정:** 효과 설명을 “실제 실행 / 규칙 적용·범위 밖 집단 / 비교 검증 실행 제외”로 문장 단위 작성하고, 묶음에도 기존 kind 한국어 사전을 적용한다. 기본 화면에서 해당 문구를 두 브라우저로 확인한다. 기존 코드 노출 결함의 잔여이며 신규 기능 결함으로 중복 계산하지 않는다.

### P6-01 [심각도 중간] — 수정 승인 후 초안 버전들을 같은 업무 목록으로 표시 — M

- **위치:** `backend/jevtriage/judgment/store.py:192`, `backend/jevtriage/judgment/api.py:67`, `frontend/src/pages/Main.tsx:163`; 처리된 Review의 업무 분담 원안도 같은 버전 구분 문제를 관찰했다.
- **재현:** 아래 새 요청을 검토자가 AI 필요성 불필요→혼합으로 수정 승인한 뒤 Main을 다시 연다. 두 브라우저 모두 “업무 분담”에 동일한 “화면·리포트 개발 / 일반 기술 / IT팀 / 현업”이 두 줄 나타난다. [C](p6-c-result-after-approval.png) / [W](p6-w-result-after-approval.png).
- **근거:** judgment API `draft_tasks`에는 같은 `draft_task_id=draft-1`의 `draft_version=1`과 `2`가 함께 반환된다. 저장소 쿼리가 run의 모든 DraftTask를 반환하고 Main은 버전 구분 없이 전부 렌더링한다. 실제 Neo4j Task 조회는 각 요청 **1개**이므로 중복 배정은 아니다. EXECUTION_CONTRACT:28의 “원안과 구분된 수정 초안” 요구에 비추어 원안/수정안 구분이 부족하다. 이번에 새로 발견했으며 이 커밋에서 발생한 회귀인지는 불확실하다.
- **제안 수정:** Main 기본 업무에는 명시적으로 선택한 초안 버전(승인 후 최신 승인 버전)을 사용하고, 원안은 버전별 비교 영역으로 분리한다. Review도 원안/수정 초안을 구분한다. 원본 이력은 보존하며 분류만 수정하는 승인과 업무 조직 수정 승인을 각각 재현해 한 업무가 한 번 표시되는지 검증한다.

## 표본과 정리

지정된 3개 회귀 종류를 모두 실행했다. 무작위 요소는 첫 요청 문구를 회의실/비품 후보 중 선택한 것이며, 전체 기능에서 균등 무작위 추출한 시험은 아니다.

- C 요청 `req_b6549a60ae3641808d62b206a4e20f18`, run `run_7a98d8901d874e15acbe74ecd020f6ae`, review `rvw_8e7de1401b2841faaeb7e231e3feffb8`, Task `task_fe243a28ff4a4d30a99126d547c7817f`.
- W 요청 `req_ec72d7e774ed4e0b9a5b0d0318ab0e15`, run `run_9273b03ee26a48e7ab49fda0922a857b`, review `rvw_8b2cc2916ae643d6ab922cdc0ca04946`, Task `task_2dd377cfa13544d99a1e2245395ca405`.
- 첫 요청은 Jev 인용 0건이라 원문 뷰어 성공 표본에 포함하지 않았다. 기본 requester/reviewer는 `can_read_source=false`여서 원문 확인은 기존 source_reader 계정으로 수행했다. 둘째 요청의 실제 인용을 C/W 모두 확인했다.
- 가상 요청 2건·수정 승인 2건·업무 2건은 개발 DB의 감사 이력으로 남겼다. 정책 v17은 유지했다. 자동화 locator 대기 실패/조작기 재시작은 제품 실패와 구분했으며 성공 증거에는 최종 완료 화면만 사용했다. 관찰된 브라우저 pageerror 0.
- 종료 시 이번 API 86858, worker 86859, collector 86860, watchdog 86861, Vite 86862와 브라우저·임시 조작기를 종료했다. 공유 Neo4j는 정지하지 않았다. 원시 임시 로그는 `/tmp/p6-retest/`에 있으며 영속 검토 산출물은 본 보고서와 스크린샷이다.
