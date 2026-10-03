# Jev Triage

요청·문서 접수와 Jev 판단, 사람 검토, 업무 추적을 위한 개발용 애플리케이션입니다. 이 저장소의 기본 실행 구성은 로컬 Docker Neo4j, FastAPI, 별도 worker, 관측 수집기/watchdog, Vite 프런트엔드입니다. 운영 배포 승인을 뜻하지 않습니다.

## 요구 사항

- Python 3.14 (프로젝트 가상환경 기준), Node.js 22와 npm
- Docker Engine/Desktop 및 Docker Compose v2
- Unix 계열 셸, 저장소 의존성 설치/접속을 위한 네트워크

## 깨끗한 설치

```sh
git clone <repository-url> decision-chat-bot
cd decision-chat-bot
cp .env.example .env
python3.14 -m venv backend/.venv
(cd backend && .venv/bin/pip install -e . --group dev)
npm --prefix frontend ci
make up
(cd backend && .venv/bin/python -m jevtriage.db.schema)
backend/.venv/bin/python scripts/bootstrap_dev.py
```

위 bootstrap 명령은 기본 개발 계정 암호를 사용합니다. 외부에 노출된 개발 환경에서는 `JEVTRIAGE_DEV_PASSWORD`를 별도로 설정하세요. `.env`는 로컬 비밀 설정이므로 저장소에 추가하지 않습니다.

## 설정

`.env.example`의 키는 다음과 같습니다. 비밀은 값이 아니라 로컬 환경에서 주입합니다.

| 키 | 목적 | 기본/주의 |
| --- | --- | --- |
| `JEV_API_KEY` | 서버에서 Jev live API 호출 | 비밀. 비어 있으면 live 판단을 할 수 없음 |
| `NEO4J_URI` | Neo4j Bolt URI | 로컬 기본 `bolt://localhost:7687` |
| `NEO4J_USER` | Neo4j 사용자 | 로컬 기본 `neo4j` |
| `NEO4J_PASSWORD` | Neo4j 비밀번호 | Compose 개발 기본 `development-only`; 운영에서 교체 필수 |
| `JEV_MODE` | 모델 연결 모드 | `live` 또는 명시적 `mock`; 결과와 화면에 모드가 보존됨 |
| `DATA_DIR` | 원본 파일, journal, metrics, 알림 경로 | 프로세스 작업 디렉터리 기준 `.data`; 모든 API/worker/collector/watchdog에 같은 영속 경로 설정 |
| `MONITORING_WEBHOOK_URL` | watchdog 알림 HTTP POST 수신 주소 | 선택값이며 비밀 URL 취급. 코드에서만 읽음 |

현재 실제 코드에서 확인되지 않은 설정은 문서에 가정해서 추가하지 않았습니다. `.env.example` 변경은 로컬 개발용 예시와 동일한지 유지하세요.

## 실행과 중지

각 명령은 별도 터미널에서 실행합니다.

```sh
make up
(cd backend && .venv/bin/python -m jevtriage.db.schema)
backend/.venv/bin/python scripts/bootstrap_dev.py
make api       # http://localhost:8000
make worker    # 시험/E2E는 --tenant <전용 tenant> 또는 WORKER_TENANTS 지정
make collector
make watchdog
make web       # http://localhost:5173
```

API 준비 상태는 `/api/health`와 `/api/ready`에서 확인합니다. 웹 앱의 `/api` 요청은 Vite 개발 프록시를 거칩니다. 종료는 각 터미널에서 Ctrl-C 후 `make down`으로 Neo4j를 정지합니다. worker는 중지 신호에서 새 Job 수신을 중단하고 진행 중 작업을 정리합니다. 전체 절차와 복구는 [운영 Runbook](docs/operations/RUNBOOK.md)을 참고하세요.

`JEV_MODE=live`는 실제 Jev API를 호출하며 서버 `JEV_API_KEY`가 필요합니다. `JEV_MODE=mock`은 장애 시험 등 명시적 로컬 시험에서만 사용하고, 저장된 결과도 모의 모드로 표시합니다. mock 결과는 live 연동 또는 인수 증거가 아닙니다. 민감한 실데이터를 mock 또는 live 데모에 사용하지 마세요.

## 검사와 평가

```sh
make test          # 백엔드 pytest + 프런트 Vitest
make test-fault     # 별도 Neo4j 기반 장애 시험
make backup BACKUP_DIR=/secure/path/backup-id \
  COMPOSE_PROJECT=jevtriage-backup NEO4J_CONTAINER=jevtriage-backup-neo4j-1 \
  NEO4J_BOLT_PORT=7689 NEO4J_DATA_DIR="$PWD/.data/neo4j" DATA_DIR="$PWD/.data"
make restore BACKUP_DIR=/secure/path/backup-id RESTORE_DATA_DIR=/srv/jevtriage-restored \
  COMPOSE_PROJECT=jevtriage-backup NEO4J_CONTAINER=jevtriage-backup-neo4j-1 NEO4J_BOLT_PORT=7689
make lint
make typecheck
make build
cd frontend && npm run e2e
backend/.venv/bin/python eval/runner.py --split tuning --max-samples 60 --concurrency 2 --retries 1
```

E2E worker는 전용 tenant allowlist로 제한하고, 실행한 API·worker·Vite를 모두 종료하세요. E2E와 live 평가의 자격 증명 및 비용, 안전한 입력 관리 지침은 해당 시험 문서를 따릅니다. [평가 안내](eval/README.md)는 저장소 안 `eval/README.md`를 참고하세요.

## 운영 문서와 알려진 제한

- [운영 Runbook](docs/operations/RUNBOOK.md)
- [백업과 복원](docs/operations/BACKUP_RESTORE.md)
- [데이터 처리](docs/operations/DATA_HANDLING.md)
- [배포 전 확인](docs/operations/DEPLOYMENT.md)
- [설정 목록](docs/operations/CONFIG.md)

현재 개발 인증은 bootstrap 계정이며 실제 운영 인증 공급자와 비밀 관리가 연결되지 않았습니다. 로컬 watchdog만으로 호스트 전체 유실을 감지할 수 없습니다. 데이터 보존 기간·삭제 정책, 원격 관측 수집, 운영 알림 수신자, 장애복구 목표, 배포 보안 검토는 미확정 또는 미검증입니다. [운영 전제와 제한](docs/operations/DEPLOYMENT.md#운영-전-확정할-사항) 및 [T26 검증 기록](artifacts/validation/t26/README.md)을 확인하세요.
