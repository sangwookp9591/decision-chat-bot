# 판단 저장 계약 (T09)

2026-10-03 기준. 판단은 실행(`Run`)마다 불변 원안으로 저장한다. 재분석은 새 `Run`과 `Judgment`를 만들고 기존 노드는 보존한다. 모든 노드는 `tenant_id`를 가지며 사용자 조회에는 요청 범위 권한을 확인한다.

## 저장 구조

- `(Run)-[:PRODUCED]->(Judgment)`와 `(Run)-[:PRODUCED]->(Draft)`를 같은 결과 트랜잭션에 생성한다.
- `Judgment` 속성은 `id`, `tenant_id`, `request_id`, `revision_id`, `run_id`, `ai_need`, `feasibility`, `urgency`, `lead_org`, `risk_confirmed`, `risks`(위험별 실제 Noul JSON), `summary`(본문·작성 주체 JSON), `author`, `versions`(model·qset·catalog·schema·config_version JSON), `mode`(`live` 또는 `mock`), `created_at`이다.
- 질문마다 `(ModelOutput)-[:OF_JUDGMENT]->(Judgment)`를 만든다. `ModelOutput`은 `id`, `tenant_id`, `question_id`, `type`, `value`, `confidence`(Choice/Score에만), `probabilities`(JSON, Choice/Score에만), `noul`(Noul에만), `legend`(Score에만, JSON), `model`, `run_id`를 가진다. 실제 `Jev 판단` RunStep에서 각 출력으로 `USED_OUTPUT` 관계를 만든다.
- `(ModelOutput)-[:CITES {prob}]->(EvidenceSpan)`는 근거 연결 결과의 `unit_id`가 같은 tenant·request·revision의 실제 `EvidenceSpan.id`와 일치할 때만 생성한다. 채팅은 `source='chat'`인 문장 단위 span으로 저장하며 파일 첨부 근거와 동일하게 연결한다. 조회 API는 출처 종류·위치·확률을 제공하고 `can_read_source` 권한이 있을 때만 원문을 제공한다.
- `(DraftTask)-[:IN_DRAFT]->(Draft)`를 만든다. `Draft`에는 `id`, `tenant_id`, `request_id`, `revision_id`, `draft_version`(초기 1), `run_id`, `created_at`이 있다. `DraftTask`에는 `id`(`{draft_id}_{draft_task_id}`), `draft_task_id`, `draft_version`, `title`, `method`, `lead_org`, `collab_orgs`(JSON), `deliverable`, `predecessors`(JSON), `status`(`draft` 또는 `undetermined`), `reason`, `author`, `tenant_id`, `request_id`, `run_id`가 있다. 정보 부족 초안도 필수 필드와 미정 사유를 보존한다.
- 자동 배정 조건을 충족하지 않으면 `Review`(`id`, `status:'pending'`, `request_id`, `revision_id`, `run_id`, `draft_version:1`, `review_version:1`, `reasons` JSON, `required_reviewer_org`, `tenant_id`, `created_at`)를 만들고 요청을 `검토 대기`로 표시한다. 조건을 충족하면 요청을 `auto_assign_eligible`로 표시하고 이벤트만 기록한다. T09는 배정 노드를 만들지 않는다.
- 판단·초안·검토·요청 상태·`Run.first_judgment_committed_at`·`judgment_saved` 이벤트는 `ctx.commit(affects_request=True)` 한 트랜잭션에서 쓴다. 인계된 worker나 비활성 실행은 커밋할 수 없다. `Run.versions_json`의 정책/Config 버전은 최초 실행에서 고정하고 인계 후 조회할 때 같은 버전의 정책을 사용한다.

## 재분석 저장 경계 (FIX-R)

- 결과 저장 시 `ctx.commit(affects_request=True)`가 Request를 잠그고 활성 실행 및 Job 소유권을 확인한 뒤, 같은 트랜잭션에서 `Request.assignment_id`와 실제 `Assignment` 노드를 확인한다.
- 배정이 있으면 새 `Judgment`·`Draft`·근거/모델 출력을 비교용으로 저장하고 `reanalysis.compared` 이벤트만 추가한다. 새 Review, 자동 배정, Request의 status·latest_judgment_id 변경은 하지 않는다. 기존 Assignment·Task도 건드리지 않는다.
- 배정 전 새 판단에서는 이전 실행의 pending Review를 `status='superseded'`, `reason='newer_run'`, `superseded_by=<new run_id>`로 닫는다. 새 실행이 검토 대상이면 pending Review를 하나 만들며, 자동 배정 대상이면 기존 자동 배정 경로가 안전 조건을 재검증한다. 이 전이는 판단 저장과 같은 트랜잭션이다.
- 검증은 실제 Neo4j, mock Jev, worker 1회 실행으로 `test_reanalysis_boundary.py`에서 수행했다. `make up` 후 `make test`: 백엔드 127 통과·1 건너뜀, 프런트 34 통과. mock 결과는 live 분류 품질의 증거가 아니다.

## 실행·검증

`make up` 후 `cd backend && .venv/bin/pytest tests/integration/test_judgment_service.py tests/unit/test_eligibility_t09.py`를 실행한다. 비민감 live 저장 결과의 ID와 mode는 `artifacts/validation/t09/live-smoke.json`에 기록했다. 그 증거는 한 건의 실제 호출·저장만 보이며 분류 품질이나 자동 배정 안전성 전체의 승인 증거는 아니다.

## 초안 버전 표시 (UX-5 / P6-01)

`GET /api/requests/{id}/judgment`의 `draft_tasks`는 **현재 초안 버전**의 업무만 담는다(같은 `draft_task_id`가 버전마다 반복되지 않는다). 현재 버전은 요청의 최신 Review가 `approved`이면 승인된 `draft_version`, 그 외에는 최신 `draft_version`이다. 추가 필드: `current_draft_version`, `draft_versions: [{draft_version, source('ai'|'reviewer'), created_by, created_at, tasks}]`. `source`는 v1이면 `ai`, 이후 버전은 검토자 수정 승인으로 만들어진 `reviewer`다. 원본 Draft·DraftTask는 수정하지 않고 보존한다. `draft_tasks`를 읽는 곳은 프런트 Main·Review뿐이며(WebMCP 도구·eval 러너는 이 API 필드를 사용하지 않는다) 필드 이름은 유지했다. Main은 현재 버전만 업무 분담에 표시하고 “원안과 비교” 펼침에 버전별 목록과 원안 대비 변경 항목을 보여 준다. 시험: `test_review_assignment.py::test_judgment_api_shows_only_current_draft_version`.
