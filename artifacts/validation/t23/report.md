# T23 접근성·반응형·브라우저 검증 결과

실행일: 2026-10-03 · 환경: 로컬 Neo4j, 실제 API, `t-t23` 전용 tenant worker. 요청 2건으로 제출·판단·검토 결정을 확인했다. worker는 `--tenant t-t23`으로 한정했고 검증 후 API/worker를 종료했다.

## 결과

| 검증 | 실행 | 결과 |
| --- | --- | --- |
| axe WCAG 2.1 A/AA, critical/serious | Playwright chromium 및 webkit 각 10개 화면 (로그인 + 핵심 9개 화면; 맵 입체/목록 포함) | 양 브라우저 0건 |
| 브라우저/키보드 실제 흐름 | `E2E_API=http://127.0.0.1:8147 E2E_PORT=5283 npx playwright test --config=playwright.a11y.config.ts --project=webkit` | 6/6 통과: 실요청 제출→저장 판단→근거 열기→키보드 검토 승인→판단 맵 목록 이동·선택 포함 |
| Chromium 보조 시나리오 | `E2E_API=http://127.0.0.1:8147 E2E_PORT=5281 npx playwright test --config=playwright.a11y.config.ts --project=chromium --grep-invert 'keyboard submits a real request'` | 5/5 통과 |
| 반응형·접근성 계약 | 1280/960/520/375px, 메뉴 위치, 가로 스크롤, ChatWidget 전체 화면, 샘플 버튼 44px, Primary 글자색, 상태 아이콘+이름, 디자인 샘플/mock 표시 검사 | 양 브라우저 통과 |
| 모션/매체 | reduced-motion 정지 PNG 및 WebKit의 idle.webp 선택 | WebKit 통과 |
| 프런트 단위 시험 | `cd frontend && npm run test` | 11 파일, 34 통과 |
| 타입 검사 | `cd frontend && npm run typecheck` | 통과 |
| 전체 저장소 시험 | `make test` | 최종 실행: 123 통과, 1 skip, 1 실패. `tests/integration/test_ingest_api.py::test_http_rejects_attachment_count_and_total_bytes`가 400 대신 503을 반환함. T23 프런트 변경과 무관한 ingest 회귀로 남김. |

axe에서 발견한 빈 공용 버튼 텍스트, 잘못된 `aria-sort` 적용 위치, 채팅 모달의 포커스/닫기 동작을 수정했다. 수정 뒤 양 브라우저 주요 화면에서 critical/serious axe 위반이 없었다.

## 스크린샷

- [Chromium 520px ChatWidget](chromium-responsive-520.png)
- [WebKit 520px ChatWidget](webkit-responsive-520.png)

## 남은 제한

백엔드 전체 시험은 위 ingest 테스트 실패 때문에 완전 통과가 아니다. Safari 동작은 Playwright WebKit 엔진으로 확인했으며 실제 macOS Safari 앱 버전별 수동 시험은 별도 수행하지 않았다.
