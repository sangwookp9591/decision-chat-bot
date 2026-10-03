# 수정 비교와 규칙 후보 API (T30/T31)

`learning.corrections`는 tenant 조건이 있는 읽기 트랜잭션으로 Correction과 연결된 ReviewDecision을 조회한다. 목록은 `field`, `request_id`, `from`, `to`를 받고, `/api/requests/{id}/corrections`는 Review 비교용 단건 결과를 제공한다. 검토자·규칙 관리자·운영자만 호출할 수 있으며 요청 조직 범위를 다시 확인한다. 원문 텍스트는 반환하지 않고 span ID만 제공하며 `can_read_source`가 없는 경우 단건 비교 응답에서 span ID를 숨긴다.

후보와 수정 기록 응답의 Neo4j 시각은 ISO 8601 문자열이다. 클라이언트는 Neo4j 내부 DateTime 객체 구조를 복원하지 않는다.

`POST /api/learning/candidates/generate`와 `python -m jevtriage.learning.candidates --tenant TENANT`는 저장된 Corrections를 `(field, ai_value, corrected_value)`로 묶는다. 판단 특징은 같은 요청·실행의 Judgment 분류와 실제 Noul ModelOutput 신호에서 수집한다. 각 수정 사례에서 공통으로 관측된 특징만 `scope.all`에 넣고, 분류는 `eq`, 신호는 실제 관측값이 0.5 이상이면 `gte 0.5`, 미만이면 `lte 0.5`라는 고정 구간 술어로 표현한다. 자유 텍스트는 범위 판단에 쓰지 않는다. 공통 특징이 없으면 빈 `all` 범위다.

동일 범위에서 해당 필드를 수정하지 않은 승인 결정이나 다른 값으로 수정한 승인 결정은 반례로 센다. 지지는 동일한 방향으로 바뀐 Correction이다. 기본 최소 지지 수는 3이며, 부족하면 `자료 부족`이다. 후보의 불확실성 필드에는 지지·반례 수, 최소 표본 기준 및 지지가 단일 요청 조직에 편중됐는지를 담는다. 이 구현은 효과나 정답률을 추론하지 않는다. 후보의 작성자는 `code:candidate@v1`이고 문장은 결정적 JSON 템플릿이다. 모델 생성은 호출하지 않는다.

`자료 부족` 후보를 승인하거나 이 승인 결정에서 규칙 버전을 만들 때는 각 요청 본문에 `acknowledge_insufficient: true`와 10자 이상의 사유를 넣어야 한다. 누락하면 422 `INSUFFICIENT_ACK_REQUIRED`다. 결정 노드에 확인 여부와 사유를 보존하고 응답 및 후보 상세에 `insufficient_approved`와 `insufficient_approval_label: "자료 부족 상태로 승인됨"`을 제공한다. 이 확인은 효과 입증을 의미하지 않는다.

사람은 `POST /api/learning/candidates`로 `field`, `proposed_action`, `scope`, `rationale`, `supporting_correction_ids`를 제출할 수 있다. 실제로 존재하고 접근 가능한 Correction만 연결한다. 후보 상세는 지지 Correction과 반례 ReviewDecision의 실제 관계를 반환한다. 후보는 제안 데이터이며 Config, 활성 규칙, 업무에 영향을 주지 않는다.

실행: `make up` 이후 `make test`로 전체 백엔드 단위·실제 Neo4j 통합 시험을 확인한다. 후보 생성 통합 시험은 3건 지지, 2건 자료 부족, 생성 재실행 멱등성과 Config 비변경을 검증한다.
