# 이벤트 스트림과 복구

T14-B 백엔드 계약. 사용자 이벤트의 기준 저장소는 Neo4j `Event`이며, tenant별 `EventCounter.seq`가 트랜잭션 안에서 단조 증가한다. stream 전송은 이 저장 기록을 짧은 간격으로 다시 읽어 프로세스 재시작 후에도 재개할 수 있다.

## API

- `GET /api/events/stream`: 로그인 세션 필수. `Last-Event-ID` 또는 `?after=` 중 하나를 사용한다. SSE `id`는 tenant 이벤트 seq, `event`는 kind다. JSON은 request/run 식별자와 상태만 포함하며 저장 payload의 임의 필드는 노출하지 않는다.
- 요청 연결 이벤트는 매번 Request 메타데이터를 확인하고 `can_view_request` 정책을 적용한다. 접근 불가 이벤트는 전달하지 않는다. tenant가 다른 요청은 tenant 조건에서 조회되지 않는다.
- cursor가 저장 head보다 앞서 있거나 보존 기한보다 오래되면 `snapshot-required`를 보내고 스트림을 닫는다. 클라이언트는 권한 확인 후 아래 snapshot을 읽고 새 cursor로 연결한다.
- 프로세스의 tenant별 단일 폴러가 0.2초 간격으로 새 이벤트를 조회해 연결들에 전달한다. 각 연결은 독립 cursor와 `can_view_request` 권한 필터를 유지한다. 폴러는 최대 1,000건씩 순서대로 읽고, 배치의 request ID를 한 번의 Cypher로 조회한다. 느린 연결의 배치 대기열이 넘치면 `snapshot-required`를 보내며 연결을 닫는다. 빈 대기에는 SSE comment를 보내고 15초마다 heartbeat comment를 보낸다. 연결 상한은 프로세스당 100개다. `SSE_POLL_SECONDS`, `SSE_MAX_CONNECTIONS`, `SSE_MAX_AFTER_AGE_SECONDS` 환경변수로 조정한다.
- `GET /api/events/snapshot?request_id=…`: 요청 상태, active run, 해당 요청의 최신 영속 이벤트 seq를 반환한다. 접근 불가/존재하지 않는 요청은 동일한 404다.

## 전달 지연

성공적으로 전달한 각 이벤트는 `kind=sse_deliver`로 독립 journal에 기록되며, `duration_ms`는 Event `created_at`부터 전송 직전까지의 지연이다. 저널에는 이벤트 ID와 request/run ID만 포함하고 이벤트 본문은 쓰지 않는다. journal 쓰기 실패는 응답 전달 이후 전파될 수 있다.

FIX-SSE 확인에서 Neo4j 5.26 `SHOW INDEXES`는 `event_tenant_seq` RANGE 색인(`Event.tenant_id, Event.seq`)을 반환했고, `EXPLAIN`은 `seq > after_seq` 조회에 `NodeIndexSeek`를 선택했다. 이전 경로는 연결 20개와 0.5초 간격에서 빈 구간에도 초당 약 40개의 이벤트 조회를 실행하고, 전달하는 요청 이벤트마다 별도의 Request 조회를 실행했다. 새 경로는 API 2프로세스·tenant당 한 폴러·0.2초 간격에서 빈 구간에 초당 약 10개의 이벤트 조회를 실행한다. 새 이벤트 배치마다 Request ID 집합을 한 번에 조회하며, 각 연결은 해당 메타데이터를 이용해 따로 권한을 확인한다. 이 수치는 설정에서 계산한 조회 빈도이며 실측 지연은 [FIX-SSE 보조 측정](LOADTEST.md#fix-sse-보조-측정)에 기록한다.

## 한계와 클라이언트 동작

이벤트 seq는 tenant 전역이므로 권한 필터를 통과하지 않은 요청의 seq에는 공백이 생길 수 있다. 이는 누락이 아니라 권한 경계다. 클라이언트는 중복 ID를 무시하고 최종 업무 상태를 snapshot으로 대조해야 한다. 연결 제한은 단일 프로세스 기준이며 다중 worker 전체의 통합 상한은 배포 계층에서 설정해야 한다.
