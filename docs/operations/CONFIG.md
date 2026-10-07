# 설정 참조

`.env`는 로컬 비밀 파일이며 저장소에 커밋하지 않는다. 애플리케이션 설정은 `backend/ildongi/config.py`와 `.env.example`, Compose는 `docker-compose.yml`을 기준으로 확인했다.

## JEV 설정에서 이전

기존 설정은 `JEV_API_KEY`→`AI_API_KEY`, `JEV_MODE`→`AI_MODE`, `JEV_MOCK_*`→`AI_MOCK_*`로 이름을 바꾸세요. 쿠키 이름 변경으로 기존 로그인 세션은 만료되어 다시 로그인해야 합니다. `AI_NAME` 또는 `AI_MODEL` 변경 후 API·worker를 재시작하고 프런트엔드를 다시 빌드해야 하며, 개발 중에는 Vite dev 서버를 재기동하세요.

| 설정 | 사용처 | 기본값/동작 |
| --- | --- | --- |
| `AI_API_KEY` | Decision AI SDK 서버 인증 | 비어 있으면 live 호출 불가. 비밀값 |
| `AI_MODE` | 판단 클라이언트 | `live` 기본값, `mock`은 명시적 모의 시험 |
| `NEO4J_URI` | Python 드라이버 | `bolt://localhost:7687` |
| `NEO4J_USER` | Python 드라이버·Compose 인증 | `neo4j` |
| `NEO4J_PASSWORD` | Python 드라이버·Compose 인증 | 로컬 전용 `development-only`; 운영 교체 필요 |
| `DATA_DIR` | 파일·journal·metrics·알림 저장 | `.data` (상대 경로는 프로세스 현재 디렉터리 기준) |
| `NEO4J_CONNECTION_TIMEOUT_SECONDS` | Neo4j 연결 | 3초 |
| `NEO4J_CONNECTION_ACQUISITION_TIMEOUT_SECONDS` | Neo4j 연결 풀 대기 | 5초 |
| `NEO4J_TRANSACTION_RETRY_SECONDS` | Neo4j 트랜잭션 재시도 | 3초 |
| `API_REQUEST_TIMEOUT_SECONDS` | API 요청 처리 | 30초 |
| `MONITORING_WEBHOOK_URL` | watchdog 알림 | 선택. `watchdog.py`가 환경에서 직접 읽음 |
| `ILDONGI_DEV_PASSWORD` | 개발 계정 bootstrap | 미설정 시 bootstrap의 개발 기본값. 운영에 사용 금지 |
| `WORKER_TENANTS` | worker tenant 제한 | 쉼표 구분 목록; CLI `--tenant`가 우선 |
| `AI_NAME` | 화면·단계에 보이는 판단 AI 이름 | `Decision AI`. 백엔드와 Vite 빌드가 함께 읽음 |
| `AI_MODEL` | 판단 AI 모델 ID | `jev-1.13.0` (제공자 실제 ID) |
| `LLM_MODE` | LLM 글쓰기 보조 | `live` 기본값, `fake`는 외부 호출 없는 시험, `off`는 끔. [LLM 보조](../architecture/LLM_ASSIST.md) |
| `ANTHROPIC_API_KEY`·`OPENAI_API_KEY`·`GEMINI_API_KEY` | LLM 제공자 인증 | 선택. 비밀값. 제공자·모델·기능은 정책 화면에서 고름 |
| `CHATGPT_AUTH_REDIRECT_PORT` | ChatGPT 구독 연결 콜백 포트 | `8000`. 경로는 `/auth/callback` 고정, 127.0.0.1 루프백 |
| `CHATGPT_AUTH_RETURN_URL` | 연결 후 돌아갈 웹 화면 | `http://127.0.0.1:5173/policy` |
| `MCP_AUTH_MODE` | ChatGPT 플러그인 MCP 서버 | `dev`를 명시해야 기동. [플러그인 안내](../mcp/CHATGPT_PLUGIN.md) |
| `MCP_DEV_USER` | MCP 개발 사용자 | `requester@t-alpha.dev`; 실제 계정의 권한으로 조회 |
| `MCP_HOST`·`MCP_PORT` | MCP 서버 주소 | `127.0.0.1`·`8787`; 루프백만 허용 |
| `MCP_SSE_ENABLED` | `/mcp/stream` SSE 엔드포인트 | 기본 꺼짐. 기본 `/mcp`는 JSON 응답 |
| `MCP_ALLOW_SUBMIT` | `submit_request` 도구 노출 | 기본 꺼짐(조회 도구 4개만) |
| `CONTROL_PLANE_API_KEY`·`CONTROL_PLANE_TUNNEL_ID` | OpenAI Secure MCP Tunnel(대안 경로) | 선택. 비밀값. Quick Tunnel 사용 시 불필요 |

Settings는 필드 이름의 대문자 환경 변수를 사용한다. `.env.example`에는 위 모든 내부 timeout, webhook, bootstrap, worker 값을 포함하지 않으므로 이 표는 실제 코드가 읽는 설정 목록이다. 개발 기본값은 운영 비밀 관리 대안이 아니다. `DATA_DIR`는 모든 관련 프로세스에서 같은 절대 영속 경로를 지정하는 편이 안전하다.
