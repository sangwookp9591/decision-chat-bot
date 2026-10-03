# UX-3 수정 보고서 — Astra 재시험 잔여 결함 P4-01~P4-05

근거: `artifacts/review/browser-retest/REPORT.md`. 순서는 항목마다 **실패하는 시험 작성 → 수정 → 통과**였다(수정 전 실패한 시험 이름을 표에 둔다). 백엔드 코드는 변경하지 않았다: `block_reasons`는 이미 업무 목록·상세 응답(`dict(t)` 전체 속성)에 있어 프런트 타입만 추가했다.

## 결과 표

| 결함 | 수정 전 실패 시험 | 수정 | 수정 후 |
| --- | --- | --- | --- |
| P4-01 차단 사유 | `Tasks.test.tsx` "shows Korean block reasons…", "keeps the latest block reasons after a 409…" 실패 | `api/tasks.ts`에 `block_reasons`, `pages/tasks/blockers.ts`(서버 규칙과 같은 조건: 선행 미완료·본업무 전제·`block_reasons`), 목록 막힘 행·상세 "시작 차단 사유", 차단 시 `진행으로 변경` 비활성(막힘 상태에도 버튼 표시), 409 뒤 상세 재조회해 최신 사유를 안내에 유지 | vitest 3건 통과. 실제 `feasibility_unresolved` 업무: C/W 모두 목록·상세에 "개발 가능성 …" 표시, 원형 코드 비노출, 시작 버튼 비활성 |
| P4-02 검증 날짜 | `Learning.test.tsx` "disables 검증 실행…when a date is cleared" 실패 | `validationRangeProblem`(필수·유효·시작≤끝) + 입력 옆 `role=alert`·`aria-invalid`, 문제 시 실행 비활성, ISO 변환은 검증 뒤 | vitest 통과. C/W 실제 화면: 시작 삭제 → 한국어 안내·비활성, pageerror 0 |
| P4-03 권한 없는 검토 오류 소실 | `Review.test.tsx` "keeps the detail error when the list refresh finishes afterwards" 실패 | `listError`/`error` 분리(목록 성공이 상세 오류를 지우지 못함), 오류 한국어화, `목록으로 돌아가기` 버튼 | vitest 통과. C/W에서 목록 응답을 800ms 지연: 목록 완료 후에도 "검토를 찾을 수 없습니다." 유지, 대기 0건과 동시에 표시 |
| P4-04 가로 넘침 | `e2e/responsive-overflow.spec.ts`(신규) Chromium 375px Main(`req_0c11…`, scrollWidth 384>375)·Review(`rvw_bcd9…`, 534>375)·Tasks 실패(Tasks는 시험 자체 결함: 고정 상세가 다음 행 클릭을 가려 시험 수정) | `style.css` 공통 규칙(긴 ID `overflow-wrap:anywhere`, 폼 `max-width:100%`, `pre` 스크롤, grid 자식 `min-width:0`), 단일 열 grid를 `minmax(0,1fr)`로(main/review/tasks css) | Chromium·WebKit 각 14/14 통과: 375·520px × Main(결과 선택 최대 8건)·Review(상태별 최대 12건 상세)·Monitoring·Learning(후보 4)·Tasks(상세 4)·Observatory(요청 3)·JudgmentMap(3D·목록), 기준 `document.scrollingElement.scrollWidth ≤ 뷰포트` |
| P4-05 내부 코드 | `lib/labels.test.ts`, `Main.test.tsx`·`Review.test.tsx`·`Monitoring.test.tsx` 신규 케이스 실패(5건) | `lib/labels.ts` 공용 라벨(질문·항목·출력 유형·검토 사유·차단 사유·수집 문제·SLO 사유·알림·규칙 결정·근거 위치), `RawDetails`("자세히")에 원본 코드/JSON, 학습 수명(승인 → "승인 · 사유 · 확정 범위: …")·규칙 대상 라벨 | vitest 통과. C/W 실제 화면 `main.innerText`에 `ai_need|feasibility|lead_org|question_id|worker_stopped|collector_stopped|Less than 30 days|approve|{"all"` 없음(Main·Review·Monitoring·Learning 후보 3건). 첫 브라우저 확인에서 Review 목록(쉼표 구분 사유)·학습 "대상 lead_org"가 남아 추가 수정 |

의도적으로 유지: 결과 카드의 "Choice confidence 72%"·"Noul 확률" 표기(기존 시험이 요구하는 Jev 신호 용어), Trace 화면의 기술 JSON(범위 밖).

## 검증

- 브라우저: API 8591(`JEV_MODE=live`, 공유 `.data`, 공유 Neo4j) + Vite 5791(임시 설정으로 `/api→8591`). tenant는 Astra가 만든 `t-alpha` 실데이터를 **읽기만** 했다(새 요청·Jev 호출 없음 → worker 미기동). Chromium·WebKit 모두 확인. 8191/5391·Astra 프로세스·7687은 건드리지 않았다.
- `npx tsc --noEmit` 통과, `npx vitest run` 21파일 92건 통과, `npm run build` 성공.
- 백엔드 `pytest -q` 393 passed / 1 skipped, `ruff check jevtriage tests` 0건.
- a11y(`--workers=1`): t23 PNG 덮어쓰기를 막기 위해 임시 복사본(PNG를 scratchpad로, 계정 tenant만 `t-alpha`)으로 실행. 결과는 아래 "a11y" 절.
- 문서: `docs/architecture/A11Y.md` "UX-3 화면 동작 기준" 추가.

## 건너뜀·한계

- 학습 화면의 `검증 실행` 클릭 후 서버 호출 경로는 실제 후보(검증 중 버전)가 `t-alpha`에 없어 브라우저에서 재현하지 못했다(빈 날짜 → 비활성·안내까지 확인). 정상 날짜 경로는 기존 vitest가 담당한다.
- 서버가 "시작 가능 여부"를 별도 필드로 내려 주는 제안은 하지 않았다(화면이 서버와 같은 조건을 계산, 최종 판정은 409). 필요하면 후속으로 `can_start`를 추가한다.
- Observatory·판단 맵의 내부 용어 전수 점검은 이 범위(P4-05의 지목 화면)에 넣지 않았다.

## a11y

`--workers=1`, Chromium·WebKit 각 5건(로그인, 주요 9화면 axe critical/serious 0, 셸·터치 영역, reduced-motion, 채팅 키보드) **10/10 통과**. 여섯 번째 시험 "keyboard … opens its saved evidence"는 LIVE Jev 판단을 기다리는 시험이라 worker 없이 실행하지 않았다(`--grep-invert`, 이번 변경과 무관). `artifacts/validation/t23/*.png`는 덮어쓰지 않았다(임시 복사본이 scratchpad로 출력).

종료 확인: 직접 띄운 API 8591·Vite 5791 종료, 공유 Neo4j 7687 유지.
