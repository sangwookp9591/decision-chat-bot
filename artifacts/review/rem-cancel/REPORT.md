# REM-CANCEL: 진행 중 분석 취소

2026-10-04 · 전용 실행: API `127.0.0.1:10191`, Vite `127.0.0.1:7491`, tenant `t-rem-cancel-20261004`, worker `--tenant t-rem-cancel-20261004`, `JEV_MODE=live`, Docker context `orbstack`.

## 재현 → 수정

| 항목 | 수정 전 재현 | 수정 후 |
| --- | --- | --- |
| 대기 작업 | `test_pending_cancel_is_immediate_idempotent_and_audited`가 `jevtriage.jobs.cancel` 부재로 실패. 추가 모니터링 시험은 취소 journal 기록 부재로 실패 | Request·Run·Job을 한 트랜잭션에서 `cancelled`로 바꾸고 lease generation을 올림. 반복 호출은 200과 같은 상태. 이벤트·감사 필드·모니터링용 `worker_run(cancelled)` journal을 각 1건 기록. |
| 실행 작업 | `test_running_cancel_fences_late_result`가 같은 부재로 실패 | 단계 경계의 `ctx.commit`이 취소된 Job 소유권을 거부. 외부 호출 중 lease heartbeat는 취소를 확인하면 호출을 강제로 끊지 않고 반환 뒤 결과 쓰기를 차단. 진행 중 RunStep은 `cancelled`로 종료. |
| 완료·경합 | 취소 API 부재로 완료 후 계약 및 완료 경합 경로 없음 | 완료된 Run은 상태를 바꾸지 않고 200. 정식 Judgment 커밋과 취소가 겹치면 먼저 커밋된 결과에 맞춰 Run·Job 상태 수렴. `test_completed_cancel_is_idempotent_and_completion_race_converges` 통과. |
| 권한 | `request:cancel` 규칙 부재 | 작성자 또는 같은 tenant 운영자만 허용. 같은 tenant의 다른 작성자 거부, 다른 tenant 격리 시험 통과. API는 CSRF를 요구. |
| 화면 | `Main.progressive.test.tsx`에 정지 버튼 시험을 추가해 수정 전 실패(`분석 정지` 버튼 없음) 확인 | Composer 정지 버튼이 취소 API를 호출. `judgment.cancelled` SSE와 progress 복원 모두 '취소됨'을 표시. 잠정 결과는 흐리게 남기되 로딩을 끝냄. 같은 요청 재분석 제공. |

## 검증

- 백엔드 전체: 최종 코드 기준 `466 passed, 1 skipped` (`pytest -q`, 148.61초). 취소 전용 4건 통과.
- Ruff: 0건. import-linter: 6 contracts kept, 0 broken. `git diff --check`: 통과.
- fault: 독립 Neo4j 포트 7688에서 `11 passed` (199.20초), 기록은 `artifacts/validation/t22/20261004T134712Z/`.
- 프런트: 전체 vitest 3회 각각 `358 passed`; `npm run typecheck`, `npm run build` 통과.
- 실제 브라우저: Chromium·WebKit 각각 전송→정지→`cancelled`→같은 요청 재분석→최종 `mode=live` 확인, 총 2건 통과. 최종 UI 토큰 변경 후 다시 캡처했다: [Chromium 취소](chromium-cancelled.png), [Chromium 재분석](chromium-reanalyzed.png), [WebKit 취소](webkit-cancelled.png), [WebKit 재분석](webkit-reanalyzed.png). 전용 journal에는 `worker_run(cancelled)` 2건과 `worker_run(judgment_saved)` 2건이 남았다([집계](journal-summary.json)).

## 범위와 남은 점

- 전체 pytest의 기존 1건 skipped는 이번 취소 기능과 무관하다.
- 실제 브라우저 실행은 잠정 분류가 나오기 전에 정지됐다. 잠정 결과가 있는 취소 화면은 `Main.progressive.test.tsx`에서 API 취소 후 흐린 카드와 `aria-busy` 해제를 검증했다.
- 공유 Neo4j(7687)와 다른 작업자의 포트 8191·5391은 중단하지 않았다. 이 시험에서 시작한 API·worker·Vite만 종료했다.
