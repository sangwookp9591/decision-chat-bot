# VERIFY-P7 — 체감 속도와 브라우저 회귀 재시험

- 일시: 2026-10-04 KST. 기준 커밋 `1495d9d`, 시험 시작 시 clean worktree.
- **판정: 점진 표시는 30/30 정상이나 전체 회귀는 통과 선언 불가.** 수정 승인 후 업무 시작 차단(높음), 정책 입력 덮어쓰기·모니터링 지연·다른 탭 신규 목록 미갱신(중간)을 확인했다.
- P7은 제품 코드·문서·설정을 수정하지 않았다. 지정 보고서 및 비민감 PNG/WebM만 생성했다. 11:28경 관측한 backend 파일 변경은 코디네이터가 배정한 FIX-BLOCK 작업자의 변경이다. 이 보고서의 소스 줄은 **1495d9d 기준**이며, API/worker는 reload 없이 시작한 기존 코드로 시험했다. 후속 수정의 검증 결과로 읽으면 안 된다.
- 기준: PRD, TASK, docs/spec/00–08, architecture의 EXECUTION_CONTRACT·IMPLEMENTATION·DATA_MODEL·PROGRESSIVE_RESULTS·EVENTS·AUTH·REVIEW_ASSIGN·MONITORING, operations, final/GATE_REPORT. 외부 완료 조건의 반복 나열은 제외했다.

## 환경과 방법

OrbStack의 공유 Neo4j 7687과 Redis 6379를 사용했다. schema/bootstrap 성공, API 8791·8792는 동일 `REDIS_URL=redis://127.0.0.1:6379/0`, `JEV_MODE=live`, 절대 `DATA_DIR=<repo>/.data`; worker는 `--tenant t-alpha --tenant t-beta`, collector와 watchdog을 기동했다. Vite 5991→8791, 6091→8792는 기존 vite.e2e.config.ts와 별도 임시 cacheDir를 사용했다. Docker Desktop 및 Neo4j 정지는 하지 않았다. Redis 일시 정지는 코디네이터가 “다른 작업자가 없음”을 확인해 허용한 뒤 수행했다.

Chromium **153.0.8010.12**, WebKit **26.6**을 저장소의 설치된 Playwright로 실행했다. Ego Chromium에서도 실제 로그인과 UI 구조를 확인했다. 속도 표본은 1440×1100 화면, 실제 UI 로그인·textarea 입력·첨부 선택·제출 버튼 클릭으로 생성했다. API나 SSE 응답을 mock하지 않았다. 비민감 회의실·공지 검색·문의 분류·시설 점검·재고 조회 문장 5종에 시험 번호를 붙였다. 첨부는 기존 비민감 acceptance fixtures의 MD 2회, DOCX 2회, PDF 1회/브라우저다.

문서 capture click 이벤트의 `performance.now()`를 t0로 하고 MutationObserver로 최초 DOM 표시를 기록했다. 각 요청 전 `/`로 이동하여 이전 결과를 제거했다. 잠정=`.provisional-badge`, 근거=`.provisional-count`, 업무=잠정 영역의 “업무 N건 준비됨”, 최종=`.result-summary h2`의 “판단 결과”다. 따라서 근거/업무 지표는 **건수 준비 표시**이며 실제 근거 원문·업무 상세는 최종 저장 후 열린다. paint 완료나 사람이 인지한 시점을 직접 측정한 것은 아니다. 공식 SLO의 서버 수신→커밋과도 시작·끝점이 다르다.

각 브라우저에서 텍스트 10건+첨부 5건을 순차 실행했다. p50/p95는 정렬된 값의 `ceil(p×n)`번째 nearest-rank, 소수 첫째 자리 ms다. 작은 표본이므로 n=10/5의 p95는 최대값이며 운영 성능 보증이 아니다. 최초 Chromium 표본의 브라우저/API 가열 비용도 제거하지 않았다. 공유 DB·metrics를 비우지 않아 콜드 라우트의 브라우저 간 차이를 엔진 자체 차이로 단정할 수 없다.

## 체감 속도

| 브라우저 | 입력(n) | 단계 | p50 ms | p95 ms |
|---|---|---|---:|---:|
| chromium | 텍스트(10) | 낙관적 요청 카드 | 2.8 | 3.8 |
| chromium | 텍스트(10) | 단계 타임라인 | 102.8 | 531.5 |
| chromium | 텍스트(10) | 잠정 판단 | 608.5 | 1589.7 |
| chromium | 텍스트(10) | 근거 준비 표시 | 1388.1 | 2933.3 |
| chromium | 텍스트(10) | 업무 준비 표시 | 907.0 | 1903.7 |
| chromium | 텍스트(10) | 최종 결과 | 1534.5 | 3510.2 |
| chromium | 첨부(5) | 낙관적 요청 카드 | 2.8 | 3.3 |
| chromium | 첨부(5) | 단계 타임라인 | 367.1 | 433.5 |
| chromium | 첨부(5) | 잠정 판단 | 741.5 | 936.4 |
| chromium | 첨부(5) | 근거 준비 표시 | 2184.7 | 2868.7 |
| chromium | 첨부(5) | 업무 준비 표시 | 1043.2 | 1419.1 |
| chromium | 첨부(5) | 최종 결과 | 2455.2 | 2919.9 |
| webkit | 텍스트(10) | 낙관적 요청 카드 | 3.0 | 6.0 |
| webkit | 텍스트(10) | 단계 타임라인 | 88.0 | 103.0 |
| webkit | 텍스트(10) | 잠정 판단 | 492.0 | 618.0 |
| webkit | 텍스트(10) | 근거 준비 표시 | 1444.0 | 1905.0 |
| webkit | 텍스트(10) | 업무 준비 표시 | 840.0 | 1153.0 |
| webkit | 텍스트(10) | 최종 결과 | 1590.0 | 2065.0 |
| webkit | 첨부(5) | 낙관적 요청 카드 | 3.0 | 4.0 |
| webkit | 첨부(5) | 단계 타임라인 | 320.0 | 378.0 |
| webkit | 첨부(5) | 잠정 판단 | 720.0 | 826.0 |
| webkit | 첨부(5) | 근거 준비 표시 | 2118.0 | 2577.0 |
| webkit | 첨부(5) | 업무 준비 표시 | 1034.0 | 1145.0 |
| webkit | 첨부(5) | 최종 결과 | 2378.0 | 2835.0 |

- 30/30 최종 결과 성공, 30/30 잠정 판단·근거 준비·업무 준비가 최종 결과 전에 관측됐다. 잠정 상태 관찰마다 검토·배정 버튼 disabled=true였다.
- 낙관적 카드는 2–6ms 수준이며 서버 접수 전에도 화면 피드백이 있어 제출 후 빈 화면은 없었다. 타임라인 p95 최대 531.5ms, 잠정 p95 최대 1,589.7ms.
- 스켈레톤 최초 표시는 잠정 카드 발생 뒤 최소 **200.9ms**였다. 별도 prefetch된 규칙 학습 이동에서 실제 LoadingState 지속 Chromium 75.4ms, WebKit 80ms 동안 spinner/skeleton 삽입 0건: 200ms 미만 깜빡임 방지 확인.
- 실제 POST를 6.2초 지연시킨 시험에서 “평소보다 오래 걸리고 있어요”를 Chromium 5,455ms, WebKit 5,433ms에 확인했다(클릭 반환 후 assertion 관찰 시각의 상한). 이후 두 브라우저 모두 live 최종 결과까지 성공했다.
- 잠정→최종 교체는 콘텐츠 위치를 바꾼다. Chromium의 요청별 `hadRecentInput=false` layout-shift 합은 **0.01349–0.03348**이었다. 정식 CLS의 session-window 값은 아니며 WebKit은 해당 API 미지원으로 미측정이다. 아래 F5 참조.
- [점진 표시 영상](P7-progressive.webm), [잠정 카드](P7-provisional.png), [Chromium 지연 안내](P7-chromium-slow.png), [WebKit 지연 안내](P7-webkit-slow.png).

## 다중 인스턴스 SSE / Redis 폴백

동일 세션의 탭 A는 5991/API8791, B는 6091/API8792였다. 접수 중 worker를 잠시 SIGSTOP하여 B에 동일 request_id를 선택하고 연결을 준비한 뒤 SIGCONT했다. 두 탭은 새로고침 없이 진행·잠정·근거·업무·최종 결과를 표시했다. 아래 수치는 worker 재개→양쪽 최종 heading 확인이며 전송 SLO 측정으로 대체하지 않는다.

| 상태 | request_id | 양쪽 최종까지 ms | B 이벤트 수 | partial A→B 차이 ms | final A→B 차이 ms | 판정 |
|---|---|---:|---:|---:|---:|---|
| healthy | `req_0032a8cd689c4e2aa652449db7850190` | 1813 | 18 | -1 | -3 | 통과 |
| redis-stopped | `req_584cec85d32e44569efcf42ff2c000f6` | 1809 | 18 | -3 | -2 | 통과 |
| recovered | `req_aa2234c81e4b4afb99c5cab5e5cdf6e3` | 1819 | 18 | -111 | 0 | 통과 |

음수는 B가 먼저 수신했음을 뜻한다. 두 탭의 동일 이벤트 seq가 대응하고, B의 핵심 네 이벤트는 각 1회였다. 18건에는 request.received와 run.step도 포함된다. `docker --context orbstack compose stop redis` 동안 실제 live 실행이 완료됐고, `compose start redis` 후 다음 실행도 정상 전달됐다. 종료 상태 healthy 확인은 아래 정리 기록 참조. 각 상태 1건이므로 장시간 장애/대규모 연결의 보증은 아니다.

**별도 실패:** 아무 요청도 선택하지 않은 탭의 새 요청 목록은 실시간 갱신되지 않는다. 충분히 로딩된 B에서 신규 요청 최종 완료 후 추가 5.5초 기다려도 목록에 없고 새로고침하면 나타났다(F4). SSE 전송 정상과 목록 갱신 실패를 구분한다.

## 콜드 dev 서버 첫 진입

매회 비어 있는 cacheDir, 새 Vite 프로세스(6191→8791), 새 브라우저 context, 실제 로그인 후 직행했다. 서버 ready 이후 `page.goto` 직전→해당 h1 표시 시간이며 DB/OS 캐시는 초기화하지 않았다. 제목 자체가 먼저 나오는 판단 맵/규칙 학습 수치는 모든 데이터 영역 완료 시간이 아니다. 별도 프로세스 ready까지는 236–303ms였다.

| 브라우저 | 화면 | 1회 ms | 2회 ms | 3회 ms |
|---|---|---:|---:|---:|
| chromium | 모니터링 | 2247 | 4678 | 3676 |
| chromium | 판단 맵 | 469 | 388 | 660 |
| chromium | 규칙 학습 | 386 | 402 | 383 |
| webkit | 모니터링 | 7795 | 7824 | 8840 |
| webkit | 판단 맵 | 507 | 463 | 486 |
| webkit | 규칙 학습 | 486 | 500 | 476 |

모니터링의 5초 초과가 재현됐다. 별도 Chromium 진단에서 alerts 40.6ms, summary 1,837.8ms, failures 1,837.9ms, slo 2,290.6ms였으며 화면은 allSettled 전체 종료를 기다렸다. Vite만의 문제로 볼 수 없고 집계 경로와 화면의 일괄 대기 모두 개선 대상이다. 이 진단 한 번은 콜드 표와 별도 실행이다.

## 회귀 판정

| 항목 | Chromium | WebKit | 근거 / 범위 |
|---|---|---|---|
| 요청자: 텍스트·PDF·DOCX·MD 접수 | 통과 | 통과 | 각 15건, mode=live, 최종 DOM 및 4종 SSE 확인 |
| 검토자: 수정 승인·원안 보존 | 저장 통과, 후속 업무 실패 | 저장 통과, 후속 업무 실패 | feasibility 최종값=가능, 원 Judgment=정보 부족; F1 |
| 팀 담당자: 업무 전이 | 실패 | 실패 | 수정 승인으로 만든 실제 업무 3건 모두 feasibility_unresolved; 진행 버튼 비활성 |
| 운영자: 관찰 재생 | 통과 | 통과 | 8개 노드, 재생→전체 결과; 전후 요청 업무 API 결과 동일 |
| 정책 편집자: 검증·게시·되돌리기 | 조건부 통과 | 조건부 통과 | 화면 안정 후 잘못된 임계값 거절, 동일 설정 게시, 원 버전 기준 새 버전 복원 성공; 즉시 편집은 F2 |
| 규칙 관리자: 학습 조회 | 통과 | 통과 | 수정 기록·후보 4건·규칙 구분 및 “모델 재학습 없음” 표시 |
| labeler: 확정·보류·불일치 | 통과 | 통과 | tuning pharma-001을 두 역할이 서로 다른 유효 값으로 확정, consensus_required 표시; 다음 표본 보류 저장 |
| 원문 권한 없음 | 통과 | 통과 | reviewer@t-alpha, chat 단위 3개 위치 유지·본문 누락, 원문 비공개 표시 |
| 원문 권한 있음 | 통과 | 통과 | 기존 비민감 t-ux2 source_reader, booking-spec.pdf 3개 단위·anchor 1개·본문 표시; 권한 변경/새 DB fixture 없음 |
| 다른 tenant 직접 조회 | 통과 | 통과 | t-beta requester로 t-alpha 요청 및 revision document 모두 404 |
| 375px 가로 넘침 | 통과 | 통과 | Main 결과, Review 상세, Tasks, Monitoring, Observatory, JudgmentMap, Policy, Learning, Evaluation 각 9화면 scrollWidth=375 |
| 예상 밖 콘솔/HTTP | 측정 표본에서 없음 | 측정 표본에서 없음 | 30건 pageerror=0, 5xx=0; 각 브라우저 auth/me 401 2건(로그인 전), 판단 저장 전 judgment 404 15건은 의도된 상태 |
| 한국어 문구 | 일부 미흡 | 일부 미흡 | 정책 필드·평가 합의 상태의 내부 코드 노출, F6 |

초기 시험 harness의 broad `role=status` 대기 때문에 검토 응답 저장 전에 조회한 사례와, 인용 없는 결과에서 “근거 열기”를 찾은 timeout은 제품 결함으로 집계하지 않았다. 저장 완료 문구와 실제 인용이 있는 요청으로 재시험했다. WebKit 라벨 초기 재시험은 reviewer의 기존 표와 같은 값이 되어 불일치가 사라졌으므로 서로 다른 유효 라벨로 다시 수행했다. 정책 즉시 편집 실패는 별도 3회 재현으로 제품 결함임을 확인했다.

상기 401/404는 속도 표본 전부에서 수집했다. 회귀는 pageerror 및 실패 요청을 집중 확인했지만 모든 탭의 console warning 전량을 보관하지 않았으므로 전체 브라우저 콘솔 무경고라고 주장하지 않는다. 원문 허용의 기존 PDF는 비민감 회의실 fixture이며, 다른 모든 신규 판단 요청은 t-alpha에서 만들었다. t-beta는 차단 시험에만 사용했다.

## 신규 결함

### F1 — [심각도 높음] `backend/jevtriage/review/service.py:180`, `backend/jevtriage/tasks/service.py:34` / 수정 승인 후 업무 상세

- **문제:** 사람이 개발 가능성을 “가능”으로 확정해도 생성 업무가 `feasibility_unresolved`로 막혀 시작할 수 없다. 화면에 차단 해결 방법도 없다.
- **근거/재현:** requester의 가상 화면 요청 → reviewer가 `정보 부족→가능` 수정 승인 → 저장 완료 및 `/reviews/{id}` 최종값 확인 → team_member의 업무 상세에서 진행 비활성. 3개 실제 업무에서 동일했다. assignment는 1495d9d service.py:180–185의 원 Judgment.feasibility를 읽으며 210–211에서 사유를 저장한다. tasks/service.py:34–38은 선행 사유만 제거하고 남은 feasibility 사유로 409를 유지한다. [화면](P7-approved-task-blocked.png).
- **제안 수정:** 검토 배정 트랜잭션에 잠금된 최종 검토 분류를 전달하고, 수정 승인 결과에 따라 feasibility 차단을 계산한다. 기존 차단 업무도 명시적 권한·감사·최종 검토 연결을 통해 해소하도록 하되 다른 risk/선행 차단은 유지한다. 정보 부족→가능 및 가능→불가의 양방향 회귀와 업무 전이를 검증한다.
- **예상 규모:** M. 코디네이터가 FIX-BLOCK을 배정했으나 본 보고서는 그 수정의 재시험 결과가 아니다.

| request | review | task | 원안 | 최종 검토 | 업무 사유 |
|---|---|---|---|---|---|
| `req_ec2eb62a189f415297801cdfb6419714` | `rvw_efa348dabad343b5806ae0068e194fdd` | `task_fd995b48e8b94b3ba7040c154e1fe2e0` | 정보 부족 | 가능 | `feasibility_unresolved` |
| `req_db1d8ccd3c7a4ed3a0f6a6e0b574adc9` | `rvw_c505bea953ae4afbaa322ce87954b51a` | `task_f7807d6055d8479cb5375b4f95a6d4ec` | 정보 부족 | 가능 | `feasibility_unresolved` |
| `req_27979727057247dc8528d08f4b49bc1e` | `rvw_0c056784783a42279a4ee6613c72c636` | `task_404a0df2d8884960a86ed4842f9af633` | 정보 부족 | 가능 | `feasibility_unresolved` |

### F2 — [심각도 중간] `frontend/src/pages/Policy.tsx:30`, `frontend/src/state/events.ts:44` / 정책 첫 진입

- **문제:** 첫 진입 직후 편집한 임계값을 서버의 기존 설정이 조용히 덮어쓰며 사용자가 입력한 값과 다른 값으로 검증된다.
- **근거/재현:** 새 context로 policy_editor 로그인 → `/policy` → choice_confidence_thresholds를 `{"ai_need":1.5}`로 입력 → 즉시 서버 검증. Chromium 3/3에서 실제 전송은 `{ai_need:0.8,feasibility:0.8,urgency:0.8}`, 응답 valid=true였다. 2회는 클릭 직전 inputValue가 1.5였는데 전송 시 이미 0.8로 바뀌었다. 두 브라우저의 초기 회귀에서도 같은 검증 실패 기대가 어긋났다. 2초 안정 후 같은 입력은 valid=false로 정상 거절된다. [덮어쓴 상태](P7-policy-edit-reset.png), [안정 후 정상 거절](P7-policy-validation.png).
- **추정 원인:** session cursor가 없는 최초 SSE 연결은 과거 policy.published를 재생하고, Policy의 onEvent가 무조건 refresh한다. refresh는 dirty 상태를 구분하지 않고 setConfig/setDrafts({})를 실행한다. StrictMode의 중복 초기 fetch도 경합에 기여할 수 있으며 각 reset의 정확한 호출 원인 구분은 불확실하다.
- **제안 수정:** 현재 activeVersion 이하의 replay 이벤트 무시, initial fetch 경합 취소/세대 검사, 편집 dirty 시 자동 덮어쓰기 대신 새 버전 알림·명시적 반영을 제공한다. 검증 요청은 사용자 draft snapshot을 사용한다. 과거 이벤트가 있는 새 세션의 즉시 입력 회귀를 추가한다.
- **예상 규모:** M.

### F3 — [심각도 중간] `frontend/src/pages/Monitoring.tsx:35`, `frontend/src/pages/Monitoring.tsx:53` / 모니터링 첫 진입

- **문제:** 데이터가 이미 준비된 영역도 가장 늦은 집계 API를 기다리며 본문 전체가 로딩 표시로 남는다. WebKit 콜드 3회 모두 7.8–8.8초, Chromium 최대 4.7초였다.
- **근거:** 위 18회 첫 진입 표와 별도 API timing. 코드가 summary/slo/failures/alerts를 allSettled로 묶고, data 없는 loading 동안 제목·필터·개별 카드까지 반환하지 않는다. [1초 시점 화면](P7-monitoring-wait.png). 네트워크/DB 상태에 따른 지연 비중은 불확실하나 영역 일괄 대기는 코드로 확인된다.
- **제안 수정:** 제목·필터·레이아웃은 즉시 렌더링하고 각 영역 응답을 독립 반영한다. summary/slo/failures의 겹치는 집계 비용을 줄이고 요청 중복 제거·짧은 캐시 또는 snapshot을 적용한다. 실제 누적 metrics를 가진 환경에서 cold API/렌더 시간을 분리 재측정한다.
- **예상 규모:** M.

### F4 — [심각도 중간] `frontend/src/pages/Main.tsx:60`, `frontend/src/pages/Main.tsx:74` / 두 번째 탭 내 요청 목록

- **문제:** 다른 탭이 만든 요청이 현재 탭의 목록에 자동 반영되지 않아 “실시간” 상태와 신규 요청 발견 경험이 다르다.
- **근거/재현:** B의 6091 `/` 목록 로딩을 2.5초 기다림 → A5991에서 `req_8160c0b3358e42319382090a8a9c59db` 생성 → A 최종 완료 후 B에서 5.5초 대기 → 목록에 없음 → B 새로고침 후 표시. Redis 중단/복구 실행의 빈 선택 탭에서도 동일했다. Main은 requestId 없으면 SSE enabled=false이고 목록 fetch는 requestId/detail.status 변화에 의존한다. [정체된 탭](P7-second-tab-stale.png).
- **제안 수정:** tenant 목록 이벤트를 요청 상세 구독과 별도로 받아 request.received 및 상태 변경 시 권한 범위 내 목록을 invalidate/refetch한다. 이벤트 burst는 debounce하며 선택 중 상세는 유지한다.
- **예상 규모:** S.

### F5 — [심각도 낮음] `frontend/src/pages/main/ProgressivePanel.tsx:42`, `frontend/src/pages/Main.tsx:151` / 잠정→최종 결과

- **문제:** 잠정 카드가 나온 뒤 요청 확인 카드·잠정 배지가 사라지고 요약 카드가 새로 삽입돼 읽던 판단 위치가 이동한다. 근거 준비도 원문 대신 건수/대기 안내라 사용자가 내용을 읽기까지는 최종 저장을 기다린다.
- **근거:** 30건에서 실제 잠정→최종 DOM 교체, Chromium layout-shift 합 0.01349–0.03348, [영상](P7-progressive.webm)과 [잠정 화면](P7-provisional.png). 중복 결과 카드가 동시에 남는 현상은 관측하지 않았다. 낮은 이동량이므로 심각한 가독성 장애로 과장하지 않는다.
- **제안 수정:** 요약·판단·업무 영역의 순서와 자리 높이를 잠정 단계부터 유지하고 최종 데이터만 교체한다. 준비 건수와 상세 열람 가능 상태를 명확히 구분한다.
- **예상 규모:** S.

### F6 — [심각도 낮음] `frontend/src/pages/Evaluation.tsx:57`, `frontend/src/lib/labels.ts:13` / 한국어 UI

- **문제:** 평가 화면의 `consensus_required`, `ai_need`, `team_set` 및 정책 편집기의 다수 snake_case 필드가 일반 조작 화면에 그대로 노출된다.
- **근거:** [라벨 불일치 화면](P7-chromium-label-disagreement.png), [WebKit](P7-webkit-label-disagreement.png), 정책 화면 캡처. 사용자에게 불일치 상태와 편집 필드의 의미가 즉시 전달되지 않는다.
- **제안 수정:** 합의 상태를 “검토자 간 의견 불일치” 등으로 매핑하고 평가/정책 필드에 한국어 이름·짧은 설명을 제공한다. 내부 키는 접힌 기술 상세에 유지한다.
- **예상 규모:** S.

## 원시 측정 요약

재현 가능한 요청 ID와 단계별 ms를 이 보고서 안에 보존한다. 임시 실행 harness/log/JSON은 최종 산출물이 아니다. 모든 행의 final 성공, partial disabled 확인값은 true다.

| 브라우저 | # | 첨부 | request_id | 낙관 | 단계 | 잠정 | 근거 | 업무 | 최종 |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|
| chromium | 1 | 텍스트 | `req_1f9dd4d2c742426a8f515544502010c9` | 3.0 | 531.5 | 1589.7 | 2933.3 | 1903.7 | 3510.2 |
| chromium | 2 | 텍스트 | `req_f611173013b84c51ba7f5cbf5f6026f5` | 2.8 | 114.2 | 456.4 | 1234.2 | 756.6 | 1402.3 |
| chromium | 3 | 텍스트 | `req_ae4416e3f3da4dbaace2ce3286c83e9e` | 3.8 | 99.0 | 674.9 | 1678.5 | 975.2 | 1885.5 |
| chromium | 4 | 텍스트 | `req_2f8706c4483043d5b5521f16362caa1e` | 2.7 | 85.9 | 621.7 | 1351.2 | 907.0 | 1534.5 |
| chromium | 5 | 텍스트 | `req_98c64c569aeb4c52a9587e3b763ecbd6` | 3.1 | 139.5 | 568.8 | 1307.9 | 886.3 | 1501.6 |
| chromium | 6 | 텍스트 | `req_1d90245a52b94c43b7128bcbc7814ce2` | 3.0 | 99.8 | 608.5 | 1666.8 | 896.1 | 1833.5 |
| chromium | 7 | 텍스트 | `req_581d49e243054681b2a325aac6d05fb8` | 2.7 | 128.4 | 599.9 | 1388.1 | 913.4 | 1525.5 |
| chromium | 8 | 텍스트 | `req_838dc8d634c84bf491dec02c2bedf59b` | 3.0 | 106.0 | 762.3 | 1761.4 | 1091.1 | 1928.4 |
| chromium | 9 | 텍스트 | `req_dbd6a4830ee444e1a6a2ca93ab29ad93` | 2.7 | 102.8 | 586.8 | 1333.0 | 873.6 | 1486.7 |
| chromium | 10 | 텍스트 | `req_b54aef0a5ac643f0958c3be683496b97` | 2.7 | 101.7 | 687.5 | 1437.0 | 994.0 | 1572.5 |
| chromium | 11 | rooms.md | `req_d6da93a9155544e195d8bc89dd6b0fbf` | 2.8 | 367.1 | 936.4 | 2868.7 | 1237.0 | 2919.9 |
| chromium | 12 | approval.docx | `req_7837125a4ed44ae8bb3669344177abdc` | 3.3 | 433.5 | 848.2 | 2061.6 | 1419.1 | 2231.9 |
| chromium | 13 | returns.pdf | `req_33490e8abfbf4a0d93d6e38149fd7a56` | 3.1 | 388.3 | 741.5 | 2269.2 | 1043.2 | 2558.5 |
| chromium | 14 | rooms.md | `req_c35afd031aab4f9d8fe9b2231610388a` | 2.7 | 282.4 | 648.9 | 2184.7 | 975.6 | 2455.2 |
| chromium | 15 | approval.docx | `req_b36157306f044cd8b52d0add6924c672` | 2.7 | 338.8 | 706.1 | 1929.5 | 995.9 | 2091.7 |
| webkit | 1 | 텍스트 | `req_8d9f04b98c054fc48fc0ecf9b0b14368` | 6.0 | 103.0 | 492.0 | 1460.0 | 799.0 | 1631.0 |
| webkit | 2 | 텍스트 | `req_17f7fc14624a44fc82e1a0955f8ed386` | 4.0 | 67.0 | 405.0 | 1706.0 | 726.0 | 1868.0 |
| webkit | 3 | 텍스트 | `req_7ccbb2b20eed4e0487ad00ade3ecbff8` | 4.0 | 90.0 | 469.0 | 1444.0 | 770.0 | 1590.0 |
| webkit | 4 | 텍스트 | `req_8308619b250d48e39e01a7bfada12a63` | 2.0 | 89.0 | 611.0 | 1430.0 | 912.0 | 1584.0 |
| webkit | 5 | 텍스트 | `req_ab4b3e0ab7444af186fbd8fe759311b3` | 3.0 | 88.0 | 618.0 | 1564.0 | 934.0 | 1767.0 |
| webkit | 6 | 텍스트 | `req_68144bc39e464e3f8f31637f2150ebe9` | 2.0 | 85.0 | 555.0 | 1580.0 | 840.0 | 1739.0 |
| webkit | 7 | 텍스트 | `req_4296887b41644160b896682eecf10e96` | 3.0 | 78.0 | 583.0 | 1905.0 | 1153.0 | 2065.0 |
| webkit | 8 | 텍스트 | `req_d1e3ae1a905e41eb912cbcef0239d072` | 3.0 | 90.0 | 420.0 | 1370.0 | 735.0 | 1518.0 |
| webkit | 9 | 텍스트 | `req_3b203a33bad142c5a8b7e1c94e1b73bf` | 3.0 | 91.0 | 487.0 | 1238.0 | 862.0 | 1379.0 |
| webkit | 10 | 텍스트 | `req_3f85aa4c318e40bcb1612031aad4b1ff` | 3.0 | 87.0 | 563.0 | 1333.0 | 856.0 | 1494.0 |
| webkit | 11 | rooms.md | `req_db1d8ccd3c7a4ed3a0f6a6e0b574adc9` | 4.0 | 302.0 | 826.0 | 2577.0 | 1145.0 | 2835.0 |
| webkit | 12 | approval.docx | `req_e728969317454f63939de824c23f2c11` | 3.0 | 359.0 | 720.0 | 1978.0 | 1034.0 | 2126.0 |
| webkit | 13 | returns.pdf | `req_5b06ff82e942423c951a193260433420` | 4.0 | 378.0 | 759.0 | 2296.0 | 1087.0 | 2573.0 |
| webkit | 14 | rooms.md | `req_ec2eb62a189f415297801cdfb6419714` | 3.0 | 258.0 | 591.0 | 2118.0 | 896.0 | 2378.0 |
| webkit | 15 | approval.docx | `req_27979727057247dc8528d08f4b49bc1e` | 3.0 | 320.0 | 696.0 | 1957.0 | 1020.0 | 2148.0 |

## 정리 및 한계

- 전체 시험 성공을 주장하지 않는다. 업무 전이 정상 완료 경로는 F1로 차단됐으며, 수정 승인 저장/원안 보존 및 차단 사유는 API·화면·DB로 대조했다. 추가로 DB task를 강제로 풀어 시험을 통과시키지 않았다.
- 권한 허용 원문 보기만 이미 저장된 t-ux2 비민감 fixture를 읽었다. 신규 판단·정책·검토·라벨 시험은 t-alpha, 차단 조회는 t-beta에서 수행했다. 합성 요청·검토·업무·라벨 감사 기록은 DB에 남긴다. 공유 DB 기록 삭제나 사용자 권한 변경은 하지 않았다.
- 정책은 각 게시 시험 직전 설정을 기준으로 rollback한 새 버전을 생성하여 설정 내용을 복원했다(v17→v18→v19, v19→v20→v21). 기록은 감사 이력에 남는다.
- 후속 코드 수정은 본 측정에 합산하지 않는다. API/worker를 재시작한 뒤 별도 회귀가 필요하다.
- 프로세스·브라우저·Redis 최종 정리 결과는 아래 완료 기록으로 확정한다.

### 완료 시 정리 확인

2026-10-04 KST 최종 확인: P7 소유 API8791·8792, worker, collector, watchdog, Vite5991·6091 프로세스 전부 종료; 콜드 Vite6191도 잔류 listener 없음. Ego task space와 Playwright contexts 종료. 공유 Neo4j와 Redis 모두 `running healthy`, Redis `PING → PONG`. 공유 컨테이너는 유지했다. 임시 harness·로그·캐시는 제거하고 본 보고서, PNG 17장, 짧은 WebM 1개만 산출물로 남겼다.
