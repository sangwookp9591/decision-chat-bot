# FIX-LEARN 검증 보고 (2026-10-05)

## 재현 → 수정 → 통과

| 항목 | 수정 전 제품 시험 실패 | 수정 | 최종 근거 |
| --- | --- | --- | --- |
| P1-03 / SPEC-F01 | `test_learning_read_contract::test_rule_effect_comparisons_expose_human_labeled_sample_counts` cohort `labeled_count` 누락, `test_effect_labels::test_effect_requires_human_labels_even_with_many_runs` KeyError | 4개 cohort 정답 실행 수, 승인/수정 후 승인 정의, 전후 정답 최소 표본 gate, 화면 정의·정답 수·미확정 안내 | 중복 결정 1건 처리·미승인/기각/shadow 제외 및 reviewer 요청 범위 집계 통과, Observation UI 시험 통과 |
| P2-08 / SPEC-F04 | `test_rule_read_allowed_for_scoped_reviewer_and_operator[reviewer/operator]` 실제 403, 기대 200 | `rule:read`와 변경 권한 분리, 버전별 requester_org 범위 필터, 범위 밖 404, 원문 기존 권한, 화면 규칙·효과 조회 연결 | 역할/조직 행렬 5개 사례의 상세·효과·목록·변경·원문 검증 통과 |
| P2-01 | `proposal.test.tsx::reviewer can open a human proposal form` 제안 버튼 없음 | 기존 propose API로 지원 값·지지 Correction 선택·범위·사유 제출, 성공 후보 자동 선택, operator/조회 불가 역할 양식 숨김 | 실제 API/Neo4j Chromium·WebKit 후보 제안→승인→섀도→게시 및 reader 변경 비활성·조직 범위 밖 404 통과 |
| 제안 지원 값 | 추가 safety 시험에서 서버 허용 값 긴급 옵션 없음 | 서버 안전 allowlist대로 urgency 긴급만, feasibility 가능 제외, 미지원 동작 안내 | safety 옵션 시험 통과 |

재현 제품 시험은 먼저 추가하고 실제 실패를 확인한 뒤 수정했다. 최초 백엔드 재현 4 failed, 최초 제안 UI 재현 1 failed/1 passed였다.

## 최종 검증

- 전체 `cd backend && .venv/bin/pytest -q`: **483 passed, 1 skipped** (166.39초).
- 담당 backend 시험(`test_learning_read_contract`, `test_rules_integration`, `test_effects_api`, `test_effect_labels`): **19 passed** (7.21초).
- `.venv/bin/ruff check jevtriage tests`: **0건**; `.venv/bin/lint-imports`: **6 kept / 0 broken**.
- 전체 vitest: 반복 성공 366/366/367개, 최종 변경 후 **368 passed / 42 files** (17.42초). 담당 Learning UI 시험도 통과했다.
- `npm run typecheck`, `npm run build`: 최종 통과.
- API **10891**, Vite **8191**, `E2E_BASE_URL=http://127.0.0.1:8191 npx playwright test e2e/learning-human.spec.ts --project=chromium --project=webkit --workers=1`: 최신 API 재시작 후 최종 **2 passed** (21.2초).
- `git diff --check`: 통과. commit/push하지 않았다.

초기 전체 pytest 실패의 구 규칙 조회 403 기대값은 새 읽기 계약에 맞춰 갱신했다. 초기 fixture의 전역 Correction ID 충돌은 tenant를 포함한 고유 ID로 수정하고 자체 시험 tenant를 정리했다. 다른 작업자의 Tasks 불변 조건 시험 실패는 코디네이터에 전달했고 최종 전체 실행에서는 통과했다. 최초 전체 vitest의 Evaluation 키보드 focus 시험은 일시 실패했으나 이후 전체 실행에서 통과했다. 초기 Monitoring 타입 fixture 누락은 담당 작업자 수정 후 통과했다. 브라우저 시험은 섀도 결과 노출 직후 후속 동작을 누르기 전에 검증 동작 완료를 기다리도록 동기화했다.

## 범위와 제한

요청 항목 중 건너뛴 항목은 없다. E2E는 별도 tenant에 결정적 사람 수정 fixture를 저장하여 학습 여정을 검사하며, fixture 생성에 외부 모델 API를 호출하지 않는다. 규칙의 조직 읽기 범위는 각 버전의 결정적 `requester_org` 조건으로 정의하며 조건 없는 규칙은 tenant 공통이다. 문서는 `docs/architecture`만 갱신했고 요구사항 원본 `docs/spec`는 수정하지 않았다. 공유 Neo4j와 타 작업자 서버는 정지하지 않았다.
