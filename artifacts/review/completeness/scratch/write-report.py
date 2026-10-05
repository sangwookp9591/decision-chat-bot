import json,re
from pathlib import Path
root=Path('artifacts/review/completeness');scratch=root/'scratch'
files=['e2e-readonly-results.json','e2e-static-results.json','e2e-safeextra-results.json','e2e-seeded-results.json']
rows=[]
def walk(s):
 for spec in s.get('specs',[]):
  for t in spec.get('tests',[]):
   result=t.get('results',[{}])[-1];f=spec.get('file','').split('/suite/')[-1]
   if f.startswith('suite/'):f=f[6:]
   rows.append((f,spec['line'],spec['title'],t['projectName'],t['status'],result.get('duration',0)))
 for child in s.get('suites',[]):walk(child)
for name in files:walk(json.loads((scratch/name).read_text()))
header='''# 역할별 브라우저 완결성 감사

- 점검: 2026-10-05, 공유 current worktree. 점검·보고 전용이며 제품 코드·스펙·설계·아키텍처 문서를 수정하지 않았다.
- 전용 환경: API **10391**, Vite **7691**, tenant **t-audit-e2e-1005**, `JEV_MODE=live`, `--tenant t-audit-e2e-1005 --concurrency 1 --max-attempts 1`. OrbStack의 별도 Redis **16391**만 중지·재시작했다. 공유 Neo4j·8191·5391은 건드리지 않았다.
- 역할: requester, reviewer, team_member, operator, policy_editor, rule_admin, labeler. 계정 시드: `scratch/seed.py`, 역할 근거 `backend/jevtriage/auth/policy.py:24`, `scripts/bootstrap_dev.py:17`.
- 실제 외부 판단은 **5개 Run**만 수행했다. `scratch/live-final-proof.json`의 5개 모두 `mode=live`, `status=judgment_saved`; 이후 live 워커를 종료했다. 취소/키보드 접수 시험의 추가 Job은 처리하지 않았다.
- 탐색 도구: ego-browser(Chromium); 기존 E2E: Playwright Chromium·WebKit, 전부 `--workers=1`, 재시도 0. 원본 시험은 수정하지 않고 `scratch/suite` 복제본의 tenant 하드코딩 및 출력 경로만 격리했다. 원본 t23 PNG를 덮어쓰지 않았다.
- **범위 제한(감사 종료 시 미완료)**: 전체 E2E의 새 판단 생성 수는 5건 상한과 충돌한다. 코디네이터에 mock 전체 실행 + live 탐색 5건 분리를 문의했으며, 완료 보고 전까지 응답이 없어 추가 외부 호출과 mock 전환을 하지 않았다. 현재 결과를 전체 E2E 통과로 해석하면 안 된다.

## 요약

기존 E2E 94개를 두 브라우저에서 합산 실행해 **78 통과, 14 실패, 2 건너뜀**이다. 실패 2개는 평가 시험의 저장 대기 누락, 12개는 전용 fixture/tenant 부족이다. 별도 결함 재현 시험에서는 **제품 P1 두 건이 Chromium·WebKit 모두 실패**했다. 전체 백엔드는 `466 passed, 1 skipped in 94.75s`, Ruff는 `All checks passed!`였다.

## 여정별 결과

| 역할·여정 | 등급 | 실측 결과와 근거 |
|---|---|---|
| 요청자 텍스트 접수→잠정→최종→새로고침 복원 | 완료 | live 1~3, 5개 Run API 대조. `scratch/live-results.json`, `e2e/live-01.png` |
| PDF/DOCX/MD 동시 첨부·근거 원문 | 완료 | 실제 3종 fixture 동시 업로드, 4건 근거 연결과 원문 강조 확인. `frontend/e2e/source-viewer/fixtures/*`, `e2e/live-02-evidence.png` |
| 읽기 실패→제외→최종 | 완료 | damaged.pdf 안내 후 제외, 같은 요청의 새 revision 판단 저장. `e2e/damaged.png`, `scratch/live-final-proof.json` |
| 읽기 실패→다시 첨부→재판단 | 부분 | UI 경로 존재. 별도 재판단은 live 5건 상한 때문에 미실행; 제외 경로만 끝까지 확인 |
| 보완 질문→답변→revision 2→취소 | 부분 | UI 정보 요청·답변 접수·취소 확인, 추가 모델 판단 미실행. `e2e/supplement-redis-down.png`, `e2e/cancelled.png` |
| 다시 분석 | 완료 | 한 요청의 두 live Run 모두 judgment_saved. `e2e/reanalyzed.png`, `scratch/live-final-proof.json` |
| 검토 수정 승인→업무 배정 | 부분 | 정상 초안 수정 승인은 완료. 미정 초안은 수정 복구가 막힘(P1-01). `e2e/review-approved.png`, `e2e/review-org-rejected.png` |
| 반려·보완 요청 | 완료 | 별도 요청에 각각 결정하고 목록 상태 확인. `e2e/review-rejected.png`, `scratch/two-tabs-snapshot.txt` |
| 검토 보류 | 부분 | 독립 보류 동작은 보이지 않음; `frontend/src/pages/Review.tsx:37`은 승인/수정 승인/반려/정보 요청만 노출. 요구의 보류가 정보 요청을 뜻하는지는 미확정 |
| 팀 담당자 대기→진행→완료 | 완료 | 실배정된 알림 연동 업무를 UI로 완료. `e2e/task-completed.png` |
| 선행 확인 완료→본업무 차단 해제 | 부분 | API는 200, UI는 진행 버튼 비활성(P1-02). `scratch/task-blocker-{ui,api}.json` |
| 운영자 실행 관찰·재생 | 완료 | 재생 전후 요청5·업무3·Run7 동일. `scratch/replay-proof.json`, `e2e/observatory-replay.png` |
| 판단 맵 경로·목록·키보드 | 완료 | 실제 live 판단·수정 그래프에 대해 기존 E2E 두 브라우저 통과, 탐색 키보드 선택. `e2e/map-keyboard-path.png`, `e2e/map-list.png` |
| 판단 맵 버전 탭 | 완료 | 별도 표시용 시드 v1~v3에서 v3 선택 확인. live 규칙 실행 증거와 혼동 금지. `scratch/seed-map.py`, `e2e/map-v3.png` |
| 규칙 후보→검증→게시→되돌리기 | 부분 | 실제 UI로 후보 승인·저장 판단5건 재평가(호출0/0, 부작용0)·v1/v2 게시·v1 되돌리기 완료. 사람 후보 및 두 번째 버전은 API로 준비; 완전한 UI 제안 여정은 미확인. `scratch/human-candidate.json`, `scratch/learning-final-proof.json`, `e2e/learning-{validation,published,reverted}.png` |
| 규칙 안전 조건 | 완료 | feasibility를 정보 부족→가능으로 만드는 집계 후보 승인을 서버가 안전 조건 위반으로 거절. 후보가 생성된다고 게시 가능한 것은 아님 |
| 평가 라벨·보류·불일치 | 완료 | 기존 시험의 저장 대기 누락을 진단본에서 보강하면 두 브라우저 통과. `scratch/e2e-diagnostic.log` |
| 정책 검증·게시·되돌리기 | 완료 | 기존 policy.spec.ts 양 브라우저 통과. `scratch/e2e-readonly-results.json`, `e2e/policy-375-dark.png` |
| 모니터링 기간·집계 | 완료 | monitoring/screens-ui/F3 시험 통과. `scratch/e2e-readonly-results.json`, `scratch/e2e-safeextra-results.json` |
| 모니터링 경보 발생·해제 | 부분 | 전용 수집기·watchdog 1회 실행으로 worker_stopped 및 판단 예산 소진 경보 2건을 생성하고 UI 알림에서 확인. 해제 동작은 UI에 없음(`frontend/src/pages/Monitoring.tsx:91`); 실제 워커 재시작 해제는 추가 판단 방지를 위해 미실행. `scratch/monitoring-probe.log`, `scratch/monitoring-snapshot.txt`, `e2e/monitoring-alert.png` |
| 권한 없는 화면 | 완료 | requester 학습 화면 거절, graph 접근 거절 시험 양 브라우저 통과. `e2e/requester-learning-forbidden.png` |
| 로그아웃·세션 만료 | 완료 | UI 로그아웃 및 전용 requester 세션 expires_at 과거 설정 후 열린 SSE 탭이 로그인으로 전환. `e2e/session-expired.png` |
| Redis 중지·SSE 재연결·동시 두 탭 | 완료 | 전용 Redis 중지 중 보완·취소 저장, 2번 탭 offline→online 후 cursor104→105 및 취소됨 반영. `scratch/two-tabs-snapshot.txt`, `e2e/two-tabs-reconnected.png`, `scratch/api-redis.log` |
| 1440·960·375, 라이트·다크 | 완료 | 9개 화면×6조건=54 캡처, 문서 가로 넘침0. `scratch/screen-metrics.jsonl`, `e2e/<화면>-<폭>-<테마>.png` |
| 전 여정 키보드만 조작 | 부분 | 요청 Enter, 평가 단축키, 판단 맵 선택/목록/버전 탭, 기존 a11y 키보드 시험 확인. 나머지 모든 업무 동작의 키보드 전용 완주는 미실행 |

## 제품 결함 (수정하지 않음)

### AUDIT-P1-01 — 미정 초안을 고쳐도 수정 승인이 불가능

- 재현: reviewer 로그인 → 시설 점검 요청 `req_33a60302a76c4b96906b01cdf11aab4e` 선택 → 개발 가능성 `가능`, 업무 주관 조직 `IT팀`, 사유 입력 → 수정 승인.
- 기대: 유효한 수정 내용을 검증하고 저장하거나, 남은 미정 필드를 UI에서 수정할 수 있어야 한다.
- 실제: HTTP **422**, `담당 조직이 tenant 범위에 없습니다`. 주관 조직을 실제 tenant Org ID로 바꿔도 같았다.
- 원인 근거: `backend/jevtriage/review/service.py:320`에서 수정 전 원본 tasks를 검증하고, 수정 적용은 `:336` 이후다. 원본에는 lead_org/method가 미정이며, `frontend/src/pages/Review.tsx:37`은 업무 방식(method) 수정 입력도 제공하지 않는다.
- 수정 전 실패 시험: `scratch/diagnostic/defects.spec.ts:4`, `AUDIT-P1-01 a reviewer can repair an undetermined draft before approval`, Chromium·WebKit **expected200/actual422**. 출력 `scratch/defect-repro.log`.
- 캡처: `e2e/review-org-rejected.png`, `e2e/defect-repro/defects-AUDIT-P1-01-a-revi-3c9b8-mined-draft-before-approval-{chromium,webkit}/test-failed-1.png`.
- 수정·수정 후 통과: 미수행(점검 전용, 제품 수정 금지).

### AUDIT-P1-02 — 선행 확인이 완료돼도 UI가 본업무 시작을 막음

- 준비: `scratch/seed-blocker.py`는 전용 tenant에 완료된 `confirmation_task=true` 선행 업무와 `feasibility_unresolved` 본업무만 시드한다.
- 재현: team_member → 업무 → `감사 시드: 확인 완료 후 시작` 상세.
- 기대: 선행 확인 완료에 따라 시작 가능 여부를 서버와 동일하게 표시.
- 실제: 선행 업무는 완료인데 `진행으로 변경` 비활성. 동일 Task 전이 API는 **200**으로 진행 전환하고 차단 사유를 해제했다. 재현 시험을 위해 해당 감사 시드만 원상 복구했다.
- 근거: `frontend/src/pages/tasks/blockers.ts:9`는 feasibility_unresolved를 그대로 유지, `backend/jevtriage/tasks/service.py:38`~`:40`은 완료된 confirmation 선행이 있으면 해제한다.
- 수정 전 실패 시험: `scratch/diagnostic/defects.spec.ts:9`, `AUDIT-P1-02 completed confirmation enables the main task start button`, 두 브라우저 **expected enabled/actual disabled**. `scratch/defect-repro.log`.
- 캡처: `e2e/task-blocker-not-released.png`; API/DOM 실측 `scratch/task-blocker-api.json`, `scratch/task-blocker-ui.json`.
- 수정·수정 후 통과: 미수행(점검 전용).

## 기존 E2E 실행 분류

| 실행 묶음 | 통과 | 실패 | 건너뜀 | 로그 |
|---|---:|---:|---:|---|
| 정책·모니터링·화면 입력·평가·WebMCP | 14 | 2 | 0 | scratch/e2e-readonly.log |
| a11y 정적4종·반응형 375/520 | 36 | 0 | 0 | scratch/e2e-static.log |
| 채팅 반응형/드롭/모션/레이아웃·P7 F2/F3/F4/F6 | 20 | 6 | 0 | scratch/e2e-safeextra.log |
| 키보드 접수·실판단 맵·rem-ui·acceptance gates | 8 | 6 | 2 | scratch/e2e-seeded.log |
| 합계 | **78** | **14** | **2** | 진단·새 결함 재현 시험 제외 |

실패 분류:

- **시험 낡음/동기화 누락 2개**: evaluation-labels.spec.ts의 `labeler confirms three...`는 이전 성공 toast를 다음 저장의 완료로 오인해 저장 중인 세 번째 Enter가 무시된다. API 로그에 pharma-003 PUT가 없다. 제품 수정 없이 매 저장 후 `await expect(confirm).toBeEnabled()`만 추가한 `scratch/diagnostic/evaluation-wait.spec.ts`는 Chromium·WebKit 모두 통과(`scratch/e2e-diagnostic.log`).
- **환경 6개**: chat-intake의 layout1440/960/375×2는 사전 조건 30개 요청을 요구하지만 전용 tenant에는 5~6개만 있었다. expected≥30/actual5 또는6. `frontend/e2e/chat-intake.spec.ts:170`, `:192`.
- **환경 4개**: rem-ui의 목록/원문 시험은 고정 제목 `회의실 예약 자동화` fixture를 찾는다. 이 감사의 실제 요청에는 해당 제목이 없다. `frontend/e2e/rem-ui.spec.ts:18`, `:33`.
- **환경 실패2 + 연쇄 건너뜀2**: acceptance gates는 별도 `${tenant}g` 계정·Cypher records를 요구한다. 전용 tenant 하나만 준비한 상태에서 로그인401, serial 다음 G06 건너뜀. `frontend/e2e/acceptance/gates.spec.ts:14`, `:21`, `:28`.
- **수집 단계 환경 오류**: extension/extension-r은 `X38_OUT/state.json`, `db_truth.<phase>.json`을 import 시 읽는다. 새 tenant용 해당 진실 자료가 없어 ENOENT로 수집 실패. 기존 tenant의 자료를 복사해 맞는 것처럼 시험하지 않았다. `scratch/e2e-extension.log`, `frontend/e2e/extension/extension.spec.ts:15`, `extension-r.spec.ts:15`.

남은 live 의존 시험은 아직 실행하지 않았다. 전체 수집 목록(확장2파일 제외)은 `scratch/e2e-list.txt`의 **154개/17파일**이고, 실행한94개를 제외한60개는 추가 판단을 요구하거나 그 serial 여정에 속한다. 아래 목록과 실제 JSON은 시험별 결과를 보존한다. 보류 시험을 통과 또는 Playwright skip으로 합산하지 않았다.

### 시험별 결과

| 원본 시험 | 브라우저 | 결과 | 시간(s) |
|---|---|---|---:|
'''
for f,line,title,browser,status,dur in rows:
 label={'expected':'통과','unexpected':'실패','skipped':'건너뜀'}.get(status,status)
 header+=f'| frontend/e2e/{f}:{line} — {title.replace("|","/")} | {browser} | {label} | {dur/1000:.2f} |\n'
header+='''
## 체감 속도

측정은 로컬 개발 서버·공유 Neo4j 조건이며 출시 성능 기준이 아니다. 요청 시간은 Enter 직전부터 DOM MutationObserver로 잠정/최종 결과 컨테이너 최초 생성을 측정했다. 첫 표시 시간은 전체 탐색 시작부터 해당 화면의 h1 또는 요청 textarea 표시까지이며, 모든 API·그래프·표 로딩 완료 시간과 다르다.

| live 요청 | 잠정(ms) | 최종(ms) |
|---|---:|---:|
| 매출 CSV 집계 | 1074.0 | 2036.2 |
| 회의실 PDF+DOCX+MD | 1676.1 | 5847.7 |
| 출하 긴급 복구 | 1140.8 | 29351.8 |
| **3건 p50** | **1140.8** | **5847.7** |

5초 이상 대기: 첨부 요청5.85초, 긴급 요청29.35초. 워커 종료 후 보완 접수의 장기 대기는 비용 상한으로 처리 워커를 의도적으로 멈춘 시험 환경 때문이며 제품 응답 성능에 넣지 않았다. 기존 반응형 시험의 5~9초는 명시적 대기와 탐색이 포함된 시험 전체 시간이다.

| 화면 | 3회(ms) | p50(ms) |
|---|---|---:|
'''
for line in (scratch/'screen-metrics.jsonl').read_text().splitlines():
 d=json.loads(line);header+=f"| {d['name']} | {', '.join(map(str,d['times']))} | {d['p50']} |\n"
header+='''
## 콘솔·네트워크·환경 분리

- 9개 화면×6 표시 조건에서 수집한 window error/unhandledrejection은 0이고 가로 넘침은 0이다. `scratch/screen-metrics.jsonl`. 모든 여정의 모든 console.warn까지 수집한 것은 아니다.
- 예상된 HTTP 오류: 비로그인401, 권한 없는 화면403, 안전하지 않은 규칙422, P1-01의422. 감사 단계별 서버 로그는 `scratch/api.log`, `scratch/api-redis.log`.
- Redis 중지 시 ConnectionError 및 재연결 TimeoutError 로그가 발생했다. UI는 DB 폴링 복구로 다음 이벤트를 받았다. 이 로그 자체를 영구 SSE 단절 결함으로 분류하지 않았다.
- 초기 ego-browser에서 다른 작업 tenant(`t-readme-*`)의 세션으로 바뀌었다. 쿠키는 포트별로 격리되지 않으므로 별도 호스트 `audit-e2e.localhost`로 옮겨 해결했다. 그때 발생한 재분석404는 제품 결함에서 제외했다. Playwright는 별도 컨텍스트를 사용했다.
- a11y 결과는 tested 화면 상태의 critical/serious axe 기준이며 모든 장애 유형에 대한 접근성 완전성 인증은 아니다.

## 검증·변경·남은 일

- `cd backend && .venv/bin/pytest -q` → **466 passed, 1 skipped**, `scratch/pytest.log`.
- `cd backend && .venv/bin/ruff check jevtriage tests` → **All checks passed!**, `scratch/ruff.log`.
- 프런트 제품 코드 수정 없음. typecheck/unit/build는 이 감사의 변경 검증 조건에 해당하지 않아 별도 실행하지 않았다.
- 재현용 시험·스크립트·보고서·캡처만 completeness 아래 작성했다. git commit/push 없음. docs/architecture 갱신은 보고서 전용 파일 경계 때문에 하지 않았다.
- 전용 API/Vite/Redis와 브라우저 공간 정리 완료. 10391·7691·16391 연결 종료 확인(`scratch/cleanup.json`), live 워커는 5건 후 종료했다. 전용 tenant 자료는 재현을 위해 보존한다.
- 미완료: 추가 live 의존 E2E60개와 extension 준비 자료, 읽기 실패 재첨부 후 최종 판단, 모든 동작의 키보드 전용 완주, 경보 해제, 사람 후보·새 규칙 버전의 UI 작성 연결.
'''
(root/'E2E_AUDIT.md').write_text(header)
print('report rows',len(rows))
