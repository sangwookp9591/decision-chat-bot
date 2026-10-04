# 운영 Runbook (개발 구성)

## 기본 확인

- `/api/health`: 프로세스 응답, `/api/ready`: Neo4j 연결 포함 준비 상태.
- `docker compose ps`, `ps -axo pid,command`, worker·collector·watchdog 출력, `DATA_DIR/metrics/` heartbeat 확인.
- Neo4j 업무 상태는 DB를 통해 확인한다. 지원 DB 접근은 공개 `db.tx.read_tx`/`write_tx`, `db.jobs`, `db.requests`, `db.events`, `db.audit` 함수를 사용한다. journal 재생으로 업무 상태를 다시 실행하지 않는다.
- 장애 진단은 `attempt_id`부터 찾는다. `DATA_DIR/journal/current.jsonl` 및 `archive-*.jsonl`에서 attempt ID를 찾고, SQLite metrics `events`에서 같은 ID의 수신/완료 이벤트와 `error_class`를 조회한다. 이벤트에 `request_id`/`run_id`가 있으면 인증된 운영 조회에서 Trace로 이동한다. 비밀이나 원문을 검색 결과/로그에 붙이지 않는다.

## 증상별 조치

| 증상 | 확인 | 복구 |
| --- | --- | --- |
| Jev 오류/지연 | API 또는 worker의 attempt/run ID, `error_class`, deadline·attempt 횟수, `JEV_MODE`; 키 값은 출력하지 않음 | 설정된 서버 secret의 존재/권한을 비밀 저장소에서 확인하고 upstream 상태·한도를 확인. transient 오류는 제한된 재시도 정책에 따름. 실패 Run은 새 실행 정책을 검토; 운영에서 mock으로 전환해 성공 처리하지 않음 |
| Neo4j 중단 | `docker compose ps`, `/api/ready`, Neo4j 컨테이너 로그와 포트, 디스크 | 원인 확인 뒤 `make up`, `/api/ready`와 DB 조회 확인. 장애 중 HTTP 실패는 journal과 metrics에서 attempt를 대조. 미커밋 입력은 성공으로 가정하지 않음 |
| 파서 실패/부분 첨부 | 요청 ID, revision, 첨부 상태·파서 오류, 크기/형식 한도 | 확인 가능한 파일만 재첨부하거나 사용자가 제외하도록 안내. 제외/재첨부는 새 revision 경로로 처리하고 이전 실행 기록 유지. OCR은 지원되지 않음 |
| SSE 정지/누락 | 로그인 세션, 브라우저 연결, `Last-Event-ID`, tenant 이벤트 seq와 snapshot 응답 | 재연결 후 영속 상태/snapshot을 기준으로 화면 복구. 네트워크/서버 복구 뒤 이벤트 순서와 상태를 대조. 이벤트를 수동으로 재생해 업무를 실행하지 않음 |
| Redis 중단 | `docker compose ps redis`, Redis 로그, API의 Redis publish/subscriber 오류와 `after_commit_failures`·`publish_failures` | API는 짧은 Neo4j 폴링과 로컬 연결 상한으로 자동 폴백한다. Redis 복구 후 구독이 재연결되면 Neo4j seq 조회로 누락을 보정한다. Redis 메시지만으로 업무 성공을 판단하지 않음 |
| worker 정지 또는 lease 인계 | worker heartbeat, 프로세스, pending/running Job의 owner·generation·expiry, run trace | worker를 재시작. 만료 lease는 정상 claim/takeover에 맡기고 과거 owner의 결과를 수동 커밋하지 않음. 시험 worker는 `--tenant <전용 tenant>`로 제한 |
| collector/watchdog 알림 | collector heartbeat/ticks, offsets/issues/gaps, watchdog JSON/stdout, disk free, webhook 수신 실패 | 먼저 journal/metrics 볼륨 공간과 권한을 확보하고 collector/watchdog를 재시작. 누락 구간은 `관측 불완전`으로 남김; 정상 0건으로 덮지 않음. webhook은 별도 수신 경로이며 실패 기록 확인 |
| journal 디스크 부족/쓰기 실패 | `DATA_DIR` 여유 공간, `disk_low`, producer heartbeat의 write failure count, journal 파일 크기 | 백업/보존 책임자 승인 절차에 따라 공간 확장 또는 보관 파일 이관. 현재 journal을 임의 삭제하지 않음. 쓰기 복구 후 writer와 collector를 확인하고 metrics 재수집/DB commit 대조 |

## 보존 정리 (개발 기본값)

`make retention RETENTION_ARGS=--dry-run`으로 삭제 예정 수를 먼저 확인한다. 검토 후 `make retention`을 실행하고 JSON 결과와 `DATA_DIR/journal/current.jsonl`의 `retention_cleanup` 요약을 보관한다. 단일 tenant 확인은 `make retention RETENTION_ARGS="--tenant <tenant-id> --dry-run"`처럼 실행한다. 현재 활성 정책의 retention 값을 읽는다.

초기 기간(Event 90일, Idempotency 30일, 만료 Session +7일, LoginAttempt 실패 창 만료 후, journal/metrics 90일)은 **운영 확정 전 개발 기본값**이다. Event 정리는 EventCounter의 `retained_from_seq`를 앞으로 이동시키지만, 현 SSE 라우터가 해당 값을 확인하지 않는 계약 불일치가 있다. SSE 소비자의 snapshot 복구 시험과 라우터 반영 전에는 운영 데이터에 보존 정리를 적용하지 않는다. 업무 기록 및 원본 업로드 파일은 이 명령의 대상이 아니다.

## 중단 및 복구 순서

일반 정지는 API·worker·collector·watchdog·Vite를 각각 Ctrl-C하고 마지막에 `make down`을 실행한다. 백업/복원 전에는 모든 writer와 collector를 정지한다. 재시작은 `make up`, 스키마 확인, API 준비 상태, worker/관측 프로세스, tenant·요청/Trace 조회 순서로 확인한다. 운영 호스트 유실은 로컬 파일만으로 복구할 수 없으므로 외부 복제 백업과 별도 감지/복구 절차가 필요하다.

운영 dump는 기본 `decision-chat-bot` 컨테이너를 대상으로 하지 않는다. writer와 기본 `make up` 프로젝트를 멈춘 뒤 `jevtriage-backup` 프로젝트, `jevtriage-backup-neo4j-1` 컨테이너, 7689 포트를 사용한다. 백업 스크립트는 컨테이너의 Compose project/포트/data mount를 확인하고, default 공유 DB가 같은 데이터 디렉터리를 사용하는 중이면 즉시 거절한다. 오프라인 dump 중에는 전용 Neo4j만 정지되며 완료 후 별도 명령으로 다시 시작한다. 운영에서는 정지 시간을 정하고 모든 애플리케이션 writer/collector가 멈춘 것을 확인한다.

이 Runbook은 개발 구성에 대한 절차다. 알림 수신자·보존·RPO/RTO·운영 인증은 [배포 전 검토](DEPLOYMENT.md)에 따라 결정되지 않았다.

## journal 그룹 커밋 복구

정상 종료에서는 API lifespan과 worker 종료가 journal 큐를 flush한다. 접수·조회·revision·실행·판단의 핵심 레코드는 append가 fsync 완료를 기다리고, SSE·단계 진행 등 진단 레코드는 그룹 큐에 비동기로 남긴다(등급 표: `docs/architecture/MONITORING.md`). 강제 종료나 전원 손실 시 비동기 대기 배치가 사라질 수 있다. DB 커밋 직후 핵심 journal append 전에 종료된 경우도 원자성이 없어 누락 가능하다. `metrics/journal-writer-failure.json`의 시각·실패 카운터와 API·worker heartbeat를 확인하고, 수집기 오프셋 및 Neo4j 커밋을 대조한다. writer 실패 후 append는 동기로 복구를 재시도하며, 실패하면 예외를 전파한다. 디스크 공간·권한을 복구하고 필요하면 프로세스를 재시작한 뒤 미확정 SLO 구간을 표시한다.
