# 일동이 TASK

> **2026-10-05 검토 정정:** 표의 완료 기록과 당시 시험 수치는 작업 당시 스냅샷이다. 취소 API는 현재 HTTP 인증·CSRF·역할·tenant 경계 시험이 `backend/tests/integration/test_cancel_http.py`에 추가됐고, 구현 외 기능 계약은 `docs/architecture/PRODUCT_BEHAVIOR_CONTRACTS.md`에 정리했다. SPEC_TRACE가 지적한 GATE 수치/범위와 해소된 과거 잔여 주장은 `artifacts/validation/final/GATE_REPORT.md`의 최신 판정 부록 및 `artifacts/review/requirements-gap.md`의 후속 상태를 참고한다. 미정 Trace drawer 항목 등 미해결 요구는 완료로 승격하지 않는다.

작성일: 2026-10-03 (Asia/Seoul) · 버전: 0.3 · 상태: 구현·검증 수행, 최종 판정은 [GATE_REPORT](artifacts/validation/final/GATE_REPORT.md)(개발 완료 미선언 — G10 차단·G12 품질 미검증·G13 운영 미검증)

제품 계약은 [PRD](PRD.md), 원본 완료 조건은 [06_ACCEPTANCE](docs/spec/06_ACCEPTANCE.md)다. 이 목록은 실행 순서·의존성·완료 증거를 정하며 제품 구현 완료를 표시하지 않는다. 담당은 구현 책임 영역이며 사람/에이전트의 실제 배정이나 외부 조직에 대한 요청 발송을 뜻하지 않는다.

필수 기술 계약은 [실행·배정·관측 계약](docs/architecture/EXECUTION_CONTRACT.md)을 따른다. 설계 수정 상태와 아래 작업의 구현/시험 상태는 별도다.

확장 설계 기준은 [08_LEARNING_LOOP](docs/spec/08_LEARNING_LOOP.md)이며 구현·시험은 아직 수행하지 않았다.

## 1. 상태와 완료 규칙

- `준비`: 선행 작업 없이 착수 가능. `대기`: 선행 작업 완료 후 착수. `진행`: 실제 수행 중. `차단`: 외부 요건으로 해당 부분 진행 불가. `완료`: 명시된 산출물·검증 증거를 충족.
- 2026-10-03 기준 각 작업의 상태와 증거는 아래 표에 있다. 게이트 판정은 [최종 판정 보고서](artifacts/validation/final/GATE_REPORT.md)를 따르며, '완료' 작업이 있어도 개발 완료(G01–G12)는 선언하지 않았다.
- 구현 작업 완료는 관련 회귀 시험, 실제 저장/조회 또는 UI 동작, 오류·권한 경로와 증거를 함께 요구한다.
- 테스트 대역은 격리된 장애·회귀 시험에서 사용할 수 있지만 실제 Decision AI·Neo4j·WebMCP 게이트를 대체하지 않는다.
- 날짜·소요시간·성능·정답률·키 유효성을 추정해 완료 처리하지 않는다. 각 작업을 끝낼 때 이 표의 상태 및 증거를 갱신한다.

## 2. 구현 기본 방향

| 영역 | 준비 단계 결정 | 검증/변경 지점 |
| --- | --- | --- |
| 백엔드 | Python 3.12, FastAPI, 비동기 Decision AI/Neo4j 어댑터 | T01에서 패키지·lock·명령 고정 |
| 프런트엔드 | React + TypeScript + Vite, 기존 CSS 토큰·에셋 재사용 | 정적 템플릿 로직을 실제 API·상태로 교체; T01 빌드 검증 |
| 영속 데이터 | 첫 버전은 Neo4j를 요청·판단·검토·업무·정책·실행/이벤트의 기준 저장소로 사용 | T04 트랜잭션/락/제약·동시 승인·읽기 성능 확인; 두 번째 저장소 추가 시 복구/정합성 증거 필수 |
| 독립 관측 | Neo4j 외부의 영속 append-only journal + 수집기 + 별도 watchdog; 수신/종료·유효성·오류·지연을 attempt ID로 대조 | T04 계약, T06/T08 계측, T18 집계/수집 장애 알림, T22 DB·수집기 별도 장애 주입; 업무 재실행 용도로 사용 금지 |
| 원본 파일 | 로컬 영속 디렉터리 + Neo4j 메타데이터·해시·권한 | T07에서 임시 파일→확정 및 중단 후 정리/복구; 운영 객체 저장소는 별도 결정 |
| 작업 실행 | 영속 Job + 별도 worker, lease/heartbeat + 단조 generation 및 쓰기 시 소유권 검증 | T08 인계 후 과거 worker 쓰기 거절·재시작 복구; 외부 모델 호출의 정확히 한 번 실행을 보장한다고 주장하지 않음 |
| 이벤트 | 커밋된 이벤트 시퀀스 + SSE 재연결·상태 스냅샷 | T14 Last-Event-ID·중복·역순·누락 검증 |
| 인증 | 서버 세션 기반 역할·조직 경계, 개발 시험 계정과 운영 인증 분리 | T05 CSRF/쿠키·조직 공유 범위, T26 운영 공급자 설정 |
| 모델 | Decision AI는 구조화된 판단만 수행; 요약/업무 분해 별도 | T02 실제 응답 계약; T03 근거 기반 분해 방식과 생성 모델 필요성 결정 |
| WebMCP | M0/T00에서 실제 지원 브라우저·호출 환경 사전 확인 | 최소 읽기 도구 실제 호출 후 T20 제품 통합; 환경 미확보 시 해당 항목 차단 표시 |
| 판단 관계/규칙 | Neo4j 노드·관계에 판단·규칙 수명 기록, RuleVersion을 Config 버전에 연결 | T29에서 제약·경로 질의 확정; 게시/중단/되돌리기마다 새 Config 버전, 기존 기록 불변 |
| 입체 판단 맵 렌더링 | DOM 노드 + CSS 3D + SVG 연결선, d3-zoom류 확대/이동, 목록 보기 대체 | T37에서 접근성·성능 검증; WebGL은 DOM 한계를 넘는다는 측정 근거가 있을 때 검토 |
| 검증 | pytest API/서비스/통합 + 브라우저 E2E + 부하/평가 | 실행 명령·표본·증거 파일은 구현 시 만들고 실행한 결과만 기록 |

Neo4j에서 큰 원문/응답을 저장하는 형식과 제한은 T04에서 정한다. JSON 문자열로 저장할 필드와 노드/관계로 질의할 필드를 구분한다. 모든 객체에 조직 범위, 실행 revision, 생성 주체 및 감사 식별자를 적용한다. 승인 대상은 request/input revision/run/초안/검토 버전이며, 요청 잠금·대상 일치·유일성을 확인하고 승인·업무/관계·감사·이벤트를 단일 트랜잭션으로 저장한다. 자동 배정 조건과 필수 검토는 [실행 계약 1절](docs/architecture/EXECUTION_CONTRACT.md#1-자동-배정과-필수-검토)을 공통 적용한다. 작업 선행 관계는 순환과 다른 조직 업무의 무권한 연결을 거절한다.

## 3. 단계와 첫 실행 순서

| 단계 | 목표 | 진입 작업 | 종료 기준 |
| --- | --- | --- | --- |
| M0 계약·기반 | 실행 구조, 모델·브라우저 계약, 저장·권한·관측 설계 | T00–T05 | 실제 WebMCP 호환성 사전 확인, 빌드/기본 테스트 가능, 불변 조건과 모델 연동 방식 확정 |
| M1 접수→판단 | 텍스트·파일→실제 Decision AI→저장된 결과 | T06–T10 | 원문 근거와 버전이 있는 결과, 보완·실패·재시작 경로 동작 |
| M2 검토→업무 | 승인·수정·반려·정보 요청, 중복 없는 배정 | T11–T13 | 역할별 검토와 업무/그래프 조회, 동시 승인 안전성 |
| M3 실시간·관찰 | SSE, 정책, Flow/Topology/Playback, 모니터링, WebMCP | T14–T20 | 저장 상태와 화면·집계·재생·도구의 일치 |
| M4 인수 | 보안·장애·사용성·품질·부하·복구 | T21–T27 | G01–G12 실제 증거 확보 |
| M5 운영 | 배포 후 실제 관측 | T28 | 연속 30일 G13 판정 |
| M6 확장 | 수정 경험의 규칙화와 입체 판단 맵 | T29–T38 | X01–X10 실제 증거 확보 |

M6은 M2/M3 기반 위에서 진행한다. 단, T29의 모델 설계는 T04와 함께 미리 반영할 수 있다.

바로 시작할 작업은 **T00 브라우저 확인과 T01 → T04·T05 및 T02·T03 조사**다. API 또는 브라우저 환경이 막힌 동안에도 앱 기반·도메인/권한·파서·디자인 컴포넌트 준비는 진행할 수 있다. T10/G03은 T02, T20/G10은 T00과 실제 제품 연동 통과 전 완료하지 않는다. M0의 차단을 숨기지 않고 독립 작업만 계속한다.

## 4. 작업 목록

### M0 — 계약과 기반

| ID | 작업·담당 | 선행 | 상태 | 산출물과 완료 기준 | PRD / 게이트 |
| --- | --- | --- | --- | --- | --- |
| T00 | WebMCP 호환성 사전 확인 · 프런트/환경 | 없음 | 차단 | 공식 초안·실제 브라우저/버전/설정/호출 주체, 최소 읽기 도구 등록·실제 실행 증거 및 미지원 브라우저 기본 페이지; JS 모의 객체/서버 MCP로 대체 금지. 환경 미확보 시 차단 기록 | R14 / G10 사전 조건 |
| T01 | 실행 가능한 프로젝트 구성 · 공통 | 없음 | 완료 | `artifacts/validation/t01/README.md`: 새 venv+pip lock 설치, Neo4j readiness 200/중지 503, pytest 3·Vitest 1 통과, Ruff·TypeScript·Vite build 통과. 재설치·mock 접수/조회 재실행: `artifacts/validation/t01-rerun/README.md` (백엔드 135 통과·1 skip, Vitest 37 통과, lint 2건은 동작 영향 가능성으로 보고) | R01, R18 / G01 |
| T02 | Decision AI 계약·실연동 확인 · 백엔드 | 없음 | 완료 | 공식 typesafe-sdk 버전 고정, AI_API_KEY 명시 전달, 모델 목록 조회 및 비민감 한국어 입력 1건 실제 판단; model/answers/usage와 Choice/Score/Noul 검증, 응답 모델 버전 기록; 키 미출력 | R04 / G03 |
| T03 | 요약·근거·업무 분해 기술 조사 · AI/백엔드 | 없음 | 완료 | 원문 span 식별/검증, 요청에 맞는 가변 업무 분해 방법, 작성 주체 기록; Decision AI에 텍스트 생성을 기대하지 않음. 생성 모델이 필요하면 공급자/모델/전송 데이터/추가 설정/평가를 결정하고 결정을 문서화; 예시 문장 고정 분해로 통과 금지 | R05, R15 / G03, G11 |
| T04 | 데이터·전이·트랜잭션·관측 기반 · 백엔드 | T01 | 완료 | 도메인 모델·조직 scope·제약·색인, 최신 run/초안 결합과 요청당 배정 유일성, generation/lease 쓰기 검증; 독립 journal 원자 append/회전/재시작 기반과 실제 Neo4j 잠금·충돌 시험. 증거: `docs/architecture/DATA_MODEL.md`; 스키마 2회 적용 성공; `NEO4J_PASSWORD=development-only .venv/bin/pytest -q --tb=short`(backend) 23 통과·1 건너뜀; 동시 배정 20개·이벤트 20개·다중 프로세스 journal 100개 확인. | R01, R07–R11, R13 / G01, G05–G09 |
| T05 | 인증·역할·조직 접근 기반 · 백엔드 | T01 | 완료 — 역할·조직 직접 호출 차단은 T21 acc_b(404 56건·403)로 검증; 운영 인증 공급자는 T26 미검증 | `backend/ildongi/auth/`, `scripts/bootstrap_dev.py`, `docs/architecture/AUTH.md`; 실제 Neo4j 로그인·12h 세션 만료·CSRF 거절·로그아웃·tenant/원문 정책 시험 2개 통과, 전체 `cd backend && .venv/bin/pytest -q` 25 통과·1 건너뜀, Ruff 통과. 남음: 각 역할별 쓰기/API 직접 접근 검증과 운영 공급자 통합(T26). | R15 / G11 |

T02 증거: `docs/architecture/AI_CONTRACT.md`, `scripts/ai_probe.py`, `artifacts/validation/t02/response-20261003T070311Z.json`. `typesafe-sdk 0.7.2`로 모델 목록·한국어 판단 성공, 반환 모델 `jev-1.13.0`; 오류 경로 401/422 확인. 429/529/timeout과 제품 통합은 미확인(T09/T10에서 수행).

### M1 — 접수와 판단

| ID | 작업·담당 | 선행 | 상태 | 산출물과 완료 기준 | PRD / 게이트 |
| --- | --- | --- | --- | --- | --- |
| T06 | 접수·조회·보완 API · 백엔드 | T04, T05 | 완료 | 텍스트/multipart 접수·revision·조회·멱등·재시작 보존; DB 저장 전 attempt 수신 및 완료/실패 계측, 최초 수신·최초 지원 revision 고정. 실제 HTTP 라우터 통합시험에서 로그인 세션·CSRF 403·역할 403·교차 tenant 단건 404/목록 비노출·원문 권한 404·Idempotency 동일 payload 재사용/다른 payload 409·stale revision 409·PDF/DOCX/MD 위치 근거 저장·손상 파일 대기→제외 새 revision과 Job 확인. DB write 오류 주입은 POST 503 및 같은 attempt의 수신/실패 journal(error_class·duration) 확인. `make up && cd backend && .venv/bin/pytest -q --tb=short`: 55 passed, 1 skipped; `backend/tests/integration/test_ingest_api.py` 인수시험 포함. | R01, R03, R13 / G01, G02, G09 |
| T07 | PDF/DOCX/MD 파서와 파일 안전 · 백엔드 | T04, T05 | 완료 | `docs/architecture/PARSERS.md`; PDF/DOCX/MD 추출·위치, 제한·spawn 자원 격리, tenant 파일 원자 저장/임시 정리 구현. `cd backend && .venv/bin/pytest -q tests/unit/test_parsers.py` 통과 7/7; `.venv/bin/ruff check backend/ildongi/ingest backend/tests/unit/test_parsers.py` 통과. OS별 메모리 제한 동작은 추가 운영 검증 필요; FIX-B에 첨부 6개 및 합계 초과 ingest HTTP 시험 추가(통합 ingest 시험 포함 전체 backend pytest에서 관련 거절 경로 통과) | R02, R03, R15 / G02, G11 |
| T08 | 영속 실행 worker와 Trace · 백엔드 | T04, T06 | 완료 | `docs/architecture/WORKER.md`; lease 인계·heartbeat 중단·소유권/active_run 검증·고정 버전·attempt/Trace/journal·재시작/기한 초과 구현. 실제 Neo4j 통합 시험 4건(인계 후 구 worker 단계/이벤트/heartbeat 거절, 구 실행 포인터 거절, 재시작·기한 초과, 폴링/사람 대기) 통과. `cd backend && .venv/bin/pytest -q --tb=short`: 29 통과·1 건너뜀; 담당 범위 Ruff 통과. FIX-B에 --tenant 반복 인자/WORKER_TENANTS 제한과 WORKER.md 테스트 격리 지침 추가; tenant allowlist 실 DB 시험 통과. 제품 판단 핸들러 연결은 T09 담당 | R01, R10, R11, R13 / G01, G07–G09 |
| T09 | 판단·근거·업무 초안 서비스 · AI/백엔드 | T02, T03, T07, T08 | 완료 | judgment worker·Neo4j 원안/질문별 ModelOutput·CITES·초안·Review·조회 API, 정책 고정·실패 상태·보수적 자동 배정 게이트 구현. `make up`, `make test`: 백엔드 69 통과·1 skip, 프런트 9 통과; 담당 Ruff 통과. 실제 Decision AI live 저장 ID `artifacts/validation/t09/live-smoke.json` (`mode=live`). 429/529/timeout 실서비스 장애 강제 재현과 분류 품질 평가는 후속 검증 | R04, R05, R07, R15 / G03, G05, G11 |
| T10 | Main·ChatWidget 및 첫 실연동 통합 · 프런트/통합 | T06, T07, T09 | 완료 — live UI 시나리오 S1·S5·S7 통과(`artifacts/validation/t21/20261003t121902z-86519`) | Main 접수/첨부/업로드·SSE 분석 진행·결과/근거 패널·revision/재첨부·이전 실행 결과 비교, ChatWidget 연결·상태 아이콘, run.step 이벤트 연결. `make up && make test`: 백엔드 93 통과·1 건너뜀, 프런트 vitest 11 통과. `npx playwright test e2e/main.spec.ts` (AI_MODE=live, 실제 API·worker): 2 통과. `npx vite build`: 통과. `npm run typecheck`는 Review.test.tsx의 미사용 waitFor 오류로 실패(T13 범위). 인계 시험은 새 run.step 이벤트를 확인하도록 기대값을 갱신. live Decision AI 출력은 원문 인용 0건이어서 위치 없음으로 표시 | R02–R05, R16 / G02, G03 |

### M2 — 검토와 업무

| ID | 작업·담당 | 선행 | 상태 | 산출물과 완료 기준 | PRD / 게이트 |
| --- | --- | --- | --- | --- | --- |
| T11 | 검토·배정·감사 단일 트랜잭션 · 백엔드 | T09, T05 | 완료 (증거: Neo4j 검토·정책 18건 통과; 전체 88통과·1실패는 T08 worker 이벤트 기대값) | 4종 검토·원안 보존, 정확한 revision/run/초안/검토 버전 잠금 검증; T30을 위한 트랜잭션 내 Correction 생성 연결; 승인 또는 조건 충족 자동 배정→업무·HAS_TASK/ASSIGNED_TO/PRECEDES·감사·이벤트 원자 생성, 순환 거절; T12 없이 실제 DB로 과거 승인 거절·동시/반복/retry 배정 중복0 시험 | R06, R07, R09 / G04–G06, G11 |
| T12 | 배정 업무·팀·선행 조회/상태 API · 백엔드 | T11 | 완료 — 업무 API·전이·막힘 + live UI S2·G05(`t21`, `t21-gates/20261003T113332Z`) | T11이 생성한 업무·팀·관계의 조회·필터·권한·상태 변경, T37 입체 판단 맵 링크와 같은 식별자 연결, 선행 막힘/해제·본업무 전제 보존; 배정 생성 책임은 T11, 재분석으로 기존 업무를 자동 변경하지 않음 | R07, R09 / G05, G06 |
| T13 | Review·Tasks 화면 · 프런트 | T10, T11, T12 | 완료 — Review·Tasks live E2E S2·S6, 오래된 결정 409(`t21`), 접근성 T23 | AI 원안 vs 최종 검토, 4종 결정·담당 변경·동시 충돌·감사, 조직/역할/방식/상태 필터, 선행 막힘과 검토 대기/시스템 실패 분리; 역할별 E2E | R06, R07, R16 / G04, G05 |

### M3 — 실시간과 관찰

| ID | 작업·담당 | 선행 | 상태 | 산출물과 완료 기준 | PRD / 게이트 |
| --- | --- | --- | --- | --- | --- |
| T14 | SSE 계약·복구·UI 연결 · 공통 | T08, T10, T13 | 완료 — SSE 재개·누락0(T21 G08), 부하 중 복구 p95 354.9ms(T25), 공유 폴링 개선 보조 측정 p95 275ms(`t25-sse/20261003T110513Z`) | T14-B 백엔드 계약에 대해 `frontend/src/state/events.ts` UI 연결 구현: 쿠키 EventSource, Last-Event-ID 자동 재개, snapshot-required 후 snapshot 조회·재연결, seq 중복/역순 무시, 연결 상태 표시. Vitest SSE 순서 검사 1 통과; 장애 주입 복구시간 측정과 서버 policy/rule tenant 이벤트·SAFE_PAYLOAD_FIELDS SSE 시험 포함 통합 시험 통과 FIX-SSE: tenant별 공유 폴러·배치 Request 메타 조회와 연결별 권한 필터, 역순/중복 없는 다중 연결 시험; SSE 통합 4통과·전체 백엔드 135통과/1건너뜀. 보조 측정 `artifacts/validation/t25-sse/20261003T110513Z/REPORT.md` 참조 | R10 / G08 |
| T15 | Dynamic Config API·버전·rollback · 백엔드 | T04, T05, T09 | 완료 — 버전·diff·rollback·불변 조건, 실행별 버전 고정(G06 `t21-gates/20261003T113332Z`, T22 정책 도중 변경) | API·정책 스키마·불변조건·Neo4j 버전/감사/이벤트·bootstrap·정책 계약 추가. `make up`, `cd backend && .venv/bin/pytest tests/integration/test_policy_versions.py -q`: 4 통과; `ruff check` 통과. `make test`는 `tests/unit/test_eval_metrics.py`의 `ModuleNotFoundError: eval` 수집 오류로 차단; worker Run snapshot 연결은 T09 연동 대기 | R08 / G06, G11 |
| T16 | Policy 화면 · 프런트 | T15, T10 | 완료 | `frontend/src/pages/Policy.tsx` 활성/이력·diff·JSON 필드 편집·서버 검증·사유 게시·409 갱신 안내·되돌리기·잠금/읽기전용 권한 적용. Vitest diff·409 포함 2 통과; `cd frontend && npm run e2e`: 실 Neo4j/API policy_editor 로그인→검증 오류→게시→이력→v1 되돌리기 새 버전 생성 1 통과; 전체 `make test`: 백엔드 63 통과·1 건너뜀, 프런트 9 통과. 실행 버전 고정 전후 비교는 별도 worker/API 검증에 의존 | R08, R16 / G06 |
| T17 | Flow·Topology·Trace·Playback · 공통 | T08, T12, T14 | 완료 — Flow·Topology·Trace·Playback live S8, Play 무부작용, 규칙 적용 상세(FIX-O, X05 재실행) | 백엔드 API 초안: 인증·can_view_request 보호 Flow/Topology/Trace/Playback 라우터, 실제 RunStep·Review 기반 조회, 병렬 predecessor와 HAS_TASK/ASSIGNED_TO/PRECEDES 실제 관계, service 집계 및 읽기 전용 playback. `make up`, `cd backend && .venv/bin/ruff check ildongi/observe tests/integration/test_observe_api.py`: 통과; `.venv/bin/pytest`: 69 통과·1 실패·1 skip (기존 test_worker takeover의 Event 기대값이 현재 run.step 이벤트와 불일치; observe 통합 시험 통과). UI, API 권한 E2E, playback 불변 카운트 assertion, Review 결정/원문 link의 실제 영속화 및 full UX 남음 | R09, R11, R12, R16, R26 / G07, X06  T17-F 관측 보강: Observatory UI·SSE·playback 상태 시험 추가; `frontend`: typecheck 통과, Vitest 22/22; observe Ruff 통과, 최종 전체 `make test`: 114 통과·1 실패(`test_expired_job_cannot_revive`, lease timing `lease is active`)·1 skip; 관측 통합 시험 통과. 실제 재분석 API와 live+review Playwright fixture는 미구현/미검증. FIX-O: Flow·Playback·step API 시각을 공용 ISO serializer로 변환하고 규칙 단계 APPLIED 정보를 API·Trace Drawer 표와 판단 맵/규칙 학습 링크에 표시; `make up`, observe 통합 1 통과, ruff/typecheck/Vitest 통과. 전체 `make test`: 128 통과·1 실패(기존 rules integration 오류 코드 기대 불일치)·1 skip. |
| T18 | 실제 집계·SLO·오류 예산·독립 알림 · 백엔드 | T08, T11, T14 | 완료(운영 30일 미검증) | journal 수신/종료와 DB 커밋 대조, attempt/요청/run 분모 분리·중복 제거·보완/retry 원실패 보존, 비용 미수집·관측 불완전 표시; 규칙 효과 지표는 SLO와 별도 집계하고 섀도 실행은 SLO 분모 제외; 별도 watchdog으로 수집기 정지/쓰기 실패 탐지, DB 오류/예산/소진 알림 및 알려진 표본 수치 검증. 증거: `make up` 성공, `cd backend && .venv/bin/pytest tests/integration/test_monitoring_collector.py -q` 13 통과, 관련 접수·SSE 회귀 21 통과, 변경 범위 ruff 통과. 전체 백엔드 재실행 112 통과·1 실패·1 건너뜀: T17 `observe/flow.py:32`의 Neo4j Duration `.total_seconds()` 오류(코디네이터에 전달); 직전 전체 실행은 112 통과·1 건너뜀. FIX-B: Request 기준 org/status 필터·분모, auto assignment 및 ReviewDecision 지표를 별도 business 집계로 구현; FIX-B 통합시험 반영; 전체 backend 재검증 121 passed, 1 skipped. 실제 30일 운영 SLO 판정은 G13 별도 | R13, R17 / G09, G12, G13 |
| T19 | Monitoring 화면 · 프런트 | T18, T17 | 완료 — 조직·상태 필터·업무 지표 연결(FIX-B·FIX-F), G09 집계 대조(T21 acc_d) | `Monitoring.tsx`·API 클라이언트·라우트 연결, KPI/SLO/지연/검토대기/예산/알림/실패 Trace·관측 불완전·null 미수집·필터·갱신시각 표시. Vitest 2 통과, Playwright 운영자 로그인 후 실제 API 요청 수 대조 1 통과; `make up && make test` 백엔드 112 통과·1 skip, 전체 Vitest 22 통과, typecheck 통과. FIX-B API가 org/status 필터와 별도 business 집계를 제공하도록 연동됨; Monitoring.tsx의 두 KPI는 현재 null 고정이며 이 dispatched 범위(frontend 수정 불가) 밖이라 화면 연결은 남음 | R13, R16 / G09 |
| T20 | WebMCP 제품 읽기 도구 통합 · 프런트/백엔드 | T00, T05, T06, T17 | 구현 완료·G10 차단 | `frontend/src/webmcp/`에 초안 `document.modelContext.registerTool` feature detection, 검색·상세·Trace 읽기 도구와 세션 쿠키 API 호출·입력 검증·요약 전용 반환·로그아웃 해제 추가; App 세션 상태에서 등록. Vitest 3 통과, 전체 Vitest 25 통과, typecheck·WebMCP E2E 1 통과. Chrome 154 headless probe는 30초 넘게 종료되지 않아 중단; 실제 agent 호출 주체 미확보. G10 통과에는 브라우저 등록/발견, 실제 agent 호출, 권한 밖 ID 404, 미지원 웹 정상 동작의 브라우저 증거가 남음. 상세: `docs/architecture/WEBMCP_PROBE.md` T20 절 | R14, R15 / G10, G11 |

### M4–M5 — 검증과 운영 준비

| ID | 작업·담당 | 선행 | 상태 | 산출물과 완료 기준 | PRD / 게이트 |
| --- | --- | --- | --- | --- | --- |
| T21 | 기능·안전·권한 인수 시험 · QA/공통 | T10, T13, T16, T17, T19, T20 | 완료(G10 차단·G06 비담당 부분 미검증)<br>증거: `artifacts/validation/t21/20261003T104827Z/gate-evidence.md` — `make test-acceptance` 백엔드 35/35·UI(Playwright) 10/10 통과, live Decision AI·실 Neo4j. 사용자 시나리오 8개·권한/격리/주입/파일/키(일치 0건)·자동 배정 0·정책 불변 조건·SSE 복구·집계 대조 통과; G01·G02·G04·G07–G09·G11 통과, G03·G05 제한 있음(근거 인용 가변·live 허용 자동 배정 성공 증거 없음), G10 브라우저 에이전트 호출 증거 없어 차단. 선행 실행 2회는 Live Decision AI 인용 가변성으로 S5 1건 실패 기록 보존(`20261003T103628Z`, `20261003T104217Z`). 수정 결함 5건(이벤트 루프 차단·내부 경로 노출·Neo4j 시간 직렬화·재분석 후 상태 고착·재생 사람 대기 노드), 보고만 R1–R5<br>**V2 보강(2026-10-03)**: `artifacts/validation/t21-gates/20261003T113332Z/gate-evidence.md` — live Decision AI·전용 tenant에서 G05 자동 배정 성공 3/5(저장·API·Tasks 화면 대조 일치, 대기 2건 사유 기록), G06 정책 버전 고정·rollback(v(n+2)=v(n))·A 불변 및 Cypher 관계=Topology/Tasks 화면 일치, G03 짧은 요청 9/9 `근거 미완료`·배정 0(합성 없음)·인용 가변성 3회×2(Jaccard≥0.857). 게이트 시험 backend 5/5·UI 2/2, 전체 backend 135 통과·1 skip. Topology 화면에 관계 목록 추가(결함 수정), 보고 R-E1~E3<br>**FIX-E (2026-10-03)**: live Decision AI 전체 `make test-acceptance` 실행 `artifacts/validation/t21/20261003t114858z-54105`, `20261003t115628z-62069`, `20261003t120447z-70931`에서 각각 backend 39 passed·1 failed, UI 12/12 passed. 첫 fixture 실패는 대문자 timestamp tenant 이메일 정규화 불일치였고 runner tenant를 소문자로 생성하도록 수정. 이후 단일 S5 실패들은 파일 span 조회에 chat span이 섞인 점, 제외 파일 assertion 자료형, 최초 revision과 후속 judgment citation ID 비교에서 비롯된 테스트 검증 오류로 확인해 구조 기준으로 수정; 최종 S5 live 재실행 `artifacts/validation/t21/20261003t121558z-83004` 1/1 통과; 최종 전체 백엔드 pytest 136 통과·1 skip. 전체 acceptance는 최종 수정 후 다시 돌리지 않아 전체 최종 통과 증거는 없음. 채팅 근거 span 저장/연결 및 run별 DATA_DIR·tenant 적용 | 원본의 사용자 8시나리오 및 권한 밖 접근/악성 지시/파싱·키 보호·무승인/중복 예방; 실제 UI/API/저장 증거, 테스트 개수·실패·skip 명시; 확장 회귀에 재사용할 G04–G09·G11 기준 증거도 식별 | R01–R16 / G01–G11, X10 선행 증거 |
| T22 | 장애·정합성·복구 시험 · QA/백엔드 | T14, T15, T18 | 완료<br>증거: `artifacts/validation/t22/20261003T093629Z/report.md`(장애 11/11 통과), `20261003T094002Z/report.md`(대조 재시험 1/1), backend pytest 128 통과·1 skip | Decision AI/파서/Neo4j/파일 장애·SSE 단절·서버 종료·정책 도중 변경; 만료 worker 복귀와 과거 초안 승인 거절; DB 실패 분모 보존·journal 쓰기/수집기 별도 장애·독립 알림·복구 대조; 거짓 성공/유실/중복 없음 | R01, R07–R15 / G01, G05–G09, G11 |
| T23 | 접근성·반응형·브라우저 시험 · QA/프런트 | T10, T13, T16, T17, T19 | 완료(전체 회귀 1 실패) | axe 10화면 critical/serious 0건(Chromium/WebKit); 키보드 실제 요청·근거·검토·판단맵 6/6, 반응형·reduced-motion·Safari WebP 통과; `artifacts/validation/t23/report.md` (전체 make test: 123 통과, 1 skip, ingest 시험 1 실패) | R16 / G02, G04, G07 |
| T24 | 현업 평가 표본·정답·품질 시험 · AI/현업 검토 | T02, T03; 최종 실행은 T09, T15 | 진행(정답 확정 대기) | 후보 120건·튜닝/최종 60건 분리와 SHA-256 manifest, live tuning 60건 실패 0; 잠정 macro-F1(AI 필요성 0.253/개발 가능성 0.554/긴급도 0.919), 긴급 recall 0.857, 팀 집합 F1 0.217 — 현업 검토·최종 평가·목표 미달 원인 후속 확인 대기 | R04, R05, R17 / G12 |
| T25 | 개발 부하·지연·SSE 시험 · QA/백엔드 | T21, T22, T24 | 완료(개발 성능 13/13 통과)<br>증거: `artifacts/validation/t25/20261003T101333Z/REPORT.md`; 30분 2,829건·SSE20·판단 성공률 99.965%, backend pytest 129 통과·1 skip. SSE 전달 p95 2,000ms 경계; G12 전체는 T21·T24 별도 | 예열 후 30분/활성10/SSE20/유효200+, 입력50/25/15/10%; 한도 근처·실패 포함 측정, journal fsync 부하 포함, 최초/보완/retry 분모·원래120초 실패 보존·예산 계산; 가용성99.9%/판단99% 및 모든 p95 목표 통과 FIX-SSE 보조 2분 예열+10분 live Decision AI·VU10·SSE20: 1,032건, SSE p50/p95/max 159/275/970ms, 중복·역순 0, Decision AI 기록 1,216회(<8,000), 전체 백엔드 135통과/1건너뜀; `artifacts/validation/t25-sse/20261003T110513Z/REPORT.md`. 30분 공식 판정은 위 증거 그대로 유지 | R17 / G12 |
| T26 | 실행·운영·보존·배포 문서 · 공통 | T21, T22 | 완료(로컬 운영 문서·백업/복원·mock 새 환경 실증) | README·docs/operations·scripts/ops 및 `artifacts/validation/t26/README.md`; 전용 Neo4j project/7689 dump→새 경로 load 후 Request 2/Review 1/Task 0/Run 2/RunStep 7/RuleVersion 0 전후 일치; 새 복사본 mock 접수·조회(202/200); `make up && make test`: backend 128 통과·1 skip, frontend 34 통과. 남음: live Decision AI, 원격 관측/알림, 호스트 유실, 운영 인증·보존/삭제 미검증. 초기 공유 Neo4j 일시 정지 후 재기동 및 백업 대상 보호 보완 내역 증거 기록 | R01, R13, R15, R18 / G01, G09, G11 |
| T27 | G01–G12 증거 종합과 완료 판정 및 X 게이트 별도 보고 · QA/공통 | T20–T26 | 완료(판정: 개발 완료 미선언 — G10 차단·G12 품질 미검증) — `artifacts/validation/final/GATE_REPORT.md` | 게이트별 상태/증거/실행ID/코드·정책·모델 버전/날짜, 실연동 vs 모의·로컬 vs 배포 구분, 필수 TODO/빈 경로 확인; 미통과가 있으면 개발 완료 선언 금지 | R18 / G01–G12 |
| T28 | 30일 실제 운영 관측 · 운영 | T27, 실제 배포 | 대기 | 연속30일 기간·트래픽·분모·오류·누락·예산·알림·원인Trace 보고; X01–X10과 혼합하지 않고 G13 별도 보고; 짧은 기간/수집 누락은 미검증, 개발 부하 통과와 별도 판정 | R13, R18 / G13 |

T24의 정답 확정과 T26의 운영 인증/보존/배포 값은 외부 책임자의 실제 요건이다. 표본 후보 생성·평가 러너·개발 권한/보안 시험은 기다리지 않고 진행한다. 필요 정보가 구체화되면 그 항목만 요청하며 모의 정답·임의 보존 기간으로 외부 확인을 대체하지 않는다.

T11이 배정 생성과 동시 승인 검증을 소유하고 T12는 생성된 업무의 조회·상태 API만 소유한다. T11 완료 증거는 실제 DB에서 확인하므로 후속 T12 완료를 요구하지 않는다. 이 책임 분리를 작업 분할 시 유지한다.

### M6 — 수정 경험의 규칙화와 입체 판단 맵

선행은 [08_LEARNING_LOOP 8절](docs/spec/08_LEARNING_LOOP.md#8-확장-작업-t29t38) 기준이다. 모든 항목은 대기이며 설계 반영은 구현·시험 완료를 의미하지 않는다.

| ID | 작업·담당 | 선행 (08 8절 기준) | 상태 | 산출물과 완료 기준 | PRD / 게이트 |
| --- | --- | --- | --- | --- | --- |
| T29 | 판단 관계 모델·Neo4j 제약·경로 질의 · 백엔드 | T04, T11, T15 | 완료 (증거: 백엔드 test_judgment_graph 5 통과·전체 백엔드 119 통과 1 건너뜀; 상세 docs/architecture/JUDGMENT_GRAPH.md) | EvidenceSpan·ModelOutput·Correction·RuleCandidate·RuleDecision·ReviewDecision·RuleVersion·ValidationRun·RunStep 의미와 실제 관계 제약/색인/경로 질의; tenant 경계 및 없는 관계 미합성 확인. 모델 설계는 T04와 병행 선반영 가능 | R25, R26 / X06, X08 |
| T30 | 수정 기록 저장과 원안 비교 API · 백엔드 | T11, T29 | 완료 (증거: Correction 조회 API·Review용 비교 API, 전체 make test 백엔드 96 통과·1 건너뜀) | 검토 결정 트랜잭션에서 항목별 Correction 원안·수정·근거·수정자·시각·revision/run/Config 기록; 원안 불변, 조회 결과와 Review/Learning 비교 대조 | R19 / X01 |
| T31 | 규칙 후보 생성(지지·반례·자료 부족) · AI/백엔드 | T30, T03 | 완료 (증거: 실제 Neo4j 후보 통합 시험 3 통과; 전체 make test 백엔드 96 통과·1 건너뜀) | 후보마다 지지·반례 Correction/EvidenceSpan ID, 범위·불확실성·출처·생성 주체/버전 연결; 최소 표본 미달 자료 부족 표시, 효과 미주장 | R20 / X02 |
| T32 | 규칙 검토·수명·권한 API와 Config 연동 · 백엔드 | T05, T15, T31 | 완료 (증거: 실제 Neo4j 규칙 통합 시험 7 통과; 전체 make test 백엔드 112 통과·1 건너뜀, 프런트 16 통과) | 규칙 관리자 권한·감사, 승인/범위 수정 승인/사유 필수 기각, 검증 및 게시·중단·되돌리기 구현; 각 동작 새 Config 버전, 필수 검토/무승인 배정 완화 거절 | R21, R22 / X03, X05, X07 |
| T33 | 섀도 비교 검증 러너 · 백엔드/QA | T09, T32 | 완료 (증거: 사람 정답·컨텍스트 호출 상한·검증 상태 전이 통합 시험; 전체 백엔드 122 통과·1 건너뜀) | 과거 입력 기준/후보 비교와 ValidationRun 조건·표본 기록; 전후 업무·배정·검토 큐·알림·사용자 이벤트·최신 포인터 수 동일(변화 0); 비용/호출 상한 확인 | R23 / X04 |
| T34 | 실행 중 규칙 적용과 RuleApplication 기록 · 백엔드 | T08, T09, T32 | 완료 (증거: 실제 Neo4j 게시 전후·범위 밖·중단·되돌리기·재시작 통합 시험 7 통과; 전체 make test 백엔드 112 통과·1 건너뜀) | 시작 시 Config 버전 고정, 범위 내 적용·범위 밖 미사용·충돌 미적용 및 전후 값 기록; 게시 전 시작 실행은 이전 버전 사용, 범위 밖 미사용 기록, 과거 결과 불변 | R22 / X05, X07 |
| T35 | 규칙 효과 관찰 집계 · 백엔드/데이터 | T18, T34 | 완료 (증거: 40건 알려진 표본의 전후·집단·지연 통합 시험; 전체 백엔드 122 통과·1 건너뜀) | 적용 전후·사용/미사용 집단 지표와 표본 수, 최소 표본 설정 근거·Config 관리; 기준 미달은 관찰 중·표본 부족으로 효과 미확정, SLO 수치·분모 불변 및 섀도 제외 대조 | R24 / X09 |
| T36 | Review 원안 비교 확장·규칙 학습 화면 · 프런트 | T13, T32–T35 | 구현 완료(2026-10-03) — vitest `Learning.test.tsx` 7건 통과; Playwright `e2e/learning.spec.ts` live Decision AI·실제 Neo4j 통과(검토자 수정 3건→후보→승인(범위 확정)→검증→게시→새 요청 범위 안 사용 1건→중단). 남은 제한: 검증 결과 조회 API 없음(브라우저 sessionStorage 보관), Review는 대기 건만 열려 결정 후 비교는 규칙 학습 화면에서 확인 | 원안/수정 Correction 비교, 후보 지지·반례·결정·검증·버전 수명·효과와 권한별 동작 표시; 동일 ID의 실제 API 결과와 화면 대조 | R19–R24 / X01–X05, X07, X09 |
| T37 | 입체 판단 맵 API·화면·목록 보기 · 공통 | T17, T29, T34 | 완료 (증거: vitest 25 통과, 실데이터 Playwright 2 통과 — 판단 1건+검토 수정 1건 이후 노드·연결 수/ID가 API와 일치, 업무 단계→EvidenceSpan 역추적, 목록 보기 키보드; T34 규칙 적용 실데이터는 병행 작업 의존) | 저장된 실제 5계층 관계만 렌더링; 필터·경로·원문 이동·줌/이동·키보드/목록 보기; 그래프 질의 결과와 화면 노드·연결 수·ID 대조, 목록 보기 E2E 및 키보드 시험 | R25, R26 / X06, X08 |
| T38 | 확장 연결 시나리오 검증과 X01–X10 판정 · QA/공통 | T21, T22, T36, T37 | 완료(2026-10-03, 최신 코드 재실행 반영) — **최신 증거**: `artifacts/validation/20261003T122747Z/extension/scenario-evidence.md`(tenant `t-x38r-10031227`, live Decision AI 39건, `--tenant` worker). X01–X10 전부 통과; 이전 한계 F3(Trace 규칙 적용 상세)·F4(불변 조건 허용 목록·blocked_by_invariant)·F5(자료 부족 승인 확인)·F6(섀도 Run/ValidationRun id 분리)·F7(시각 직렬화) 해소 확인, lead_org 수정 경로 1회(후보→규칙→섀도 검증→게시→적용)·텍스트 전용 요청의 chat EvidenceSpan 판단 맵 표시와 업무→근거 역추적 확인, X08 재시작+새로고침 후 검증 카드 서버 조회 일치. 재실행 결함 F10(판단 맵 응답 순서 경합)을 `JudgmentMap.tsx`에서 최소 수정. X10: `make test` 136 통과·1 건너뜀+vitest 37 통과, `make test-fault` 11/11, `make test-acceptance` 백엔드 40/40·UI 12/12. 남은 제한: lead_org 규칙은 모델이 근거 인용을 달지 않아 원문 역추적 없음(feasibility 체인으로 입증), X09 표본 충분 판정 경로 미시험, FIX-SSE·FIX-R 직접 대조 없음. — 이전 실행: `artifacts/validation/20261003T093618Z/extension/scenario-evidence.md`(ID 표·DB 질의 요약·스크린샷). X01–X04·X06–X08·X10 통과, X05 통과(Trace 단계 상세가 규칙 버전·전후 값을 표시하지 않는 한계 F3), X09 통과(표본 부족 미확정 경로만 시험). 실제 Decision AI·전용 tenant·`--tenant` worker·API/worker 재시작 diff 0건. 백엔드 129 통과·1 건너뜀, vitest 34 통과. 발견 결함 F1(`POST /api/learning/candidates` 항상 500)·F2(후보 rule_id 형식) 수정, F3–F9 보고. 남은 제한: 같은 문장 템플릿의 판단 편중, lead_org 수정 미시험, 표본 충분 효과 판정은 T35 시험 의존, T21·T22는 선행 '대기' 상태 | 10단계 연결 시나리오(6단계 이후 X09 효과 관찰 확인 포함)의 실제 저장 ID·UI 대조와 X01–X10 증거 보고; X10에서 G04–G09·G11 시험 재실행 결과 및 기존 게이트 별도 판정 | R19–R26 / X01–X10 |

## 5. 구현 시작 시 작성할 계약

### 상태 모델

T04에서 상태 이름은 확정하되 아래 의미를 유지한다.

| 객체 | 상태 의미 / 전이 제한 |
| --- | --- |
| 요청 | 접수·보완 필요·처리 중·검토 대기·배정 완료·반려·실패; 사람 대기와 시스템 실패 구분 |
| 실행 | 대기·진행·판단 저장 완료·실패·취소; 정보 부족도 필수 기록 저장 시 판단 완료; 새 실행 선택 후 과거 실행이 최신 포인터를 변경하지 못함 |
| 단계 | 대기·진행·성공·실패·건너뜀·사람 대기; 시작/종료/실행 주체·버전·부모/선행 기록 |
| 검토 | 대기→승인/수정 승인/반려/정보 요청; request/revision/run/초안/검토 버전 결합, 과거 대상 충돌 시 409 |
| 업무 | T11 트랜잭션에서 승인 또는 자동 배정 모든 조건 충족 후 생성; 대기·막힘·진행·완료, 미충족 전제/선행 시작 거절 |
| 규칙 후보 | 제안·검토 필요·자료 부족; 후보 자체는 실행에 영향 없음 |
| 규칙 결정 | 후보에 대한 `RuleDecision`: 승인·범위 수정 승인·기각(사유 필수); 결정자·확정 범위·시각 기록, 실행 영향 없음 |
| 규칙 버전 | 검증 중→검증 완료→게시→중단/되돌림; 검증 완료 전 게시 금지; 게시/중단/되돌리기는 새 Config 버전, 과거 기록 불변 |
| 섀도 실행 | shadow 종류의 비교 결과; 업무·배정·검토 큐·알림·사용자 이벤트·최신 포인터 변경 금지 |
| 정책 | 검증된 새 버전→활성; rollback도 새 버전; 실행 버전 불변, 필수 검토 해제 금지 |
| Job | DB 시각 lease + 단조 generation; 인계/갱신/결과 쓰기에서 잠금 검증, 만료 소유권 부활 금지 |

### API와 권한

T01/T04에서 OpenAPI와 프런트 계약을 함께 고정한다. 초기 리소스는 auth/session, requests/revisions/attachments/runs, decisions/reviews/tasks/teams, policies/versions, traces/topology/events, monitoring/alerts, corrections, rule-candidates, rules/versions, validations, judgment-graph다. 접수·검토·재실행·정책 변경에 멱등키 또는 기대 revision을 적용한다. 조회 pagination/filter 범위, 오류 코드, 파일 다운로드·SSE·WebMCP의 같은 접근 경계를 시험한다. 아직 구현하지 않은 경로나 명령을 검증 완료 문서에 기재하지 않는다.

### 증거 파일

T01에서 `artifacts/validation/<run-id>/` 구조를 만든다. 확장 증거는 `artifacts/validation/<run-id>/extension/` 하위에 보존한다. 각 실행은 manifest(코드 SHA·정책·모델·질문/스키마·환경·시각·입력 범위·실연동 여부), test-results, 비민감 Trace ID/집계, 부하 원시 표본, 평가 표본 hash/정답 검토 이력, gate-report를 남긴다. 민감 원문·키·세션 값은 제외한다. 생성 결과를 무분별하게 Git에 추가하지 않으며 재현에 필요한 비민감 보고서와 입력만 관리한다.

## 6. 추적 행렬

| 게이트 | 주요 작업 | 필수 증거 |
| --- | --- | --- |
| G01 | T01, T04, T06, T08, T22, T26 | 깨끗한 설치·실제 접수/조회·재시작/복원 |
| G02 | T06, T07, T10, T21 | 형식별·부분 실패·초과·보완 입력과 화면 |
| G03 | T02, T03, T09, T10, T24 | 실제 Decision AI 결과·원문 근거·업무 분해·버전 |
| G04 | T11, T13, T21 | 4종 검토·원안/수정·감사·역할별 화면 |
| G05 | T04, T11, T12, T13, T22 | 실제 업무·팀/선행 관계·동시 승인 중복0 |
| G06 | T12, T15, T16, T22 | 실제 그래프·정책 전후/되돌리기·버전 고정 |
| G07 | T08, T17, T21 | 실제 성공/실패/사람대기·Playback 부작용0 |
| G08 | T14, T22, T25 | SSE 차단/복원·최종 상태·복구 p95/누락0 |
| G09 | T04, T06, T08, T18, T19, T22, T26 | DB 실패 분모 보존·집계/진단 대조·독립 알림·관측 누락 표시 |
| G10 | T00, T20, T21 | M0 실제 브라우저 사전 확인 + 제품 도구·권한·미지원 회귀 |
| G11 | T05, T07, T09, T11, T20–T22, T26 | 조직/역할·파일/주입·키·저장 장애 시험 |
| G12 | T24, T25, T27 | 현업 정답과 분리 평가·30분 원시 부하 측정 |
| G13 | T18, T19, T28 | 실제 배포 후 30일 운영 보고 |
| X01 | T30, T36, T38 | DB Correction와 Review/Learning 원안·수정 비교 대조 |
| X02 | T31, T36, T38 | 지지·반례·범위·불확실성·자료 부족 후보와 Correction ID |
| X03 | T32, T36, T38 | 역할별 API 허용/403(무권한 범위 수정·미검증 게시 거절 포함), 단건 승인 분리, 확정 범위·감사 기록 |
| X04 | T33, T38 | 섀도 전후 부작용 카운트 0, ValidationRun 조건·표본 |
| X05 | T32, T34, T38 | RuleApplication 사용/범위 밖 미사용·전후 값, 안전 조건 거절 |
| X06 | T29, T37, T38 | Neo4j 관계와 화면 노드/연결 ID·수 대조, 목록·키보드 E2E |
| X07 | T32, T34, T38 | 중단/되돌리기 새 버전, 진행 중 실행 버전·과거 기록 불변 |
| X08 | T29, T37, T38 | 재시작 전후 관계·후보·규칙·적용 질의 대조 |
| X09 | T35, T36, T38 | 알려진 실행 표본의 별도 효과 집계·표본 부족 미확정 |
| X10 | T38 | G04–G09·G11 회귀 시험 결과 |

## 7. 준비 완료 기록

- PRD와 T00–T28 총 29개 작업·선행 관계·산출물·검증·게이트 연결 작성. T00 사전 호환성 확인을 M0에 추가하고 T11/T12 책임을 분리.
- 기존 AI_API_KEY 존재 확인. 공식 문서 접근 및 API/모델/SDK 계약 확인. 키 값은 기록하지 않음.
- Decision AI 모델 목록 조회: proxy CONNECT 403, 실제 인증/판단 미검증. 기존 docs.typesafe.ai 규칙을 보존하면서 api.typesafe.ai를 환경 설정 초안 허용 목록에 추가.
- 개발 전제 도구의 통과 결과는 제품 인수 증거와 분리. 정적 Observatory 누락은 T17의 실제 화면 구현에 포함.
- 설계 리뷰 7건을 PRD·TASK·원 요구사항·실행 계약·디자인 샘플에 반영했다. [수정 추적표](docs/architecture/EXECUTION_CONTRACT.md#7-디자인-샘플과-수정-추적)에 검증 담당을 기록했다. 애플리케이션 구현·제품 테스트·배포는 아직 수행하지 않았다.
- 2026-10-03 기준 PRD/TASK v0.3에 08 확장 설계, R19–R26·X01–X10·T29–T38 추적을 반영했다. 이는 문서 변경이며 확장 기능 구현·시험은 미수행이다.

T03 증거: `docs/architecture/JUDGMENT_DESIGN.md`, `backend/ildongi/judgment/`, 단위 시험 7건 통과 및 Decision AI live 2건 업무 초안 차이 확인; 결과 `artifacts/validation/t03/live-smoke.json`. 429/529·timeout 장애 재현 시험은 미수행.

## 2026-10-05 후속 문서 상태

- **정정:** 당시 `136` backend / `37` Vitest는 이전 실행 스냅샷 수치다. 최신 기준선 수치는 SPEC_TRACE에 적힌 466/1 skip, 358이며, 브라우저 전체 통과를 뜻하지 않는다.
- **해소된 과거 잔여 주장:** 외부 모델 전송 마스킹은 `domain/masking.py` 구현 및 단위 시험이 확인됐다. EvidenceViewer 원문 anchor 및 맵 확대/버전 탭도 현재 구현 증거가 있다. 실송신 전 경로 전수 실측 및 운영 민감 데이터 평가는 계속 제한이다.
- **부분/미해결:** Trace drawer의 오류·duration·실행 model/schema 표시, 검토 수정 승인 결함, 선행 완료 이후 업무 시작 UI 결함, 지정 browser 성능 경계, 현업 평가 및 운영/외부 의존 게이트는 해결로 표시하지 않는다. 최신 상태는 `artifacts/validation/final/GATE_REPORT.md` 2026-10-05 부록 참조.
