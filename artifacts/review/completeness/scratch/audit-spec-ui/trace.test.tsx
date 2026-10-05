import '@testing-library/jest-dom/vitest';
import React from 'react';
import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Observatory } from '/Users/psw/Projects/decision-chat-bot/frontend/src/pages/Observatory';
import { observeApi } from '/Users/psw/Projects/decision-chat-bot/frontend/src/api/observe';

vi.mock('/Users/psw/Projects/decision-chat-bot/frontend/src/state/events', () => ({ useEventStream: () => ({ status: 'connected', lastSeq: 0 }) }));
vi.mock('/Users/psw/Projects/decision-chat-bot/frontend/src/api/observe', async (original) => ({ ...(await original<any>()), observeApi: { requests: vi.fn(), runs: vi.fn(), flow: vi.fn(), playback: vi.fn(), topology: vi.fn(), step: vi.fn() } }));
afterEach(cleanup);

it.each(['JevTimeout', '12345', 'jev-audit-1', 'schema-audit-1'])('Trace shows saved %s required by spec/04:13', async (expected) => {
  vi.mocked(observeApi.requests).mockResolvedValue({ items: [{ id: 'req_1', status: 'failed' }] });
  vi.mocked(observeApi.runs).mockResolvedValue({ active_run_id: 'run_1', runs: [{ id: 'run_1', status: 'failed', versions: {} }] });
  vi.mocked(observeApi.flow).mockResolvedValue({ request_id: 'req_1', run_id: 'run_1', live: false, nodes: [{ id: 'step_1', name: 'Jev 판단', kind: 'ai', status: 'failed' }], edges: [] });
  vi.mocked(observeApi.playback).mockResolvedValue({ request_id: 'req_1', run_id: 'run_1', live: false, events: [], reviews: [], final_result: 'failed' });
  vi.mocked(observeApi.step).mockResolvedValue({ id: 'step_1', name: 'Jev 판단', kind: 'ai', status: 'failed', run_id: 'run_1', error_class: 'JevTimeout', duration_ms: 12345, versions: { model: 'jev-audit-1', schema: 'schema-audit-1' }, judgment: null, input_summary: {}, output_summary: {}, review_history: [], source_links: [] } as any);
  render(<MemoryRouter initialEntries={['/observatory?request_id=req_1']}><Observatory /></MemoryRouter>);
  fireEvent.click(await screen.findByRole('button', { name: /Jev 판단/ }));
  const dialog = await screen.findByRole('dialog', { name: 'Trace 상세' });
  expect(dialog).toHaveTextContent(expected);
});
