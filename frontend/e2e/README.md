# 정책 E2E

실제 Neo4j와 API를 사용하는 Playwright 시나리오입니다. 테스트는 `policy_editor@t-alpha.dev`로 로그인해 잘못된 threshold 검증, 정상 게시, 버전 이력 조회, v1 기준 되돌리기를 수행합니다.

저장소 루트에서 실행합니다.

```sh
make up
cd backend
.venv/bin/python ../scripts/bootstrap_dev.py
.venv/bin/uvicorn jevtriage.main:app --host 127.0.0.1 --port 8000
```

별도 터미널에서 프런트 테스트를 실행합니다.

```sh
cd frontend
npx playwright install chromium
npm run e2e
```

개발 계정 암호를 변경해 bootstrap한 경우 `JEVTRIAGE_DEV_PASSWORD`에 같은 암호를 지정합니다. API 서버와 Neo4j는 테스트가 끝날 때까지 실행 중이어야 합니다.
