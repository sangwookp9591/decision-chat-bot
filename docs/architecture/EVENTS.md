# 이벤트 스트림과 복구

T14-B 백엔드 계약. 사용자 이벤트의 기준 저장소는 Neo4j `Event`이며, tenant별 `EventCounter.seq`가 트랜잭션 안에서 단조 증가한다. Redis가 설정되면 커밋 후 `tenant:{tenant_id}` 채널에 seq를 알리고 각 API 인스턴스가 Neo4j에서 재생한다. Redis 메시지는 영속 기록이 아니므로 재연결과 누락 보정은 항상 Neo4j seq를 기준으로 한다.

`realtime.notifier.publish_job(job_id)`와 `realtime.subscriber.JobSubscriber`는 `jobs` 채널을 제공한다. worker는 새 Job 커밋 후 알림을 받아 발견 질의를 앞당길 수 있으며, 주기적 Job 발견은 계속 필요하다.

## API

- `GET /api/events/stream`: 로그인 세션 필수. 첫 연결은 `?after=`를 사용하고 EventSource 자동 재연결이 `Last-Event-ID`를 붙이면 헤더가 우선한다. 둘 다 있어도 400을 반환하지 않는다. SSE `id`는 tenant 이벤트 seq, `event`는 kind다. JSON은 request/run 식별자와 허용된 상태 필드만 포함하며 저장 payload의 임의 필드는 노출하지 않는다.
- 요청 연결 이벤트는 매번 Request 메타데이터를 확인하고 `can_view_request` 정책을 적용한다. 접근 불가 이벤트는 전달하지 않는다. tenant가 다른 요청은 tenant 조건에서 조회되지 않는다.
- cursor가 저장 head보다 앞서 있거나 보존 기한보다 오래되면 `snapshot-required`를 보내고 스트림을 닫는다. 클라이언트는 권한 확인 후 아래 snapshot을 읽고 새 cursor로 연결한다.
- 프로세스의 tenant별 단일 폴러가 Redis 알림이 오면 즉시 새 seq 범위를 조회하고 연결들에 전달한다. 알림 누락에 대비해 5초마다 백업 조회하며 Redis 미설정·장애 시 0.2초 폴링으로 전환한다. 각 연결은 독립 cursor와 `can_view_request` 권한 필터를 유지한다. 폴러는 최대 1,000건씩 순서대로 읽고, 배치의 request ID를 한 번의 Cypher로 조회한다. 느린 연결의 배치 대기열이 넘치면 `snapshot-required`를 보내며 연결을 닫는다. 빈 대기에는 SSE comment를 보내고 15초마다 heartbeat comment를 보낸다. Redis 연결 시 연결 상한은 모든 API 인스턴스 합산 100개이며 TTL 슬롯으로 누수를 제한한다. Redis 미설정·장애 시 프로세스 로컬 상한을 사용한다. `REDIS_URL`, `SSE_POLL_SECONDS`, `SSE_MAX_CONNECTIONS`, `SSE_MAX_AFTER_AGE_SECONDS` 환경변수로 조정한다. 세션은 15초마다 다시 확인하며 폐기·만료 시 `session-expired` 이벤트와 함께 닫는다.
- 현재 제품 코드가 발행하는 저장 이벤트 kind: `run.step`, `judgment_saved`, `judgment_failed`, `reanalysis.compared`, `review_decided`, `auto_assignment_deferred`, `assignment_created`, `task.transitioned`, `policy.published`, `rule.decision`, `rule.version_created`, `rule.validated`, `rule.publish`, `rule.stop`, `rule.revert`. 정책 되돌리기도 새 Config를 게시하므로 `policy.published`를 발행한다. 저장 이벤트 외 스트림 제어 이벤트는 `snapshot-required`, `session-expired`다.
- 진행 이벤트 `request.received`, `judgment.partial`, `judgment.evidence_ready`, `judgment.tasks_ready`도 요청 단위 권한 필터를 거친다. `classifications`·`confidences`·`risk_flags`는 허용된 분류 키와 단순 분류값·수치·불리언만, `preliminary`는 불리언만, `evidence_count`·`task_count`는 0 이상의 정수만 SSE에 포함한다. 원문 필드는 전달하지 않는다.
- `GET /api/events/snapshot?request_id=…`: 요청 상태, active run, 해당 요청의 최신 영속 이벤트 seq를 반환한다. 접근 불가/존재하지 않는 요청은 동일한 404다.

## 전달 지연

성공적으로 전달한 각 이벤트는 `kind=sse_deliver`로 독립 journal에 기록되며, `duration_ms`는 Event `created_at`부터 전송 직전까지의 지연이다. 저널에는 이벤트 ID와 request/run ID만 포함하고 이벤트 본문은 쓰지 않는다. journal 쓰기 실패는 응답 전달 이후 전파될 수 있다.

FIX-SSE 확인에서 Neo4j 5.26 `SHOW INDEXES`는 `event_tenant_seq` RANGE 색인(`Event.tenant_id, Event.seq`)을 반환했고, `EXPLAIN`은 `seq > after_seq` 조회에 `NodeIndexSeek`를 선택했다. 이전 경로는 연결 20개와 0.5초 간격에서 빈 구간에도 초당 약 40개의 이벤트 조회를 실행하고, 전달하는 요청 이벤트마다 별도의 Request 조회를 실행했다. 새 경로는 API 2프로세스·tenant당 한 폴러·0.2초 간격에서 빈 구간에 초당 약 10개의 이벤트 조회를 실행한다. 새 이벤트 배치마다 Request ID 집합을 한 번에 조회하며, 각 연결은 해당 메타데이터를 이용해 따로 권한을 확인한다. 이 수치는 설정에서 계산한 조회 빈도이며 실측 지연은 [FIX-SSE 보조 측정](LOADTEST.md#fix-sse-보조-측정)에 기록한다.

## 한계와 클라이언트 동작

이벤트 seq는 tenant 전역이므로 권한 필터를 통과하지 않은 요청의 seq에는 공백이 생길 수 있다. 이는 누락이 아니라 권한 경계다. 클라이언트는 중복 ID를 무시하고 최종 업무 상태를 snapshot으로 대조해야 한다. Redis 연결 슬롯은 TTL 30초이며 활성 SSE 연결은 10초마다 갱신한다. Redis 장애 시 로컬 상한으로 폴백하므로 그 동안 전체 인스턴스 합산 상한은 보장되지 않는다.

## 프런트 구독 계약 (UX-1)

- **kind 목록**: EventSource는 이름이 같은 `event:`만 리스너에 전달하므로 프런트는 서버가 발행하는 kind를 `frontend/src/state/events.ts`의 `EVENT_KINDS`에 정확히 같게 둔다. 현재 목록은 `run.step`, `judgment_saved`, `judgment_failed`, `reanalysis.compared`, `review_decided`, `assignment_created`, `auto_assignment_deferred`, `task.transitioned`, `policy.published`, `rule.decision`, `rule.version_created`, `rule.validated`, `rule.publish`, `rule.stop`, `rule.revert`이며 특수 이벤트 `snapshot-required`·`session-expired`는 별도로 처리한다. 예전에 구독하던 `request.updated`·`run.updated`·`run.started`·`run.completed`는 서버가 발행하지 않아 제거했다. `events.test.ts`가 백엔드 소스에서 `append_event*`·`event_kind` 호출을 읽어 목록이 어긋나면 실패한다.
- **업무·검토 화면 갱신**: `task.transitioned`는 업무 상태 변경을 커밋한 뒤 발행한다. 스트림은 요청 접근 권한을 확인한 뒤 이벤트의 `request_id`와 허용된 상태 필드를 전달한다(업무 ID는 페이로드 허용 목록에 없어 전달하지 않는다). 열린 업무 화면은 현재 필터 목록을 다시 읽고, 선택한 상세가 해당 요청에 속하면 상세도 다시 읽어 상태 전이 버튼을 최신 상태로 맞춘다. 정상 검토 생성은 판단 저장 트랜잭션에서 `judgment_saved`, 자동 배정이 검토로 전환된 경우는 `auto_assignment_deferred`, 검토 변경은 `review_decided`를 발행한다. 검토 대기 화면은 세 이벤트에서 현재 선택된 상태 필터로 목록을 다시 읽으며 선택 상세를 유지한다. 별도 `review.created` 이벤트는 발행하지 않는다.
- **재연결**: 브라우저 자동 재연결은 `Last-Event-ID`를 `?after=`와 함께 보내 400을 받으므로 오류가 나면 클라이언트가 소스를 닫고 지수 백오프(1→2→4…최대 30초, 연속 6회 실패 시 `disconnected`)로 직접 `?after=<마지막 seq>`만 붙여 다시 연결한다. 오류 때마다 `/api/auth/me`를 한 번 조회해 세션 만료는 로그인 화면으로 전환한다. `session-expired` 이벤트도 같은 방식으로 처리한다.
- **복구**: `snapshot-required`이면 요청 화면은 snapshot을 읽어 커서를 맞춘 뒤 `onSnapshot`·`onResync`로 다시 조회하고 재연결한다. 요청이 없는 화면(정책)은 저장된 커서를 버리고 화면 재조회 콜백을 부른 뒤 처음부터 한 번 다시 연결한다.
- **커서 범위**: 커서는 tenant 전역 seq이므로 sessionStorage 키를 `jevtriage:last-event-seq:<tenant>:<user>`로 둔다. 같은 탭에서 다른 tenant로 로그인해도 이전 커서가 섞이지 않는다.

### 정책 화면의 재생 이벤트 처리 (UX-6, F2)

- 커서가 없는 새 세션은 과거 `policy.published`를 재생한다. 정책 화면은 payload `version`이 화면의 활성 버전 이하이면 무시하고, 더 새로운 버전일 때만 반응한다(첫 조회가 끝나기 전 이벤트도 무시: 조회 결과가 이미 최신).
- 편집 중(입력한 필드가 있음)에 새 버전이 오면 덮어쓰지 않고 '새 버전 v N이 게시되었습니다 — 새 버전 반영 / 내 편집 유지'를 묻는다. 편집이 없으면 조용히 다시 불러온다. 조회 응답은 세대 번호로 검사해 늦게 도착한 옛 응답이 새 응답을 덮지 못한다.
- 서버 검증·게시는 렌더 시점 state가 아니라 키 입력마다 갱신하는 draft snapshot(ref)을 보낸다.
- 요청 목록은 요청 상세 구독과 별개의 tenant 이벤트 스트림으로 갱신한다(`PROGRESSIVE_RESULTS.md` 'P7 보완').
