# P3 실제 브라우저 탐색 보고서

- 대상: `/Users/psw/Projects/decision-chat-bot`, HEAD `0da8b1e`.
- 실행: 2026-10-03 23:58 ~ 2026-10-04 00:10 KST, 로컬 macOS / OrbStack Neo4j.
- 브라우저: Playwright 실제 Chromium `153.0.8010.12`, WebKit `26.6`. 주 시험은 Chromium, WebKit은 로그인 세션·모바일 ChatWidget·미지원 권한 화면을 보조 확인했다. DOM 클릭·타이핑·파일 선택·키보드로 조작했으며 모의 API 응답을 사용하지 않았다.
- 역할: t-alpha의 requester/reviewer/team_member/operator/policy_editor/rule_admin 모두 별도 브라우저 세션. t-beta requester/operator도 별도 세션으로 접근 경계 시험.
- 기준: PRD, TASK, spec 02·04·06·08, EXECUTION_CONTRACT, IMPLEMENTATION, DATA_MODEL, AUTH, CONFIG, GATE_REPORT를 중심으로 요구와 실제 동작 대조. 모든 기준 문서의 모든 조항을 전수 검증한 보고서는 아니다.
- 제품 코드·문서·설정·Git 상태를 변경하지 않았다. 이 보고서와 같은 폴더의 PNG만 산출물로 작성했다. 실행으로 생성된 가상 요청·검토·업무·정책/규칙 감사 이력은 공유 개발 DB에 보존했다.

## 요약

재현 결함 13건(높음 2, 중간 9, 낮음 2)을 확인했다. 핵심 문제는 로그인 진입 수단 부재, 정보 요청 후 보완 동선 단절, 잘못된 Trace 링크, 역순 Flow, 규칙 검증 결과 직렬화 불일치다. 정상 경로의 실제 Jev 분석·손상 파일 제외·재분석·승인/수정 승인·팀 업무 전이·정책 및 규칙 수명은 동작했지만, 이 결과만으로 요구사항 전체 통과를 선언하지 않는다.

아래 스크린샷 링크는 모두 이 폴더의 상대 경로이며 가상 입력/개발 계정만 포함한다. 오류 화면이 API 응답 이전에 찍힌 경우에는 안정화 후 읽은 DOM·HTTP 상태와 코드 근거를 우선한다.

## 재현된 결함

### P3-01 [심각도 높음] `frontend/src/pages/Login.tsx:1` — 로그인 화면에 행동 수단이 없음

- 재현: 쿠키가 없는 새 브라우저에서 `/` 방문.
- 기대/실제: 개발 계정으로 로그인하거나 인증 공급자로 이동할 수 있어야 하나, “로그인이 필요합니다 / 인증된 세션으로 접속해 주세요” 텍스트만 있다. 입력·버튼·로그인 링크가 전혀 없어 사람 사용자는 시작할 수 없다.
- 근거: 실제 Chromium 화면 [01-login-no-action.png](01-login-no-action.png). Login 컴포넌트는 정적 설명만 반환한다. 후속 시험은 `POST /api/auth/login`으로 쿠키를 만든 뒤 UI를 조작했으며, 이를 UI 로그인 성공으로 세지 않았다.
- 제안 수정: 이메일/암호 폼을 기존 인증 API에 연결하거나 실제 동작하는 인증 진입 링크 제공. 성공 후 원래 URL 복원, 오류 안내와 제출 중 상태 추가.
- 예상 규모: M.

### P3-02 [심각도 높음] `frontend/src/pages/Main.tsx:70`, `:130`, `:140` — 정보 요청 후 보완 제출과 상태 표시가 단절됨

- 재현: 요청 `req_f838e37f861d47be856085a935e2aa31`을 검토자 두 탭에서 열고 한 탭에서 “사용 부서와 완료 희망일을 보완해 주세요”라는 정보 요청 저장. 요청자에서 해당 요청 다시 열기.
- 기대/실제: 보완 사유와 필요한 정보를 보여 주고 같은 요청의 새 revision을 제출해야 한다. 실제 요청 목록/운영 화면은 “보완 필요”이지만 결과·진행 카드는 “검토 대기”이고, 사유와 보완 제출 버튼은 없다. 입력 폼 버튼은 “요청 보내기”이며 `needs_file_decision`일 때만 revisions API로 보내므로 일반 정보 보완은 새 요청으로 접수된다.
- 근거: [07-info-request-no-revision.png](07-info-request-no-revision.png), `Main.tsx`의 `revising = detail?.request.status === 'needs_file_decision'` 및 `judgment.review` 객체 존재만으로 상태 라벨을 결정하는 분기. spec 02의 정보 요청→새 revision 흐름과 불일치.
- 제안 수정: needs_info 등 보완 상태와 최신 ReviewDecision/needed_info를 읽고, expected_revision을 포함한 보완 폼을 제공. 요청 상태와 검토의 실제 status를 기준으로 결과 배지를 표시하고 반려/승인 후에도 갱신.
- 예상 규모: M.

### P3-03 [심각도 중간] `frontend/src/pages/Monitoring.tsx:59`, `frontend/src/layout/AppShell.tsx:16` — 실패→Trace 링크가 없는 라우트로 이동

- 재현: 운영자 모니터링의 “실패 원인과 Trace”에서 요청 링크 클릭.
- 기대/실제: 실패 실행/시도 상세로 이동해야 하나 `/observatory/trace?request_id=req_ad2641e055634f17b0dcc8e780e773a7`에서 “페이지를 찾을 수 없습니다”.
- 근거: [11-monitoring-trace-404.png](11-monitoring-trace-404.png). Monitoring은 `/observatory/trace`를 만들지만 AppShell은 `/observatory`만 등록한다. 같은 패턴의 실행·시도 링크에도 적용된다.
- 제안 수정: Trace 라우트와 request/run/attempt 식별자 해석을 구현하거나 지원되는 `/observatory` 라우트로 연결하고 해당 실행/단계를 자동 선택. attempt-only 실패도 찾을 수 있게 처리.
- 예상 규모: M.

### P3-04 [심각도 중간] `backend/jevtriage/observe/flow.py:15`, `frontend/src/pages/Observatory.tsx:34` — Flow가 실제 순서의 역순이고 관계를 그리지 않음

- 재현: 운영자 `/observatory?request_id=req_f838e37f861d47be856085a935e2aa31`, 실행 Flow 확인·재생·전체 결과 선택.
- 기대/실제: 입력 정리→Jev 판단→근거 연결→업무 분해→규칙 적용→배정 검사→저장 순서를 표시해야 한다. 실제 DOM 순서는 “결과 저장, 자동 배정 조건 검사, 규칙 적용, 업무 분해, 근거 연결, Jev 판단, 입력 정리, human”.
- 근거: [24-flow-order.png](24-flow-order.png). Neo4j `collect(DISTINCT s)`에 정렬이 없고 프런트는 그대로 `flow.nodes.map`을 렌더링한다. API의 edges는 Flow 화면에서 그리지 않으며 재생 완료 판정에도 배열 인덱스를 사용한다. 특정 시점 재생의 모든 강조 상태까지 전수 검증하지 않았으나 순서 오류는 재현 확정.
- 제안 수정: predecessor DAG에 따른 안정적 위상 정렬과 시작 시각 보조 정렬 적용. edges로 연결/분기를 표시하고 재생 완료 여부를 노드별 이벤트로 판단. 사람 노드 이름도 한국어로 표시.
- 예상 규모: M.

### P3-05 [심각도 중간] `frontend/src/layout/AppShell.tsx:16`, `frontend/src/pages/Main.tsx:30` — 접수 화면에서 ChatWidget 전송이 즉시 전달되지 않음

- 재현: `/`에서 위젯 열기→“채팅으로 추가한 회의실 검색 요청입니다” 입력→보내기→닫기.
- 기대/실제: 입력이 접수 폼에 전달되거나 접수 동작/확인이 있어야 한다. 위젯 입력만 지워지고 접수 textarea는 빈 값이다. 새로고침한 뒤에야 해당 문장이 나타난다.
- 근거: [02-chat-send-stuck.png](02-chat-send-stuck.png), 전송 직후 `요청 내용.inputValue() === ''`, reload 후 문장 복원. AppShell은 sessionStorage 저장 후 같은 `/`로 navigate하고, Main은 mount 때만 storage를 읽는다. Main의 `chat:request` 이벤트 수신기에 해당 이벤트를 보내지 않는다.
- 제안 수정: 공유 상태 또는 실제 `chat:request` 이벤트로 즉시 전달하고 포커스를 접수 입력으로 이동. 사용자가 확인할 수 있는 전달 완료 안내 제공.
- 예상 규모: S.

### P3-06 [심각도 중간] `backend/jevtriage/learning/shadow.py:200`, `:211`, `frontend/src/pages/learning/sections.tsx:49` — 검증 결과가 문자 인덱스로 표시되고 검증 기간이 없음

- 재현: 수정 기록에서 후보 집계→자료 부족 후보 `cand_b00c9548d5bf016247b666e0` 승인→`R-BROWSERP-01@1` 검증 실행.
- 기대/실제: “lead_org:현업 8건”과 검증 시작/끝을 표시해야 한다. 실제 “0 { · 1 \" · 2 l · 3 e · … · 11 현 · 12 업 …”처럼 문자열의 각 문자가 펼쳐지고 기간은 `— ~ —`, 실패는 `[]`로 표시된다.
- 근거: [16-learning-validation-garbled.png](16-learning-validation-garbled.png). 실제 검증 `val_b693263d3cf84c138c98f8d2eb14ed44`, 표본 22건/변경 8건. GET 조회는 Neo4j properties를 그대로 반환하여 `changes_by_value` JSON 문자열을 해제하지 않고 `from_at/to_at`을 프런트의 `from/to`에 맞추지 않는다. 프런트는 Object.entries를 적용한다.
- 제안 수정: POST/GET/목록이 같은 ValidationResult DTO를 반환하도록 JSON 필드 역직렬화와 날짜/실패 개수 정규화. 게시 전 검증 요약에 실제 필드별 변경 수를 표시.
- 예상 규모: S.

### P3-07 [심각도 중간] `frontend/src/pages/Review.tsx:12`, `:16` — 409 충돌 안내가 즉시 지워짐

- 재현: 같은 검토를 두 탭에서 열고 첫 탭에서 정보 요청 결정. 이전 탭에서 반려 시도. 이후 승인까지 진행한 뒤 오래된 탭에서 다시 반려하여 재확인.
- 기대/실제: 다른 검토자가 변경했다는 안내와 최신 상태가 유지돼야 한다. 실제 HTTP 409는 확인됐지만 안정화 후 `role=status` 내용은 빈 배열이고 오류 배너도 없다.
- 근거: [06-review-conflict.png](06-review-conflict.png), 네트워크 409 실측. catch에서 setNotice 후 `open()`을 호출하고, `open()` 마지막의 `setNotice('')`가 설명을 지운다.
- 제안 수정: 새 대상 로드 이후 충돌 notice를 설정하거나 open의 notice 초기화를 선택적으로 수행. 최신 검토가 종료 상태이면 결정 버튼도 비활성화.
- 예상 규모: S.

### P3-08 [심각도 중간] `frontend/src/pages/Policy.tsx:33` — JSON 편집기의 일반 타이핑이 방해됨

- 재현: 정책 편집자로 `risk_clear_max` 값 `0.2` 전체 선택→Backspace.
- 기대/실제: 빈 중간 입력을 유지하며 새 값을 쓸 수 있어야 한다. 실제 값은 즉시 `0.2`로 돌아오고 “올바른 JSON 값이 아닙니다”가 발생한다. 객체/문자열도 일시적으로 JSON이 깨지는 일반 편집을 할 수 없다. 완성된 유효 JSON을 한 번에 붙여 넣으면 변경은 가능했다.
- 근거: [10-policy-json-edit.png](10-policy-json-edit.png). onChange에서 매번 JSON.parse를 성공해야만 controlled value를 갱신한다.
- 제안 수정: 필드별 raw draft 문자열을 따로 보관하고 blur/서버 검증 시 파싱. 문법 오류 위치와 마지막 유효 값은 별도로 표시.
- 예상 규모: S.

### P3-09 [심각도 중간] `frontend/src/pages/Monitoring.tsx:20` — 날짜를 지우면 처리되지 않은 예외 발생

- 재현: 운영자 모니터링→시작 datetime-local 값을 지우기.
- 기대/실제: 필수 날짜 오류와 적용 비활성화를 기대하나 Chromium pageerror `Invalid time value` 발생. 기존 통계가 남고 해당 입력 오류 안내는 없다.
- 근거: [23-monitor-invalid-date.png](23-monitor-invalid-date.png), 페이지 오류 리스너에서 예외 수집. `new Date(range.from).toISOString()`을 검증/try 이전에 실행하고 필터 onChange가 즉시 load를 유발한다.
- 제안 수정: 날짜 유효성·시작≤끝 검사 후 조회. draft 필터와 적용 필터를 분리하고 예외를 입력 오류로 안내.
- 예상 규모: S.

### P3-10 [심각도 중간] `frontend/src/pages/judgment-map/Detail.tsx:39`, `frontend/src/pages/Review.tsx:10` — 판단 맵→원문·검토 딥링크가 요청을 선택하지 않음

- 재현: 요청 ID로 판단 맵 필터→회의실.md 문서 근거 노드 선택→“원문·검토 열기”.
- 기대/실제: 같은 요청의 검토/원문 상세를 보여야 하나 `/review?request_id=...`에서 “왼쪽 목록에서 요청을 선택하세요”만 표시된다. 이미 pending 목록에서 빠진 요청은 이 화면에서 다시 찾기도 어렵다.
- 근거: [12-map-selected.png](12-map-selected.png)의 링크 및 클릭 후 안정화 DOM. Review는 URL query를 읽지 않으며 항상 selected=null로 시작한다.
- 제안 수정: request_id/review_id로 대상 조회 후 상세 자동 선택. 처리된 검토도 조회할 수 있는 경로와 역할별 읽기 전용 상세를 제공.
- 예상 규모: M.

### P3-11 [심각도 중간] `frontend/src/pages/Main.tsx:25`, `:99`, `:134` — 새로고침 후 선택 요청/결과가 사라짐

- 재현: 요청 목록에서 결과가 있는 요청 선택→새로고침.
- 기대/실제: 같은 요청 결과와 진행 화면을 유지해야 하나 접수 초기 화면으로 돌아가고 “분석 진행” heading 개수가 0이 된다. 저장 데이터는 목록에서 다시 선택하면 조회된다.
- 근거: 실제 reload 확인; requestId가 React 지역 상태에만 있고 URL/storage 복원 경로가 없다. 단순 데이터 유실이 아니라 탐색 상태 유실이다.
- 제안 수정: `/?request_id=...` 또는 요청 상세 라우트를 만들고 선택/뒤로가기/새로고침 모두 동일 ID로 복원.
- 예상 규모: S.

### P3-12 [심각도 낮음] 요청·학습 모바일 화면 — 긴 목록 우선 배치, 375px 넘침과 상태 줄바꿈

- 재현: 개발 요청이 약 25개 있는 상태에서 375×900 요청 접수/규칙 학습 화면 방문.
- 기대/실제: 핵심 접수 입력을 쉽게 찾아야 하나 “내 요청” 전체 목록이 위로 이동하여 textarea y=2176px에 있다. 상태가 “검토 대/기”, “배정 완/료”로 깨져 읽히며, 요청 페이지 scrollWidth=387/viewport=375, 학습 395/375로 가로 넘침이 있다.
- 근거: [17-request-375.png](17-request-375.png), [22-learning-375.png](22-learning-375.png). `main.css` 960px media에서 request-list에 order:-1. 정책·검토·업무·관찰·맵·모니터링은 시험 상태에서 375/520/960px 루트 가로 넘침 없음.
- 제안 수정: 모바일에서 입력/선택 결과를 먼저 두고 요청 목록을 접기 또는 별도 탭/페이지로 이동. 식별자는 축약+복사, 상태 배지는 nowrap, 긴 후보 ID에 overflow-wrap 및 grid min-width 적용.
- 예상 규모: M.

### P3-13 [심각도 낮음] `AppShell.tsx:15`, Review/Monitoring/Map 화면 — 사용자 문구에 내부 코드·영문 상태 노출

- 재현/실제: team_member/policy_editor로 로그인 시 역할 문자열 그대로 표시. 손상 PDF에 `unsupported_type`, 검토 이력 `request_info/reject`, 맵 상태 `published/validated`, 권한 오류 `Insufficient role`, 없는 요청 `Request not found`, 정책 검증 `SCHEMA_INVALID: Value error, thresholds must be between 0 and 1` 등이 표시됨.
- 근거: [04-damaged-file.png](04-damaged-file.png), [05-review-detail.png](05-review-detail.png), [19-policy-375.png](19-policy-375.png). roleLabel은 team_member 대신 assignee만 정의한다. 한글 자체의 인코딩 깨짐은 관찰하지 않았다.
- 제안 수정: 공통 한국어 역할·상태·오류 매핑을 사용하고 내부 코드는 펼쳐 보는 기술 상세에 배치. 손상 파일은 “PDF 형식을 읽을 수 없습니다. 다시 저장해 첨부하거나 제외하세요”처럼 복구 행동 제시.
- 예상 규모: S.

## 잘 동작한 흐름 / 범위와 제한

| 시험 | 실제 결과 |
| --- | --- |
| 텍스트+MD, PDF+DOCX | 실제 Jev LIVE 결과 저장, 업로드/분석 진행과 결과 카드·업무 분담 확인. PDF/DOCX는 저장소의 비민감 acceptance fixture 사용. |
| 손상 PDF | 파일 결정 대기로 멈추고 실패 파일명 표시. 명시적 제외 후 같은 요청의 새 revision, 실제 판단 저장. [04](04-damaged-file.png). |
| 재분석 | 새 run `run_30bdff58570e4c5084f884dedca70ac8` 생성, 이전 `run_2eebd094824843379d39348517a31ad2`와 버전/분류 비교 보존. |
| 검토 | 정보 요청·반려·승인·담당 조직 수정 승인 실제 저장. 두 탭 409 서버 거절 확인. AI 원안/수정 입력과 “단건 승인은 규칙 게시가 아님” 안내 표시. |
| 팀 업무 | 선행 막힘 원인·선행 제목·필터/빈 목록 확인. 신규 `task_fe064f0144ea4ff7a6f8052f426c2c6d`를 대기→진행→완료로 변경 성공. [13](13-task-blocked.png). |
| 관찰 | Flow 노드 클릭 Trace, 재생·속도 4×·전체 결과, 업무/서비스 Topology 전환 성공. 업무 완료와 실제 주관/협업 관계 표시. 순서 결함은 별도 기록. 모든 재생 프레임·부작용 DB 카운트를 전수 비교하지는 않음. |
| 모니터링 | KPI·SLO·지연/미수집·실패 목록·알림 빈 상태·수집기 상태 표시. 상태 필터 입력/적용 실행. 잘못된 Trace 동선·빈 날짜 예외는 별도 기록. 알림 발생 장애 주입은 수행하지 않음. |
| 판단 맵 | 요청 필터·입체/목록 전환·확대/축소/전체 보기·문서 노드 선택·연결 강조 확인. 목록 키보드 ArrowDown/Enter로 문서 근거 상세 선택. 작은 화면 목록 기본 보기 확인. 존재하지 않는 요청에 오류/다시 시도 표시. |
| 정책 | 임계값 1.5의 서버 검증 거절, 0.19 유효 검증, v7 게시, v6 기준 v8 되돌리기 및 diff 확인. risk_clear_max 0.2 복원. |
| 규칙 학습 | 집계 전 후보 0개 빈 상태→지지 1개 자료 부족 후보와 기존 지지 4개 후보 생성. 부족 확인+사유로 승인, v1/v2 섀도 검증·완료 처리·게시, 중단, v2→v1 복원 모두 UI 실행. 최종 활성 규칙 없음. [14](14-learning-insufficient.png), [21](21-learning-reverted.png). |
| ChatWidget | 열기/닫기, 결과에 따른 “검토가 필요해요” 아이콘/문구, Escape 후 런처 포커스 복귀 확인. 520/375px 전체화면, 960px 420×620 패널. 별도의 데스크톱 전체화면 토글은 없음. WebKit은 idle.webp와 375×812 전체화면 확인. [20](20-webkit-chat-375.png). |
| 접근 경계 | t-beta requester의 t-alpha `/api/requests/<id>` 직접 조회 404. t-beta operator로 t-alpha request_id를 지정한 실제 Observatory URL 접속도 “Request not found”; 타 tenant 결과 노출 없음. |
| 콘솔/네트워크 | 일반 탐색에서 수집한 pageerror는 없음; 모니터링 빈 날짜에서 1건 `Invalid time value`. 요청자 페이지 기록 401×2(로그인 전), 404×13(판단 대기 및 원문 거절), 검토 409 실측. 모든 페이지의 전체 네트워크를 영구 HAR로 수집한 것은 아니므로 전역 5xx 부재를 주장하지 않음. |

### 원문 권한에 따른 확인 제한 (제품 결함과 구분)

bootstrap은 모든 역할 계정에 `can_read_source=false`를 생성한다(`scripts/bootstrap_dev.py:43`). 요청자 본인 문서 근거를 눌러도 evidence API 404이며 “원문 위치를 확인할 수 없습니다”로 끝났다([25-source-denied.png](25-source-denied.png)). 검토자 화면은 요청 텍스트와 원안 값을 보여 주지만 근거 발췌는 권한 없음 안내만 나타나고, 운영자 판단 맵에는 원문 버튼이 없다. 권한을 임의 승격하지 않았으므로 권한 있는 계정의 PDF 페이지/DOCX 문단/MD 행 원문 이동·하이라이트는 이 실행에서 확인하지 못했다. 이 제한을 원문 조회 기능 자체의 고장으로 단정하지 않는다.

다만 접근 거절을 일반 위치 오류로 바꾸는 안내는 개선할 수 있다. [심각도 낮음] `Main.tsx:120` — 원문 권한 거절을 “위치 확인 불가”로 안내 — 기본 계정 evidence 404/상기 화면 — 권한 상태를 응답 계약으로 명확히 구분하고 사용자에게 권한 요청 경로 제시 — 예상 규모 S. **불확실:** 요청자 본인 원문에도 별도 권한이 필요한 것이 최종 제품 정책인지 문서만으로 확정하지 않았다.

## 추가 사용성 제안

- [심각도 낮음] 내 요청/검토 목록 — UUID만으로 요청 구별이 어려움 — [17-request-375.png](17-request-375.png)의 ID 목록 — 제목/첫 문장·접수 시각·최근 상태를 기본 표시하고 ID는 복사 가능한 보조 정보로 축약 — 예상 규모 S.
- [심각도 낮음] 입체 맵 전체 보기 — 1440px에서도 자동 fit 44%에서 카드 글자가 매우 작음 — [12-map-selected.png](12-map-selected.png) — 선택 노드 근처 확대, 읽기 가능한 최소 글자 크기, 범례/설명 겹침 방지 및 목록 보기 안내 강화 — 예상 규모 M.
- [심각도 낮음] 검토 수정 입력 — 분류/조직을 자유 텍스트로 입력하며 허용값을 모름 — [05-review-detail.png](05-review-detail.png) — enum/조직 선택 입력으로 바꾸고 미정 업무의 방법·산출물 수정 가능 여부/보완 필요 사유 안내 — 예상 규모 M. 시험 중 미정 DraftTask가 있는 요청의 수정 승인은 조직 오류로 거절됐으며, 정상 초안 요청은 수정 승인 성공했으므로 “조직명 입력 전부 실패”로 보고하지 않음.

## 환경 정리와 재현 데이터

- `make up`은 기존 `decision-chat-bot-neo4j-1`을 재사용. Docker Desktop을 실행하지 않았고 공유 Neo4j/7687은 종료하지 않았다.
- schema와 bootstrap 적용 후 `JEV_MODE=live` API 8191, t-alpha/t-beta 제한 worker, collector, watchdog, Vite 5391(`/api`→8191) 실행.
- 시험 후 Chromium/WebKit 및 Node REPL 종료. 직접 시작한 PID 1174/1197/1230/1272/1343/1362를 종료하고 8191/5391 LISTEN 없음·해당 PID 없음 확인. Neo4j는 실행 상태 유지.
- 최종 정책 v13, rules=[]; 시험 규칙 R-BROWSERP-01은 중단. risk_clear_max=0.2. v6과 달리 서버가 기본값인 learning 설정과 noul_uncertain_band를 명시한 필드가 추가되어 객체 바이트 동일 상태는 아님. 기존 의미의 임계값·활성 규칙은 복원했으며 과거 감사/버전은 삭제하지 않았다.
- 생성 요청: MD `req_f838e37f861d47be856085a935e2aa31`, PDF+DOCX `req_ec1bdfcb23e5465391a67fc4f5b864c1`, 손상 PDF `req_485a624bcf7341559510630a204a77ef`. API/worker 실연동 자료이며 재시험은 새 가상 요청 생성 권장.
- `git status`에서 다른 작업자의 `architecture-review.md`, `requirements-gap.md` 산출물이 관찰됐으나 읽거나 수정하지 않았다. 본 작업 제품 변경 없음.

### 최종 작업 트리 주의

보고서 링크 확인 시 공유 작업 트리에 다른 작업에서 작성된 백엔드/아키텍처 변경 16개와 새 auth 정책·통합 테스트·t22 산출물이 추가로 나타났다. 본 브라우저 API는 `--reload` 없이 시험 시작에 기동했으며 위 결과는 당시 실행 상태에 대한 증거다. 본 작업은 해당 제품 변경을 작성하거나 되돌리지 않았고, 변경 후 회귀 통과를 주장하지 않는다. 특히 원문 권한과 shadow 응답 관련 원인 코드 줄은 다른 작업의 수정으로 이동하거나 해결될 수 있으므로 최종 통합판에서 재확인이 필요하다.
