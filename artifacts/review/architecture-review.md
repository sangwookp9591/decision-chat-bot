# 아키텍처 점검 보고서 (P1)

- 점검일: 2026-10-04 · 대상 커밋: `0da8b1e` · 방식: 읽기 전용 코드·문서 정적 검토(실행 재현 없음)
- 범위: `backend/jevtriage/**`(약 8.7천 줄), `frontend/src/**`, 기준 문서 PRD·TASK·docs/spec·docs/architecture(EXECUTION_CONTRACT·IMPLEMENTATION·DATA_MODEL·AUTH·EVENTS·WORKER)·docs/operations·GATE_REPORT
- 제외: GATE_REPORT에 이미 기록된 외부 요건(G10·G12·G13)과 알려진 제한(백업 범위, 마스킹 미구현, npm 감사 경고)은 다시 적지 않았다.
- 표기: 재현하지 않고 코드 경로만으로 판단한 항목은 근거에 "코드 경로 근거"로 적었다. 확신이 낮은 부분은 **불확실**로 표시했다.

## 요약

트랜잭션 핵심 경로는 계약에 맞게 구현돼 있다. worker 커밋(`JobContext.commit`)은 Request → Run → Job 순서로 잠그고 소유권과 활성 실행을 같은 트랜잭션에서 검증한다. 검토 승인과 배정, 감사, 이벤트, 멱등 결과도 한 `write_tx`에 들어간다. 다만 이 불변 조건은 **관례로만 지켜진다.** `write_tx(tenant_id, …)`는 tenant를 강제하지 않고, `set_active_run` 같은 안전 도우미를 우회하는 원시 Cypher 쓰기 경로가 여럿 있으며, 권한 판정과 원문 차단은 엔드포인트마다 따로 구현돼 있다. 이 구조에서 실제 권한 결함이 두 건 나왔다. 하나는 검토자 조직 fallback 때문에 tenant 안의 모든 검토자·팀 담당자가 검토를 승인할 수 있는 문제이고, 다른 하나는 요청 상세 API가 원문을 `can_read_source` 없이 반환하는 문제다. SSE 재연결 계약 불일치(재연결 시 400)도 확인했다. 성능 면에서는 색인이 없는 라벨(Session·Judgment·ModelOutput·Draft 등), 라벨 없는 MATCH, 무제한 목록, 이벤트 루프를 막는 fsync가 데이터 증가 시 주요 위험이다.

## 핵심 위험 목록 (20건, 관점별)

### (1) 모듈 경계·의존 방향

**R1. [심각도 중간] 모듈 순환 의존과 지연 import로 감춘 계층 역전**
- 위치: `judgment/service.py:15,166`, `learning/shadow.py:15-17`, `review/service.py:16-18`, `policy/service.py:35`, `journal/watchdog.py:15-17`, `monitoring/aggregates.py:14`
- 문제: judgment↔learning, judgment↔review, policy→learning→judgment→policy, journal↔monitoring 순환이 있다. 일부는 함수 안 지연 import로 import 오류만 피한다. 판단 저장 트랜잭션(judgment)이 배정 서비스(review)를 직접 호출하고, 정책(policy)이 학습 규칙 검증(learning.apply)에 의존한다.
- 근거: `judgment/service.py:166` `from jevtriage.review.service import auto_assign_after_judgment_in_tx`(함수 내부), `review/service.py:16` `from jevtriage.judgment.eligibility import evaluate_auto_assign`, `monitoring/aggregates.py:14` `from jevtriage.journal.collector import connect`와 `journal/watchdog.py:15` `from jevtriage.monitoring.aggregates import …`.
- 제안 수정: (a) `judgment.eligibility`·`judgment.questions`의 상수와 순수 함수, `learning.apply.validate_rule`을 의존 없는 `domain/`(예: `domain/eligibility.py`, `domain/rules.py`)으로 옮긴다. (b) 배정은 `assignment` 서비스 하나로 분리해 judgment와 review가 모두 그쪽에 의존하게 한다. (c) collector의 SQLite 스키마와 `connect`를 `journal/metrics_store.py`로 분리해 monitoring과 watchdog이 같은 하위 모듈을 공유하게 한다. (d) `import-linter` 계약(api→service→store→db, domain은 단말)을 CI에 넣는다.
- 예상 규모: M

**R2. [심각도 중간] 모듈 간 사설 함수 직접 호출과 api 계층의 DB 직접 접근**
- 위치: `auth/router.py:6,32-37,71-78,87-95`, `learning/candidates_api.py:16`(`_json`), `monitoring/slo.py:7`(`_time`), `graph/query.py:23`(`_decode`), `review/api.py:79-84`, `jobs/worker.py:17`(`lock_node_in_tx` 직접 사용)
- 문제: router가 `get_driver().session()`으로 Cypher를 직접 실행하고(auth), api 모듈이 `read_tx`로 질의를 인라인한다(review). 다른 모듈의 `_` 접두 함수도 import한다. IMPLEMENTATION.md §2는 "다른 모듈의 공개 함수 시그니처"를 기준으로 소유권을 나누는데, 사설 함수 의존은 이 경계를 무너뜨린다.
- 근거: `auth/router.py:6` `_token_hash`를 import하고, `auth/router.py:73-77`에서 `MATCH (s:Session {token_hash:$hash}) DETACH DELETE s`를 직접 실행한다. `review/api.py:80` `MATCH (j:Judgment …) WHERE j.run_id IN $runs`.
- 제안 수정: `auth/store.py`(세션·사용자·로그인 시도)와 `review/store.py`에 질의를 모은다. 공용 직렬화 도우미(`_json`·`_decode`·`_time`)는 `domain/serialize.py`의 공개 함수로 승격한다. ruff `PLC2701`(private import)을 활성화한다.
- 예상 규모: S

### (2) 트랜잭션·잠금 경계와 실행 계약 불변 조건

**R3. [심각도 높음] 검토자 조직 fallback(`"검토자"`) 때문에 tenant 안의 모든 reviewer/team_member가 검토를 승인할 수 있음**
- 위치: `review/service.py:34-37,262-267`, `review/api.py:32-37`, `auth/core.py:156-157`, 생성 지점 `judgment/store.py:145`, `review/service.py:495`
- 문제: 담당 조직이 미정이거나 자동 배정이 보류되면 Review의 `required_reviewer_org`가 `"검토자"`로 저장된다. `required_reviewer_org()`는 이 값을 **호출자 자신의 첫 조직**으로 바꾸고, 그 조직을 요청 메타 `org_ids`에 합친 뒤 `can_review`를 검사한다. 이 때문에 `can_view_request`의 조직 교집합 검사와 `reviewer_org in principal.org_ids` 검사가 항상 참이 된다. 결과적으로 같은 tenant의 reviewer 또는 team_member는 요청 조직과 상관없이 해당 검토를 보고 승인할 수 있고, 승인은 곧 배정 트랜잭션으로 이어진다. 또한 `can_review`가 `team_member`를 포함하므로 AUTH.md("team_member: 배정 조직 업무 조회·허용 상태 변경")와 다르게 팀 담당자도 검토 결정 권한을 갖는다.
- 근거: 코드 경로 근거. `review/service.py:35-36` `if value == "검토자": return next(iter(org_ids), "")`, `review/service.py:265` `meta["org_ids"] = list(set(meta.get("org_ids") or []) | {reviewer_org})`, `auth/core.py:157` `{"reviewer", "team_member"}.intersection(principal.roles)`. GATE G11의 56건 교차 호출 시험은 다른 tenant·조직 직접 호출을 다뤘고, 같은 tenant 안의 `"검토자"` fallback 경로는 포함 여부가 확인되지 않는다(**불확실**).
- 제안 수정: (a) `"검토자"`를 호출자 조직으로 바꾸지 말고, 정책에 정의한 검토 담당 조직(예: tenant 기본 검토 조직)이나 요청자 조직으로 생성 시점에 확정해 저장한다. (b) 권한 판정에서 요청 메타를 변조하지 말고 `can_view_request(principal, request) and required_org in principal.org_ids`로 분리한다. (c) `can_review`에서 `team_member`를 빼고 AUTH.md와 맞춘다. (d) 같은 tenant·다른 조직 reviewer와 team_member의 승인 403을 회귀 시험에 추가한다.
- 예상 규모: S

**R4. [심각도 중간] 활성 실행 포인터와 잠금 도우미를 우회하는 원시 쓰기 경로**
- 위치: `ingest/store.py:172-181`(`_create_run_job`), `ingest/service.py:97-101`(`reanalyze`), `db/requests.py:46-64`(`set_active_run`, 제품 코드 미사용·테스트만 사용), `tasks/service.py:20`, `judgment/service.py:169-174`
- 문제: DATA_MODEL은 `db.requests.set_active_run`/`assert_active_run_in_tx`를 활성 포인터 변경의 공개 경계로 정의한다. 하지만 실제 신규·재분석 실행은 `SET r.active_run_id=$run_id`를 직접 실행하고, 이전 포인터 기대값·revision·shadow 여부를 검증하는 도우미를 쓰지 않는다. `tasks/service.py:20`도 `lock_node_in_tx`(LOCK_ORDER에 Task 없음) 대신 원시 `SET t._lock`을 쓴다. `reanalyze` API의 열람 권한 검사(`ingest/api.py:166`)는 쓰기 트랜잭션 **밖에서** 수행한다. 현재 각 경로가 Request 잠금을 따로 잡고 있어 즉시 결함은 아니지만, "검증 후 쓰기" 불변 조건이 도우미가 아니라 호출부 관례에만 의존한다.
- 근거: `grep set_active_run` 결과, 제품 코드의 호출부는 0건이다(테스트 2개만). `ingest/store.py:175` `"SET r.active_run_id=$run_id, "`.
- 제안 수정: `db.requests`에 `start_run_in_tx(tx, tenant, request_id, revision_id, kind, expected_active_run_id)`를 만들어 Run·Job 생성, 포인터 갱신, shadow 거절을 한곳에서 처리하고 ingest 두 경로를 이 함수로 바꾼다. `LOCK_ORDER`에 Task를 추가하거나 Task 전용 잠금 도우미를 둔다. 권한 재검사는 `write_tx` 안 Request 잠금 직후로 옮긴다. 원시 `active_run_id` SET을 금지하는 grep 시험을 추가한다.
- 예상 규모: M

**R5. [심각도 중간] 실행 고정 Config 결정과 자동 배정 재검증이 세 곳 이상에 중복되고 키 이름도 다름**
- 위치: `judgment/handler.py:8-29`, `judgment/service.py:19-76`(경로 2개), `jobs/worker.py:253-260`, `review/service.py:117-175`, `judgment/store.py:52`
- 문제: Run의 Config 버전 고정이 handler(`created_at <= started_at` 기준), service `_fixed_policy`(활성 snapshot 기준과 이미 고정된 값 기준), worker `_begin_attempt`(속성 fallback)에 나뉘어 있다. 자동 배정 조건도 판단 시점(`judgment/service.py:156` 메모리 값)과 배정 시점(`review/service.py:117-175` 저장 값 재조회)에 따로 구현돼 있다. 배정 시점에는 `assign_in_tx`의 `policy` 인자(`review/service.py:102,482`)를 무시하고 `Judgment.versions["config_version"]`으로 다시 읽는다. Run은 `config`, Judgment는 `config_version` 키를 쓰므로 한쪽 이름만 바꿔도 조용히 `DEFAULT_CONFIG`로 떨어질 수 있다(`if config_version:`은 0도 거짓으로 처리한다).
- 근거: `review/service.py:131-141` `config_version = versions.get("config_version") … else: policy = DEFAULT_CONFIG`.
- 제안 수정: `policy.service.pin_config_for_run_in_tx(tx, tenant, run_id)` 하나로 고정 로직을 모으고 Run 생성 트랜잭션(`start_run_in_tx`, R4)에서 호출한다. 자동 배정 조건은 `domain.eligibility.evaluate(snapshot)` 하나만 쓰고, 판단 시점 결과를 Judgment에 저장한 뒤 배정 시점에는 같은 함수로 저장 값만 재평가한다. 사용하지 않는 `policy` 인자는 제거한다. 버전 키 이름은 `config_version` 하나로 통일한다.
- 예상 규모: M

**R6. [심각도 중간] 조건부 가능 본업무의 시작 차단이 Task 상태 전이에서 강제되지 않음**
- 위치: `review/service.py:206-211`(생성 시 `막힘` 판정), `tasks/service.py:16,29-35`(전이 검증)
- 문제: 배정 시 `unresolved_feasibility and not confirmation_task` 또는 초안 `status == "undetermined"`이면 Task를 `막힘`으로 만들지만, 그 원인을 `reason`이나 선행 관계로 저장하지 않는다. 전이 검증은 `task.reason`과 선행 업무 완료 여부만 보므로, 선행 관계가 없는 이런 본업무는 팀 담당자가 `막힘 → 진행`으로 바로 바꿀 수 있다. EXECUTION_CONTRACT §1("본업무의 시작 차단 조건을 유지")과 어긋난다.
- 근거: 코드 경로 근거. `tasks/service.py:34` `if task.get('reason') or any(s not in (None,'완료','completed') …)`. 생성 시 `reason=draft.get("reason")`(`review/service.py:225`)이며 feasibility 차단 사유는 저장되지 않는다. catalog 분해가 확인 업무를 항상 선행으로 연결하는지는 확인하지 못했다(**불확실**).
- 제안 수정: Task에 `block_reasons`(예: `feasibility_unresolved`, `undetermined_draft`)를 저장하고, 해제는 별도 명령(확인 업무 완료 또는 검토자 해제와 감사)으로만 하게 한다. 전이 검증은 `block_reasons`가 비어 있을 때만 `진행`을 허용한다.
- 예상 규모: S

### (3) 데이터 모델·제약·질의 성능

**R7. [심각도 높음] 핵심 조회 라벨에 색인과 유일 제약이 없음**
- 위치: `db/schema.py:7-12,35-58`
- 문제: `LABELS`와 색인 목록에 `Session`, `User`, `Org`, `Judgment`, `Draft`, `DraftTask`, `RuleSeries`, `Tenant`가 없다. 또 `ModelOutput.run_id`, `EvidenceSpan.revision_id`, `RunStep.run_id`, `Event.request_id`, `ConfigVersion(tenant_id, version)` 색인도 없다. 그 결과 (a) 모든 인증 요청의 `MATCH (s:Session {token_hash})`(`auth/core.py:112`)가 Session 라벨 전체를 스캔하고 만료 세션은 삭제되지 않으며, (b) 로그인 `MATCH (u:User {email})`도 전체 스캔이고 email 유일 제약이 없어 두 tenant에 같은 email이 있으면 `LIMIT 1`이 임의 계정을 고른다(`auth/core.py:66-72`). (c) 검토·배정·Trace의 `MATCH (o:ModelOutput {tenant_id, run_id})`, `(:Judgment {run_id})`, `(:Draft {run_id, draft_version})`는 라벨 스캔이다.
- 근거: `db/schema.py:47-54`의 색인은 6개(Request·Run·Job·Event·Review·Task)뿐이다. `grep -E "\(\w*:Session|:User|:Judgment"`로 사용처를 확인했다.
- 제안 수정: `session_token_hash_unique`(Session.token_hash), `user_email_unique`(User.email, 또는 tenant 선택 로그인이면 (tenant_id, email)), `judgment_tenant_run`, `modeloutput_tenant_run`, `draft_tenant_run_version`, `drafttask_tenant_run`, `evidencespan_tenant_revision`, `runstep_tenant_run`, `event_tenant_request`, `configversion_tenant_version_unique`를 추가한다. Session에 TTL 정리 작업(만료 후 삭제)을 둔다. `EXPLAIN` 기반 회귀 시험(라벨 스캔 금지)을 주요 질의 10개에 적용한다.
- 예상 규모: S

**R8. [심각도 중간] 라벨 없는 MATCH와 tenant 조건 없는 그래프 질의**
- 위치: `graph/query.py:203`(`_induced_edges`), `graph/query.py:313`(`edge_props`), `graph/query.py` `trace`의 `(a {tenant_id:$t})` 확장 패턴
- 문제: `UNWIND $edges AS e MATCH (a {tenant_id:$t,id:e.source})-[r]->(b …)`는 라벨이 없어 색인을 쓸 수 없으므로 간선마다 AllNodesScan이 일어날 수 있다. `_induced_edges`의 `MATCH (a)-[r]->(b) WHERE elementId(a) IN $ids`에는 tenant 조건이 없다. 지금은 시드가 tenant로 제한돼 있어 안전하지만, 방어선이 호출 순서 하나뿐이다.
- 근거: 코드 인용과 같음. 실행 계획(EXPLAIN)은 확인하지 않았다(**불확실**: Neo4j 플래너가 시작 노드를 바꿔 완화할 수 있음).
- 제안 수정: `edge_props`는 `kind_of`로 알고 있는 라벨을 동적 라벨(`MATCH (a:$($kind) …)`, Neo4j 5.26 이상)이나 라벨별 UNWIND 묶음으로 지정한다. `_induced_edges`에는 `AND a.tenant_id=$t AND b.tenant_id=$t`를 추가한다. 그래프 API에 노드·간선 수 상한과 질의 timeout(`tx.run(..., timeout=)`)을 둔다.
- 예상 규모: S

**R9. [심각도 중간] 무제한 목록과 "LIMIT 후 권한 필터" 패턴**
- 위치: `tasks/store.py:9-30` + `tasks/api.py:25-39`, `review/store.py:53-61` + `review/api.py:95-96`
- 문제: 업무 목록은 tenant의 모든 Task를 OPTIONAL MATCH 두 번과 함께 한 번에 읽은 뒤 Python에서 권한과 필터를 적용한다. 페이지 처리도 상한도 없다. 검토 목록은 `LIMIT 100`을 **먼저** 적용한 뒤 Python에서 `_allowed`로 거른다. 그래서 다른 조직의 최신 검토 100건이 있으면 정당한 검토자의 큐가 비어 보인다(정합성 결함). 요청 목록(`ingest/service.py:247-268`)은 `scope_filter_cypher`를 Cypher에 넣는 올바른 패턴을 쓴다. 같은 정책을 모듈마다 다르게 적용하고 있는 것이다.
- 근거: `tasks/api.py:29` `rows=await list_tasks(principal.tenant_id,{})`, `review/store.py:59` `ORDER BY v.created_at DESC LIMIT $limit` 다음에 `review/api.py:96` `_allowed(principal, v, dict(row["q"]))`.
- 제안 수정: `auth`에 `scope_predicate(principal, var)`(Cypher 조각과 파라미터)를 공개 함수로 두고 tasks·reviews·learning 목록이 모두 DB 질의 안에서 권한·필터·`SKIP/LIMIT`을 적용하게 한다. 응답에 `next_cursor`를 넣는다.
- 예상 규모: M

**R10. [심각도 중간] Event·Idempotency·Session·journal·metrics의 보존과 삭제 경로가 없어 시간이 지날수록 질의 비용이 커짐**
- 위치: `events/router.py:168-175`(`bounds`), `events/router.py:241-248`(`snapshot`), `journal/writer.py:52-58`(archive 회전), `journal/watchdog.py:67`, `monitoring/aggregates.py:28-38`
- 문제: 제품 코드의 삭제 경로는 로그아웃 세션 삭제 하나뿐이다. 그런데 SSE 연결마다 `OPTIONAL MATCH (e:Event {tenant_id}) … min(e.created_at)`로 tenant의 모든 이벤트를 집계하고, snapshot은 색인이 없는 `Event.request_id`로 `max(e.seq)`를 구한다. watchdog은 10초마다 30일치 metrics 행 전체를 메모리로 읽어 burn rate를 계산한다(`events_between` → `fetchall`). journal archive 파일도 지워지지 않는다. 보존 정책 "확정"은 G13 외부 요건이지만, 이 항목은 **보존 값과 무관하게** 보존 기한 질의와 정리 구조가 코드에 없다는 구조 문제다.
- 근거: `grep -rn "DELETE" backend/jevtriage` 결과는 `auth/router.py:75` 1건이다.
- 제안 수정: (a) `bounds`는 `min`을 쓰지 말고 `Event(tenant_id, seq)` 색인으로 `ORDER BY e.seq LIMIT 1`을 조회하고, EventCounter에 `retained_from_seq`를 둔다. (b) `Event.request_id` 색인을 추가한다(R7). (c) 보존 기간을 설정값으로 받는 정리 프로세스(`python -m jevtriage.ops.retention`)를 만들어 Event·Idempotency·Session·journal archive(수집 완료 offset 이후)·metrics 원시 행을 정리한다. (d) watchdog은 시간 단위 사전 집계 테이블이나 최근 1시간 질의만 쓴다.
- 예상 규모: M

**R11. [심각도 중간] worker 발견 질의가 tenant 없이 Job 전체를 스캔함**
- 위치: `jobs/worker.py:199-210`
- 문제: `MATCH (j:Job) WHERE (size($tenants)=0 OR j.tenant_id IN $tenants) AND (j.status='pending' OR …) ORDER BY j.created_at`는 `job_tenant_status`(tenant_id, status) 복합 색인의 선두 속성을 쓰지 못한다. 완료된 Job은 계속 쌓이므로, worker 수 × 0.5초마다 전체 Job을 스캔하고 정렬한다. `read_tx("worker-discovery", …)`는 tenant 인자를 형식적으로만 넘긴다.
- 근거: 코드 인용과 같음. `db/schema.py:50` 색인 정의.
- 제안 수정: `Job.status` 단일 색인(또는 `(status, created_at)`)을 추가하고 질의를 `MATCH (j:Job) WHERE j.status IN ['pending','running'] …`으로 바꾼다. 완료 시 `status`를 `completed`/`failed`로 바꾸므로 대상 집합이 작게 유지된다. 운영에서는 tenant 목록이 정해지면 tenant별 UNION 질의로 복합 색인을 쓴다.
- 예상 규모: S

### (4) 보안 구조

**R12. [심각도 높음] 요청 상세 API가 원문 입력(`InputRevision.text`)을 `can_read_source` 확인 없이 반환함**
- 위치: `ingest/store.py:260-282`, `ingest/service.py:270-282`, `auth/core.py:150-151`
- 문제: `GET /api/requests/{id}`는 InputRevision 노드 속성 전체(채팅 원문 `text` 포함)와 Attachment 속성을 반환한다. `_public`은 `_lock`과 `path`만 제거한다. `can_view_request`는 operator에게 tenant 안 모든 요청을 허용하므로, `can_read_source=false`인 운영자도 모든 요청 원문을 읽을 수 있다. AUTH.md("운영자는 메타데이터를 볼 수 있어도 원문은 `can_read_source`가 별도로 참이어야 한다")를 위반한다. 같은 원문을 근거 span으로 보여 줄 때는 `review/api.py:51`, `judgment/api.py:61`, `observe/api.py:107`, `ingest/service.py:286`에서 각각 차단하므로 **원문 차단이 엔드포인트별로 흩어져** 생긴 누락이다. 프런트 검토 화면도 이 응답의 `revisions[].text`를 원문으로 표시한다(`frontend/src/pages/Review.tsx:12`).
- 근거: 코드 경로 근거(재현하지 않음). `judgment/store.py:23` `RETURN i.text AS text`로 InputRevision에 원문이 저장됨을 확인했다.
- 제안 수정: (a) 응답 직렬화를 화이트리스트 DTO(`RequestDetailOut`, `RevisionOut`)로 바꾸고 `text`는 `principal.can_read_source` 또는 요청자 본인일 때만 넣는다. (b) 원문 필드(`text`, `source_text`, 첨부 추출본)는 `domain.redact.source_fields(principal, obj)` 하나에서만 처리한다. (c) 원문 필드명 목록을 기준으로 모든 GET 응답을 검사하는 계약 시험(operator·no-source 계정)을 추가한다.
- 예상 규모: S

**R13. [심각도 높음] 로그인 실패 제한이 성공 경로를 막지 않고 시간 창도 없음**
- 위치: `auth/router.py:26-43`, `auth/core.py:23-42`
- 문제: 비밀번호 검증(`authenticate`)이 실패 카운터 확인보다 **먼저** 실행된다. 10회를 넘어도 실패 응답만 401에서 429로 바뀔 뿐, 맞는 비밀번호는 언제나 200으로 성공한다. 무차별 대입을 늦추지 못하고, 429/200 차이가 오히려 성공 판별 신호가 된다. `window_start`는 저장만 하고 쓰지 않으며, 카운터는 로그인에 성공해야만 초기화된다. 알 수 없는 계정은 실패마다 User 조회를 한 번 더 한다(색인 없음, R7).
- 근거: `auth/router.py:28` `account = await authenticate(...)` 다음에 `:38-40` `count = await increment_login_attempt(...)`, `if count > 10: raise 429`.
- 제안 수정: 로그인 시작 시 `(tenant|unknown, email)` 카운터와 `window_start`를 먼저 읽고, 창 안에서 임계값을 넘었으면 비밀번호 검증 없이 429를 반환한다. 창이 지나면 초기화한다. 추가로 IP별 상한도 둔다. 실패·잠금 응답 시간을 맞추고, 감사 이벤트를 남긴다.
- 예상 규모: S

**R14. [심각도 중간] tenant 격리와 권한 판정이 구조로 강제되지 않음(관례 의존)**
- 위치: `db/tx.py:14-27`, `auth/core.py:147-169`, `tasks/api.py:18-46`, `review/api.py:32-37`, `graph/api.py:13-30`, `events/router.py:203-214`
- 문제: `write_tx/read_tx(tenant_id, fn)`는 tenant_id가 비어 있지 않은지만 확인하고 세션이나 질의에 아무것도 강제하지 않는다. 모든 Cypher가 `tenant_id`를 수동으로 넣어야 한다(R8처럼 빠진 곳이 있다). 권한 판정도 `can_view_request`·`can_review`·`scope_filter_cypher`·tasks의 `_visible`과 team_member 추가 필터·graph의 `_ROLES`·SSE 필터로 각자 구현돼 있어 R3, R9, R12 같은 불일치가 생겼다. 예를 들어 tasks는 `shared_org_ids`가 있으면 `org_ids`를 **대체**하는데(`tasks/store.py:27`), `can_view_request`는 둘을 **합친다**(`auth/core.py:152`).
- 근거: 코드 인용과 같음.
- 제안 수정: (a) `TenantTx` 래퍼를 둔다. `tx.run(query, **p)`에서 `$tenant_id` 파라미터를 자동 주입하고, 테스트 모드에서는 질의 문자열에 `tenant_id`가 없으면 예외를 낸다. (b) 권한을 `auth/policy.py` 한 곳의 `Decision(principal, action, resource)` 함수로 통합하고, 목록용 Cypher 술어(R9)와 단건 판정이 같은 정의에서 나오게 한다. (c) AUTH.md 역할표를 표 기반 시험(역할 × 엔드포인트 × 같은/다른 조직)으로 자동화한다.
- 예상 규모: M

**R15. [심각도 중간] SSE 연결이 세션 폐기·만료 후에도 계속 스트리밍됨**
- 위치: `events/router.py:137-235`
- 문제: principal을 연결 시작 시 한 번만 확인한다. 이후 로그아웃(세션 삭제), 12시간 만료, 계정 비활성화, 역할·조직 변경이 일어나도 연결이 열려 있는 동안 이벤트(요청 ID·상태)를 계속 받는다. heartbeat 주기마다 하는 세션 재검증이 없다.
- 근거: `principal: Principal = Depends(get_principal)` 이후 루프에서 세션을 다시 조회하지 않는다.
- 제안 수정: 15초 heartbeat마다 `session_principal(token)`으로 재검증하고, 실패하면 `event: session-expired`를 보낸 뒤 닫는다. org/role이 바뀌면 principal을 교체한다. 연결 최대 수명(예: 세션 만료 시각)도 둔다.
- 예상 규모: S

### (5) 관측·운영 구조

**R16. [심각도 중간] 동기 fsync journal 쓰기가 API·worker 이벤트 루프를 막고, journal 실패가 업무 API 실패로 번짐**
- 위치: `main.py:92-131`, `journal/writer.py:39-73`, `jobs/worker.py:62-80`, `ingest/api.py:193-217`
- 문제: API 요청마다 2~5회 `JournalWriter.append`(mkdir, 잠금 파일 open, flock, open, write, fsync, close)를 async 미들웨어와 핸들러에서 **동기로** 호출한다. 디스크 지연이 그대로 이벤트 루프 전체를 멈춰 SSE와 동시 요청 지연이 커진다. SSE만 `asyncio.to_thread`를 쓴다(`events/router.py:226`). 또한 `finally` 블록의 append가 `OSError`를 던지면 이미 만들어진 응답을 덮어써 500이 된다. 디스크가 가득 차면 업무 DB가 정상이어도 모든 API가 실패한다. "쓰기 실패 전파"는 DATA_MODEL의 의도지만, 관측 장애가 서비스 가용성 장애로 번지는 결합은 별도 결정이 필요하다.
- 근거: 코드 인용과 같음. GATE G12의 SSE p95 경계값(2,000ms) 원인과의 관련성은 측정하지 않았다(**불확실**).
- 제안 수정: (a) 프로세스별 단일 writer 스레드와 bounded queue를 둔다. 큐가 넘치거나 쓰기가 실패하면 실패 카운터와 heartbeat로 드러내고 요청은 계속 처리하는 정책을 문서로 정한다. (b) fsync는 배치 단위(예: 50ms 또는 N건)로 그룹 커밋한다. (c) 잠금 파일과 디렉터리는 한 번만 연다. (d) 미들웨어 `finally`의 실패는 응답을 덮지 않게 분리한다.
- 예상 규모: M

**R17. [심각도 낮음] 설정 관리가 분산되어 있고 문서와 코드가 어긋남**
- 위치: `config.py:8-21`, `events/router.py:19-21`, `journal/watchdog.py:100`, `judgment/jev_client.py:93-96`, `jobs/worker.py:441-448`, `docs/operations/CONFIG.md:16`, `main.py:38`
- 문제: SSE 상한·폴링 간격·webhook·mock 장애 설정은 `Settings`를 거치지 않고 import 시점의 `os.getenv`로 읽는다. 그래서 검증이 안 되고 테스트 중 바꿀 수 없다. CONFIG.md는 `API_REQUEST_TIMEOUT_SECONDS`를 "실제 코드가 읽는 설정"이라고 적었지만 코드에는 없다. worker 기본값은 CLI 인자에만 있다. `lifespan`이 만든 `app.state.neo4j_driver`는 `/api/ready`만 쓰고, 실제 요청은 `get_driver()`의 루프별 별도 드라이버를 쓴다. 그래서 readiness가 실제 풀 상태를 반영하지 않는다.
- 근거: `grep -rn "os.getenv"` 결과와 CONFIG.md:16.
- 제안 수정: 모든 설정을 `Settings`(하위 그룹 `sse`, `worker`, `watchdog`)로 옮기고 시작 시 한 번 검증해 로그로 남긴다. CONFIG.md 표는 `Settings.model_json_schema()`에서 생성한다. readiness는 `get_driver()`와 같은 드라이버를 쓰게 통일한다.
- 예상 규모: S

### (6) 프런트 구조

**R18. [심각도 높음] SSE 자동 재연결이 서버 계약과 충돌해 영구 단절되고, 서버 이벤트 종류와 구독 목록도 다름**
- 위치: `frontend/src/state/events.ts:22-35`, `backend/jevtriage/events/router.py:145-146`
- 문제: (a) 클라이언트는 항상 `?after=`로 연결한다. 이벤트를 하나라도 받은 뒤 네트워크가 끊기면 브라우저 EventSource가 자동 재연결하면서 `Last-Event-ID` 헤더를 붙인다. 서버는 둘 다 있으면 400("Use either Last-Event-ID or after")을 반환하고, 2xx가 아닌 응답에서 EventSource는 재시도를 멈춘다. 클라이언트 `onerror`에는 수동 재연결이 없어 `disconnected`로 끝난다. GATE G08 시험은 수동 `Last-Event-ID` 재개였을 가능성이 있다(**불확실**). (b) 클라이언트가 구독하는 이벤트(`request.updated`, `run.updated`, `run.started`, `run.completed`)는 서버가 발행하지 않는다. 서버가 발행하는 `judgment_saved`·`judgment_failed`·`review_decided`·`assignment_created`·`auto_assignment_deferred`·`task.transitioned`·`rule.*`는 이름 지정 리스너가 없어 전달되지 않는다. (c) `snapshot-required`가 오면 requestId가 없는 화면(정책 화면)은 복구 없이 끊긴다. 커서는 tenant 범위인데 sessionStorage 키는 tenant와 무관해서, 같은 탭에서 다른 tenant로 다시 로그인하면 `cursor_out_of_range`로 끊긴다.
- 근거: 코드 경로 근거(브라우저 재현은 하지 않음). EventSource 재연결 시 `Last-Event-ID`를 보내는 것은 WHATWG HTML 표준 동작이다.
- 제안 수정: (a) 서버는 둘 다 있으면 400 대신 `max(after, Last-Event-ID)`를 사용한다(또는 클라이언트가 재연결을 직접 관리하고 URL 커서만 쓴다). (b) 이벤트 kind 목록을 백엔드 `events/kinds.py` 상수로 두고, OpenAPI나 생성 스크립트로 프런트 `EventKind` 타입을 생성한다. 프런트는 kind를 사전 등록하지 말고 단일 `message` 이벤트에 `data.kind`를 싣는 방식도 검토한다. (c) 끊김 상태에서 지수 백오프로 재연결하고, `snapshot-required`이면 화면별 재조회 콜백을 호출한다. (d) 커서 키에 `tenant_id`와 `user_id`를 포함한다.
- 예상 규모: S

**R19. [심각도 중간] 세션 상태 공유가 없고 역할 기반 라우팅이 없으며 화면 코드 밀도가 높아 유지보수가 어려움**
- 위치: `frontend/src/state/session.ts:6-15`, `frontend/src/App.tsx:7`, `frontend/src/layout/AppShell.tsx:15-16`, `frontend/src/pages/Review.tsx`(13줄 안에 화면 전체)
- 문제: `useSession()`은 Context 없이 호출하는 곳마다 `/api/auth/me`를 따로 요청하고 상태를 따로 가진다(Shell과 AppShell에서 최소 2회). `SessionUser`에는 tenant·org·can_read_source가 없다. 메뉴와 라우트는 역할과 상관없이 8개를 모두 노출하고, 권한 없는 화면은 서버 403 메시지로만 처리한다. 역할 라벨은 서버 역할명과 다르다(`assignee` ↔ 서버 `team_member`, `policy_editor` 라벨 없음). Review·AppShell 등 주요 화면이 한 줄짜리 거대 컴포넌트로 작성돼 있어 상태·API·표시 분리와 리뷰가 어렵다. 오류 처리도 화면마다 다르다(`.catch(() => undefined)`로 무시 `pages/Main.tsx:50`, `setError`, `setNotice`).
- 근거: 코드 인용과 같음.
- 제안 수정: `SessionProvider`(Context)와 `RequireRole` 라우트 가드를 도입하고, 역할·라벨 표를 서버 역할 enum과 일치시킨다. 데이터 조회는 TanStack Query 같은 공용 캐시 계층으로 바꿔 로딩·오류·재시도·SSE 무효화를 한 방식으로 처리한다. Review·Main·Learning을 컨테이너와 표시 컴포넌트로 나누고 prettier/eslint `max-len`을 적용한다.
- 예상 규모: M

### (7) 기술 부채·확장성

**R20. [심각도 중간] 다중 인스턴스 동작이 프로세스 로컬 상태에 묶여 있음**
- 위치: `events/router.py:22-27,155-157`(전역 `_connections`·`_hubs`), `jobs/worker.py:199-210`, `journal/collector.py:107-115`, `journal/writer.py:36-58`
- 문제: (a) SSE 연결 상한과 tenant 폴러가 프로세스마다 따로 있어 API N개면 tenant당 폴링 N배, 상한도 N×100이 된다(EVENTS.md는 배포 계층 위임을 인정함). 여러 호스트에서는 `DATA_DIR` 로컬 journal, metrics, 파일 저장소를 공유할 수 없어 collector와 watchdog이 호스트별로 갈라진다. (b) `_connections`는 `StreamingResponse` 본문 생성기가 시작돼야 `finally`에서 감소한다. 응답 시작 전에 클라이언트가 끊기면 카운터가 새어 결국 모든 연결이 503이 될 수 있다(**불확실**: Starlette가 시작되지 않은 생성기를 처리하는 방식에 따라 다름). (c) worker는 동시성만큼 각자 0.5초 간격 발견 질의를 실행하며 경쟁적 lease에 의존한다(정합성은 generation으로 보장되지만 확장 시 DB 부하가 선형으로 는다). (d) `reanalyze`가 활성 실행을 바꿔도 이전 Job은 취소되지 않아 Jev 호출이 끝날 때까지 낭비된다(커밋은 StaleRun으로 막힘).
- 근거: 코드 인용과 같음.
- 제안 수정: (a) 이벤트 분배를 Neo4j 폴링에서 외부 pub/sub(예: Redis Streams, NATS) 또는 DB 폴러 1개 + 내부 브로드캐스트로 분리하고, 연결 상한은 공유 저장소 카운터나 ingress에서 관리한다. (b) 연결 수 증감을 생성기 안으로 옮기거나 `BackgroundTask`로 감소를 보장한다. (c) worker 발견은 R11 색인 + `SKIP LOCKED` 유사 패턴(조건부 claim 한 질의)으로 바꾸고 polling backoff를 둔다. (d) 활성 포인터가 바뀌면 이전 Job에 `cancel_requested`를 표시하고 heartbeat에서 확인해 조기 종료한다. (e) 다중 호스트 배포 전에 journal·파일 저장소의 원격화 설계(T26 범위)를 이 항목과 함께 결정한다.
- 예상 규모: L

## 낮은 우선순위 메모 (목록 외)

- DATA_MODEL.md의 `save_step` 예시는 `verify_owner_in_tx`(Job)를 `assert_active_run_in_tx`(Request)보다 먼저 호출해 문서의 잠금 순서와 반대다. 구현(`jobs/worker.py:87-96`)은 올바르므로 문서 예시만 고치면 된다.
- `jobs/worker.py:290-337` `_finish`의 내부 `op`가 뒤에서 정의하는 `update_request`를 클로저로 참조한다. 지금은 동작하지만 순서에 의존하므로 인자로 넘기는 편이 안전하다.
- `jobs/worker.py:244-250`의 deadline 경과 계산은 Python 시각을 쓴다. 계약("lease 비교는 DB 기준 시각")은 lease에 한정되지만, deadline도 DB 시각으로 맞추면 호스트 시계 차이에 강해진다.
- `monitoring/aggregates.py:35`는 tenant 필터에 `tenant_id IS NULL` 행을 포함한다. 인증 전 API 경계 이벤트가 모든 tenant 운영자에게 보이므로, 다른 tenant 트래픽 규모가 간접 노출된다. 설계 의도(미확정 표본 공개)와 tenant 경계 사이의 결정이 필요하다.

## 구조적으로 우선 개선할 3가지

1. **권한·원문 공개를 단일 정책 계층으로 통합한다** (R3, R9, R12, R14, R15). `auth/policy.py`에 `can(principal, action, resource)`와 목록용 Cypher 술어를 한 정의에서 만들고, 응답은 화이트리스트 DTO와 `redact_source(principal, …)`로만 직렬화한다. 이 계층 하나로 확인된 두 권한 결함(검토자 fallback, 요청 원문 노출)과 목록 정합성 문제를 함께 닫고, 역할 × 엔드포인트 × 조직 표 기반 계약 시험으로 회귀를 막는다. 규모 M.
2. **쓰기 불변 조건을 도우미 API로만 통과하게 한다** (R4, R5, R6, R14). `TenantTx`(tenant 자동 주입·검사), `start_run_in_tx`(Run·Job·활성 포인터·Config 고정 한 번에), `assignment` 서비스(자동·검토 배정 단일 경로, 단일 eligibility 함수), Task `block_reasons`를 도입한다. 원시 `SET …active_run_id`·`_lock`·`status`를 금지하는 lint/grep 시험을 CI에 넣어, EXECUTION_CONTRACT를 관례가 아니라 구조로 강제한다. 규모 M.
3. **데이터 증가와 다중 프로세스를 전제로 저장·관측 경로를 정비한다** (R7, R8, R10, R11, R16, R18, R20). 누락된 색인과 유일 제약을 추가하고 라벨 스캔 금지 EXPLAIN 시험을 둔다. 보존 정리 프로세스를 만들고, journal은 비동기 그룹 커밋 writer로 바꾼다. SSE는 커서 계약(R18)을 먼저 고친 뒤 분배를 프로세스 밖으로 꺼낸다. 이 순서로 하면 공유 Neo4j 부하와 SSE 지연 위험을 운영 30일 관측(G13) 전에 줄일 수 있다. 규모 M–L.
