# CHAT-POLISH 검증 자료

- 전용 포트: API 9791, vite 7091 (수정 전 비교용 7092 = HEAD fdf275c 사본, `before/`). 테넌트 `t-chatpol` — 요청 34건 시드(목 worker로 판단 처리 후 `--tenant t-chatpol` 제한 live worker로 교체), requester에 `can_read_source=true`(목록 제목을 보려면 필요).
- 실행: `E2E_BASE_URL=http://127.0.0.1:7091 E2E_TENANT=t-chatpol E2E_REQUESTER=requester@t-chatpol.dev CHAT_SHOT_DIR=../artifacts/review/chat-polish npx playwright test e2e/chat-intake.spec.ts e2e/main.spec.ts e2e/progressive-results.spec.ts --project=chromium|webkit`
- `metrics.jsonl`: 폭별(1440/960/375) 문서 높이·창 높이·가로 폭. 수정 전(`before/metrics.jsonl`)은 3505/986/1044px였다.
- 캡처: `{chromium,webkit}-{greeting,list,conversation,detail}-{1440,960,375}.png`, `list-open-*`, `file-failure`, `info-request`, `result`.
