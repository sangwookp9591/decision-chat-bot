# 규칙 검증 및 효과 API (T33/T35)

`POST /api/learning/rules/{rule_id}/versions/{v}/validate`는 `rule_admin`이 기간(`from` 포함, `to` 제외), 요청 ID `scope_filter`, 선택적 `max_calls`를 지정한다. 활성 Config의 저장된 모델 반환값에 기준 규칙과 후보 규칙을 각각 적용한다. `ReviewDecision.action`이 `approve` 또는 `approve_with_changes`인 판단만 정답 표본으로 센다. 정답은 원 Judgment 분류에 해당 결정의 `Correction.corrected_value`를 덮어쓴 값이다. 두 규칙 결과가 정답과 다른 판단 수를 `human_correction_needed_base/candidate`로 저장한다.

`GET /api/learning/validations/{id}`는 단일 tenant 내 ValidationRun을 조회하고, `GET /api/learning/rules/{rule_id}/versions/{v}/validations`는 해당 RuleVersion에 연결된 결과를 최신순으로 반환한다. 두 조회는 `rule_admin`, `operator`, `reviewer`가 사용할 수 있다. 시각과 기간 등 Neo4j temporal 값은 ISO 8601 문자열로 직렬화한다. 학습 화면은 이 조회 결과로 검증 카드를 복원하므로 새로고침 후에도 유지된다. 검증 실행(POST)·단건 조회·목록 조회는 같은 DTO를 반환한다(`validation_dto`): 저장 시 JSON 문자열로 둔 `changes_by_value`(객체, 키는 `<필드>:<값>`)·`usage`(객체)·`failures`(목록)는 풀어서 반환하고, `failure_count`(정수)를 추가하며, 저장 속성 `from_at`/`to_at`은 응답 필드 `from`/`to`로도 제공한다(`from_at`/`to_at`은 호환을 위해 유지). 화면은 변경 수를 '담당 조직 · 주관 → 현업 8건'처럼 표시한다.

새 섀도 검증은 `val_<uuid>` ValidationRun과 별도 `run_shadow_<uuid>` Run을 만들고 `(ValidationRun)-[:HAS_SHADOW_RUN]->(Run)`으로 연결한다. 검증 API의 `id`는 ValidationRun ID이며 `run_id`는 섀도 Run ID다. 기존 저장 데이터의 ID는 변경하지 않는다.

후보의 `effect=context`가 요청 조직 범위에 해당하면 보관된 InputRevision/EvidenceSpan에서 state를 재구성해 `operating_guidance`를 넣고 Decision AI를 재호출한다. 클라이언트는 `AI_MODE` 설정을 따른다. 호출 상한은 Config의 `learning.shadow_max_calls`(기본 20)와 요청의 `max_calls` 중 작은 값이다. 실제 호출 수, token usage, 판단별 실패를 ValidationRun에 남긴다. 상한 초과나 호출 실패 시 검증 상태는 `failed`다.

검증 시작과 저장 직전에 tenant의 Task, Assignment, Review, Event, Request, 정식 Judgment 전체 속성을 카운트와 SHA-256으로 비교한다. 이 값에는 `Request.active_run_id`가 포함된다. 차이가 있으면 `side_effects=1`, `status=failed`다. 섀도 Run/ValidationRun과 journal만 새로 쓰며 SLO와 사용자 이벤트에 넣지 않는다. `mark-validated`는 완료 상태와 `side_effects=0`을 함께 요구한다.

`GET /api/learning/rules/{rule_id}/effects?days=7`은 해당 규칙의 첫 게시 Config 시각을 기준으로 양쪽 `days` 길이의 실제 Run을 비교한다(`days`는 1~90). 게시 후 같은 창의 `APPLIED` 결과로 `used`, `out_of_scope` 집단을 나눈다. 응답에는 기간 경계, 표본 수, 분류 변경률, Correction 발생률, Review 전환율, 실패율, Run 시작에서 첫 Judgment 커밋까지의 지연 p50/p95와 지연 표본 수를 각각 표시한다. 한 Run의 Correction/Review/APPLIED가 여러 개여도 각 비율에는 한 번만 센다. 섀도 Run은 제외한다.

효과 판정은 전·후 창 중 작은 표본 수가 Config `learning.min_effect_sample`(기본 20) 미만이면 `insufficient_sample`이다. 그 밖에는 Correction 발생률과 실패율을 비교한다. 어느 하나라도 상승하면 `worse`, 둘 다 하락하면 `improved`, 하나만 하락하고 다른 하나가 그대로면 `partial`, 둘 다 그대로면 `no_change`다. 지연과 검토 전환은 해석용 지표로 제공하며 이 판정에는 사용하지 않는다. 이 판정은 관찰 관계이며 인과 효과를 보장하지 않는다.

## 효과 관찰의 사람 정답 표본 (FIX-LEARN)

`before_after.before/after`, `groups.used/out_of_scope` 모두 `labeled_count`를 반환한다. 정답 표본은 해당 production 실행에 사람의 `ReviewDecision.action`이 `approve` 또는 `approve_with_changes`인 결정이 하나 이상 있는 실행이며, 같은 실행의 여러 결정·여러 Correction은 1건으로 센다. 수정만 존재하거나 미승인·기각·대기 상태인 실행과 shadow 실행은 정답 표본에 포함하지 않는다. 정의 식별자는 `labeled_definition=approved_human_review_per_run`이다.

효과 판정은 게시 전·후의 실행 표본 및 정답 표본 모두 Dynamic Config `min_effect_sample` 이상일 때만 확정한다. 기준 미달은 `insufficient_sample`을 반환하며 화면은 cohort별 정답 수와 정의, 정답 부족 시 **미확정**을 표시한다. 기존 관찰률·SLO 분모는 유지한다.
