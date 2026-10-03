# 실행 관찰 API (T17-B)

모든 경로는 인증된 세션과 요청별 `can_view_request` 검사를 적용한다. 요청 식별이 없거나 요청 접근이 불가한 경우 404를 돌려 존재 여부를 노출하지 않는다. 원문 링크/본문은 `can_read_source`가 참일 때에만 제공한다. 모든 응답은 `request_id`, `run_id`, `step_id`, `review_id`, `config_version` 중 해당 범위의 공통 식별자를 포함한다.

## Flow

`GET /api/observe/runs/{run_id}/flow`는 `RunStep`의 저장 상태, 시작/종료/소요시간, 주체, attempt, 버전, 입력·출력 요약과 실제 `predecessor_ids` 및 `parent_step_id` 연결을 반환한다. 단계가 같은 predecessor를 가리키면 병렬 분기는 엣지로 표현된다. pending Review는 생성시각부터 결정 전까지 `waiting_human` 노드로 표현된다. `nodes`는 predecessor/parent 연결을 따르는 위상 순서이며 같은 단계 후보는 시작 시각, 그다음 ID 순이다(저장 순서·`collect` 순서에 의존하지 않는다). 선행 정보가 없는 단계는 시작 순서대로 `kind: sequence` 엣지로 이어지고, Review 노드(`name: 사람 검토`)는 마지막 단계에서 `kind: review` 엣지로 이어진다. 프런트는 이 순서와 엣지로 Flow를 그리고(`obs-edges` 목록, 각 노드의 '선행' 표시) 재생 도달 여부는 배열 위치가 아니라 노드 ID로 판단한다. `/observatory`는 `request_id`·`run_id` 쿼리를 모두 받으며 `run_id`만 있으면 flow 응답의 `request_id`로 요청을 맞춘다. 모니터링의 실패 Trace 링크는 `/observatory?request_id=…&run_id=…`이며 요청·실행 없이 시도 ID만 있는 실패는 링크 없이 시도 ID만 표시한다.

## Topology

`GET /api/observe/requests/{request_id}/topology?kind=business|service`의 business 형태는 저장된 `HAS_TASK`, `ASSIGNED_TO {role}`, `PRECEDES`만 반환한다. T11이 관계를 생성하기 전에는 빈 그래프가 유효 응답이다. service 형태는 요청 실행의 `RunStep.kind/name/actor/status/error_class`를 묶어 서비스별 호출 및 오류 수를 제공한다.

## Trace 상세

`GET /api/observe/steps/{step_id}`는 단계 원시 속성, 식별자, 시각, 소요, 요약, 주체, attempt 및 버전을 반환한다. 저장된 단계에 실제로 존재하는 정책/모델/스키마 버전만 반환하며 숨겨진 사고 과정은 제공하지 않는다. 원문은 이 API의 일반 요약에서 제외하고 `source_links` 필드를 원문 권한으로 제한한다.

## Playback

`GET /api/observe/runs/{run_id}/playback`은 저장된 단계 시작/종료 및 검토 대기 시작/결정 이벤트를 시간순 반환하고 live 실행 여부와 최종 실행 상태를 포함한다. 이벤트 시각 간 대기시간을 압축 표시해도 `duration_ms`에 실제 시간을 제공한다. 이 엔드포인트는 읽기 전용이며 rerun 경로를 제공하지 않는다.

현재 저장소 상태에서는 T11 업무 관계, ReviewDecision 세부 수정값·검토자, 단계별 근거 링크의 영속 연결이 아직 만들어지지 않는다. 해당 정보는 합성하지 않으며 생성 경로가 구현된 뒤 저장 사실만 반환한다.
