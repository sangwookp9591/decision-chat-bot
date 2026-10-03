# T26 운영·보존·새 환경 검증 기록

실행일: 2026-10-03 · 환경: macOS, Python 3.14.6, Node.js 22.14.0, Docker Desktop, Neo4j Community 5.26.0.

## 실행 결과

- 새 임시 복사본을 `.env`, `.data`, `.git`, 기존 `.venv`/`node_modules`, 기존 증거 디렉터리 없이 만들었다. Python 의존성은 `cd backend && .venv/bin/pip install -e . --group dev`, 프런트는 `npm --prefix frontend ci`로 설치했다. `make up`, schema, bootstrap을 실행했다. `backend/requirements.lock`만 설치한 첫 시도에서는 argon2 등의 애플리케이션 의존성이 포함되지 않은 것을 확인했다. 최종 README는 `pyproject.toml`의 앱·dev group 설치를 안내한다.
- 새 환경은 `JEV_MODE=mock`, 전용 임시 `.data`, Neo4j 호스트 포트 7689, API 8198, Vite 5174를 사용했다. API `/api/ready` 및 웹 `/` 응답이 성공했다. 개발 requester 계정으로 synthetic 입력 1건을 POST했고 202 접수 후 `/api/requests/{id}` 조회 200을 확인했다. 조회된 상태는 `judgment_pending`, Jev 모드는 `mock`이었다. request ID: `req_eefa7fd582ff4a3c83e7d94240e6bff3`. Live Jev 판단 완료는 이 재현에서 검증하지 않았다.
- collector, watchdog도 별도 프로세스로 기동했다. worker에는 `--tenant t-alpha`를 지정했다. API·worker·collector·watchdog·Vite 종료 뒤 임시 전용 Neo4j 프로젝트를 내렸고 T26 실행의 임시 포트/경로 프로세스가 남지 않았음을 `ps`와 `docker ps`로 확인했다.
- 백업/복원은 전용 Compose 프로젝트 `jevtriage-backup`, 전용 컨테이너 `jevtriage-backup-neo4j-1`, Bolt 7689에서 `make backup`/`make restore`를 실행했다. Community `neo4j-admin database dump`는 오프라인에서 성공했고 restore load 및 SHA-256 manifest 확인도 성공했다. 복원 전후 t-alpha의 엔터티 수가 일치했다: Request 2, Review 1, Task 0, Run 2, RunStep 7, RuleVersion 0.
- `make up && make test`: 백엔드 128 passed, 1 skipped; 프런트 Vitest 34 passed. 실행 요약은 백엔드 86.31초, 프런트 2.86초다. `bash -n scripts/ops/backup.sh scripts/ops/restore.sh` 통과. 프로젝트/포트/공유 컨테이너 값으로 백업을 시도하면 거부되는 것도 확인했다.

## 사고 및 조치 기록

초기 백업 스크립트 시험에서 대상 Compose 파일을 저장소 루트로 잘못 잡아 공유 `decision-chat-bot-neo4j-1` 컨테이너를 잠시 정지했다. 즉시 `docker compose up -d neo4j`로 재기동했고 `make up`으로 Running을 확인했다. 코디네이터 지시에 따라 백업·복원 스크립트는 전용 프로젝트/컨테이너/7689 포트를 요구하고, 실제 Compose label·port·`/data` mount를 확인하며, 같은 경로를 쓰는 실행 중 공유 DB가 있으면 거절하도록 바꿨다. 이후 실증은 전용 임시 복사본에서만 수행했다. 공유 DB 데이터는 수정하지 않았다.

## 미검증·제한

- 외부 Jev live 호출, 실데이터 처리/동의, 운영 인증 공급자 및 secret manager는 검증하지 않았다. 입력 마스킹은 미구현이며 민감 실데이터 데모를 금지한다.
- 원격 관측 수집·알림 실제 수신, 호스트 전체 유실 감지/복구, 백업의 외부 저장소 복제, 복구 RPO/RTO, 보존·삭제 정책은 미검증 또는 미확정이다. 로컬 webhook 성공도 시험하지 않았다.
- Community dump에는 `system` DB의 사용자·역할이 없다. 복원 후 auth/bootstrap/schema를 다시 구성해야 한다. 파일/journal/metrics/alerts의 tar 백업은 수행했지만 별도 운영 스냅샷/외부 백업 저장소는 검증하지 않았다.
- 임시 새 환경에서 요청을 접수·조회했으나 `judgment_pending`까지 확인했으며 실제 live 판단/업무 할당 흐름은 이 작업의 재현 증거로 주장하지 않는다. E2E 전체 suite 및 평가 러너는 실행하지 않았다.

## 코디네이터 추가 제한 (2026-10-03)

- 복원 대조 데이터에는 Task·RuleVersion이 0건이었다. 업무(Task·Assignment·PRECEDES)와 규칙 버전·APPLIED 관계의 백업·복원은 이 실증으로 검증되지 않았으므로 **미검증**이다. 해당 엔터티를 포함한 데이터로 재실증해야 G01 복원 근거로 사용할 수 있다.
