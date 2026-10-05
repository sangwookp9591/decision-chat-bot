# 전체 E2E 재실행 — 2026-10-05

**최종: 192개(Chromium 96·WebKit 96) 중 191 통과·0 실패·1 환경 skip·0 미실행.** 모든 대상 시험의 마지막 실제 실행 결과를 합친 집계이며, 마지막 22개 회귀 실행은 22/22 통과했다. 전용 서버·워커를 모두 종료했다.

## 범위와 실행 조건

- 저장소 73d5e72 이후 현재 공유 worktree. 제품 소스는 이 작업에서 수정하지 않았다.
- API `127.0.0.1:11091`, Vite `127.0.0.1:8491`, 새 tenant `t-e2e-all-1005` 및 분리된 학습·extension·rem 표본.
- 기본 `JEV_MODE=mock`. `scripts/e2e/mock_worker.py`는 JevClient 응답 경계만 결정적 표본으로 교체하고 mode=mock을 보존한다. API·Neo4j·작업·검토·규칙·배정은 실제 제품 경로다. 모델 정확도나 외부 Jev 품질을 입증하는 실행은 아니다.
- Chromium·WebKit, `--workers=1`; a11y도 단일 워커. `A11Y_SHOT_DIR`는 이 디렉터리여서 기존 t23 PNG를 덮어쓰지 않았다.
- OrbStack의 공유 Neo4j를 이용했고 다른 서버/워커 및 Docker Desktop은 조작하지 않았다.
- 전체 독립 준비 실행기: `backend/.venv/bin/python scripts/e2e/run.py`. 계정, 30건 목록, schema 오류 워커, 자동 배정 gate, extension 단계 자료를 스스로 준비한다. extension의 재시작 검증 단계는 실제 소유 API와 워커를 종료·재시작한다.

## 집계 방법

파일·브라우저 표는 [TABLE.md](TABLE.md), 시험별 최신 실행 증거는 [latest-results.json](latest-results.json)이다. `scripts/e2e/summarize.py`가 진단 실행과 수정 후 재실행에서 같은 시험의 **마지막 실제 실행 결과**를 합친다. 이는 단일 실행 결과와 구분되며, 새 tenant 전체 실행은 `20261005T152719/`, 수정 영향 96개 실행은 `20261005T154849/`, 마지막 22개 실행은 `20261005T160522/`에 보존했다. serial 실패 때문에 시작하지 못한 시험을 통과로 계산하지 않는다. Extension의 준비 전/후/재시작 phase는 해당 단계에서 실제 실행하고 다른 phase의 skip이 실행 결과를 덮지 않게 한다.

초기 Chromium 진단은 95개 중 53 통과·8 실패·34 skipped(환경/단계 skip 및 serial 후속 미실행 포함), 536.5초였다([baseline.json](baseline.json)). 진단 도중 준비 환경을 수정했으므로 고정 스냅샷의 대조군으로 주장하지 않는다. 이후 일반 전체 두 브라우저 실행은 142개 중 123 통과·6 실패·13 skipped(실제 skip 1, 후속 미실행 12), 825.3초였다([all.json](all.json)). 새 모달 회귀 시험까지 포함한 최종 대상은 192개이다.

## 파일·브라우저별 최종 결과

| 파일 | 브라우저 | 통과 | 실패 | skip | 미실행 | skip 사유 |
|---|---|---:|---:|---:|---:|---|
| a11y/a11y.spec.ts | chromium | 6 | 0 | 0 | 0 |  |
| a11y/a11y.spec.ts | webkit | 6 | 0 | 0 | 0 |  |
| acceptance/gates.spec.ts | chromium | 2 | 0 | 0 | 0 |  |
| acceptance/gates.spec.ts | webkit | 2 | 0 | 0 | 0 |  |
| acceptance/scenarios.spec.ts | chromium | 10 | 0 | 0 | 0 |  |
| acceptance/scenarios.spec.ts | webkit | 10 | 0 | 0 | 0 |  |
| chat-intake.spec.ts | chromium | 14 | 0 | 0 | 0 |  |
| chat-intake.spec.ts | webkit | 14 | 0 | 0 | 0 |  |
| evaluation-labels.spec.ts | chromium | 2 | 0 | 0 | 0 |  |
| evaluation-labels.spec.ts | webkit | 2 | 0 | 0 | 0 |  |
| extension/extension-r.spec.ts | chromium | 6 | 0 | 0 | 0 |  |
| extension/extension-r.spec.ts | webkit | 6 | 0 | 0 | 0 |  |
| extension/extension.spec.ts | chromium | 8 | 0 | 0 | 0 |  |
| extension/extension.spec.ts | webkit | 8 | 0 | 0 | 0 |  |
| judgment-map.spec.ts | chromium | 2 | 0 | 0 | 0 |  |
| judgment-map.spec.ts | webkit | 2 | 0 | 0 | 0 |  |
| learning-human.spec.ts | chromium | 1 | 0 | 0 | 0 |  |
| learning-human.spec.ts | webkit | 1 | 0 | 0 | 0 |  |
| learning.spec.ts | chromium | 1 | 0 | 0 | 0 |  |
| learning.spec.ts | webkit | 1 | 0 | 0 | 0 |  |
| main.spec.ts | chromium | 2 | 0 | 0 | 0 |  |
| main.spec.ts | webkit | 2 | 0 | 0 | 0 |  |
| modal-stack.spec.ts | chromium | 1 | 0 | 0 | 0 |  |
| modal-stack.spec.ts | webkit | 1 | 0 | 0 | 0 |  |
| monitoring.spec.ts | chromium | 1 | 0 | 0 | 0 |  |
| monitoring.spec.ts | webkit | 1 | 0 | 0 | 0 |  |
| p7-fixes.spec.ts | chromium | 7 | 0 | 0 | 0 |  |
| p7-fixes.spec.ts | webkit | 6 | 0 | 1 | 0 | layout-shift entries exist only in Chromium |
| policy.spec.ts | chromium | 1 | 0 | 0 | 0 |  |
| policy.spec.ts | webkit | 1 | 0 | 0 | 0 |  |
| progressive-results.spec.ts | chromium | 1 | 0 | 0 | 0 |  |
| progressive-results.spec.ts | webkit | 1 | 0 | 0 | 0 |  |
| rem-ui.spec.ts | chromium | 3 | 0 | 0 | 0 |  |
| rem-ui.spec.ts | webkit | 3 | 0 | 0 | 0 |  |
| responsive-overflow.spec.ts | chromium | 14 | 0 | 0 | 0 |  |
| responsive-overflow.spec.ts | webkit | 14 | 0 | 0 | 0 |  |
| review-repair.spec.ts | chromium | 1 | 0 | 0 | 0 |  |
| review-repair.spec.ts | webkit | 1 | 0 | 0 | 0 |  |
| screens-ui.spec.ts | chromium | 3 | 0 | 0 | 0 |  |
| screens-ui.spec.ts | webkit | 3 | 0 | 0 | 0 |  |
| source-viewer/source-viewer.spec.ts | chromium | 7 | 0 | 0 | 0 |  |
| source-viewer/source-viewer.spec.ts | webkit | 7 | 0 | 0 | 0 |  |
| task-blocker.spec.ts | chromium | 2 | 0 | 0 | 0 |  |
| task-blocker.spec.ts | webkit | 2 | 0 | 0 | 0 |  |
| webmcp.spec.ts | chromium | 1 | 0 | 0 | 0 |  |
| webmcp.spec.ts | webkit | 1 | 0 | 0 | 0 |  |

## 재현 → 수정 → 검증

| 항목 | 수정 전 재현 | 수정 및 검증 근거 |
|---|---|---|
| 새 tenant 역할·schema 실패 계정 | baseline: labeler/fault 계정 401 | seed.py가 requester/reviewer/operator/admin/labeler 및 f/g/b tenant 준비; evaluation-labels 두 브라우저 통과(all) |
| mock와 live 표기 | baseline: mode가 live여야 한다는 assertion 실패 | 실행 모드를 환경과 비교하고 live5 별도 실행; chat/main 두 브라우저 통과 |
| 30건 목록·rem 고정 제목 | 기존 조건부 skip 및 다른 tenant 자료 의존 확인 | 취소된 목록 표본 30건 준비, rem은 독립 tenant와 seed 반환 request ID; all 두 브라우저 통과 |
| provisional 상태 | baseline: 너무 빠른 mock 응답으로 provisional 관찰 실패 | fixture의 task 응답에 결정적 3초 지연; p7 일반·불확실 두 상태 통과(all); WebKit LayoutShift는 아래 사유로 skip |
| main·acceptance 상세 선택자 | baseline/acceptance-v2~v5: 사라진 code/strong/원시 ID, 숨은 비교 및 체크박스 선택 실패 | 상세 drawer를 열어 표시 계약을 검증, request ID 행으로 선택, 커스텀 체크박스 키보드 Space 조작, API revision 비교 |
| S8/G10 부분 실행과 입력 | acceptance-tail: 앞선 실행 파일에 의존해 request ID 누락; 수정 후 WebKit S8은 전체 결과 pointer dispatch 15초 초과 | S8이 승인·대기 요청을, G10이 권한 비교 요청을 필요 시 직접 생성; 전체 결과는 실제 focus+Enter로 조작하고 동일 노드·저장 수 불변 assertion 유지 |
| S8 조회 준비 시간 | acceptance-v6: WebKit 600초 초과, helpers.ts 순차 judgment 조회에서 중단 | 동일 요청·실행·출력 전체를 최대 8개 요청씩 병렬 조회; assertion과 제한 시간 유지, 마지막 S8 양쪽 통과 |
| 원문 대비 검사 시점 | 수정 후 Chromium axe: 비-anchor 라벨이 합성색 #7a838f, 대비 3.7로 기록됨 | 160ms overlay fade 중 측정 가능성을 제거하도록 유한 animation.finished 대기; 코디네이터는 일반 라벨도 ink-2로 강화 |
| learning-human 완료 대기 | 새 전체 실행 WebKit: 검증 POST 처리 중 이전 승인 notice를 검사해 5초 실패 | 검증 POST 응답 성공을 먼저 확인한 뒤 완료 notice와 DB/API 결과를 검증 |
| source fixture 입력 확인 | 제품 변경 중 새 전체 실행 WebKit: 준비 POST의 chat text가 빈 문자열, 문서 units 비어 실패 | 첨부 후 text 입력·입력값 확인·POST 202와 반환 request ID를 기다리고 chat unit 존재를 명시 검증 |
| mock 레이아웃 분기 | p7-fixture-red: possible 표본에서도 uncertain DOM 1개(예상 0) | mock 모드에서 표본 상태를 명시적으로 검사하고 해당 문장만 가능 응답을 받도록 준비 코드를 수정 |
| Portal 상세창 범위 | fresh-run: S4 검토 사유를 main에서 찾지 못함 | 제품 Overlay portal 반영에 맞춰 판단 상세 dialog 범위에서 같은 API 사유를 검증 |
| chat 중복 제목 | all: 동일 제목 여러 요청에 대한 strict locator 실패 | 생성한 request ID 행으로 제한; learning-chat-final 양쪽 통과 |
| learning 브라우저 간 후보 상태 오염 | all: 두 번째 실행에서 이미 승인된 후보 버튼 assertion 실패 | 실행마다 독립 tenant/제한 mock 워커를 만들고 정리; learning-chat-final 양쪽 통과 |
| source-viewer 준비 | baseline: 버튼 JSON 파싱 실패; source/source-v3: tenant query guard 실패 | 자동 seed, tenant 접두사 전역 ID, 실제 document 응답 위치 비교, 실제 detail 내 evidence 사용 |
| source-viewer focus | all/source-v2: WebKit pointer click 후 복원 대상이 focus되어 있지 않음 | 키보드 Enter로 열어 focus 복원 계약 검증; source-keyboard 및 source-version-final 통과. Safari pointer click 동작을 제품 결함으로 단정하지 않음 |
| extension 진실 자료 | extension-ui1: 승인 전 문구·중복 규칙 노드 strict locator·흐름 설정 버전 불일치 | DB/API에서 단계별 자료 생성, 현재 후보 상태 문구, exact node, run별 저장 버전, 실제 raw output과 비교; ui1-v2/v3 양쪽 통과 |
| extension 자료 부족 후보 | extension-r1: 이전 브라우저가 사용한 후보 상태 때문에 예상 경고 없음 | 매 시험 실제 reviewer API로 후보 생성, 유효한 고유 규칙 ID, 키보드 checkbox; extension-r1-v2 양쪽 통과 |
| extension 목록 키보드 | 선택된 layer가 하나뿐인 상태에서 ArrowRight만 눌러 이동하지 않음 | Home+ArrowDown으로 정해진 다른 레이어 이동 검증; ui1-v3 통과 |
| 자동 배정 gate | 사전 records 파일이 없으면 skip하는 기존 조건 | gates.py가 실제 auto_assign 정책/요청/배정을 수행한 뒤 DB 관계를 읽어 기록; 0건 허용하지 않음, all 양쪽 통과 |

## 제품 결함 — 별도 제품 작업자가 수정

1. 중첩 dialog에서 Escape가 source viewer와 판단 상세를 동시에 닫는다. 새 [modal-stack.spec.ts](../../../frontend/e2e/modal-stack.spec.ts)로 양쪽 실패를 확정했다([modal-keyboard-repro.log](modal-keyboard-repro.log)). 기대: 최상단 viewer만 닫히고 판단 상세와 근거 버튼 focus가 남는다. 코디네이터에 제품 Overlay 수정 요청을 전달했다.
2. source viewer를 연 상태에서 배경 map의 dim 노드 small 텍스트가 axe serious color-contrast를 위반한다. [source-axe-final.log](source-axe-final.log)에서 Chromium·WebKit 양쪽 재현했다. 제품의 dim 대비 또는 배경 inert 처리 검토 요청을 전달했다.

이 두 결함을 skip이나 느슨한 assertion으로 숨기지 않았다. 코디네이터가 공용 Overlay 스택·body portal·배경 inert·근거 라벨 대비를 수정하고, Main에서 근거를 열 때 상위 판단 상세를 닫던 동작을 제거했다. 이 작업자는 제품 소스를 수정하지 않았으며 `20261005T154849/`에서 main/chat/p7/a11y 등 영향 범위를, `20261005T160522/`에서 modal/source 전체와 S8/S9/G10을 새 Vite로 재검증했다. 일반 라벨 대비 강화와 유한 animation 완료 대기를 함께 적용해 중간 fade 색상을 검사하는 문제도 방지했다.

남은 **확정 제품 결함은 없다**. 최종 modal/source 16개와 S8/S9/G10 6개는 [마지막 결과](20261005T160522/results.json)·[로그](20261005T160522/results.log)에서 22/22 통과했다. 기본·수정·수명 주기·실제 재시작 extension 28개는 [ui1](20261005T152719/extension/ui1.json), [r1](20261005T152719/extension/r1.json), [ui2](20261005T152719/extension/ui2.json), [r3](20261005T152719/extension/r3.json) 모두 통과했다.

## skip·live 구분

- 유일한 본질적 환경 skip: WebKit은 LayoutShift PerformanceEntry를 제공하지 않아 `p7-fixes F5 layout-shift`의 브라우저 성능 entry 검사가 불가능하다. 시험에 사유가 명시되어 있고 Chromium에서는 실행했다.
- WebMCP 제품 도구는 양 브라우저에서 handler를 실제 호출하여 권한 없는 ID의 404와 fallback 경로를 검증했다. 외부 실제 WebMCP agent와의 상호운용성을 검증했다고 주장하지 않는다.
- 제품 E2E의 화면/저장 계약은 mock 표본으로 검증 가능하다. 외부 모델의 분류·confidence 분포는 mock으로 대체할 수 없으므로 코디네이터 승인 하에 대표 S2와 X05만 live로 재실행했다.
- live S2 Chromium: 판단 1건, 1개 시험 통과([live-s2.json](live-s2.json)).
- live extension X05: in-scope/out-of-scope 등 판단 4건을 저장 후 같은 자료를 Chromium·WebKit에서 조회, 2개 시험 통과([live-extension.json](live-extension.json)).
- **live 총 5건**, 모두 `mode=live`, `judgment_saved` 저장 확인([live-proof.json](live-proof.json)). 추가 live 호출 없이 워커 종료. extension의 규칙은 기존 mock 자료에서 만든 규칙이고 새 판단 4건의 모델 응답만 live라는 범위를 명확히 한다.

## 필수 검증

- Backend 전체 pytest: 483 passed, 1 skipped, 160.65초([pytest.log](pytest.log)). skip은 `tests/live/test_judgment_live.py::test_two_live_request_shapes`의 opt-in 조건(`JEV_MODE=live`) 미충족이다. 별도 live smoke를 추가로 실행해 비용 한도를 넘기지 않고 승인된 S2·X05 5건을 수행했다.
- Backend `ruff check jevtriage tests`: 0건([ruff.log](ruff.log)).
- Frontend `npm run typecheck && npm run test && npm run build`: 통과, 42개 파일·369개 시험([typecheck.log](typecheck.log), [unit.log](unit.log), [build.log](build.log)).
- 추가 `ruff check scripts/e2e frontend/e2e/source-viewer/seed.py`: 0건([scripts-ruff.log](scripts-ruff.log)).

## 최종 확인

- 시작: 2026-10-05 05:43:24 UTC / 14:43:24 KST.
- 종료: 2026-10-05 07:15:31 UTC / 16:15:31 KST. **총 경과 1시간 32분 7초**(환경 준비·진단·수정·재실행·필수 검증 포함).
- 영향 범위 96개 실행: 15.3분(수정 전 잔여 실패 포함); 마지막 자체 준비 22개 실행: 7.7분, 22 통과. 전체 진단/재시도 이력은 원본 Playwright JSON·로그에 보존했다.
- 최종 집계: Chromium 96 통과, WebKit 95 통과·1 skip; 실패·미실행 0.
- API 11091·Vite 8491 listener 없음, E2E tenant 워커 없음([cleanup.json](cleanup.json)). 공유 Neo4j와 다른 포트의 서버는 종료하지 않았다.
- 반복 DB 알림이 큰 서버 로그 2개는 `.log.gz`로 압축했다. 브라우저 JSON·로그·실패 trace는 보존했다.
- 커밋·push·외부 채널 게시 없음. 제품 변경은 별도 작업자가 수행했으며 이 작업의 변경은 E2E·준비 스크립트·해당 문서·이 증거 디렉터리뿐이다.
