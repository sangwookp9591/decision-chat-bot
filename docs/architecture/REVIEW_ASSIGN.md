# 검토·배정·수정 기록 구현 (T11/T30)

2026-10-03 기준. `review.api`는 검토 목록·상세·결정 API를 제공한다. POST 결정은 세션의 `Principal`, 전역 CSRF 미들웨어, `Idempotency-Key`를 요구한다. 검토 대상은 요청 ID, 입력 revision, 실행 ID, 초안 버전, 검토 버전의 결합이며 오래된 대상은 최신 대상 정보를 포함한 409를 반환한다. 조직별 검토 권한은 `can_review`와 검토 책임 조직을 함께 검사한다. 다른 tenant의 ID는 404로 처리한다.

`decide`는 `Request → Review` 순서로 잠근 한 `write_tx`에서 최신 대상·권한·초안 필수 필드·tenant 조직·선행 순환을 재검증한다. `ReviewDecision`의 결정자·사유·시각·버전을 기록하고 수정 승인에서는 기존 Judgment/Draft를 그대로 두고 새 Draft 버전을 만든다. 분류와 초안 업무의 변경 항목별 `Correction`에는 원값·수정값·사유·근거 ID·수정자·시각·request/revision/run/Config 버전을 저장한다. 모델 반환값에 해당하는 분류 수정은 `CORRECTS`로 원 `ModelOutput`에 연결된다. 카탈로그가 작성한 초안 업무 필드는 대응하는 Jev `ModelOutput`이 없으므로 관계를 합성하지 않고 `RECORDED`와 원안·수정값을 보존한다. 단건 결정은 RuleCandidate·RuleVersion·ConfigVersion을 변경하지 않는다.

승인 시 같은 트랜잭션의 `assign_in_tx`가 요청당 Assignment 1개와 `(assignment_id,draft_task_id)`당 Task 1개를 생성한다. Request에서 Task로 `HAS_TASK`, Task에서 Org로 `ASSIGNED_TO {role}`를 만들고 실제 선행 작업에만 `PRECEDES`를 만든다. 선행 작업·초안 사유·미정 상태 또는 미해결 개발 가능성이 있는 본업무는 `막힘`으로 시작한다. 정보 요청은 `보완 필요`와 `needed_info` 목록을, 반려는 `반려` 상태를 저장한다. 결정·배정·감사·이벤트·멱등 결과는 함께 커밋한다.

worker 판단 저장 후 자동 배정 대상은 같은 `assign_in_tx`를 호출한다. 이는 worker 소유권과 활성 실행을 검증한 `ctx.commit` 내부다. 배정 서비스는 실행 고정 Config 버전, 최신 입력/실행, 근거 링크, 모든 Choice/Noul 신호, 위험·긴급·개발 가능성, 초안, 기존 배정을 다시 확인한다. 조건이 강화되거나 초안이 유효하지 않으면 최초 판단은 보존하고 새 검토 대상으로 전환한다. 이미 배정된 요청의 재분석은 기존 업무를 유지한다. 부트스트랩 정책은 자동 배정 off이며 안전 조건은 on 정책에서도 서버 코드로 강제한다.

FIX-R: 이미 Assignment가 있는 요청의 재분석 결과 저장 경로는 `auto_assign_after_judgment_in_tx`를 호출하지 않으며 Review를 만들지 않는다. 배정 전 재분석의 이전 pending Review는 판단 저장 트랜잭션에서 superseded로 닫는다. 과거 Review 결정은 `decide`의 대상 상태·최신 실행 검사로 409가 된다. Request 잠금과 활성 run·worker 소유권 검증은 기존 `ctx.commit`이 적용한다.

검증: `make up` 후 `backend/.venv/bin/pytest backend/tests/integration/test_review_assignment.py backend/tests/integration/test_policy_versions.py -q`에서 실제 Neo4j 통합 시험 18건 통과했다. 검토 결정 4종, 원안·Correction 관계, 과거 버전 409, 동시 승인 20개, 멱등 충돌, 권한·tenant·CSRF, 자동 배정 안전 재검증, 재분석 후 업무 불변을 포함한다. 마지막 전체 `make test`는 88건 통과·1건 실패·1건 건너뜀이다. 실패는 T08 worker 인계 시험의 예상 이벤트 목록이 실제 `run.step` 이벤트를 포함하지 않는 문제이며, 요청 검토 시험은 모두 통과했다.
