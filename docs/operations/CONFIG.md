# 설정 참조

`.env`는 로컬 비밀 파일이며 저장소에 커밋하지 않는다. 애플리케이션 설정은 `backend/jevtriage/config.py`와 `.env.example`, Compose는 `docker-compose.yml`을 기준으로 확인했다.

| 설정 | 사용처 | 기본값/동작 |
| --- | --- | --- |
| `JEV_API_KEY` | Jev SDK 서버 인증 | 비어 있으면 live 호출 불가. 비밀값 |
| `JEV_MODE` | 판단 클라이언트 | `live` 기본값, `mock`은 명시적 모의 시험 |
| `NEO4J_URI` | Python 드라이버 | `bolt://localhost:7687` |
| `NEO4J_USER` | Python 드라이버·Compose 인증 | `neo4j` |
| `NEO4J_PASSWORD` | Python 드라이버·Compose 인증 | 로컬 전용 `development-only`; 운영 교체 필요 |
| `DATA_DIR` | 파일·journal·metrics·알림 저장 | `.data` (상대 경로는 프로세스 현재 디렉터리 기준) |
| `NEO4J_CONNECTION_TIMEOUT_SECONDS` | Neo4j 연결 | 3초 |
| `NEO4J_CONNECTION_ACQUISITION_TIMEOUT_SECONDS` | Neo4j 연결 풀 대기 | 5초 |
| `NEO4J_TRANSACTION_RETRY_SECONDS` | Neo4j 트랜잭션 재시도 | 3초 |
| `API_REQUEST_TIMEOUT_SECONDS` | API 요청 처리 | 30초 |
| `MONITORING_WEBHOOK_URL` | watchdog 알림 | 선택. `watchdog.py`가 환경에서 직접 읽음 |
| `JEVTRIAGE_DEV_PASSWORD` | 개발 계정 bootstrap | 미설정 시 bootstrap의 개발 기본값. 운영에 사용 금지 |
| `WORKER_TENANTS` | worker tenant 제한 | 쉼표 구분 목록; CLI `--tenant`가 우선 |

Settings는 필드 이름의 대문자 환경 변수를 사용한다. `.env.example`에는 위 모든 내부 timeout, webhook, bootstrap, worker 값을 포함하지 않으므로 이 표는 실제 코드가 읽는 설정 목록이다. 개발 기본값은 운영 비밀 관리 대안이 아니다. `DATA_DIR`는 모든 관련 프로세스에서 같은 절대 영속 경로를 지정하는 편이 안전하다.
