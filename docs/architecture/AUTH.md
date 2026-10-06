# 인증·역할·조직 접근

## 역할과 권한

| 역할 | 권한 |
| --- | --- |
| requester | 본인 및 명시 공유 요청 생성·조회·보완 |
| reviewer | 소속/공유 범위 검토·승인·수정 승인·반려·정보 요청, 후보 제안 |
| team_member | 배정 조직 업무 조회·허용 상태 변경 |
| operator | 운영 메타데이터 조회·오류 진단·재시도; 원문 열람은 별도 `can_read_source` 허용 필요 |
| policy_editor | Dynamic Config 편집·게시(별도 구현 모듈에서 강제) |
| rule_admin | 규칙 후보 승인·범위 수정·기각·검증·게시·중단·되돌리기(08_LEARNING_LOOP 4절) |

역할은 Neo4j Membership 관계에서만 읽고, 요청 본문·헤더의 tenant나 role은 권한 근거가 아니다. `get_principal`은 세션 tenant/user와 조직·역할을 제공한다. `auth/policy.py`의 `can(principal, action, resource_meta)`가 요청·검토·업무·Trace·그래프·학습·정책·모니터링 권한을 판정한다. 기존 `can_view_request`, `can_review` 등은 이 정책을 호출하는 호환 래퍼다. 목록의 `scope_filter_cypher`는 단건 조회와 동일하게 `org_ids`와 `shared_org_ids`의 합집합을 사용한다.

관리형 DB transaction은 인증된 tenant를 `TenantTx`에 고정한다. 질의가 전달한 `tenant_id` 또는 `tenant` 값이 다르면 실행 전에 거부한다. 시험은 tenant 매개변수가 없는 질의를 거부하며, worker 발견 등 운영상 교차 tenant 작업은 사유가 필요한 `cross_tenant_tx`를 사용한다. 이 DB 경계는 역할·조직 권한을 대신하지 않으며 위 정책 판정을 함께 적용한다.

로그인 이메일 조회(`auth.login_tenant`, `auth.authenticate`), 세션 token 조회(`auth.session_lookup`)와 token hash 기반 폐기(`auth.revoke_session`)는 tenant가 정해지기 전이므로 이유를 기록한 `cross_tenant_tx`를 사용한다. 로그인 실패 카운터와 세션 생성은 `write_tx`, 표시 이름 조회는 `read_tx`로 확정된 tenant에 고정한다. AST 회귀 시험은 `db/driver.py`와 `db/tx.py` 밖에서 직접 `get_driver` 또는 `.session()`을 사용하는 코드를 금지한다.

로그인 이메일 조회(`auth.login_tenant`, `auth.authenticate`), 세션 token 조회(`auth.session_lookup`)와 token hash 기반 폐기(`auth.revoke_session`)는 tenant가 정해지기 전이므로 이유를 기록한 `cross_tenant_tx`를 사용한다. 로그인 실패 카운터, 세션 생성, 표시 이름 조회는 확정된 tenant를 사용해 각각 `write_tx` 또는 `read_tx`로 실행한다. AST 회귀 시험은 `db/driver.py`와 `db/tx.py` 밖에서 직접 `get_driver` 또는 `.session()`을 사용하는 코드를 금지한다.

검토 결정은 같은 tenant의 **reviewer** 역할과 검토의 `required_reviewer_org` 소속을 모두 요구한다. 판단의 `lead_org`가 정해지지 않아 저장된 `"검토자"` 값은 tenant의 AI 조직(`<tenant>-ai`)으로 해석한다. 호출자 자신의 조직으로 해석하거나 요청 메타에 담당 조직을 삽입하지 않는다. `team_member`는 검토 결정을 할 수 없다.

원문(`InputRevision.text`, 근거 `source_text`, 추출 텍스트)은 `can_read_source=true`인 계정에게만 응답한다. 요청 상세를 포함한 API 응답은 공통 `redact_source(principal, payload)`에서 원문 필드를 제거한다. 운영자는 tenant 안의 메타데이터를 볼 수 있어도 이 플래그가 없으면 원문을 볼 수 없다. 근거 단건 API는 원문 권한이 없으면 404를 반환한다.

검토 대기 목록은 검토 권한을 통과한 항목에 저장된 마스킹 `title`을 포함한다. `preview`는 `can_read_source` 또는 작성자 요청 읽기 권한이 있을 때만 포함한다. 검토 상세는 검토 권한으로 열 수 있지만, 일반 요청 상세 API는 요청자·공유·조직 범위(`can_view_request`)가 별도이므로 404일 수 있다. 검토 상세의 `request.request_text`는 검토자가 `can_read_source=true`일 때만 포함하고, 그렇지 않으면 화면은 제목·허용된 마스킹 미리보기와 원문 권한 안내를 표시한다.

## API와 세션

- `POST /api/auth/login`은 `{ "email": "...", "password": "..." }`를 받고 일반화된 실패 응답을 반환한다.
- 성공 시 12시간 서버 저장 세션을 만들고 무작위 bearer 값을 HttpOnly `ildongi_session` 쿠키로 전달한다. DB에는 bearer SHA-256만 보관한다. 브라우저 HTTPS 요청에는 Secure가 설정된다.
- `GET /api/auth/me`는 사용자·tenant·조직·역할과 CSRF 토큰을 반환한다.
- `POST /api/auth/logout`은 세션을 폐기한다.
- 로그인 실패 카운터는 `(tenant_id, email)` 유일 제약이 있는 `LoginAttempt` 노드에 원자적으로 누적한다. 기본 시간 창은 15분(`LOGIN_WINDOW_SECONDS=900`), 최대 실패 횟수는 10회(`LOGIN_FAILURE_LIMIT=10`)다. 한도에 도달하면 비밀번호 검증 전에 429를 반환하며, 창이 지나면 카운터를 초기화한다. 미등록 계정도 `unknown` tenant 네임스페이스에서 같은 카운터 형식과 더미 Argon2 검증을 사용한다. 성공 시 카운터를 초기화한다. 상태 변경 API는 `X-CSRF-Token`과 `ildongi_csrf` 쿠키 값을 함께 보내야 하며 double-submit 값을 서버 세션과 비교한다.
- SSE 스트림은 연결 중 기본 15초마다(`SSE_SESSION_RECHECK_SECONDS`) 세션을 다시 읽는다. 폐기·만료·비활성화 시 `session-expired` 이벤트를 보내고 연결을 닫는다. 역할·조직이 바뀌면 갱신된 principal로 후속 이벤트의 요청 범위를 판정한다.

## 개발 계정과 운영 인증

`python scripts/bootstrap_dev.py [--password PASSWORD]`는 `t-alpha`, `t-beta` 각각에 AI·IT·현업 조직과 여섯 역할 계정을 만든다. 계정은 `<role>@<tenant>.dev`이며 기본 암호는 `dev-only-change-me`; 로컬 개발 전용이므로 운영에서 사용하지 않는다. `ILDONGI_DEV_PASSWORD` 또는 `--password`로 실행 시 암호를 지정할 수 있다. 비밀번호는 Argon2id로 해시한다.

개발 계정은 실제 운영 인증 공급자와 분리된 개발 편의 경로다. 운영 공급자 연동과 설정은 T26의 범위이며 이 bootstrap을 운영 계정 프로비저닝으로 사용하면 안 된다.

### 규칙 읽기 권한

`rule:read`는 reviewer·operator·rule_admin의 규칙 조회 권한이며 `learn_admin`(rule_admin 전용 변경)과 분리한다. reviewer는 조직 제한 규칙 버전의 requester_org 범위와 소속 조직이 일치해야 한다; 조직 제한이 없는 규칙은 tenant 공통으로 조회한다. operator·rule_admin은 tenant 전체를 조회한다. 목록에서 가려진 버전은 제외하고 범위 밖 상세·효과는 404로 응답한다. 원문은 기존 source 권한으로 제거하며 후보 제안은 기존 `learn_propose`(reviewer·rule_admin)를 사용한다.

## 요청 검증·조회 경계 (FIX-QAC, 2026-10-05)

전역 `RequestValidationError` 핸들러는 422 `detail[]`에서 `loc`, `type`, `msg`만 반환하고 제출 값인 `input`과 예외 객체가 들어갈 수 있는 `ctx`를 제거한다. 사용자 값을 메시지에 삽입할 수 있는 custom ValueError/AssertionError는 일반화된 메시지를 반환한다. JSON 요청은 본문 경계에서 비유한 수를 거부하며 `1e1000`, `NaN`, `Infinity`, `-Infinity`는 중첩 설정 객체 안에서도 400을 반환한다. 타입 오류는 원문을 반사하거나 JSON 직렬화 500을 만들지 않는다.

정책 버전 경로·게시/rollback 버전, 그래프 `config_version`, 검토 결정 버전 및 목록 offset은 공용 `domain.api_types.Int64`로 Neo4j의 signed int64 범위를 검증한다. 범위를 벗어난 값은 저장소 호출 전에 422로 거절한다. 각 필드의 기존 양수·깊이·limit 제약은 함께 적용한다.

검토 목록은 reviewer 역할을 확인한 뒤 책임 조직의 정규 ID와 기존 별칭(`AI팀`, `IT팀`, `현업`, `검토자`)을 상세와 동일하게 해석하여 DB WHERE에 적용한다. 권한 필터 뒤에 정렬·페이지 제한을 적용하므로 더 최근의 타 조직 검토 100건이 허용 검토를 가리지 않는다. operator 역할만 가진 계정은 검토 목록을 받지 않는다. 담당자 별칭 `검토자`는 계속 tenant AI 조직에만 대응한다.
