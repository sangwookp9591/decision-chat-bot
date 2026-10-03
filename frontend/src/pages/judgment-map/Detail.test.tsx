import { afterEach, describe, expect, it, vi } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import type { GraphNode } from '../../api/graph';
import { Detail } from './Detail';
import { requestApi } from '../../api/requests';

vi.mock('../../api/requests', () => ({ requestApi: { document: vi.fn() } }));
afterEach(cleanup);
const span: GraphNode = { id: 'esp_5', kind: 'EvidenceSpan', layer: 1, title: '문서 근거 3', summary: '', status: '보존', actor: null, at: null, version: 'rev_1', source: 'att_1', request_id: 'req_1',
  refs: { request_id: 'req_1', revision_id: 'rev_1', source: 'att_1', span_id: 'esp_5' } };

describe('judgment map evidence node', () => {
  it('opens the source viewer at the node unit even when the account cannot read the source text', async () => {
    vi.mocked(requestApi.document).mockResolvedValue({ request_id: 'req_1', revision: 1, revision_id: 'rev_1', source: 'att_1', kind: 'pdf', filename: 'a.pdf', can_read_source: false,
      units: [{ unit_id: 'esp_5', order: 0, location: { page: 3 }, char_start: 0, char_end: 1 }] });
    Element.prototype.scrollTo = vi.fn() as never;
    const detail = { ...span, upstream: [], downstream: [], edges: [], can_read_source: false, source_link: null };
    render(<MemoryRouter><Detail node={span} detail={detail} loading={false} onPick={() => undefined} layerName={() => '근거'} /></MemoryRouter>);
    fireEvent.click(screen.getByRole('button', { name: '원문 열기' }));
    expect(await screen.findByText(/원문 열람 권한 없음/)).toBeInTheDocument();
    expect(requestApi.document).toHaveBeenCalledWith('req_1', 'rev_1', 'att_1');
    expect(document.querySelector('[data-unit-id="esp_5"]')).toHaveAttribute('aria-current', 'location');
  });
  it('has no open-source button for other node kinds', () => {
    const other = { ...span, kind: 'RunStep' as const, refs: { request_id: 'req_1' } };
    render(<MemoryRouter><Detail node={other} detail={null} loading={false} onPick={() => undefined} layerName={() => '업무'} /></MemoryRouter>);
    expect(screen.queryByRole('button', { name: '원문 열기' })).toBeNull();
  });
});
