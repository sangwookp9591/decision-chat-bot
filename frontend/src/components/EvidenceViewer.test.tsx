import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { EvidenceViewer } from './EvidenceViewer';
import { requestApi, type SourceDocument } from '../api/requests';

vi.mock('../api/requests', () => ({ requestApi: { document: vi.fn() } }));
afterEach(cleanup);

const pdf = (canRead: boolean): SourceDocument => ({
  request_id: 'req_1', revision: 1, revision_id: 'rev_1', source: 'att_1', kind: 'pdf', filename: 'spec.pdf', can_read_source: canRead,
  units: [1, 2, 3].map((page) => ({ unit_id: `esp_${page}`, order: page - 1, location: { file: 'spec.pdf', page }, char_start: 0, char_end: 5, ...(canRead ? { text: `PAGE-${page}-TEXT` } : {}) })),
});
const target = { requestId: 'req_1', revision: 'rev_1', source: 'att_1', unitId: 'esp_2' };

describe('EvidenceViewer', () => {
  it('lists every unit in order with page breaks and highlights + scrolls to the anchor unit', async () => {
    vi.mocked(requestApi.document).mockResolvedValue(pdf(true));
    const scroll = vi.fn();
    Element.prototype.scrollTo = scroll as never;
    render(<EvidenceViewer target={target} onClose={() => undefined} />);
    expect(await screen.findByText('PAGE-1-TEXT')).toBeInTheDocument();
    expect(requestApi.document).toHaveBeenCalledWith('req_1', 'rev_1', 'att_1');
    const anchor = document.querySelector('[data-unit-id="esp_2"]') as HTMLElement;
    expect(anchor).toHaveAttribute('aria-current', 'location');
    expect(document.querySelectorAll('[aria-current="location"]')).toHaveLength(1);
    expect(screen.getAllByRole('heading', { level: 3 }).map((h) => h.textContent)).toEqual(['1쪽', '2쪽', '3쪽']);
    await waitFor(() => expect(scroll).toHaveBeenCalled());
  });
  it('shows positions only and the permission notice when the server withholds the source', async () => {
    vi.mocked(requestApi.document).mockResolvedValue(pdf(false));
    render(<EvidenceViewer target={target} onClose={() => undefined} />);
    expect(await screen.findByText(/원문 열람 권한 없음/)).toBeInTheDocument();
    expect(document.body.textContent).not.toContain('PAGE-2-TEXT');
    expect(document.querySelector('[data-unit-id="esp_2"]')).toHaveAttribute('aria-current', 'location');
  });
  it('says so when the anchor unit is not in the document and when loading fails', async () => {
    vi.mocked(requestApi.document).mockResolvedValue(pdf(true));
    const { unmount } = render(<EvidenceViewer target={{ ...target, unitId: 'esp_gone' }} onClose={() => undefined} />);
    expect(await screen.findByText(/해당 근거 위치를 문서에서 찾지 못했습니다/)).toBeInTheDocument();
    unmount();
    vi.mocked(requestApi.document).mockRejectedValue({ status: 404, message: 'x' });
    render(<EvidenceViewer target={target} onClose={() => undefined} />);
    expect(await screen.findByRole('alert')).toHaveTextContent('원문을 불러오지 못했습니다');
  });
});
