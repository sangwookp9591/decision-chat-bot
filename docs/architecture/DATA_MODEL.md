# 데이터 모델과 트랜잭션 경계

T04 구현 기준, 2026-10-03. Neo4j가 업무 상태의 기준 저장소이고 journal은 독립 관측 기록이다.

## 노드와 저장 형식

| 영역 | 라벨 | 핵심 속성 및 관계 |
| --- | --- | --- |
| 접수 | `Request`, `InputRevision`, `Attachment` | `Request.id`, `tenant_id`, `status`, `latest_revision_id`, `active_run_id`; `Request-[:HAS_REVISION]->InputRevision` |
| 실행 | `Run`, `RunStep`, `Job` | Run의 `request_id`, `input_revision_id`, `kind`(`normal`/`shadow`), 고정 Config 버전; Job의 `owner_id`, `lease_generation`, `lease_expires_at`, `status` |
| 검토·배정 | `Review`, `ReviewDecision`, `Assignment`, `Task`, `Team` | 검토 대상은 request/revision/run/draft/review 버전의 결합. Assignment는 요청당 하나, Task는 배정과 초안 업무 ID 쌍당 하나 |
| 정책·학습 | `Policy`, `ConfigVersion`, `Correction`, `RuleCandidate`, `RuleDecision`, `RuleVersion`, `ValidationRun`, `RuleApplication` | 수정 원안은 보존. 규칙 버전은 `rule_id@version`, 실행은 시작 시 Config 버전을 고정 |
| 판단 관계 | `EvidenceSpan`, `ModelOutput`, `RunStep` 및 위 학습 노드 | 08_LEARNING_LOOP 3절의 `CITES`, `CORRECTS`, `RECORDED`, `SUPPORTED_BY`, `DECIDES`, `DERIVED_FROM`, `PUBLISHED_IN`, `VALIDATES`, `APPLIED`, `USED_OUTPUT` 관계만 실제 생성 시 기록. T29가 관계 생성·경로 질의를 담당 |
| 운영 | `Idempotency`, `EventCounter`, `Event`, `Audit` | Idempotency는 `(tenant_id, scope, key)`, EventCounter는 tenant별 seq, Event는 순서·payload JSON, Audit은 행위자·대상·전후 요약·사유 |

모든 업무 질의에 인증에서 결정한 `tenant_id`를 포함한다. 원문과 모델 반환값은 조회 목적에 따라 분리한다. `ModelOutput.answers`는 Jev의 Choice `choice/probabilities/confidence`, Score `score/legend/probabilities/confidence`, Noul `noul`을 타입별 원형으로 보존하는 JSON 필드로 다루며, 관계 탐색이 필요한 판단·근거·업무 식별자와 위치는 별도 노드·관계로 저장한다. 대용량 원본 파일은 `.data/files`에 두고 Neo4j에는 메타데이터와 해시를 둔다. Neo4j 속성에는 Python dict를 직접 넣지 않고 JSON 문자열로 직렬화한다.

## 제약, 색인, 잠금

`python -m jevtriage.db.schema`는 일반 라벨의 `id` 유일 제약, tenant 범위 ID를 쓰는 라벨의 `(tenant_id, id)` 복합 유일 제약, `Assignment(tenant_id, request_id)`, `Task(assignment_id, draft_task_id)`, `Idempotency(tenant_id, scope, key)`, `EventCounter(tenant_id)` 유일 제약 및 조회 색인을 `IF NOT EXISTS`로 만든다. 이전 전역 ID 제약은 `DROP IF EXISTS`로 제거한 뒤 tenant 복합 제약을 설치한다. 두 번 실행해도 같은 스키마가 유지된다. `RuleVersion.id`는 공개 식별자 `rule_id@version`이며 tenant 사이에 같은 값을 쓸 수 있다. AI가 결정적으로 만든 `RuleCandidate.id`도 tenant 사이에 같을 수 있다. [Neo4j 5 공식 제약 문서](https://neo4j.com/docs/cypher-manual/5/constraints/create-constraints/)에서 복합 속성 유일 제약을 확인했고, Neo4j 5.26 Community에서 제약 생성과 같은 ID·다른 tenant 노드 2개 저장을 실행해 확인했다.

2026-10-04 추가: `Session.token_hash`, 현재 전역 email 로그인 계약에 맞춘 `User.email`, `ConfigVersion(tenant_id,version)`, `Event(tenant_id,seq)`, `Judgment(tenant_id,run_id)`는 유일 제약이다. `Org`, `Judgment`, `Draft`, `DraftTask`, `RuleSeries`, `LoginAttempt`의 ID는 tenant 범위로 제약한다. `Judgment`처럼 테스트나 외부 입력에서 결정적 ID를 쓰는 노드도 tenant 사이에 같은 ID를 저장할 수 있다. 기존 `Event(tenant_id,seq)`와 `Judgment(tenant_id,run_id)` 비유일 색인은 제약의 내장 range 색인과 충돌하므로 먼저 제거한다. 추가 range 색인은 `Judgment`의 request 조회, `ModelOutput`의 run 조회, `Draft`·`DraftTask`·`EvidenceSpan`·`RunStep`의 관련 ID 조회, `Event`의 request 조회, `Job`의 status/lease 조회, `Review`·`Task`의 request 조회를 지원한다. Neo4j 5.26 Community에서 두 번 마이그레이션하고 10개 대표 `EXPLAIN` 계획의 index seek를 확인한다.

Worker는 tenant 허용 목록이 있으면 그 목록으로 후보를 제한한다. 허용 목록이 비어 있으면 모든 tenant의 Job을 처리하되 `Job.status` range 색인에서 후보를 찾는다. 대기 Job 또는 lease가 만료된 실행 Job 한 개를 생성 시각 순으로 선택하고 같은 쓰기 트랜잭션에서 잠금·조건 재검사·generation 증가·lease 부여를 수행한다. 빈 폴링 간격은 기본 0.5초에서 지수적으로 증가하며 `--max-poll-seconds` 기본 8초를 넘지 않는다. 그래프 조회는 간선 양 끝의 tenant를 검사하고, ID로 관계 속성을 찾을 때 이미 알고 있는 노드 라벨을 사용한다. `elementId` 기반 직접 조회는 tenant 필터를 추가로 유지한다.

`write_tx`와 `read_tx`는 callback에 `TenantTx`를 전달한다. `tx.run`은 `$tenant_id`를 자동 주입하고 등록된 별칭 `$tenant`도 같은 값으로 주입한다. 호출자가 다른 tenant 값을 넘기면 예외를 낸다. `JEVTRIAGE_STRICT_TENANT=1`인 테스트에서는 두 매개변수 중 하나도 참조하지 않는 질의를 거부한다. 운영에서는 `tenant_scope_warnings` 지표를 증가시키고 경고 로그를 남긴다. worker 후보 발견·선점과 전체 tenant 보존 정리는 사유를 기록하는 `cross_tenant_tx(reason, ...)`로 실행한다. DB driver와 transaction 경계 모듈 외의 애플리케이션 코드는 직접 driver/session을 사용하지 않는다.

엄격 모드 전수 시험에서 tenant 별칭을 정규화한 질의는 `graph/query.py`의 `$t` 사용처이며, worker의 `worker-discovery`와 보존 정리의 전체 tenant 발견을 명시적 교차 tenant 경로로 옮겼다. 통합 시험의 `test_judgment_graph.py`, `test_source_document.py`에 있던 `$t` 별칭 및 `test_retention.py`의 tenant 없는 검증 질의도 갱신했다. 문자열 검사는 매개변수 참조를 확인하며 Cypher의 모든 경로와 관계 확장을 증명하는 정적 분석은 아니다. 각 질의는 여전히 실제 노드의 tenant 속성을 검사해야 한다.

R8 질의 점검: `graph/query.py`의 관계 속성 조회 시작점과 `learning/shadow.py`의 보호 상태 스냅샷은 라벨별 조회로 바꿨다. `graph/query.py`의 `elementId` 기반 조회·경로 확장은 tenant를 양 끝에서 확인하며, `elementId` 직접 조회라서 라벨 색인 대신 ID 조회를 사용한다. `review/store.py`의 `Correction` 선택 조회와 `review/service.py`의 첨부 조회는 대상 노드에도 tenant 조건을 추가했다. `auth/core.py`의 로그인 email 조회는 인증 전에 tenant를 알 수 없는 경로이며, `ingest/api.py`에는 라벨 없는 `MATCH`가 없다. `MEMBER_OF`는 별도 `Membership` 노드가 아닌 관계라서 노드 유일 제약을 만들지 않았다.

활성 판단 Run의 생성과 Config 버전 고정은 `start_run_in_tx`/`pin_config_for_run_in_tx`가 담당한다. Task의 `block_reasons`는 미해결 전제가 있는 본업무의 시작 차단 근거다. 태스크 목록·상세 응답은 서버가 `can_start`와 `start_blockers`를 함께 계산해 반환하며, 상태 전이도 같은 판정 함수를 사용한다. 완료된 `confirmation_task` 선행 업무는 `feasibility_unresolved` 차단을 해제하고, 진행 중인 선행 업무나 다른 차단 근거가 남으면 진행 전이를 409로 거절한다.

잠금 순서는 `Request → Run → Review → Assignment → Job`이며 같은 라벨에서는 ID 순서다. `lock_nodes_in_tx`가 잘못된 순서를 거절한다. 실제 쓰기 잠금은 해당 노드의 `_lock` 속성을 `randomUUID()`로 바꾸어 얻고 트랜잭션이 끝날 때까지 유지한다. EventCounter는 tenant별로 잠그고 seq 증가와 Event 생성이 같은 트랜잭션이므로 롤백 시 결번이 없다. Job은 소유권 검증과 결과 쓰기를 같은 트랜잭션에서 수행한다.

## 공개 함수와 경계

R2에서 확인한 인증·검토·이벤트·그래프·관측·모니터링·학습 후보·판단 진행·평가 API의 직접 Cypher는 저장소 또는 query 모듈로 이동했다. 인증은 `auth.store`, 검토 목록의 긴급도는 `review.store`, SSE 커서·스냅샷은 `events.store`, 그래프 범위 조회는 `graph.query`, 실행 관측 상세는 `observe.trace_store`, 운영 대조는 `monitoring.aggregates`, 학습 후보는 `learning.candidates_store`, 판단 진행은 `judgment.progress_store`, 평가 레이블은 `evaluation.store`가 읽고 쓴다. SQLite 관측 스키마와 연결은 `metrics_store`가 소유하며 `journal.collector`의 이전 `connect`·`metrics_path` 이름은 호환성을 위해 재수출한다. 이 이동은 질의문, tenant 조건, 반환 형식을 바꾸지 않는다.

활성 Run·Job 생성 구현은 `db.runs.start_run_in_tx`가 소유한다. 이전 `domain.runs.start_run_in_tx` 경로는 통합 호출자의 호환 import로만 남았다. 검토와 판단이 함께 쓰는 질문 선택지·자동 배정 조건·초안 표시 메타데이터는 순수 `domain` 모듈에서 읽는다.

정책 버전 고정의 Cypher 구현은 `db.pinning.pin_config_for_run_in_tx`가 소유한다. `policy.pinning`은 이전 import 경로를 재수출한다. 접수 후 worker 깨우기는 `worker_wakeup`의 프로세스 로컬 등록소를 사용하고 Redis 알림은 기존대로 발행한다. 이 변경은 Job lease, 이벤트 순서, 응답 JSON에 영향을 주지 않는다.

| 모듈 | 함수 | 사용 조건 |
| --- | --- | --- |
| `db.driver` | `get_driver`, `close_driver`, `create_driver` | 실행 루프별 async 드라이버; 앱 종료 시 close |
| `db.tx` | `write_tx(tenant_id, fn)`, `read_tx(tenant_id, fn)`, `cross_tenant_tx(reason, fn)`, `db_now`, `db_now_in_tx` | callback은 async. 드라이버 관리형 재시도 때문에 callback 안에는 DB 동작만 넣고 외부 호출·파일 쓰기를 넣지 않는다. 스키마 관리와 인증 전 email/token 조회처럼 tenant 미확정 경로는 구체적인 사유를 기록하는 `cross_tenant_tx`를 사용한다 |

평가 라벨 export는 `JEVTRIAGE_TENANT_ID`로 tenant를 지정하고 `read_tx`로 해당 tenant의 라벨만 읽는다.
| `db.locks` | `lock_node_in_tx`, `lock_nodes_in_tx` | 변경 대상 잠금은 같은 트랜잭션에서 획득 |
| `db.jobs` | `create_job`, `claim_or_takeover`, `heartbeat`, `verify_owner_in_tx` | 결과·단계·이벤트 커밋 전에 마지막 함수를 **같은 쓰기 트랜잭션**에서 호출. 실패하면 `OwnershipLost` |
| `db.requests` | `create_request`, `add_input_revision`, `set_active_run`, `assert_active_run_in_tx` | 활성 결과·검토 대상·배정 포인터 변경 전에 활성 실행 확인. 불일치하면 `StaleRun` |
| `db.events` | `append_event_in_tx`, `append_event`, `list_events` | 사용자 SSE 이벤트만 append; `after_seq` 이후 순서 조회 |
| `db.idempotency` | `get_or_create_in_tx`, `get_or_create` | 동일 키·해시는 저장 결과 재반환, 다른 해시는 `IdempotencyConflict`(409). 권한은 결과 재반환 전에 호출 측에서 재검사 |
| `db.audit` | `append_audit_in_tx` | 업무 변경과 같은 트랜잭션에서 감사 기록 생성 |
| `domain` | `new_id`, 상태 enum, `assert_transition` | 허용되지 않은 전이는 `InvalidTransition` |
| `journal.writer` | `JournalWriter.append`, `failure_count` | API/worker 경계에서 DB와 독립적으로 사용. 쓰기 실패를 상위에 전파 |

예: worker 결과를 저장할 때는 다음 순서를 지킨다.

```python
async def save_step(tx):
    await verify_owner_in_tx(tx, tenant_id, job_id, owner_id, generation)
    await assert_active_run_in_tx(tx, tenant_id, request_id, run_id, revision_id)
    # 이후 이 tx에서 단계·판단 결과·이벤트를 함께 쓴다.

await write_tx(tenant_id, save_step)
```

검토 승인·업무 배정은 T11에서 Request·Review 잠금, 최신 revision/run/초안/검토 버전·권한·필수 검토·기존 배정을 재확인한 뒤 Assignment·Task·Audit·Event·Idempotency 결과를 한 `write_tx`에 넣는다. 섀도 실행은 요청 최신 포인터·검토 큐·배정·알림·사용자 SSE를 변경할 수 없다. 게시·중단·되돌리기는 T15/T32에서 새 Config 버전과 감사·이벤트를 한 트랜잭션에 넣는다.

## 독립 journal

경로는 `DATA_DIR/journal/current.jsonl`, 회전 파일은 `archive-<uuid>.jsonl`이다. 필수 필드는 `event_id`, `attempt_id`, `kind`, `ts`이며 writer의 `ALLOWED_FIELDS`만 기록한다. `time_to_preliminary_ms`, `time_to_evidence_ms`, `time_to_tasks_ms` 같은 비민감 정수 지표는 허용하되 키·쿠키·원문·모델 전송본문은 거절한다. 프로세스별 bounded 큐와 전용 스레드가 최대 64건 또는 5ms마다 한 번의 `O_APPEND` write와 `fsync`로 묶는다. 큐가 가득 차면 호출자 스레드가 동기 기록한다. 프로세스 간 `flock`으로 배치와 회전을 직렬화한다. API lifespan·worker 정상 종료·프로세스 종료 훅에서 대기 기록을 flush한다. 비정상 프로세스 종료나 전원 장애 시 마지막 최대 5ms의 대기 기록은 유실될 수 있으며, 디스크 쓰기 실패도 해당 배치의 기록을 잃을 수 있다. 실패는 프로세스 내 카운터와 `metrics/journal-writer-failure.json` 신호에 남는다. 다음 append는 동기 재시도로 회복을 확인하며 재시도도 실패하면 예외를 전파한다. `raise_on_background_error=True` 모드는 다음 append에서 즉시 예외를 전파한다. journal은 업무 재생이나 배정 실행에 사용하지 않는다.

로컬 Docker 기본 DB 비밀번호를 쓰는 경우 실행 명령에 `NEO4J_PASSWORD=development-only`를 제공해야 한다. 설정이 다른 배포에서는 해당 환경의 비밀번호를 제공한다.

T22 장애 시험에서 인증 전 Neo4j 중단 시 tenant를 확정할 수 없어 API 경계 journal은 `validity=undetermined`와 tenant 미지정으로 수신·실패를 보존한다. 독립 수집의 미확정 표본으로 드러내며 tenant별 성공 분모에 추정 편입하지 않는다.
