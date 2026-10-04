# 구현 기준 (코드 구조·소유권·실행 규칙)

작성일 2026-10-03 · 상태: 구현 시작 기준. 제품 계약은 [PRD](../../PRD.md)·[TASK](../../TASK.md)·[실행 계약](EXECUTION_CONTRACT.md)·[확장 설계](../spec/08_LEARNING_LOOP.md)가 우선한다. 이 문서는 여러 작업자가 같은 코드베이스를 충돌 없이 만들기 위한 구조 합의다.

## 1. 기술 선택

| 영역 | 선택 |
| --- | --- |
| 백엔드 | Python 3.14(로컬 확인 버전) + FastAPI + Pydantic v2, `uvicorn`; 패키지 `jevtriage`, 프로젝트 `backend/pyproject.toml`, 가상환경 `backend/.venv` |
| 저장소 | Neo4j 5 (Docker Compose `neo4j` 서비스, bolt 7687, 데이터 `./.data/neo4j`), 공식 `neo4j` Python async 드라이버 |
| 실시간 알림 | Redis 7.4.2 pub/sub(`tenant:{id}`, `jobs`); Neo4j Event/Job이 진실의 원천이며 Redis는 깨우기 전용 |
| 작업 실행 | 별도 worker 프로세스(`python -m jevtriage.jobs.worker`), Neo4j의 Job 노드 lease/generation |
| 관측 journal | `./.data/journal/*.jsonl` append+fsync, 수집기 `python -m jevtriage.journal.collector`, watchdog `python -m jevtriage.journal.watchdog` |
| 원본 파일 | `./.data/files/<tenant>/<sha256>` + Neo4j 메타데이터 |
| 프런트엔드 | React 18 + TypeScript + Vite (`frontend/`), 디자인 토큰 `docs/design-handoff/tokens.css` 재사용, 라우팅 react-router |
| 테스트 | `pytest`(+`pytest-asyncio`), 실제 Neo4j 대상 통합 시험(`tests/integration`), 프런트 `vitest`, E2E `playwright` |
| Jev | `typesafe-sdk`(공식 SDK) 또는 공식 HTTP API, 서버 설정의 `JEV_API_KEY`를 명시 전달 |

## 2. 디렉터리와 소유 모듈

```
backend/jevtriage/
  main.py            앱 팩토리·라우터 등록 (공통; 라우터 추가만 허용)
  config.py          환경 설정 (공통)
  db/                드라이버·스키마 제약·트랜잭션 도우미 (T04)
  domain/            공통 Pydantic 모델·상태 enum·순수 텍스트 마스킹 (T04, 추가만 허용)
  auth/              세션·역할·tenant·CSRF (T05)
  journal/           관측 journal·수집기·watchdog (T04/T18)
  ingest/            접수·revision·첨부 API, parsers/ (T06/T07)
  jobs/              Job lease·worker (T08)
  judgment/          Jev 클라이언트·질문·근거·업무 초안·자동 배정 조건 (T02/T03/T09)
  review/            검토·배정 트랜잭션 (T11), Correction 생성 (T30)
  tasks/             업무 조회·상태 (T12)
  policy/            Dynamic Config (T15)
  events/            이벤트 시퀀스·SSE (T14)
  observe/           Trace·Flow·Topology·Playback 데이터 (T17)
  monitoring/        집계·SLO·알림 (T18)
  learning/          후보·규칙·섀도·적용·효과 (T31–T35)
  graph/             판단 관계·판단 맵 질의 (T29/T37)
backend/tests/{unit,integration,e2e}
frontend/src/{api,components,pages,webmcp,state}
scripts/             dev 시작/중지, probe, 평가·부하 러너
artifacts/validation/<run-id>/   검증 증거 (비민감)
```

작업자는 자기 작업의 모듈과 테스트만 수정한다. `main.py` 라우터 등록, `domain/` 모델 추가, `pyproject.toml` 의존성 추가는 **추가만** 허용하고 기존 항목을 바꾸지 않는다. 다른 모듈의 공개 함수 시그니처를 바꿔야 하면 코디네이터에게 질문한다.

## 3. 공통 규칙

### 레이어 의존 계약 (2026-10-04)

`make lint`는 Ruff와 `lint-imports`를 실행한다. `backend/pyproject.toml`의 여섯 계약은 기능 패키지 안의 `api → service → store`, policy→db→domain, judgment→review, learning→judgment→policy 방향과 기능 패키지 사이의 비순환성을 강제한다. API·router의 `db.tx`/`db.driver` import와 직접 `tx.run` 호출, 모듈 간 `_private` import는 `tests/unit/test_architecture_contracts.py`가 검사한다. Ruff의 `PLC2701`도 제품 코드의 private import를 금지하며 테스트의 기존 직접 점검 경로만 제외한다. 인증·검토·이벤트·그래프·관측·모니터링 API의 인라인 Cypher는 각 기능의 store 또는 query 모듈로 옮겼다. `metrics_store.py`는 journal 수집기와 monitoring 집계가 함께 쓰는 SQLite 연결을 소유한다.

기능 패키지 사이에서는 상대 기능의 `store`·`trace_store`를 직접 import하지 않는다. 요청 메타 조회는 `ingest.service.request_meta`, 학습 검증 입력은 `judgment.service.load_input_for_shadow`, worker의 단계 기록은 `observe.service`의 공개 함수로 호출한다. 이 규칙도 정적 계약 시험이 새 import를 거절한다.

| 최초 정적 조사 항목 | 확인한 경로 | 현재 상태 |
| --- | --- | --- |
| 상호 의존 | `db↔domain`, `journal↔monitoring`, `judgment↔learning`, `judgment↔policy`, `judgment↔review`, `learning↔policy`; 간접 순환 `ingest→jobs→judgment→ingest`; `journal.writer↔group_commit` | 공용 `domain` 정의, `metrics_store`, `journal.failure`, `db.runs`·`db.pinning`, `worker_wakeup`으로 해소. `domain.runs→db.runs` 호환 import 한 건만 예외 |
| 함수 내부 지연 import | `auth.core` 4, `judgment.service` 2, `ingest.service` 8, `ingest.api` 1, `db.events` 1 (총 16개; 조사 시점 AST 기준) | 공용 Principal 타입 분리와 import 방향 정리 후 모두 모듈 상단으로 이동 |
| 모듈 간 private import | `journal.group_commit→writer._record_failure`, `learning.candidates_api→candidates._json`, `graph.query→model._decode`, `monitoring.slo→aggregates._time` | 공개 이름으로 전환하고 기존 private 함수는 내부 호환성을 위해 유지 |
| API의 직접 DB 접근 | `auth.router`, `review.api`, `events.router`, `graph.api`, `observe.api`, `monitoring.api` | 직접 트랜잭션·Cypher 제거, 기능별 저장소 함수 호출 |

현재 `domain.runs→db.runs`는 기존 `start_run_in_tx` import 경로를 유지하기 위해 두 계약의 `ignore_imports`에 같은 한 건을 명시했다. 실제 구현과 정책 pinning은 `db.runs`·`db.pinning`이 소유한다. `domain.runs`는 함수 재수출만 담당하므로 데이터 모델과 저장 형식은 바뀌지 않았다. 새 코드에서는 domain에 DB·정책 의존을 추가하지 않고, 모듈 간 호출은 공개 함수에 한정한다.

`domain.masking`은 judgment의 외부 전송 마스킹 패턴과 순수 함수를 소유하며, `judgment.masking`은 기존 import 경로를 유지하는 재수출 모듈이다. API 표시 제목·미리보기도 같은 domain 마스킹 함수를 사용해 규칙 복제를 막는다.

평가 기능 작업자의 변경이 완료된 뒤 `evaluation.api → evaluation.service → evaluation.store`로 라우터, 판단 로직, Neo4j 접근을 나눴다. 기존 평가 응답·레이블 저장 형식과 `evaluation.service`의 분석 도우미 공개 경로는 유지한다.

### 구조 재현과 회귀 시험

| 재현 시험 (수정 전 실패 확인) | 수정 | 완료 검증 |
| --- | --- | --- |
| API의 `db.tx`/`db.driver` import·인라인 `tx.run`, 인증 라우터의 `session.run` | auth·review·events·graph·observe·monitoring·learning·judgment 진행·evaluation 질의를 소유 store/query로 이동 | `test_api_modules_do_not_import_database_access`, `test_auth_router_uses_public_auth_boundary`, 평가 API 통합 시험 |
| 모듈 간 private import 4건 | 공개 이름으로 전환하고 Ruff `PLC2701`을 `make lint`에서 실행 | `test_modules_do_not_import_other_modules_private_functions`, `make lint` |
| 정책→학습 검증, 정책→판단 마스킹, 검토→판단 정의, DB→정책 pinning | 순수 정의를 domain으로, pinning과 Run 생성은 db로 이동 | 해당 `test_architecture_contracts.py` 시험과 여섯 import-linter 계약 |
| 접수→worker 순환과 journal writer→batcher 순환 | 공용 `worker_wakeup`·`journal.failure`로 의존 역전 | `test_ingest_does_not_import_worker_runtime`, `test_journal_batcher_does_not_import_writer`, 비순환 계약 |
| 기능 간 store 직접 import, 평가 라우터·service·store 혼재 | 상대 기능 공개 service로 위임, 평가 경계 분리 | `test_feature_modules_use_other_features_public_services`, `test_evaluation_router_service_store_boundary` |

호환성 예외는 `domain.runs→db.runs` 한 건이며 계약에 이유를 기록했다. 그 외 재현 시험은 수정 후 통과했다.

최종 확인: `backend/.venv/bin/pytest -q` 439 통과·1 건너뜀, `make lint` 여섯 import 계약 위반 0건·Ruff 0건, `make test-fault` 전용 7688에서 11건 통과. 구조 변경에는 프런트 파일 수정이 없다.

- 모든 Neo4j 쓰기는 `db.tx` 도우미의 쓰기 트랜잭션을 사용하고 `tenant_id`를 항상 조건에 포함한다.
- ID 형식: `req_`, `rev_`, `run_`, `step_`, `job_`, `rvw_`, `task_`, `cfg_`(Config 버전은 정수 `version`), `cor_`, `cand_`, `rdec_`, `rule_`(규칙 버전은 `rule_id@version`), `val_`, `att_`(attempt), `evt_` + ULID/uuid 기반.
- 시각은 UTC ISO 8601, 비교는 DB 시각(`datetime()`) 기준.
- 키·쿠키·원문 전체·모델 전송본을 로그와 journal에 쓰지 않는다.
- 모의(mock) Jev는 `JEV_MODE=mock`일 때만 동작하고, 그 결과는 저장·화면·보고서에 `mock`으로 표시한다. 게이트 증거는 `JEV_MODE=live`만 인정한다.
- 기본 실행: `make up`(neo4j) → `make api` → `make worker` → `make web`. `make test`는 단위+통합(실제 Neo4j) 시험.
- 개발 계정은 `scripts/bootstrap_dev.py`가 만든다(요청자·검토자·팀 담당자·운영자·규칙 관리자, 두 tenant). 운영 인증과 구분한다.

## 4. 진행 상태

작업별 상태와 증거는 [TASK](../../TASK.md)를 갱신한다. 이 문서는 구조 합의가 바뀔 때만 수정한다.
