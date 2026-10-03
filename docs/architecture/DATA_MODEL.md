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

`python -m jevtriage.db.schema`는 일반 라벨의 `id` 유일 제약, `RuleCandidate`와 `RuleVersion`의 `(tenant_id, id)` 복합 유일 제약, `Assignment(tenant_id, request_id)`, `Task(assignment_id, draft_task_id)`, `Idempotency(tenant_id, scope, key)`, `EventCounter(tenant_id)` 유일 제약 및 요청·실행·Job·Event·검토·업무 조회 색인을 `IF NOT EXISTS`로 만든다. 이전 전역 `rulecandidate_id_unique`·`ruleversion_id_unique` 제약은 `DROP IF EXISTS`로 제거하고 tenant 복합 제약을 설치한다. 두 번 실행해도 같은 스키마가 유지된다. `RuleVersion.id`는 공개 식별자 `rule_id@version`이며 tenant 사이에 같은 값을 쓸 수 있다. AI가 결정적으로 만든 `RuleCandidate.id`도 tenant 사이에 같을 수 있다. 나머지 다중 tenant ID는 UUID 기반 또는 tenant를 포함한 전역 고유값이다. [Neo4j 5 공식 제약 문서](https://neo4j.com/docs/cypher-manual/5/constraints/create-constraints/)에서 복합 속성 유일 제약을 확인했고, Neo4j 5.26 Community에서 제약 생성과 같은 ID·다른 tenant 노드 2개 저장을 실행해 확인했다.

잠금 순서는 `Request → Run → Review → Assignment → Job`이며 같은 라벨에서는 ID 순서다. `lock_nodes_in_tx`가 잘못된 순서를 거절한다. 실제 쓰기 잠금은 해당 노드의 `_lock` 속성을 `randomUUID()`로 바꾸어 얻고 트랜잭션이 끝날 때까지 유지한다. EventCounter는 tenant별로 잠그고 seq 증가와 Event 생성이 같은 트랜잭션이므로 롤백 시 결번이 없다. Job은 소유권 검증과 결과 쓰기를 같은 트랜잭션에서 수행한다.

## 공개 함수와 경계

| 모듈 | 함수 | 사용 조건 |
| --- | --- | --- |
| `db.driver` | `get_driver`, `close_driver`, `create_driver` | 실행 루프별 async 드라이버; 앱 종료 시 close |
| `db.tx` | `write_tx(tenant_id, fn)`, `read_tx(tenant_id, fn)`, `db_now`, `db_now_in_tx` | callback은 async. 드라이버 관리형 재시도 때문에 callback 안에는 DB 동작만 넣고 외부 호출·파일 쓰기를 넣지 않는다 |
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

경로는 `DATA_DIR/journal/current.jsonl`, 회전 파일은 `archive-<uuid>.jsonl`이다. 허용 필드는 `event_id`, `attempt_id`, `request_id?`, `run_id?`, `kind`, `ts`, `status_code?`, `error_class?`, `duration_ms?`, `validity?`뿐이고 필수 필드는 앞의 두 ID·kind·ts다. 키·쿠키·원문·모델 전송본문은 거절한다. 프로세스 간 `flock`으로 회전과 append를 직렬화하고 한 번의 `O_APPEND` write 후 `fsync`한다. 회전은 설정된 `max_bytes` 기준이며 쓰기 실패는 예외와 프로세스 내 실패 카운터로 드러난다. journal은 업무 재생이나 배정 실행에 사용하지 않는다. 수집기·watchdog은 T18 담당이다.

로컬 Docker 기본 DB 비밀번호를 쓰는 경우 실행 명령에 `NEO4J_PASSWORD=development-only`를 제공해야 한다. 설정이 다른 배포에서는 해당 환경의 비밀번호를 제공한다.

T22 장애 시험에서 인증 전 Neo4j 중단 시 tenant를 확정할 수 없어 API 경계 journal은 `validity=undetermined`와 tenant 미지정으로 수신·실패를 보존한다. 독립 수집의 미확정 표본으로 드러내며 tenant별 성공 분모에 추정 편입하지 않는다.
