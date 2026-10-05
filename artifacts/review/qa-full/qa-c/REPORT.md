# QA-C 신뢰성·데이터 무결성·API 경계 점검

2026-10-05 실행 결과. **확정 결함 6건(P0 1건·P1 5건)**을 재현 시험과 함께 남겼다. 제품 코드와 사양·디자인 문서는 수정하지 않았고 commit/push도 하지 않았다. QA-C 검증 시점의 전체 백엔드 회귀는 **483 passed, 1 skipped**, ruff는 0건이었다. 종료 시점에 다른 작업자의 변경이 추가되어 최신 전체 ruff에는 해당 변경의 I001 1건이 남았다(아래 시점 구분). 이 회귀 통과와 아래 추가 결함 재현의 실패는 서로 다른 시험 집합이다.

## 환경과 증거 범위

- 점검 작업트리 HEAD: `5213ebf6eefb127cd2b49d4ad912a399ebb143e8`. 공유 작업트리이므로 다른 작업자의 변경은 이 작업의 수정 목록에 포함하지 않는다.
- OrbStack, Neo4j Community 5.26.0, 전용 Bolt 7688. API 11491/11492, 추가 QA Redis 11493/DB 15. 전용 tenant `qa_c_*` 및 기존 장애 시험의 무작위 `t22_*`를 사용했다.
- 추가 QA worker는 `--tenant`로 제한했고 `scripts/e2e/mock_worker.py`의 결정적 모델 fixture를 재사용했다. 실제 Jev 호출 **0건**, `JEV_MODE=mock`이다.
- 근거: [`FAULT_TESTS.md`](../../../../docs/architecture/FAULT_TESTS.md), [`LOADTEST.md`](../../../../docs/architecture/LOADTEST.md), [`architecture-review.md`](../../architecture-review.md), [`requirements-gap.md`](../../requirements-gap.md), [`브라우저 보고서`](../../browser-exploration/REPORT.md).
- 모든 개인정보·키 표본은 합성 값이다. HTTP 오류 캡처와 mock 모델 페이로드는 JSON으로 보존했다. 이 작업에서는 브라우저를 조작하지 않았다.
- 공유 Neo4j 7687을 중지하거나 대량 시드/부하에 사용하지 않았다. 공유 Redis를 중지하지 않았으며 기존 전체 회귀의 Redis fixture는 자체 기존 설정인 6379/DB 15를 사용했다. 8191·5391 프로세스는 건드리지 않았다.
- 메모리를 제한한 전용 DB에서 `NEO4J_WRITE_TIMEOUT_SECONDS=30`을 사용했다. 기본 5초 설정의 콜드 스타트 실패를 별도로 보존했으며, 이를 기본 설정의 성능 통과로 해석하지 않는다.

## 점검 체크리스트

| 항목 | 방법 | 결과 | 근거 |
| --- | --- | --- | --- |
| 기존 장애 시험 전체 | 상류 `scripts/fault/run.sh` 2회, 전용 환경에서 11개 시나리오 전체 1회 | 8 통과/3 실패; 아래 재확인·시험 가정 문제 구분 | [전체 로그](evidence/fault-final.log), [JUnit](evidence/fault/junit.xml) |
| Jev timeout·429·529·schema | 장애 mock, 실패 Run·Assignment 0 확인 | 정상: 429/529/schema 통과, timeout 웜 재시험 통과 | [시나리오](evidence/fault/scenarios.jsonl), [재시험](evidence/fault-focused/scenarios.jsonl) |
| 손상 파일·DB 중단/복구 | 손상 PDF, 전용 컨테이너 pause/unpause, 503·회복·journal 확인 | 정상 | [시나리오](evidence/fault/scenarios.jsonl) |
| worker 재시작·lease 인수 | SIGSTOP/SIGCONT, SIGKILL 후 재시작; generation·정식 Judgment 개수 확인 | 정상: 웜 재시험 generation 1→2, Judgment 1건 | [재시험](evidence/fault-focused.log), [시나리오](evidence/fault-focused/scenarios.jsonl) |
| API 재시작·SSE Last-Event-ID | 재시작 뒤 cursor 재개, snapshot·상태 대조 | 정상: 재개 2,982ms, 표본 1건 | [시나리오](evidence/fault/scenarios.jsonl) |
| 정책 도중 게시·rollback | 각 Run의 고정 버전 대조 | 정상: 1→2→3 | [시나리오](evidence/fault/scenarios.jsonl) |
| 관측 중단·journal 장애·120초 이후 회복 | collector/watchdog 및 독립 journal 대조 | 정상 | [시나리오](evidence/fault/scenarios.jsonl) |
| 같은 요청 동시 수정 승인 2건 | 서로 다른 검토자 두 클라이언트, 같은 버전 병렬 수정 승인, 승자 키 재전송 | 정상: 200/409, 배정 1·업무 2·중복 0, 재전송 200 | [캡처](evidence/changed-approval-race.json) |
| 취소와 완료 경합 | Worker 종료 bookkeeping과 취소 20회 병렬 실행; 기존 running-cancel 회귀 포함 | 정상: 20회 Run/Job 상태 단일 수렴; 표본은 모두 완료 승리, 취소 승리 경로는 기존 회귀로 확인 | [캡처](evidence/cancel-race.json), [전체 회귀](evidence/backend-full-pytest.log) |
| worker 2개 동시 claim | 같은 Job 두 owner의 claim 동시 실행 | 정상: generation 1 승자 1개·OwnershipLost 1개 | [캡처](evidence/parallel-claim.json) |
| Redis 중단/복구·API 두 인스턴스 전달 | API A에서 접수, API B에서 SSE; 전용 Redis 종료·재시작, Last-Event-ID 재개 | 정상: 기대 seq 439/440/441 모두 수신, 중복 0·관찰 유실 0 | [캡처](evidence/two-api-redis-recovery.json) |
| 공개 API JSON/누락/과대 입력/ID/CSRF/만료 | OpenAPI 63개 경로 inventory, 62개 경로·64개 operation·189개 경계 호출; 추가 특수 입력 재현 | 기본 행렬 정상(5xx 0), 추가 입력에서 결함 4종 | [행렬](evidence/api-matrix.json), 아래 QA-C-01/03/05/06 |
| 다른 tenant 요청 ID | 실제 타 tenant Request 생성 후 상세·실행·판단·진행·수정 이력 조회 | 정상: 5개 404 | [캡처](evidence/cross-tenant.json) |
| 검토 목록의 권한·LIMIT 경계 | 최신 타 조직 검토 100건 뒤에 허용 검토 1건 | **결함 QA-C-04** | [캡처](evidence/review-starvation.json) |
| 20건 동시 접수·검토 1천 건 | 실제 API·DB·worker, 목록/상세/SSE 각 30회 측정 | 정상: 접수 20건 판단 완료, 조회 오류율 0% | [원시 측정](evidence/small-load.json) |
| retention dry-run·실행 | 업무 기록을 1,000일 전 생성 시각으로 만들고 dry-run/삭제 전후 개수 대조 | 정상: 업무 기록 불변, 만료 Event 442건 삭제 | [캡처](evidence/retention.json) |
| 백업→복원 | 모든 writer 종료, Community offline dump/load, 노드·관계 속성 해시 및 앱 파일 SHA 대조 | 정상: 노드 815·관계 532 및 해시 일치, 파일 13개 일치 | [캡처](evidence/backup-restore.json), [로그](evidence/backup-restore.log) |
| 일반 판단 외부 전송 마스킹 | 채팅/근거 단위/근거 검증/운영 가이드에 합성 5종 표본, 실제 mock client 경계 캡처 | 정상: 14회 호출, 표본 원문 0 | [캡처](evidence/regular-masking.json) |
| shadow 재검증 외부 전송 마스킹 | 같은 5종 표본을 입력과 context rule에 넣고 mock 경계 캡처 | **결함 QA-C-02**: 22회 모두 원문 포함 | [캡처](evidence/shadow-masking.json) |

## 확정 결함과 실패하는 재현 시험

### QA-C-01 / P1 — 검증 오류 응답에 제출 원문 포함

- **재현**: 로그인 `password` 객체, 정책 `config` 배열, 재분석 `expected_revision` 배열, 검토 `action`의 잘못된 문자열, 업무 전이 `to` 배열에 합성 이메일을 넣는다. [시험](repro/test_api_error_redaction.py) **5개 실패**.
- **기대**: 오류 위치·종류만 반환하고 제출 원문/비밀값은 오류 응답에서 제거.
- **실제**: HTTP 422의 `detail[*].input`에 합성 이메일이 그대로 들어가며 누락 필드 오류에서는 제출 객체가 반복된다. 로그인은 인증 전 재현된다.
- **캡처/실패 확인**: [응답](evidence/validation-redaction.jsonl), [로그](evidence/redaction-pytest.log).
- **심각도 근거**: 제출자에게 입력을 반사하는 오류 정보 노출이다. 다른 사용자의 비밀을 읽은 증거는 없으므로 P1로 분류했다.
- **수정 방향**: 공통 RequestValidationError 응답에서 input 및 원문을 포함할 수 있는 context를 제거.

### QA-C-02 / P0 — shadow 모델 호출이 마스킹을 우회

- **재현**: `masking.enabled=true`인 tenant에서 context 규칙의 shadow 재검증을 실행한다. 입력과 운영 가이드에 이메일·전화·주민번호·Luhn-valid 카드·키 패턴의 합성 표본을 넣고 `JevClient.ask`에 전달되는 state/questions를 CaptureClient로 저장한다. [시험](repro/test_shadow_masking.py) **실패**.
- **기대**: 일반 판단과 같이 외부 모델 경계에 표본 원문 0건.
- **실제**: 완료된 shadow 재검증의 **22개 페이로드 각각에 5종 표본 모두** 남는다. 일반 판단의 같은 캡처는 14회 모두 원문 0건이다.
- **원인**: `learning.shadow._LimitedClient.ask`가 raw state와 `operating_guidance`를 inner client에 직접 보내고, 마스킹은 `judgment.service.execute_judgment` 안의 래퍼에만 있다.
- **캡처/실패 확인**: [22개 페이로드](evidence/shadow-masking.json), [실패 로그](evidence/qa-runtime-final.log), [일반 판단 대조](evidence/regular-masking.json).
- **심각도 근거**: 개인정보/비밀을 외부로 전송하는 보안 경계 누락이므로 P0. 실제 외부 Jev에는 호출하지 않았으며, live 전송 위험은 동일 코드 경로에 근거한 판단이다.
- **수정 방향**: 일반 판단과 shadow가 공유하는 외부 호출 경계에서 모든 사용자 유래 문자열을 일관되게 마스킹.

### QA-C-03 / P1 — 큰 정수 입력이 Neo4j 직렬화 오류로 500

- **재현**: 로그인 뒤 `/api/policy/versions/1208925819614629174706176`, `/api/graph/judgment?config_version=1208925819614629174706176` 호출. [시험](repro/test_api_robustness.py)의 `test_oversized_integer_never_causes_500` 중 **2개 실패**.
- **기대**: 허용 정수 범위를 검증하여 4xx 또는 없는 버전 404.
- **실제**: 모두 500 `Internal Server Error`; 서버 로그에는 `OverflowError: Integer ... out of range`.
- **대조**: 없는 rule의 큰 version으로 validations 목록을 읽는 경로는 200/빈 목록이었다. 모든 정수 경로가 실패한다고 확대하지 않는다.
- **캡처/실패 확인**: [응답](evidence/oversized-integer.jsonl), [로그](evidence/qa-runtime-final.log).
- **수정 방향**: 경로·쿼리 모델에 DB 정수 범위 상한을 지정하고 저장소 호출 전 검증.

### QA-C-04 / P1 — 타 조직 검토가 허용 검토를 목록에서 가림

- **재현**: 같은 tenant에 오래된 허용 검토 1건과 더 최근 타 조직 검토 100건을 시드한 뒤 목록과 허용 검토 상세를 비교한다. [시험](repro/test_review_queue_starvation.py) **실패**.
- **기대**: 권한이 있는 대기 검토가 목록에 표시.
- **실제**: 상세는 200인데 목록은 빈 배열이다. `review.store.list_reviews`의 LIMIT 100 뒤에 Python 권한 필터를 적용하기 때문이다. 기존 아키텍처 R9의 정합성 우려를 실행으로 확정했다.
- **캡처/실패 확인**: [응답](evidence/review-starvation.json), [로그](evidence/qa-runtime-final.log).
- **수정 방향**: 권한 조건을 DB 조회에 넣은 뒤 LIMIT/페이지 처리를 적용.

### QA-C-05 / P1 — 숫자 검증 오류의 JSON 직렬화가 500

- **재현**: 인증 없이 로그인에 `{"email":1e1000,"password":"qa-only"}` 전송. NaN·Infinity·-Infinity도 동일하다. [시험](repro/test_api_numeric_errors.py) **4개 실패**.
- **기대**: 잘못된 email 타입 또는 JSON 숫자 입력을 4xx로 처리.
- **실제**: 모두 500. email 타입 검증 오류의 input에 비유한 float가 남아 오류 응답 JSON 직렬화가 실패한다. `1e1000`은 JSON 문법상 허용되는 숫자이며, NaN/Infinity 같은 비표준 토큰도 별도로 시험했다.
- **캡처/실패 확인**: [응답](evidence/numeric-validation.jsonl), [로그](evidence/numeric-pytest.log).
- **수정 방향**: 비유한 수를 입력 경계에서 거절하고 검증 오류를 안전한 JSON DTO로 직렬화. QA-C-01의 input 제거와 함께 해결 가능.

### QA-C-06 / P1 — 중첩 검토 변경의 타입 검증 누락으로 500

- **재현**: 유효한 pending 검토의 수정 승인 명령에 `changes.classifications=["qa-invalid"]` 또는 `changes.draft_tasks=["qa-invalid"]`를 넣는다. [시험](repro/test_api_robustness.py)의 `test_nested_review_changes_are_validated_before_service` **실패**.
- **기대**: 잘못된 중첩 구조를 422로 반환하고 기존 검토를 보존.
- **실제**: 두 경우 500. 서비스가 각각 `.items()` 및 `.get()`을 가정한다. 잘못된 lead_org 배열과 잘못된 분류 문자열은 대조군으로 422를 반환했다.
- **캡처/실패 확인**: [응답](evidence/nested-review-changes.json), [최종 실패 로그](evidence/nested-final.log).
- **수정 방향**: `dict[str, Any]` 변경값을 분류·업무 수정용 중첩 모델로 검증.

## 부하 측정

실제 API·전용 DB·결정적 mock worker를 사용했다. 텍스트 요청 20건을 동시에 접수했고, 같은 tenant의 pending 검토 1,000건을 시드했다. 결과의 백분위는 정렬 표본의 하위 index 방식이며 원시 값도 보존했다.

| 동작 | 표본 수 | p50(ms) | p95(ms) | 오류 |
| --- | ---: | ---: | ---: | ---: |
| 동시 접수 및 active run 조회 | 20 | 483.33 | 565.80 | 0 |
| 검토 목록 | 30 | 47.91 | 93.67 | 0 |
| 검토 상세 | 30 | 14.14 | 19.45 | 0 |
| SSE 과거 이벤트 첫 id 수신 | 30 | 58.79 | 67.21 | 0 |

20개 Run은 모두 judgment_saved였다. 목록/상세/SSE 90개 호출의 오류율은 0%다. 접수 측정은 harness의 active-run 조회 시간을 포함하고, 상세 시드에는 실제 판단/초안 전체가 없다. SSE 측정은 연결 뒤 **이미 영속화된 첫 이벤트 수신**이며 신규 이벤트 전달 지연의 p95나 30분 T25/운영 SLO 측정이 아니다. 신규 전달은 별도 3개 표본에서 Redis 정상 116.89ms, 중단 129.86ms, 복구 11.98ms였다.

## 장애 시험 실패의 재확인

1. 상류 러너 첫 실행: 기본 write timeout 5초의 bootstrap 지연으로 11개 setup 오류. [로그](evidence/fault-run.log)와 `artifacts/validation/t22/20261005T091430Z/` 보존.
2. 두 번째 실행: 콜드 스타트 연결 실패로 11개 setup 오류. [로그](evidence/fault-retry.log)와 `artifacts/validation/t22/20261005T091942Z/` 보존.
3. 메모리 제한/30초 write timeout 환경의 전체 실행: **8 passed, 3 failed**. 실패는 timeout 최초 처리 지연, worker 인계의 추가 attempt(3 vs 기대 2), 병렬 승인 뒤 재전송 409.
4. 같은 전용 DB를 예열한 뒤 timeout·worker 인계/재시작을 재실행하여 **2 passed, 9 deselected**. SIGSTOP 인수는 generation 1→2, 정식 Judgment 1건, SIGKILL 재시작도 완료. [로그](evidence/fault-focused.log).
5. 병렬 승인 시험은 20개 요청 중 실제 승자를 찾지 않고 항상 index 0의 키를 재전송한다. index 0이 패자이면 409가 올바른 응답이므로 이 실패를 제품 멱등성 결함으로 분류하지 않았다. 별도 두 검토자 수정 승인 시험에서 **실제 승자의 키**를 재전송하여 200 및 배정 중복 0을 확인했다.

따라서 “기존 장애 시험 11개가 한 번에 모두 통과했다”고 보고하지 않는다. 콜드 지연/짧은 lease 환경 민감성과 위 시험 가정의 개선이 남는다.

## 보존·백업 결과

retention 대상 업무 기록은 Request 44, InputRevision 44, Run 44, Judgment 23, Review 23, Assignment 1, Task 2, Audit 1이었다. 생성 시각을 1,000일 전으로 바꿔도 dry-run/실행 후 모두 그대로였으며 만료 Event 442건만 삭제됐다. [전후 대조](evidence/retention.json).

writer 종료 뒤 Neo4j Community의 offline dump/load를 별도 빈 경로로 수행했다. 노드 **815→815**, 관계 **532→532**였으며 노드·관계의 정렬된 속성 SHA-256도 각각 일치했다. 전용 앱 data의 파일 13개(첨부·journal·heartbeat)도 모두 SHA-256 일치였다. system DB의 사용자/권한은 dump 범위에 들어가지 않으며 복원 전용 컨테이너는 개발 인증으로 기동했다. 이 시험은 [`scripts/ops/backup.sh`](../../../../scripts/ops/backup.sh)의 7689/Compose 대상 검사를 시험한 것이 아니라 같은 Community offline dump/load 방법의 데이터 보존을 검증한 것이다.

## 재현·검증 명령과 산출물

DB 없는 확정 재현:

```sh
cd backend
PYTHONPATH=. JEV_MODE=mock .venv/bin/pytest -q \
  ../artifacts/review/qa-full/qa-c/repro/test_api_error_redaction.py \
  ../artifacts/review/qa-full/qa-c/repro/test_api_numeric_errors.py --tb=short
```

전용 DB를 7688에 준비한 뒤 [`run_dedicated.py`](repro/run_dedicated.py)를 실행하면 상류 장애·전체 회귀·QA 재현을 수행한다. API 11491/11492와 Redis 11493이 비어 있어야 한다. [`check_backup.py`](repro/check_backup.py)는 이 작업의 이름인 `jevtriage-qa-c-neo4j`만 대상으로 백업·복원하고 전용 컨테이너와 지정 data 경로를 정리한다.

- 전체 백엔드: [483 passed, 1 skipped](evidence/backend-full-pytest.log). skip은 live Jev 품질 시험.
- backend ruff: 검증 시점 [0건](evidence/backend-ruff.log). QA 재현 코드 최종 [0건](evidence/repro-ruff.log). 09:54 UTC 최종 전체 검사에서는 다른 작업자가 수정 중인 `backend/tests/unit/test_evaluation_labels.py:1`의 I001 1건이 새로 나왔다([최신 로그](evidence/backend-ruff-final.log)); 코디네이터에게 통지했으며 소유권 밖 파일은 고치지 않았다.
- 위 483개 통과 후 공유 트리에 evaluation/observatory 등의 동시 수정이 들어왔다. 이 결과를 그 동시 수정까지 포함한 최종 통합 회귀로 주장하지 않는다. 전용 자원 정리 후의 통합 재검증은 코디네이터가 해야 한다.
- 추가 runtime QA: [10 passed, 5 failed](evidence/qa-runtime-final.log). 여기의 nested 변경 시험은 첫 500 뒤 연결 재사용 오류로 끝나 별도 `Connection: close` 재시험의 [실제 500/500/422/422 캡처](evidence/nested-review-changes.json)를 최종 근거로 사용한다.
- 첫 QA 묶음의 HTTP 401들은 fixture에 Tenant→HAS_ORG 관계가 빠져 생긴 준비 오류다. 이를 harness에서 고친 뒤 재시험했으며 제품 결함으로 세지 않았다. 처음의 [22 failed, 2 passed 로그](evidence/qa-pytest.log)는 오류 원인을 추적할 수 있도록 보존했다.
- 결함 수정은 이 작업 범위 밖이므로 제품 수정 후 통과 시험은 없다. 코디네이터가 위 실패 재현을 수정 담당자에게 전달하면 된다.

## 못 본 항목과 제한

- 공개 API 189개 행렬은 각 경로에서 적용 가능한 대표 입력을 시험했다. 모든 필드·중첩 조합·첨부 크기·모든 역할을 조합한 전수 fuzzing은 아니다. 로그아웃은 공용 시험 세션 폐기를 피하기 위해 행렬에서 제외했고 기존 전체 회귀의 로그인/로그아웃/CSRF/실제 만료 시험으로 확인했다.
- 새 foreign tenant의 실제 ID 검증은 요청 하위 5개 조회에 집중했다. 나머지 경로의 실제 foreign resource ID를 각각 새로 시드한 전수 교차 tenant 시험은 하지 않았다. 기존 전체 tenant/authz 회귀 통과를 보조 증거로만 사용한다.
- 취소 20경합의 관찰 표본은 모두 완료 승리였고, handler는 모델 결과 저장 대신 Worker 종료 bookkeeping을 경합시켰다. 실제 판단 중 취소의 쓰기 차단은 기존 `test_running_cancel_fences_late_result` 회귀로 확인했다.
- 소규모 텍스트/mock 부하는 T25의 첨부 비율·30분 live·25,000회 호출 게이트를 재현하지 않았다. 실 Jev 품질이나 운영 SLO 통과로 해석하지 않는다.
- 원격 백업·암호화·호스트 유실·system 사용자 복구·운영 백업 CLI의 전용 Compose 안전 검사는 범위 밖이다.
- React Router 업그레이드, 운영 IdP/MFA, 외부 게이트 G10/G12/G13은 지시대로 결함으로 보고하지 않았다.
- QA 전용 산출물 소유권을 지켜 `docs/architecture/*.md`를 변경하지 않았다. 기존 문서의 시험 결과를 대신 덮어쓰지 않고 이 보고서에서 이번 결과와 제한을 연결했다.

## 종료 정리

전용 API·worker·Redis·collector·watchdog과 전용 Neo4j/복원 컨테이너를 종료·제거했다. `.data/neo4j-fault`, `.data/qa-c-backup`, `.data/qa-c-restore`, `.data/qa-c-restore-app`을 삭제했고 `.data`의 git 제외를 확인했다. 영구 증거는 본 디렉터리에 남겼다. [정리 확인](evidence/cleanup.json).
