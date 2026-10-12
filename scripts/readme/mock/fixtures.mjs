// Mock API for the decision-chat-bot frontend. Shapes follow frontend/src/api/*.ts, src/state/*.ts and the vitest mocks.
// routeApi(page, { role }) installs page.route for every /api/** path and an EventSource stub (no real SSE server exists).

const NOW = Date.now();
const ago = (minutes) => new Date(NOW - minutes * 60_000).toISOString();
const days = (d, extraMin = 0) => ago(d * 1440 + extraMin);

export const ALL_ROLES = ['requester', 'reviewer', 'team_member', 'operator', 'policy_editor', 'rule_admin', 'labeler'];
export const USER = { id: 'usr_kim_review', user_id: 'usr_kim_review', name: '김검토', display_name: '김검토', roles: ALL_ROLES, mode: 'live', tenant_id: 't-demo' };

// ---------------------------------------------------------------- requests
const REQ = {
  sap: 'req_5ap7c3e91f', room: 'req_r00m4b2d7a', demand: 'req_dem8a61c04', ship: 'req_5h1p9e2b3c', inv: 'req_1nv6d0f5a8',
};
const RUN = { sap2: 'run_5ap2b7e19c', sap1: 'run_5ap1a0c4d2', room: 'run_r00m7c1e3a', demand: 'run_dem3e8b4f1', ship: 'run_5h1p6a2d90', inv: 'run_1nv4c9e7b2' };
const REV = { sap: 'rev_5ap0001a', room: 'rev_r00m001a', demand: 'rev_dem0001a', ship: 'rev_5h1p001a', inv: 'rev_1nv0001a' };

const requestTexts = {
  [REQ.sap]: 'SAP에서 내려받은 매출 CSV를 월별·사업부별로 집계해 경영회의 화면에 보여 주세요. 지금은 매달 재무팀이 엑셀로 피벗을 다시 만들고 있어 반나절이 걸립니다. 10월 말 경영회의부터 쓰고 싶습니다.',
  [REQ.room]: '본사 3~7층 회의실 예약 현황을 한눈에 보는 대시보드가 필요합니다. 그룹웨어 예약 데이터를 읽어 층별 사용률과 노쇼 비율을 주간 단위로 보여 주면 좋겠습니다.',
  [REQ.demand]: '병원별 지난 24개월 판매량으로 다음 달 수요를 예측하고, 예측 대비 실적이 20% 이상 미달하는 병원은 영업 담당자에게 알림을 보내 주세요. 거래처 마스터는 IT팀이 관리합니다.',
  [REQ.ship]: '오늘 오전 9시 이후 출하 지시가 ERP에서 물류센터로 넘어가지 않고 멈춰 있습니다. 오늘 16시 마감 물량이 120건이라 원인 확인이 급합니다. 인터페이스 로그는 첨부했습니다.',
  [REQ.inv]: '분기 재고 실사 결과와 ERP 장부 재고를 자동으로 대사해 차이 품목만 목록으로 뽑아 주세요.',
};
const requestTitles = {
  [REQ.sap]: 'SAP 매출 CSV 월별 집계 화면', [REQ.room]: '회의실 예약 현황 대시보드', [REQ.demand]: '병원별 수요 예측과 미달 알림',
  [REQ.ship]: '출하 지시 중단 원인 확인', [REQ.inv]: '재고 실사 자동 대사',
};
const requestItems = [
  { id: REQ.ship, status: 'review_pending', created_at: ago(38) },
  { id: REQ.demand, status: 'review_pending', created_at: ago(165) },
  { id: REQ.sap, status: 'assigned', created_at: ago(420) },
  { id: REQ.room, status: 'review_pending', created_at: days(1, 95) },
  { id: REQ.inv, status: 'assigned', created_at: days(4, 30) },
];
const statusOf = (id) => requestItems.find((r) => r.id === id)?.status || 'received';
const runOf = { [REQ.sap]: RUN.sap2, [REQ.room]: RUN.room, [REQ.demand]: RUN.demand, [REQ.ship]: RUN.ship, [REQ.inv]: RUN.inv };
const revOf = { [REQ.sap]: REV.sap, [REQ.room]: REV.room, [REQ.demand]: REV.demand, [REQ.ship]: REV.ship, [REQ.inv]: REV.inv };

function requestDetail(id) {
  return {
    request: { id, status: statusOf(id), active_run_id: runOf[id], revision_number: 1, info_requested: null, needed_info: null },
    revisions: [{ id: revOf[id], number: 1, text: requestTexts[id] }],
    attachments: id === REQ.ship ? [{ id: 'att_5h1p_log', filename: 'if_shipment_0912.log.md', status: 'ok', byte_count: 48213, content_type: 'text/markdown', revision_id: REV.ship }] : [],
    active_run: { status: 'succeeded' },
  };
}

const ev = (id, text, location = { paragraph: 0, sentence: 0 }) => ({ id, source: 'chat', attachment_id: null, location, source_text: text, probability: 0.91 });
const judgments = {
  [REQ.sap]: {
    classifications: { ai_need: '불필요', feasibility: '가능', urgency: '일반', lead_org: 'IT팀' },
    summary: { text: 'SAP 매출 CSV를 월별·사업부별로 집계해 경영회의용 화면으로 제공하는 요청입니다. 정형 집계라 AI 없이 일반 기술로 구현할 수 있고, 10월 말 경영회의가 목표 시점입니다.', author: 'llm:anthropic/claude-sonnet-4-5', base: { text: 'SAP에서 내려받은 매출 CSV를 월별·사업부별로 집계해 경영회의 화면에 보여 주세요.', author: 'code:extractive@1' } },
    outputs: [
      { id: 'out_sap_ai', question_id: 'ai_need', type: 'Choice', value: '불필요', confidence: 0.93, evidence: [ev('span_sap_1', '매출 CSV를 월별·사업부별로 집계해')] },
      { id: 'out_sap_fe', question_id: 'feasibility', type: 'Choice', value: '가능', confidence: 0.88, evidence: [ev('span_sap_2', '지금은 매달 재무팀이 엑셀로 피벗을 다시 만들고', { paragraph: 0, sentence: 1 })] },
      { id: 'out_sap_ur', question_id: 'urgency', type: 'Choice', value: '일반', confidence: 0.81, evidence: [ev('span_sap_3', '10월 말 경영회의부터 쓰고 싶습니다', { paragraph: 0, sentence: 2 })] },
      { id: 'out_sap_lo', question_id: 'lead_org', type: 'Choice', value: 'IT팀', confidence: 0.86, evidence: [ev('span_sap_1', '매출 CSV를 월별·사업부별로 집계해')] },
      { id: 'out_sap_it', question_id: 'it_team_involvement', type: 'Noul', value: null, noul: 0.92, evidence: [] },
    ],
    draft_tasks: [
      { id: 'dt_sap_1', title: 'SAP 매출 CSV 적재 파이프라인', method: '일반 기술', lead_org: 'IT팀', collab_orgs: ['현업'], predecessors: [], deliverable: '일 1회 적재 배치', description: 'SFTP로 받은 CSV를 검증 후 분석 DB에 적재' },
      { id: 'dt_sap_2', title: '월별·사업부별 집계 뷰', method: '일반 기술', lead_org: 'IT팀', collab_orgs: [], predecessors: ['SAP 매출 CSV 적재 파이프라인'], deliverable: '집계 SQL 뷰' },
      { id: 'dt_sap_3', title: '경영회의 화면 검수', method: '사람', lead_org: '현업', collab_orgs: ['IT팀'], predecessors: ['월별·사업부별 집계 뷰'], deliverable: '검수 체크리스트' },
    ],
    review_reasons: [], review: { status: 'approved' },
    rule_effects: [{ rule_version: 'R-LEAD_ORG-01@2', source: 'rule:R-LEAD_ORG-01@v2', effect: 'rule', outcome: 'used', target: 'lead_org', before: 'AI팀', after: 'IT팀', matches: [{ unit_id: 'span_sap_1', char_start: 18, char_end: 20, keyword: '집계' }], config_version: 14 }],
  },
  [REQ.room]: {
    classifications: { ai_need: '불필요', feasibility: '가능', urgency: '일반', lead_org: 'IT팀' },
    summary: { text: '그룹웨어 회의실 예약 데이터로 층별 사용률·노쇼 비율 대시보드를 만드는 요청입니다.', author: 'code:extractive@1' },
    outputs: [
      { id: 'out_room_ai', question_id: 'ai_need', type: 'Choice', value: '불필요', confidence: 0.9, evidence: [ev('span_room_1', '그룹웨어 예약 데이터를 읽어 층별 사용률과 노쇼 비율을')] },
      { id: 'out_room_lo', question_id: 'lead_org', type: 'Choice', value: 'IT팀', confidence: 0.64, evidence: [ev('span_room_2', '본사 3~7층 회의실 예약 현황을 한눈에 보는 대시보드')] },
    ],
    draft_tasks: [
      { id: 'dt_room_1', draft_task_id: 'dtk_room_1', title: '그룹웨어 예약 API 연동', method: '일반 기술', lead_org: 'IT팀', collab_orgs: [], predecessors: [], deliverable: '예약 데이터 수집 배치' },
      { id: 'dt_room_2', draft_task_id: 'dtk_room_2', title: '층별 사용률 대시보드', method: '일반 기술', lead_org: 'IT팀', collab_orgs: ['현업'], predecessors: ['그룹웨어 예약 API 연동'], deliverable: '주간 대시보드' },
    ],
    review_reasons: ['Choice confidence 미충족: lead_org'], review: { status: 'pending' },
  },
  [REQ.demand]: {
    classifications: { ai_need: '필요', feasibility: '조건부 가능', urgency: '일반', lead_org: 'AI팀' },
    summary: { text: '병원별 24개월 판매 이력으로 다음 달 수요를 예측하고 20% 이상 미달 병원을 영업 담당자에게 알리는 요청입니다. 거래처 마스터 정합성이 전제 조건입니다.', author: 'code:extractive@1' },
    outputs: [
      { id: 'out_dem_ai', question_id: 'ai_need', type: 'Choice', value: '필요', confidence: 0.87, evidence: [ev('span_dem_1', '지난 24개월 판매량으로 다음 달 수요를 예측하고')] },
      { id: 'out_dem_fe', question_id: 'feasibility', type: 'Choice', value: '조건부 가능', confidence: 0.71, evidence: [ev('span_dem_2', '거래처 마스터는 IT팀이 관리합니다', { paragraph: 0, sentence: 1 })] },
      { id: 'out_dem_lo', question_id: 'lead_org', type: 'Choice', value: 'AI팀', confidence: 0.62, evidence: [ev('span_dem_1', '지난 24개월 판매량으로 다음 달 수요를 예측하고')] },
    ],
    draft_tasks: [
      { id: 'dt_dem_1', draft_task_id: 'dtk_dem_1', title: '거래처 마스터 정합성 점검', method: '사람', lead_org: 'IT팀', collab_orgs: ['현업'], predecessors: [], deliverable: '병원 코드 매핑표' },
      { id: 'dt_dem_2', draft_task_id: 'dtk_dem_2', title: '병원별 수요 예측 모델', method: 'AI', lead_org: 'AI팀', collab_orgs: ['IT팀'], predecessors: ['거래처 마스터 정합성 점검'], deliverable: '월간 예측 배치' },
      { id: 'dt_dem_3', draft_task_id: 'dtk_dem_3', title: '미달 병원 알림 발송', method: '일반 기술', lead_org: 'IT팀', collab_orgs: ['현업'], predecessors: ['병원별 수요 예측 모델'], deliverable: '영업 담당자 알림' },
    ],
    review_reasons: ['Choice confidence 미충족: feasibility/lead_org'], review: { status: 'pending' },
  },
  [REQ.ship]: {
    classifications: { ai_need: '불필요', feasibility: '가능', urgency: '긴급', lead_org: 'IT팀' },
    summary: { text: '오늘 09시 이후 ERP→물류센터 출하 지시 인터페이스가 멈춰 16시 마감 물량 120건이 대기 중입니다. 즉시 원인 확인이 필요한 긴급 장애 요청입니다.', author: 'code:extractive@1' },
    outputs: [
      { id: 'out_ship_ur', question_id: 'urgency', type: 'Choice', value: '긴급', confidence: 0.97, evidence: [ev('span_ship_1', '오늘 16시 마감 물량이 120건이라 원인 확인이 급합니다', { paragraph: 0, sentence: 1 })] },
      { id: 'out_ship_lo', question_id: 'lead_org', type: 'Choice', value: 'IT팀', confidence: 0.91, evidence: [ev('span_ship_2', '출하 지시가 ERP에서 물류센터로 넘어가지 않고 멈춰')] },
    ],
    draft_tasks: [
      { id: 'dt_ship_1', draft_task_id: 'dtk_ship_1', title: '출하 인터페이스 로그 분석', method: '사람', lead_org: 'IT팀', collab_orgs: [], predecessors: [], deliverable: '장애 원인 보고' },
      { id: 'dt_ship_2', draft_task_id: 'dtk_ship_2', title: '미전송 출하 지시 재전송', method: '일반 기술', lead_org: 'IT팀', collab_orgs: ['현업'], predecessors: ['출하 인터페이스 로그 분석'], deliverable: '재전송 결과 120건' },
    ],
    review_reasons: ['필수 검토: urgent'], review: { status: 'pending' },
  },
  [REQ.inv]: {
    classifications: { ai_need: '불필요', feasibility: '가능', urgency: '일반', lead_org: 'IT팀' },
    summary: { text: '분기 재고 실사 결과와 ERP 장부 재고를 자동 대사해 차이 품목만 추출하는 요청입니다.', author: 'code:extractive@1' },
    outputs: [{ id: 'out_inv_ai', question_id: 'ai_need', type: 'Choice', value: '불필요', confidence: 0.9, evidence: [ev('span_inv_1', '재고 실사 결과와 ERP 장부 재고를 자동으로 대사해')] }],
    draft_tasks: [], review_reasons: [], review: { status: 'approved' },
  },
};
function judgmentFor(id, runId) {
  const base = judgments[id];
  if (!base) return null;
  const j = { id: `jdg_${id.slice(4)}`, request_id: id, revision_id: revOf[id], run_id: runId || runOf[id], risk_confirmed: true, risks: [], author: 'code:extractive@1', versions: { config_version: 14, model: 'claude-sonnet-4-5', question_set_version: 'qset-3' }, mode: 'live', questions: null, llm: null, current_draft_version: 1, draft_versions: [], ...structuredClone(base) };
  if (runId === RUN.sap1) { j.classifications = { ...j.classifications, lead_org: 'AI팀' }; j.rule_effects = []; }
  return j;
}
function runsFor(id) {
  if (id === REQ.sap) return { active_run_id: RUN.sap2, runs: [{ id: RUN.sap2, revision_id: REV.sap, status: 'succeeded', versions: { config_version: 14, model: 'claude-sonnet-4-5' }, created_at: ago(415) }, { id: RUN.sap1, revision_id: REV.sap, status: 'succeeded', versions: { config_version: 13, model: 'claude-sonnet-4-5' }, created_at: ago(418) }] };
  return { active_run_id: runOf[id], runs: [{ id: runOf[id], revision_id: revOf[id], status: 'succeeded', versions: { config_version: 14 }, created_at: requestItems.find((r) => r.id === id)?.created_at }] };
}
const progressFor = (id) => ({ request_id: id, run_id: runOf[id], status: 'judgment_saved', final: true, evidence_ready: true, tasks_ready: true,
  steps: ['입력 정리', 'Decision AI 판단', '근거 연결', '업무 분해', '결과 저장'].map((name) => ({ name, status: 'succeeded' })), timings_ms: { received_to_preliminary: 2400, received_to_final: 9800 } });

// ---------------------------------------------------------------- reviews
const reviewRows = [
  { id: 'rvw_dem01a7', request_id: REQ.demand, title: requestTitles[REQ.demand], preview: '병원별 판매량으로 다음 달 수요 예측…', run_id: RUN.demand, revision_id: REV.demand, draft_version: 1, review_version: 1, status: 'pending', reasons: ['Choice confidence 미충족: feasibility/lead_org'], reasons_summary: 'Choice confidence 미충족: feasibility/lead_org', urgency: '일반', required_reviewer_org: 'AI팀', waiting_seconds: 9840, created_at: ago(164) },
  { id: 'rvw_5h1p02b', request_id: REQ.ship, title: requestTitles[REQ.ship], preview: '출하 지시가 ERP에서 물류센터로…', run_id: RUN.ship, revision_id: REV.ship, draft_version: 1, review_version: 1, status: 'pending', reasons: ['필수 검토: urgent'], reasons_summary: '필수 검토: urgent', urgency: '긴급', required_reviewer_org: 'IT팀', waiting_seconds: 2220, created_at: ago(37) },
  { id: 'rvw_r00m03c', request_id: REQ.room, title: requestTitles[REQ.room], preview: '본사 3~7층 회의실 예약 현황…', run_id: RUN.room, revision_id: REV.room, draft_version: 1, review_version: 1, status: 'pending', reasons: ['Choice confidence 미충족: lead_org'], reasons_summary: 'Choice confidence 미충족: lead_org', urgency: '일반', required_reviewer_org: 'IT팀', waiting_seconds: 92400, created_at: days(1, 94) },
];
const approvedRows = [
  { id: 'rvw_5ap00d1', request_id: REQ.sap, title: requestTitles[REQ.sap], run_id: RUN.sap2, revision_id: REV.sap, draft_version: 1, review_version: 2, status: 'approved', reasons: ['Choice confidence 미충족: lead_org'], urgency: '일반', required_reviewer_org: 'IT팀', waiting_seconds: 1500, created_at: ago(410) },
];

// ---------------------------------------------------------------- cases (DecisionCase)
const cases = [
  { id: 'case_lead_0007', field: 'lead_org', ai_value: 'AI팀', corrected_value: 'IT팀', reason: '예측 모델보다 거래처·판매 데이터 정비가 선행돼야 하며, 집계·알림은 IT팀 표준 배치로 처리합니다.', situation: '대리점별 판매 실적 집계와 미달 알림', request_id: 'req_0ld7a1c2e4', status: 'verified', conditions: ['집계', '알림', '판매량'], exceptions: ['신규 모델 개발'], outcome: 'held', outcome_note: 'IT팀 주관으로 2주 내 배포, 재배정 없음', version: 3, owner: '박검토', consulted: 6, followed: 5, created_at: days(41), updated_at: days(12),
    history: [
      { version: 1, action: 'record', status: 'recorded', by: '박검토', at: days(41), conditions: [], exceptions: [], outcome: null, note: '검토 수정 승인에서 기록' },
      { version: 2, action: 'confirm', status: 'confirmed', by: '박검토', at: days(30), conditions: ['집계', '알림', '판매량'], exceptions: ['신규 모델 개발'], outcome: null, note: null },
      { version: 3, action: 'outcome', status: 'verified', by: '이운영', at: days(12), conditions: ['집계', '알림', '판매량'], exceptions: ['신규 모델 개발'], outcome: 'held', outcome_note: 'IT팀 주관으로 2주 내 배포, 재배정 없음', note: '결과 유효' },
    ] },
  { id: 'case_feas_0011', field: 'feasibility', ai_value: '가능', corrected_value: '조건부 가능', reason: '거래처 코드가 영업·물류 시스템에서 서로 달라 매핑표 정리 전에는 예측 정확도를 보장할 수 없습니다.', situation: '병원 거래처별 월간 발주 예측', request_id: 'req_0ld9c3e5a1', status: 'confirmed', conditions: ['거래처', '예측'], exceptions: [], outcome: null, outcome_note: null, version: 2, owner: '김검토', consulted: 3, followed: 2, created_at: days(19), updated_at: days(9),
    history: [
      { version: 1, action: 'record', status: 'recorded', by: '김검토', at: days(19), conditions: [], exceptions: [], outcome: null, note: null },
      { version: 2, action: 'confirm', status: 'confirmed', by: '김검토', at: days(9), conditions: ['거래처', '예측'], exceptions: [], outcome: null, note: null },
    ] },
  { id: 'case_urg_0014', field: 'urgency', ai_value: '일반', corrected_value: '긴급', reason: '당일 마감 출하에 영향을 주는 인터페이스 중단은 금액과 무관하게 긴급으로 처리합니다.', situation: 'WMS 입고 지시 전송 지연', request_id: 'req_0ldb2f7c90', status: 'recorded', conditions: [], exceptions: [], outcome: null, outcome_note: null, version: 1, owner: '최물류', consulted: 1, followed: 1, created_at: days(3), history: [] },
  { id: 'case_ai_0003', field: 'ai_need', ai_value: '필요', corrected_value: '불필요', reason: '규칙 기반 키워드 분류로 충분하다고 판단했으나 이후 오분류가 잦아 폐기합니다.', situation: 'VOC 문의 자동 분류', request_id: 'req_0ld3a8d6b2', status: 'retired', conditions: ['문의', '분류'], exceptions: [], outcome: 'failed', outcome_note: '오분류율 31%로 재작업', version: 4, owner: '정현업', consulted: 4, followed: 1, created_at: days(70), updated_at: days(25), history: [] },
];
const precedent = (c, applicability, keyword, age) => ({ ...c, applicability, matched_keyword: keyword, age_days: age, stale: age > 60 });

function reviewDetail(id) {
  const row = [...reviewRows, ...approvedRows].find((r) => r.id === id);
  if (!row) return null;
  const j = judgmentFor(row.request_id, row.run_id);
  const tasks = j.draft_tasks.map((t, i) => ({ ...t, draft_task_id: t.draft_task_id || `dtk_${i}`, draft_version: 1 }));
  const draft = { draft_version: 1, source: 'ai', created_by: 'ai', created_at: row.created_at, tasks };
  return {
    orgs: [{ id: 'org_ai', name: 'ai' }, { id: 'org_it', name: 'it' }, { id: 'org_biz', name: 'business' }],
    review: row,
    request: { id: row.request_id, title: row.title, request_text: requestTexts[row.request_id], preview: row.preview },
    judgment: { ...j.classifications, rule_effects: j.rule_effects || [] },
    outputs: j.outputs,
    drafts: [draft], original_draft: draft, current_draft: draft,
    history: row.status === 'approved' ? [{ id: 'rdh_1', action: 'approve', actor_id: '김검토', created_at: ago(400), reason: '원안 승인' }] : [],
    final_classifications: { ...j.classifications }, final_draft_version: 1,
    precedents: row.request_id === REQ.demand ? {
      lead_org: { items: [precedent(cases[0], 'applies', '판매량', 41), precedent(cases[3], 'excepted', null, 70)], conflict: false, hidden_unmet: 1 },
      feasibility: { items: [precedent(cases[1], 'applies', '거래처', 19)], conflict: false, hidden_unmet: 0 },
    } : row.request_id === REQ.ship ? { urgency: { items: [precedent(cases[2], 'unconfirmed', null, 3)], conflict: false, hidden_unmet: 0 } } : {},
  };
}

// ---------------------------------------------------------------- tasks
const pred = (id, title, status) => ({ id, title, status });
const tasks = [
  { id: 'tsk_5ap_01', request_id: REQ.sap, title: 'SAP 매출 CSV 적재 파이프라인', method: '일반 기술', lead_org: 'IT팀', collab_orgs: ['현업'], deliverable: '일 1회 적재 배치', predecessors: [], predecessor_tasks: [], successors: [pred('tsk_5ap_02', '월별·사업부별 집계 뷰', '진행')], reason: null, block_reasons: [], can_start: true, start_blockers: [], status: '완료' },
  { id: 'tsk_5ap_02', request_id: REQ.sap, title: '월별·사업부별 집계 뷰', method: '일반 기술', lead_org: 'IT팀', collab_orgs: [], deliverable: '집계 SQL 뷰', predecessors: ['tsk_5ap_01'], predecessor_tasks: [pred('tsk_5ap_01', 'SAP 매출 CSV 적재 파이프라인', '완료')], successors: [pred('tsk_5ap_03', '경영회의 화면 검수', '대기')], reason: null, block_reasons: [], can_start: true, start_blockers: [], status: '진행' },
  { id: 'tsk_5ap_03', request_id: REQ.sap, title: '경영회의 화면 검수', method: '사람', lead_org: '현업', collab_orgs: ['IT팀'], deliverable: '검수 체크리스트', predecessors: ['tsk_5ap_02'], predecessor_tasks: [pred('tsk_5ap_02', '월별·사업부별 집계 뷰', '진행')], successors: [], reason: null, block_reasons: [], can_start: false, start_blockers: ['predecessor_incomplete'], status: '대기' },
  { id: 'tsk_1nv_01', request_id: REQ.inv, title: '실사 데이터 표준 양식 정리', method: '사람', lead_org: '현업', collab_orgs: [], deliverable: '실사 업로드 양식', predecessors: [], predecessor_tasks: [], successors: [pred('tsk_1nv_02', '장부·실사 재고 자동 대사', '막힘')], reason: null, block_reasons: [], can_start: true, start_blockers: [], status: '완료' },
  { id: 'tsk_1nv_02', request_id: REQ.inv, title: '장부·실사 재고 자동 대사', method: '일반 기술', lead_org: 'IT팀', collab_orgs: ['현업'], deliverable: '차이 품목 리포트', predecessors: ['tsk_1nv_01'], predecessor_tasks: [pred('tsk_1nv_01', '실사 데이터 표준 양식 정리', '완료')], successors: [], reason: 'feasibility_unresolved', block_reasons: ['feasibility_unresolved'], can_start: false, start_blockers: ['feasibility_unresolved', 'reason:ERP 재고 조회 권한 승인 대기'], status: '막힘' },
  { id: 'tsk_1nv_03', request_id: REQ.inv, title: '차이 원인 분류 보조 모델 검토', method: 'AI', lead_org: 'AI팀', collab_orgs: ['IT팀'], deliverable: '분류 가능성 메모', predecessors: [], predecessor_tasks: [], successors: [], reason: null, block_reasons: [], can_start: true, start_blockers: [], status: '진행' },
];

// ---------------------------------------------------------------- observe
const t0 = Date.parse(ago(416));
const at = (ms) => new Date(t0 + ms).toISOString();
const flowSteps = [
  { id: 'stp_sap_01', name: '입력 정리', kind: 'code', actor_kind: 'code', s: 0, e: 380 },
  { id: 'stp_sap_02', name: 'Decision AI 판단', kind: 'ai', actor_kind: 'ai', s: 400, e: 6200 },
  { id: 'stp_sap_03', name: '근거 연결', kind: 'code', actor_kind: 'code', s: 6250, e: 7100 },
  { id: 'stp_sap_04', name: '규칙 적용', kind: 'rule', actor_kind: 'rule', s: 7150, e: 7240 },
  { id: 'stp_sap_05', name: '업무 분해', kind: 'ai', actor_kind: 'ai', s: 7300, e: 9300 },
  { id: 'stp_sap_06', name: '결과 저장', kind: 'code', actor_kind: 'code', s: 9350, e: 9800 },
];
function flowFor(runId) {
  const nodes = flowSteps.map((s, i) => ({ id: s.id, name: s.name, kind: s.kind, actor_kind: s.actor_kind, status: 'succeeded', started_at: at(s.s), ended_at: at(s.e), duration_ms: s.e - s.s, attempt: s.id === 'stp_sap_02' ? '2' : undefined, parent_step_id: null, predecessor_ids: i ? [flowSteps[i - 1].id] : [] }));
  nodes.push({ id: 'review:rvw_5ap00d1', name: '사람 검토', kind: 'human', actor_kind: 'human', status: 'succeeded', started_at: at(9900), ended_at: at(1_509_900), duration_ms: 1_500_000 });
  nodes.push({ id: 'stp_sap_07', name: '업무 배정', kind: 'code', actor_kind: 'code', status: 'succeeded', started_at: at(1_510_000), ended_at: at(1_510_400), duration_ms: 400 });
  const edges = nodes.slice(1).map((n, i) => ({ from: nodes[i].id, to: n.id, kind: n.kind === 'human' ? 'review' : 'sequence' }));
  return { request_id: REQ.sap, run_id: runId, live: false, nodes, edges };
}
function playbackFor(runId) {
  const events = flowSteps.flatMap((s) => [{ type: 'step_started', at: at(s.s), step_id: s.id }, { type: 'step_ended', at: at(s.e), step_id: s.id, status: 'succeeded', duration_ms: s.e - s.s }]);
  events.push({ type: 'human_wait_started', at: at(9900), review_id: 'rvw_5ap00d1' }, { type: 'human_wait_ended', at: at(1_509_900), review_id: 'rvw_5ap00d1', duration_ms: 1_500_000 });
  return { request_id: REQ.sap, run_id: runId, live: false, events, reviews: [{ id: 'rvw_5ap00d1', status: 'approved' }], final_result: 'succeeded' };
}
const topology = (id, kind) => kind === 'service'
  ? { request_id: id, kind, services: [{ name: 'Anthropic API', calls: 3, errors: 1 }, { name: 'Neo4j', calls: 41, errors: 0 }, { name: '첨부 파서', calls: 0, errors: 0 }, { name: 'SSE 브로커', calls: 12, errors: 0 }] }
  : { request_id: id, kind, nodes: [{ id, type: 'Request', name: requestTitles[id] || id, status: '배정 완료' }, ...tasks.filter((t) => t.request_id === id).map((t) => ({ id: t.id, type: 'Task', name: t.title, status: t.status })), { id: 'org_it', type: 'Org', name: 'IT팀', status: '주관' }, { id: 'org_biz', type: 'Org', name: '현업', status: '협업' }],
    edges: [{ from: id, to: 'tsk_5ap_01', kind: 'HAS_TASK' }, { from: 'tsk_5ap_01', to: 'tsk_5ap_02', kind: 'PRECEDES' }, { from: 'tsk_5ap_02', to: 'tsk_5ap_03', kind: 'PRECEDES' }, { from: 'tsk_5ap_01', to: 'org_it', kind: 'ASSIGNED_TO', role: 'lead' }, { from: 'tsk_5ap_03', to: 'org_biz', kind: 'ASSIGNED_TO', role: 'lead' }] };
const stepDetail = (id) => { const n = flowFor(RUN.sap2).nodes.find((x) => x.id === id) || flowFor(RUN.sap2).nodes[0]; return { ...n, run_id: RUN.sap2, config_version: 14, error_class: null, versions: { config_version: 14, model: 'claude-sonnet-4-5' }, input_summary: { chars: 128 }, output_summary: { classifications: judgments[REQ.sap].classifications } }; };

// ---------------------------------------------------------------- judgment graph
const gnode = (id, kind, layer, title, summary, extra = {}) => ({ id, kind, layer, title, summary, status: null, actor: null, at: null, version: null, source: null, request_id: REQ.sap, refs: { request_id: REQ.sap }, upstream_count: 1, downstream_count: 1, ...extra });
const graphNodes = [
  gnode('gs_span_1', 'EvidenceSpan', 1, '원문 · 문단 1 문장 1', '“매출 CSV를 월별·사업부별로 집계해”', { source: 'chat', at: ago(416) }),
  gnode('gs_span_2', 'EvidenceSpan', 1, '원문 · 문단 1 문장 3', '“10월 말 경영회의부터 쓰고 싶습니다”', { source: 'chat', at: ago(416) }),
  gnode('gs_mo_lead', 'ModelOutput', 1, 'Decision AI · lead_org', 'AI팀 (확신도 0.62)', { actor: 'claude-sonnet-4-5', at: ago(416) }),
  gnode('gs_mo_urg', 'ModelOutput', 1, 'Decision AI · urgency', '일반 (확신도 0.81)', { actor: 'claude-sonnet-4-5', at: ago(416) }),
  gnode('gs_corr_1', 'Correction', 1, '사람 수정 · lead_org', 'AI팀 → IT팀', { actor: '박검토', at: days(41), request_id: 'req_0ld7a1c2e4' }),
  gnode('gs_corr_2', 'Correction', 1, '사람 수정 · lead_org', 'AI팀 → IT팀', { actor: '김검토', at: days(20), request_id: 'req_0ld9c3e5a1' }),
  gnode('gs_cand_1', 'RuleCandidate', 2, '규칙 후보 · lead_org', '집계·알림 요청은 IT팀 주관', { status: 'approved', actor: 'code:candidate@v1', at: days(18) }),
  gnode('gs_dec_1', 'RuleDecision', 3, '규칙 결정 · approve_with_scope_change', '범위를 판매·집계 키워드로 좁혀 승인', { status: 'approve_with_scope_change', actor: '이규칙', at: days(17) }),
  gnode('gs_rvd_1', 'ReviewDecision', 3, '요청 검토 결정 · approve', '원안 승인', { status: 'approve', actor: '김검토', at: ago(400) }),
  gnode('gs_rv_1', 'RuleVersion', 4, '규칙 버전 R-LEAD_ORG-01@1', 'v1 · 첫 게시 후 되돌림', { status: 'reverted', version: 'R-LEAD_ORG-01@1', refs: { rule_id: 'R-LEAD_ORG-01', rule_version: 'R-LEAD_ORG-01@1' }, at: days(16) }),
  gnode('gs_rv_2', 'RuleVersion', 4, '규칙 버전 R-LEAD_ORG-01@2', 'v2 · 범위 축소 후 운영 중', { status: 'published', version: 'R-LEAD_ORG-01@2', refs: { rule_id: 'R-LEAD_ORG-01', rule_version: 'R-LEAD_ORG-01@2' }, at: days(10) }),
  gnode('gs_val_1', 'ValidationRun', 4, '비교 검증 val_lead_0002', '표본 48건 · 변경 7건 · 부작용 0건', { status: 'completed', actor: '이규칙', at: days(11) }),
  gnode('gs_cfg_14', 'ConfigVersion', 4, 'Config v14', 'R-LEAD_ORG-01@2 게시', { status: 'active', version: '14', actor: '이규칙', at: days(10) }),
  gnode('gs_step_2', 'RunStep', 5, 'Decision AI 판단', '실행 run_5ap2b7e19c · 성공', { status: 'succeeded', version: '{"config_version":14,"model":"claude-sonnet-4-5"}', at: ago(416) }),
  gnode('gs_step_4', 'RunStep', 5, '규칙 적용', 'lead_org AI팀 → IT팀', { status: 'succeeded', version: '{"config_version":14,"rule_version":"R-LEAD_ORG-01@2"}', at: ago(416) }),
];
const gedge = (type, up, down, props) => ({ id: `${type}:${down}->${up}`, type, source: down, target: up, upstream: up, downstream: down, ...(props ? { props } : {}) });
const graphEdges = [
  gedge('CITES', 'gs_span_1', 'gs_mo_lead'), gedge('CITES', 'gs_span_2', 'gs_mo_urg'), gedge('CORRECTS', 'gs_mo_lead', 'gs_corr_1'), gedge('CORRECTS', 'gs_mo_lead', 'gs_corr_2'),
  gedge('SUPPORTED_BY', 'gs_corr_1', 'gs_cand_1'), gedge('SUPPORTED_BY', 'gs_corr_2', 'gs_cand_1'), gedge('DECIDES', 'gs_cand_1', 'gs_dec_1'),
  gedge('DERIVED_FROM', 'gs_dec_1', 'gs_rv_1'), gedge('DERIVED_FROM', 'gs_dec_1', 'gs_rv_2'), gedge('VALIDATES', 'gs_rv_2', 'gs_val_1'), gedge('PUBLISHED_IN', 'gs_rv_2', 'gs_cfg_14'),
  gedge('USED_OUTPUT', 'gs_mo_lead', 'gs_step_2'), gedge('USED_OUTPUT', 'gs_mo_urg', 'gs_step_2'), gedge('APPLIED', 'gs_rv_2', 'gs_step_4', { outcome: 'used' }), gedge('RECORDED', 'gs_step_2', 'gs_rvd_1'),
];
const graphLayers = [
  { layer: 1, name: '근거', desc: '문서 구간 · 모델 반환값 · 사람 수정' }, { layer: 2, name: '가설', desc: '근거에서 나온 규칙 후보' }, { layer: 3, name: '판단', desc: '요청 검토 결정 · 후보 승인·기각' },
  { layer: 4, name: '적용', desc: '규칙·Config 버전 · 검증 · 상태' }, { layer: 5, name: '업무 단계', desc: '판단과 규칙을 실제로 쓴 실행 단계' },
].map((l) => ({ ...l, count: graphNodes.filter((n) => n.layer === l.layer).length }));
const judgmentGraph = { nodes: graphNodes, edges: graphEdges, layers: graphLayers, truncated: false, node_count: graphNodes.length, edge_count: graphEdges.length, criteria: {} };
function nodeDetail(id) {
  const n = graphNodes.find((x) => x.id === id) || graphNodes[0];
  const ref = (nid) => { const x = graphNodes.find((g) => g.id === nid); return { id: x.id, kind: x.kind, layer: x.layer, title: x.title }; };
  return { ...n, upstream: graphEdges.filter((e) => e.downstream === n.id).map((e) => ref(e.upstream)), downstream: graphEdges.filter((e) => e.upstream === n.id).map((e) => ref(e.downstream)), edges: graphEdges.filter((e) => e.upstream === n.id || e.downstream === n.id), can_read_source: true, source_link: null };
}

// ---------------------------------------------------------------- learning
const ruleBody = (version, scope) => ({ schema: 'rule-v1', rule_id: 'R-LEAD_ORG-01', version, effect: 'rule', target: 'lead_org', scope, action: { set: 'IT팀' }, candidate_id: 'cand_lead_01', decision_id: 'rdec_lead_01' });
const scopeV1 = { all: [{ field: 'ai_need', op: 'eq', value: '불필요' }] };
const scopeV2 = { all: [{ field: 'ai_need', op: 'eq', value: '불필요' }, { text: { contains_any: ['집계', '판매량', '알림'] } }] };
const candidateRows = [
  { id: 'cand_lead_01', field: 'lead_org', status: 'approved', source: 'ai', author: 'code:candidate@v1', support_count: 7, counter_count: 1, created_at: days(18), rationale: '집계·알림 요청에서 AI팀 원안이 IT팀으로 7회 수정됨',
    proposed_body: JSON.stringify(ruleBody(1, scopeV2)), uncertainty: JSON.stringify({ support_count: 7, counter_count: 1, minimum_support: 3, organization_count: 3, single_organization_bias: false }) },
  { id: 'cand_urg_02', field: 'urgency', status: '제안', source: 'ai', author: 'code:candidate@v1', support_count: 4, counter_count: 0, created_at: days(2), rationale: '당일 마감·출하 키워드에서 일반 → 긴급 수정 4회',
    proposed_body: JSON.stringify({ rule_id: '', version: 1, effect: 'rule', target: 'urgency', scope: { all: [{ text: { contains_any: ['마감', '출하', '중단'] } }] }, action: { set: '긴급' } }), uncertainty: JSON.stringify({ support_count: 4, counter_count: 0, minimum_support: 3, organization_count: 2 }) },
  { id: 'cand_feas_03', field: 'feasibility', status: '자료 부족', source: 'human', author: '김검토', support_count: 1, counter_count: 0, created_at: days(6), rationale: '거래처 마스터 미정비 요청은 조건부 가능',
    proposed_body: JSON.stringify({ rule_id: '', version: 1, effect: 'context', target: 'feasibility', scope: { all: [{ text: { contains_any: ['거래처'] } }] }, action: { set: '조건부 가능' }, context_text: '거래처 코드 정합성이 확인되지 않으면 조건부 가능으로 봅니다.' }), uncertainty: JSON.stringify({ support_count: 1, counter_count: 0, minimum_support: 3, single_organization_bias: true }) },
  { id: 'cand_ai_04', field: 'ai_need', status: 'rejected', source: 'ai', author: 'code:candidate@v1', support_count: 3, counter_count: 3, created_at: days(28), rationale: '문의 분류 요청의 AI 필요성 수정이 엇갈림',
    proposed_body: JSON.stringify({ rule_id: '', version: 1, effect: 'rule', target: 'ai_need', scope: { all: [{ text: { contains_any: ['문의', '분류'] } }] }, action: { set: '불필요' } }), uncertainty: JSON.stringify({ support_count: 3, counter_count: 3, minimum_support: 3 }) },
];
const corrections = [
  { id: 'cor_0101', request_id: 'req_0ld7a1c2e4', run_id: 'run_0ld7a1', revision_id: 'rev_0ld7a1', field: 'lead_org', ai_value: 'AI팀', corrected_value: 'IT팀', reason: '집계·알림은 IT 표준 배치', corrected_by: '박검토', corrected_at: days(41), config_version: 9 },
  { id: 'cor_0117', request_id: 'req_0ld9c3e5a1', run_id: 'run_0ld9c3', revision_id: 'rev_0ld9c3', field: 'lead_org', ai_value: 'AI팀', corrected_value: 'IT팀', reason: '판매량 집계 후 알림', corrected_by: '김검토', corrected_at: days(20), config_version: 11 },
  { id: 'cor_0124', request_id: 'req_0ldc4a2e18', run_id: 'run_0ldc4a', revision_id: 'rev_0ldc4a', field: 'lead_org', ai_value: 'AI팀', corrected_value: 'IT팀', reason: '대리점 실적 집계', corrected_by: '최물류', corrected_at: days(19), config_version: 11 },
  { id: 'cor_0130', request_id: 'req_0ldb2f7c90', run_id: 'run_0ldb2f', revision_id: 'rev_0ldb2f', field: 'urgency', ai_value: '일반', corrected_value: '긴급', reason: '당일 마감 출하 영향', corrected_by: '최물류', corrected_at: days(3), config_version: 14 },
  { id: 'cor_0131', request_id: 'req_0ld9c3e5a1', run_id: 'run_0ld9c3', revision_id: 'rev_0ld9c3', field: 'feasibility', ai_value: '가능', corrected_value: '조건부 가능', reason: '거래처 코드 불일치', corrected_by: '김검토', corrected_at: days(20), config_version: 11 },
];
function candidateDetail(id) {
  const row = candidateRows.find((c) => c.id === id) || candidateRows[0];
  const examples = row.id === 'cand_lead_01'
    ? [...corrections.filter((c) => c.field === 'lead_org').map((c) => ({ role: 'support', case: c })), { role: 'counter', case: { id: 'rdec_0090', request_id: 'req_0ld2e9a7f3', run_id: 'run_0ld2e9', action: 'approve', actor_id: '정현업', created_at: days(33) } }]
    : corrections.filter((c) => c.field === row.field).map((c) => ({ role: 'support', case: c }));
  return { ...row, examples };
}
const ruleDetail = { rule_id: 'R-LEAD_ORG-01', versions: [
  { version: 1, status: 'reverted', body: ruleBody(1, scopeV1), config_versions: [12], application_count: 9 },
  { version: 2, status: 'published', body: ruleBody(2, scopeV2), config_versions: [14], application_count: 23 },
] };
const validation = { id: 'val_lead_0002', rule_version: 'R-LEAD_ORG-01@2', base_config_version: 13, candidate_config_version: 'shadow-13+R-LEAD_ORG-01@2', from: days(41), to: days(11), scope_filter: null,
  sample_count: 48, labeled_count: 31, changed_count: 7, changes_by_value: { 'lead_org:IT팀': 7 }, human_correction_needed_base: 9, human_correction_needed_candidate: 3,
  review_transition_base: 14, review_transition_candidate: 11, failures: [], failure_count: 0, side_effects: 0, status: 'completed', max_calls: 20, calls: 17, usage: { input_tokens: 182340, output_tokens: 20811 } };
const metrics = (sample, labeled, ch, corr, rev, fail, p50, p95) => ({ labeled_count: labeled, sample_count: sample, classification_changes: Math.round(sample * ch), corrections: Math.round(sample * corr), review_transitions: Math.round(sample * rev), failures: Math.round(sample * fail),
  latency_sample_count: sample, latency_p50_ms: p50, latency_p95_ms: p95, classification_change_rate: ch, correction_rate: corr, review_transition_rate: rev, failure_rate: fail });
const ruleEffects = { rule_id: 'R-LEAD_ORG-01', active_config_version: 14, published_at: days(10), window_days: 7, minimum_sample: 20, sample_count: 64,
  before_after: { before: metrics(29, 22, 0.0, 0.31, 0.45, 0.03, 6100, 13200), after: metrics(35, 26, 0.2, 0.11, 0.37, 0.0, 6300, 12800), before_from: days(17), before_to: days(10), after_from: days(10), after_to: days(3) },
  groups: { used: metrics(23, 18, 0.3, 0.09, 0.3, 0.0, 6400, 12900), out_of_scope: metrics(41, 30, 0.0, 0.24, 0.41, 0.02, 6050, 13100) }, effect: 'improved', shadow_runs_excluded: 2, slo_included: false, comparison_conditions: 'live runs / APPLIED vs out_of_scope / shadow excluded' };

// ---------------------------------------------------------------- policy
const policyConfig = {
  schema_version: 'policy-schema-v1', auto_assign: false,
  choice_confidence_thresholds: { ai_need: 0.8, feasibility: 0.8, urgency: 0.75, lead_org: 0.8 },
  noul_probability_thresholds: { evidence: 0.6, catalog: 0.6 }, noul_uncertain_band: [0.35, 0.65], risk_clear_max: 0.2,
  reviewer_groups: { clinical_safety: ['grp_medical'], regulatory: ['grp_ra'], urgent: ['grp_it_oncall'] },
  limits: { text_chars: 20000, attachments: 5, file_bytes: 10485760, total_bytes: 26214400, pdf_pages: 50 },
  evidence_noul_threshold: 0.6, catalog_noul_threshold: 0.6, feature_flags: { progressive_results: true, decision_cases: true },
  rules: [{ rule_id: 'R-LEAD_ORG-01', version: 2, effect: 'rule', target: 'lead_org', scope: scopeV2, action: { set: 'IT팀' }, candidate_id: 'cand_lead_01', decision_id: 'rdec_lead_01' }],
  learning: { min_support: 3, min_effect_sample: 20, shadow_max_calls: 20, effect_window_days: 7 },
  masking: { enabled: true, categories: ['registration', 'business', 'card', 'email', 'phone', 'account', 'ip', 'url_query', 'api_key'] },
  llm: { provider: 'anthropic', model: 'claude-sonnet-4-5', features: { summary: true, task_description: true, questions: false, rule_explanation: true }, timeout_seconds: 15, step_budget_seconds: 20, max_output_tokens: 2000 },
  retention: { event_days: 90, idempotency_days: 30, session_grace_days: 7, login_attempt_window_seconds: 900, journal_days: 90, metrics_days: 90, batch_size: 500 },
};
const policyVersions = [
  { version: 14, status: 'active', reason: 'R-LEAD_ORG-01 v2 게시 (범위: 집계·판매량·알림)', created_by: '이규칙', created_at: days(10) },
  { version: 13, status: 'superseded', reason: 'R-LEAD_ORG-01 v1 되돌리기 — 범위 과다', created_by: '이규칙', created_at: days(14) },
  { version: 12, status: 'superseded', reason: 'R-LEAD_ORG-01 v1 게시', created_by: '이규칙', created_at: days(16) },
  { version: 11, status: 'superseded', reason: '긴급도 선택 확신도 0.8 → 0.75 조정', created_by: '한정책', created_at: days(27) },
  { version: 10, status: 'superseded', reason: '규제 검토 그룹 추가', created_by: '한정책', created_at: days(45) },
];
const policyDiffs = {
  14: { rules: { before: [], after: [{ rule_id: 'R-LEAD_ORG-01', version: 2 }] } },
  13: { rules: { before: [{ rule_id: 'R-LEAD_ORG-01', version: 1 }], after: [] } },
  12: { rules: { before: [], after: [{ rule_id: 'R-LEAD_ORG-01', version: 1 }] } },
  11: { choice_confidence_thresholds: { before: { ai_need: 0.8, feasibility: 0.8, urgency: 0.8, lead_org: 0.8 }, after: { ai_need: 0.8, feasibility: 0.8, urgency: 0.75, lead_org: 0.8 } } },
  10: { reviewer_groups: { before: { clinical_safety: ['grp_medical'], urgent: ['grp_it_oncall'] }, after: { clinical_safety: ['grp_medical'], regulatory: ['grp_ra'], urgent: ['grp_it_oncall'] } } },
};
const providers = [
  { provider: 'anthropic', key_configured: true, sdk_available: true, default_model: 'claude-sonnet-4-5', connected: true },
  { provider: 'openai', key_configured: false, sdk_available: true, default_model: 'gpt-4.1' },
  { provider: 'google', key_configured: false, sdk_available: false, default_model: 'gemini-2.5-pro' },
];

// ---------------------------------------------------------------- monitoring
const collection = { complete: true, issues: [], has_collected_events: true, damaged_lines_or_truncations: 0, incomplete_intervals: [], last_collected_at: ago(1), limitations: [] };
const failureCauses = {
  external_model: [{ request_id: REQ.room, run_id: RUN.room, attempt_id: 'att_9f21', error_class: 'RateLimitError', ts: days(1, 90) }, { request_id: REQ.sap, run_id: RUN.sap1, attempt_id: 'att_8c04', error_class: 'APITimeoutError', ts: ago(417) }],
  parsing: [{ request_id: 'req_0lde7b3a52', run_id: 'run_0lde7b', attempt_id: 'att_7a11', error_class: 'DocxParseError', ts: days(5) }],
  sse: [{ attempt_id: 'att_6d90', error_class: 'ClientDisconnected', ts: days(2) }],
};
function monitoringSummary(url) {
  return {
    from: url.searchParams.get('from') || days(30), to: url.searchParams.get('to') || ago(0), filters: { org: null, status: null, version: null },
    availability: { valid_calls: 4210, successful_calls: 4208, failed_calls: 2, pending_calls: 0, unknown_validity: 0, ratio: 0.99952 },
    judgment: { eligible_requests: 1180, within_120s: 1161, failed_120s: 19, pending_120s: 0, ratio: 0.9839, late_recoveries: 4, failed_runs: 7 },
    requests: { received: 1184, failed_before_id: 3 }, cancellations: 12, shadow_runs: 48,
    business: { request_denominator: 1184, org_unconfirmed: 41, auto_assignment_count: 702, review_completed_count: 455 },
    latency_ms: { intake_p95: 640, text_first_p95: 11800, attachment_first_p95: 38400, sse_deliver_p95: 220, revision_p95: 9700, step_p95: 7400 },
    steps: { intake: { count: 1187, p50_ms: 210, p95_ms: 640 }, text_first: { count: 1012, p50_ms: 6200, p95_ms: 11800 }, attachment_first: { count: 168, p50_ms: 21500, p95_ms: 38400 },
      sse_deliver: { count: 9340, p50_ms: 45, p95_ms: 220 }, revision: { count: 96, p50_ms: 5800, p95_ms: 9700 }, step: { count: 7120, p50_ms: 900, p95_ms: 7400 } },
    review_wait_ms: { p50: 2_640_000, p95: 30_240_000, longest: 92_400_000, unresolved: 3, source_status: 'ok' },
    supplement_wait_ms: { p50: 5_400_000, p95: 61_200_000, unresolved: 2 },
    failures: failureCauses, collection, unscoped_events: 2,
  };
}
const slo = { window_start: days(30), window_end: ago(0), verified: true, reason: null,
  availability: { target: 0.999, total: 4210, failures: 2, remaining_failures: 2.21, burn_rate_1h: 0.4, verified: true },
  first_judgment: { target: 0.99, total: 1180, failures: 19, remaining_failures: -7.2, burn_rate_1h: 2.6, verified: true }, collection };
const alerts = { alerts: [
  { id: 'alr_0031', kind: 'slo_burn', title: '최초 판단 저장 신뢰성 목표 미달', message: '최근 1시간 소진율 2.6× — 외부 모델 시간초과가 주요 원인입니다.', created_at: ago(42), severity: 'warning' },
  { id: 'alr_0030', kind: 'worker_stopped', message: 'judgment-worker-2가 3분간 하트비트를 보내지 않아 재시작했습니다.', created_at: days(1, 300), severity: 'info' },
] };

// ---------------------------------------------------------------- evaluation
const evalCandidates = [
  { id: 'eval-t-0142', text: requestTexts[REQ.demand], rationale: '예측 모델이 핵심이지만 거래처 마스터 정비가 선행 조건이라 조건부 가능으로 제안합니다.',
    proposed_labels: { ai_need: '필요', feasibility: '조건부 가능', urgency: '일반', team_set: ['AI팀', 'IT팀', '현업'], risk_areas: [] },
    my_labels: undefined, consensus: 'consensus_required',
    labels: [
      { user_id: 'usr_park', status: 'confirmed', labels: { ai_need: '필요', feasibility: '조건부 가능', urgency: '일반', team_set: ['AI팀', 'IT팀'], risk_areas: [] }, created_at: days(2, 120) },
      { user_id: 'usr_lee', status: 'confirmed', labels: { ai_need: '필요', feasibility: '가능', urgency: '일반', team_set: ['AI팀', 'IT팀', '현업'], risk_areas: [] }, created_at: days(1, 600) },
    ] },
  { id: 'eval-t-0143', text: requestTexts[REQ.ship], rationale: '당일 마감 물량 영향으로 긴급.', proposed_labels: { ai_need: '불필요', feasibility: '가능', urgency: '긴급', team_set: ['IT팀', '현업'], risk_areas: [] }, consensus: 'single_label',
    labels: [{ user_id: 'usr_park', status: 'confirmed', labels: { ai_need: '불필요', feasibility: '가능', urgency: '긴급', team_set: ['IT팀', '현업'], risk_areas: [] }, created_at: days(1, 60) }] },
  { id: 'eval-t-0144', text: requestTexts[REQ.room], rationale: '정형 데이터 시각화.', proposed_labels: { ai_need: '불필요', feasibility: '가능', urgency: '일반', team_set: ['IT팀'], risk_areas: [] }, consensus: 'unlabeled', labels: [] },
];
const evalProgress = { total: 120, confirmed: 74, deferred: 9, remaining: 37, percent: 62 };

// ---------------------------------------------------------------- router
const json = (body, status = 200) => ({ status, contentType: 'application/json; charset=utf-8', body: JSON.stringify(body) });
const notFound = (msg = 'Not found') => json({ detail: { code: 'NOT_FOUND', message: msg } }, 404);
const enc = (s) => decodeURIComponent(s);

/** Ordered [method, regex, handler(match, url, request)] table. First match wins. */
function routes(role) {
  return [
    ['GET', /^\/api\/auth\/me$/, () => role === 'anonymous' ? json({ detail: 'Not authenticated' }, 401) : json({ ...USER, roles: role && role !== 'all' ? [role] : ALL_ROLES })],
    ['POST', /^\/api\/auth\/(login|logout)$/, () => json({ ok: true })],
    ['GET', /^\/api\/events\/snapshot$/, (_m, url) => { const id = url.searchParams.get('request_id') || ''; return json({ request_id: id, status: statusOf(id), active_run_id: runOf[id] || null, latest_seq: 1042 }); }],
    ['GET', /^\/api\/events\/stream$/, () => ({ status: 200, contentType: 'text/event-stream', headers: { 'cache-control': 'no-cache' }, body: 'retry: 600000\n: keep-alive\n\n' })],

    ['GET', /^\/api\/requests$/, () => json({ items: requestItems })],
    ['GET', /^\/api\/requests\/([^/]+)$/, (m) => { const id = enc(m[1]); return requestTexts[id] ? json(requestDetail(id)) : notFound('Request not found'); }],
    ['GET', /^\/api\/requests\/([^/]+)\/judgment$/, (m, url) => { const j = judgmentFor(enc(m[1]), url.searchParams.get('run_id') || undefined); return j ? json(j) : notFound('Judgment not found'); }],
    ['GET', /^\/api\/requests\/([^/]+)\/runs$/, (m) => json(runsFor(enc(m[1])))],
    ['GET', /^\/api\/requests\/([^/]+)\/progress$/, (m) => json(progressFor(enc(m[1])))],
    ['GET', /^\/api\/requests\/([^/]+)\/corrections$/, (m) => json({ corrections: enc(m[1]) === REQ.sap ? [{ id: 'cor_5ap_1', request_id: REQ.sap, run_id: RUN.sap2, revision_id: REV.sap, field: 'lead_org', ai_value: 'AI팀', corrected_value: 'IT팀', corrected_by: '김검토', corrected_at: ago(400), config_version: 14 }] : [] })],
    ['GET', /^\/api\/requests\/([^/]+)\/evidence\/([^/]+)$/, (m) => { const id = enc(m[1]); const span = enc(m[2]); const out = (judgments[id]?.outputs || []).flatMap((o) => o.evidence).find((e) => e.id === span); return json(out || ev(span, requestTexts[id]?.slice(0, 40) || '')); }],
    ['GET', /^\/api\/requests\/([^/]+)\/revisions\/([^/]+)\/document$/, (m, url) => { const id = enc(m[1]); const text = requestTexts[id] || ''; const sentences = text.split(/(?<=[.다요])\s+/); let pos = 0;
      return json({ request_id: id, revision: 1, revision_id: revOf[id] || enc(m[2]), source: url.searchParams.get('source') || 'chat', kind: 'chat', filename: null, can_read_source: true,
        units: sentences.map((s, i) => { const u = { unit_id: (judgments[id]?.outputs || []).flatMap((o) => o.evidence).find((e) => e.location.sentence === i)?.id || `unit_${i}`, order: i, location: { paragraph: 0, sentence: i }, char_start: pos, char_end: pos + s.length, text: s }; pos += s.length + 1; return u; }) }); }],
    ['POST', /^\/api\/requests(\/.*)?$/, () => json({ request_id: REQ.sap, run_id: RUN.sap2, job_id: 'job_1', revision_id: REV.sap, status: 'received' }, 202)],

    ['GET', /^\/api\/reviews$/, (_m, url) => { const s = url.searchParams.get('status') || 'pending'; return json({ reviews: s === 'pending' ? reviewRows : s === 'approved' ? approvedRows : [] }); }],
    ['GET', /^\/api\/reviews\/([^/]+)$/, (m) => { const d = reviewDetail(enc(m[1])); return d ? json(d) : notFound('Review not found'); }],
    ['POST', /^\/api\/reviews\/([^/]+)\/decision$/, () => json({ status: 'approved' })],

    ['GET', /^\/api\/tasks$/, (_m, url) => { const p = url.searchParams; return json({ tasks: tasks.filter((t) => (!p.get('org') || t.lead_org === p.get('org') || t.collab_orgs.includes(p.get('org'))) && (!p.get('status') || t.status === p.get('status')) && (!p.get('method') || t.method === p.get('method'))) }); }],
    ['GET', /^\/api\/tasks\/([^/]+)$/, (m) => { const t = tasks.find((x) => x.id === enc(m[1])); return t ? json({ task: t }) : notFound(); }],
    ['POST', /^\/api\/tasks\/([^/]+)\/transition$/, () => json({ ok: true })],

    ['GET', /^\/api\/observe\/runs\/([^/]+)\/flow$/, (m) => json(flowFor(enc(m[1])))],
    ['GET', /^\/api\/observe\/runs\/([^/]+)\/playback$/, (m) => json(playbackFor(enc(m[1])))],
    ['GET', /^\/api\/observe\/requests\/([^/]+)\/topology$/, (m, url) => json(topology(enc(m[1]), url.searchParams.get('kind') || 'business'))],
    ['GET', /^\/api\/observe\/steps\/([^/]+)$/, (m) => json(stepDetail(enc(m[1])))],

    ['GET', /^\/api\/graph\/judgment$/, () => json(judgmentGraph)],
    ['GET', /^\/api\/graph\/judgment\/path$/, (_m, url) => { const id = url.searchParams.get('node_id'); return json({ origin: { id, kind: graphNodes.find((n) => n.id === id)?.kind || 'RunStep' }, paths: [], nodes: [], edges: [], upstream_ids: [], downstream_ids: [], truncated: false }); }],
    ['GET', /^\/api\/graph\/judgment\/nodes\/([^/]+)$/, (m) => json(nodeDetail(enc(m[1])))],

    ['GET', /^\/api\/cases$/, (_m, url) => { const s = url.searchParams.get('status'); return json({ cases: s ? cases.filter((c) => c.status === s) : cases }); }],
    ['POST', /^\/api\/cases\/([^/]+)\/\w+$/, (m) => json(cases.find((c) => c.id === enc(m[1])) || cases[0])],

    ['GET', /^\/api\/learning\/orgs$/, () => json({ orgs: [{ id: 'org_ai', name: 'ai' }, { id: 'org_it', name: 'it' }, { id: 'org_biz', name: 'business' }] })],
    ['GET', /^\/api\/learning\/candidates$/, () => json({ candidates: candidateRows })],
    ['GET', /^\/api\/learning\/candidates\/([^/]+)$/, (m) => json(candidateDetail(enc(m[1])))],
    ['GET', /^\/api\/learning\/corrections$/, () => json({ corrections })],
    ['GET', /^\/api\/learning\/rules$/, () => json({ rules: [{ rule_id: 'R-LEAD_ORG-01', latest_version: 2, version_count: 2 }] })],
    ['GET', /^\/api\/learning\/rules\/([^/]+)$/, () => json(ruleDetail)],
    ['GET', /^\/api\/learning\/rules\/([^/]+)\/versions\/(\d+)\/validations$/, (m) => json({ validations: m[2] === '2' ? [validation] : [] })],
    ['GET', /^\/api\/learning\/validations\/([^/]+)$/, () => json(validation)],
    ['GET', /^\/api\/learning\/rules\/([^/]+)\/effects$/, () => json(ruleEffects)],
    ['POST', /^\/api\/learning\/candidates\/([^/]+)\/explanation$/, (m) => json({ candidate_id: enc(m[1]), explanation: '판매·집계 요청에서 AI팀 원안이 IT팀으로 반복 수정되어, 해당 범위에서는 IT팀 주관을 제안합니다.', author: 'llm:anthropic/claude-sonnet-4-5' })],
    ['POST', /^\/api\/learning\//, () => json({ ok: true })],

    ['GET', /^\/api\/policy\/active$/, () => json({ version: 14, config: policyConfig })],
    ['GET', /^\/api\/policy\/versions$/, () => json({ versions: policyVersions })],
    ['GET', /^\/api\/policy\/versions\/(\d+)$/, (m) => { const v = policyVersions.find((x) => x.version === Number(m[1])); return v ? json({ ...v, config: policyConfig, diff: policyDiffs[v.version] || {} }) : notFound(); }],
    ['POST', /^\/api\/policy\/validate$/, () => json({ valid: true, config: policyConfig, errors: [] })],

    ['GET', /^\/api\/assist\/providers$/, () => json({ providers })],
    ['GET', /^\/api\/assist\/providers\/(\w+)\/models$/, (m) => json({ provider: m[1], source: 'api', models: m[1] === 'anthropic' ? [{ id: 'claude-sonnet-4-5', label: 'Claude Sonnet 4.5' }, { id: 'claude-haiku-4-5', label: 'Claude Haiku 4.5' }, { id: 'claude-opus-4-1', label: 'Claude Opus 4.1' }] : [], error_code: null })],
    ['GET', /^\/api\/assist\/chatgpt\/status$/, () => json({ connected: false, email: null, plan_usage_granted: false, expires_at: null, client_registered: false, connected_by: null, connected_tenant: null, error_code: null })],

    ['GET', /^\/api\/monitoring\/summary$/, (_m, url) => json(monitoringSummary(url))],
    ['GET', /^\/api\/monitoring\/slo$/, () => json(slo)],
    ['GET', /^\/api\/monitoring\/failures$/, () => json({ causes: failureCauses, unscoped_events: 2 })],
    ['GET', /^\/api\/monitoring\/alerts$/, () => json(alerts)],
    ['GET', /^\/api\/monitoring\/collection-status$/, () => json(collection)],

    ['GET', /^\/api\/evaluation\/candidates$/, (_m, url) => json({ candidates: url.searchParams.get('split') === 'final' ? evalCandidates.slice(1).map((c) => ({ ...c, proposed_labels: undefined, rationale: undefined })) : evalCandidates, progress: evalProgress })],
    ['PUT', /^\/api\/evaluation\//, () => json({ ok: true })],
    ['POST', /^\/api\/evaluation\//, () => json({ ok: true })],
  ];
}

/** Stub EventSource: opens immediately and stays open (no events), so pages show "실시간 연결됨" instead of reconnect noise. */
const EVENT_SOURCE_STUB = `(() => {
  class StubEventSource extends EventTarget {
    constructor(url, init) { super(); this.url = String(url); this.withCredentials = !!(init && init.withCredentials); this.readyState = 0; this.onopen = null; this.onmessage = null; this.onerror = null;
      setTimeout(() => { if (this.readyState === 2) return; this.readyState = 1; const e = new Event('open'); this.dispatchEvent(e); if (typeof this.onopen === 'function') this.onopen(e); }, 30); }
    close() { this.readyState = 2; }
  }
  StubEventSource.CONNECTING = 0; StubEventSource.OPEN = 1; StubEventSource.CLOSED = 2;
  window.EventSource = StubEventSource;
})();`;

/**
 * @param {import('playwright').Page} page
 * @param {{ role?: 'all'|'anonymous'|string, log?: (msg: string) => void }} [options]
 * role 'all' (default) = every role; 'anonymous' = /api/auth/me → 401 (login page); any other string = that single role.
 * Returns { unknown: string[] } collecting unmatched API paths.
 */
export async function routeApi(page, { role = 'all', log = (m) => console.log(m) } = {}) {
  const table = routes(role);
  const unknown = [];
  await page.addInitScript(EVENT_SOURCE_STUB);
  // Predicate, not the '**/api/**' glob: the glob would also swallow Vite module URLs like /src/api/client.ts.
  await page.route((u) => u.pathname.startsWith('/api/'), async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const method = request.method();
    for (const [m, re, handler] of table) {
      if (m !== method) continue;
      const match = re.exec(url.pathname);
      if (!match) continue;
      try { return await route.fulfill(handler(match, url, request)); }
      catch (error) { log(`[fixtures] handler error ${method} ${url.pathname}: ${error.message}`); return route.fulfill(json({ detail: String(error) }, 500)); }
    }
    const key = `${method} ${url.pathname}${url.search}`;
    unknown.push(key);
    log(`[fixtures] UNMOCKED ${key} → 200 {}`);
    return route.fulfill(json({}));
  });
  return { unknown };
}

export const FIXTURE_IDS = { REQ, RUN, REV, firstReview: reviewRows[0].id, learningCandidate: 'cand_lead_01' };
