"""Build the audit-only specification trace; all references resolve against current files."""
from collections import Counter
import ast
import random
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'artifacts/review/completeness/SPEC_TRACE.md'
PREFIX = 'artifacts/review/completeness/'
lines = []


def emit(text=''):
    lines.append(text)


def ref(path, needle=None):
    content = (ROOT / path).read_text().splitlines()
    index = next((i + 1 for i, line in enumerate(content) if needle in line), None) if needle else 1
    if index is None:
        raise ValueError((path, needle))
    return f'`{path}:{index}`'


def test(file, name):
    candidates = list((ROOT / 'backend/tests').rglob(file))
    if len(candidates) != 1:
        raise ValueError((file, candidates))
    return ref(str(candidates[0].relative_to(ROOT)), f'def {name}(') + f' `{name}`'


def table(headers, rows):
    emit('| ' + ' | '.join(headers) + ' |')
    emit('| ' + ' | '.join('---' for _ in headers) + ' |')
    for row in rows:
        emit('| ' + ' | '.join(str(x).replace('|', '\\|').replace('\n', '<br>') for x in row) + ' |')
    emit()


def source(path, needle=None):
    return ref('backend/jevtriage/' + path, needle)


def ui(file, needle=''):
    return ref('frontend/src/' + file, needle or None)


E = {
    'suite': '`' + PREFIX + 'scratch/backend-pytest.log` — 현재 466 통과·1 skip',
    'front': '`' + PREFIX + 'scratch/frontend-vitest.log` — 현재 358 통과/40파일',
    'intake': ref('artifacts/review/completeness/E2E_AUDIT.md', '요청자 텍스트') + ' — live 5 Run, 3종 첨부·복원 확인',
    'files': ref('artifacts/validation/t21/20261003t121902z-86519/junit.xml') + '; ' + ref('artifacts/validation/t21/20261003t121902z-86519/ui-results.json') + ' — 과거 backend40/UI12 통과',
    'gates': ref('artifacts/validation/t21-gates/20261003T113332Z/gate-evidence.md') + ' — 자동배정3/5·정책v2→v3→v4·짧은입력9/9',
    'fault': ref('artifacts/validation/t22/20261004T134712Z/report.md') + ' — 과거 전용 환경 fault11/11',
    'ext': ref('artifacts/validation/20261003T122747Z/extension/scenario-evidence.md') + ' — 과거 X01–X10 live39건',
    'load': ref('artifacts/validation/t25/20261003T101333Z/REPORT.md', '| 접수·조회 가용성') + ' — 과거30분2829건, 100%/99.965%',
    'browser': ref('artifacts/review/completeness/E2E_AUDIT.md', '기존 E2E 94개') + ' — 현재78통과·14실패·2skip; 실패 전부 제품 결함은 아님',
    'reviewgap': ref('artifacts/review/completeness/E2E_AUDIT.md', '### AUDIT-P1-01') + ' — 미정 초안 수정 승인422, 양 브라우저 실패',
    'taskgap': ref('artifacts/review/completeness/E2E_AUDIT.md', '### AUDIT-P1-02') + ' — 선행확인 완료 뒤 UI disabled/API200',
    'replay': ref('artifacts/review/completeness/E2E_AUDIT.md', '운영자 실행 관찰·재생') + ' — 재생 전후 요청5/업무3/Run7 동일',
    'map': ref('artifacts/review/completeness/E2E_AUDIT.md', '판단 맵 경로') + ' — live 그래프·목록·키보드/별도시드 버전탭',
    'cancel': ref('artifacts/review/rem-cancel/REPORT.md', '실제 브라우저:') + ' — Chromium/WebKit 각 취소→재분석 mode=live',
    'source': ref('artifacts/review/rem-ui/REPORT.md', '| 검토 상세 원문') + ' — 원문 권한 API3건·양 브라우저',
    'newgap': '`' + PREFIX + 'scratch/audit-spec-gap-repro.log` — 현재 효과 정답 표본 수·원문 노드 생성시각·조회 권한 요구4건 실패',
    'tracegap': '`' + PREFIX + 'scratch/audit-spec-trace-repro.log` — 현재 Trace 오류·버전 표시 요구 실패',
    'eval': ref('eval/README.md', '| AI 필요성 macro-F1') + ' — tuning 잠정0.807, 팀F1 0.570; final미실행',
    'webmcp': ref('artifacts/validation/final/GATE_REPORT.md', '| G10 WebMCP') + ' — 실제 agent 호출 미확보',
    'ops': ref('artifacts/review/completeness/OPS_AUDIT.md', '| 배포·실행') + ' — 로컬 개발 증거/운영 외부조건 미확정',
}
for key, capture in {
    'intake': 'artifacts/review/completeness/e2e/live-02-evidence.png',
    'reviewgap': 'artifacts/review/completeness/e2e/review-org-rejected.png',
    'taskgap': 'artifacts/review/completeness/e2e/task-blocker-not-released.png',
    'replay': 'artifacts/review/completeness/e2e/observatory-replay.png',
    'map': 'artifacts/review/completeness/e2e/map-keyboard-path.png',
    'cancel': 'artifacts/review/rem-cancel/chromium-cancelled.png',
    'source': 'artifacts/review/rem-ui/chromium-review-source-reader.png',
}.items():
    assert (ROOT / capture).is_file(), capture
    E[key] += f'; 캡처 `{capture}`'

# ID, title, specification anchor, implementation, automatic test, measurement, UI, grade, limit.
R = []


def req(number, title, code, automated, evidence, visible, grade='완료', limit=''):
    identifier = f'R{number:02d}'
    spec = ref('PRD.md', f'| {identifier} |') if number < 19 else ref('docs/spec/08_LEARNING_LOOP.md', f'| {identifier} |')
    R.append([identifier, title, spec, code, automated, evidence, visible, grade, limit or '—'])


req(1, '영속 접수·조회·재시작', source('ingest/service.py','async def submit('), test('test_ingest_api.py','test_text_ingest_persists_revision_run_and_job'), E['intake']+'; '+E['fault'], ui('pages/Main.tsx','export function Main'), '부분', '새 환경 기동 실증은 mock·Docker Desktop; 현재 OrbStack clean install/live 전 구간 재검증 없음')
req(2, 'PDF/DOCX/MD·원문 위치·한도', source('ingest/parsers/api.py','def parse_file(')+'; '+source('ingest/service.py','async def visible_document('), test('test_parsers.py','test_pdf_page_and_encryption_limits')+'; '+test('test_source_document.py','test_document_returns_ordered_units_with_text_for_source_reader'), E['intake']+'; '+E['source'], ui('components/EvidenceViewer.tsx','export function EvidenceViewer'))
req(3, '부분 파일 실패·제외/재첨부·이전 결과', source('ingest/service.py','async def decide_files(')+'; '+source('ingest/service.py','async def revise('), test('test_ingest_api.py','test_http_multipart_file_decision_creates_supported_revision_and_job')+'; '+test('test_judgment_service.py','test_reanalysis_preserves_previous_judgment'), E['files']+'; '+E['intake'], ui('pages/Main.tsx','async function submit'), '완료', '이번 브라우저 감사는 제외 경로 확인, 재첨부 live 완주는 과거 증거를 사용')
req(4, '핵심 분류·불확실성·버전·실제 Jev', source('judgment/pipeline.py','def classify(')+'; '+source('judgment/store.py','async def save_judgment_in_tx('), test('test_judgment_service.py','test_fixed_policy_survives_new_active_version')+'; '+test('test_judgment_pipeline.py','test_schema_rejects_missing_answer'), E['intake']+'; '+E['gates'], ui('pages/main/ResultCard.tsx'))
req(5, '원문 근거·업무 방식/담당/선행/산출물', source('judgment/evidence.py','def link_evidence(')+'; '+source('judgment/decompose.py','def decompose('), test('test_judgment_service.py','test_real_span_citation_is_persisted_with_probability'), E['gates']+'; '+E['intake'], ui('pages/main/ResultCard.tsx')+'; '+ui('components/EvidenceViewer.tsx'), '완료', '과거 인용 Jaccard≥0.857·소표본; 모든 판단에 인용을 생성할 수 없으면 검토 전환')
req(6, '승인·수정·반려·정보 요청·원안/감사', source('review/service.py','async def decide('), test('test_review_assignment.py','test_four_decisions_history_audit_and_assignment')+'; '+test('test_review_assignment.py','test_correction_preserves_original_and_relationships'), E['reviewgap']+'; '+E['source'], ui('pages/Review.tsx'), '부분', '미정 초안의 정상 수정 승인 복구가422로 차단')
req(7, '자동 배정 불변 조건·단일 배정·팀 추적', source('domain/eligibility.py','def evaluate_auto_assign(')+'; '+source('review/service.py','async def assign_in_tx(')+'; '+source('tasks/service.py','async def transition('), test('test_review_assignment.py','test_concurrent_approvals_one_assignment_and_idempotency')+'; '+test('test_review_assignment.py','test_auto_path_rechecks_mandatory_review_and_infeasibility'), E['gates']+'; '+E['taskgap'], ui('pages/Tasks.tsx')+'; '+ui('pages/tasks/blockers.ts'), '부분', '완료된 confirmation 선행을 UI 차단 판정이 반영하지 않음')
req(8, 'Dynamic Config 검증·diff·게시·되돌리기·고정', source('policy/service.py','async def publish(')+'; '+source('policy/service.py','async def rollback('), test('test_policy_versions.py','test_publish_diff_audit_snapshot_and_rollback')+'; '+test('test_policy_versions.py','test_reject_unsafe_publish_and_rollback'), E['gates']+'; '+E['browser'], ui('pages/Policy.tsx'))
req(9, '실제 Neo4j 업무·팀·선행 그래프', source('observe/topology.py','async def get_topology('), test('test_observe_api.py','test_observe_reads_saved_steps_reviews_and_real_topology'), E['gates']+'; '+E['replay'], ui('pages/Observatory.tsx'))
req(10, 'SSE 순서·재개·권한·최종 상태', source('events/router.py','async def stream_events('), test('test_sse_events.py','test_stream_order_resume_scope_and_snapshot')+'; '+test('test_authz_matrix.py','test_sse_rechecks_revoked_session'), E['browser']+'; '+E['cancel'], ui('state/events.ts'))
req(11, '실제 단계·Trace 시각/오류/모델/스키마', source('observe/api.py','async def step_detail(')+'; '+source('observe/trace_store.py','async def start_step_in_tx('), test('test_observe_api.py','test_observe_reads_saved_steps_reviews_and_real_topology')+'; `scratch/audit-spec-ui/trace.test.tsx` (이번 추가 실패)', E['tracegap'], ui('pages/Observatory.tsx','Trace 상세'), '부분', 'API에는 오류·소요시간·versions가 있으나 Trace drawer에는 오류/소요시간/실행 versions 표시 없음')
req(12, 'Playback 제어·실패/건너뜀/사람 대기·무부작용', source('observe/playback.py','async def get_playback('), test('test_observe_api.py','test_observe_reads_saved_steps_reviews_and_real_topology')+'; '+ref('frontend/src/pages/observatory/playback.test.ts'), E['replay']+'; '+E['files'], ui('pages/Observatory.tsx','재생 구간'))
req(13, '독립 관측·기간/조직/상태/버전·예산·알림', source('monitoring/aggregates.py','def summarize(')+'; '+source('monitoring/slo.py','def error_budget(')+'; '+source('journal/watchdog.py'), test('test_monitoring_collector.py','test_collector_deduplicates_and_keeps_db_failure_in_availability')+'; '+test('test_monitoring_collector.py','test_watchdog_alerts_fast_burn_and_repeated_failures'), E['fault']+'; '+E['browser'], ui('pages/Monitoring.tsx'), '부분', '보완 대기 별도 시간 지표 미확인(추정); 운영 원격 알림·30일 관측 없음')
req(14, 'WebMCP 읽기 도구 실제 에이전트 호출', ui('webmcp/index.ts','export function createWebMcpTools'), ref('frontend/src/webmcp/index.test.ts')+'; '+ref('frontend/e2e/webmcp.spec.ts','application remains usable'), E['webmcp']+'; '+E['browser'], ui('webmcp/index.ts','export async function registerWebMcpTools'), '외부 대기', '지원 브라우저의 실제 agent 호출 주체 필요; 모의 registerTool·미지원 웹 회귀만 확인')
req(15, 'tenant/조직/역할·입력/키/저장 안전', source('auth/policy.py','def can(')+'; '+source('auth/policy.py','def redact_source(')+'; '+source('domain/masking.py','def mask_for_external('), test('test_authz_matrix.py','test_request_access_matrix')+'; '+test('test_judgment_service.py','test_external_state_masked_but_saved_citation_uses_original_span'), E['suite']+'; '+E['source']+'; '+E['files'], ui('pages/Review.tsx')+'; 원문 권한 안내', '완료', '개발 안전 범위 판정; 운영 IdP/원격 보존 정책·마스킹의 모든 민감 유형 보장은 별도')
req(16, '키보드·아이콘/텍스트·터치·반응형·모션', ui('styles/tokens.css')+'; '+ui('lib/motion.ts'), ref('frontend/e2e/a11y/a11y.spec.ts')+'; '+ref('frontend/e2e/chat-intake.spec.ts','reduced motion'), E['browser']+' — 54화면 캡처 가로넘침0', ui('pages/Main.tsx')+'; 모든 화면', '부분', '주요 흐름·axe·반응형 캡처는 통과했으나 전 여정 키보드만 완주 증거 없음')
req(17, 'SLO 개발 부하·분류 품질·표본', source('monitoring/aggregates.py','def summarize(')+'; '+ref('eval/runner.py'), test('test_eval_metrics.py','test_metrics') if 'def test_metrics(' in (ROOT/'backend/tests/unit/test_eval_metrics.py').read_text() else ref('backend/tests/unit/test_eval_metrics.py'), E['load']+'; '+E['eval'], ui('pages/Monitoring.tsx')+'; '+ui('pages/Evaluation.tsx'), '부분', '현업 정답/final60·브라우저 상태반영 부하실측·최신30분 재검증 없음')
req(18, '게이트·실행/운영/복구 제출물·30일', ref('README.md')+'; '+ref('docs/operations/RUNBOOK.md')+'; '+ref('artifacts/validation/final/GATE_REPORT.md'), '아래 전체 검증6명령·T27/T28; 새 운영 인수 시험 없음', E['ops']+'; '+E['suite'], ui('pages/Monitoring.tsx'), '부분', '최종 게이트/작업표의 코드SHA·시험수·미비 문구 갱신 필요; G10/G12/G13 미완료')
req(19, 'Correction·AI 원안 보존·비교', source('review/service.py','async def decide(')+'; '+source('learning/corrections.py','async def list_corrections('), test('test_review_assignment.py','test_correction_preserves_original_and_relationships'), E['ext']+'; '+E['source'], ui('pages/Review.tsx')+'; '+ui('pages/Learning.tsx'))
req(20, '후보·지지/반례·범위·출처·자료 부족', source('learning/candidates.py','async def generate_candidates(')+'; '+source('learning/candidates_api.py','async def propose('), test('test_candidates.py','test_three_support_cases_generate_idempotent_candidate_without_config_write')+'; '+test('test_candidates.py','test_two_support_cases_are_marked_insufficient'), E['ext']+'; '+E['browser'], ui('pages/Learning.tsx'), '완료', '명세의 집계 후보 생성·검토는 연결됨. 별도 사람 직접 제안 API의 UI 폼은 없으나 그 폼을 필수 수락 조건으로 단정하지 않음')
req(21, '규칙 관리자 결정·수명·권한·감사', source('learning/rules.py','async def decide_candidate(')+'; '+source('learning/rules_api.py','async def rules('), test('test_rules_integration.py','test_role_matrix_and_state_transitions')+'; `scratch/test_audit_spec_gaps.py::test_rule_read_allowed_for_scoped_reviewer_and_operator` (두 역할 실패)', E['ext']+'; '+E['newgap'], ui('pages/learning/Actions.tsx')+'; '+ui('pages/Learning.tsx','if (perms.isAdmin)'), '부분', '08:91은 검토자/운영자 조회를 허용하지만 GET rules가 rule_admin 전용으로403. 기존 role_matrix 시험은 이 거절을 정상으로 기대; 게시·변경 권한은 정상')
req(22, '게시 Config·고정 버전·APPLIED·안전 거절', source('learning/rules.py','async def change_publication(')+'; '+source('learning/apply.py'), test('test_rules_integration.py','test_publication_application_stop_revert_and_restart')+'; '+test('test_rules_integration.py','test_unsafe_rule_rejected_at_create_publish_and_revert'), E['ext']+'; '+E['suite'], ui('pages/Observatory.tsx','適用' if False else '적용된 규칙')+'; '+ui('pages/Learning.tsx'))
req(23, '섀도 비교·호출 상한·부작용0', source('learning/shadow.py','async def validate_rules('), test('test_shadow_api.py','test_shadow_stores_validation_without_business_mutation')+'; '+test('test_shadow_api.py','test_context_call_limit_records_failure'), E['ext']+'; '+ref('artifacts/review/completeness/E2E_AUDIT.md','규칙 후보→검증')+' — 현재5건 재평가·호출0/0·부작용0', ui('pages/learning/sections.tsx','사람 확정 정답'))
req(24, '효과 비교·표본·정답표본·지표·SLO 분리', source('learning/effects.py','async def rule_effects('), test('test_effects_api.py','test_effects_known_windows_and_application_groups')+'; `scratch/test_audit_spec_gaps.py::test_rule_effect_comparisons_expose_human_labeled_sample_counts` (현재 실패)', E['newgap']+'; '+E['ext'], ui('pages/learning/sections.tsx','게시 후 관찰'), '부분', '각 cohort의 labeled_count가 없음; 충분표본 판정은40건 DB seed 시험만, 실사용 UI 대조 없음')
req(25, '실제 판단 관계·tenant 경계·미합성', source('graph/query.py','async def collect(')+'; '+source('graph/query.py','async def trace('), test('test_judgment_graph.py','test_request_graph_has_isolated_nodes_and_no_synthesized_edges')+'; '+test('test_judgment_graph.py','test_authorization_and_tenant_boundaries'), E['ext']+'; '+E['map'], ui('pages/JudgmentMap.tsx'))
req(26, '5계층·양방향·필터/줌/이동/축약/목록/키보드·상세 메타데이터', ui('pages/JudgmentMap.tsx','export function JudgmentMap')+'; '+ui('pages/judgment-map/MapView.tsx')+'; '+source('graph/api.py','async def judgment_path('), test('test_judgment_graph.py','test_path_both_directions_with_depth_and_limits')+'; '+ref('frontend/e2e/source-viewer/source-viewer.spec.ts','judgment map: version tabs'), E['map']+'; '+E['ext'], ui('pages/JudgmentMap.tsx','크게 보기'), '완료', '버전탭 현재 감사는 표시용 seed; 실제규칙 양방향 체인은 과거X06 증거')
for row in R:
    if row[0] in {'R25', 'R26'}:
        row[7] = '부분'
        row[8] = '08:48 공통 노드 생성시각 요구: 실제 EvidenceSpan에 created_at 없음(SPEC-F03). 생성주체 직접 속성도 코드에서 확인되지 않음; 관계 조회·필터·키보드·버전탭은 동작함'
BY_R = {row[0]: row for row in R}

emit('# 명세 대비 구현 추적표 — AUDIT-SPEC')
emit()
emit('점검일: 2026-10-05 (Asia/Seoul). 코드: `' + subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip() + '`. 전체 검증 시작 시점은 `5da8381`이며 점검 중 코디네이터가 README 문서만 변경한 `00cc01e`를 커밋했다. `git diff 5da8381..HEAD -- backend frontend`는 변경 0건이다. 점검·보고 전용이며 제품 코드·명세·설계·아키텍처 문서는 수정하지 않았다. 이 문서와 `scratch/audit_spec*.py`, `scratch/audit-spec*`, `scratch/test_audit_spec_gaps.py`, 아래 검증 로그만 이 작업의 산출물이다. 같은 completeness 디렉터리의 E2E_AUDIT/OPS_AUDIT는 다른 작업자의 동시 감사 자료로 출처를 명시해 인용했다.')
emit()
emit('대상: docs/spec/01·02·04·05·06·08, README, 연결된 TASK.md, 최종 GATE_REPORT. **01 문서에는 R01–R18 번호가 없다**. R번호는 `PRD.md:103`의 기준표를 이용해 01의 필수 문장에 연결했다. **docs/spec/README에는 TASK ID 목록이 없다**. T00–T28은 TASK.md, T29–T38은 08과 TASK.md를 대조했다. 문서 누락을 임의 번호로 덮지 않았다.')
emit()
emit('등급: 완료=구현+관련 자동 시험+실측 증거, 부분=구현 있으나 일부 기능/시험/실측/UI 불충족, 미구현=요구 경로 없음, 외부 대기=지원 환경·현업 확정·운영 기간 등 외부 조건 필요. 과거 live·부하·재시작 증거에는 날짜/실행 ID를 보존했으며 현재 시험 통과가 과거30분 부하 또는 모든 live UI를 재검증한 뜻은 아니다. 코드 경로만으로 판단하는 잔여 항목은 **추정**으로 표시한다.')
emit()
emit('## 요약')
emit()
counts=Counter(row[7] for row in R)
table(['범위','완료','부분','미구현','외부 대기','핵심 제한'], [['R01–R26',counts['완료'],counts['부분'],counts['미구현'],counts['외부 대기'],'검토 422·업무 시작 차단·Trace 필드·효과 정답 표본·원문 노드 생성시각·조회 권한·G10/G12/G13'], ['전체 자동 검증','6명령 모두 통과','live pytest1건 skip','—','—','backend466/Vitest358/import계약6'], ['무작위 완료 검증','10항목 모두 통과',f'완료{counts["완료"]}개 중 sample10·seed20261005','—','—','아래 선택/명령/출력 보존'], ['신규 요구 재현','—','pytest효과/노드/조회4실패·VitestTrace4실패','—','—','점검 전용: 수정·수정 후 통과 없음']])
emit('개발 완료와 확장 완료는 선언할 수 없다. 현재 G04/G05/G07/G09/X06/X09 및 규칙 조회 권한에 부분 조건이 있고, G10은 외부 대기, G12는 부하 계측 경계와 현업 최종 평가가 남으며 G13은 운영30일 관측이 없다. 안전 단일 배정의 backend 시험은 통과했지만 현재 UI 결함 두 건을 통과 주장에 포함할 수 없다.')
emit()
emit('## 현재 실행한 검증')
emit()
table(['명령','결과','출력 경로'], [
 ['cd backend && .venv/bin/pytest -q','exit0; 466 passed, 1 skipped in100.99s',f'`{PREFIX}scratch/backend-pytest.log`'],
 ['cd backend && .venv/bin/ruff check jevtriage tests','exit0; All checks passed!',f'`{PREFIX}scratch/backend-ruff.log`'],
 ['cd backend && .venv/bin/lint-imports','exit0; 121파일/295의존성; 6 kept, 0 broken',f'`{PREFIX}scratch/backend-lint-imports.log`'],
 ['cd frontend && npm run typecheck','exit0; tsc --noEmit',f'`{PREFIX}scratch/frontend-typecheck.log`'],
 ['cd frontend && npm run test','exit0; 358 passed/40files,27.62s',f'`{PREFIX}scratch/frontend-vitest.log`'],
 ['cd frontend && npm run build','exit0; Vite build900ms',f'`{PREFIX}scratch/frontend-build.log`'],
])
emit('skip 근거: '+ref('backend/tests/live/test_judgment_live.py','pytestmark')+' — `JEV_MODE=live` 및 live 자격증명을 요구하는 `test_two_live_request_shapes`. 이번 SPEC 감사에서는 외부 모델 호출·API/worker 서버를 시작하지 않았다. pytest의 UUID 전용 tenant는 기존 시험 cleanup을 사용했고, 신규 효과 재현 tenant도 finally에서 삭제했다. 공유 Neo4j를 중지하지 않았고 8191/5391 프로세스를 건드리지 않았다. UI 재현은 jsdom에서 수행했다. Docker Desktop 실행·git commit/push 없음.')
emit()
emit('### 완료 항목 무작위10개 재실행')
emit()
selected_requirements = random.Random(20261005).sample([row[0] for row in R if row[7] == '완료'], 10)
selection_tree = ast.parse((ROOT / (PREFIX + 'scratch/audit_spec_random_requirements.py')).read_text())
selection_tests = next(ast.literal_eval(node.value) for node in selection_tree.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'tests' for target in node.targets))
emit(f'요구사항 상세 표에서 완료인 R항목{sum(row[7] == "완료" for row in R)}개를 모집단으로 `random.Random(20261005).sample(population, 10)`을 실행했다. 선택한 ID는 ' + '·'.join(selected_requirements) + '이며 해당 시험을 실제로 재실행했다. 모집단·선택ID·명령은 `artifacts/review/completeness/scratch/audit-spec-random-requirements.json`, 재현은 `scratch/audit_spec_random_requirements.py`, 결과는 `scratch/audit-spec-random-requirements-backend.log`와 `scratch/audit-spec-random-requirements-frontend.log`에 있다. 무작위로 선택된 10개 항목의 백엔드 시험 10건이 모두 통과했다(3.65초). 모션·공용 UI 시험 18건도 별도 실행하여 통과했으며 이 추가 실행은 선택된 10항목의 수에 포함하지 않았다. 별도 기능군별 무작위10시험의 10/10 통과 출력도 `scratch/audit-spec-random-tests.log`에 보존했다.')
emit()
random_rows=[]
for identifier in selected_requirements:
    node = selection_tests[identifier]
    if identifier == 'R16':
        automatic = ref('frontend/' + node) + ' `reads prefers-reduced-motion`, `CountUp keeps the final value readable for assistive tech` 외16건'
    else:
        filename, function = node.split('::')
        automatic = test(Path(filename).name, function)
    random_rows.append([identifier, BY_R[identifier][1], automatic, '18 PASSED' if identifier == 'R16' else 'PASSED'])
table(['무작위 ID','완료 수락 항목','실행 시험','결과'], random_rows)
emit('### 수정 전 실패 재현(이번 감사 작성)')
emit()
table(['항목','명세·코드 근거','시험·명령','결과·처리'],[
 ['SPEC-F01 효과 정답 표본수 누락',ref('docs/spec/04_OBSERVATORY.md','각 비교에는')+'; '+source('learning/effects.py','def _metrics(')+'; '+ui('pages/learning/sections.tsx','게시 후 관찰'),'`cd backend && JEVTRIAGE_STRICT_TENANT=1 .venv/bin/pytest ../artifacts/review/completeness/scratch/test_audit_spec_gaps.py -q`','실제 Neo4j 전용tenant4cohort 반환 후 labeled_count assertion실패; '+E['newgap']+'; cleanup완료, 수정금지에 따라 잔여'],
 ['SPEC-F02 Trace필드 UI 누락',ref('docs/spec/04_OBSERVATORY.md','노드를 클릭하면')+'; '+source('observe/api.py','async def step_detail(')+'; '+ui('pages/Observatory.tsx','Trace 상세'),'`cd frontend && npx vitest run --config ../artifacts/review/completeness/scratch/audit-spec-ui/vitest.config.mts`','저장응답 fixture의 JevTimeout·12345ms·model/schema를 drawer에 표시하도록 요구; 오류/소요시간/model/schema 4개 assertion 모두 실패; '+E['tracegap']+'; 제품수정없음'],
 ['SPEC-F03 원문 노드 생성시각 누락',ref('docs/spec/08_LEARNING_LOOP.md','모든 노드는')+'; '+source('ingest/store.py','CREATE (e:EvidenceSpan'),'`scratch/test_audit_spec_gaps.py::test_persisted_evidence_node_has_creation_time_and_creator` — 위 pytest 명령에 함께 실행','실제 텍스트 요청을 저장한 뒤 EvidenceSpan.created_at이 None이라 실패. 생성주체 직접 속성도 코드에 없음; '+E['newgap']+'; 전용tenant finally삭제'],
 ['SPEC-F04 검토자/운영자 규칙 조회 거절',ref('docs/spec/08_LEARNING_LOOP.md','| 조회 |')+'; '+source('learning/rules_api.py','ADMIN =')+'; '+source('learning/rules_api.py','async def rules(')+'; '+ui('pages/Learning.tsx','if (perms.isAdmin)'), '`scratch/test_audit_spec_gaps.py::test_rule_read_allowed_for_scoped_reviewer_and_operator` — 위 pytest 명령에 함께 실행', '전용 tenant의 reviewer/operator GET rules 각각 기대200 실제403; '+E['newgap']+'; DB 쓰기 없음. 기존 role_matrix가403을 기대하므로 전체 시험 통과로 발견되지 않음'],
 ['AUDIT-P1-01/02 브라우저 결함','위 R06/R07 코드 근거 및 E2E_AUDIT 원문','다른 작업자의 `scratch/diagnostic/defects.spec.ts` — 두브라우저 각각 실패','422·UI disabled/API200 확인, 이 SPEC 작업에서는 해당 브라우저 시험을 다시 실행하지 않음'],
])
emit('Trace 재현의 초반 설정 실패(React import·active_run fixture)는 scratch 시험환경을 고친 뒤 최종 product assertion으로 다시 실행했다. 보고서 판정은 최종 로그의 drawer 오류·소요시간·model/schema 표시 4개 실패를 사용한다. 효과 재현은 모델 호출이나 업무 생성 없이 실제 서비스/Neo4j 경로를 검증한다.')
emit()
emit('## 요구사항 상세 — R01–R26')
emit()
table(['ID','요구·수락기준','명세 위치','구현 위치','자동 시험','실측 증거','UI노출','등급','제한'],R)

emit('### 01 목표·핵심 판단·필수 문장과 ID 연결')
emit()
SPEC01 = [
 (9,'AI 필요성: 필요·불필요·혼합·정보 부족','R04'),
 (10,'개발 가능성: 가능·조건부 가능·현재 불가·정보 부족','R04'),
 (11,'긴급도: 긴급·일반·판단 보류 및 근거','R04'),
 (12,'담당: AI·IT·현업의 주관/협업·업무별 책임','R05'),
 (13,'처리방법: AI·일반기술·사람·순서/산출물','R05'),
 (14,'검토 대상·사유·추가 정보','R06'),
 (16,'불확실성 비이분법·기술/조직/승인 구분·재판단 조건','R04'),
 (20,'웹 채팅 텍스트·PDF·DOCX·MD·다중 첨부','R02'),
 (21,'원문/분석텍스트 연결·추가 질문 답변 보완','R03'),
 (22,'실제 Jev·결정별 근거/신호/정책 버전','R04'),
 (23,'여러 조직 업무분해·주관/협업/선행','R05'),
 (24,'검토 승인/수정/반려/정보 요청·이력','R06'),
 (25,'요청/업무/검토/팀/진행 대시보드·필터','R07'),
 (26,'실제 실행 Flow/Topology/Playback/지표 연결','R11'),
 (27,'Dynamic Config·실제 Neo4j 관계 저장/조회','R08'),
 (28,'SSE진행·WebMCP권한조회','R14'),
 (29,'Correction·규칙후보 검토/검증/적용/관찰','R24'),
 (30,'근거/가설/판단/적용/업무단계 실제관계','R25'),
 (31,'입체 판단맵·규칙학습 경험','R26'),
 (35,'confidence≠정답·문서명령무효·가설/승인구분·단건승인≠공통게시·모델재학습아님','R15'),
 (47,'SAP관련 요청·내부배정; SAP/외부티켓 직접쓰기 범위 제외','R07'),
 (49,'임상/안전/규제 고영향 책임자 검토·전문인증/승인 주장 없음','R15'),
 (51,'확장 후 SAP범위/필수검토/무승인0 유지','R22'),
 (53,'최신입력/필수근거/초안·가능·미해결/미정0 자동배정·위험/긴급 필수검토·정책우회0','R07'),
]
table(['문장 ID','명세·수락기준','요구 ID·구현·시험','실측·캡처','UI','등급'],[
 [f'GO{i:02d}',f'`docs/spec/01_GOALS_REQUIREMENTS.md:{number}` '+title,identifier+'; '+BY_R[identifier][3]+'; '+BY_R[identifier][4],BY_R[identifier][5],BY_R[identifier][6],BY_R[identifier][7]]
 for i,(number,title,identifier) in enumerate(SPEC01,1)
])
emit('GO16의 SSE 부분은 R10으로 완료이며 WebMCP 실제 호출은 R14 외부 대기로 표시했다. GO21/24의 backend 자동배정 안전과 내부배정 범위는 완료이고, 연결된 R07의 전체 UI 여정은 선행 확인 완료 후 시작 버튼 결함 때문에 부분이다. 범위에서 제외된 외부 SAP 쓰기를 미구현 결함으로 집계하지 않았다.')
emit()

emit('## 사용자 경험·관찰 문장 전수 대조')
emit()
UX = [
 ['UX01', '02:3 접수→파일확정→판단→검토→배정',3,['R01','R03','R04','R06','R07'],'부분','검토·업무 UI 결함 영향'],
 ['UX02','지원입력 정보부족도 실제필수판단 먼저 저장; 미정사유',24,['R04','R05'],'완료','mock서비스 시험+과거짧은입력9/9 배정0'],
 ['UX03','텍스트/첨부·업로드와 분석 분리·요약/담당/업무/추가정보',28,['R02','R04','R05'],'완료','현재live5Run 및 단계UI'],
 ['UX04','근거마다 원문 페이지/문단 이동',28,['R02','R05'],'완료','EvidenceViewer 위치강조·권한별응답'],
 ['UX05','실패파일 알림·명시제외/재첨부·scan/OCR안내',30,['R02','R03'],'완료','OCR 기본미지원은 PARSERS 문서/scan시험의 허용대안'],
 ['UX06','보완·재분석 과거결과·변경이유·실행버전',32,['R03','R04'],'완료','reanalysis boundary 및 대화복원'],
 ['UX07','검토원문/신뢰/업무·4종결정·이력·무승인/중복0',36,['R06','R07','R15'],'부분','미정원안 수정 복구422'],
 ['UX08','팀업무·선행막힘; 실패Trace/재시도; 검토대기≠실패',40,['R07','R11','R13'],'부분','확인선행 완료 뒤 UI차단·Trace필드부족'],
 ['UX09','8개경험+키보드+색상이외상태',44,['R16','R26'],'완료','54캡처·주요키보드·아이콘/텍스트'],
 ['UX10','원안/Correction 비교·단건수정과공통게시 구분',48,['R19','R21'],'완료','X01/X03·검토 UI 안내'],
    ['UX11','후보→범위확정/기각→검증→게시/중단/되돌림·감사·시작버전',50,['R20','R21','R22','R23'],'완료','집계후보 생성부터 게시·되돌리기 확인'],
 ['UX12','실제관계양방향·원문권한·동일목록·미합성',52,['R25','R26'],'부분','graph exact·경로·목록 시험'],
 ['UX13','09맵/10학습 번호·같은 식별자 연결',65,['R25','R26'],'완료','routes/딥링크·같은 ID'],
]
table(['ID','문장·명세위치','구현·자동시험','실측','UI','등급·제한'],[[a,b+'; '+ref('docs/spec/02_USER_EXPERIENCE.md', (ROOT/'docs/spec/02_USER_EXPERIENCE.md').read_text().splitlines()[c-1]),'<br>'.join(BY_R[k][3]+'; '+BY_R[k][4] for k in ds),BY_R[ds[0]][5],'<br>'.join(BY_R[k][6] for k in ds),grade+' — '+limit] for a,b,c,ds,grade,limit in UX])
OBS = [
 ['OBS01',7,'Flow실행순서·Topology업무/서비스 의미구분·실관계',['R09','R12'],'완료'],
 ['OBS02',9,'AI/코드/규칙/외부/사람; 상태6종·병렬/재시도',['R11','R12'],'부분'],
 ['OBS03',13,'Trace ID/시각/시간/주체/입출력/원문/오류/재시도/버전',['R11'],'부분'],
 ['OBS04',15,'숨은사고과정 제외·반환값/정책/사람결정·원문권한',['R15','R19'],'완료'],
 ['OBS05',19,'재생/정지/처음/속도/구간/전체·압축사람대기·무재호출',['R12'],'완료'],
 ['OBS06',21,'활성노드/상태/실패종료·skipped·live vs replay',['R12'],'완료'],
 ['OBS07',25,'요청/자동/검토/실패/timeout/시간/단계/대기/retry/version·null비용',['R13'],'완료'],
 ['OBS08',27,'모델/파싱/저장/SSE 오류구분·기간/시간대/조직/상태·Trace·누락/갱신',['R13','R11'],'부분'],
 ['OBS09',31,'5계층 저장노드·빈계층·미합성',['R25','R26'],'완료'],
 ['OBS10',33,'선택경로·상세·원문·줌/팬/fit·필터/축약/키보드/list/reduced',['R26'],'부분'],
 ['OBS11',35,'Flow/Topology/Map/Learning 같은7종ID 상호이동',['R22','R25','R26'],'완료'],
 ['OBS12',39,'효과 전후·사용/미사용·5지표·조건/표본/정답표본·5효과상태',['R24'],'부분'],
 ['OBS13',41,'효과지표≠SLO·shadow분모제외',['R23','R24'],'완료'],
 ['OBS14',45,'같은request/run·retry요청중복0·승인대기≠실패·AI원안보존',['R13','R19'],'완료'],
]
table(['ID','명세','구현·자동시험','実측' if False else '실측','UI','등급'],[[a,ref('docs/spec/04_OBSERVATORY.md',(ROOT/'docs/spec/04_OBSERVATORY.md').read_text().splitlines()[n-1])+' '+name,'<br>'.join(BY_R[k][3]+'; '+BY_R[k][4] for k in ds),BY_R[ds[0]][5],BY_R[ds[0]][6],grade] for a,n,name,ds,grade in OBS])

emit('## SLO·분모·품질·개발/운영 조건 전수')
emit()
SLO = [
 ['S01',7,'20,000자/5파일/10MiB개별/25MiB합계/PDF50page','R02','완료','parser/HTTP한도시험; 과거한도근처113건'],
 ['S02',7,'초과/암호화/손상/미지원 거절·보완; OCR별도범위','R02','완료','scan은OCR미지원 안내; 별도OCR기능 요구아님'],
 ['S03',9,'서버수신부터; 모든필수분류+근거 저장만 최초완료','R04','완료','judgment_committed complete_judgment 경계; 잠정은완료아님'],
 ['S04',15,'운영30일 유효접수/조회 가용성≥99.9%','R13','외부 대기','개발21856/21856=100%; 운영30일없음'],
 ['S05',16,'운영30일 최초지원 요청120s성공≥99.0%','R13','외부 대기','개발2828/2829=99.965%; 운영30일없음'],
 ['S06',17,'접수응답 p95≤2s(실패포함)','R17','완료','과거888ms; 최신부하는미재실행'],
 ['S07',18,'텍스트 최초판단 p95≤15s','R17','완료','과거3462.8ms; 최신소표본과별개'],
 ['S08',19,'첨부최초판단 p95≤45s','R17','완료','과거15906ms'],
 ['S09',20,'저장→연결된 브라우저반영 p95≤2s','R10','부분','과거2000ms는서버전송직전까지만; browser render 미측정'],
 ['S10',21,'네트워크복원→최신영속상태표시 p95≤5s·누락0','R10','부분','과거354.9ms/600 snapshotHTTP표본; browser표시완료 경계미측정'],
 ['S11',22,'Trace필수단계/분기/버전/종료 시험100%·운영99.9%','R11','부분','과거2829/2829·운영미확인; UI필드누락별도'],
 ['S12',24,'실패/timeout 지연포함·미도달120s·부하/외부장애 분모유지','R13','완료','collector_known + fault DB실패journal·late_recoveries'],
 ['S13',24,'취소별도수·기발생실패 취소재분류금지','R10','완료',E['cancel']+'; backendcancel경합/collector시험'],
 ['S14',26,'사람검토대기 p50/p95/최장/미처리·반려정상','R13','완료','review_wait 실제DB집계·Monitoring'],
 ['S15',32,'첫수신시각고정·정보부족필수기록·미정사유','R04','완료','fixed policy/information gap + G03짧은9건'],
 ['S16',33,'보완대기 별도지표·원래120s시계정지금지','R13','부분','실패시계불변시험은있음; 사용자답변대기 시간지표미확인(추정)'],
 ['S17',34,'새revision/run재판단시간별도·최초분모증가0','R03','완료','revision_p95·reanalysis boundary·first sample시험'],
 ['S18',35,'retry누적deadline·120s뒤회복분리·원실패유지','R13','완료','late_recoveries·workerdeadline·collector시험'],
 ['S19',36,'파일객관제외/첫지원revision1표본·기실패불변·지원parser장애분모유지','R03','완료','test_first_eligible_after_file_exclusion_and_retry_keep_one_sample'],
 ['S20',37,'호출가용성/요청최초/revision단위·독립attempt·미확정공개','R13','완료','unknown_validity/unconfirmed_samples·snapshot試험'],
 ['S21',43,'현업한국어정답≥100·지원클래스·tuning/final분리·final≥60고정','R17','외부 대기','candidate120·60/60 hash는있음; 현업확정전'],
 ['S22',45,'AI 필요성macroF1≥.85','R17','외부 대기','잠정tuning .807; 목표미달·final미실행'],
 ['S23',45,'개발가능성macroF1≥.85','R17','외부 대기','잠정tuning1.000; 확정final증거없음'],
 ['S24',45,'긴급도macroF1≥.85','R17','외부 대기','잠정tuning1.000; 확정final증거없음'],
 ['S25',45,'긴급recall≥.95','R17','외부 대기','잠정tuning1.000; 확정final증거없음'],
 ['S26',45,'담당팀집합 평균F1≥.85','R17','외부 대기','잠정tuning.570(evalREADME)/.556(GATE); 최종확정없음'],
 ['S27',45,'분류표본/오분류/전환/자동율·보류정답외오답·confidence정확도','R17','완료','eval metrics/confusion/confidence bin 단위시험·잠정결과'],
 ['S28',47,'무승인배정/권한밖조회수정/중복업무0','R15','완료','현재auth/review全시험통과; 과거fault/56직접호출'],
 ['S29',51,'환경/version/config/model/크기·예열30분·활성10/SSE20·≥200','R17','부분','과거30분2829건있음; 최신프로세스 공식재실행없음'],
 ['S30',51,'텍스트50/PDF25/DOCX15/MD10·한도근처·원시시간/분모보존','R17','부분','과거49.9/25/15.1/10%; 대형raw git밖·현재raw위치미재확인'],
 ['S31',53,'개발도동일지연/가용성/성공목표·장애시험별도','R17','부분','서버전송/Snapshot 경계로browser목표대체불가'],
 ['S32',55,'30분개발≠운영30일·예산0.1/1%·빠른소진/반복/수집중단 실제알림','R13','외부 대기','로컬watchdog통과·현재UI경보2건; 운영원격/기간없음'],
]
table(['ID','명세 위치·기준','구현·시험','실측 수치/증거','UI','등급'],[[a,ref('docs/spec/05_SLO.md',(ROOT/'docs/spec/05_SLO.md').read_text().splitlines()[n-1])+' '+name,BY_R[r][3]+'; '+BY_R[r][4],detail+'; '+(E['load'] if a in {'S04','S05','S06','S07','S08','S09','S10','S11','S29','S30','S31'} else BY_R[r][5]),BY_R[r][6],grade] for a,n,name,r,grade,detail in SLO])

emit('## 수락 게이트 — G01–G13 / X01–X10')
emit()
GATES = [
 ['G01','R01','부분','깨끗한설치mock·과거live재시작; 현재OrbStack全절차없음'],
 ['G02','R02','완료','현재3종첨부원문강조+과거한도/부분파일'],
 ['G03','R04','완료','실제live5Run+저장분류·원문·버전, 소표본근거안정성제한'],
 ['G04','R06','부분','4종결정backend통과, 미정초안수정승인422'],
 ['G05','R07','부분','중복0 backend/과거DB=UI; 현재선행완료UI해제실패'],
 ['G06','R08','완료','현재publish/rollback 양브라우저+과거run버전고정'],
 ['G07','R11','부분','재생부작용0·순서일치; Trace오류/소요시간/실행버전 UI부족'],
 ['G08','R10','완료','현재Redis중지/2탭재연결·cancel수렴; 목표p95는S09/S10별도부분'],
 ['G09','R13','부분','집계/알림로컬실측; 원인Trace필드부족·보완대기시간미확인'],
 ['G10','R14','외부 대기','실제지원browser agent 도구호출 증거없음'],
 ['G11','R15','완료','현재466시험·권한별원문·로그아웃SSE 회귀; 운영인증한계별도'],
 ['G12','R17','부분','개발부하browser측정경계불충족+현업final60미확정'],
 ['G13','R18','외부 대기','운영배포연속30일 관측없음'],
 ['X01','R19','완료','원안/Correction DB·UI 비교'],
    ['X02','R20','완료','집계후보/지지/반례/자료부족 실제 생성과 화면 확인'],
 ['X03','R21','완료','권한/감사·미검증게시거절·단건승인분리'],
 ['X04','R23','완료','현재5재평가호출0/0·부작용0, 과거全境界diff0'],
 ['X05','R22','완료','과거used/out_of_scope/blocked·현재backend回귀; 새UI에서게시후live적용미재실행'],
 ['X06','R26','부분','현재live그래프/목록/키보드+과거實규칙체인; 버전탭현재seed'],
 ['X07','R22','완료','현재UI v1/v2게시/v1되돌림+backend既存run/과거불변'],
 ['X08','R25','완료','과거API/worker/collector재시작diff0·현재새로고침; 모든서버재시작미반복'],
 ['X09','R24','부분','효과cohort정답표본누락·충분표본API/DBseed시험만'],
 ['X10','R18','부분','현재pytest/vitest全通과, 새로운검토/업무UI결함·全live E2E未完'],
]
table(['ID','명세','구현·자동 시험','실측','UI','현재 등급','판정 설명'],[[g,ref('docs/spec/06_ACCEPTANCE.md','| '+g+' '),BY_R[r][3]+'; '+BY_R[r][4],BY_R[r][5],BY_R[r][6],grade,note] for g,r,grade,note in GATES])
emit('X02는 명세가 요구하는 수정 기록의 집계 후보 생성·자료 부족 표시를 기준으로 완료로 판정했다. 별도 사람 제안 API의 직접 작성 UI 폼은 문서화와 제품 개선 항목이며 필수 수락 조건 누락으로 단정하지 않는다. X08은 과거 재시작 보존과 현재 저장모델/backend회귀를 함께 인용한다.')
emit()
emit('### 필수 사용자 시나리오8개')
emit()
SCENARIOS=[(1,69,'일반기술','R04','완료'),(2,70,'혼합·AI/IT/현업/선행','R07','부분'),(3,71,'긴급근거·검토/우선순위','R04','완료'),(4,72,'정보부족/불가·보완·무승인0','R04','완료'),(5,73,'3종문서·손상명시','R02','완료'),(6,74,'사람수정·원안/최종·반려/정보요청','R06','부분'),(7,75,'새revision/run/버전·중복0','R03','완료'),(8,76,'성공/실패/검토대기재생·시각/상태·부작용0','R12','완료')]
table(['ID','수락기준위치','구현·자동 시험','실측','UI','등급'],[[f'SC{n:02d}',ref('docs/spec/06_ACCEPTANCE.md',(ROOT/'docs/spec/06_ACCEPTANCE.md').read_text().splitlines()[line-1])+' '+name,BY_R[r][3]+'; '+BY_R[r][4]+'; '+ref('backend/tests/acceptance/acc_a_scenarios.py'),BY_R[r][5],BY_R[r][6],grade] for n,line,name,r,grade in SCENARIOS])
emit('### 필수 실패·예방10개')
emit()
FAIL=[(82,'Jevtimeout/rate/잘못된응답·parser/저장오류→거짓성공0','R15','완료'),(83,'반복/동시승인/retry중복0·충돌설명','R07','완료'),(84,'SSE차단복원·중간재시작·저장실패복구','R10','완료'),(85,'다른user/org/무권한검토/WebMCP서버차단','R15','완료'),(86,'문서지시권한무효·초과/손상/암호화/script안전','R15','완료'),(87,'실행중policy변경/rollback·기존고정','R08','완료'),(88,'高confidence불가/정보부족·clinical/safety/regulatory/urgent/riskunknown배정0·정책해제거절','R07','완료'),(89,'A정지lease만료B완료A복귀쓰기0·구초안승인409','R07','완료'),(90,'Neo4j정지중독립分母·collector쓰기/정지알림·복구대조','R13','완료'),(91,'정보부족필수기록후보완·수시간/120s後retry原失敗불변','R13','완료')]
table(['ID','명세·예방','구현·자동시험','실측','UI','등급'],[[f'FP{i:02d}',ref('docs/spec/06_ACCEPTANCE.md',(ROOT/'docs/spec/06_ACCEPTANCE.md').read_text().splitlines()[n-1])+' '+name,BY_R[r][3]+'; '+BY_R[r][4],E['fault']+'; '+E['suite']+'; '+BY_R[r][5],BY_R[r][6],grade] for i,(n,name,r,grade) in enumerate(FAIL,1)])
emit('FP02/07/08은 backend 안전 수락조건에 한해 완료다. R06/R07의 UI 수정복구·시작버튼 결함과 모순되지 않는다. fault11/11는 과거실행이므로 현재모든장애를 새로주입했다는 주장은 하지 않는다.')
emit()
emit('### 확장 연결10단계·실패예방8개·제출물')
emit()
CONNECT=[('EC01',42,'요청분석→사람분류/담당수정','R06','부분'),('EC02',43,'AI원안·수정비교','R19','완료'),('EC03',44,'근거후보제안','R20','완료'),('EC04',45,'권한자범위확정','R21','완료'),('EC05',46,'부작용0검증→게시','R23','완료'),('EC06',47,'범위내새요청실제사용+48효과표본','R22','부분'),('EC07',49,'원문↔규칙↔후속실행','R26','부분'),('EC08',50,'중단/rollback新run·과거불변','R22','완료'),('EC09',51,'새로고침/서버재시작영속','R25','완료'),('EC10',52,'승인/권한/중복/재생/SLO回귀','R18','부분')]
XFAIL=[('XF01',56,'단건수정으로공통게시거절','R21','완료'),('XF02',57,'무권한게시/rollback403','R21','완료'),('XF03',58,'필수검토약화저장/게시/rollback거절','R22','완료'),('XF04',59,'shadow업무/배정/검토/알림/event/latest변경0','R23','완료'),('XF05',60,'게시직전run기존snapshot','R22','완료'),('XF06',61,'표본부족효과확정금지','R24','완료'),('XF07',62,'맵미저장관계0','R25','완료'),('XF08',63,'재시작관계보존','R25','완료')]
table(['ID','수락기준·위치','구현·시험','실측','UI','등급'],[[a,ref('docs/spec/06_ACCEPTANCE.md',(ROOT/'docs/spec/06_ACCEPTANCE.md').read_text().splitlines()[n-1])+' '+name,BY_R[r][3]+'; '+BY_R[r][4],BY_R[r][5],BY_R[r][6],grade] for a,n,name,r,grade in CONNECT+XFAIL])
table(['ID','수락기준','구현/시험/실측','UI','등급'],[
 ['D01',ref('docs/spec/06_ACCEPTANCE.md','코드와 실행 README')+' 실행/설정/버전/입력/시험/원시/제약/복구/보존·비밀제거',ref('README.md')+'; '+ref('docs/operations/RUNBOOK.md')+'; '+E['ops'],'문서','부분 — 운영값·raw保管限定'],
 ['D02',ref('docs/spec/06_ACCEPTANCE.md','완료 보고서에는')+' 게이트status/ID/version/date·live/mock·local/deploy',ref('artifacts/validation/final/GATE_REPORT.md')+'; 이보고서現검증','문서','부분 — 과거SHA·낡은통과修正필요'],
 ['D03',ref('docs/spec/06_ACCEPTANCE.md','개발 완료를 주장하기 전에')+' TODO/빈구현/고정응답/모의로그 검사',E['suite']+'; 本문전체code경로대조; JEV_MODE mock은명시분리','—','부분 — G10/G12/G13未通過로완료불가'],
])

emit('## 확장 관계 모델·수명·권한 계약')
emit()
MODEL=[['M00', ref('docs/spec/08_LEARNING_LOOP.md','모든 노드는') + ' 모든 노드의 tenant·생성시각·생성주체', source('ingest/store.py', 'CREATE (e:EvidenceSpan') + '; ' + test('test_judgment_graph.py','test_node_detail_counts_and_source_link_permission') + '; `scratch/test_audit_spec_gaps.py::test_persisted_evidence_node_has_creation_time_and_creator`', E['newgap'], ui('pages/judgment-map/Detail.tsx'), '부분 — 실제 EvidenceSpan.created_at 누락 재현']]

spec08=(ROOT/'docs/spec/08_LEARNING_LOOP.md').read_text().splitlines()
for n in [52,53,54,55,56,57,58,59,60,64,65,66,67,68,69,70,71]:
    text = (spec08[n-1].split('|')[2].strip() if n <= 60 else spec08[n-1].strip()[1:].rsplit('|', 2)[0].strip())
    r='R20' if text == '`RuleCandidate`' else 'R21' if text == '`RuleDecision`' else 'R19' if 'Correction' in text else 'R22' if any(v in text for v in ['RuleVersion','APPLIED','PUBLISHED']) else 'R23' if 'Validation' in text else 'R25'
    MODEL.append([f'M{len(MODEL):02d}',f'`docs/spec/08_LEARNING_LOOP.md:{n}` '+text,BY_R[r][3]+'; '+test('test_judgment_graph.py','test_rule_graph_matches_stored_nodes_and_edges_exactly'),E['ext']+'; '+E['map'],BY_R[r][6],'완료'])
table(['ID','노드·관계 수락기준','구현·시험','실측','UI','등급'],MODEL)
LIFE=[]
for n in [79,80,81,82,83,84,88,89,90,91,93,97,98,99,100,101,112,114,116]:
    text=spec08[n-1].strip().strip('|').replace('|',' / ')
    r='R23' if n in {97,98,99} else 'R24' if n in {100,101} else 'R26' if n in {112,114,116} else 'R21' if n in {79,80,81,82,88,89,90,91} else 'R22'
    LIFE.append([f'LC{len(LIFE)+1:02d}',f'`docs/spec/08_LEARNING_LOOP.md:{n}` '+text,BY_R[r][3]+'; '+BY_R[r][4],BY_R[r][5],BY_R[r][6],'부분' if n == 91 else '완료'])
table(['ID','수명·권한·검증·화면 계약','구현·시험','실측','UI','등급'],LIFE)
emit('LC07(후보 제안 권한)의 API는 구현됐다. 별도 사람 직접 작성 폼은 필수 조건으로 단정하지 않는다. LC14(검증결과 요약)의 shadow ValidationRun은 labeled_count를 제공하지만 **게시후 effects cohort에는 없음**을 구별한다. 모델 모든노드의 생성주체/버전 속성은 모델정의와 fixture가 부분씩 제공하므로 전노드 동일메타 coverage는 추가실측 권장(추정); M행 완료는 실제노드/관계 저장과조회 의미에 한정한다. M00의 생성시각 누락은 별도 실패로 기록했다.')
emit()

emit('## TASK 전수 — T00–T38')
emit()
T_META={
 0:('R14','외부 대기','지원agent 호출환경'),1:('R01','부분','현재OrbStack clean/live설치없음'),2:('R04','완료','Jev실계약/비민감호출'),3:('R05','완료','가변업무분해/근거설계'),4:('R07','완료','모델·잠금·lease·journal기반'),5:('R15','완료','개발역할/조직경계; 운영IdP별도'),6:('R03','완료','접수/revision/幂등/조회'),7:('R02','완료','3종파서/위치/격리/한도'),8:('R11','완료','worker永續/lease/Trace저장; UI부족T17'),9:('R04','완료','실제판단/근거/초안서비스'),10:('R03','완료','新채팅접수/파일/보완/복원'),11:('R06','부분','미정원안검증이수정적용前이라422'),12:('R07','완료','backend task전이/조회; UI부족T13'),13:('R07','부분','미정수정복구+선행확인완료UI'),14:('R10','완료','SSE契約/재개/최종연결'),15:('R08','완료','DynamicConfig/API/rollback'),16:('R08','완료','정책UI現在양browser'),17:('R11','부분','Trace 오류/시간/版本 UI缺'),18:('R13','부분','보완대기시간/운영30일·remote알림'),19:('R13','부분','Trace 상세완결성·보완대기未연결'),20:('R14','외부 대기','실제지원agent未확보'),21:('R18','부분','현재全liveE2E未完/새UI결함'),22:('R15','완료','과거fault11/11·현재관련integration回귀'),23:('R16','부분','현재 주요axe/keyboard/54캡처 통과; 전 여정 키보드 증거 없음'),24:('R17','외부 대기','현업confirmed·final60'),25:('R17','부분','browserrender境界未측정·最新30분없음'),26:('R18','부분','backup Task/RuleVersion0·운영요건未확정'),27:('R18','부분','2026-10-03 gateclaim 갱신필요'),28:('R18','외부 대기','실제배포연속30일'),29:('R25','부분','graph제약/질의 동작; 공통 노드시각 누락'),30:('R19','완료','Correction保存/비교'),31:('R20','완료','집계후보/지지/반례/자료부족'),32:('R21','부분','규칙수명/변경권한 정상; 검토자/운영자 조회403'),33:('R23','완료','shadow部작용0'),34:('R22','완료','고정규칙/APPLIED'),35:('R24','부분','effect labeled_count缺·40seed밖UI검증없음'),36:('R24','부분','effect정답표본/사람제안UI'),37:('R26','부분','Map/source/version/list 동작; 원문노드 생성시각 누락'),38:('R18','부분','현재X연결全再실행없음·X09빈필드·새UI결함')}
task_lines=(ROOT/'TASK.md').read_text().splitlines()
task_rows=[]
for n in range(39):
    ident=f'T{n:02d}'
    line_number,text=next((i+1,v) for i,v in enumerate(task_lines) if v.startswith('| '+ident+' |'))
    name=text.split('|')[2].strip()
    r,grade,note=T_META[n]
    code=BY_R[r][3]
    tests=BY_R[r][4]
    if n==1: code=ref('Makefile')+'; '+ref('backend/pyproject.toml')+'; '+ref('frontend/package.json')
    if n==2: code=source('judgment/jev_client.py','class JevClient')
    if n==4: code=source('db/schema.py')+'; '+source('db/runs.py')+'; '+source('journal/writer.py'); tests=test('test_db_foundation.py','test_schema_twice_and_assignment_contention')+'; '+test('test_domain_journal.py','test_multiprocess_journal_and_forbidden_fields')
    if n==8: code=source('jobs/worker.py','class JobContext'); tests=test('test_worker.py','test_takeover_rejects_old_steps_results_events_and_heartbeat')
    if n==21: code=ref('backend/tests/acceptance/acc_a_scenarios.py')+'; '+ref('frontend/e2e/acceptance/scenarios.spec.ts')
    if n==22: code=ref('backend/tests/fault/scenarios.py')+'; '+ref('scripts/fault/run.sh')
    if n==24: code=ref('eval/runner.py')+'; '+source('evaluation/service.py','async def save_label('); tests=test('test_evaluation_api.py','test_label_edit_defer_resume_disagreement_and_consensus')
    if n==25: code=ref('loadtest/run.sh')+'; '+ref('loadtest/measure.py') if (ROOT/'loadtest/measure.py').exists() else ref('loadtest/run.sh')
    if n==26: code=ref('docs/operations/DEPLOYMENT.md')+'; '+ref('docs/operations/RUNBOOK.md'); tests=E['ops']
    if n==27: code=ref('artifacts/validation/final/GATE_REPORT.md'); tests='아래현재검증6명령·낡은주장표'
    if n==28: code=source('monitoring/slo.py','def error_budget('); tests=test('test_monitoring_collector.py','test_error_budget_is_unverified_before_30_days')
    if n==38: code=ref('backend/tests/acceptance/extension/scenario_r.py')+'; '+ref('frontend/e2e/extension/extension-r.spec.ts')
    task_rows.append([ident,name,f'`TASK.md:{line_number}`'+(' ; '+ref('docs/spec/08_LEARNING_LOOP.md','| '+ident+' |') if n>=29 else ''),code,tests,BY_R[r][5],BY_R[r][6],grade,note])
table(['ID','작업','명세/목록','구현/산출물','자동시험','실측','UI','등급','잔여'],task_rows)

emit('## 낡은 게이트 통과 주장·문서 불일치')
emit()
table(['기존 주장 위치','현재 근거','현재 판단·권장 정정'],[
 [ref('artifacts/validation/final/GATE_REPORT.md','코드:'),'현재HEAD00cc01e(README 문서 변경); aaffd41/0514443/3dd900a/efbb9c7/e550dce/ed0e1e2 이후','e55b42d+미커밋 범위의 과거판정임을 유지하고 최신판정 부록 분리'],
 [ref('artifacts/validation/final/GATE_REPORT.md','| G04 검토'),'AUDIT-P1-01 양browser422; review/service원안검증선행','통과→부분(미정원안수정복구 제외), 정상4종결정 통과는 유지'],
 [ref('artifacts/validation/final/GATE_REPORT.md','| G05 업무'),'AUDIT-P1-02 UIdisabled/API200','통과→부분(확인업무완료 후 시작동선); 중복배정0은 유지'],
 [ref('artifacts/validation/final/GATE_REPORT.md','| G07 흐름'),'SPEC-F02 drawer 오류/소요시간/실행model/schema 표시누락','재생 무부작용 통과와 Trace완전표시부분을 분리'],
 [ref('artifacts/validation/final/GATE_REPORT.md','| G09 관찰'),'현재Trace필드不足·보완대기시간미확인(추정)','집계정합/로컬알림과 완결된진단/별도대기지표를 분리'],
 [ref('artifacts/validation/final/GATE_REPORT.md','| G08 SSE'),'aaffd41 이후新SSE UI·e550dce/ed0e1e2 취소event; current2탭재연결證','과거354.9ms는snapshotHTTP 경계; currentUI정합증거참조·p95browser표시주장금지'],
 [ref('artifacts/validation/final/GATE_REPORT.md','| G12 성능'),'T25 REPORT:26 browser렌더미측정; t25-sse:50도동일·최신30분없음','개발성능13/13을명세상browserend-to-end통과로해석하지말고부분'],
 [ref('artifacts/validation/final/GATE_REPORT.md','| X09 효과'),'SPEC-F01 각effectscohort labeled_count 없음;40seed효과시험만','통과(제한)→부분, 필요한정답표본필드와현재UI실측추가'],
 [ref('artifacts/validation/final/GATE_REPORT.md','| X06 판단'),'SPEC-F03: 08:48의 원문 노드 생성시각 없음; 맵 원문 노드 상세 시각도 비어 있음','관계·양방향·목록·키보드 통과를 유지하고 공통 메타데이터 누락은 부분으로 별도 표기'],
 [ref('artifacts/validation/final/GATE_REPORT.md','| X10 회귀'),'현재backend466/Vitest358 통과·browser94개78/14/2·전live連결미완','과거136/37全통과는과거스냅샷; 현재자동시험과E2E한계를별도'],
 [ref('artifacts/validation/final/GATE_REPORT.md','마스킹은 구현되지'),'domain/masking.py:61·judgment/service.py:95·test_external_state_masked...통과','마스킹미구현 문구는낡음; 패턴마스킹구현+민감全유형/송신全경로실측한계로정정'],
 [ref('artifacts/validation/final/GATE_REPORT.md','npm 감사 경고'),'OPS_AUDIT prod moderate2/전체audit/Python未완료','예전7건 수치를 current 결과로재사용금지; 감사시각/범위별記錄'],
 [ref('TASK.md','| T36 |'),'shadow_api.py GET/list존재·validationCard서버조회시험/과거X08재시작','"검증결과조회API없음/sessionStorage" 잔여문구는해소됨'],
 [ref('TASK.md','| T24 |'),ref('eval/README.md','| AI 필요성 macro-F1')+' qsetv2 .807/1/1/1/.570','T24의qsetv1 .253/.554/.919/.857/.217은과거값; GATE팀F1 .556과README.570은run/계산정의구분필요'],
 [ref('docs/spec/08_LEARNING_LOOP.md','상태: 설계 확장'),'확장実装/API/tests/과거X全증거','요구문서의설계상태자체는보존하되 구현추적문서로最新상태연결'],
 [ref('artifacts/review/requirements-gap.md','근거 원문 페이지'),'현재EvidenceViewer原文anchor·Map크게보기/versiontabs·마스킹 구현','과거P2未구현 주장3개는 현재해소; 이번감사에서새결함과혼동금지'],
])
emit('G10 차단·G12 현업정답 미확정·G13 운영30일 미검증과 "개발 완료를 선언하지 않는다"는 과거결론은 현재도 유효하다. 과거노드/카운트/파일한도/권한 결과가 모두 실패로 바뀌었다는 주장은 하지 않는다. 새UI를 덮는 과거전면통과주장과 확인된현재반례만 낡음으로 표시했다.')
emit()

emit('## 명세 기능 누락·구현 기능의 문서 누락')
emit()
table(['유형','항목','명세/구현/시험·실측 근거','권장 문서/구현 보완'],[
 ['명세→구현 누락','효과 각비교의사람정답표본수','docs/spec/04:39; effects._metrics·SPEC-F01실패','effects cohort labeled_count/정답정의·UI·DB/API 대조'],
 ['명세→UI 누락','Trace오류·소요시간·model/schema실행버전','docs/spec/04:13; API필드는존재·SPEC-F02실패','drawer errors/duration/versions 표시·실패/재시도例실측'],
 ['명세→저장 누락','모든 관계 노드의 생성시각·생성주체','docs/spec/08:48; EvidenceSpan.created_at 실제 None·SPEC-F03실패; 직접 주체속성도 코드에 없음','원문 노드 생성시각/주체 저장, 기존 데이터는 근거가 있는 경우만 보완하고 누락은 명시'],
 ['명세→조회 누락','검토자/운영자의 규칙 조회','docs/spec/08_LEARNING_LOOP.md:91; SPEC-F04 두 역할 실제403; rules_api.py:21/113; Learning.tsx:51','조회와 변경 권한을 분리하여 tenant·조직 범위 내 읽기 허용, 원문은 기존 권한 유지'],
 ['코드 기능의 UI 확장 제안','사람규칙후보직접제안','08:26/88·candidates_api.propose存在·E2E_AUDIT API준비','Learning에제안폼/지지Correction 선택·권한/미지원값안내'],
 ['명세→측정 누락(추정)','사용자보완답변대기 별도시간','05:33; aggregates.summarize반환·Monitoring검색에서없음','보완요청→답변wait·unresolved집계/API/UI·최초SLO時計유지'],
 ['명세→실측 누락','저장→browser상태반영/복구표시 p95','05:20/21; T25:26·t25-sse:50의경계제한','브라우저DOM反영timestamp·切断復元 동일종료점30분부하'],
 ['명세→외부조건','WebMCPagent·confirmedfinal60·운영30일','G10/G12/G13·eval/README·slo未검증시험','지원agent/현업책임자/운영배포 확보 뒤실측'],
 ['코드→명세문서 누락','정지/협조적취소·author/operator·terminalrace·재분석',source('jobs/cancel.py','async def cancel_run(')+'; '+ui('pages/Main.tsx','async function cancel(')+'; '+E['cancel'],'05의취소수문장外UX/06시나리오에없음; 자동race/latewrite/UI복원 수락조건추가'],
 ['코드→명세문서 누락','ChatGPT式 대화목록/하단고정composer·단일대화접수',ui('pages/Main.tsx')+'; '+ref('frontend/e2e/chat-intake.spec.ts','layout ${size.w}')+'; aaffd41','02흐름은있으나현재대화기준동선/키보드/복원·960折りたたみ 추적목록없음; 화면배치자유는유지'],
 ['코드→명세문서 누락','잠정판단/slow/worker-wakeup·정식판단과별도상태',source('judgment/service.py','async def save_partial(')+'; '+test('test_progressive_judgment.py','test_partial_result_precedes_evidence_and_final_commit'),'05:9 최초완료정의는保持; 02에잠정표시와미배정/취소/復元수락조건'],
 ['코드→명세문서 누락','mask된title/preview/기존요청lazybackfill·owner/source권한',source('ingest/store.py','def _display_fields(')+'; '+test('test_api_preview.py','test_request_preview_masking_and_owner_permissions')+'; 3dd900a/efbb9c7','목록API추가필드/60·140제한·목록제목권한 vs preview권한·legacy이행 기준'],
 ['코드→명세문서 누락','labeler평가 UI/독립표본라벨/불일치합의',source('evaluation/service.py','async def confirm_consensus(')+'; '+ui('pages/Evaluation.tsx')+'; '+test('test_evaluation_api.py','test_label_edit_defer_resume_disagreement_and_consensus'),'05평가목표는있음; 02역할·권한·final예측숨김·labelingstate 수락조건추가'],
 ['구현→낡은문서','마스킹·원문Viewer·Map확대/버전탭',source('domain/masking.py','def mask_for_external(')+'; '+ui('components/EvidenceViewer.tsx')+'; '+ui('pages/JudgmentMap.tsx','크게 보기'),'GATE/P2 미구현文句와最新architecture/test証거 연결'],
])

emit('## 우선순위 미비 목록·권장 조치·규모')
emit()
table(['우선순위/ID','미비 또는 개선 제안·현재 증거','권장 조치·수락 기준','규모'],[
 ['P0','현재감사에서새로확인한P0 없음; 安全backend시험通過','G10/G12/G13 未충족중완료/운영SLO 선언을보류','—'],
 ['P1-01','AUDIT-P1-01 미정초안수정422·R06/G04/T11/T13','원본값검증前 수정내용적용; 방식/조직/산출물미정필드修正입력; Chromium/WebKit expected200再검증','M'],
 ['P1-02','AUDIT-P1-02 선행確認완료UIdisabled/API200·R07/G05/T13','backend/프런트한開始가능性 projection; 확인완료後UI enabled·전이200·未完409','S'],
 ['P1-03','SPEC-F01 effect cohort labeled_count 없음·R24/X09/T35/36','사람확정정답定義와cohort별count·조건표시; knowncohort DB/API/UI一致·sample不足미확정','M'],
 ['P1-04','SPEC-F02 Trace 오류/시간/model/schema 없는 UI·R11/G07/T17','같은실행의error_class/duration_ms/versions表示; 실패와재시도모델버전drawer可読·원문권한継続','S'],
 ['P1-05','G12 S09/S10 browser종료경계未測·최신공식30분 없음','Event저장→DOM·网络복원→snapshot DOM 측정;30분10VU/20SSE/200+·실패120s 포함·raw保存','M'],
 ['P1-06','현업정답최종60·품질目標未확정/잠정AI .807·팀.570','외부책임자confirmed100+후 final60고정평가; macroF1/recall/team·confusion/version 결과보고','L (외부대기)'],
 ['P1-07','운영30일·remote警報·IdP/복원/보존조건未확정·R18/G13','운영계획/책임자정하고30일분모/누락/예산/실제수신·Task/RuleVersion있는복원리허설','L (외부대기)'],
 ['P2-01 (제품 개선 제안)','사람후보API있으나 UI제안폼 없음; 명세 위반으로 단정하지 않음','제안폼/근거선택/role보호 추가후 후보→승인→shadow→게시全UI여정','M'],
 ['P2-02','05:33 보완대기별도시간 未확인(추정)','측정계약 확인후 wait p50/p95/미답변count 명시; 완료판단/SLOclock불변','M'],
 ['P2-08','SPEC-F04 검토자/운영자 규칙 조회403·08:91/R21/T32','읽기 역할과 변경 역할을 분리; reviewer/operator 목록·상세·효과 접근200·범위 밖404·변경403·원문 기존 권한 시험; Learning 조회 연결','M'],
 ['P2-07','SPEC-F03 원문 노드 생성시각 없음·08:48/R25/R26/T29/T37','모든 노드의 시각/주체·버전 의미를 계약으로 고정; 원문 생성시각 저장·DB/API/맵 상세 대조·근거 없는 과거 시각 합성 금지','M'],
 ['P2-03','G01 새설치현재OrbStack+live 未재현','깨끗한임시copy·전용Neo4j/port/tenant에서README설치→live→재시작·중복0','S'],
 ['P2-04','GATE/TASK/P2文書 SHA/수치/기능상태 낡음','過거結果유지·최신部록추가;136/37→466/358·취소/title/source/provisional追跡','S'],
 ['P2-05','T24/GATE/README 팀F1 run별.217/.556/.570 혼재','수치별runid/model/qset/teams計算法固定·根據JSONリンク·最終정답과구분','S'],
 ['P2-06','G10 실제agent 호출주체未확보','지원browser버전/feature/도구발견·3조회·무권한404·미지원웹 재현증거확보','S (외부대기)'],
])
emit('규모 S=대체로 한 기능/문서 또는 짧은 재현, M=API·UI·시험/계측을 함께 조정, L=여러 운영 구성 또는 현업/운영 기간 필요. 일정 견적이나 검증된 공수는 아니다.')
emit()
emit('## 문서 자체 검증')
emit()
emit('R26개·T39개·G13개·X10개 ID 누락 0건, 파일:줄 참조 2114개 모두 파일 존재 및 줄 범위 확인. 검증 출력: `artifacts/review/completeness/scratch/audit-spec-document-check.log`. 요구사항 최종 등급은 완료13·부분12·미구현0·외부대기1이다.')
emit()
emit('## 건너뛴 항목·한계')
emit()
emit('- 이번 SPEC 감사에서는 신규 live 모델 호출, 전용 서버 기동, 전체 브라우저 시험을 실행하지 않았다. 현재 UI 실측은 같은 제품 코드에서 진행한 E2E_AUDIT와 과거 REM 보고서를 출처와 함께 인용했다. E2E 감사의 78 통과·14 실패·2 skip 및 미실행 60개와 확장 시험 수집 실패를 전체 통과로 해석하지 않았다.')
emit('- 30분 부하, 전체 장애 주입, 깨끗한 환경 설치, 백업·복원, 운영 30일 관측은 다시 실행하지 않았다. 과거 전용 환경의 결과와 현재 관련 단위·통합 시험 통과를 구분했다. 필요한 실측이 없으면 부분 또는 외부 대기로 표시했다.')
emit('- 신규 요구 재현 시험 8건(효과 1·노드 생성시각 1·조회 권한 2·Trace 4)은 실패 상태로 보존했다. 점검 전용 작업의 제품 수정 금지에 따라 수정 및 수정 후 검증은 수행하지 않았다. 기존 pytest/Vitest 전체 통과와 이 추가 실패는 함께 존재하며 기존 시험이 해당 수락 조건을 검사하지 않았음을 보여 준다.')
emit('- 필수SAP외부직접쓰기 제외/내부배정/고영향필수검토/무승인0 범위는 '+ref('docs/spec/01_GOALS_REQUIREMENTS.md','첫 버전의 SAP 범위')+' 및 '+source('domain/eligibility.py','def evaluate_auto_assign(')+'로유지되고 관련안전시험이현재통과했다. 외부SAP/ticket쓰기 기능을추가완료로기록하지않았다.')
emit('- docs/spec/08의미확정사항: 후보생성은결정적집계이며 사람제안API추가, min_effect_sample은policy기본20. 그기본값자체가현업효과보장의검증된임계값이라는주장은하지않는다. 충분표본효과라벨의사용자화면실측은잔여다.')
emit('- 파일:줄은 보고서 작성 시점의 경로다. 이후 수정으로 줄번호가 바뀌면 함께 기록한 시험 이름과 실행 ID를 사용한다. 제품 코드·docs/spec·docs/design-handoff·docs/architecture 수정 및 git commit/push는 수행하지 않았다.')
report = '\n'.join(lines) + '\n'
wording = {
    '折りたたみ': '접기', 'リンク': '링크', '一致': '일치', '不足': '부족',
    '保存': '보존', '保持': '유지', '保管限定': '보관 제한', '修正': '수정',
    '全再': '전체 재', '全境界': '전체 경계', '全通': '전체 통', '全': '전체',
    '分母': '분모', '切断復元': '차단·복원', '原失敗': '원래 실패', '原文': '원문',
    '可読': '읽기 가능', '報告原文': '보고서 원문', '境界未': '경계 미', '契約': '계약',
    '存在': '존재', '安全': '안전', '定義': '정의', '実装': '구현', '實': '실제',
    '幂': '멱', '復元': '복원', '报告': '보고서', '文句': '문구', '文書': '문서',
    '既存': '기존', '時計': '시계', '最新': '최신', '最終': '최종', '未完': '미완료',
    '未測': '미측정', '未通過': '미통과', '根據': '근거', '永續': '영속', '版本': '버전',
    '現在': '현재', '目標未': '목표 미', '確認': '확인', '結果': '결과', '継続': '유지',
    '网络': '네트워크', '表示': '표시', '計算法固定': '계산 방법 고정', '記錄': '기록',
    '語句': '문구', '警報': '경보', '追跡': '추적', '通過': '통과', '開始': '시작',
    '未': '미', '再': '재', '例': '예시', '前': '전', '反': '반', '回': '회', '外': '외',
    '式': '식', '後': '후', '性': '성', '新': '새 ', '本': '이 ', '現': '현재 ',
    '缺': '누락', '証': '증거', '試': '시', '證': '증거', '連': '연', '過': '과거',
    '部': '부', '高': '높은 ',
}
wording.update({'증거거': '증거', '과거거': '과거'})
for original, replacement in sorted(wording.items(), key=lambda pair: -len(pair[0])):
    report = report.replace(original, replacement)
report = report.replace('증거거', '증거').replace('과거거', '과거')
OUT.write_text(report)
print(f'{OUT}: {len(lines)} lines, R={len(R)}, SLO={len(SLO)}, G/X={len(GATES)}, TASK={len(task_rows)}')
