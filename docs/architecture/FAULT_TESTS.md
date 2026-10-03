# T22 장애·정합성·복구 시험

## 실행

저장소 루트에서 `make test-fault`를 실행한다. 스크립트는 `neo4j:5.26.0-community` 전용 컨테이너 `jevtriage-fault-neo4j`를 호스트 7688 포트에 띄우고, 전용 tenant·DATA_DIR·API 포트를 사용한다. API, 두 worker, collector, watchdog은 실제 subprocess다. Neo4j pause/unpause는 전용 컨테이너에만 적용하며 스크립트의 EXIT trap이 컨테이너를 제거한다. 결과는 `artifacts/validation/t22/<UTC timestamp>/`에 `pytest.log`, `scenarios.jsonl`, 프로세스 로그, journal, SQLite metrics, alerts로 남는다. 비밀 키는 로그·보고에 포함하지 않는다.

`backend/tests/fault/scenarios.py`는 파일 이름이 `test_*.py`가 아니므로 기본 `make test` 수집에서 분리된다. `make test-fault`가 파일을 명시해 실행한다. `JEV_MODE=mock`의 `JEV_MOCK_FAULT={timeout,429,529,schema}`와 `JEV_MOCK_DELAY_SECONDS`는 장애 주입용이며 기본값은 비활성이다. 실제 Jev 요청은 하지 않으며 결과는 mock으로 기록된다.

## 판정 기준

`scenarios.jsonl`의 각 행은 통과한 경로의 request/run ID와 상태를 남긴다. 실패한 pytest 사례는 `pytest.log`에 남으며, 전체 완료 판정에는 실패·미검증 사례를 따로 명시한다. SSE 복구 시간은 API 재기동 시작부터 `Last-Event-ID` 재연결 이벤트 수신까지이며, 최종 상태는 판단 완료 후 snapshot·요청 조회로 별도 대조한다. 표본 수를 함께 남기며 5초 p95 목표는 표본 1건만으로 운영 성능 통과를 선언할 수 없다.

Jev 장애는 실패 Run과 Assignment 0건, 파서 손상은 파일 결정 대기, DB 중단은 503과 독립 journal 미확정 표본, worker 인계는 이전 generation의 정식 쓰기 거절, API/SSE 재시작은 영속 상태·이벤트 seq 대조, 정책 변경은 각 Run의 고정 버전, 동시 승인은 Assignment 1건과 Task ID 중복 0건, 관측 장애는 독립 alert와 collector 중복 제거, 120초 이후 회복은 최초 실패 표본과 late recovery를 확인한다.

Neo4j가 인증 전에 중단되면 tenant를 DB 없이 검증할 수 없다. 이때 접수 표본은 tenant 미확정으로 기록하며, tenant별 집계에 임의 귀속하지 않는다. 로컬 watchdog 파일은 호스트 전체 유실 시 살아남지 않으므로 원격 관측·알림 검증은 T26 범위다. 전용 mock 모델의 안전성 시험은 실 Jev 품질 게이트를 대체하지 않는다.
커밋 대조의 `run_commits_missing_journal`은 종료 상태(`judgment_saved`·`failed`·`cancelled`) Run만 비교한다. 아직 처리하지 않은 Run은 완료 journal이 없는 것이 정상이다.

## 실행 결과 (2026-10-03 UTC)

전용 Neo4j 7688 컨테이너에서 `make test-fault`를 실행해 **11 passed, 0 failed**였다. 시나리오별 request/run ID, 측정값, 프로세스 로그는 [`20261003T093629Z/report.md`](../../artifacts/validation/t22/20261003T093629Z/report.md)에 있다.

| 시나리오 | 판정 | 핵심 결과 |
| --- | --- | --- |
| Jev timeout·429·529·스키마 오류 | 통과 | mock 4종 모두 실패 Run, 배정 0건 |
| 파서 손상·Neo4j pause/unpause | 통과 | 파일 결정 대기, HTTP 503·미확정 journal 1건, 재개 후 접수 성공 |
| worker SIGSTOP 인계·SIGKILL 복구 | 통과 | generation 1→2, 정식 Judgment 1건, 죽은 worker 재시작 완료 |
| API 재시작·SSE 차단/복구 | 통과 | cursor 1→2, 재연결 1004ms, snapshot·영속 상태 일치 |
| 정책 도중 게시·rollback | 통과 | Run 고정 버전 1→2→3 |
| 두 검토자 병렬 승인 20건·멱등 재전송·과거 승인 | 통과 | 200 응답 1건·409 19건, 배정 1·업무 1·재전송 200·과거 승인 409 |
| collector 정지·journal 권한 장애 | 통과 | watchdog 알림 2종, 집계 중복 ID 0건 |
| 정보 부족 판단·보완 대기·120초 후 회복 | 통과 | 필수 판단 11개 저장, 정보 요청 후 보완 대기, 최초 실패 1건·late recovery 1건 유지 |

관측 대조에서 미처리 Run을 journal 누락으로 표시하던 오진을 수정하고 전용 컨테이너로 재시험했다. [`20261003T094002Z/report.md`](../../artifacts/validation/t22/20261003T094002Z/report.md)에 **1 passed**와 누락·불일치 배열 모두 빈 값을 기록했다. `make up` 후 전체 백엔드 `pytest -q --tb=short`는 **128 passed, 1 skipped**였다. 종료 후 전용 컨테이너와 API·worker·collector·watchdog 대상 `docker ps`/`ps` 조회 결과 잔여 프로세스는 없었다.
