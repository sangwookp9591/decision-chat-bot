# QA-B 운영자·정책·학습·평가·판단 맵 점검

- 일자: 2026-10-05 KST. 제품 코드·명세·핸드오프·기존 테스트를 수정하지 않은 결함 탐색 작업이다.
- 환경: API `11391`, Vite `8791`, tenant `t-qa-b-1005181417`; OrbStack의 기존 Neo4j를 사용했다. `JEV_MODE=mock`, `scripts/e2e/mock_worker.py --tenant …`만 사용했고 실제 Jev 호출은 0건이다.
- 실행 구성: `scripts/e2e/run.py` 및 `frontend/e2e/all.config.ts`를 참조한 이 폴더의 `run.py`, `playwright.config.ts`, `repro.config.ts`. 8191·5391 프로세스 및 공유 Neo4j에 정지·재시작을 하지 않았다.
- 판정: **P1 4건 확정**. 제품 수정은 QA-B 범위 밖이므로 실패 시험을 그대로 남겼다. 환경 시간 초과는 기능 결함으로 합산하지 않았다.

## 점검 체크리스트

| 항목 | 방법 | 결과 | 근거·제한 |
|---|---|---|---|
| 요청·실행 선택 검색 | 실 API 및 독립 HTTP fixture로 요청 전환 | 결함 | QA-B-03: 실행 없는 요청 선택 후 이전 Flow가 남음 |
| Trace 오류·소요시간·버전·단계 상세 | 실 API 단계 열기, fixture의 100ms/config v1, 기존 컴포넌트 시험 | 정상 | `captures/trace.png`, `isolated.log`, `frontend-focused.log` |
| 재생 무부작용 | 실 API 재생→전체 결과, 브라우저 네트워크에서 GET/HEAD 외 요청 0건 | 정상 | `browser.log`의 playback 시험; DB 전체 스냅샷 비교는 기존 통합 시험 범위 |
| 맵 요청 필터·노드 수 | 요청 ID 쿼리로 조회, API node_count=UI 대조 | 정상 | `browser-retry.log` real judgment map |
| 맵 노드 선택·경로 강조·상세 시각 | 실 저장 ModelOutput/EvidenceSpan 선택, 경로 목록과 상세 확인 | 정상 | `captures/map-detail.png`, `captures/map-source.png`; 경로 전체 ID 집합 대조는 미완료 |
| 맵 확대·축소·전체 보기·크게 보기 | 버튼 조작, 확대 비율·expanded 클래스, Escape | 정상 | `repro/journeys.spec.ts`, `browser-retry.log` |
| 맵 목록·키보드·ID 복사 | 목록 수=API, ArrowRight→Enter, clipboard 권한 후 복사됨 | 정상 | `browser-retry.log`, `captures/map-detail.png` |
| 맵 버전 탭 | 기존 컴포넌트 + 독립 브라우저 fixture에서 v2/v3/전체 전환 | 정상(fixture) | `frontend-focused.log`, `version-tabs.log` 1 passed, `captures/map-versions-fixture.png`; 실 API 다중 규칙 버전은 미확인 |
| 맵 원문 열기 | EvidenceSpan에서 뷰어 모달 열기, 원문 권한 계정 추가 시험 | 부분 확인 | 모달 열림 통과; 권한 계정 추가 시험은 복구 후에도 graph 조회 지연으로 미완료 (`recovered.log`) |
| 규칙 후보 목록·사람 제안 | 실제 Neo4j에 3개 correction을 만든 기존 E2E | 정상 | `runtime/results.log` human proposal |
| 규칙 승인·섀도·게시 | 관리자 승인→검증→사람 확정 정답 3건·부작용 0→게시 | 정상 | 같은 E2E 통과; fixture 품질은 모델 품질 증거가 아님 |
| 규칙 효과 정답 표본 수·미확정 | reviewer/operator로 게시 후 관찰 | 정상 | 기존 learning-human E2E의 사람 확정 정답 표본 수·미확정 검증 |
| 규칙 기각·중단·되돌리기 | 기존 백엔드 통합 시험 실행 대상 | 미확인 | `test_rules_integration.py`; 브라우저로 기각·되돌리기를 직접 완료하지는 않음 |
| 학습 reviewer/operator 읽기 전용·변경 403 | 브라우저 버튼 비활성·제안 숨김 및 실제 HTTP matrix | 정상 | `runtime/results.log`, `access.log`, `access-retry.log` |
| 평가 튜닝·칩·1–4·Enter·J/K·보류 사유 | 기존 실제 API E2E, 키보드 이동·저장 | 정상 | `runtime/results.log` 첫 시험; K는 기존 컴포넌트 수준, 새 실 브라우저 시퀀스는 J |
| 평가 최종 분할 예측 숨김·375px | 기존 E2E 재시험 | 정상 | `retry2.log` final split 1 passed |
| 평가 불일치·합의 | 서로 다른 두 사용자 투표 후 합의 POST | 결함 | QA-B-02 확정 수 감소, QA-B-04 같은 팀 집합을 불일치 처리 |
| 평가 서버 값·타입 검증 | 잘못된 값/타입/null을 실제 PUT | 결함 | QA-B-01 |
| 모니터링 한국어 날짜·집계·대기·경보 | 실 집계 숫자 대조, 모바일 캡처, 기존 UI 시험 | 정상(확인 범위) | `runtime/results.log`, `captures/mobile-monitoring.png`, `frontend-focused.log`; 보완 대기 0/미수집 표시 및 수집 불완전 경보 확인 |
| 모니터링 count-up·기간 필터 계산 | 기존 컴포넌트 시험·화면 관찰 | 부분 확인 | 애니메이션 프레임 추적 및 비영(非零) 보완 대기 지표 DB 대조는 미완료 |
| 정책 필드 폼·범위·서버 검증 | 확신도 1.5 거부→원래값 복원→검증 통과, 폼 컴포넌트 시험 | 정상(확인 범위) | `runtime/results.log`, `frontend-focused*.log`; 모든 필드의 모든 경계값은 새 브라우저에서 순회하지 않음 |
| 정책 게시 사유·게시·이력·diff·되돌리기 | policy_editor 실제 E2E | 정상 | v1→v2→v3, `runtime/results.log` |
| 정책 JSON 보기·읽기 전용 | 기존 Policy 컴포넌트 시험 및 7역할 화면 조회 | 정상(확인 범위) | `frontend-focused.log`, `screens-*.json` |
| 정책 실행 고정 버전 유지 | 기존 백엔드 정책/규칙 통합 시험 | 미확인 | 새 브라우저에서 게시 전후 run 버전 동시 비교는 미완료 |
| 역할별 주요 API | 7역할×12개 읽기 API + 비인가 정책/규칙 쓰기 403 | 정상 | 처음 4역할 통과, 나머지 3역할 재시험 통과; 합계 114개 기대 상태 검사 |
| 역할별 9개 화면 | 역할별 로그인 후 전체 route 방문·화면 텍스트·pageerror 수집 | 정상(표시/오류) | `screens-{requester,reviewer,team_member,operator,policy_editor,rule_admin,labeler}.json`; 권한 결정 근거는 API matrix |
| 다크 모드·375px | 범위 6화면, 시스템 dark 강제, 가로 overflow 0 | 정상 | `captures/mobile-*.png`, `browser.log` 6건 |
| 키보드·콘솔 | 평가 단축키·맵 탐색·Tab; 7역할 9화면 pageerror 수집 | 정상(확인 범위) | `screens-*.json` errors=[]; 개발 서버 Router 경고는 범위 밖 |

주요 증거: [평가 실패 로그](evaluation-repro.log), [집합 순서 실패 로그](evaluation-order-repro.log), [stale Flow 캡처](captures/stale-flow-isolated.png), [평가 저장 응답](captures/evaluation-state.json).

## 확정 결함

### QA-B-01 · P1 · 평가 라벨의 값과 타입을 검증하지 않고 저장

- 재현: labeler로 로그인 → tuning 표본 `pharma-060`에 모든 키를 포함하되 `ai_need='INVALID'`, `team_set='not-array'`, `risk_areas=123`인 라벨 PUT. 같은 시험에서 필수 단일 선택값을 null로도 전송한다.
- 기대: HTTP 422, 정답 데이터에 허용되지 않은 값·타입이 저장되지 않음.
- 실제: 두 입력 모두 HTTP 200 `{"id":"pharma-060","status":"confirmed"}`. 이어지는 GET에서도 저장된 null 라벨을 확인했다.
- 영향: UI의 선택지 제약을 우회해 평가 정답 및 진행률에 잘못된 데이터를 넣을 수 있다. 사용자 역할은 정상 labeler이며 권한 상승 문제는 아니다.
- 실패 시험: `repro/test_evaluation.py::test_invalid_label_values_rejected` (2개 case).
- 근거: `evaluation-repro.log`, `captures/evaluation-state.json`.
- 코드 단서: `backend/jevtriage/evaluation/service.py::_validate_labels`가 키 집합만 검사하고 각 필드 enum·타입을 검사하지 않는다.

### QA-B-02 · P1 · 합의 완료 후 확정 진행률이 후퇴

- 재현: labeler/reviewer가 `pharma-059`에 다른 라벨을 확정 → labeler가 `/consensus` POST → 목록 progress 재조회.
- 기대: 합의된 표본도 확정 수에 포함되고, 합의 직후 완료 수가 감소하지 않음.
- 실제: 합의 상태는 `resolved`인데 confirmed **5→4**, remaining **54→55**, percent **8→7**로 변한다.
- 실패 시험: `repro/test_evaluation.py::test_consensus_preserves_completed_progress`.
- 근거: `evaluation-repro.log`, `captures/evaluation-state.json`.
- 코드 단서: `_latest_by_user`가 본인 투표를 `consensus_confirmed`로 바꾸지만 `progress_summary`는 `confirmed`만 센다.

### QA-B-03 · P1 · 실행 없는 요청을 선택해도 이전 요청의 Flow가 남음

- 재현: 실행이 있는 요청 A의 실행 관찰을 열기 → 요청 검색에서 실행 없는 요청 B 선택.
- 기대: A의 Flow/재생 결과/Trace를 지우고 B에 실행 기록이 없다는 빈 상태를 표시.
- 실제: 실행 선택은 “이 요청의 실행 없음”으로 비활성인데 이전 요청 A의 단계와 성공 결과가 그대로 보인다.
- 실패 시험: `repro/observatory-isolated.spec.ts` 첫 시험; 실 API 변형은 `repro/journeys.spec.ts`의 observatory selecting 시험.
- 근거: `isolated.log`, `captures/stale-flow-isolated.png`; **복구 후 실 API에서도 0개 기대/8개 실제로 확정** (`recovered.log`, [실환경 캡처](captures/stale-flow.png)). `stale-real.log`는 복구 전 환경 실패이다.
- 코드 단서: `frontend/src/pages/Observatory.tsx`의 요청 onChange는 requestId/runId만 변경하며, 빈 runId일 때 effect가 즉시 return해 기존 flow/playback/detail을 초기화하지 않는다.

### QA-B-04 · P1 · 같은 팀 집합을 선택한 순서가 다르면 평가 불일치 처리

- 재현: `pharma-058`에 첫 사용자는 `team_set=['AI팀','IT팀']`, 두 번째는 `['IT팀','AI팀']`으로 확정. 나머지 라벨은 동일하다.
- 기대: 팀 집합이 같으므로 `agreed`.
- 실제: `consensus_required`로 표시되어 불필요한 합의 작업을 요구한다. 칩은 선택 순서대로 배열을 만들 수 있어 UI에서도 도달 가능한 입력이다.
- 실패 시험: `repro/test_evaluation.py::test_team_set_order_does_not_create_disagreement`.
- 근거: `evaluation-order-repro.log`, `captures/evaluation-state.json`.
- 코드 단서: `consensus_state`의 `json.dumps(sort_keys=True)`는 객체 키만 정렬하고 집합 의미의 배열 순서는 정규화하지 않는다.

## 실행 및 재현

```sh
# 저장소 루트; 서버는 시험 후에도 추가 조사용으로 대기한다(최대 30분).
backend/.venv/bin/python artifacts/review/qa-full/qa-b/run.py 'policy.spec.ts|monitoring.spec.ts|learning-human.spec.ts|evaluation-labels.spec.ts|judgment-map.spec.ts'
# 다른 터미널, 서버가 준비되면
backend/.venv/bin/pytest -q artifacts/review/qa-full/qa-b/repro/test_evaluation.py
backend/.venv/bin/pytest -q artifacts/review/qa-full/qa-b/repro/test_access.py
cd frontend
E2E_BASE_URL=http://127.0.0.1:8791 npx playwright test --config=../artifacts/review/qa-full/qa-b/repro.config.ts
# 저장소 루트에서 조사 종료
# touch artifacts/review/qa-full/qa-b/runtime/STOP
```

실 환경 지연 때문에 실패한 초기 시험은 `runtime/results.log`, `retry.log`, `browser.log`, `access.log`에 남겨 두었다. 같은 항목 재시험 로그를 함께 읽어야 하며 최초 실패를 제품 결함이라고 단정하지 않는다. 원본 Playwright trace에는 세션 쿠키가 포함될 수 있어 전달물에서는 제거하고 캡처·실패 단언·로그만 보존한다.

## 환경 제약과 못 본 항목

1. 코디네이터가 18:29 KST 공유 Neo4j 재시작을 공지했다. 해당 구간의 연결 오류는 별도 환경 실패로 취급했다. 공유 Neo4j에서 `TransactionTimedOutClientConfiguration`이 발생해 접수 503, 목록/검토 결정 500, 세션 로딩 지연이 간헐적으로 발생했다. `intake-probe.json`, `runtime/api.log`, `retry2.log`에 기록되어 있다. 코디네이터에 escalation했으며 DB를 재시작하지 않았다.
2. 기존 판단 맵 E2E의 전체 Correction/ReviewDecision 연결 대조는 검토 결정 500 때문에 완료하지 못했다. 대신 저장된 실행/근거 그래프로 맵 UI 시험을 완료했다.
3. 학습 충분 표본의 실데이터 효과 판정, 실제 다중 버전 탭, 브라우저에서 규칙 기각·되돌리기, 모든 정책 필드 경계값, 고정 run 버전의 게시 전후 UI 비교, 비영 보완 대기 지표 대조는 미완료다. 컴포넌트/기존 통합 시험과 실제 여정 증거를 구분했다.
4. React Router 업그레이드, IdP/MFA 및 G10/G12/G13은 요청에 따라 결함 대상에서 제외했다.
5. QA-B는 수정 단계가 아니므로 `docs/architecture`와 제품 파일 변경은 하지 않았다. 발견 결함에 대한 수정→통과는 후속 수정 작업의 책임이다.

## 최종 검증 결과

- `ruff check jevtriage tests`: **All checks passed** (`ruff.log`).
- 전체 `pytest -q` 첫 실행: **227 passed, 7 failed, 32 errors**, 코디네이터의 DB 재시작 공지를 받은 뒤 SIGINT 중단 (`backend-pytest.log`). 실패·오류는 환경 복구 후 재판정 대상이며 전체 통과를 주장하지 않는다.
- 관련 프런트 컴포넌트 10파일/61시험: 최초 **60 passed + 1 timeout**; 해당 1시험을 단독 30초 제한으로 재실행해 **1 passed** (`frontend-focused.log`, `frontend-focused-retry30.log`). 제품 변경 없이 통과했다.
- API 역할 매트릭스: 최초 4 passed, 환경 실패 3건은 재실행 **3 passed**.
- 평가 결함: 기대 422 대 실제 200 2건, 합의 진행률 감소 1건, 팀 집합 순서 불일치 1건, 총 **4 failed**가 의도된 재현 결과이다.
- 실행 관찰 독립 fixture: stale Flow **1 failed**, 재생·Trace **1 passed**. 실 API stale Flow는 DB 복구 후에도 **0 기대/8 실제**로 실패해 독립 fixture 결과를 확인했다 (`recovered.log`).
- 7역할×9화면: 재시험 합산 모두 표시 확인·pageerror 0. 375px/dark 6화면은 6 passed.
- 실제 판단 맵 탐색 시험은 통과했으나 원문 권한 계정의 콘텐츠 로딩 완료는 복구 후에도 graph 조회 15초 초과로 추가 확인하지 못했다. 모달 열림만 확인한 것과 원문 콘텐츠 성공을 구분한다.
- 프런트 제품 파일은 수정하지 않았으므로 전체 typecheck/build는 이 QA에서 추가 실행하지 않았다.
- 복구 후 `JEV_MODE=mock pytest -q`: 첫 `test_api_preview`에서 Neo4j 트랜잭션 시간 초과가 다시 발생했다. 코디네이터의 “지연 재발 시 즉시 멈춤” 지시에 따라 중단: **1 failed in 37.21s** (`backend-pytest-recovered.log`). 전체 통과 조건은 충족하지 못했다.
- 종료: 18:37 KST 전용 실행기의 STOP으로 API·Vite·워커를 정리했고 `11391/8791 LISTEN 없음`, QA-B pytest/worker/run.py 프로세스 없음으로 확인했다. 공유 Neo4j는 이 작업자가 정지하지 않았다.
- 변경 파일은 `artifacts/review/qa-full/qa-b/**`뿐이며 커밋·푸시는 하지 않았다. 재현 시험의 의도된 실패 5개 case(평가 4 + Flow 1)는 수정 담당자가 이어받아야 한다.

## 후속 작업

1. QA-B-01~04를 담당자에게 배정하고 해당 실패 시험을 먼저 실행한 뒤 수정한다.
2. 공유 DB 지연 원인을 분리한 환경에서 전체 pytest와 미확인 항목을 다시 점검한다. 원문 권한 계정의 graph 조회 직후 지연이 관찰됐다는 사실은 코디네이터에 전달했으며 원인으로 확정하지 않았다.
3. UI·API 버그 4건은 환경 시간 초과와 독립된 실패 단언으로 확정했으므로 DB 안정화를 기다리지 않고 수정 설계를 진행할 수 있다.
