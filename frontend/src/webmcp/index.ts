import { apiFetch } from '../api/client';

type RequestRow = { id?: unknown; status?: unknown };
type RequestDetail = { request?: { id?: unknown; status?: unknown }; latest_judgment_summary?: unknown };
type Judgment = { summary?: unknown; classifications?: unknown };
type Flow = { request_id?: unknown; run_id?: unknown; nodes?: Array<{ id?: unknown; kind?: unknown; status?: unknown }> };
type WebMcpTool = { name: string; title: string; description: string; inputSchema: Record<string, unknown>; annotations: { readOnlyHint: true }; execute: (input: unknown) => Promise<unknown> };
type ModelContext = { registerTool: (tool: WebMcpTool, options?: { signal?: AbortSignal }) => Promise<void> };

const schemas = {
  search_requests: { type: 'object', properties: { query: { type: 'string', maxLength: 120 }, status: { type: 'string', maxLength: 40 }, limit: { type: 'integer', minimum: 1, maximum: 100 } }, additionalProperties: false },
  get_request: { type: 'object', properties: { request_id: { type: 'string', minLength: 1, maxLength: 128 } }, required: ['request_id'], additionalProperties: false },
  get_trace: { type: 'object', properties: { run_id: { type: 'string', minLength: 1, maxLength: 128 } }, required: ['run_id'], additionalProperties: false },
};

function objectInput(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('입력은 객체여야 합니다.');
  return value as Record<string, unknown>;
}
function assertKeys(input: Record<string, unknown>, allowed: string[]) {
  if (Object.keys(input).some((key) => !allowed.includes(key))) throw new Error('지원하지 않는 입력 항목이 있습니다.');
}
function boundedString(input: Record<string, unknown>, name: string, required = false): string | undefined {
  const value = input[name];
  if (value === undefined && !required) return undefined;
  const maxLength = name === 'query' ? 120 : name === 'status' ? 40 : 128;
  if (typeof value !== 'string' || value.length < (required ? 1 : 0) || value.length > maxLength) throw new Error(`${name} 입력이 올바르지 않습니다.`);
  return value;
}
function requestSummary(row: RequestRow) { return { id: String(row.id ?? ''), status: String(row.status ?? 'unknown') }; }
function safeError(error: unknown): Error {
  const candidate = error as { status?: number; code?: string; message?: string };
  return new Error(`API_ERROR ${candidate?.status || 0} ${candidate?.code || 'REQUEST_FAILED'}: ${candidate?.message || '요청을 처리하지 못했습니다.'}`);
}

export function createWebMcpTools(): WebMcpTool[] {
  return [
    { name: 'search_requests', title: '요청 검색', description: '로그인한 사용자가 접근할 수 있는 요청을 상태 또는 ID로 검색합니다. 원문은 반환하지 않습니다.', inputSchema: schemas.search_requests, annotations: { readOnlyHint: true }, execute: async (value) => {
      try {
        const input = objectInput(value); assertKeys(input, ['query', 'status', 'limit']); const query = boundedString(input, 'query'); const status = boundedString(input, 'status');
        const rawLimit = input.limit ?? 20;
        if (!Number.isInteger(rawLimit) || Number(rawLimit) < 1 || Number(rawLimit) > 100) throw new Error('limit 입력이 올바르지 않습니다.');
        const params = new URLSearchParams({ limit: String(rawLimit) }); if (status) params.set('status', status);
        const result = await apiFetch<{ items: RequestRow[] }>(`/api/requests?${params}`);
        const items = (result.items || []).map(requestSummary).filter((item) => !query || `${item.id} ${item.status}`.toLowerCase().includes(query.toLowerCase())).slice(0, Number(rawLimit));
        return { items };
      } catch (error) { if (error instanceof Error) throw error; throw safeError(error); }
    } },
    { name: 'get_request', title: '요청 상세 조회', description: '접근 가능한 요청의 ID, 상태, 판단 요약만 조회합니다. 원문은 반환하지 않습니다.', inputSchema: schemas.get_request, annotations: { readOnlyHint: true }, execute: async (value) => {
      try {
        const input = objectInput(value); assertKeys(input, ['request_id']); const id = boundedString(input, 'request_id', true)!;
        const detail = await apiFetch<RequestDetail>(`/api/requests/${encodeURIComponent(id)}`);
        let judgment: Judgment | null = null;
        try { judgment = await apiFetch<Judgment>(`/api/requests/${encodeURIComponent(id)}/judgment`); } catch { /* Judgment may not exist yet; detail access is still valid. */ }
        const summary = judgment?.summary ?? detail.latest_judgment_summary;
        return { id: String(detail.request?.id ?? id), status: String(detail.request?.status ?? 'unknown'), judgment_summary: typeof summary === 'string' ? summary.slice(0, 500) : summary && typeof summary === 'object' && 'text' in summary ? String((summary as { text?: unknown }).text ?? '').slice(0, 500) : null };
      } catch (error) { if (error instanceof Error) throw error; throw safeError(error); }
    } },
    { name: 'get_trace', title: '실행 Trace 조회', description: '접근 가능한 실행 Trace의 단계 ID, 종류, 상태만 조회합니다. 원문은 반환하지 않습니다.', inputSchema: schemas.get_trace, annotations: { readOnlyHint: true }, execute: async (value) => {
      try {
        const input = objectInput(value); assertKeys(input, ['run_id']); const runId = boundedString(input, 'run_id', true)!;
        const flow = await apiFetch<Flow>(`/api/observe/runs/${encodeURIComponent(runId)}/flow`);
        return { request_id: String(flow.request_id ?? ''), run_id: String(flow.run_id ?? runId), steps: (flow.nodes || []).map((node) => ({ id: String(node.id ?? ''), kind: String(node.kind ?? ''), status: String(node.status ?? '') })) };
      } catch (error) { if (error instanceof Error) throw error; throw safeError(error); }
    } },
  ];
}

let activeController: AbortController | null = null;
export function unregisterWebMcpTools() { activeController?.abort(); activeController = null; }

export async function registerWebMcpTools(): Promise<number> {
  const context = (document as Document & { modelContext?: ModelContext }).modelContext;
  if (!context || typeof context.registerTool !== 'function') return 0;
  unregisterWebMcpTools();
  const controller = new AbortController(); activeController = controller;
  let count = 0;
  for (const tool of createWebMcpTools()) {
    try { await context.registerTool(tool, { signal: controller.signal }); count += 1; }
    catch { /* A browser may expose the draft API partially; keep the app usable. */ }
  }
  return count;
}

if (typeof window !== 'undefined') window.addEventListener('auth:unauthorized', unregisterWebMcpTools);
