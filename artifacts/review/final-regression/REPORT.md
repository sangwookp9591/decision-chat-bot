# 최종 회귀 검증 (FINAL-REG)

## 판정

**브라우저 최종 합산: 199 passed, 0 failed, 1 skipped, 0 미실행 (25개 파일 × Chromium/WebKit, 200개 시험).** 최초 전체 실행 뒤 실패 및 serial 후속 미실행을 재검증해 합산한 결과이며, 한 번의 전체 실행이 모두 녹색이었다는 뜻은 아니다. 백엔드 최종 532 passed / live 전용 1 skipped, ruff 0건, import 계약 6개 통과. 최종 프런트 typecheck·Vitest 372개·build와 장애 시험 11개도 모두 통과했다.

- 시작: 2026-10-05 20:36:22 KST. 종료: 2026-10-05 21:51:39 KST. **총 벽시계 시간 75분 17초** (fixture 준비, 재검증, 보고서 및 정리 포함; 백엔드/초기 프런트는 브라우저와 일부 병렬).
- 최초 코드 `d763b5d`; 재검증 코드 `f699b64`. 제품 수정은 코디네이터가 수행했고 이 worker는 제품 코드를 수정하지 않았다. Git commit/push 없음.
- API `127.0.0.1:11791`, Vite `127.0.0.1:9191`. 공유 Neo4j `7687`와 기존 서버 `8191/5391`은 정지하거나 변경하지 않았다. Docker context는 `orbstack`; Docker Desktop 사용 없음.
- 모든 실행 `JEV_MODE=mock`, **실제 Jev 호출 0건**. `scripts/e2e/mock_worker.py`의 mock 단언과 결정적 client를 사용했다. 실제 HTTP/API/Neo4j 경로를 검증하며, 신규 UI 전용 회귀 일부는 해당 spec의 route fixture를 사용한다. 실 Jev 품질 증거가 아니다.
- 모든 Playwright 실행 `--workers=1`, retry 0. a11y도 단일 worker. 브라우저 inventory와 파일·suite·시험 제목·browser를 키로 비교해 빠진 시험 0건을 확인했다.

## 파일·브라우저별 최종 결과

| 파일 (`frontend/e2e/`) | Chromium 통과/실패/skip/미실행 | WebKit 통과/실패/skip/미실행 |
|---|---:|---:|
| `a11y/a11y.spec.ts` | 6/0/0/0 | 6/0/0/0 |
| `acceptance/gates.spec.ts` | 2/0/0/0 | 2/0/0/0 |
| `acceptance/scenarios.spec.ts` | 10/0/0/0 | 10/0/0/0 |
| `chat-intake.spec.ts` | 14/0/0/0 | 14/0/0/0 |
| `evaluation-labels.spec.ts` | 2/0/0/0 | 2/0/0/0 |
| `extension/extension-r.spec.ts` | 6/0/0/0 | 6/0/0/0 |
| `extension/extension.spec.ts` | 8/0/0/0 | 8/0/0/0 |
| `judgment-map.spec.ts` | 2/0/0/0 | 2/0/0/0 |
| `learning-human.spec.ts` | 1/0/0/0 | 1/0/0/0 |
| `learning.spec.ts` | 1/0/0/0 | 1/0/0/0 |
| `main.spec.ts` | 2/0/0/0 | 2/0/0/0 |
| `modal-stack.spec.ts` | 1/0/0/0 | 1/0/0/0 |
| `monitoring.spec.ts` | 1/0/0/0 | 1/0/0/0 |
| `observatory-stale.spec.ts` | 1/0/0/0 | 1/0/0/0 |
| `p7-fixes.spec.ts` | 7/0/0/0 | 6/0/1/0 |
| `policy.spec.ts` | 1/0/0/0 | 1/0/0/0 |
| `progressive-results.spec.ts` | 1/0/0/0 | 1/0/0/0 |
| `realtime-lists.spec.ts` | 3/0/0/0 | 3/0/0/0 |
| `rem-ui.spec.ts` | 3/0/0/0 | 3/0/0/0 |
| `responsive-overflow.spec.ts` | 14/0/0/0 | 14/0/0/0 |
| `review-repair.spec.ts` | 1/0/0/0 | 1/0/0/0 |
| `screens-ui.spec.ts` | 3/0/0/0 | 3/0/0/0 |
| `source-viewer/source-viewer.spec.ts` | 7/0/0/0 | 7/0/0/0 |
| `task-blocker.spec.ts` | 2/0/0/0 | 2/0/0/0 |
| `webmcp.spec.ts` | 1/0/0/0 | 1/0/0/0 |

유일한 브라우저 skip은 `p7-fixes.spec.ts:55` WebKit의 LayoutShift PerformanceEntry 미지원이다. 같은 파일의 두 provisional→final 위치·높이 직접 비교 시험은 두 브라우저 모두 통과했다. 최초 serial 실패에 따라 미실행된 acceptance 3개와 source-viewer 4개는 새 fixture 재실행에서 모두 통과했으며 최종 skip으로 남기지 않았다. extension의 phase별 조건은 해당 단계에서 각각 실행했고 미실행·중복으로 세지 않았다.

## 실행별 증거와 결과

원시 파일은 `.gitignore`로 제외한 로컬 증거다. 아래 경로는 이 보고서 디렉터리 기준이다.

| 실행 | 결과 | Playwright 시간 | 로컬 증거 |
|---|---|---:|---|
| 최초 기본 전체, 두 브라우저 | 156 pass / 8 fail / 1 명시적 skip / 7 serial 미실행 | 2093.52초 | `20261005T203622/results.json`, `results.log` |
| 확장 ui1 | 10 pass | 209.28초 | `20261005T203622/extension/ui1.json` |
| 확장 r1 | 10 pass | 149.54초 | `20261005T203622/extension/r1.json` |
| 확장 ui2 | 5 pass / 1 fail | 127.32초 | `20261005T203622/extension/ui2.json` |
| 확장 r3, API·worker 재시작 | 2 pass | 18.29초 | `20261005T203622/extension/r3.json` |
| WebKit 실패 파일 전체와 serial 후속 재검증 | 24 pass / 1 fail(평가 시험 전체 시간) | 약 13.0분 | `20261005T212930/results.json`, `results.log` |
| 평가·접수·맵 필터 최종 재검증, 두 브라우저 | 10 pass / 0 fail | 약 1.8분 | `20261005T214328/results.json`, `results.log` |

최초 runner 종료 코드 1과 WebKit 재검증 종료 코드 1을 보존했다. 마지막 runner는 코드 0이다. 각 runner는 새 tenant·역할 계정·목록 표본·fault tenant를 준비하고 소유한 API·worker·Vite를 종료했다. 확장 맵 최종 재검증은 최초 extension의 `db_truth.pre.json`과 보존된 독립 tenant를 사용해 같은 저장 그래프를 재대조했다.

## 실패 분류, 수정 전 재현, 조치, 재검증

### FR-01 — 제품 회귀: 불확실 평가 라벨 HTTP 422 (코디네이터 수정)

- **수정 전 실패:** `evaluation-labels.spec.ts:12` Chromium·WebKit. 네 번째 표본을 보류한 뒤 64행 성공 toast 대기가 실패했다.
- 요청: `PUT /api/evaluation/candidates/tuning/pharma-004`, `labels.ai_need="정보 부족"`, `status="deferred"`, `reason="검토 표본 보류"`. 응답은 422, `detail.details.fields.ai_need="허용된 선택지 중 하나를 선택해야 합니다."`.
- 원인: frontend `evaluation/options.ts`의 AI 필요성·개발 가능성 “정보 부족”, 긴급도 “판단 보류”가 backend `evaluation/service.py:LABEL_OPTIONS`에서 누락됐다. 기존 E2E가 그대로 실패 재현 시험이다.
- 코디네이터에 보고했고 코디네이터가 `f699b64`에서 허용값과 단위 회귀 시험을 추가했다. worker 제품 수정 없음.
- **수정 후:** 새 API에서 보류 저장 HTTP 성공과 toast가 확인됐다. 마지막 두 브라우저 평가 각 2개 모두 통과했고, backend 전체도 532 passed / 1 live skip으로 재검증했다.

### FR-02 — 시험 대기: 접수 완료 이전에 진행 UI를 5초만 기다림

- **수정 전 실패:** WebKit `main.spec.ts:10`은 `분석 진행` heading 대기 5초를 초과했다. error-context에는 첨부 업로드 100%, “보내는 중…”이 표시되어 있었고 접수 응답 처리 전이었다.
- **시험 수정:** `frontend/e2e/main.spec.ts`가 POST `/api/requests` HTTP 202를 먼저 확인한다. 클릭 전에 MutationObserver를 설치해 실제 표시된 진행 heading과 내용 정리·Jev 판단·근거 연결을 기록한다. 진행 화면의 순간 표시를 놓치지 않으며, 해당 단계가 실제 표시돼야 통과한다. 진행 관찰 제한은 30초이고 최종 저장 결과·환경 모드·근거 원문 검증은 유지했다.
- **수정 후:** WebKit 재검증 및 마지막 Chromium·WebKit 각 접수 2개 모두 통과했다.

### FR-03 — 복합 시험의 전체 30초 예산 부족

- **수정 전 실패:** Chromium extension ui2 맵 필터 시험은 30초 전체 제한을 초과했다. 새 API에서 422가 해소된 WebKit 평가 시험도 네 번 저장 및 보류 성공 toast 이후 마지막 progress GET에서 전체 30초 제한을 초과했다. 개별 제품 assertion 실패가 아니다.
- **시험 수정:** `evaluation-labels.spec.ts:12`의 네 표본 결정·조회 시나리오, `extension/extension.spec.ts:259`의 네 필터/API 대조·zoom 시나리오에 각각 `test.setTimeout(60_000)`을 명시했다. 선택자·기대값·권한/수치 assertion은 유지했다.
- **수정 후:** 두 브라우저의 평가·맵 필터 모두 통과했다. 최종 WebKit 평가 8.0초, 맵 필터 11.0초로 종료했다.

### FR-04 — 일시적 실행 지연으로 분류한 최초 WebKit 실패

| 최초 실패 | 관측 증거 | 조치 / 재검증 |
|---|---|---|
| acceptance S7 | target visible/enabled/stable, `performing click action`에서 15초 초과 | 코드 변경 없이 새 fixture; S1–S9·G10 10개 모두 통과 |
| policy | 시험 전체 30초 초과 | 코드 변경 없이 새 fixture; 5.9초 통과 |
| realtime Escape | 제품 업무 동작 전 로그인 POST 15초 초과 | 코드 변경 없이 새 fixture; 32.6초 전체 시나리오 통과 |
| realtime 두 탭 | 첫 탭 “완료로 변경” 표시 대기 15초 초과 | 코드 변경 없이 새 fixture; 34.9초 전체 시나리오 통과 |
| source-viewer 권한 | 권한 안내 문구 표시 대기 5초 초과 | 코드 변경 없이 새 fixture; 3.3초 통과, 후속 4개도 통과 |

기능 기대값을 낮추거나 force click·무조건 sleep·자동 retry로 덮지 않았다. 첫 실행은 WebKit 시나리오 시간이 점차 증가했고 새 프로세스·새 tenant 재실행에서는 동일 실패가 재현되지 않았다. 일시적 환경/실행 지연이라는 분류는 관측에 근거한 추정이며 근본적인 host 지연 원인을 확정한 성능 진단은 아니다. 최초 trace와 로그는 모두 남아 있다.

## 백엔드·프런트·장애 검사

| 검사 | 결과 | 증거 |
|---|---|---|
| 최초 `cd backend && JEV_MODE=mock .venv/bin/pytest -q` | 531 passed / 1 skipped, 153.37초 | `backend-pytest.log` |
| `f699b64` backend 전체 재검증 | 532 passed / 1 skipped, 169.73초 | `backend-pytest-final.log` |
| `.venv/bin/ruff check jevtriage tests` | All checks passed, 0건 | `ruff-final.log` |
| `.venv/bin/lint-imports` | Contracts: 6 kept, 0 broken | `lint-imports-final.log` |
| frontend 최초 typecheck / vitest / build | 모두 통과, Vitest 42 files / 372 tests | `checks.json` 및 각 log |
| frontend 시험 보강 후 최종 typecheck / vitest / build | 모두 통과; typecheck 1.10초, Vitest 42 files / 372 tests (21.76초), build 2.22초 | `final-checks.json` 및 `*-final.log` |
| `make test-fault` 1회 | 11 passed / 0 failed / 0 skipped, pytest 232.09초 (컨테이너 준비·정리 포함 255.58초) | `fault.log`, `fault/20261005T124634Z/` |

백엔드 skip 1건은 `tests/live/test_judgment_live.py`의 live Jev 자격증명 전용 시험이다. 실제 Jev 0건 지시에 따라 의도적으로 실행하지 않았다. 그 외 요청된 시험 범위를 건너뛰지 않았다.

## 실행 재현 및 정리

`scripts/e2e/run.py` 방식으로 로컬 `run.py`·`extension_suite.py` 복사본을 만들고 repo ROOT, 산출물 디렉터리, API 11091→11791, Vite 8491→9191만 치환했다. Vite proxy도 11791로 맞췄다. 제품 runner는 수정하지 않았다.

```sh
# 로컬 전용 runner (원본 scripts/e2e/run.py와 동일한 mock 준비/정리)
backend/.venv/bin/python artifacts/review/final-regression/run.py
# WebKit 재검증
backend/.venv/bin/python artifacts/review/final-regression/run.py \
  'acceptance/scenarios.spec.ts$|evaluation-labels.spec.ts$|main.spec.ts$|policy.spec.ts$|realtime-lists.spec.ts$|source-viewer/source-viewer.spec.ts$' --project=webkit
# 최종 평가·접수·맵 필터 (X38_OUT/TENANT/PHASE/TRUTH는 최초 extension fixture)
X38_OUT="$PWD/artifacts/review/final-regression/20261005T203622/extension" \
X38_TENANT=t-e2e-1005203622x X38_PHASE=ui2 X38_TRUTH=pre \
backend/.venv/bin/python artifacts/review/final-regression/run.py \
  'evaluation-labels.spec.ts$|main.spec.ts$|extension/extension.spec.ts$' \
  --grep 'labeler|final split|live request|live damaged|criteria filters'
```

마지막 브라우저 runner 종료 뒤 API 11791·Vite 9191·장애 전용 7688이 모두 비어 있음을 확인하고 장애 시험을 시작했다. 장애 시험은 브라우저 실행과 겹치지 않았다. 최종 검증에서 API 11791·Vite 9191·Bolt 7688 모두 미사용, 소유한 API·worker 잔여 0건, `jevtriage-fault-neo4j` 컨테이너 없음, `.data/neo4j-fault` 없음, 공유 Neo4j running=true를 확인했다 (`cleanup.json`).


### 장애 시험 상세

`make test-fault`는 단 한 번 실행했고 종료 코드 0이었다. 브라우저 마지막 runner가 종료되고 전용 포트가 해제된 뒤 시작했다.

- mock Jev timeout·429·529·schema: 실패 Run, Assignment 0건.
- 파서 손상·Neo4j pause/unpause: HTTP 503와 독립 미확정 journal 표본, 복구 후 정상 접수.
- worker SIGSTOP 인계·SIGKILL 복구: generation 1→2→3, 정식 Judgment 1건.
- API 재시작·SSE: cursor 1→2, 재연결 3404ms, 표본 1건. 5000ms 시험 기준 내지만 운영 p95 달성 근거로 확대하지 않는다.
- 정책 도중 변경: Run 버전 1→2→3 고정; 병렬 검토 20건: 성공 1·409 19, Assignment 1·Task 1, 승자 멱등 재전송 200·과거 승인 409.
- 관측 중단·journal 권한 오류: alert 2종, 중복 ID 0, reconciliation 누락/불일치 없음.
- 정보 보완 대기·121초 후 회복: 최초 실패 표본을 보존하고 late recovery 1건 기록.
- fault 내부 `process_cleanup.remaining={}`. 외부 포트·컨테이너·데이터 경로 정리도 별도 확인.

fault script가 생성한 `artifacts/validation/t22/20261005T124634Z`는 실행이 끝난 뒤 이 보고서의 `fault/20261005T124634Z`로 옮겨 원시 증거를 Git에서 제외했다. 원본 junit/report 안의 출력 경로는 실행 당시 경로다.

## 변경 파일 / 남은 범위

시험 파일 3개(`main.spec.ts`, `evaluation-labels.spec.ts`, `extension/extension.spec.ts`), `.gitignore`, 이 보고서, `docs/architecture/FINAL_REGRESSION.md`만 이 worker가 변경했다. frontend/backend 제품 코드는 수정하지 않았다. 관련 아키텍처 문서는 [최종 회귀 검증 계약](../../../docs/architecture/FINAL_REGRESSION.md)을 참조한다.

미해결 재현 제품 결함과 미실행 필수 시험은 없다. 남은 명시적 제외는 WebKit LayoutShift 지원 부재 1건, live Jev 전용 backend 1건이다. 최초 실행의 일시적 지연 원인은 확정하지 않았으므로, CI/호스트 성능 안정성의 보편적 보증은 이 결과의 범위 밖이다.
