# 독립 관측 수집과 모니터링

T18 구현 메모, 2026-10-03.

## 실행과 저장

`make up` 이후 API·worker와 별도 터미널에서 `make collector`, `make watchdog`을 실행한다. `DATA_DIR` 기본값은 프로세스 작업 디렉터리 기준 `.data`다. Makefile 명령은 `backend/`에서 실행하므로 journal, metrics, alerts는 기본적으로 `backend/.data/` 아래에 놓인다. 운영 환경에서는 세 프로세스가 같은 영속 `DATA_DIR`을 보도록 설정해야 한다.

수집기는 `journal/archive-*.jsonl`과 `journal/current.jsonl`의 완성된 줄만 읽고 `metrics/metrics.db`의 `events`에 `event_id`를 고유 키로 넣는다. 파일 inode별 바이트 오프셋을 같은 SQLite 트랜잭션에서 갱신한다. 손상된 줄·잘린 파일은 `collection_issues`에 기록한다. 수집기 heartbeat는 `metrics/collector-heartbeat.json`이다. 10초 간격 체크포인트와 30초 초과 수집 공백은 `collector_ticks`·`collection_gaps`에 저장한다. DB와 독립적으로 작동하며 journal을 재생해 업무 트랜잭션을 실행하지 않는다.

watchdog은 collector heartbeat, 생산자 heartbeat·journal 쓰기 실패 누적값, 디스크 여유, 최근 실패와 오류 예산 소진 속도를 검사한다. 알림은 `alerts/alert_*.json`에 기록하고 표준 출력에도 보낸다. `MONITORING_WEBHOOK_URL`을 설정하면 같은 알림을 HTTP POST로 전송한다. 전송 실패도 표준 출력에 남기며 로컬 알림 파일은 유지한다. API·worker는 유휴 중에도 약 5초마다 heartbeat를 갱신한다. 로컬 알림 파일을 쓸 수 없는 디스크 장애에서는 표준 출력과 설정된 webhook 경로가 남는다.

## 집계 계약

- 접수·조회 가용성은 `request_received`/`lookup_received`와 같은 attempt의 종료 레코드를 짝짓는다. 유효 호출의 HTTP 2xx만 성공이다. DB 실패 503은 ID가 없어도 분모·실패에 남는다. 응답 레코드가 없으면 미확정으로 표시하고 성공으로 채우지 않는다.
- 최초 판단은 첫 적격 접수·파일 제외·보완 revision의 수신 시각과 `judgment_committed`를 request ID로 연결한다. 이 이벤트는 Run의 `first_judgment_committed_at`이 실제 저장된 경우에만 worker가 기록한다. 재시도는 같은 요청의 최초 시각을 유지하고 120초 이후 성공은 회복 건수로 별도 집계한다. 120초를 지난 미완료 건은 120,000ms 실패 표본이다. 아직 120초가 지나지 않은 미완료 건은 대기 표본이다.
- 섀도 실행은 `run_kind=shadow`인 Run 집계와 판단 완료에서 제외하고 별도 건수를 보인다. revision/run 지연은 최초 요청 지연과 별개다. 파일 제외·첫 적격 보완 경로·SSE 전달·단계별 지연·버전별 결과를 기록된 필드만으로 집계한다. 사용량·비용처럼 생산자가 기록하지 않는 값은 `null`이다.
- 30일 오류 예산은 가용성 허용 실패율 0.1%, 판단 허용 실패율 1%다. 30일 전부터 이어진 수집기 체크포인트, 최근 heartbeat, 공백·손상 없음이 확인되지 않으면 `verified=false`와 잔여 예산 `null`로 표시한다. 최근 1시간 소진율은 조기 알림을 위해 별도로 계산하며 30일 달성 판정과 구별한다.
- 사람 검토 대기는 Neo4j `Review.created_at`/`decided_at`에서 별도 조회한다. 업무 DB가 중단되면 검토 지표만 `null`과 `source_status=unavailable`로 보이고 journal 기반 시스템 지표는 조회 가능하다.
- 보완 답변 대기는 journal의 `review_decided(action=request_info)`부터 같은 요청의 다음 `revision_received`까지 별도 계산한다. summary는 완료 대기의 p50/p95와 응답이 관측되지 않은 질문 수를 `supplement_wait_ms`로 반환한다. 이는 사람 검토 queue 지표 및 최초 판단 SLO 시계와 독립적이다.

## API와 대조

운영자 역할만 `/api/monitoring/summary`, `/slo`, `/failures`, `/alerts`, `/collection-status`에 접근할 수 있다. journal에 `tenant_id`가 있는 이벤트만 해당 운영자의 테넌트 집계에 포함된다. 새 SSE 이벤트에도 tenant ID를 적고, 이전 SSE 이벤트는 같은 기간의 테넌트가 확인된 request ID와 연결될 때만 포함한다. 연결할 수 없는 이전 이벤트는 합치지 않고 `unscoped_events`로 공개한다. `/failures`는 원인별 request/run/attempt ID와 시각을 돌려준다. `reconcile_commits(tenant_id, rows)`는 `db.tx.read_tx`로 Neo4j의 Request/Run ID와 journal ID를 비교해 누락·불일치를 반환한다. 이 함수는 조회만 수행한다.

모니터링 조회는 SQLite `events_tenant_ts` 식 인덱스(`payload.tenant_id`, `ts`, `kind`)를 사용한다. 같은 프로세스·테넌트·data directory의 summary/SLO/failures 요청은 최대 5초 동안 원시 이벤트 스냅샷을 공유하고, 동시에 시작한 조회는 하나의 SQLite 작업을 기다린다. 각 요청은 공유 스냅샷에서 자신의 기간을 다시 선택하므로 SLO 30일 창과 분모 정의는 그대로 유지된다. 이 짧은 캐시 기간에는 새 수집 이벤트가 최대 5초 늦게 보일 수 있다. summary의 journal 조회와 Neo4j 업무·검토 조회는 함께 시작한다. 현재 데이터에서 측정한 지연 및 조회 계획은 `artifacts/validation/perf/monitoring.md`에 기록했다.

새 접수에서는 요청자의 org ID를 Request와 journal에 기록한다. `/summary`의 `org`·`status` 필터는 기간 내 Request의 현재 조직·상태로 범위를 결정한 뒤 journal을 같은 요청 ID로 제한한다. 과거 Request에 조직 필드가 없으면 조직을 추정하지 않고 필터 대상 미확정 표본으로 공개한다. 필터 없는 journal 집계는 DB 장애에도 가능하지만, org/status 필터는 정확한 분모를 위해 업무 DB 장애 때 503을 반환한다. `version`은 worker에 기록된 Config 버전을 사용한다. 버전 필터에서는 요청 ID가 없는 실패를 정확히 귀속할 수 없어 가용성 분모와 비율을 `null`로 표시한다. 비용 미수집값도 `null`이다. 로컬 watchdog의 원격 수신·호스트 전체 유실 복구 보장은 T26 운영 검증 대상이다.

## 검증

`make up` 후 `cd backend && .venv/bin/pytest tests/integration/test_monitoring_collector.py -q`로 실제 writer 기록, SQLite 재수집 중복, 손상 줄, DB 실패 표본, 120초 실패·지연, 섀도 제외, 조직 저장·필터, 커밋 대조, 수집 공백, 빠른 오류 예산 소진·반복 장애 watchdog 알림, 30일 미검증 상태, 스냅샷 공유·만료·테넌트 격리·기존 SSE 귀속을 검사한다.

# Monitoring business filters and counts

T22의 API 경계 journal(`api_boundary_received`/`api_boundary_completed`)은 인증 전에도 남는다. DB 중단으로 인증이 끝나지 않은 접수는 `request_received`/`request_failed`의 `validity=undetermined` 표본으로 보존하며, tenant별 가용성 분모에 추정 합산하지 않는다.
인증 전 경계 진단 레코드는 정상 호출에도 tenant 미지정으로 남으므로, 모니터링의 `unscoped_events`는 이 두 진단 kind를 제외하고 실제 미귀속 업무 표본만 계산한다.

`GET /api/monitoring/summary` accepts `org` and `status` alongside its time and version filters. These filters select requests from tenant scoped `Request` records by current status and `org_id`/`org_ids`; journal rows are then restricted to those exact request IDs, so events with missing historical attribution do not inflate a filtered denominator. Business counts use the request creation cohort and remain separate from SLO calculations: `business.request_denominator`, `business.org_unconfirmed`, `business.auto_assignment_count` (Assignment pathway `auto`), and `business.review_completed_count` (persisted ReviewDecision records). Legacy requests with neither organization field are counted as `org_unconfirmed` when they fall in the selected scope.

The same summary includes review queue wait percentiles based on the request's organization and current status. These are operational workload measures, not SLO samples.

## 그룹 커밋 관측

API·worker의 `append()`는 아래 등급에 따라 반환한다. 내구 등급은 같은 그룹 커밋 큐에서 해당 레코드를 포함한 배치의 fsync가 끝나야 반환한다. 비동기 등급은 큐 등록 후 반환하며 정상적으로도 수집기가 최대 약 5ms 동안 디스크에 없는 레코드를 볼 수 있다. writer 실패는 `metrics/journal-writer-failure.json`과 생산자 heartbeat의 `journal_write_failures`로 확인한다. 비정상 종료에서 비동기 대기 배치가 유실되면 해당 진단 구간은 미확정으로 취급하고 DB 커밋 대조를 확인한다.

| 등급 | journal kind | 반환 조건 |
| --- | --- | --- |
| 내구 | `request_received/completed/failed`, `lookup_received/completed/failed`, `eligibility_received/completed/failed`, `revision_received/completed/failed` | fsync 완료. 가용성 분모·결과와 최초 판단 시작 시각을 보존 |
| 내구 | `worker_attempt_start/failure`, `worker_run`, `ownership_lost`, `judgment_preliminary`, `judgment_committed`, `retention_cleanup` | fsync 완료. 실행·시도 종료와 최초 판단의 대조 근거를 보존 |
| 비동기 | `sse_deliver`, `worker_step`, `external_model`, `external_masking`, `api_boundary_received/completed`, 기타 진단 kind | 큐 등록. 대량 진행·전달 기록은 그룹으로 기록 |

Neo4j 업무 커밋과 로컬 journal fsync는 하나의 원자적 트랜잭션이 아니다. 커밋 직후 journal append 전에 프로세스가 강제 종료되면 여전히 누락 가능성이 있으므로 `reconcile_commits` 결과를 운영자가 확인한다. 동기 등급은 append가 반환한 뒤의 버퍼 유실을 막는다.

로컬 경계 요청 100회 측정(2026-10-04, `POST /api/requests`, 인증 전 401, 동일 프로세스 TestClient, 각 단계 별도 DATA_DIR)에서 기존 동기 writer의 p50/p95는 3.068/4.588ms, 그룹 커밋 writer는 1.949/3.151ms였다. 이는 접수 경계의 journal 비용을 포함하지만 인증된 202 접수와 DB·외부 모델 경로의 지연 개선값은 아니다.
