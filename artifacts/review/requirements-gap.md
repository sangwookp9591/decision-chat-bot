# 요구사항 대비 미비·약한 부분 감사 (P2)

> **2026-10-05 후속 상태:** 이 문서는 과거 읽기 전용 감사의 판정 기록을 보존한다. 다음 항목은 현재 worktree에서 해소/정정된 과거 주장으로 읽는다: EvidenceViewer 원문 위치 anchor, 판단 맵 확대/버전 탭, 외부 모델 입력의 패턴 마스킹. 마스킹은 구현·단위시험이 확인됐으나 모든 실송신 경로/민감 유형 실측은 별도 제한이다. CORS는 아직 명시적 미들웨어 정책이 없고 same-origin/Vite proxy 계약을 `docs/operations/DEPENDENCIES.md`에 기록했다. 이번 FIX-DOCS에서 추가한 HTTP 취소 시험 및 기타 갱신은 `artifacts/validation/final/GATE_REPORT.md`의 2026-10-05 부록과 운영/제품 계약 문서를 참조한다.

- 대상: `/Users/psw/Projects/decision-chat-bot`, 커밋 `0da8b1e`, 읽기 전용 감사. 코드·문서·설정은 수정하지 않았다.
- 판정 기준: **(a)** 구현+검증, **(b)** 구현됐으나 해당 동작 검증 증거 없음, **(c)** 부분 구현, **(d)** 미구현. 게이트 보고서에 증거가 명시되면 검증으로 간주하고, 화면 코드 존재만으로 end-to-end 검증이라 간주하지 않았다. GATE_REPORT에 명시된 외부 G10 브라우저 에이전트, G12 현업 정답/품질, G13 30일 운영 요건은 상세 결함으로 반복 기재하지 않았다.
- 근거 기준 문서: `PRD.md` R01–R26 및 화면 표, `docs/spec/01_GOALS_REQUIREMENTS.md`, `02_USER_EXPERIENCE.md`, `04_OBSERVATORY.md`, `08_LEARNING_LOOP.md`, `06_ACCEPTANCE.md`, `docs/architecture/EXECUTION_CONTRACT.md`, `docs/design-handoff/HANDOFF.md`, `docs/design-handoff/source/*.dc.html`, `artifacts/validation/final/GATE_REPORT.md`.

## 기준 문서 위치 색인

| 항목 | 위치 |
|---|---|
| PRD 요구 R01–R18 / R19–R26, 화면 요구 | `PRD.md:103–120` / `PRD.md:121–128`, 화면 `PRD.md:164–173` |
| 필수 기능 문장 | `docs/spec/01_GOALS_REQUIREMENTS.md:18–32`; 사용자 흐름·수정 순환 `docs/spec/02_USER_EXPERIENCE.md:3–58` |
| 관찰·맵·효과 | `docs/spec/04_OBSERVATORY.md:5–45`; 규칙 수명·맵 `docs/spec/08_LEARNING_LOOP.md:33–117` |
| 필수 게이트·시나리오·실패 시나리오 | `docs/spec/06_ACCEPTANCE.md:7–21`, `:23–65`, `:67–95` |
| 실행 계약 검증 문단 | `docs/architecture/EXECUTION_CONTRACT.md:7–24`, `:26–57`, `:59–75`, `:95–115` |
| 핸드오프 화면·상호작용 | `docs/design-handoff/HANDOFF.md:15–45`; 원본은 각 화면 파일 `docs/design-handoff/source/{Main,Review,Tasks,ChatWidget,Observatory,Monitoring,Policy,Foundations,JudgmentMap,Learning}.dc.html` |

## 판정표 — PRD R01–R26

| 항목 | 판정 | 근거 위치 및 판단 |
|---|---|---|
| R01 영속 접수·조회·재시작 | (a) | GATE_REPORT §기존 게이트 G01, `backend/jevtriage/ingest/`, `backend/tests/acceptance/acc_c_g01_restart.py`; 재시작 전후 보존 증거 명시. 새 환경 기동은 mock 제한이 있어 운영환경 이식성은 별도 제약. |
| R02 첨부·원문 위치·오류 안내 | (a) | G02 증거, `backend/jevtriage/ingest/parsers/`, `backend/tests/unit/test_parsers.py`; PDF/DOCX/MD·실패 파일 선택 및 입력 한도. |
| R03 부분 파일 실패·재첨부/제외·이전 결과 보존 | (a) | `frontend/src/pages/Main.tsx` 파일 결정/새 revision 흐름, `backend/tests/acceptance/acc_a_scenarios.py`; G02·G03 증거. |
| R04 핵심 분류·불확실성·버전 | (a) | `backend/jevtriage/judgment/`, G03 실제 Jev 결과 저장 증거. |
| R05 판단별 원문 근거·업무 초안 | (a) | G03, `backend/jevtriage/judgment/evidence.py`, `frontend/src/pages/Main.tsx`; 원문 근거 일부 실행 간 변동(Jaccard ≥0.857, 작은 표본)은 검증 보고서가 밝힌 제한. |
| R06 4종 사람 검토·원안/이력 | (a) | G04 4종 결정·원안 보존·감사·승인 전 배정 0; `frontend/src/pages/Review.tsx`, `backend/tests/integration/test_review_assignment.py`. |
| R07 안전한 단일 배정·중복 방지·팀 업무 | (a) | G05 동시 승인/반복 클릭 중복 0, API=DB=화면; `docs/architecture/EXECUTION_CONTRACT.md` §2. |
| R08 정책 검증·사유·버전·diff·rollback·실행 고정 | (a) | G06 정책 v2→v3→v4 및 과거 불변; `frontend/src/pages/Policy.tsx` 정책 diff/이력/고정 안내. |
| R09 실제 Neo4j 업무 그래프 조회·화면 | (a) | G06·G05 API/화면 대조, `backend/jevtriage/graph/`, `frontend/src/pages/Observatory.tsx`, `Tasks.tsx`. |
| R10 SSE 재연결·누락 보정 | (a) | G08 Last-Event-ID 재개 누락·중복 0, 복구 p95 354.9ms; `backend/tests/integration/test_sse_events.py`. |
| R11 실제 실행 단계·Trace 상세 | (a) | G07 저장 RunStep 노드 상태 대조, `frontend/src/pages/Observatory.tsx` Trace drawer 및 observe API. |
| R12 Playback 저장 기록만 재생·제어 | (a) | G07 성공/대기/실패 및 부작용 불변; `frontend/src/pages/observatory/playback.test.ts`, `backend/jevtriage/observe/playback.py`. |
| R13 관측 집계·필터·Trace·알림 | (a) | G09 알려진 집합 대조, Neo4j 장애 분모 보존·로컬 장애 알림. `Monitoring.tsx` 기간/조직/상태/버전 필터와 알림 목록 있음. 운영 원격 수신은 GATE_REPORT §남은 외부 요건에 남은 항목. |
| R14 WebMCP 조회 도구 | (b) | 제품 도구 3개 및 서버 권한 경유는 구현, 미지원 브라우저 정상. G10 실제 에이전트 호출만 차단(기존 외부 요건이므로 상세 재기재 제외). `frontend/src/webmcp/index.ts`. |
| R15 권한·입력·키·장애 안전 | (a) | G11 tenant/role 404·403, 악성 입력·키 보호 등 증거; 단, GATE_REPORT §남은 제한의 외부 모델 전송 데이터 마스킹 미구현은 P1 위험 항목에 별도 기재. |
| R16 접근성·상태·터치·반응형 | (a) | G04 UI 12/12, G07 및 `frontend/e2e/a11y/a11y.spec.ts`; `frontend/src/style.css` 44px 메뉴/960px 대응, ChatWidget의 reduced motion/Safari 대체 코드. |
| R17 품질·성능 지표 및 표본 | (b) | 성능 30분 부하 실측 완료이나 공식 SSE p95 2000ms 경계, 개선 후 10분 보조측정만 있음. 분류 품질은 기존 G12 외부 요건으로 상세 반복하지 않음. `artifacts/validation/t25/20261003T101333Z/REPORT.md`. |
| R18 게이트·운영 제출물 | (c) | GATE_REPORT 존재, G01–G12 중 G10 차단/G12 미검증이며 G13 미검증. 알려진 외부 잔여 요건은 본 감사 결함 목록에서 제외. |
| R19 Correction 수정 원안 보존 | (a) | X01 DB Correction=화면 대조, extension `scenario-evidence.md`; `backend/jevtriage/learning/corrections.py`. |
| R20 규칙 후보·지지/반례·범위·불확실성 | (a) | X02 통과; 후보 자료 부족 표현 포함. `backend/jevtriage/learning/candidates.py`, `frontend/src/pages/Learning.tsx`. |
| R21 규칙 관리자 권한·상태 결정 | (a) | X03 권한 상태전이·미검증 게시 거절·단건 승인 불변. extension 증거 및 `frontend/src/pages/learning/Actions.tsx`. |
| R22 Config 연결·RuleApplication·불변 조건 | (a) | X05 범위 내/외 기록, Trace=API=DB, 완화 규칙 거절; X07 버전 고정. |
| R23 섀도 검증 무부작용 | (a) | X04 전후 업무/배정/검토/이벤트/포인터 불변; `backend/tests/integration/test_shadow_api.py`. |
| R24 규칙 효과 지표·표본 수 | (b) | X09 API=DB 수치 및 표본 부족 미확정은 검증. 다만 표본 충분한 실데이터 효과 판정 경로는 미시험(통합 시험만)이라고 GATE_REPORT가 명시. |
| R25 실제 판단 관계·권한 경계 | (a) | X06/X08 실제 관계만 렌더, tenant 경계·재시작/새로고침 유지 증거; `backend/jevtriage/graph/`. |
| R26 5계층 판단 맵·양방향 탐색·목록/키보드·연결 | (c) | X06 관계·목록·키보드·양방향 탐색 통과. `JudgmentMap.tsx`에는 맵/목록 전환과 상세가 있으나 HANDOFF 의도인 별도 “크게 보기” 조작/확대 모드가 없음(확인한 컴포넌트·스타일 범위). 버전 탭도 없음; 기준 필터에 config_version은 있으나 상세 패널의 버전 타임라인/탭과는 다름. |

## 필수 문장·화면 의도 추가 대조

| 요구 묶음 | 판정 | 근거 위치 및 판단 |
|---|---|---|
| spec 01 핵심 기능·사용자 경계·고정 정책 | (a) | PRD R01–R18 대응과 G01–G11 증거, `backend/tests/integration/test_auth.py`, `acc_b_safety.py`. 모델 데이터의 외부 전송 마스킹은 구현되지 않았다고 GATE_REPORT가 명시(아래 상세). |
| spec 02 접수→판단→보완→검토→배정 흐름 | (a) | `Main.tsx`, `Review.tsx`, `Tasks.tsx`; G02–G05 증거. |
| spec 02 수정 비교→규칙 수명 순환 | (a) | X01–X08 extension 실연동 증거; 섀도·권한·게시 흐름 존재. |
| spec 04 Flow/Topology/Trace/Playback/실시간 구분 | (a) | G06–G08; `Observatory.tsx`; Playback 부작용 확인. |
| spec 04 모니터링·누락/수집중단·Trace 이동 | (a) | G09 및 `Monitoring.tsx`; 집계·알림 UI와 로컬 장애 주입 증거. |
| spec 04 입체 맵·효과 관찰 | (b) | X06 검증. X09는 표본 부족 경로만 실데이터 검증, 충분 표본 효과 판정은 통합 시험에 한정. |
| spec 08 후보-결정-검증-게시-적용-효과 | (b) | X01–X08 통과. X09 실데이터 충분 표본 효과 확인은 없음. |
| HANDOFF 01 Main: 다중 파일·업로드/분석·결과 카드·원문 | (c) | 파일/진행/카드는 구현+G02/03 검증. `Main.tsx` `openEvidence`는 위치를 제목에 문자열로 표시하고 원문 텍스트를 패널에 띄움; PDF 페이지/문단 위치로 실제 문서를 열어 해당 위치에 스크롤/하이라이트하는 이동 동작은 없음. |
| HANDOFF 02 Review: 4종 결정·원안·충돌·이력 | (a) | G04 UI 12/12 및 G05 동시 승인 증거. |
| HANDOFF 03 Tasks: 팀/역할/방식/상태 필터·선행 | (a) | `Tasks.tsx`에 팀·역할·방식·상태 모두 존재, G05 화면/API/DB 대조. |
| HANDOFF 04 ChatWidget: 결과 아이콘 규칙 | (a) | `ChatWidget.tsx`의 긴급은 빨간 alert만, 검토는 surprised, 결과는 like; `Main.tsx`에서 판단 이벤트 전달. GATE_REPORT는 UI 시나리오 통과. |
| HANDOFF 05 Observatory: 저장 실행 playback·별도 재실행 | (a) | G07 및 `Observatory.tsx`; 재생은 저장 읽기, 별도 “새 실행으로 다시 처리”. |
| HANDOFF 06 Monitoring: KPI/SLO/실패 Trace/알림 | (a) | G09 증거, `Monitoring.tsx`에 알림 목록·필터·Trace 링크 존재. |
| HANDOFF 07 Policy: 검증/diff/버전/rollback/실행 고정 | (a) | G06 증거 및 `Policy.tsx` 실제 diff 렌더링. |
| HANDOFF 08 Foundations 토큰·상태·접근성 | (a) | `frontend/src/styles/tokens.css`, `style.css`, G11 접근성/UI 증거. |
| 화면 09 판단 맵: 다섯 계층·관계·필터·목록·원문 이동 | (c) | X06 통과 및 `JudgmentMap.tsx`, `Detail.tsx`. 관계·목록은 확인됨; 상기 “크게 보기”/버전 탭 미존재. 원문 이동은 상세에서 URL/위치 정보를 볼 수 있지만 원문 뷰어로 실제 이동 여부는 제한적. |
| 화면 10 규칙 학습: 후보/지지반례/권한/검증/게시/효과 | (b) | `Learning.tsx`, `Actions.tsx` 모든 동작 버튼이 상태별 enable/disable 및 사유 표시. X01–X08 통과; 충분 표본 효과는 미검증(X09 제한). |

## 06_ACCEPTANCE 필수 게이트 및 시나리오

| 항목 | 판정 | 근거 위치 및 판단 |
|---|---|---|
| G01 실행·재시작 | (a) | GATE_REPORT G01 및 `acc_c_g01_restart.py`; 신규 환경은 mock 제한을 함께 기록. |
| G02 입력·복수 파일·실패 안내 | (a) | GATE_REPORT G02, parser unit/acceptance. |
| G03 실제 판단·근거 | (a) | GATE_REPORT G03; 근거 일관성 제한 보고. |
| G04 검토 | (a) | GATE_REPORT G04. |
| G05 업무 배정 | (a) | GATE_REPORT G05. |
| G06 정책·그래프 | (a) | GATE_REPORT G06. |
| G07 재생 무부작용 | (a) | GATE_REPORT G07. |
| G08 SSE 재연결 | (a) | GATE_REPORT G08. |
| G09 모니터링·알림 | (a) | GATE_REPORT G09. |
| G10 WebMCP | (b) | 제품 구현 확인, 실제 에이전트 호출 증거는 기존 외부 요건으로 생략. |
| G11 안전 | (a) | GATE_REPORT G11. |
| G12 성능·품질 | (b) | 부하 성능 증거 존재, 공식 SSE 전달 p95 경계/보조 재측정 제한. 품질은 기존 외부 요건. |
| 확장 X01–X08, X10 | (a) | GATE_REPORT extension 최신 실행 통과. |
| X09 충분 표본 효과 관찰 | (b) | GATE_REPORT에 통합 시험만으로 검증했다고 제한 명시. |
| 사용자 시나리오 1–8 (접수·첨부·판단·보완·검토·배정·모니터링·재생) | (a) | `backend/tests/acceptance/acc_a_scenarios.py`, `acc_d_events_monitoring.py`, GATE_REPORT G02–G09; 화면/DB/저장 기록 대조. |
| 실패·예방: 모델 timeout/호출제한/오응답, 파서/저장 오류 | (a) | `backend/tests/fault/scenarios.py`, `backend/tests/acceptance/acc_b_safety.py`, GATE_REPORT G03/G11, fault 11/11. |
| 실패·예방: SSE/서버 재시작/일부 저장소 실패 후 복구 | (a) | `acc_c_g01_restart.py`, `test_sse_events.py`, GATE_REPORT G01/G08 및 fault report. |
| 실패·예방: 타 사용자·조직 ID/권한 없는 결정/WebMCP 권한 | (a) | `acc_b_safety.py`, GATE_REPORT G11 권한 차단 증거; WebMCP 지원 호출 주체 검증만 기존 G10 차단. |
| 실패·예방: 중복·동시 승인·오래된 화면 결정 | (a) | `test_review_assignment.py`, `test_reanalysis_boundary.py`, EXECUTION_CONTRACT §2 검증 및 G05 증거. |
| 실패·예방: 위험·불가·정보부족 자동 배정 금지/정책 필수검토 잠금 | (a) | `test_eligibility_t09.py`, `test_rule_invariants.py`, G05/G11. |
| 실패·예방: 만료 worker A의 지연 쓰기 차단 | (a) | `backend/tests/fault/` 및 GATE_REPORT fault 11/11, EXECUTION_CONTRACT §2. |
| 실패·예방: Neo4j 중단 중 journal 분모·수집 알림·복구 대조 | (a) | G09, `test_monitoring_collector.py`, gate report t22. |
| 실패·예방: 정보 부족 요청의 최초 판단·SLO 시작시각 불변 | (a) | `backend/tests/integration/test_reanalysis_boundary.py`, `acc_a_scenarios.py` 및 GATE_REPORT G03/G09 evidence. |
| 확장 실패: 단건 승인으로 게시 불가, 권한 없는 게시/rollback, 안전 불변 약화 거절 | (a) | extension X03/X05 증거; `test_rule_invariants.py`. |
| 확장 실패: 미검증 규칙 게시·적용/섀도 부작용·버전 고정 | (a) | X04/X05/X07 evidence; `test_shadow_api.py`, `test_rules_integration.py`. |

## 화면 원본별 실제 상호작용 점검 (design-handoff/source)

| 화면 | 판정 | 근거 |
|---|---|---|
| 01 Main | (c) | `Main.tsx` 접수/파일 결정/판단 카드 구현; 근거 열기는 텍스트 패널 중심이고 원문 페이지·문단으로 이동하지 않음. |
| 02 Review | (a) | `Review.tsx`, `Review.test.tsx`, G04 UI evidence. |
| 03 Tasks | (a) | `Tasks.tsx`, `test_tasks_api.py`, G05. 모든 지정 필터 동작. |
| 04 ChatWidget | (a) | `ChatWidget.tsx`; 아이콘·긴급 무마스코트 코드 규칙 확인. |
| 05 Observatory | (a) | `Observatory.tsx`, `playback.test.ts`, G07. |
| 06 Monitoring | (a) | `Monitoring.tsx`, `Monitoring.test.tsx`, G09. 알림 목록 포함. |
| 07 Policy | (a) | `Policy.tsx`, `Policy.test.tsx`, G06; diff/rollback/버전 고정. |
| 08 Foundations | (a) | `style.css`, `tokens.css`, a11y tests 및 G11. |
| 09 JudgmentMap | (c) | `JudgmentMap.tsx`, X06. 데이터 기반 탐색은 통과했으나 “크게 보기” UI 조작은 컴포넌트에 없음. 상세에 버전 필드는 있어도 버전 탭/이력 비교는 없음. |
| 10 Learning | (b) | `Learning.tsx`, `Actions.tsx`, X01–X08; 버튼의 상태/비활성 사유 동작 구현. 충분 표본 실효 검증은 X09 제한. |

## EXECUTION_CONTRACT 검증 문단 대조

| 검증 문단 | 판정 | 근거 |
|---|---|---|
| §1 자동 배정의 정보부족/파일미확정/위험/필수검토 거절과 정상 배정 | (a) | `test_eligibility_t09.py`, G05/G11; 조건별 자동 배정 0 증거. |
| §2 lease 만료 A→B 인계 후 늦은 쓰기 거절, 과거 승인 거절, 동시 승인 단일 배정 | (a) | fault 11/11, `test_review_assignment.py`, G05. |
| §3 DB/journal 장애와 수집기 중단 watchdog 알림·복구 대조 | (a) | G09 로컬 경로 증거, `test_monitoring_collector.py`; 운영 원격 알림은 문서도 별도 운영 조건으로 남김. |
| §4 정보부족 실제 판단 선저장·보완/120초 분모 보존 | (a) | G03/G09 evidence 및 acceptance scenario. |
| §6 WebMCP 실제 브라우저 확인 | (b) | 실제 에이전트 호출 증거만 기존 G10 차단 요건. |
| §8 규칙 권한 전이·안전 규칙 거절·단건 수정 승인 불변 | (a) | X03 evidence, `test_rule_invariants.py`. |
| §8 게시 전후 고정 버전·소유권 원자 커밋·RuleApplication | (a) | X05/X07 evidence, `test_rules_integration.py`. |
| §8 섀도 전후 업무 등 부작용 0·SLO 분리 | (a) | X04 evidence, `test_shadow_api.py`. |
| §8 실제 엔터티 관계/tenant 경계/재시작 후 보존 | (a) | X06/X08 evidence, graph integration tests. |

## (c)·(d) 및 위험 높은 (b) 상세

1. **[심각도 높음] `frontend/src/pages/Main.tsx:122–133`, 근거 원문 페이지·문단 이동 — (c)** — 현재 클릭은 `location`을 제목에 JSON 문자열로 표시하고 `source_text`를 blockquote로 띄운다. 실제 PDF 페이지/문단으로 스크롤·선택·하이라이트하는 문서 뷰어 이동은 코드에서 확인되지 않는다. R02/R05와 HANDOFF Main/Review의 원문 위치 탐색 요구 대비 위치는 표시되지만 탐색 의미가 충족되지 않는다. — 제안: source 종류별 PDF/DOCX/MD 원문 뷰어를 만들고 evidence location에 페이지/문단/행 anchor를 부여해 이동·하이라이트, 권한 거절 상태를 통합 시험한다. — 예상 규모 **M**.
2. **[심각도 중간] `frontend/src/pages/JudgmentMap.tsx:93–121`, 판단 맵 확대·버전 탭 — (c)** — 실제 UI에는 `입체 맵`/`목록 보기`, 필터, 상세만 있으며 디자인 원본 `docs/design-handoff/source/JudgmentMap.dc.html:108`의 확대 조작과 버전 비교 탭은 없다. `config_version` 필터는 한 버전으로 조회하는 기준이지 노드 버전 이력 탭이 아니다. — 제안: 확대/전체보기 버튼(뷰포트 fit/zoom 및 키보드 지원)과 선택 노드의 버전 타임라인/비교 탭 추가. — 예상 규모 **M**.
3. **[심각도 높음] `artifacts/validation/final/GATE_REPORT.md` §남은 제한, 민감 데이터 전송 마스킹 — (d)** — 문서가 “외부 모델 전송 데이터의 마스킹은 구현되지 않았다”고 직접 기록한다. 입력·로그 보호 요구와 연결되고 G11 통과가 전송 본문 비마스킹을 해결하지는 않는다. — 제안: Jev 요청 직전 PII/민감필드 탐지·마스킹 정책을 명시하고 재식별 불가 로그/전송 fixture 및 민감 표본 검증을 추가; 불가 시 민감 원문 전송 차단. — 예상 규모 **L**.
4. **[심각도 중간] R24/X09 충분 표본 효과 관찰 — (b)** — X09는 표본 부족 표시와 API/DB 수치 대조는 통과했지만 충분 표본 데이터가 있는 개선/악화 판정은 실데이터 미시험. — 제안: 알려진 분류 변경·수정·검토전환·실패·지연을 포함하는 fixture cohort를 만들고 각 효과 레이블과 sample count가 API/DB/UI에서 일치하는 실행 증거를 남긴다. — 예상 규모 **S**.
5. **[심각도 중간] R17 성능 경계 여유 — (b)** — 공식 30분 시험의 SSE 전달 p95가 목표 2,000ms 경계이고 개선 뒤 10분 보조 측정 275ms만 있다. 성능 목표 판정은 통과로 기록됐으나 보조 결과로 공식 장시간 시험을 대체할 수 없다. — 제안: 수정 코드/설정 고정 후 동일 공식 30분 부하 시험 재실행, 지연 분포·자원 포화·SSE 동시 연결의 여유폭 기록. — 예상 규모 **M**.
6. **[심각도 중간] G01 새 환경에서 전체 실연동 재현 — (b)** — GATE_REPORT G01은 새 복사본 설치·기동은 mock, 재시작 시나리오는 live라고 구분한다. 이미 운영 제약이나 기능 누락은 아니지만 깨끗한 환경에서 실제 모델까지 연결한 통합 재현 증거는 제한적. — 제안: 깨끗한 OrbStack 기반 복사본에서 live Jev 접수→판단→조회·재시작 재현 결과를 G01 부록으로 남긴다. — 예상 규모 **S**.
7. **[심각도 낮음] G03 원문 근거 안정성 — (b)** — GATE_REPORT G03은 작은 표본에서 실행별 인용 Jaccard ≥0.857을 보고한다. 기능·근거 저장은 통과했지만 동일 입력 재실행에서 근거 선택이 일부 변동한다. — 제안: 질문별 반복 실행 표본을 늘려 위치/인용 정확도를 평가하고 낮은 안정성은 검토 전환 또는 근거 신뢰도 표시 기준에 반영한다. — 예상 규모 **M**.

## 우선순위 상위 10

| 순위 | 항목 | 이유 | 우선 조치 |
|---:|---|---|---|
| 1 | 민감 데이터 외부 모델 전송 마스킹 (R15) | Gate report가 명시한 실제 보호 공백, 민감 실데이터 시연 위험 | 마스킹/전송 차단 설계와 검증 |
| 2 | 원문 근거의 페이지·문단 실제 이동 (R02/R05, 화면 01/02/09) | 화면에 근거 위치 문자열만 보여주는 것은 검토자가 원문 맥락을 재확인하는 핵심 동작을 완성하지 못함 | anchor 기반 원문 viewer 구현 |
| 3 | 판단 맵 “크게 보기”·버전 탭 (R26, 화면 09) | 핸드오프에 명시된 탐색 조작 누락 | 확대/fit, 버전 이력·비교 UI 구현 |
| 4 | X09 표본 충분 효과 판정 실데이터 대조 (R24) | 효과 분류가 실제 알려진 입력에서 맞는지 미검증 | controlled cohort로 DB/API/UI 대조 |
| 5 | 공식 30분 성능 시험 재실행 (R17/G12 성능) | 공식 p95가 경계에 있고 개선 후 시험은 10분 | 같은 조건으로 30분 재측정 |
| 6 | 깨끗한 환경 live Jev E2E 증거 (R01/G01) | 새 환경 기동 증거의 mock 제한 | live 접수부터 재시작까지 재현 |
| 7 | 근거 선택 반복 안정성 (R05/G03) | 작은 표본에서 인용 변동 확인 | 반복 표본 평가·검토 전환 기준 |
| 8 | R18 완료 판정 취합 | 구현/검증은 많이 갖췄으나 차단·미검증 게이트 존재 | 모든 게이트 증거 링크/상태 자동 인덱스 유지 |
| 9 | R13 운영 알림의 배포 수신 경로 | 로컬 독립 watchdog까지 검증; 외부 요건 G13 제외 후에도 운영화 연결이 남음 | 배포 수신기·원격 경로 준비 시 인수 검증 |
| 10 | R02 원문 anchor 권한/파일종류 일관성 | 원문 링크 추가 시 tenant/조직 접근 통제가 UI에서 우회되지 않도록 해야 함 | backend evidence endpoint와 viewer 통합 보안 시험 |

## 범위 및 한계

- 감사는 읽기 전용 코드·문서 grep/열람으로 수행했고 시험을 새로 실행하지 않았다. 보고서 파일 `artifacts/review/requirements-gap.md`만 생성했다.
- `GATE_REPORT.md`는 판정 기준 커밋 `e55b42d`와 미커밋 작업 트리를 가리키고, 이번 감사 worktree는 `0da8b1e`다. 따라서 문서의 최신 증거는 현재 커밋과 완전히 같은 스냅샷이라고 보장되지 않는다. 코드 인용은 현 worktree에서 직접 확인했고 이 시점 차이를 불확실성으로 남긴다.

## 2026-10-05 항목 상태 정정

| 과거 P2 잔여 주장 | 최신 상태 |
| --- | --- |
| R02 원문 anchor 기능 부재 | **해소된 과거 주장** — EvidenceViewer의 unit anchor·스크롤 구현 및 UI 시험이 있다. 권한은 API 경계와 별도 시험으로 확인한다. |
| 판단 맵 확대/버전별 보기 미구현 | **해소된 과거 주장** — 확대/목록 및 버전 탭 구현과 UI 시험이 있다. |
| 외부 모델 송신 마스킹 미구현 | **해소된 과거 주장** — 패턴 마스킹과 단위 시험이 있다. 모든 민감 유형/실제 송신 경로 실측은 별도 미완료다. |
| 취소 API HTTP 경계 검증 부재 | **해소** — `backend/tests/integration/test_cancel_http.py` 추가, 2 passed; session/CSRF/role/tenant 응답 경계를 확인했다. |
| 전체 e2e 데이터 fixture 고정 | **부분** — 30건 chat 목록, rem-ui 제목/결과, acceptance 별도 계정, X38 db_truth 사전조건에 명확한 skip을 추가했다. 스크린샷 기반 전용 fixture를 자동 생성하는 대신 표본이 없으면 skip한다. |
| CORS 경계 문서 부재 | **문서화** — 현재 same-origin/Vite proxy 계약과 별도 origin 배치 시 필요한 allowlist 정책은 `docs/operations/DEPENDENCIES.md`에 기재. CORS middleware는 미구현이며 지금 API는 cross-origin 허용을 보내지 않는다. |

Trace drawer 상세, 지정 조건 browser 성능 측정, 현업 final 평가, live G10, G13 운영 SLO 등은 잔여이며 최신 판정 부록에 미해결로 남겼다.
