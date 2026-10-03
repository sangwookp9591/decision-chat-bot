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

역할은 Neo4j Membership 관계에서만 읽고, 요청 본문·헤더의 tenant나 role은 권한 근거가 아니다. `get_principal`은 세션 tenant/user와 조직·역할을 제공한다. `can_view_request`, `can_review`, `scope_filter_cypher`는 요청 목록·상세 구현이 적용할 정책 도우미다. 운영자는 tenant 내 메타데이터를 볼 수 있어도 원문은 `can_read_source`가 별도로 참이어야 한다.

## API와 세션

- `POST /api/auth/login`은 `{ "email": "...", "password": "..." }`를 받고 일반화된 실패 응답을 반환한다.
- 성공 시 12시간 서버 저장 세션을 만들고 무작위 bearer 값을 HttpOnly `jev_session` 쿠키로 전달한다. DB에는 bearer SHA-256만 보관한다. 브라우저 HTTPS 요청에는 Secure가 설정된다.
- `GET /api/auth/me`는 사용자·tenant·조직·역할과 CSRF 토큰을 반환한다.
- `POST /api/auth/logout`은 세션을 폐기한다.
- 로그인 실패 카운터는 `(tenant_id, email)` 유일 제약이 있는 `LoginAttempt` 노드에 원자적으로 누적한다. tenant/email 키의 `MERGE`와 증가를 한 쿼리로 처리해 동시에 첫 실패가 발생해도 한 노드에 모든 시도가 반영된다. 상태 변경 API는 `X-CSRF-Token`과 `jev_csrf` 쿠키 값을 함께 보내야 하며 double-submit 값을 서버 세션과 비교한다.

## 개발 계정과 운영 인증

`python scripts/bootstrap_dev.py [--password PASSWORD]`는 `t-alpha`, `t-beta` 각각에 AI·IT·현업 조직과 여섯 역할 계정을 만든다. 계정은 `<role>@<tenant>.dev`이며 기본 암호는 `dev-only-change-me`; 로컬 개발 전용이므로 운영에서 사용하지 않는다. `JEVTRIAGE_DEV_PASSWORD` 또는 `--password`로 실행 시 암호를 지정할 수 있다. 비밀번호는 Argon2id로 해시한다.

개발 계정은 실제 운영 인증 공급자와 분리된 개발 편의 경로다. 운영 공급자 연동과 설정은 T26의 범위이며 이 bootstrap을 운영 계정 프로비저닝으로 사용하면 안 된다.
