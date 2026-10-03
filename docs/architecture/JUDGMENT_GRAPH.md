# 판단 관계 질의 API와 입체 판단 맵 (T29/T37)

2026-10-03 기준. 저장된 Neo4j 노드·관계만 읽는다. 없는 관계를 합성하거나 모델 값을 추정하지 않는다. 모든 질의는 `tenant_id` 조건을 포함하며 쓰기는 없다.

## 계층과 관계

| 계층 | 노드 라벨 |
| --- | --- |
| 1 근거 | `EvidenceSpan`, `ModelOutput`, `Correction` |
| 2 가설 | `RuleCandidate` |
| 3 판단 | `RuleDecision`, `ReviewDecision` |
| 4 적용 | `RuleVersion`, `ValidationRun`, `ConfigVersion` |
| 5 업무 단계 | `RunStep` |

허용 관계는 `CITES`, `CORRECTS`, `RECORDED`, `SUPPORTED_BY`, `DECIDES`, `DERIVED_FROM`, `PUBLISHED_IN`, `VALIDATES`, `APPLIED`, `USED_OUTPUT`뿐이다. 응답의 각 연결은 저장 방향(`source`→`target`)과 의미 방향(`upstream`=근거 쪽, `downstream`=실행 쪽)을 함께 가진다. `PUBLISHED_IN`만 저장 source가 upstream이고 나머지는 저장 target이 upstream이다. 라벨이 아직 없는 계층(예: 병행 작업의 `ValidationRun`)은 빈 계층으로 보인다.

## API

모두 `reviewer`/`rule_admin`/`operator` 역할만 호출할 수 있다(그 외 403). 요청에 묶인 노드(`EvidenceSpan`·`ModelOutput`·`Correction`·`ReviewDecision`·`RunStep`)는 요청 범위 권한(`can_view_request` + 검토/관리 역할)을 통과할 때만 노드·연결·경로·개수에 포함된다. 권한 밖 노드를 지나는 경로는 통째로 제외된다. 다른 tenant의 노드는 404이다.

- `GET /api/graph/judgment?request_id|run_id|rule_id|config_version|status&depth=6` — 기준(여러 개는 합집합)에 맞는 시작 노드에서 근거 쪽·실행 쪽으로 각각 단조롭게 `depth`(최대 8)단계 확장한 노드(최대 400개, 초과 시 `truncated`)와, 그 노드들 사이에 실제 저장된 연결 전부. `rule_id`는 `R-ROUTE-07`(모든 버전) 또는 `R-ROUTE-07@1`. `status`는 단독이면 `RuleCandidate`/`RuleVersion`/`ValidationRun`/`ConfigVersion`의 상태 일치 노드에서 시작하고, 다른 기준과 함께면 해당 라벨 노드의 후처리 필터이다. 기준이 없으면 최근 `Correction`·`RuleCandidate`·`RuleVersion`·`ReviewDecision` 개요. 응답: `nodes`(id·kind·layer·title·summary·status·actor·at·version·source·refs·상·하류 직접 연결 수), `edges`(id=`TYPE:source->target`, type, source, target, upstream, downstream, props — `APPLIED`의 outcome·before·after, `SUPPORTED_BY`의 role, `CITES`의 prob), `layers`(계층별 개수), `node_count`, `edge_count`, `truncated`.
- `GET /api/graph/judgment/path?node_id&direction=up|down|both&depth=6&limit=100` — Neo4j quantified path pattern(`((a)-[:...]->(b)){1,N}`)으로 상류/하류 경로. 다른 경로의 앞부분인 경로는 제외(최대 경로만), `limit`(최대 500) 초과 시 `truncated`. `ConfigVersion`은 `PUBLISHED_IN`을 거쳐 `RuleVersion`부터 상류로, `RuleVersion` 하류는 `PUBLISHED_IN`으로 `ConfigVersion`까지 이어진다. 응답: `paths`(node_ids, edge_ids, direction), 합친 `nodes`/`edges`, `upstream_ids`, `downstream_ids`.
- `GET /api/graph/judgment/nodes/{id}` — 상세. 계층·종류·출처·내용 요약·결정 주체·시각·버전·상태, 전체 상류/하류 개수(깊이 8, 권한 있는 노드만), 직접 연결 노드와 연결, `refs`(`request_id`, `run_id`, `step_id`, `review_id`, `candidate_id`, `rule_id`, `rule_version`, `config_version`). `EvidenceSpan` 노드의 `refs`는 원문 뷰어 앵커(`span_id`, `revision_id`, `source`=attachment ID 또는 `chat`)를 가진다(참조 ID이며 원문 텍스트가 아니다). `source_link`는 `EvidenceSpan`이고 호출자의 `can_read_source`가 참일 때만 `/api/requests/{request_id}/evidence/{span_id}`이며, 그렇지 않으면 `null`이다. 원문 텍스트는 이 API가 반환하지 않는다.

모듈: `backend/jevtriage/graph/{model,query,api}.py`. 시험: `backend/tests/integration/test_judgment_graph.py`(실제 Neo4j에 시드한 관계와 노드·연결 ID 정확 일치, 없는 중간 관계 미생성, 양방향·깊이·limit, 권한/tenant).

## 화면 09 `/judgment-map`

- 5계층 판을 CSS 3D(`perspective` + `rotateX`)로 배치하고, 노드는 접근 가능한 `<button>`, 연결선은 같은 3D 판 위 SVG이다. 확대/축소/이동/전체 보기와 %는 `d3-zoom`(Ctrl/⌘+휠, 버튼, 드래그), reduced-motion이면 전환 애니메이션을 끈다.
- 노드 선택 시 `/path`로 상·하류 경로를 불러와 화면에 병합하고(기준 확장 범위 밖의 이웃도 실제 저장 관계면 표시), 경로 밖은 흐리게 한다. 상세 패널은 값을 저장된 그대로 보여 주고 `↑ 근거 쪽으로 n개`/`↓ 실행 쪽으로 n개`, 원문 보기(권한 시)·검토 열기(`/review?request_id=`)·Flow(`/observatory?run_id=`)·규칙 학습(`/learning?rule_id=rule_id@version`|`candidate_id`|`config_version`) 이동을 제공한다.
- 탐색 기준(요청·실행·규칙·Config 버전·상태)은 URL 쿼리(`request_id`,`run_id`,`rule_id`,`config_version`,`status`)와 동기화되어 다른 화면에서 같은 ID로 들어올 수 있다.
- 한 계층이 12개를 넘으면 종류별 묶음("ModelOutput 외 n개")으로 축약하고, 선택 경로의 노드는 항상 펼쳐 둔다. 묶음을 누르면 펼친다.
- **목록 보기**(760px 이하 기본): 계층별 목록과 선택 경로 표. 키보드: ←/→ 같은 계층, ↑/↓ 이웃 계층, Home/End, Enter 선택, Esc 해제(맵·목록 공통).

### 크게 보기·확대·버전 탭 (UX-2)

- **크게 보기**: 머리글의 토글(`aria-pressed`)이 `.jm-page.is-expanded`(화면 전체 고정 레이아웃, 무대 높이 ≥ 700px)로 전환한다. 포커스는 토글에 남고 `Esc`로 해제된다(열린 원문 뷰어 대화상자가 있으면 그것이 먼저 닫힌다). 해제해도 선택한 노드·확대 상태는 유지되고, 크기가 바뀐 무대는 사용자가 확대하지 않았다면 `ResizeObserver`로 다시 맞춘다. 확대율 %는 `+`/`−` 버튼(×1.25)과 `전체 보기`(맞춤 비율로 복귀)와 함께 동작한다.
- **규칙 버전 탭**: 탐색 기준의 규칙(`rule_id`, `@버전` 제외) 또는 불러온 `RuleVersion` 노드가 한 규칙뿐일 때 그 규칙의 버전 목록을 `전체 · v1 · v2 …`로 보이고 각 탭에 상태 배지(`published/active`=운영 중, `validating/validated`=검증 중, `stopped`=중단, `reverted`=되돌림)를 붙인다. 탭을 고르면 그 `RuleVersion` 노드에서 근거 쪽·실행 쪽으로 닿는 노드·연결만 남긴다(형제 버전은 제외, 계층별 개수·요약도 같은 기준). 버전 데이터가 없으면 탭 영역에 빈 상태 문구를 보인다. 별도 백엔드 조회는 없고 이미 불러온 저장 노드·연결만 사용한다.
- **원문 열기**: `EvidenceSpan` 노드 상세의 `원문 열기`는 `refs`로 원문 뷰어(`GET /api/requests/{id}/revisions/{rev}/document`, [INGEST_API](INGEST_API.md))를 연다. 원문 권한이 없으면 위치만 보이고 '원문 열람 권한 없음'을 안내한다.

## 검증

- 백엔드: `make up` 후 `cd backend && .venv/bin/pytest tests/integration/test_judgment_graph.py`.
- 프런트: `cd frontend && npm run test`(경로 강조 계산, 묶음·키보드 이동, 목록 보기 렌더).
- UX-2: `frontend/src/pages/judgment-map/versionTabs.test.tsx`(버전 탭 목록·필터·빈 상태, 크게 보기 토글·Esc·포커스), `Detail.test.tsx`. E2E는 `frontend/e2e/source-viewer/`(전용 API 8391·vite 5591, `bash e2e/source-viewer/env.sh start`, `npx playwright test -c playwright.source-viewer.config.ts`; `t-ux2` tenant에 규칙 R-UX-01 v1·v2·v3를 시드).
- E2E(실데이터, live Jev 호출): API와 worker 기동 후 `cd frontend && E2E_PORT=5273 E2E_API=http://127.0.0.1:8000 npx playwright test -c playwright.judgment-map.config.ts`. 요청 접수→판단→검토자 수정 승인을 공개 API로 수행하고, 맵의 노드·연결 수와 ID가 `/api/graph/judgment`와 일치하는지, 업무 단계에서 `EvidenceSpan`까지 역추적되는지, 목록 보기 키보드 이동을 확인한다.

## 제한

- 확장 범위는 시작 노드에서 근거 쪽·실행 쪽 단조 확장이다. 같은 `RunStep`이 읽은 다른 출력처럼 옆 가지는 해당 노드를 선택해야(경로 병합) 나타난다.
- `RuleVersion` 적용·`ValidationRun` 라벨은 병행 작업(T32–T34)이 저장해야 실데이터로 나타난다. 이 작업의 시험은 같은 속성·관계로 시드한 노드로 질의 계약을 검증했다.
