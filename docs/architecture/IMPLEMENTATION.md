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
  domain/            공통 Pydantic 모델·상태 enum (T04, 추가만 허용)
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

- 모든 Neo4j 쓰기는 `db.tx` 도우미의 쓰기 트랜잭션을 사용하고 `tenant_id`를 항상 조건에 포함한다.
- ID 형식: `req_`, `rev_`, `run_`, `step_`, `job_`, `rvw_`, `task_`, `cfg_`(Config 버전은 정수 `version`), `cor_`, `cand_`, `rdec_`, `rule_`(규칙 버전은 `rule_id@version`), `val_`, `att_`(attempt), `evt_` + ULID/uuid 기반.
- 시각은 UTC ISO 8601, 비교는 DB 시각(`datetime()`) 기준.
- 키·쿠키·원문 전체·모델 전송본을 로그와 journal에 쓰지 않는다.
- 모의(mock) Jev는 `JEV_MODE=mock`일 때만 동작하고, 그 결과는 저장·화면·보고서에 `mock`으로 표시한다. 게이트 증거는 `JEV_MODE=live`만 인정한다.
- 기본 실행: `make up`(neo4j) → `make api` → `make worker` → `make web`. `make test`는 단위+통합(실제 Neo4j) 시험.
- 개발 계정은 `scripts/bootstrap_dev.py`가 만든다(요청자·검토자·팀 담당자·운영자·규칙 관리자, 두 tenant). 운영 인증과 구분한다.

## 4. 진행 상태

작업별 상태와 증거는 [TASK](../../TASK.md)를 갱신한다. 이 문서는 구조 합의가 바뀔 때만 수정한다.
