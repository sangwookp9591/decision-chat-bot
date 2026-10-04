# 판단 결과 점진 표시 계약

작성일 2026-10-04 · 상태: 구현 계약(백엔드·프런트 공통)

## 배경과 근거

사용자는 판단 파이프라인 전체(Jev 분류 → 근거 연결 → 업무 분해 → 저장)가 끝날 때까지 결과를 하나도 보지 못했다. 공개 사례에서 다음 원칙을 채택한다.

- 데이터가 필요한 영역 가까이에서 영역별로 로딩하고, 최종 콘텐츠와 닮은 폴백을 쓴다 — [토스페이먼츠 초기 렌더링 최적화](https://toss.tech/article/faster-initial-rendering).
- 짧은 로딩(≈200ms 이내)은 로딩 UI를 보여주지 않아 깜빡임을 막는다 — 토스 오픈소스 [Suspensive `<Delay/>`](https://suspensive.org/docs/react/Delay).
- API를 나눠 먼저 준비된 결과부터 보여주고 다음 화면을 prefetch한다 — [토스 프론트엔드 서비스 최적화](https://toss.tech/article/32583).
- AI 응답은 완성까지 기다리지 않고 먼저 나온 부분부터 스트리밍하며, 첫 결과까지의 시간(TTFT)을 핵심 지표로 본다 — [The Latency Perception Gap](https://tianpan.co/blog/2026-04-20-latency-perception-gap-ai-interfaces).

## 단계와 이벤트

| 단계 | 서버 동작 | SSE 이벤트(kind) | payload(원문 금지) |
| --- | --- | --- | --- |
| 접수 | Request·Run 생성 | `request.received` | `request_id, run_id, status` |
| 진행 | 각 RunStep 시작·종료 | `run.step`(기존) | `step_name, kind, status` |
| 잠정 판단 | 핵심 분류 Jev 응답 직후, Run에 `preliminary` 저장 | `judgment.partial` | `request_id, run_id, classifications{ai_need,feasibility,urgency,lead_org}, confidences{…}, risk_flags{…}, preliminary:true` |
| 근거 연결 완료 | 근거 결과를 Run에 임시 저장 | `judgment.evidence_ready` | `request_id, run_id, evidence_count` |
| 업무 분해 완료 | 초안 결과를 Run에 임시 저장 | `judgment.tasks_ready` | `request_id, run_id, task_count` |
| 최종 판단 | 기존 정식 Judgment 저장(최초 판단 완료) | `judgment_saved`(기존) | 기존 + `classifications` |

- **잠정 결과는 판단 완료가 아니다.** 05_SLO의 최초 판단 완료 시각은 정식 Judgment 커밋 시각 그대로다. 잠정 결과는 검토·배정·자동 배정 판단에 쓰지 않는다. 화면에는 '잠정 — 근거와 업무 분해를 확인하는 중' 배지를 단다.
- 잠정 결과 쓰기도 `ctx.commit`(소유권·active run 검증) 안에서 한다. 과거 run의 잠정 결과는 active run이 아니면 쓰지 않는다.
- 근거 연결과 업무 분해는 서로 독립이므로 병렬로 실행한다.
- 근거 연결 내부에서도 선택 단위 × 네 판단의 Jev Noul 호출을 최대 4개씩 병렬 실행한다. 완결된 호출 결과는 기존 판단 순서와 원문 단위 순서로 모아 저장하므로 진행 이벤트 및 최종 근거 배열의 계약은 동일하다. 한 호출의 실패는 단계 실패로 전파한다. [PERF-3 측정](../../artifacts/validation/perf/evidence.md)은 live 20건 수신→최종 지연과 근거 연결 지연을 분리해 기록한다.

## 조회 API

`GET /api/requests/{id}/progress?run_id=`(기본 active run): 권한은 `can_view_request`.

```json
{
  "request_id": "...", "run_id": "...", "status": "processing|judgment_saved|failed|...",
  "steps": [{"name": "...", "kind": "ai|code|rule", "status": "...", "started_at": "...", "ended_at": "..."}],
  "preliminary": {"classifications": {}, "confidences": {}, "risk_flags": {}} ,
  "evidence_ready": false, "tasks_ready": false, "final": false,
  "timings_ms": {"received_to_preliminary": 0, "received_to_final": 0}
}
```

화면은 새로고침·재연결 시 이 API로 현재 단계를 복원하고, 이후는 SSE 이벤트로 갱신한다.

## 진행 중 분석 취소 (REM-CANCEL)

`POST /api/requests/{request_id}/runs/{run_id}/cancel`은 요청 작성자와 같은 tenant의 운영자에게 허용한다. CSRF를 요구하며, 다른 tenant의 요청·실행은 404, 같은 tenant의 권한 없는 호출은 403이다. 대기·실행 중인 Run은 `cancelled`로 바꾸고 `{request_id,run_id,status}`를 200으로 반환한다. 이미 끝난 Run은 변경 없이 현재 `cancelled|failed|judgment_saved` 상태를 200으로 반환한다. 이 계약은 재전송에도 동일하다.

취소 트랜잭션은 Request→Run→Job 순서로 잠그고 Job을 `cancelled`로 바꾸며 lease generation을 올린다. 그래서 대기 작업은 claim 대상에서 즉시 빠지고, 기존 워커의 단계 시작·종료·결과 저장 `ctx.commit`은 소유권 검증에서 막힌다. 진행 중인 외부 Jev 호출은 반환될 때까지 기다리되 결과는 저장하지 않는다. 최종 Judgment가 먼저 커밋된 경우에는 취소보다 완료를 우선해 Run·Job 상태를 `judgment_saved`·`completed`로 수렴시킨다. 취소가 먼저 커밋되면 이후 완료 시도는 lease 검증에 실패한다.

Run은 `cancelled_by`, `cancelled_at`, `cancelled_step`과 종료 시각을 남기고, 진행 중 RunStep도 `cancelled`로 닫는다. 요청 상태도 `cancelled`가 된다. 같은 트랜잭션에서 `judgment.cancelled` 이벤트를 한 번 발행한다. 커밋 후에는 `worker_run(status_code=cancelled)` journal 기록을 한 번 남겨 모니터링 취소 집계와 맞춘다. SSE와 progress 조회의 `cancelled`는 화면에서 '취소됨'으로 나타난다. 잠정 분류가 이미 있었다면 결과를 흐리게 남기고 로딩 표시를 끝낸다. 같은 요청의 '다시 분석'은 현재 revision으로 새 Run·Job을 만든다.

## 지표

- `time_to_preliminary_ms`(수신→잠정 판단)와 기존 최초 판단 지연을 함께 journal에 기록하고 모니터링에 별도 지표로 표시한다. 기존 SLO 수치·분모는 바꾸지 않는다.

## 구현 상태 (PERF-1, 2026-10-04)

`POST /api/requests`가 요청을 저장한 뒤 `request.received`를 한 번 기록한다. `Jev 판단` RunStep은 핵심 분류 호출만 포함한다. 분류 응답 직후 active run 및 Job 소유권을 확인하는 `ctx.commit(affects_request=True)`에서 `Run.preliminary_json`·`preliminary_at`과 `judgment.partial` 이벤트를 함께 기록한다. 이 시점에는 `Judgment`, `Review`, `Assignment`를 만들지 않는다. 근거 연결과 업무 분해는 별도 스레드에서 동시에 실행하고 각각 `Run.evidence_json`·`evidence_count`·`evidence_ready_at`과 `Run.tasks_json`·`task_count`·`tasks_ready_at` 및 대응 이벤트를 커밋한다. 임시 근거 JSON에는 원문을 넣지 않고 unit ID·확률·작성 주체만 넣는다. 정식 근거와 작업 초안은 최종 `Judgment`/`Draft` 트랜잭션에 저장한다. `judgment_saved`에는 네 분류 필드를 `classifications`로 추가했다.

`GET /api/requests/{id}/progress?run_id=`는 `can_view_request` 권한을 확인한 뒤 RunStep, 잠정 분류, 준비 여부, 수신→잠정·수신→최종 시간을 Neo4j에서 읽는다. `run_id`가 없으면 active run을 사용한다. 시간 값이 아직 없으면 `null`이다. journal의 `judgment_preliminary.time_to_preliminary_ms`는 수신 시각과 잠정 커밋 시각 차이다. 검증: `backend/tests/integration/test_progressive_judgment.py`에서 근거/분해 호출을 멈춘 상태로 잠정 결과만 읽고, 정식 판단·배정이 없음을 확인한다.

## 프런트엔드 구현 (PERF-2)

### 상태와 흐름

- `frontend/src/state/progress.ts`의 순수 리듀서가 단계를 관리한다: `idle → submitting(낙관적 카드) → received → preliminary → final | failed`. 단계는 앞으로만 간다(늦게 온 `judgment.partial`이나 progress API 복원 응답이 `final`을 되돌리지 못함). `evidence_ready`·`tasks_ready`는 도착 순서와 무관하게 각자의 영역 플래그만 켠다. 다른 `request_id`의 이벤트는 무시한다.
- 접수 직후 제출한 요청 카드(`aria-label="제출한 요청"`)를 즉시 표시하고 서버 `request_id`가 오면 '접수됨'으로 확정한다. 접수 실패 시 카드를 걷어내고(롤백) 입력 내용은 그대로 두며, 원인과 '다시 시도' 버튼을 보여 준다.
- `judgment.partial`이 오면 4개 판단 카드가 '잠정' 배지와 함께 바로 나온다. 근거 영역·업무 분담 영역은 최종 모양의 스켈레톤이고 `evidence_ready`(근거 N건 연결됨)·`tasks_ready`(업무 N건 준비됨)에 따라 각각 채워진다. 최종 저장 전에는 '검토·배정은 최종 판단 저장 후 가능해요' 버튼이 비활성이다(검토·배정 행동은 정식 Judgment가 있어야 열린다).
- `judgment_saved`의 `classifications`로 카드를 먼저 최종 값으로 바꾸고(잠정 배지 제거), 그다음 상세(`/judgment`)를 조회해 기존 결과 화면으로 교체한다.
- 새로고침·재연결: 판단이 아직 없으면(`/judgment` 404) `GET /api/requests/{id}/progress`로 단계 타임라인과 잠정 카드를 복원하고 이후는 SSE로 갱신한다. 10초 폴링은 SSE가 끊겼을 때의 보조 수단으로 유지한다.
- SSE 구독 목록(`EVENT_KINDS`)에 `request.received`, `judgment.partial`, `judgment.evidence_ready`, `judgment.tasks_ready`를 추가하고, 이벤트 전체 payload를 `StreamEvent.payload`로 전달한다. 채팅 위젯은 `chat:progress`로 '요청을 분석하고 있어요 · 현재 단계'를 보여 준다.

### 로딩 표시 원칙

- **영역별 로딩**: 전체 화면 스피너 대신 근거·업무 영역만 스켈레톤으로 둔다. 라우트 전환 폴백도 본문 영역 스켈레톤이다.
- **200ms 지연**: `useDelayedFlag`(`state/useDelayedFlag.tsx`)로 로딩 표시를 200ms 늦춘다. `LoadingState`·`Skeleton`·라우트 폴백이 모두 사용한다. **Suspensive `<Delay/>`를 직접 쓰지 않고 작은 훅을 둔 이유**: 필요한 것이 지연 하나뿐이고, Suspensive는 Suspense·ErrorBoundary 묶음까지 들어오는 새 의존성이라 번들·검증 비용이 이득보다 크다. 동작은 같다(활성 상태가 지연 시간 이상 지속될 때만 true, 끝나면 즉시 false).
- **경과 시간**: 5초 이상 결과가 없으면 `useSlowNotice`가 '조금 더 걸리고 있어요 · 현재 단계: …'를 보여 준다. 실패(`judgment_failed`·접수 오류)는 즉시 원인과 '다시 시도' 버튼(접수 실패 → 같은 입력 재제출, 분석 실패 → 새 실행)을 보인다.

### 첫 로딩

- `vite.warmup.ts`의 `server.warmup.clientFiles`에 진입 파일과 모든 라우트 페이지를 지정했다([Vite 성능 가이드](https://vite.dev/guide/performance#warm-up-frequently-used-files)); `vite.config.ts`·`vite.e2e.config.ts`가 공유한다.
- 랜딩(`/`) 외 7개 라우트는 `React.lazy` 청크로 분리했다(`layout/routes.tsx`). 메뉴에 마우스를 올리거나 포커스하면 해당 청크를 prefetch하고, 첫 렌더 후 브라우저가 한가할 때(`requestIdleCallback`) 나머지를 차례로 prefetch한다. prefetch 실패는 다음 hover에서 재시도한다.

### 측정 (2026-10-04, 로컬 mock 모드)

| 항목 | 이전 | 이후 |
| --- | --- | --- |
| 초기 JS(`vite build`) | 368.9 kB (gzip 118.1 kB) | 220.5 kB (gzip 72.6 kB), 라우트 청크는 이동 시 로드 |
| 초기 CSS | 46.2 kB (gzip 9.6 kB) | 20.3 kB (gzip 5.2 kB) |
| 콜드 dev 서버 → 모니터링 제목(API 목) 3회 | 569·568·558 ms | 492·519·532 ms |
| 콜드 dev 서버 → 모니터링 제목(실제 API) 3회 | 444·459·401 ms | 545·503·383 ms |
| 제출 → 낙관적 카드 / 잠정 카드 / 최종 결과(live, mock Jev) | 해당 없음(최종만) | 39 ms / 396 ms / 703 ms |

- **모니터링 첫 실행 5초 초과는 이 환경에서 재현되지 않았다.** 비어 있는 `cacheDir`의 새 dev 서버(콜드)에서 목 API·실제 API(`/api/monitoring/summary` 60ms) 모두 0.4–0.6초였다. 개선 전후 차이는 측정 잡음 범위이므로 '콜드 시작이 빨라졌다'고 주장하지 않는다. 원인 후보(공유 `node_modules/.vite` 의존성 재최적화로 인한 전체 새로고침, 여러 dev 서버 동시 기동, 운영 데이터가 쌓인 집계 지연)는 같은 조건에서 다시 보지 못했다. 측정 방법은 `node scripts/measure-cold-start.mjs [횟수] [경로]`(실제 API는 `REAL_API=1 E2E_API=…`)이다.
- 실측으로 확인된 개선은 초기 번들 감소(JS −40%, CSS −56%)와 점진 표시(첫 의미 있는 결과 396ms, 최종 703ms의 약 56% 지점)다. mock Jev는 응답이 빠르므로 live Jev에서는 두 값의 차이가 더 커진다.

### 시험

- vitest: `state/progress.test.ts`(이벤트 순서별 상태, 복원, 퇴행 방지), `state/useDelayedFlag.test.tsx`(200ms 미만 깜빡임 방지, 5초 안내), `pages/Main.progressive.test.tsx`(낙관적 카드 확정·실패 롤백·재시도, 잠정 카드·영역별 채움, 최종 payload 즉시 갱신, progress API 복원, 지연 안내, 실패 안내), `layout/routes.test.tsx`(prefetch).
- playwright(live): `e2e/progressive-results.spec.ts`(제출→낙관적→잠정→최종 시점 측정, 화면 기록은 `artifacts/validation/perf2-live/`). a11y 회귀는 `A11Y_SHOT_DIR`로 PNG 출력 위치를 바꿔 t23 증거 파일을 덮어쓰지 않는다.

## P7 보완 (UX-6, 2026-10-04)

- **잠정→최종 자리 유지(F5)**: `ProvisionalResult`와 `Result`가 같은 영역(`data-region`: `summary` → `judgment` → `tasks`)을 같은 순서·자리 높이로 그린다. 잠정 단계에서도 요약 카드(제목·요약 슬롯 스켈레톤·한 줄 안내·근거 건수 줄)가 먼저 있고, 최종 저장 후에는 같은 슬롯의 데이터만 바뀐다. 제출한 요청 카드는 최종 후에도 유지한다(걷어내면 아래 전체가 밀린다). 슬롯 최소 높이는 `main.css` 하단에 있다.
- **F5 잔여(UX-7)**: 잠정 분류가 `UNCERTAIN_VALUES`(정보 부족·판단 보류·미정)이면 최종과 같은 불확실성 안내(`.uncertain-result`)를 잠정 단계부터 그리고 선택 칩은 강조하지 않는다. 판단 카드의 신뢰 신호 줄·근거 줄(최소 44px)과 요약 카드 제목 줄(32px)·동작 슬롯(44px)을 잠정부터 최종 크기로 예약한다. 검증은 layout-shift 합이 아니라 스크롤 상태에서 summary/judgment/tasks의 문서 top과 judgment 높이 차 ≤4px 단언(`e2e/p7-fixes.spec.ts` “F5 residue”, Chromium·WebKit live): 수정 전 업무 top +83~154px → 수정 후 0px.
- **준비 건수와 열람 가능 상태 구분**: '근거 N건 연결됨'·'업무 N건 준비됨'은 건수만 뜻하고, 원문·상세 열람은 '원문 열람은 최종 저장 후 가능'·'검토·배정은 최종 판단 저장 후 가능해요'로 따로 표시한다.
- **측정**: `e2e/p7-fixes.spec.ts`가 잠정 카드가 뜬 뒤부터 최종까지의 `layout-shift` 합(`hadRecentInput=false`)을 재고 0.005 미만을 요구한다(Chromium 전용). 이전 관측은 0.0135–0.0335였고 수정 후 0.00001이었다.
- **모니터링 화면(F3)**: 제목·필터는 즉시 그리고 summary·slo·failures·alerts는 각각 독립 요청·독립 영역이다(`Monitoring.tsx`의 `useArea`). 영역은 최종 모양(라벨·표 행 고정, 값 자리만 스켈레톤)이며 200ms 미만이면 빈 자리만 둔다. 한 영역의 실패는 그 영역에만 표시하고 나머지는 그대로 쓴다. `api/monitoring.ts`는 같은 URL의 진행 중 GET을 하나로 합친다(완료 후 캐시 없음).
- **요청 목록(F4)**: 요청 상세 구독과 별도로 `Main`이 필터 없는 tenant 이벤트 스트림을 하나 더 열고, 목록에 영향을 주는 이벤트(`request.received`, `judgment_saved|failed`, `review_decided`, `assignment_created`, `auto_assignment_deferred`, `task.transitioned`, `reanalysis.compared`)가 오면 400ms debounce 후 `GET /api/requests`만 다시 부른다(권한 범위는 서버가 정한다). 열려 있는 상세는 이 스트림으로 다시 불러오지 않는다.

## 대화형 접수 (CHAT-1)

요청 접수 화면(`pages/Main.tsx`)은 일동이와의 대화다. 떠 있는 채팅 위젯·런처는 `AppShell`에서 제거했고 다른 화면의 요청 동선은 사이드바 '요청 접수'로 일원화했다. 위 점진 표시 계약은 그대로이고 표시 단위만 말풍선이 되었다.

- **메시지는 서버 상태에서 파생**한다(별도 대화 저장소 없음): 사용자 말풍선은 `detail.revisions`(보완 revision은 서버가 '이전 문장+새 문장'으로 저장하므로 `conversation.userMessages`가 이번 턴에 더한 문장·새 첨부만 보여 준다)와 낙관적 전송, 일동이 말풍선은 업로드 %(`uploadRequest`) → 분석 진행(`run.step`, thinking 아이콘) → 잠정 답변(`ProvisionalResult`) → 최종 답변(`Result`) 순이다. 새로고침은 `?request_id=` + detail·judgment·runs·progress로 같은 대화를 복원하므로 백엔드 추가 API는 없다.
- **자리 유지**: 잠정·최종 답변은 같은 말풍선 틀(44px 아바타 칸, `bubble-title` 한 줄)을 쓰고, 다시 분석·새 요청 시작은 결과 카드 밖 `QuickReplies` 줄(요청이 열린 순간부터 렌더, 최종 저장 전 '다시 분석' 비활성)로 옮겨 카드 높이가 변하지 않는다. 말풍선 안 카드의 위 여백을 건드리는 CSS(`p` 일괄 margin 재설정)는 쓰지 않는다 — 한 번 8px 이동을 만들었다(F5 e2e가 검출).
- **결과 아이콘 규칙**: 긴급(`urgency`에 '긴급') → 마스코트 없이 ⚠ 표식, 검토 필요 → surprised, 그 외 → like. 문장으로도 전달한다.
- **대화 속 상호작용**: 읽기 실패 파일(`needs_file_decision`) → '이 파일을 읽지 못했어요' + [제외하고 진행](file-decision API)·[다시 첨부](파일 선택 → 같은 입력창 전송이 revision). 서버는 새 revision에도 이전 파일을 이어 붙이므로 다시 첨부해도 읽지 못한 파일은 남아 선택이 이어진다(`currentAttachments`가 최신 revision 파일만 표시). 보완 요청(`needed_info`) → 질문 말풍선, 같은 입력창의 답은 `revisions` API(`expected_revision`). 요청이 열려 있고 보완 상태가 아니면 입력은 새 요청으로 접수된다(안내 문구 표시).
- **입력창**: 여러 줄, Enter 전송·Shift+Enter 줄바꿈(한글 IME 조합 중 Enter는 전송하지 않음, Ctrl/⌘+Enter도 전송), 파일 첨부 버튼·드래그 앤 드롭·칩(제거 가능, 최대 5개 안내), 예시 요청 칩 3개는 입력창을 채우기만 한다. 마스코트 매체는 `components/Mascot.tsx`(webm / Safari webp / reduced-motion png).
- **검증**: vitest `Main.chat.test.tsx`·`main/conversation.test.ts`(상태 전이·파일 실패 선택·정보 요청 답변→revision·복원·아이콘 규칙), e2e `e2e/chat-intake.spec.ts`(Chromium·WebKit, 375/520/960/1440px 캡처는 `artifacts/review/chat-intake/`).

## 대화 화면 레이아웃 (CHAT-POLISH, ChatGPT 같은 채팅창)

토스 토큰·브랜드 색은 그대로 두고 배치를 ChatGPT식으로 바꿨다. 색·글꼴·반경은 토큰만 쓴다(`main/main.css`).

- **화면 높이 고정**: `main > section.chat-page`가 `100dvh - --shell-top`(상단바·좁은 화면 메뉴 줄 높이를 `Main.tsx`가 측정) 높이이고 문서 높이가 창 높이와 같다. 스크롤은 대화(`.chat-scroll`)와 왼쪽 목록(`.list-scroll`)에서만 난다. 셸의 `.app-main{min-height:100vh}`는 `.app-main:has(.chat-page)`로 풀었다. 목록 행 안의 `.sr-only`는 `.request-row{position:relative}`로 가둔다(아니면 절대 위치 요소가 문서 높이를 늘린다). 측정값: `artifacts/review/chat-polish/metrics.jsonl`.
- **왼쪽 '내 요청 대화'**(`main/RequestList.tsx`): 위에 `새 요청` 버튼, 날짜 묶음(오늘/어제/지난 7일/지난 30일/`YYYY년 M월`, `listFormat.groupLabel`), 행 = 작은 상태 점(`.status-dot`, 이름은 상태 라벨) + 요청 첫 문장 1줄 말줄임 + 짧은 ID(앞 8자, hover·선택 때만 보임, 전체는 `title`과 보이지 않는 텍스트로 유지), 선택 행은 회색 면. API는 접수 시점에 `masking.py`의 기존 규칙으로 만든 표시용 `Request.title`(첫 문장 60자)·`Request.preview`(140자)를 저장하고 목록·상세에서 제공한다. 기존 요청은 목록·상세를 읽을 때 tenant 쓰기 트랜잭션에서 Request를 잠근 뒤 누락 필드를 한 번 채운다. 작성자는 source 권한과 관계없이 자기 요청의 원문을 읽을 수 있고, preview는 작성자 또는 `can_read_source` 권한자에게만 제공한다. 다른 역할에는 마스킹된 제목만 제공한다.
- **960px 이하**: 목록 칸을 숨기고 머리줄의 ☰('내 요청')가 공용 `Drawer`(시트)를 연다. 고르면 닫힌다. 머리줄의 ＋('새 요청 시작')도 이때만 보인다.
- **대화 본문**: 가운데 768px 열. 내 말은 오른쪽 회색 둥근 말풍선(최대 70%), 일동이는 말풍선 없이 작은 마스코트(32px 고정 칸) + 본문이 열 폭으로 흐른다. 같은 화자가 이어지면 아바타는 첫 줄만(결과 답변은 분위기 아이콘 유지). 읽기 실패·보완 요청·실패는 색 면(callout)으로 구분한다. 등장은 공용 `m-fade-up`, reduced-motion이면 정지.
- **빈 대화**: 인사('무엇을 도와드릴까요?') + 큰 입력창 + 예시 요청 칩이 화면 가운데에 한 덩어리. 첫 전송 때 입력창이 아래로 내려가는 전환은 FLIP(`el.animate`, `MOTION.slow`, reduced-motion이면 생략)이고 입력창은 같은 DOM 노드다.
- **입력창**: 둥근 큰 상자(반경 = `--radius-xl`×1.2), 글자 수에 따라 높이가 늘고 약 8줄부터 내부 스크롤, 왼쪽 ＋ 첨부(탭 순서: 첨부 → 입력 → 전송), 오른쪽 원형 전송 버튼(`button.primary`, 입력 없으면 비활성, 보내는 중에는 정지 모양 + '전송 중'), 아래 안내문(첨부 형식·Enter 전송·Shift+Enter 줄바꿈). 취소 API가 없어 정지 버튼은 동작을 만들지 않는다(모양만).
- **진행 표시**: 일동이 자리에서 점 3개 타이핑(`TypingBubble`, '일동이가 입력 중') → 잠정 답변이 이벤트 도착 순서대로(분류 카드는 36ms 간격 등장, 근거·업무는 자기 영역에 채움 — 인위적 지연 없음) → 최종. 잠정과 최종은 **같은 답변 요소**(`일동이의 답변`/`잠정 답변` 한 노드)라 교체 때 다시 그려지거나 움직이지 않는다.
- **답변 아래 동작 줄**(`AnswerActions`): 답변 복사 / 다시 분석 / 근거 보기 아이콘 버튼. 첫 잠정 카드부터 자리를 잡고(최종 저장 전 비활성) 최종 저장 후 활성이 된다. 새 요청은 왼쪽 목록의 `새 요청`.
- **새 메시지 ↓**: 맨 아래(80px 이내)면 부드럽게(reduced-motion은 즉시) 따라가고, 위로 올려 읽는 중이면 이동하지 않고 하단 원형 ↓ 버튼만 띄운다(새 메시지가 있으면 강조·이름 '새 메시지 보기'). 내가 보낸 메시지는 항상 따라간다.
- **판단 결과 = 답 안의 카드**(`ResultBrief`): 판단 결과 + 상태 배지, 요약 2줄, 핵심 4개 분류(값 + 근거 열기), '업무 N건 · IT팀 2 · AI팀 1', [자세히 보기]. 전체 결과(`Result`)는 `Drawer`('판단 상세'). 근거 원문을 열면 상세 시트는 닫히고 원문을 닫으면 돌아온다.
- **검증**: vitest `Main.layout.test.tsx`(목록 행·날짜 묶음·시트·빈 대화 순서·요약 카드·상세 시트·동작 줄·복사·입력창 자동 높이·Enter 키·입력 중·↓ 버튼), `main/listFormat.test.ts`; e2e `chat-intake.spec.ts`의 `layout *px`(문서 높이 = 창 높이, 목록 자체 스크롤, 입력창 위치)·`reduced motion`·`새 메시지` 버튼, `p7-fixes`의 F4/F5(0px 이동) 그대로 통과. 캡처·수치: `artifacts/review/chat-polish/`.
