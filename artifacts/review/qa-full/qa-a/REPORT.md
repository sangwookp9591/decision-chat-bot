# QA-A 요청자·검토자·업무 담당자 여정 점검

> **최신 상태:** 아래 “재개 실행 — QA-A2”에서 전수 점검을 완료했다. Chromium 고유 62건 중 59건 통과·UI 결함 재현 3건, WebKit 핵심 6여정 통과, backend 531 passed·1 skipped 및 ruff 0건이다. 아래 원래 QA-A 실패 기록은 이력으로 보존한다.

**최종 결과: failed — 환경 차단으로 QA-A 전수 점검 미완료. 확정 제품 결함 0건이며, 무결함을 뜻하지 않는다.** 첫 실행은 9건 실패·77건 미실행, DB 복구 후 두 번째 실행은 1건 통과·2건 실패·119건 미실행이다. 시험 작성 오류와 환경 차단을 제품 결함으로 집계하지 않는다.

## 조건 및 증거

- 2026-10-05, 공유 current worktree. 제품 코드·docs/spec·docs/design-handoff·기존 시험은 변경하지 않았다. 커밋·push·외부 메시지 전송 없음.
- 전용 API 11291 / Vite 8691, tenant `t-qa-a-1005181556`; JEV_MODE=mock. `scripts/e2e/seed.py`, `mock_worker.py --tenant`를 재사용했다. 실제 Jev 호출 0건.
- `run.py`는 기존 `scripts/e2e/run.py` 방식으로 seed → API/제한 워커/Vite → Playwright → finally 소유 프로세스 종료를 수행한다. `playwright.config.ts`는 기존 `frontend/e2e/all.config.ts`를 확장한다.
- 전체 실행: [results.json](runs/20261005T181556/results.json), [results.log](runs/20261005T181556/results.log), [요약](results-summary.json). 실패별 screenshot/trace/error-context는 `runs/20261005T181556/results/`에 있다.
- 초기 준비 실행 `20261005T181322`는 QA 전용 Vite 설정의 ESM 디렉터리 import 실패. 파일 진입점 경로로 수정 후 기동 성공했으며 제품 실패로 세지 않았다.

## 환경 차단

Neo4j가 `Neo.ClientError.Transaction.TransactionTimedOutClientConfiguration`을 반환했다. backend 전체 시험은 247 passed 후 ingest_api 3 failed·3 errors가 동일 DB 시간 초과로 발생했고, QA mock 워커도 같은 예외를 기록했다. 읽기 전용 `SHOW TRANSACTIONS` 진단조차 같은 오류로 실패했으므로 DB 잠금의 원인/보유자를 확정하지 못했다.

API 로그인은 15초 시간 초과, 승인 준비는 5초 상태 대기 실패, 경합 시험은 120초 전체 시간 초과가 발생했다. 이 상태의 실패를 UI/SSE 제품 결함으로 잘못 보고하지 않도록 실행을 중단했다. 소유 pytest에는 SIGINT, 소유 Playwright에는 SIGINT를 전달했고 runner finally가 API·워커·Vite를 종료했다. 공유 Neo4j, Docker Desktop, 다른 작업자 포트/프로세스는 조작하지 않았다.

## 점검 체크리스트

`정상(부분)`은 해당 단계의 assertion은 성공했지만 전체 시험은 다른 이유로 실패했다는 뜻이다. `미점검`은 결함 판정이 아니다.

| 항목 | 방법 | 결과 | 근거 |
|---|---|---|---|
| 잘못된 암호 안내 | UI 이메일/암호 입력 → Enter | 정상(부분) | [캡처](runs/20261005T181556/acceptance/chromium-wrong-password.png), 로그인 시험 alert assertion 통과 |
| 정상 UI 로그인 | 암호 수정 → Enter → 인사 확인 | 정상(부분) | 로그인 시험 인사 assertion 통과 |
| 로그아웃 | 버튼 Enter | 미점검 | 두 로그아웃 버튼에 대한 strict selector 오류; `.first()`로 시험 수정, 재실행 필요 |
| 계정 잠금 | 10회 잘못된 암호 → 올바른 암호도 429 | 미점검 | `repro/boundaries.spec.ts` 작성, 환경 차단 후 미실행 |
| 빈 대화 인사·예시 칩 | 로그인 후 인사 확인, 첫 칩 Enter | 정상(부분) | journeys UI 로그인/키보드 시험의 앞 단계 통과 |
| Shift+Enter | 줄바꿈 입력 | 정상(부분) | error-context textarea에 줄바꿈 관찰; 이후 시험의 잘못된 `press('가')` 호출에서 중단 |
| Enter 전송·IME | 합성 composition 이벤트, Enter 요청 | 미점검 | 한글 입력을 keyboard.insertText로 수정, 재실행 필요; OS 네이티브 IME 검증은 별도 필요 |
| 긴 입력 | 20,001자 → 400·입력 보존 | 미점검 | boundaries 시험 작성, 미실행 |
| 첨부 5개 초과·제거 | 6개 선택 → 5개·안내 → 각각 제거 | 정상(부분) | journeys 첨부 시험의 파일 개수/안내 assertions 통과 |
| 10 MiB 초과 | 큰 MD 업로드 | 정상(부분)/화면 재검증 필요 | API 202. 계약은 전체 413 거절이 아니라 해당 파일 rejected/too_large 및 읽기 실패 선택으로 진행; 시험 가정 수정 |
| PDF·DOCX·MD 정상 파싱 | 기존 acceptance S5 | 미점검 | 대상 시험 선택됨, 환경 때문에 미실행 |
| 암호 PDF·확장자 위장 | 생성한 암호 PDF/위장 파일 → 제외 | 미점검 | boundaries 시험 작성, 미실행 |
| 손상 파일·제외·재첨부 | 기존 chat-intake/S5 | 미점검 | 대상 시험 선택됨, 미실행 |
| 정지·다시 분석 | 기존 chat-intake | 미점검 | 대상 시험 선택됨, 미실행 |
| 보완 질문·revision 2 | 기존 chat-intake | 미점검 | 대상 시험 선택됨, 미실행 |
| 새로고침 복원·새 요청 | 기존 chat-intake | 미점검 | 대상 시험 선택됨, 미실행 |
| 목록 날짜·제목·선택·960 이하 시트 | 기존 chat-intake layout | 미점검 | 대상 시험 선택됨, 미실행 |
| ↓ 버튼·복사 | 기존 chat-intake 및 추가 수동 확인 | 미점검 | 환경 차단 |
| 근거 원문 강조·중첩 Escape | 기존 modal-stack/source-viewer | 미점검 | modal-stack 선택되었으나 미실행; source-viewer 추가 실행 필요 |
| 잠정→최종 0px | bounding box 측정 필요 | 미점검 | 기존 p7은 4px 허용이므로 0px 요구의 증거로 재사용 불가 |
| 검토 필터·긴급 정렬·제목 | 기존 S3 및 화면 | 미점검 | 미실행 |
| 원문/AI 원안 비교 | 기존 S2/S6 | 미점검 | 미실행 |
| 승인 | 업무 준비에서 reviewer UI 승인 | 정상(부분) | 첫 업무 생명주기 시험은 승인 후 업무를 조회하고 전이 성공 |
| 수정 승인 정상/미정 초안 | 기존 S6/review-repair | 미점검 | 미실행 |
| 반려·정보 요청·사유 필수·두 검토자 경합 | journeys 및 기존 S4/S6 | 미점검 | jobs/준비 단계 환경 시간 초과, 경합 assertion 도달 못함 |
| 업무 대기→진행→완료·새로고침·완료 필터 | 실제 UI 승인 후 팀 담당자 UI | 정상(부분) | lifecycle 앞 단계 assertions 통과; [캡처](runs/20261005T181556/acceptance/chromium-task-complete.png) |
| 업무 팀·역할·방식 필터 | 필터 선택 | 미점검 | 선택 조작은 했으나 최종 포함성 검증 없음, 정상으로 주장하지 않음 |
| 선행 차단/해제 | 실제 승인된 업무 관계 필요 | 미점검 | 기존 task-blocker는 API 응답 모킹이므로 실제 업무 여정 증거로 사용하지 않음 |
| 권한 없는 전이 | requester로 transition API | 미점검 | 시험 payload의 to_status 오타로 422, to로 수정 후 재실행 필요 |
| 업무 상세 Escape | 실제 업무 행 Enter → Escape | 미점검/후보 | 승인 준비 실패로 본 assertion 도달 못함. 소스만으로 결함 확정하지 않음 |
| 다른 탭/다른 역할 SSE | 두 업무 탭에서 상태 전이 | 미점검/후보 | 로그인 시간 초과로 본 assertion 도달 못함 |
| 1440·375 / 라이트·다크 / 키보드 | 12개 화면 조합 시험 | 미점검 | 첫 두 조합 로그인 시간 초과. 캡처만으로 완료 주장 안 함 |
| WebKit 핵심 5여정 | 같은 설정의 WebKit 프로젝트 | 미점검 | Chromium 도중 환경 중단으로 WebKit 0건 실행 |

## 실패 시험의 분류 및 수정

| 초기 실패 | 판정 | QA 시험 조치 |
|---|---|---|
| 로그아웃 버튼이 두 곳에 있어 strict mode violation | 시험 선택자 오류 | 첫 버튼으로 한정 |
| `press('가')` unknown key | 시험 API 오용 | `keyboard.insertText('가')`로 수정 |
| 10 MiB 파일에 HTTP 413 기대, 실제 202 | 시험 계약 가정 오류 | 읽기 실패 파일 안내를 검증하도록 수정 |
| 권한 없는 전이에서 422 | 시험 필드 이름 오류 | to_status → to |
| Escape 시험의 승인 준비 실패 | 환경 차단 | 제품 결함 확정 보류 |
| 다른 탭 시험 로그인 timeout | 환경 차단 | 제품 결함 확정 보류 |
| 검토자 경합 120초 timeout | 환경 차단 | 경합 결과 검증 못함 |
| 1440 light/dark 로그인 timeout | 환경 차단 | 화면 검증 못함 |

최초 시험 이름에 DEFECT가 들어간 두 후보는 현재 `candidate`로 바꿨다. 최초 실행 원본 JSON/trace는 수정하지 않았으며, 그 이름은 확정 판정을 뜻하지 않는다. 제품 코드를 고치거나 실패 assertion을 skip 처리하지 않았다.

## 검증 및 잔여 작업

- [pytest.log](pytest.log): **247 passed / 3 failed / 3 errors**, 275.32초 후 환경 때문에 중단. 전체 통과 조건 미충족.
- [ruff.log](ruff.log): `ruff check jevtriage tests` 0건.
- 프런트 제품 소스 수정 없음. [typecheck.log](typecheck.log)·[build.log](build.log) 통과. 최초 기본 병렬 단위 실행은 366 passed / 3 failed였고, 실패 두 파일의 단일 워커 재실행은 31 passed였다. 이어 `npm run test -- --maxWorkers=1 --minWorkers=1` 전체 재실행은 **42개 파일 / 369 passed**([unit-serial.log](unit-serial.log)). 최초 실패는 5초 timeout 2건과 제목 조회 실패 1건이며, 단일 워커에서 제품 변경 없이 모두 통과했다.
- docs/architecture 변경 없음: QA-A의 결함 찾기·재현 전용 및 담당 파일 외 수정 금지 범위에 따라 이 보고서만 작성했다.
- 초기 실패 4개의 시험 수정은 아직 재실행으로 검증되지 않았다. boundaries 시험도 미실행이다.
- 브라우저 콘솔/HTTP telemetry는 `runs/20261005T181556/acceptance/telemetry.jsonl`; page fixture 대상 기록이다. 직접 만든 actor context 전체를 감시한 완전한 콘솔 로그는 아니므로 무오류로 주장하지 않는다.
- 5초 초과 대기: 첨부 시험 5.494초, 업무 19.977초, 승인 준비/Escape 31.702초, 다른 탭 18.253초, 경합 121.258초, 화면 로그인 16.894/21.160초. 이는 전체 시험 시간이며 단일 사용자 동작의 정밀 측정값과 구분한다.
- 11291·8691 listener 없음 확인. 전용 프로세스 종료, fixture 데이터는 해당 새 tenant에 보존.

재개 명령(환경 복구 후):

```sh
backend/.venv/bin/python artifacts/review/qa-full/qa-a/run.py 'chat-intake|modal-stack|review-repair|acceptance/scenarios|journeys|boundaries' --grep-invert 'S8|G10'
```

추가로 실제 선행 업무 해제, 원문 강조, 복사, 0px 전환, 전역 콘솔/실패 요청 계측 시험을 보완하고 전체 backend pytest를 재실행해야 한다. React Router 업그레이드·운영 IdP/MFA·외부 게이트 G10/G12/G13은 결함 목록에서 제외했다.

## 18:35 복구 후 재시도

코디네이터가 공유 DB 재시작 및 CPU 2%·즉시 조회 응답을 확인한 뒤 재개를 지시했다. 새 tenant `t-qa-a-1005183533`로 122개 시험을 수집했으며, backend pytest를 병행하지 않았다. 20,001자 입력은 HTTP 400·입력 보존·새 요청 미생성까지 통과했다.

잠금 시험은 10회차 응답을 429로 기대했지만 401을 받아 실패했다. 코드 계약은 10회 실패를 기록한 뒤 11회부터 429이므로 시험을 수정했고 제품 결함에서 제외한다. 이어 암호 PDF POST /api/requests가 7,673ms 후 503을 반환하여, 코디네이터의 재발 시 즉시 중지 지시에 따라 시험을 중단하고 전용 서비스를 종료했다. [새 실행 로그](runs/20261005T183533/results.log)·[telemetry](runs/20261005T183533/acceptance/telemetry.jsonl)에 시각/요청 지연이 있다. 원인 불명 상태이므로 제품 결함 확정 보류.

다음 실행용 `api_diagnostic.py`는 ingest 예외의 클래스 및 Neo4j code만 출력하고 원래 예외를 재전파한다. 타임아웃/응답/DB 로직은 변경하지 않는다. 아직 이 진단 실행기로 서버를 기동하지 않았다.

## 인계 상태

접수 503 재발 후 소유 서비스를 종료하고 코디네이터에게 직전 시험·요청 지연·진단 계획을 전달했다. 진단 1건 실행 여부 질문 `msg_d20765bf2f7a`는 40분 이상 응답되지 않아 여러 차례 동일 메시지로 대기를 재개했으며, 이후에도 재개 지시를 받지 못했다. 완료를 주장하지 않고 실패 결과로 인계한다. 환경 복구 여부를 확인하고 준비된 `api_diagnostic.py`로 먼저 접수 1건의 예외 코드를 확인한 뒤 전체 여정을 다시 실행해야 한다.

최신 재실행 권장 명령은 다음과 같다(제품 행동/타임아웃 변경 없음).

```sh
backend/.venv/bin/python artifacts/review/qa-full/qa-a/run.py 'chat-intake|modal-stack|review-repair|acceptance/scenarios|journeys|boundaries|layout.spec|rem-ui.spec|source-viewer.spec' --grep-invert 'S8|G10'
```

`repro/`의 후보 시험은 재현 확정 전까지 결함 목록이 아니다. 추가한 실제 선행 업무 해제·팀 필터·검토 목록 SSE·정확한 0px 전환 시험은 TypeScript 수집만 확인했고 아직 실행에 도달하지 못했다. 프런트 369개 단위 시험 통과는 이 미실행 브라우저 여정을 대체하지 않는다.

## 재개 실행 — QA-A2 (2026-10-05 19:47 이후)

이 절은 위 QA-A 기록을 보존한 추가 실행 결과다. 기준 HEAD는 `8403639`이며 5213ebf·7de15b4·f0f3e53·f243786 수정이 포함된 공유 worktree에서 실행했다. 제품 코드·docs/spec·docs/architecture는 수정하지 않았고, 실제 Jev 호출은 0건이다. 새 tenant, API 11291·Vite 8691, `JEV_MODE=mock`, tenant 제한 worker를 사용했다. QA 전용 자료 외 파일을 변경하지 않았다.

### 진단 선행 실행

- `runs/20261005T194718`: 암호 PDF 시험 실패, HTTP 500. `api_diagnostic.py`의 진입점 보호 누락으로 파서 spawn 자식이 uvicorn을 재실행하고 같은 포트 bind에 실패했다. `QA_INGEST_EXCEPTION EOFError`는 QA 실행기에서 유발한 오류이며 제품 결함으로 세지 않는다.
- 진단 실행기에 `if __name__ == '__main__'`만 추가한 후 동일 시험을 재실행했다. `runs/20261005T194815`: **1 passed (8.9초)**, 첨부 거절 안내 → 제외 → 분석 완료까지 정상. DB timeout 없음.
- `runs/20261005T194843`: Chromium 전체 61건 실행. 로그와 캡처는 해당 폴더에 보존. 아래 최종 집계는 후속 재현/보완 결과까지 반영한다.

### 확정 결함 (제품 수정하지 않음)

| ID / 심각도 | 재현·실제 결과 | 실패하는 시험 / 근거 | 수정 방향 |
|---|---|---|---|
| QA-A2-01 / 중간 | 승인된 업무를 담당자로 열고 Escape. 상세 dialog가 계속 남음. | `repro/journeys.spec.ts` “task detail Escape”; [캡처](runs/20261005T194843/acceptance/chromium-task-escape.png). 기대 dialog count 0, 실제 1. | 공용 dialog/overlay의 Escape·초점 복원 처리 적용 |
| QA-A2-02 / 중간 | 같은 업무를 두 탭에 열고 두 번째 탭에서 대기→진행. 첫 탭은 15초 후에도 “진행으로 변경”에 머물고 “완료로 변경” 없음. | `repro/journeys.spec.ts` “task update in second tab”; [캡처](runs/20261005T194843/acceptance/chromium-task-other-tab-before.png). 두 번째 탭 전이 성공 후 검증. | 업무 이벤트 구독 후 목록과 선택 상세를 함께 갱신 |
| QA-A2-03 / 중간 | 검토 목록을 열어둔 채 다른 역할에서 요청 접수·판단 완료. API에는 pending review가 있지만 열린 목록에는 15초 후에도 새 항목 없음. | `repro/journeys.spec.ts` “reviewer queue receives other role”; [캡처](runs/20261005T194843/acceptance/chromium-review-sse.png). | 검토 생성/변경 이벤트 구독 후 현재 필터 목록 갱신 |

각 결함의 실제 저장/전이/목록 API는 정상이고, UI 반영 assertion에서 실패했다. 최초 후보였던 IT팀 필터는 이번 실제 fixture에서 통과했으므로 결함에서 제외한다.

### Chromium 전체 범위 점검표 (이전 미점검 항목 보충)

| 범위 | 결과 및 근거 |
|---|---|
| 로그인·로그아웃·10회 실패 후 잠금 | 통과. 10회 401 후 정상 암호도 429. Enter 로그인/로그아웃 포함. |
| 빈 화면·예시 칩·Shift+Enter·Enter·IME 경계 | 통과. 합성 composition 키 이벤트로 전송 억제를 확인; OS 네이티브 한글 IME 자체의 검증은 아님. |
| 긴 입력·첨부 개수/제거·10MiB 초과 | 통과. 20,001자는 400·입력 보존, 6개는 5개 제한, 용량 초과는 읽기 실패 선택으로 진행. |
| 암호 PDF·위장 파일·PDF/DOCX/MD 정상·손상 파일 | 통과. `boundaries` 및 S5, `chat-intake` 재첨부/제외/새 revision. |
| 취소·다시 분석·보완 답변·새로고침 복원·새 요청 | 통과. `chat-intake` 4개 주요 실제 여정 및 S7 실행 비교/중복 업무 없음. |
| 대화 목록·375/520/960/1440·내부 스크롤·입력창 고정 | 통과. `chat-intake` 반응형/레이아웃 및 새 메시지 pill 이동. |
| 근거 원문·강조·중첩 Escape·포커스 복원 | 통과. `modal-stack`, `source-viewer` 7건. PDF/DOCX/MD/chat 특정 anchor 시험은 실제 저장 문서에 인용 목록만 응답 모킹으로 고정한 UI 검증이다. 나머지 실제 모델 인용 열기도 통과. |
| 원문 권한·마스킹·식별자 표시 | 통과. `rem-ui` 3건, `source-viewer` 권한 없음 위치 전용 처리. |
| 승인·수정 승인·반려·정보 요청·사유 필수·원안 보존 | 통과. S2/S4/S6 및 `review-repair`, 실제 API·저장 결과 대조. |
| 두 검토자 경합 | 통과. 동시 반려가 200/409, 패자에게 최신 검토 안내. |
| 긴급 우선 정렬·검토 제목 | 통과. S3 및 rem-ui. 상태별 필터의 처리 완료 항목 선택/결정 비활성은 추가 `filters.spec.ts`에서 별도 검증. |
| 업무 대기→진행→완료·새로고침·권한 거부·팀 필터 | 통과. lifecycle + IT팀 포함성. 역할/방식 필터 포함성 assertion을 보강하여 후속 재실행. |
| 선행 업무 차단/해제 | 첫 시험은 개발 가능성 미확인 차단까지 혼합하여 실패. 실행 가능 mock fixture로 수정 후 별도 재실행 결과를 아래 기록. |
| 1440·375 / light·dark / Tab | 3역할×2폭×2테마 12건 통과, 전체 페이지 캡처 보존. 실제 375 검토 화면과 1440 요청 화면 다크 캡처를 시각 확인. 전체 OS/스크린리더 감사는 아님. |
| 업무 Escape / 타 탭 업무 / 타 역할 검토 목록 | QA-A2-01/02/03 재현 실패. |
| 잠정→최종 정확히 0px / 복사 | 위치·판단 높이 차이 0, [측정 JSON](runs/20261005T194843/acceptance/chromium-zero-layout.json). 복사는 headless 클립보드 권한 부재로 실패하여 권한 부여 후 재실행. |

첫 전체 실행은 **56 passed / 5 failed / 0 skipped**, 360.6초다. 실패 5건 중 UI 결함 3건과 QA 조건 오류 2건을 분리했다. 조건 오류를 제품 수정으로 숨기거나 실패 assertion을 skip 처리하지 않았다.

### WebKit 및 보완 재실행

- [WebKit 실행](runs/20261005T195514/results.log): **9 passed / 3 failed / 0 skipped**, 162.1초. 핵심 6여정(로그인·로그아웃, 암호 PDF 제외, 취소·재분석, 결과·복원·새 요청, 보완 답변, 업무 생명주기)은 모두 통과했다. 추가 필터·선행 차단/해제·0px/복사도 통과했고, 실패 3건은 QA-A2-01/02/03과 동일하다.
- [양 브라우저 보완 실행](runs/20261005T195820/results.log): **8 passed / 0 failed**, 108.1초. Chromium/WebKit 각각 검토 상태 필터, 업무 역할·방식·상태 필터/전이, 실제 선행 차단→완료 후 해제, 정확히 0px 전환+복사 4건이다. 선행 fixture는 실행 가능성 불확실 조건을 제거하고 실제 선행 관계만 시험하도록 `E2E_AUTO_ASSIGN` 표시를 사용했다. API/worker/실제 저장 업무는 모킹하지 않았다.
- Chromium의 clipboard 권한을 부여해 복사를 검증했고 WebKit은 기존 사용자 클릭 경로에서 성공했다. 최종 위치 측정은 [Chromium](runs/20261005T195820/acceptance/chromium-zero-layout.json)·[WebKit](runs/20261005T195820/acceptance/webkit-zero-layout.json) 모두 차이 0이다.
- 초기 WebKit 업무 시험에서 전이 직후 새로고침으로 취소된 요청 1건과 access-control pageerror 2건이 기록됐다. 완료 전이 HTTP 200 및 상세 갱신 완료를 기다린 후 새로고침하도록 시험을 보강했고, 보완 실행에서는 **pageerror 0건**이다. 제품 CORS 결함으로 확정하지 않는다.
- 모든 Chromium 대상은 실행됐으며 최초 2개 QA 조건 오류도 후속 통과했다. 고유 Chromium 대상은 추가 상태 필터 포함 **62건: 59건 통과, 확정 결함 재현 3건**이다. 실패 시험 이름의 `candidate`는 이전 QA-A 이름을 보존한 것이고 이 절의 판정이 최종이다.

### 콘솔·관찰 범위와 제외

`repro/telemetry.ts`는 QA actor가 만든 모든 탭의 pageerror, console error, 실패 요청, HTTP 4xx/5xx 및 5초 이상 비-SSE 요청을 기록한다. 초기 전체 Chromium 계측은 HTTP 28건(401 15, 429 1, 400 1, 404 10, 409 1), 콘솔 28건, 취소 요청 1건, pageerror 0건이다. 로그인 실패·입력 경계·경합 의도 오류와 판단/진행 생성 전 404가 주된 내용이며, 5xx·5초 이상 비-SSE 요청은 관찰되지 않았다. 기존 `frontend/e2e` 시험 내부에서 직접 생성한 context 전체에는 이 추가 계측이 붙지 않으므로 모든 시험의 콘솔이 무오류라고 주장하지 않는다. 기존 시험 실패 trace와 자체 assertion도 함께 확인했다.

이전 보고서의 미점검 기능은 위 표와 보완 실행으로 채웠다. 단 실제 Jev 품질·성능, 운영 로그인/IdP/MFA, OS 네이티브 IME, React Router 및 외부 게이트 G10/G12/G13은 범위 밖이거나 이 자동화가 증명하지 않는 조건이다. 실제 Jev는 최대 3건 허용 범위 중 **0건** 사용했다. 별도의 제품 수정·통과 회귀 단계는 이 작업의 “결함 찾기·재현 전용” 규칙 때문에 하지 않았고, 결함 3건은 수정 담당자에게 인계한다. docs/architecture는 담당 파일 외 변경 금지에 따라 수정하지 않았다.

### 최종 검증·정리

- [backend 전체 pytest](resume-pytest.log): **531 passed / 1 skipped**, 81.38초, 종료 코드 0. live Jev 시험은 live 모드/자격증명 조건부 skip이며 이번 작업은 mock 범위다.
- [ruff](resume-ruff.log): `ruff check jevtriage tests` **All checks passed**.
- 프런트 제품 코드 변경 없음. 이번 재개에서는 타입체크·단위 시험·빌드를 반복하지 않았으며 위 QA-A의 기존 성공 결과와 이번 실제 Chromium/WebKit E2E 결과를 구분한다. 변경한 QA TypeScript 파일은 실제 Playwright 실행으로 수집·실행했다.
- API·Vite·두 tenant 제한 worker 프로세스 모두 종료됐고 **11291/8691 listener 없음**. [정리 증거](resume-cleanup.json). 공유 Neo4j·다른 작업자 서비스는 중단하지 않았다.
- [실행별 집계](resume-results-summary.json). 제품 tracked 파일 diff 없음, git commit/push 없음. 새 tenant fixture는 재현 증거로 보존했다.
- **QA-A2 결과: 점검 완료, 확정 결함 3건 인계.** 검증한 모든 범위의 결과를 기록했으며, 제품이 무결함이거나 결함 수정이 완료됐다는 뜻은 아니다.
