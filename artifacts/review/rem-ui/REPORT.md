# REM-UI 수정 및 검증

작업일: 2026-10-04

## 수정 사항

- 검토 목록은 Request의 저장된 마스킹 `title`을 제목으로 사용하며 값이 없으면 `제목 없는 요청`을 표시한다. 긴급도와 짧은 요청 ID는 보조 줄에 둔다. review 목록 응답의 제목은 항상 제공하고 `preview`는 `can_read_source` 또는 작성자 요청 읽기 권한일 때만 제공한다.
- 검토 상세의 원문 조회 실패 원인은 검토 접근과 요청 상세 접근의 권한 범위가 다르기 때문이다. `/api/reviews/{id}`는 `can_review`를 허용하지만 `/api/requests/{id}`는 별도로 `can_view_request` 범위를 요구해 검토 조직만 가진 사용자는 404를 받는다. 검토 API는 현재 revision의 `request_text`를 `can_read_source=true`인 경우에만 반환하도록 했고, 그 외에는 제목 및 정책상 허용된 마스킹 요약과 “원문 열람 권한이 없습니다. 제목과 허용된 마스킹 요약만 표시합니다.” 안내를 표시한다.
- 판단 결과 상세의 실행·revision 메타는 접힌 “자세히 보기” 안에 두고 공용 `ShortId` 칩을 사용한다. 대화 요약 카드에는 ID 줄을 노출하지 않는다.

## 재현 시험 → 수정 → 통과

| 항목 | 수정 전 실패 | 수정 후 검증 |
| --- | --- | --- |
| 검토 목록 제목·요약 | `Review.test.tsx`에서 제목/요약이 없어 제목 버튼을 찾지 못함 | Vitest 제목·권한 테스트 통과; API 통합 테스트에서 제목 상시 제공 및 source 권한별 preview 검사 통과 |
| 검토 상세 원문 | `test_review_display.py`에서 source-reader 응답의 `request_text` 키가 없어 실패. 코드 확인으로 `/api/requests/{id}` 404는 review 권한과 요청 scope 권한이 별도인 데서 발생함을 확인 | 원문 권한 없는 응답에는 원문 필드가 없고, source reader에는 revision 원문이 제공됨. pytest 3건 통과. Chromium·WebKit에서 source reader/일반 reviewer 상세 확인 |
| 판단 카드 ID | `Main.test.tsx`에서 원시 run ID가 정규 화면에 포함되어 실패 | 판단 상세 ID 축약·상세 영역 시험 통과. Chromium·WebKit 캡처/E2E 통과 |

## 실행 결과

- `backend/.venv/bin/pytest -q`: **466 passed, 1 skipped**.
- `frontend`: typecheck 통과, 전체 Vitest **3회 연속 각 358 passed / 40 files**, build 통과.
- REM-UI 전용 Playwright: Chromium·WebKit 각각 검토 목록/권한별 상세/판단 카드 캡처; **6 passed**.
- `ruff check jevtriage/review tests/integration/test_review_display.py`: 통과.
- 전체 `ruff check jevtriage tests`: 최종 통과(0건).
- `lint-imports`: 최종 통과(6 contracts kept, 0 broken). 병렬 REM-CANCEL 수정이 완성되기 전 중간 실행에서만 main.py import 정렬과 ingest→jobs 계약 실패가 보였으며, 마지막 재실행에서 해소됨을 확인했다.
- E2E는 OrbStack 컨텍스트의 공유 Neo4j를 계속 실행한 상태로 전용 API 10091/Vite 7391 및 `t-rem-ui-20261004`만 사용했다. 두 서버와 tenant 테스트 노드는 시험 후 종료·삭제했다. 브라우저 캡처는 이 폴더의 `chromium-*.png`, `webkit-*.png`에 보관한다.

## 건너뛴 항목

- REM-UI 항목 중 건너뛴 기능은 없다.
