# FIX-P7 — P7 결함 F2·F3·F4·F5·F6 수정 결과 (UX-6)

- 일시: 2026-10-04. 기준: VERIFY-P7.md F2–F6. 수정 범위는 `frontend/**`뿐(백엔드 무변경). 커밋은 하지 않았다.
- 순서: 재현 시험 작성 → 수정 전 실패 확인 → 수정 → 통과. F2의 "수정 전 실패"는 vitest에서 확인했다(아래 표). 수정 전 라이브 브라우저 재현은 VERIFY-P7의 기록을 그대로 근거로 쓰며 이번에 다시 하지 않았다(공유 worktree라 stash/되돌리기를 하지 않음).

## 결과 표

| 항목 | 재현 시험(수정 전) | 수정 | 수정 후 검증 |
|---|---|---|---|
| F2 정책 덮어쓰기 | `Policy.test.tsx` 3건 실패: ① 과거 이벤트(v1·v2, 활성 v2) 후 active 재조회·입력값 소실 ② 편집 중 새 버전이 입력을 덮어씀 ③ 늦은 옛 응답이 새 응답을 덮음. (편집 없음 + 새 버전 자동 재조회는 원래 통과) | `Policy.tsx`: payload `version` ≤ 활성 버전이면 무시, 첫 조회 전 이벤트 무시, 조회 세대 번호 검사, dirty면 '새 버전 vN이 게시되었습니다 — 새 버전 반영 / 내 편집 유지' 알림, 검증·게시는 ref에 둔 draft snapshot 사용 | vitest 통과; 라이브 `p7-fixes F2`: 새 context 3회 반복, 입력 `{"ai_need":1.5}`가 그대로 전송·검증 오류 응답(Chromium·WebKit 통과) |
| F3 모니터링 | `Monitoring.test.tsx` 3건·`api/monitoring.test.ts` 1건 실패(제목·필터 즉시 렌더, 영역 독립, 실패 격리, 200ms 미만 미표시, 중복 요청 제거) | `Monitoring.tsx`: 제목·필터 즉시, 4개 요청을 `useArea`로 독립 반영, 최종 모양 스켈레톤(200ms 지연), 영역별 오류, `api/monitoring.ts`: 같은 URL의 진행 중 GET 합치기(캐시 없음) | vitest 통과; 라이브: summary를 4초 지연시켜도 1초 안에 제목·필터, 3초 안에 SLO 영역 표시, KPI 영역만 `aria-busy` 유지(Chromium·WebKit) |
| F4 목록 | `Main.list.test.tsx` 2건 실패(선택 요청이 없을 때 tenant 스트림 구독 없음, 목록 미갱신) | `Main.tsx`: 필터 없는 tenant 스트림 추가, 목록 관련 이벤트 8종을 400ms debounce해 `GET /api/requests`만 재호출, 열린 상세는 재조회하지 않음 | vitest 통과(버스트 4건 → 재조회 1회, 상세 호출 불변); 라이브: 탭 B(선택 없음)가 탭 A의 새 요청을 8초 안에 새로고침 없이 표시(Chromium·WebKit) |
| F5 잠정→최종 | `Main.progressive.test.tsx` 4건 실패(영역 순서, 제출 카드 유지, 요약 슬롯 선점, 건수/열람 구분) | `ProgressivePanel.tsx`·`Main.tsx`·`main.css`: 두 컴포넌트가 `summary → judgment → tasks` 영역을 같은 슬롯·최소 높이로 렌더, 제출 카드 유지, 요약 카드를 잠정 단계부터 배치, 근거 N건 연결됨(건수)과 '원문 열람은 최종 저장 후 가능'(열람 상태) 분리 | vitest 통과; 라이브 CLS 시험(`p7-fixes F5`, Chromium): 잠정 카드 이후 layout-shift 합 **0.00001**(P7 관측 0.0135–0.0335). WebKit은 API 미지원이라 시험 건너뜀 |
| F6 한국어 | `Evaluation.test.tsx` 1건 실패, `Policy.test.tsx` 한국어 필드 시험 | `lib/labels.ts`에 `policyFieldInfo`(이름+짧은 설명)·`evaluationFieldInfo`·`consensusLabel`; `Policy.tsx`·`Evaluation.tsx`는 한국어 이름·설명, 내부 키·원 합의 코드는 접힌 '기술 상세'에만 | vitest 통과; 라이브: 정책·평가 화면 본문에 내부 키 0건(details·input·code 제외), Chromium·WebKit 통과 |

## 검증 결과

- `npm run typecheck` 통과, `npm run test` 28 파일 145건 통과, `npm run build` 통과.
- `backend/.venv/bin/pytest -q` 457 passed, 1 skipped; `ruff check jevtriage tests` 0건(백엔드는 이번 작업에서 수정하지 않음).
- 환경: API 8891, vite 6191(`vite.e2e.config.ts`), `--tenant t-alpha --tenant t-beta --tenant t-t23` worker, `JEV_MODE=live`, OrbStack 공유 Neo4j·Redis. 시험 후 내가 띄운 세 프로세스만 종료했고 7687은 건드리지 않았다.
- 새 라이브 시험 `e2e/p7-fixes.spec.ts`: Chromium 5/5, WebKit 4/4(F5 건너뜀).
- 기존 e2e 회귀(`--workers=1`, 양 브라우저): policy·monitoring·main·progressive-results·evaluation-labels·responsive-overflow(375/520) 통과. `policy.spec.ts`는 라벨 변경(`선택형 판단 최소 확신도`)과, 버전이 10개를 넘으면 `name:'v1'`이 부분 일치로 깨지는 기존 취약점(`exact: true`)을 함께 고쳤다.
- a11y(`playwright.a11y.config.ts --workers=1`, 포트 6291): Chromium·WebKit 12/12 통과. 처음 실행은 worker가 `t-t23`을 처리하지 않아 키보드 제출 시험 2건이 시간 초과였고, worker에 `t-t23`을 추가해 재실행하니 통과했다.
- **t23 PNG**: `A11Y_SHOT_DIR`를 지정하지 않고 첫 a11y 실행을 해서 `artifacts/validation/t23/{chromium,webkit}-responsive-520.png`가 덮어쓰였으나, 바로 `git checkout`으로 HEAD 상태로 복원했다. 현재 `git status`에 t23 변경 없음.

## 건너뜀·한계

- WebKit F5 CLS는 `layout-shift` 미지원이라 측정하지 못했다. 구조(영역 순서·슬롯)는 vitest로 양 엔진 공통 검증이다.
- F3의 서버 쪽 집계 비용(summary/slo/failures 겹침)은 MON-PERF 담당이라 손대지 않았다. 이번 수정은 화면이 느린 집계를 기다리지 않게 하는 것까지다.
- F2 라이브 시험은 재생 이벤트가 있는 t-alpha 정책 이력에 의존하며, 편집 중 새 버전 알림은 라이브가 아닌 vitest로만 검증했다(다른 사용자의 게시가 필요).
- 공유 DB: 기존 `policy.spec.ts`가 t-alpha 정책 버전을 몇 개 더 만들었고(시험 설계상 게시·되돌리기), 새 요청 몇 건이 생성됐다.
- 변경 파일: `frontend/src/{api/monitoring.ts, lib/labels.ts, pages/{Policy,Monitoring,Main,Evaluation}.tsx, pages/main/{ProgressivePanel.tsx,main.css}, pages/{policy,monitoring}/*.css}`, 시험 `src/api/monitoring.test.ts`·`src/pages/{Main.list,Main.progressive,Monitoring,Policy,Evaluation}.test.tsx`·`e2e/{p7-fixes,policy}.spec.ts`, 문서 `docs/architecture/{PROGRESSIVE_RESULTS,EVENTS}.md`.
