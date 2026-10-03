# T01 새 환경 재실행 증거

실행일: 2026-10-03 (Asia/Seoul)

## 새 복사본 설치 및 인프라

| 단계 | 실행 | 결과 |
|---|---|---|
| 복사 | `rsync -a --exclude='.env' --exclude='.data' --exclude='node_modules' --exclude='.venv' --exclude='.git' ./ "$RUN_DIR/"` | 임시 경로 `/tmp/t01-rerun.CiayPI`에 복사. 비밀·런타임 데이터·설치 산출물 제외 |
| 환경 | `python3.14 -m venv "$RUN_DIR/backend/.venv"` | Python 3.14.6 가상환경 생성 |
| 백엔드 | `(cd "$RUN_DIR/backend" && .venv/bin/pip install -e . --group dev)` | editable 프로젝트 및 dev 의존성 설치 성공 |
| 프런트 | `npm --prefix "$RUN_DIR/frontend" ci` | 패키지 310개 설치 성공. npm이 7개 취약성 알림(중간 5, 높음 1, 치명 1)을 출력함 |
| Neo4j | 복사본 `docker-compose.yml`의 호스트 포트를 `17474:7474`, `7691:7687`로 바꾼 뒤 `docker compose -p t01rerun up -d neo4j` | 별도 Compose 프로젝트 `t01rerun`의 Neo4j healthy 확인. 첫 시도에서 기본 HTTP 포트 7474 충돌이 확인되어 HTTP 포트도 임시 포트 17474로 조정 |
| 설정 | 복사본 `.env.example`을 `.env`로 복사하고 `NEO4J_URI=bolt://localhost:7691`, `JEV_MODE=mock` 설정 | 로컬 복사본 설정만 변경 |
| 스키마 | `(cd "$RUN_DIR/backend" && .venv/bin/python -m jevtriage.db.schema)` | 성공 |
| 개발 계정 | `(cd "$RUN_DIR" && backend/.venv/bin/python scripts/bootstrap_dev.py)` | 성공 |

README 깨끗한 설치 절차와 비교하면 별도 인스턴스를 위해 임시 복사본의 Neo4j 호스트 포트를 7691로 바꾸고 Compose 프로젝트 이름을 지정했다. API 포트는 기본 8000 대신 8101을 사용했다. schema/bootstrap 명령은 README 절차와 같았다.

## 기능 확인

- API: `backend/.venv/bin/uvicorn jevtriage.main:app --host 127.0.0.1 --port 8101`; `/api/ready`는 `{"status":"ready"}` 반환.
- 제한 worker: `backend/.venv/bin/python -m jevtriage.jobs.worker --tenant t-alpha` 실행. tenant 제한을 지정했다.
- 개발 요청자 계정으로 `/api/auth/login` 로그인 후 CSRF 쿠키를 사용해 텍스트 접수. `POST /api/requests`는 HTTP 202, `req_4758049f8db94265b976868d86597878`, 초기 상태 `judgment_pending` 반환.
- worker 처리 후 `GET /api/requests/{id}`에서 상태 `검토 대기`, `GET /api/requests/{id}/judgment`에서 `mode=mock` 확인.
- `GET /api/requests` 목록에 해당 요청이 포함되고 단건 조회도 성공.
- `npm --prefix "$RUN_DIR/frontend" run typecheck`: 통과.
- `npm --prefix "$RUN_DIR/frontend" test`: 11개 파일, 37개 테스트 통과.
- `npm --prefix "$RUN_DIR/frontend" run build`: 통과. 기존 동적 import chunk 경고 1건.

## 저장소 검증

- `make up && make test`: Neo4j 실행, 백엔드 135 passed / 1 skipped, Vitest 37 passed.
- `make typecheck`: 통과.
- `make build`: 통과.
- `make lint`: 기존 36건 중 import 정렬·미사용 변수·포맷 수정 후 2건 남음. `backend/jevtriage/learning/apply.py:35`의 `ValueError`를 `TypeError`로 바꾸라는 TRY004는 입력 예외의 외부 동작을 바꿀 수 있다. `backend/jevtriage/learning/shadow.py:153`의 `except Exception`은 shadow 실행 오류를 실패 기록으로 보존하는 경계로 보이며, 예외 범위를 축소하면 동작을 바꾼다. 담당 규칙에 따라 두 건은 noqa나 동작 변경으로 숨기지 않고 보고한다.

## 정리

API와 tenant 제한 worker를 종료하고 `docker compose -p t01rerun down`을 실행해 임시 Neo4j 컨테이너와 네트워크를 제거했다. `ps` 확인 시 이 실행의 API·worker는 남아 있지 않았다. Vite 서버는 띄우지 않았다.
