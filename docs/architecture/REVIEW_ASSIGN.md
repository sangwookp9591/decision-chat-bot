# 검토·배정·수정 기록 구현 (T11/T30)

2026-10-03 기준. `review.api`는 검토 목록·상세·결정 API를 제공한다. POST 결정은 세션의 `Principal`, 전역 CSRF 미들웨어, `Idempotency-Key`를 요구한다. 검토 대상은 요청 ID, 입력 revision, 실행 ID, 초안 버전, 검토 버전의 결합이며 오래된 대상은 최신 대상 정보를 포함한 409를 반환한다. 조직별 검토 권한은 `can_review`와 검토 책임 조직을 함께 검사한다. 다른 tenant의 ID는 404로 처리한다.

`decide`는 `Request → Review` 순서로 잠근 한 `write_tx`에서 최신 대상·권한·초안 필수 필드·tenant 조직·선행 순환을 재검증한다. `ReviewDecision`의 결정자·사유·시각·버전을 기록하고 수정 승인에서는 기존 Judgment/Draft를 그대로 두고 새 Draft 버전을 만든다. 분류와 초안 업무의 변경 항목별 `Correction`에는 원값·수정값·사유·근거 ID·수정자·시각·request/revision/run/Config 버전을 저장한다. 모델 반환값에 해당하는 분류 수정은 `CORRECTS`로 원 `ModelOutput`에 연결된다. 카탈로그가 작성한 초안 업무 필드는 대응하는 Jev `ModelOutput`이 없으므로 관계를 합성하지 않고 `RECORDED`와 원안·수정값을 보존한다. 단건 결정은 RuleCandidate·RuleVersion·ConfigVersion을 변경하지 않는다.

승인 시 같은 트랜잭션의 `assign_in_tx`가 요청당 Assignment 1개와 `(assignment_id,draft_task_id)`당 Task 1개를 생성한다. Request에서 Task로 `HAS_TASK`, Task에서 Org로 `ASSIGNED_TO {role}`를 만들고 실제 선행 작업에만 `PRECEDES`를 만든다. 개발 가능성 차단은 승인 결정의 `Correction` 수정값이 있으면 그 값을, 없으면 원 `Judgment.feasibility`를 사용한다. 선행 작업·초안 사유·미정 상태 또는 최종 분류의 미해결 개발 가능성이 있는 본업무는 `막힘`으로 시작한다. 명시적으로 연결된 선행 확인 업무와 모든 선행 업무가 완료되면 본업무 시작 전이에서 가능성 차단을 해제하고 감사 기록에 전후 차단 사유를 남긴다. 다른 초안 전제는 그대로 유지한다. 정보 요청은 `보완 필요`와 `needed_info` 목록을, 반려는 `반려` 상태를 저장한다. 결정·배정·감사·이벤트·멱등 결과는 함께 커밋한다.

worker 판단 저장 후 자동 배정 대상은 같은 `assign_in_tx`를 호출한다. 이는 worker 소유권과 활성 실행을 검증한 `ctx.commit` 내부다. 배정 서비스는 실행 고정 Config 버전, 최신 입력/실행, 근거 링크, 모든 Choice/Noul 신호, 위험·긴급·개발 가능성, 초안, 기존 배정을 다시 확인한다. 조건이 강화되거나 초안이 유효하지 않으면 최초 판단은 보존하고 새 검토 대상으로 전환한다. 이미 배정된 요청의 재분석은 기존 업무를 유지한다. 부트스트랩 정책은 자동 배정 off이며 안전 조건은 on 정책에서도 서버 코드로 강제한다.

FIX-R: 이미 Assignment가 있는 요청의 재분석 결과 저장 경로는 `auto_assign_after_judgment_in_tx`를 호출하지 않으며 Review를 만들지 않는다. 배정 전 재분석의 이전 pending Review는 판단 저장 트랜잭션에서 superseded로 닫는다. 과거 Review 결정은 `decide`의 대상 상태·최신 실행 검사로 409가 된다. Request 잠금과 활성 run·worker 소유권 검증은 기존 `ctx.commit`이 적용한다.

검증: `make up` 후 `backend/.venv/bin/pytest backend/tests/integration/test_review_assignment.py backend/tests/integration/test_policy_versions.py -q`에서 실제 Neo4j 통합 시험 18건 통과했다. 검토 결정 4종, 원안·Correction 관계, 과거 버전 409, 동시 승인 20개, 멱등 충돌, 권한·tenant·CSRF, 자동 배정 안전 재검증, 재분석 후 업무 불변을 포함한다. 마지막 전체 `make test`는 88건 통과·1건 실패·1건 건너뜀이다. 실패는 T08 worker 인계 시험의 예상 이벤트 목록이 실제 `run.step` 이벤트를 포함하지 않는 문제이며, 요청 검토 시험은 모두 통과했다.

UX-5: 검토 상세(`GET /api/reviews/{id}`)의 각 `drafts[]` 항목에 `source`(`ai`|`reviewer`)·`created_by`가 추가되고, 최상위에 `original_draft`(최초 AI 원안)와 `current_draft`(검토의 현재 `draft_version`)가 추가된다. 권한 판정은 바꾸지 않았다. 화면은 현재 초안의 업무만 편집 대상으로 보이고 “AI 원안” 값은 `original_draft`에서 가져오며 처리된 검토는 “원안과 비교”로 버전별 차이를 확인한다.

P1-01 (2026-10-05): 수정 승인은 원본 초안의 필수 필드 검증을 건너뛰고 허용된 검토 수정 값을 먼저 합친 최종 초안을 검증한다. 일반 승인은 원본을 그대로 검증하며 반려·정보 요청은 기존 동작을 유지한다. 미정 주관 조직·업무 방식·제목·산출물을 보완할 수 있으며 원본 Draft/Judgment, 새 Draft 버전, Correction, 감사 기록의 저장 구조는 유지한다. 필수 텍스트는 공백 또는 `미정`을 허용하지 않는다. 422 응답은 `detail.message`와 `detail.details.field_errors[]`의 `draft_task_id`, `field`, `message`를 제공하고 화면의 해당 공용 Field 입력에 접근 가능한 오류를 표시한다. 상세 응답의 추가 필드 `orgs`는 tenant 내 조직의 `id`·`name`을 제공하여 주관 조직 선택에 사용한다. 화면은 공용 Select/TextField로 업무 방식, 주관 조직, 업무 제목, 산출물, 협업 조직과 선행 업무를 편집하며 처리된 업무 입력은 읽기 전용이다.

재현·검증: `test_review_assignment.py`의 미정 초안 보완 승인 및 미해결 422 안내 시험 2건과 `Review.test.tsx`의 보완 입력·필드 오류 시험 2건은 수정 전 실패를 확인했다. 수정 후 검토 통합 시험 21건 통과. `frontend/e2e/review-repair.spec.ts`는 각 브라우저 프로세스별 새 tenant만 시드·정리하며 실제 API 10591/Vite 7891에서 Chromium·WebKit 모두 미해결 422 → 수정 승인 200, v2와 AI 원안 보존을 검증했다. 생성 Job을 사용하지 않아 worker 실행은 필요하지 않다. 전체 검증 결과는 해당 개선 단계의 코디네이터 보고로 함께 기록한다.

P1-01 최종 확인: 검토 통합 시험 전체 24건 통과, 전체 Ruff 0건, import 계약 6개 통과, typecheck/build 통과. 전체 pytest 최초 실행은 475 통과·2 실패·1 건너뜀이며 실패는 `test_rules_integration.py::test_role_matrix_and_state_transitions`(learning 읽기 역할의 기대 403과 실제 200 차이)과 `test_write_invariants.py::test_completed_confirmation_predecessor_releases_feasibility_block`(tasks 감사 after의 가능성 차단값 잔존)으로 담당 밖 동시 변경 항목이다. 해당 파일은 수정하지 않고 코디네이터에 상세 실패를 보고했다. 전체 Vitest 초기 실행은 동시 변경 중 learning/proposal 및 Monitoring 시험 실패를 관찰했으나 이후 3회 연속 실행에서 각각 41개 파일·366건 모두 통과했다. P1-01 구현과 전용 시험에서 건너뛴 항목은 없으며 공유 서버/Neo4j를 정지하지 않고 전용 서버만 종료했다.

FIX-QAC (2026-10-05): `DecisionCommand.changes`를 분류·업무 수정용 중첩 Pydantic 모델로 검증한다. 분류 목록, 문자열 업무 항목, 배열인 조직/업무 방식, 잘못된 선행 업무 ID 타입 및 허용하지 않은 필드는 서비스 트랜잭션에 진입하기 전에 422를 반환한다. 부분 수정은 기존 필드 이름을 유지하고 제공하지 않은 값은 서비스 명령에서 제외한다. 잘못된 입력 뒤 Review·Draft·판단·결정 이력 및 Assignment/Task/Correction은 변경되지 않는다. 유효한 수정 승인과 업무 필수 필드 오류의 기존 서비스 응답 계약은 유지한다.

검토 목록은 책임 조직 조건을 DB WHERE에 적용한 뒤 `created_at DESC, id DESC`로 정렬하고 `SKIP/LIMIT`을 적용한다. `GET /api/reviews`에 선택적인 `limit`(기본 100, 최대 500)·`offset`(기본 0)을 추가했다. 기존 응답 `reviews[]`는 유지한다. 회귀 시험은 최신 타 조직 100건 뒤의 허용 검토가 목록과 상세에 모두 나타나는지, 정규 ID·네 종류의 조직 별칭과 역할 조건이 동일한지 확인한다.

재현·검증 증거는 `artifacts/review/fix-qac/REPORT.md`와 수정 전/후 로그에 기록한다. 제품 시험은 `tests/unit/test_qac_api_boundaries.py`, `tests/unit/test_qac_external_boundary.py`, `tests/integration/test_qac_regressions.py`이다.
