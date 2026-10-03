# P4 개선 후 최종 브라우저 재시험

- 대상: `/Users/psw/Projects/decision-chat-bot`, 시작·종료 HEAD **`de02e7b`**.
- 실행: 2026-10-04 01:06–01:20 KST, macOS / OrbStack 공유 Neo4j.
- 브라우저: 실제 Playwright **Chromium 153.0.8010.12 / WebKit 26.6**. 클릭·입력·파일 선택·키보드·새로고침으로 시험했다.
- 기준: PRD, TASK, spec 00–08 및 아키텍처/운영 문서 중 실행·권한·원문·업무·학습 계약, 기존 GATE_REPORT, P3 `REPORT.md`와 `FIX-REPORT.md`. 모든 문서의 모든 조항을 전수 검증한 결과는 아니다.
- 제품 코드·문서·설정 및 Git을 수정하지 않았다. 저장소 산출물은 이 보고서와 같은 폴더의 비민감 PNG뿐이다. 재현용 요청·계정·업무·규칙/정책 감사 기록은 개발 DB에 남겼다.

## 결론

**P3 13건 중 해결 11건, 부분 해결 2건(P3-12·13).** FIX-REPORT의 핵심 기능 수정은 재현됐지만, 모든 모바일 화면과 모든 한국어 문구가 해결됐다는 범위까지는 확인되지 않았다.

새로 확인한 결함은 **3건(P4-01~03, 모두 중간)**이며, 남은 반응형/한국어 문제는 **P4-04(중간), P4-05(낮음)**로 구체화했다. 권한 없는 검토 결정, 원문 필드 노출, tenant 간 요청 접근은 이번 표본에서 차단됐다. 전체 브라우저 품질 통과를 선언하지 않는다.

## 1. 이전 결함별 판정

C=Chromium, W=WebKit. 기존과 같은 사용자 행동을 새 가상 요청 또는 같은 기존 규칙 데이터에 적용했다. 화면과 API가 함께 필요한 항목은 실제 응답을 대조했다.

| 항목 | 판정 | 재수행 및 FIX-REPORT 대조 | 증거 |
| --- | --- | --- | --- |
| P3-01 로그인 행동 수단 | 해결 | C/W 쿠키 없는 `/`에 이메일·암호·로그인 버튼. 여섯 역할 UI 로그인 성공. 잘못된 암호 한국어 오류, 원래 URL 유지. | [로그인 차단 화면](15-login-throttled.png), [재로그인 화면](16-webkit-sse-logout.png) |
| P3-02 정보 요청→보완 | 해결 | C에서 정보 요청 사유/보완 필요/보완 제출 버튼 표시, 같은 요청 revision 1→2. W도 손상 파일 제외 후 revision 2→3 보완 제출. 요청 ID 유지, 다시 LIVE 판단 저장. | [보완 화면](11-info-request.png), 아래 재현 ID |
| P3-03 실패→Trace 라우트 | 해결 | 실제 stale revision 409가 journal/collector에 수집된 실패 행의 링크 클릭. C/W 모두 `/observatory?request_id=…`에서 실행 단계 표시, 라우트 404 없음. 종료 필터는 발생 시각을 포함하도록 다음 날로 설정. | [실패→Trace](28-monitor-trace-link.png) |
| P3-04 Flow 역순/관계 없음 | 해결 | C/W 모두 입력 정리→Jev 판단→근거 연결→업무 분해→규칙 적용→자동 배정 조건 검사→결과 저장→사람 검토. 연결·선행 표시, 재생/전체 결과 동작. C 4× 재생 및 업무/서비스 Topology 전환. | [Flow·Trace](12-flow-trace.png) |
| P3-05 ChatWidget 즉시 전달 | 해결 | C/W 접수 화면에서 위젯 입력→보내기 후 즉시 textarea에 전달, 위젯 닫힘. C 입력 포커스/전달 안내도 확인. 새로고침 불필요. | [즉시 전달](01-chat-handoff.png) |
| P3-06 검증 직렬화/기간 | 해결 | 기존 R-BROWSERP-01 검증을 C/W에서 조회. 새 후보 집계→자료 부족 승인→R-PFOUR-01 검증도 실제 실행: 날짜 범위·실패 0·“담당 조직 · 주관 → 현업 16건” 정상. 문자열 문자 인덱스 없음. 새 검증 실행은 C. | [기존 검증](17-validation-normalized.png), [새 검증](25-new-validation.png) |
| P3-07 409 안내 소실 | 해결 | C/W 각각 두 검토 탭에서 정보 요청 후 오래된 탭 반려→실제 409. 최신 검토 로드 뒤 안내가 계속 남고 결정 버튼 비활성. C 다른 흐름을 수행한 뒤에도 안내 유지 확인. | [검토 충돌](10-review-conflict.png) |
| P3-08 JSON 일반 편집 | 해결 | C 전체 선택→Backspace, W 빈 값 입력 시 빈 초안 유지. 이어 1.5 입력·서버 검증 한국어 거절, 0.2 재입력 가능. C 유효 검증/게시/되돌리기까지 성공. | [정책 편집](03-policy-edit.png), [설정 복원](26-policy-restored.png) |
| P3-09 모니터링 빈 날짜 | 해결 | C/W 시작 날짜 삭제→입력 오류 안내·적용 비활성, pageerror 없음. 동일 오류 유형이 **규칙 학습에는 남음(P4-02)**. | [날짜 오류 안내](02-monitoring-date.png) |
| P3-10 맵→검토 대상 선택 | 해결 | 담당 검토자로 C/W 문서 근거 노드→원문·검토 열기→해당 요청 검토 상세 자동 선택. 처리된 검토도 review_id로 읽기 전용 상세 표시. 담당 조직 밖 source_reader의 거절은 권한 계약상 정상. | [대상 검토 선택](09-map-review-link.png), [처리된 검토 원문](34-review-source-authorized.png) |
| P3-11 요청 새로고침 | 해결 | C 선택 요청 reload 후 동일 request_id/판단 결과·분석 진행 복원. W 보완 제출 후 reload에도 동일 request_id/분석 진행, 후속 결과 저장 확인. | [선택 결과](29-main-result-overflow.png), 재현 URL |
| P3-12 모바일 넘침/목록 우선 | **부분 해결** | 입력이 목록 앞에 있고 배지 줄바꿈은 개선. 학습 화면 375px 통과. 하지만 선택 결과가 있는 Main 375px에서 scrollWidth=385, Review는 C/W 모두 520·375px에서 540. FIX의 “10개 화면 넘침 없음”을 최종 데이터 상태에서는 재현하지 못함. | [요청 입력](19-owner-375.png), [결과 잘림](29-main-result-overflow.png), [검토 모바일](21-webkit-reviewer-375.png), P4-04 |
| P3-13 내부 코드/영문 | **부분 해결** | 역할·손상 파일·기존 검토 결정·없는 요청·정책 검증·맵 버전 상태는 한국어로 개선. 하지만 일반 결과의 ai_need/feasibility/lead_org, 검토 상세 question_id, 모니터링 영어 문장·알림 코드, 학습 수명의 approve/JSON은 여전히 펼침 없이 노출. | [손상 파일](31-webkit-damaged-file.png), [결과](29-main-result-overflow.png), [검토 상세](30-review-detail-overflow.png), P4-05 |

## 2. 보안 및 새 기능 판정

| 시험 | 판정과 실제 근거 |
| --- | --- |
| 담당 조직 외 검토자·team_member의 결정 | **서버/UI 결정 거절 통과.** 기존 검토자 화면을 열어 둔 브라우저의 실제 세션을 각 계정으로 바꾼 뒤 반려 버튼을 눌렀다. 두 경우 모두 실제 POST 403 및 “검토 권한이 없습니다” 표시. 별도 direct API도 403. [팀 담당자](20-decision-team_member.png), [다른 조직 검토자](20-decision-outsider_reviewer.png). 다만 권한 없는 상세 URL 진입 안내에는 P4-03의 소실 문제가 있다. |
| 원문 없는 운영자의 상세·뷰어·맵 | **통과.** 실제 브라우저 response JSON을 재귀 검사했다. 원문 키 `text/source_text/extracted_text/raw_text`, 시험 이메일·전화번호가 요청 상세, judgment, document, 맵 노드·경로 응답에 없었다. 원문 검사 리스너가 수집한 83개 200 JSON 응답 중 위 위반 0건(인증·목록 등도 포함한 수, 서로 다른 API 83종이라는 의미 아님). 뷰어는 위치·“원문 비공개/원문 열람 권한 없음”만 표시. [상세 뷰어](07-operator-no-source.png), [맵 뷰어](08-map-no-source.png). 원문 검사 응답은 변조하지 않았다. |
| 로그인 10회 실패→올바른 암호 | **통과.** `outsider_requester@t-beta.dev`의 별도 브라우저 로그인 폼에서 10회 401, 다음 올바른 암호도 429. “로그인 시도가 너무 많습니다. 잠시 후 다시 시도해 주세요.” [화면](15-login-throttled.png). 15분 창 만료 후 해제까지 기다린 시험은 하지 않았다. |
| 로그아웃 뒤 열린 SSE 화면 | **통과.** 같은 브라우저 컨텍스트의 다른 탭에서 UI 로그아웃. 기존 요청 SSE 화면은 C 약 11.5초, W 약 14.7초 뒤 결과 화면을 제거하고 같은 URL의 로그인 폼으로 전환. [C](33-chromium-sse-logout.png), [W](16-webkit-sse-logout.png). 로그아웃 이후 이벤트 부하를 별도로 주입한 처리량 시험은 아니다. |
| t-beta→t-alpha 직접 URL | **통과.** t-beta operator로 Main request_id, Observatory request_id+run_id, judgment-map request_id 직접 접근. 실제 404 및 한국어 거절, 타 tenant 결과 없음. [맵 거절](14-tenant-denied.png). |
| 원문 뷰어 4형식 | **통과, 증거 수준 구분.** 실제 LIVE 요청의 파서 결과에서 PDF 3단위, DOCX 6단위, MD 6단위, 채팅 7단위를 조회. 원래 LIVE 근거는 채팅 문장을 실제 클릭했고, 보완 실행의 PDF 근거도 W에서 실제 클릭했다. 네 형식을 모두 고정 확인할 때에만 판단 응답의 근거 목록을 실제 저장 unit_id로 고정하는 route 보조 시험을 사용했다. 원문/파서/문서 응답은 실제 서버 데이터이며 조작하지 않았다. PDF **3쪽**, DOCX **문단 5**, MD **5행**, 채팅 **문단 1·문장 5**에 aria-current=location과 강조 텍스트 확인. [PDF](05-viewer-pdf.png), [DOCX](05-viewer-docx.png), [MD](05-viewer-md.png), [채팅](05-viewer-chat.png). 모든 형식을 LIVE 모델이 자연스럽게 인용했다고 주장하지 않는다. |
| Main·Review·판단 맵의 원문 진입 | **통과.** Main·맵에서 원문 권한 있는 source_reader, Review에서 별도 p4_source_reviewer로 실제 저장 근거를 열었다. 기본 reviewer/operator는 위치만 표시. Escape로 닫기 및 원래 버튼 포커스 복귀 확인. [Review 권한 있음](34-review-source-authorized.png), [권한 없음](06-review-source-denied.png), [W 실제 원문](27-webkit-live-source.png). |
| 맵 크게 보기·버전·확대율 | **통과(C).** R-BROWSERP-01 실제 저장 관계 전체 22노드/20연결, v1 9/8, v2 13/12. 탭 필터로 수 변경, 확대 44%→56%, 크게 보기 진입·Escape 복귀. [크게 보기](18-map-expanded.png). W 목록 및 원문/검토 이동·키보드는 별도 확인. |
| 업무 block_reasons·409 | **부분 해결.** 실제 `feasibility_unresolved` Task를 생성했고 서버 진행 시도는 409로 차단. UI의 이유 표시는 **실패(P4-01)**. 별도의 정상 업무를 두 탭에서 시작하면 오래된 탭 409 안내·최신 상태 재조회는 정상. [업무 충돌](22-task-conflict.png). |
| 가상 민감값·LIVE 판단·외부 마스킹 | **기능 확인, 외부 payload 자체는 미수집.** 가상 `demo.p4@example.invalid`, `010-0000-1234` 포함 문장+3종 첨부가 실제 LIVE 판단으로 저장됐다(정보 부족/검토 전환도 실제 판단값으로 보존). 원문 권한 있는 뷰어에는 대체 토큰이 아닌 원래 문자가 표시됐다. 이메일은 문장 파서가 마침표에서 세 단위로 나눠 표시하므로 하나의 연속 문자열로는 보이지 않는다. Trace에는 `mask_input_chars=3380`, `mask_output_chars=3420`, `mask_count=16`, `mask_calls=74`만 표시되고 토큰 표·외부 전송본문은 없었다. [원문](04-live-chat-viewer.png), [Trace](12-flow-trace.png). 마스킹 탐지율이나 모든 외부 호출 본문을 검증한 것으로 확대하지 않는다. |

## 3. 새 결함과 남은 문제

### P4-01 [심각도 중간] `frontend/src/pages/Tasks.tsx:11`, `frontend/src/api/tasks.ts:2` — 업무 시작 차단 이유 누락 — 예상 규모 S

- **문제:** 서버가 `block_reasons`에 개발 가능성 미해결을 저장해도 목록은 “막힘 · 전제 확인 필요”, 상세는 빈 선행/후행 항목만 보여 준다. 사용자가 무엇을 해결해야 하는지 알 수 없다.
- **재현:** 아래 요청 A의 보완 실행을 검토자가 승인 → 팀 담당자 `/tasks` → `task_8f9892a1fb5c450ba5530a9fa3863339` 선택.
- **근거:** 실제 API `status="막힘"`, `block_reasons=["feasibility_unresolved"]`, `predecessor_tasks=[]`. [상세 화면](23-block-reason-missing.png)에 개발 가능성 사유가 없다. direct transition `막힘→진행`은 409 “선행 업무 완료와 본업무 전제 해결 후 진행할 수 있습니다”. Tasks 타입에 block_reasons가 없고 렌더는 `predecessor_tasks… || reason || '전제 확인 필요'`만 사용한다. 실행 계약의 차단 조건 저장·확인과 화면 표시가 이어지지 않는다.
- **제안 수정:** Task DTO에 `block_reasons: string[]` 추가, 각 코드를 “개발 가능성 또는 수행 전제가 아직 해결되지 않았습니다” 등 한국어로 목록·상세에 표시. 서버가 확인한 시작 가능 여부를 별도로 응답해 차단 해소 후 재조회/진행 동선을 제공. 409 이후에도 최신 차단 이유를 유지.

### P4-02 [심각도 중간] `frontend/src/pages/learning/Actions.tsx:75` — 검증 날짜를 비우면 처리되지 않은 예외 — 예상 규모 S

- **재현:** rule_admin → 후보 집계·승인으로 검증 중 버전 생성 → 검증 시작 날짜 삭제 → 활성 상태인 “검증 실행” 클릭.
- **실제:** API 검증 요청으로 진행하지 못하고 `Invalid time value` pageerror 발생. 입력 오류 안내나 버튼 차단 없음. Chromium의 한 번 클릭에서 동일 오류 이벤트 2건을 수집했다. 날짜를 정상 값으로 복원하면 검증 성공.
- **근거:** [빈 날짜 화면](24-learning-empty-date.png). onClick의 `new Date(from).toISOString()`/`new Date(to).toISOString()`에 유효성 검사가 없다. 모니터링 P3-09와 같은 오류가 다른 화면에 남아 있다.
- **제안 수정:** 필수 날짜·유효성·시작≤끝을 공통 검증하고 입력 가까이에 한국어 오류 표시, 문제가 있으면 실행 버튼 비활성. ISO 변환은 검증 이후 수행하고 실패를 UI에서 처리.

### P4-03 [심각도 중간] `frontend/src/pages/Review.tsx:15–16,20–22` — 권한 없는 검토 상세 오류가 목록 응답에 의해 지워짐 — 예상 규모 S

- **재현:** team_member로 `/review?review_id=rvw_473ae391e3c44669930c75751112ada3` 직접 접근. 상세 404와 대기 목록 200이 경합하면 오류 없이 “대기 0건 / 왼쪽 목록에서 요청을 선택하세요”만 남는다.
- **재확인:** 실제 목록 응답을 route.fetch로 받은 뒤 전달만 800ms 지연했다(상태/본문은 그대로). 상세의 “검토를 찾을 수 없습니다.”가 나타난 뒤 목록 완료 시 사라짐을 DOM으로 확인. [최종 화면](32-review-denial-disappears.png). 지연 없는 최초 team_member 탐색에서도 같은 최종 화면을 관찰했다.
- **원인:** `open()`이 공유 error를 설정하지만 `refresh()` 성공이 무조건 `setError('')`한다. P3-07의 결정 notice 소실은 해결됐으나 독립적인 상세 오류와 목록 오류가 여전히 같은 상태를 공유한다.
- **제안 수정:** listError/detailError를 분리하거나 대상 요청별 오류 소유권을 두어 목록 성공이 상세 권한/없는 대상 오류를 지우지 못하게 한다. 재시도/목록 돌아가기 동선을 제공.
- **영향 제한:** 서버의 권한 우회는 관찰하지 않았다. 실제 결정 POST 403 및 그 결정 안내는 유지됐다.

### P4-04 [심각도 중간] `frontend/src/pages/main/main.css:1`, `frontend/src/pages/review/review.css:1` — 선택 결과·검토 상세의 모바일 가로 넘침 — 예상 규모 M

- **재현:** Main에서 두 실행이 있는 요청 A 선택 후 375×900. Review에서 상세가 선택된 상태로 520×900/375×900.
- **근거:** Main Chromium `scrollWidth=385 > 375`. Review Chromium/WebKit 모두 `540 > 520`, `540 > 375`. [Main 결과 잘림](29-main-result-overflow.png), [C 검토](19-reviewer-375.png), [W 검토](21-webkit-reviewer-375.png), [검토 상세](30-review-detail-overflow.png).
- **원인 추정:** 결과 카드의 grid 자식 min-content, 긴 UUID/JSON·근거 버튼, 검토 목록 strong·상세 식별자·입력에 줄바꿈/최소 너비 제한 부족. CSS와 실제 경계 측정이 이를 뒷받침하지만 모든 넘침 기여 요소를 각각 격리하지 않았으므로 정확한 최소 수정 셀렉터는 **불확실**.
- **제안 수정:** 결과/검토 grid 자식 `min-width:0`, 긴 식별자·원문 위치·JSON에 `overflow-wrap:anywhere`, 폼 요소 `max-width:100%`; 긴 기술 정보는 접기·복사로 분리. 초기 빈 화면뿐 아니라 선택 결과·이전 실행 비교·완료 검토·긴 후보 데이터 상태로 375/520px 회귀.
- **P3 대조:** 요청 입력 우선 배치와 학습 화면 넘침 수정은 유지되므로 P3-12는 부분 해결이다.

### P4-05 [심각도 낮음] `frontend/src/pages/Main.tsx:158–161`, `Review.tsx:29`, `Monitoring.tsx:69–73`, 학습 수명 화면 — 일반 화면의 내부 코드 잔존 — 예상 규모 S

- **재현/근거:** Main 검토 사유에 `Choice confidence 미충족: ai_need/feasibility/lead_org`, Review 신뢰 신호에 원형 question_id, 모니터링에 `Less than 30 days of complete observation` 및 `worker_stopped/api_stopped`, 신규 규칙 승인 수명에 `approve`와 조건 JSON이 직접 노출된다. [Main](29-main-result-overflow.png), [Review](30-review-detail-overflow.png), [모니터링](19-operator-375.png). 일반 문구의 한글 인코딩 깨짐은 없었다.
- **문제:** 기존 지적의 역할·상태·대표 오류 번역은 개선됐지만, 사용자 화면에 내부 식별자/운영 코드가 남아 P3-13 전체 해결로 보기 어렵다. Trace의 명시적인 기술 JSON 표시는 이 결함 범위에 넣지 않았다.
- **제안 수정:** 공통 question/reason/event/action 한국어 매핑을 결과·검토·학습·모니터링에 일관되게 적용하고 원형 코드/조건 JSON은 접힌 “기술 상세”로 옮긴다.

## 4. 역할·반응형·키보드 회귀

### 역할별 정상 동작

| 역할 | 실제 수행한 주요 흐름 |
| --- | --- |
| 요청자 | C/W UI 로그인, 채팅 즉시 전달, 키보드 접수(C), 텍스트+PDF/DOCX/MD LIVE 판단, 손상 PDF 한국어 거절→명시 제외(W), 정보 보완→같은 요청 새 revision(C/W), 선택 요청 새로고침 복원 |
| 검토자 | 담당 검토 상세/원안·수정값, 정보 요청(C/W), 오래된 반려 409(C/W), 승인·담당 조직 수정 승인(C), 처리된 검토 읽기 전용, 원문 권한별 표시, 맵 딥링크(C/W) |
| 팀 담당자 | 팀/업무 목록·상세, 신규 정상 업무 대기→진행→완료, 두 탭 전이 충돌 409 안내, 별도 차단 업무 서버 시작 거절; 구체적 차단 사유 UI는 P4-01 |
| 운영자 | 모니터링·필터 오류·실패 Trace 링크(C/W), 단계 순서·재생·전체 결과(C/W), C 업무/서비스 Topology, 원문 없는 메타데이터/근거 위치 조회, t-beta 접근 거절 |
| 정책 편집자 | C/W JSON 중간 빈 초안 유지·잘못된 임계값 한국어 검증, C 0.19 게시 후 0.2 되돌리기, 활성 규칙 없음으로 종료 |
| 규칙 관리자 | 기존 후보/근거·버전·검증 표시(C/W), 신규 후보 집계→자료 부족 확인+사유→승인→검증→검증 완료→게시→중단(C), 새 검증의 정상 DTO와 표본 수 표시. 새 규칙의 두 번째 버전 생성·되돌리기는 이번 재시험에서 수행하지 않음 |

### 실측 scrollWidth (px)

모든 화면 높이 900. 열 값은 960 / 520 / 375px viewport 순서다. Main의 C는 요청 A(이전 실행 비교 있음), W는 요청 B(단일 실행)로 데이터 상태가 다르므로 브라우저 간 우열 비교가 아니다.

| 화면 | Chromium | WebKit |
| --- | --- | --- |
| Main 선택 결과 | 960 / 520 / **385** | 960 / 520 / 375 |
| Review 선택 상세 | 960 / **540** / **540** | 960 / **540** / **540** |
| 팀 업무 | 960 / 520 / 375 | 960 / 520 / 375 |
| 모니터링 | 960 / 520 / 375 | 960 / 520 / 375 |
| 정책 | 960 / 520 / 375 | 960 / 520 / 375 |
| 학습 후보 선택 | 960 / 520 / 375 | 960 / 520 / 375 |

- C/W 채팅: Enter 열기, Shift+Tab으로 보내기 이동, Escape 닫기, 런처 포커스 복귀 확인. 375px 전체 화면 표시.
- 원문 뷰어: 근거 버튼 Enter, 단일 위치 강조, Escape 및 버튼 포커스 복귀. W 맵 목록은 ArrowDown으로 다른 계층 노드로 이동하고 Enter 상세 선택. ArrowRight는 같은 계층에 노드가 하나일 때 제자리 유지가 정상이다.
- 맵 확대·버전·전체/크게 보기와 선택 경로는 C의 실제 관계로 확인했다. 모든 UI의 자동 axe 검사나 모든 탭 순서를 전수 수행한 것은 아니다.
- 새로고침 영속성은 Main 선택 요청과 서버 저장 결과를 확인했다. 서버 재시작 전후 전체 데이터 스냅샷 비교는 이번 브라우저 재시험 범위에서 수행하지 않았다.

### 콘솔·HTTP 관찰

일반 흐름에서 확인한 유일한 pageerror 유형은 P4-02 `Invalid time value`다(수집 이벤트 2건). 인증 전/세션 만료 401, 권한 403/404, 판단 저장 대기 중 judgment 404, 의도한 오래된 검토·업무·revision의 409, 로그인 제한 429는 정상 또는 명시적인 오류 경로로 분리했다. 관찰 페이지의 응답 리스너에서 5xx는 없었다. 모든 임시 탭·APIRequestContext 요청의 전역 HAR를 저장하지 않았으므로 전체 서비스의 4xx/5xx 부재를 주장하지 않는다.

## 5. 재현 데이터·방법·정리

### 새 데이터

- **요청 A:** `req_e83022236db54a85950d9c5de402171d` — 원문/가상 연락처·3형식 첨부, 최초 run `run_449d755734ca404a82704671089dc6eb`, 최초 revision `rev_86d49b4ff9f54533bc324d73c952832c`, 정보 요청 review `rvw_473ae391e3c44669930c75751112ada3`. 보완 run `run_021dac6abc95436f9a5520943a02d493`, 승인 후 막힘 업무 `task_8f9892a1fb5c450ba5530a9fa3863339`.
- **요청 B:** `req_95970208694043bb9ebf31e345173b2a` — W 실제 요청 접수, 구체적인 회의실 예약 웹페이지 요구. C 담당 조직 수정 승인. 정상 업무 `task_b8ae2cede8ba48a6aeeee7efd7bc5c31` 최종 완료.
- **요청 C:** `req_0c11c90775ed4e969c5bdce809e83d80` — W 손상 PDF 제외→LIVE 판단→정보 요청→보완 revision 3. 최종 run `run_b510088fd25c4b40a43460001b04172b`, 검토 대기.
- **새 규칙:** `R-PFOUR-01@1`, 후보 `cand_7387355e065b553b253a070a`, 검증 `val_f29fe358038c4a68be5eba2c91513f45`, 31표본·변경 16·실패 0·부작용 0, 최종 상태 `stopped`.
- bootstrap과 기존 acceptance provision으로 t-alpha/t-beta의 테스트용 outsider/source_reader 등을 준비했다. 원문 있는 검토 화면에는 별도 `p4_source_reviewer@t-alpha.dev`(동 tenant 3조직 reviewer, can_read_source=true)를 추가했다. 일반 operator/reviewer의 원문 권한을 승격하지 않았다. 가상 로그인 제한 계정은 `outsider_requester@t-beta.dev`다.

### 실행 방법

OrbStack context `orbstack`, 기존 `decision-chat-bot-neo4j-1` 재사용. schema/bootstrap 뒤 API `127.0.0.1:8491`, worker `--tenant t-alpha --tenant t-beta`, collector, watchdog을 직접 시작했다. 모두 `JEV_MODE=live`, 공통 절대 `DATA_DIR=/Users/psw/Projects/decision-chat-bot/.data`. Vite는 프로그램 방식 createServer로 `5691`, `/api→8491`을 지정했고 저장소 설정을 바꾸지 않았다. Playwright 조작기는 임시 localhost 포트 15991을 사용했다.

외부 Jev 전송에는 비민감 가상 문장·저장소 fixture만 사용했다. 스크린샷은 그 가상 데이터와 로컬 개발 역할/ID만 포함한다. 키·쿠키·실제 개인정보·모델 전송본문은 보고서/이미지에 저장하지 않았다.

### 종료 확인

- Chromium·WebKit 종료 후 직접 시작한 API **5884**, worker **5885**, collector **5886**, watchdog **5887**, Vite **5888**, Playwright 조작기 **6914** 종료.
- `lsof` 확인: **8491/5691/15991 LISTEN 없음**. 공유 Neo4j는 **Up / healthy**, 7687 유지. Docker Desktop을 실행하거나 공유 Neo4j를 정지하지 않았다.
- 정책은 v13에서 시험을 시작해 새 규칙 게시/중단 v14/v15, 임계값 게시/되돌리기 v16/v17을 남겼다. 최종 **v17**, `risk_clear_max=0.2`, `auto_assign=false`, `rules=[]`, `masking.enabled=true`.
- v13의 기존 설정값은 유지됐지만 최신 스키마의 기본 `masking`과 `retention` 필드가 직렬화되어 추가됐으므로 저장 객체가 v13과 바이트 동일하다고 주장하지 않는다. 과거 감사·버전·가상 요청은 삭제하지 않았다.
- 최종 Git 변경은 `artifacts/review/browser-retest/`뿐이다. 수정 제안은 구현하지 않았다.
