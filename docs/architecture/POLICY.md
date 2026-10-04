# Dynamic Config 정책 API (T15)

정책은 tenant별 불변 `ConfigVersion` 노드에 JSON으로 저장한다. `schema_version`은 `policy-schema-v1`이며 Choice confidence 임계값과 Noul 확률 임계값을 별도 맵으로 관리한다. 초기 설정은 자동 배정 off, 위험 없음 확인 대역 `risk_clear_max=0.2`, 근거·카탈로그 Noul 임계값 0.6이다. 한도는 PRD 7절의 최대값(텍스트 20,000자, 첨부 5개, 파일 10 MiB, 합계 25 MiB, PDF 50페이지)을 넘을 수 없다.

Choice confidence 기본 임계값은 `ai_need`·`feasibility`·`urgency`·`lead_org` 각각 0.8이다.
참여 Noul 불확실 대역 `noul_uncertain_band` 기본값은 `[0.35, 0.65]`이며 이 구간은 사람 검토 사유다.

규칙 학습 설정 `learning`은 `min_support=3`(최소 2), `min_effect_sample=20`(최소 5), `shadow_max_calls=20`(0~200), `effect_window_days=7`(1~90)을 기본값으로 갖는다. 이 값은 ConfigVersion에 저장되어 후보 자료 부족, 섀도 호출 상한, 효과 판정 표본 및 관찰 창에 사용된다.

`GET /api/policy/active`는 실행 시작 시 호출할 `get_active_snapshot(tenant) -> (version, config)`와 같은 tenant 활성본을 돌려준다. worker는 Job/Run 생성 또는 claim 시점에 이 반환값을 Run에 기록해 실행 동안 고정해야 하며 이후 게시가 기존 Run의 버전을 바꾸지 않는다. 이 API에서 0은 아직 부트스트랩하지 않은 tenant의 보수적 기본값이다. `scripts/bootstrap_dev.py`는 개발 tenant의 버전 1을 생성한다.

버전 조회는 `GET /versions`, `GET /versions/{version}`이며 상세 응답의 `diff`는 직전 활성본 대비 변경 키를 담는다. `POST /validate`는 초안을 저장하지 않는다. 게시와 되돌리기는 각각 새 버전을 만든다. 쓰기 요청은 `policy_editor`, CSRF 토큰, `Idempotency-Key`를 요구한다. `expected_active_version` 불일치는 409, 불변 조건 위반은 오류 코드와 사유가 담긴 422다. 변경 사유는 필수다. 감사 기록·이벤트와 활성 포인터 변경은 동일 Neo4j 쓰기 트랜잭션에 커밋된다.

필수 검토 대상의 무승인 배정 금지는 서버 불변 조건이다. `auto_assign=true`는 게시할 수 있지만 실행 시 고정 정책과 입력·판단·근거·초안·위험 신호·중복 여부를 모두 재검증한 요청에만 적용된다. `risk_clear_max > 0.5`, 필수 검토 해제, 조건부/현재 불가/정보 부족/미정 자동 배정을 허용하는 위험 완화 규칙 참조는 거절한다. 일반 policy_editor 게시/rollback은 `rules`를 변경할 수 없다. 규칙 게시·중단·되돌리기용 권한 경로는 T32가 담당한다.

한계: 이번 버전은 정책 데이터와 고정 지점 API를 제공한다. T09 worker가 실제 Run에 snapshot을 기록하는 연동은 별도 선행 작업이다. 개발 bootstrap 외 운영 tenant 초기 버전 프로비저닝은 배포 절차에서 호출해야 한다.

## 정책 편집 화면 (UX-SCREENS)

- 편집기는 항목별 입력 폼이다. 수치는 숫자 입력(허용 범위 표시), `noul_uncertain_band`는 하한·상한 두 값, 불리언(`feature_flags`, `masking.enabled`)은 스위치, `masking.categories`는 칩이다. 영문 키는 각 묶음의 ‘기술 상세’ 안에만 보인다.
- 원본 JSON은 ‘고급: JSON 보기’(접힌 영역)에서 항목별 textarea(`<이름> (JSON)`)로 편집한다. 잘못된 JSON은 마지막 유효값을 유지한다. 폼과 JSON은 같은 `configRef`를 갱신한다.
- 숫자 칸이 비어 있거나 숫자가 아니면 게시가 막히고, 게시 버튼이 비활성인 동안 이유 문구(`게시할 수 없는 이유: …`)를 보여 준다.
- 버전 이력은 카드 안 가로 스크롤 표(>520px)와 카드형 목록(≤520px)이다.
- 서버 `PolicyConfig`의 `noul_uncertain_band`·`learning`·`masking`·`retention`은 화면에서 `FullPolicyConfig`(pages/policy/PolicyForm.tsx)로 다룬다. API 계약은 바뀌지 않았다.

## 공용 입력 구성요소

`frontend/src/components/fields.tsx`(+`fields.css`): `Field`, `TextField`, `Select`, `Checkbox`, `Switch`, `ChipGroup`, `NumberField`, `SearchSelect`(검색 가능한 combobox), `DateTimeField`/`DateRange`(년·월·일·시·분 입력, 브라우저 로케일과 무관한 한국어 형식), `EmptyCard`, `FilterBar`. 정책·업무·검토 대기·실행 관찰·모니터링이 사용하며 모든 컨트롤은 44px 터치 높이와 같은 포커스 링을 쓴다.
