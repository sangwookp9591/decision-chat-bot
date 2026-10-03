# T01 검증 기록

실행 환경: Python 3.14.6, Node.js 22.14.0, Docker Compose 2.32.4.

## 실행 명령과 결과

- `python3 -m venv backend/.venv` — 새 가상환경 생성 완료.
- 임시 새 venv에서 `pip install -r backend/requirements.lock` — 고정한 백엔드 의존성 설치 성공. 앱 코드는 `cd backend` 실행 경로에서 import합니다.
- `npm --prefix frontend install` 후 `npm --prefix frontend ci --no-audit --no-fund` — lock 동기화 및 클린 설치 성공.
- `docker compose up -d neo4j` — Neo4j 5.26.0-community 시작, health `healthy`.
- `NEO4J_PASSWORD=development-only backend/.venv/bin/python ... TestClient ... GET /api/ready` — 실제 Neo4j 연결, HTTP 200 `{"status":"ready"}`.
- `docker compose stop neo4j` 후 같은 준비상태 호출 — HTTP 503 `{"detail":"Neo4j unavailable"}` 확인; 검증 뒤 `docker compose start neo4j` 실행.
- `NEO4J_PASSWORD=development-only make test` — pytest 3 passed(health, DB 미가용, 실제 Neo4j readiness); Vitest 1 passed.
- `make lint` — Ruff 통과.
- `make typecheck` — TypeScript 검사 통과.
- `make build` — Vite 프로덕션 빌드 통과.

Starlette TestClient에서 httpx 관련 deprecation warning과 React Router의 v7 future flag 안내가 출력됐습니다. 실패한 검증은 없습니다. 실제 readiness 검증은 로컬 Neo4j 자격 증명으로 실행했고 어떤 키 값도 증거에 기록하지 않았습니다.
