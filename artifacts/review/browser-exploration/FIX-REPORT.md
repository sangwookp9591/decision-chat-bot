# UX-1 수정 보고: 브라우저 탐색 결함 13건 + 프런트 SSE 정합

- 대상: `REPORT.md` P3-01~P3-13, `architecture-review.md` R18(프런트 쪽).
- 절차: 결함마다 실패하는 시험을 먼저 작성 → 수정 → 통과 → 실제 브라우저(Playwright Chromium)에서 재현 시나리오 그대로 재확인.
- 재확인 환경: API 8291(`JEV_MODE=live`), Vite 5491, tenant 제한 worker(`t-alpha`, a11y용 `t-t23`), 비민감 문장. 확인 후 모든 프로세스 종료(8291/5491/5281 LISTEN 없음). 공유 Neo4j(7687)와 다른 작업자의 8191/5391은 건드리지 않았다. 스크린샷·원시 결과는 `fix/` 폴더.

## 수정 전 실패 확인 방법

- 백엔드: `tests/integration/test_ux_projections.py` 3건이 수정 전 3건 모두 실패(역순 Flow, 엣지 없음, 검증 GET이 JSON 문자열 반환)했고 수정 후 통과.
- 프런트: 새 시험을 HEAD(`0da8b1e`) 소스에 복사해 실행한 결과 신규/변경 시험 27건이 실패했고(Login 3, statusLabels 3, events 3, validationCard 2, Observatory 2, Monitoring 2, Policy 2, Review 3, Main 6, playback 1), 수정 후 전체 통과(15 파일·65건).

## 결함별 재확인 결과

| ID | 수정 | 재현 시험(수정 전 실패) | 브라우저 재확인 |
| --- | --- | --- | --- |
| P3-01 | `Login.tsx`: 이메일·암호 폼, 제출 중 상태, 401/429 한국어 오류, 성공 시 세션 갱신(URL 유지로 원래 경로 복귀) | `Login.test.tsx` 3건 | 통과. 쿠키 없는 새 브라우저 `/review?x=1` → 폼 표시, 잘못된 암호 → "이메일 또는 암호가 올바르지 않습니다.", 정상 로그인 → `/review?x=1` 그대로 표시 (`fix/p3-01-*.png`) |
| P3-02 | `main/requestState.ts`: '보완 필요' 상태에서 사유·필요 정보 카드, "보완 내용 제출 (새 revision)" → `/revisions`(`expected_revision` 포함). 결과 배지는 요청 상태(보완 필요/반려됨/배정 완료) 우선, `review_decided` 등 SSE로 갱신 | `Main.test.tsx` 3건(보완/반려/배지) | 통과. 검토자가 "사용 부서와 완료 희망일을 보완해 주세요"로 정보 요청 → 요청자 화면에 사유·"보완 필요 · 정보 요청"·제출 버튼 표시 → 제출 후 같은 요청의 revision 2건(새 요청 아님) (`fix/p3-02-*.png`) |
| P3-03 | Monitoring 링크를 `/observatory?request_id=&run_id=`로 변경(시도만 있는 실패는 링크 없이 시도 ID 표시). Observatory가 `run_id`만으로도 요청을 맞춤, 목록 밖 요청도 선택 가능 | `Monitoring.test.tsx`(href), `Observatory.test.tsx` | 통과. 실제 실패 목록 링크 클릭 → 실행 관찰 화면(404 아님), `?run_id=`만으로 요청 자동 선택 (`fix/p3-03-failure-link.png`) |
| P3-04 | `observe/flow.py`: predecessor/parent 위상 정렬(시작 시각·ID 보조), 선행 없는 단계는 `sequence` 엣지, Review 노드 이름 "사람 검토"+`review` 엣지. 프런트: `<ol>` 순서·'선행' 표시·엣지 목록, 재생 도달은 노드 ID 기준 | `test_ux_projections.py` 2건, `Observatory.test.tsx`, `playback.test.ts` | 통과. 실제 실행 순서: 입력 정리 → Jev 판단 → 근거 연결 → 업무 분해 → 규칙 적용 → 자동 배정 조건 검사 → 결과 저장 → 사람 검토, 엣지 7개 (`fix/p3-04-flow-order.png`) |
| P3-05 | 위젯 전송 시 접수 화면이면 `chat:request` 이벤트, 다른 화면이면 저장 후 `/` 이동. 접수 입력에 채우고 포커스·안내, 위젯은 닫힘 | `Main.test.tsx` | 통과. 전송 즉시 textarea 값 채워짐·포커스 `request-text`·위젯 닫힘·안내 표시 (`fix/p3-05-chat-handoff.png`) |
| P3-06 | `learning/shadow.py`: `validation_dto`로 POST/단건/목록이 같은 DTO(`changes_by_value`·`usage` 객체, `failures` 목록+`failure_count`, `from`/`to`). 화면은 "담당 조직 · 주관 → 현업 8건"과 기간·실패 수 표시 | `test_ux_projections.py`, `validationCard.test.tsx` | 통과. 기존 검증 `val_9f48…`: "AI 필요성 → 필요 4건", 기간 `2026. 9. 3. … ~ 2026. 10. 4. …`, "실패 0" (`fix/p3-06-validation-card.png`). 문자 인덱스 펼침 없음 |
| P3-07 | `open(id, keepNotice)`와 409 처리 순서 수정: 최신 로드 후 충돌 안내 설정. 종료된 검토는 결정 버튼 비활성+읽기 전용 안내. 결정 중복 전송 방지(in-flight 가드) | `Review.test.tsx` 2건(409 유지, 중복 클릭 1회) | 통과. 두 탭, 한 탭이 승인한 뒤 오래된 탭에서 반려 → 409 안내가 2.5초 후에도 유지, 승인·반려 버튼 비활성 (`fix/p3-07-conflict-notice.png`) |
| P3-08 | `Policy.tsx`: 필드별 원문 초안 유지, 유효한 JSON일 때만 설정에 반영, 필드별 오류 표시(마지막 유효 값 유지) | `Policy.test.tsx` | 통과. `risk_clear_max` `0.2` 전체 선택→Backspace → 빈 입력 유지, 이어서 `1.5` 입력 가능 (`fix/p3-08-policy-edit.png`) |
| P3-09 | Monitoring 초안/적용 필터 분리, `rangeProblem`으로 빈 값·역순을 입력 오류로 안내하고 적용 비활성, 예외 없음 | `Monitoring.test.tsx` | 통과. 시작 날짜 비움 → pageerror 0건, "시작과 종료 시각을 모두 올바르게 입력해 주세요.", 적용 비활성 (`fix/p3-09-monitoring-date.png`) |
| P3-10 | Review가 `?request_id=`/`?review_id=` 딥링크를 읽어 대상 검토를 자동 선택(처리 완료 검토는 상태별 목록에서 찾아 읽기 전용). 상태 필터 추가, 선택 시 URL에 `review_id` 반영 | `Review.test.tsx` 2건 | 통과(검토자). 판단 맵 "원문·검토 열기" → 대상 요청 검토 상세, 승인 후에도 request_id 링크로 열림. **제한**: operator 계정은 서버 권한상 검토 목록이 비어 "연결된 검토가 없습니다…" 안내만 표시(서버 권한 정책, 변경 대상 아님) (`fix/p3-10-*.png`) |
| P3-11 | Main이 `?request_id=`를 선택 상태로 사용(제출·목록 선택은 URL 반영, 뒤로가기·새로고침 복원) | `Main.test.tsx` 2건 | 통과. 새로고침 후 같은 요청 결과·진행 유지, 다른 요청 선택 후 뒤로가기로 복원 (`fix/p3-11-*.png`) |
| P3-12 | 모바일에서 입력을 목록보다 먼저(`order:-1` 제거, 목록은 최대 60vh 스크롤), 배지 `nowrap`, ID 줄바꿈, 학습 카드 grid `min-width:0` | CSS 변경이라 시험은 브라우저로 확인 | 통과. 375px 10개 화면 모두 `scrollWidth==375`, 요청 입력 y=359(수정 전 2176), 배지 깨짐 0, 후보 선택한 규칙 학습 화면도 넘침 없음(수정 전 396) (`fix/p3-12-*-375.png`) |
| P3-13 | `statusLabels.ts`: `roleLabel`(team_member·policy_editor 포함), `reviewActionLabel`, `attachmentReasonLabel`(복구 행동 포함), `statusText`, `localizeError`; `apiFetch` 오류를 한국어로 변환(원문은 `raw`), 정책 검증 오류는 코드를 '기술 상세'로 | `statusLabels.test.ts` 3건, `Policy.test.tsx`, `Main.test.tsx` | 통과. 팀 담당자/정책 편집자 라벨, 결정 이력 "정보 요청/승인", 없는 요청 "요청을 찾을 수 없습니다.", 정책 검증 "임계값은 0과 1 사이여야 합니다." + 펼침 상세 `SCHEMA_INVALID`, 판단 맵 상태 필터 "게시됨" (`fix/p3-13-*.png`) |
| R18(프런트) | `EVENT_KINDS`를 서버 kind와 동일하게(서버가 안 보내는 `request.updated`·`run.*` 제거, `judgment_saved`·`review_decided`·`task.transitioned`·`rule.*` 등 추가). 오류 시 소스를 닫고 지수 백오프로 `?after=`만 쓰는 수동 재연결(Last-Event-ID 충돌 회피), 오류 때 세션 확인, `session-expired` 처리, 요청 없는 화면의 `snapshot-required` 복구, 커서 키에 tenant·user 포함 | `events.test.ts`(백엔드 소스를 읽어 kind 목록 대조·재연결·커서 범위) | 일반 흐름(SSE 연결·갱신)은 위 시나리오에서 동작. 네트워크 단절 재연결은 단위 수준(백오프·URL)까지만 확인하고 브라우저 장애 주입은 하지 않음 |

## 검증 결과

- `cd frontend && npm run typecheck && npm run test && npm run build`: 통과 (vitest 15 파일 65건, 빌드 OK).
- `cd backend && .venv/bin/pytest -q`: 389 passed, 1 skipped. `.venv/bin/ruff check jevtriage tests`: 0건.
- `npx playwright test -c playwright.a11y.config.ts --workers=1` (E2E_API=8291, E2E_PORT=5281, `t-t23` worker 별도 기동): chromium+webkit 12/12 통과.
  - `--workers=1` 없이 실행하면 chromium·webkit 프로젝트가 같은 tenant(`t-t23`)에서 동시에 "키보드 접수" 시험을 돌려 서로의 요청·검토를 가로채 실패할 수 있다(원인은 시험 간 간섭이며 제품 결함 아님). 그 과정에서 같은 결정 버튼의 중복 활성화 가능성을 발견해 Review에 중복 전송 가드를 추가했다.
  - 이 실행은 추적 중인 `artifacts/validation/t23/{chromium,webkit}-responsive-520.png`를 덮어썼다. 필요하면 코디네이터가 되돌리거나 함께 커밋.
- 기존 e2e: `main.spec`·`monitoring.spec`·`webmcp.spec`·`judgment-map.spec` 6건 통과. `main.spec`의 손상 파일 시험은 선택자가 최신 상태 라벨('파일 결정 필요')과 어긋나 있어 정규식에 추가했다. `policy.spec`(정책 게시)·`learning.spec`(신규 tenant 필요)는 공유 데이터 변경을 피하려고 실행하지 않았다.

## 변경 파일

- 백엔드: `observe/flow.py`, `learning/shadow.py`, 시험 `tests/integration/test_ux_projections.py`(신규), `test_observe_api.py`(엣지 단언을 predecessor 한정으로 갱신).
- 프런트: `state/events.ts`·`session.ts`, `api/{client,requests,reviews,observe,learning}.ts`, `components/{statusLabels.ts,ChatWidget.tsx,ui.css}`, `layout/AppShell.tsx`, `App.tsx`, `pages/{Login,Main,Review,Monitoring,Policy,Observatory,JudgmentMap}.tsx`, `pages/main/requestState.ts`(신규), `pages/learning/sections.tsx`, `pages/judgment-map/Detail.tsx`, CSS 4개, 시험(신규 `Login`·`Observatory`·`statusLabels`·`validationCard`, 갱신 `Main`·`Review`·`Monitoring`·`Policy`·`events`·`playback`), `e2e/main.spec.ts`.
- 문서: `EVENTS.md`(프런트 구독 계약), `OBSERVE_API.md`, `LEARNING_VALIDATION.md`, `A11Y.md`.

## 건너뜀·남은 사항

- 원문 권한 거절을 "위치 확인 불가"로 안내하는 낮은 심각도 항목, 추가 사용성 제안(요청 목록 제목 표시, 맵 글자 크기, 검토 수정 입력 enum)은 이번 13건 범위 밖이라 하지 않았다.
- operator 계정으로는 서버 권한 때문에 검토 상세를 열 수 없어 판단 맵→검토 딥링크는 검토자 계정으로 확인했다.
- 요청 목록에는 여전히 ID만 표시한다(P3 추가 제안).
