# T21 보강(V2) — G03·G05·G06 증거

실행: 2026-10-03 (UTC 11:33) · 증거 폴더 `artifacts/validation/t21-gates/20261003T113332Z/` · 명령 `ACC_OUT_ROOT=artifacts/validation/t21-gates ACC_PYTEST_ARGS=tests/acceptance/acc_e_gates.py ACC_UI_ARGS=gates.spec.ts make test-acceptance` (기본 `make test-acceptance`는 두 파일을 함께 포함한다)
연동: **실연동** Jev `JEV_MODE=live`(`jev-1.13.0`, qset-v2, catalog-v2, judgment-v1), 실제 Neo4j(공유 컨테이너, 정지 없음), 전용 tenant `t-acc21-<MMDDhhmm>g`(이번 실행 `t-acc21-10031133g`), `--tenant` 제한 worker. 입력은 비민감 가상 문서·문장. 기반 판정은 `artifacts/validation/t21/20261003T104827Z/gate-evidence.md`.
코드: HEAD `e55b42d` + 미커밋 작업 트리(아래 "수정" 포함).

## 결과 요약

| 구분 | 실행 | 결과 |
| --- | --- | --- |
| 백엔드 `acc_e_gates.py` | 5 | **5 통과 / 0 실패 / 0 skip** (`pytest.log`, `junit.xml`) |
| UI `gates.spec.ts`(Playwright) | 2 | **2 통과 / 0 실패 / 0 skip** (`ui.log`, `ui/gates-ui-evidence.json`, `ui/g05-*.png`, `ui/g06-*.png`) |
| 전체 `make test-acceptance`(별도 실행 `20261003T112514Z`) | 백엔드 40 / UI 12 | 백엔드 38 통과·2 실패, UI 12 통과 — 실패 2건은 게이트 시험이 아님(아래 "다른 시험 실패") |
| 전체 `backend/.venv/bin/pytest`(기본 수집) | 136 | **135 통과 / 0 실패 / 1 skip** |
| `npm run test` / `npm run typecheck` | 37 / — | 37 통과 / 통과 |

모든 ID·값은 `records/records.jsonl`(`g05_auto_assign`, `g06_policy_versions`, `g06_graph`, `g03_short_requests`, `g03_citation_variability`)에 있다.

## 판정

| 게이트 | 판정 | 요약 |
| --- | --- | --- |
| G05 업무(자동 배정) | **통과** — 이전 "제한 있음"의 live 자동 배정 증거 공백 해소 | 허용 정책 + 실제 Jev 5건 중 3건 자동 배정 성공, 저장·API·화면 대조 일치. 나머지 2건은 사유가 기록된 대로 배정 0. |
| G06 정책·그래프 | **통과** | (a) 버전 고정·게시·rollback(v(n+2)=v(n))·A 불변, (b) Cypher 관계 = Topology API = 업무 API = Topology 화면·업무 화면. |
| G03 판단 | **통과(제한 있음, 품질 지표 보고)** | 짧은 요청은 근거를 합성하지 않고 `근거 미완료`로 검토 대기(9/9, 허용 정책 아래서도 배정 0). 근거 인용 가변성은 3회×2입력으로 측정(아래). |

## G05 — 자동 배정 실연동

**정책.** tenant 정책 v1 → v2 게시: `auto_assign=true` **하나만** 변경, 임계값은 기본값 유지 — Choice confidence 0.8(4항목), `risk_clear_max=0.2`, Noul 불확실 대역 [0.35, 0.65], 근거/카탈로그 Noul 0.6. 근거: 서버 불변 조건 안의 안전 기본값이고(`risk_clear_max>0.5` 등은 게시 자체가 거절됨), 아래 요청이 기본값에서 통과해 완화할 필요가 없었다. 조건 우회·임계값 완화 없음.

**요청 5건**(문장에 데이터·권한 확보·긴급 아님·규제/안전 무관·AI 불필요를 명시한 `.md` 문서 1개 + 한 줄 안내문, 실제 Jev; `records.g05_auto_assign.requests`):

| 문서 | 요청 ID | 결과 | eligibility 사유 |
| --- | --- | --- | --- |
| 매출 리포트 화면 | `req_1f8e932e14304c18a704b11d4ea38608` | **배정 완료**(Assignment 1, `pathway=auto`, Task 1) | 사유 없음 |
| 재고 현황 화면 | `req_9db1975261e141a8bde2988463bad2e7` | **배정 완료**(Assignment 1, `auto`, Task 1) | 사유 없음 |
| 주문 ETL+현황 화면 | `req_ff2058f4199847e0928a1a3b741b2ee7` | **배정 완료**(Assignment 1, `auto`, Task 2, PRECEDES 1) | 사유 없음 |
| 공지사항 목록 화면 | `req_55aca70ae9a3410f8ff5ce4aa8935a99` | 검토 대기, 배정 0·Task 0 | `Noul 참여 불확실: business_involvement` |
| 근태 CSV 버튼 | `req_189612565e914a18a61efd177175889d` | 검토 대기, 배정 0·Task 0 | `Noul 참여 불확실: business_involvement`, `업무 책임 또는 산출물 누락`(업무 분해가 `미정` 1건) |

(같은 5개 문서를 세 번 실행했을 때(수동 탐색 포함 2회 + 이 실행, 전체 실행 `20261003T112514Z`) 모두 3건 성공·2건 같은 사유 대기였다. 표본이 작아 live 신호 가변성은 배제하지 못한다.) 대기된 2건은 조건이 정상적으로 막은 것이므로 우회하지 않았다.

**성공 3건의 저장 대조**(Cypher, `acc_e_gates.compare_stored_to_api`): Assignment 1개(`pathway=auto`, run=활성 run), `HAS_TASK`(Request→Task) = 초안 업무 수, `ASSIGNED_TO{role}` lead 1·collab 1/업무, 실제 선행에만 `PRECEDES`(ETL → 화면, 의존 업무는 `막힘`·선행은 `대기`), 검토 대기·ReviewDecision 0, Run 고정 정책 버전 = 2, API `/api/requests/{id}/topology`의 엣지 집합(3·3·7개) = Cypher 집합, `/api/tasks`의 `orgs`·`predecessor_tasks` = 저장 관계. **화면**(UI, 검토자): 업무 화면에 각 Task가 id·제목·`주관 IT팀`·협업 `현업`·상태(`막힘 · 데이터 연결·ETL`)와 함께 표시, 상세 패널의 선행/후행 업무 일치(`ui/gates-ui-evidence.json` `g05_tasks_screen`, `ui/g05-tasks-auto-assigned.png`).

**검토 승인 경로의 배정·동시 승인 중복 0**: 변경 없이 T21 증거 재사용 — `t21/20261003T104827Z`의 `b_duplicate_assignment`(같은 멱등키 8중 동시 200 동일·배정 1, 두 검토자 경합 [200,409]·배정 1), `s2`, `s7`. 이번 실행의 G06(b)는 자동 배정되지 않으면 검토 승인(`decide approve`)으로 이어지게 작성했으나 첫 시도가 자동 배정되어 그 분기는 실행되지 않았다(재사용 증거로 충족).

**제한.** 자동 배정은 첨부 문서에서 *저장된 근거 span*이 있을 때만 성립한다. 첨부 없이 문장만 제출한 요청은 근거가 영속되지 않아(아래 G03·R-E1) 자동 배정 대상이 되지 못한다 — 이번 5건이 모두 문서 첨부인 이유. 위험·긴급·정보 부족 요청은 T21 `b_auto_assign_zero`가 별도로 배정 0을 증명.

## G06 — 정책·그래프

### (a) 정책 버전 고정과 rollback (`g06_policy_versions`)
- v(n)=2(자동 배정 on): 요청 **A** `req_d357925bd2494277a83d7c3a15473bed`(`run_44ee0145…`) → **배정 완료**, 사유 없음.
- v(n+1)=3 게시(변경: Noul 불확실 대역 [0.35,0.65] → [0.0,1.0], 더 엄격한 불변 조건 안 변경; 사유 필수 기록) → 같은 문서 요청 **B** `req_08db5ed97043438491c0faa6e8bccc34`(`run_d3a9f4b3…`) → **검토 대기**, 배정 0, 사유 `Noul 참여 불확실: ai_team_involvement / it_team_involvement / business_involvement`.
- rollback(target=2) → **v(n+2)=4**, 내용이 v(2)와 동일(`config` 완전 일치). 같은 문서 요청 **C** `req_818f3b754ad64d9da03a9de8afa4f5ff`(`run_bfe2cf12…`) → v4로 처리, **배정 완료**, 사유 없음(B와 달리 허용으로 복귀).
- Run 버전 고정: API `runs[*].versions.config` A=2, B=3, C=4 = Neo4j `Run.config_version`(Cypher) A=2, B=3, C=4.
- A의 기록 불변: 게시·rollback 이후 A의 판단(JSON 전체)·run 목록(versions 포함)·업무 id·집계 카운트가 이전 스냅샷과 **완전 동일**.
- 정책 이력 {2,3,4} 모두 보존(`/api/policy/versions`).

### (b) Neo4j 관계 ↔ Topology/업무 화면 (`g06_graph`, `ui/gates-ui-evidence.json` `g06_graph_ui`)
- 요청 `req_1cd5849c729e411bb7cb9e56eddceb12`(ETL + 화면, 자동 배정): Cypher로 조회한 엣지 7개 — `HAS_TASK` 2, `ASSIGNED_TO` 4(lead/collab × 2 업무, 조직 `it`·`business`), `PRECEDES` 1(`데이터 연결·ETL` → `화면·리포트 개발`).
- 같은 집합이 `GET …/topology?kind=business` 응답과 일치(노드: request 1·task 2·org 2).
- **UI(Playwright)**: 실행 관찰 → 업무 Topology 탭의 노드 5개(`data-node-id/type`)와 관계 목록 7개(`data-edge-*`)가 Cypher 집합과 **집합 동일**, 업무 화면의 두 업무와 선행/후행 표시가 PRECEDES와 일치(스크린샷 `ui/g06-topology-business.png`, `ui/g06-tasks-screen.png`).

### 발견·수정한 결함 (최소 수정)
1. **업무 Topology 화면이 관계를 표시하지 않음**(`frontend/src/pages/Observatory.tsx`): API는 `edges`(HAS_TASK/ASSIGNED_TO/PRECEDES)를 주는데 화면은 노드 카드만 그려 "관계가 화면에 보이는가"를 만족하지 못했다. 노드 카드에 `data-node-id/type`을 넣고 `저장된 관계` 목록(`<ul class="obs-edges">`, 항목 `from —KIND(role)→ to`)을 추가했다(`observatory.css` 1규칙 추가). typecheck·Vitest 37 통과, UI 시험으로 일치 확인.

## G03 — 근거 확인 (품질 지표, 결과 위조 없음)

**짧은 요청의 안전 처리**(`g03_short_requests`): 서로 다른 한 줄 요청 3종 × 3회 = 9건을 자동 배정 허용 정책(v2) 아래에서 실행했다. 9/9 모두 인용 0건 → `근거 미완료`(+`개발 가능성 미충족`, `미정 분류: feasibility` 등)가 사유에 포함, 상태 `검토 대기`, **배정 0·업무 0**. 인용된 근거가 있다면 원문 발췌인지 단정(없음). 근거를 합성해 채우는 경로는 관찰되지 않았다. 분류 자체는 `feasibility=정보 부족`, `urgency=판단 보류`로 보류 처리(요청 ID는 records).

**근거 인용 가변성**(`g03_citation_variability`, 같은 문서를 새 요청 3건으로 제출, 인용 키 = (질문, 파일·줄 범위)):

| 입력 | 실행별 인용 수 | 질문별 인용(핵심 4종) | 합집합 / 교집합 | 쌍별 Jaccard | 인용 위치(파일·줄) 합집합/교집합 |
| --- | --- | --- | --- | --- | --- |
| 매출 리포트 화면 문서 | 7, 6, 6 | feasibility 2·ai_need 2·urgency 1~2·lead_org 1 | 7 / 6 | 0.857, 0.857, 1.0 | 2 / 2 (3회 모두 같은 2개 줄 인용) |
| 주문 ETL 문서 | 6, 7, 6 | 동일 패턴(lead_org 1~2) | 7 / 6 | 0.857, 1.0, 0.857 | 2 / 2 |

- 인용 0건 실행: 0/6. 3회 반복에서 인용 집합 차이는 질문별 1개(urgency 또는 lead_org)에 한정(Jaccard ≥ 0.857). 인용은 모두 문서 원문 발췌(단정 통과).
- 보정 전 지표 정의 오류 1건을 수정: 첫 실행은 per-request `attachment_id`를 인용 키에 넣어 교집합이 항상 0으로 나왔다 — 키를 (질문, 파일·줄 범위)로 바꿔 재실행한 위 값이 유효. 폐기한 값은 증거에 남기지 않았다.
- 별도 관찰(T21 `s5_citation_coverage`, 전체 실행 `20261003T112514Z`): 같은 문서 묶음에서 한 시도가 **모든 Choice가 임계 미만·위험 미확정 + 인용 0건**으로 나와 해당 시험이 실패했다 — 이 시도는 판단 신뢰도 전체가 낮은 live Jev 실행이며, 시스템은 합성 없이 `근거 미완료`로 검토 대기 처리했다(위조 없음 확인). 인용 가변성은 문서 입력에서는 작지만 실행에 따라 0건으로 무너질 수 있다는 위험으로 남긴다.

**판정.** 안전 처리·비합성: 통과. 가변성: 문서 입력에서 측정 범위(2입력×3회)는 낮지만, 이 표본은 작고 한 번의 전체 실행에서는 드문 저신뢰 실행도 나타났다 → "통과(제한 있음)", 임계 보정은 T09 사안(R1 유지).

## 보고만 하는 항목

- **R-E1 (T09/T10)** 문장만 제출(첨부 없음)한 요청은 `outputs[*].evidence`는 문서 span만 담고 채팅 문장 근거(`chat:<n>`)는 저장·표시되지 않는다(코드 확인: `judgment/service.py`가 `units`(문서)에 속한 인용만 `eligible`로 인정, 저장 span은 첨부 기준). 탐색 중 명확한 장문 텍스트 요청 1건(정책 v1)은 인용 0건인데도 사유에 `근거 미완료`가 없었다 — 채팅 근거가 내부적으로 연결되었으나 저장되지 않은 것으로 **추정**(미확정, 단건 관찰). 자동 배정을 기대하는 사용자는 문서를 첨부해야 하는 점을 제품 문구/정책 설명에 반영할 필요.
- **R-E2 (공유 환경)** 첫 전체 실행(폴더는 보존하지 않고 폐기)에서 요청 3+1건이 `LookupError`로 실패해 `judgment_pending`에 고착됐다. Job `owner_id`가 전용 worker와 다르고(다른 작업자의 **tenant 제한 없는 worker**가 내 tenant Job을 가로챈 것으로 판단, 해당 worker는 이후 소멸) 재실행에서 재현되지 않았다. 다만 **실패한 Run이 있어도 Request가 `judgment_pending`으로 남는 것**은 사용자 화면에서 영구 처리 중으로 보이는 위험이다(실패 Run은 `failed`, Request만 미갱신). T21 실패 시험(`s8_failed`)은 잘못된 키 worker 경로로 상태 `failed|실패`를 확인했으나, 이 `LookupError` 경로는 Request 상태를 바꾸지 않았다 — T08 확인 요청.
- **R-E3 (T21 하네스)** `.data/t21` journal이 실행마다 누적(수 MB)될 때 `acc_d::test_g09_summary…`의 `collection.complete`가 False로 실패했다(전체 실행 `20261003T112514Z`). 새 `ACC_DATA_DIR`에서 `acc_d` 4건 통과로 확인(데이터 디렉터리 비움). 코디네이터 확인 필요: 누적 journal 용량/무결성 때문에 `complete`가 거짓이 되는지.
- **다른 시험 실패(전체 실행 `20261003T112514Z`)**: ① `acc_a::test_s5_citation_coverage_across_attempts` — 위 G03 관찰의 저신뢰 시도(기존 T21 가변성 제한과 동일 성격), ② `acc_d::test_g09_…` — R-E3. 게이트 시험(`acc_e`)은 같은 실행에서도 통과.
- 이번에 추가·수정한 시험 파일은 ruff 통과(`acc_e_gates.py`·`harness.py`·`provision.py`만 검사; 전체 `make lint`는 실행하지 않음).

## 변경 파일

`backend/tests/acceptance/acc_e_gates.py`(신규), `backend/tests/acceptance/{harness.py,provision.py,env.sh,run.sh}`(전용 tenant `g` 추가, 증거 폴더·시험 선택 변수 추가), `frontend/e2e/acceptance/gates.spec.ts`(신규), `frontend/src/pages/Observatory.tsx`·`frontend/src/pages/observatory/observatory.css`(Topology 관계 표시), `TASK.md`(T21 행 메모).

## 재현

```sh
make up
make test-acceptance            # acc_a–e + Playwright(scenarios, gates), 증거는 artifacts/validation/t21/<ts>/
ACC_OUT_ROOT=artifacts/validation/t21-gates ACC_PYTEST_ARGS=tests/acceptance/acc_e_gates.py ACC_UI_ARGS=gates.spec.ts make test-acceptance   # 게이트만
```
`ACC_TENANT`를 쓰면 같은 값으로 tenant가 재사용되어 이전 데이터가 남으니, 새 증거에는 비워 둔다(기본은 시각 기반 새 tenant). 비밀: `.env`는 읽기 전용으로만 사용, 값은 어디에도 기록하지 않았다.
