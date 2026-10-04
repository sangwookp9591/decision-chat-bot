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
- **경과 시간**: 5초 이상 결과가 없으면 `useSlowNotice`가 '평소보다 오래 걸리고 있어요 · 현재 단계: …'를 보여 준다. 실패(`judgment_failed`·접수 오류)는 즉시 원인과 '다시 시도' 버튼(접수 실패 → 같은 입력 재제출, 분석 실패 → 새 실행)을 보인다.

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
