import { afterEach, describe, expect, it, vi } from 'vitest';
import { apiFetch } from '../api/client';
import { createWebMcpTools, registerWebMcpTools } from './index';

vi.mock('../api/client', () => ({ apiFetch: vi.fn() }));
const apiFetchMock = vi.mocked(apiFetch);

afterEach(() => { vi.restoreAllMocks(); apiFetchMock.mockReset(); delete (document as Document & { modelContext?: unknown }).modelContext; });

describe('WebMCP integration', () => {
  it('does not register tools when the draft API is unavailable', async () => {
    apiFetchMock.mockResolvedValue({ id: 'user' });
    expect(await registerWebMcpTools()).toBe(0);
    expect(apiFetchMock).not.toHaveBeenCalled();
    expect(document.body).toBeTruthy();
  });

  it('validates handler input and turns API failures into tool errors', async () => {
    const [search] = createWebMcpTools();
    await expect(search.execute({ limit: 101 })).rejects.toThrow('limit 입력이 올바르지 않습니다.');
    await expect(search.execute({ query: 'x'.repeat(121) })).rejects.toThrow('query 입력이 올바르지 않습니다.');
    await expect(search.execute({ query: 'ok', surprise: true })).rejects.toThrow('지원하지 않는 입력');
    apiFetchMock.mockRejectedValue({ status: 404, code: 'NOT_FOUND', message: 'not found' });
    await expect(search.execute({ query: 'req_', limit: 5 })).rejects.toThrow('404 NOT_FOUND');
  });

  it('returns only request and trace summaries without evidence text', async () => {
    const tools = createWebMcpTools();
    apiFetchMock.mockResolvedValueOnce({ request: { id: 'req_1', status: 'review' } }).mockResolvedValueOnce({ summary: { text: 'Short summary' } });
    await expect(tools[1].execute({ request_id: 'req_1' })).resolves.toEqual({ id: 'req_1', status: 'review', judgment_summary: 'Short summary' });
    apiFetchMock.mockResolvedValueOnce({ request_id: 'req_1', run_id: 'run_1', nodes: [{ id: 'step_1', kind: 'judge', status: 'succeeded', output_summary: { source_text: 'secret' } }] });
    await expect(tools[2].execute({ run_id: 'run_1' })).resolves.toEqual({ request_id: 'req_1', run_id: 'run_1', steps: [{ id: 'step_1', kind: 'judge', status: 'succeeded' }] });
  });
});
