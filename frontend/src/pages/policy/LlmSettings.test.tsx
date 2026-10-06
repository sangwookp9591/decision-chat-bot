import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { useState } from 'react';
import '@testing-library/jest-dom/vitest';
import { LlmSettings } from './LlmSettings';
import { defaultLlmConfig, llmApi, type LlmConfig } from '../../api/llm';

vi.mock('../../api/llm', async (original) => ({ ...(await original<typeof import('../../api/llm')>()), llmApi: { providers: vi.fn(), models: vi.fn(), test: vi.fn() } }));
beforeEach(() => {
  vi.mocked(llmApi.providers).mockResolvedValue({ providers: [
    { provider: 'anthropic', key_configured: false, sdk_available: true, default_model: 'claude-opus-5-5' },
    { provider: 'openai', key_configured: false, sdk_available: true, default_model: 'gpt-6-astra' },
    { provider: 'google', key_configured: false, sdk_available: true, default_model: 'gemini-3.8-flash' },
  ] });
  vi.mocked(llmApi.models).mockResolvedValue({ provider: 'anthropic', source: 'default', error_code: 'KEY_MISSING', models: [{ id: 'claude-opus-5-5', label: 'Claude Opus 5.5' }, { id: 'claude-sonnet-5-5', label: 'Claude Sonnet 5.5' }] });
  vi.mocked(llmApi.test).mockResolvedValue({ provider: 'anthropic', model: 'claude-opus-5-5', ok: false, latency_ms: 412, error_code: 'KEY_MISSING', message: 'API 키가 없습니다.', tested_at: '2026-10-06T08:12:00Z' });
});
afterEach(() => { cleanup(); vi.clearAllMocks(); });
function Editor() { const [config, setConfig] = useState(defaultLlmConfig); return <><LlmSettings config={config} canEdit onChange={setConfig} /><output data-testid="config">{JSON.stringify(config)}</output></>; }
it('shows three provider states, safe failure, model source and actual config changes', async () => {
  render(<Editor />);
  fireEvent.click(await screen.findByRole('button', { name: 'Claude 연결 테스트' }));
  expect(await screen.findByText(/실패 · 412ms/)).toHaveTextContent('API 키가 없습니다.');
  fireEvent.change(screen.getByLabelText('사용할 제공자'), { target: { value: 'anthropic' } });
  expect(await screen.findByText('기본 목록')).toBeVisible();
  expect(screen.getByTestId('config')).toHaveTextContent('claude-opus-5-5');
  fireEvent.focus(screen.getByRole('combobox', { name: '모델' }));
  fireEvent.mouseDown(screen.getByRole('option', { name: /Claude Sonnet 5.5/ }));
  fireEvent.click(screen.getByRole('switch', { name: '요약 다듬기' }));
  expect(screen.getByTestId('config')).toHaveTextContent('claude-sonnet-5-5');
  expect(screen.getByTestId('config')).toHaveTextContent('"summary":true');
  expect(document.body.textContent).not.toContain('sk-ant-test-SECRET');
});
it('operator sees status with read-only config and no test buttons', async () => {
  render(<LlmSettings config={{ ...defaultLlmConfig, provider: 'anthropic', model: 'claude-opus-5-5' } as LlmConfig} canEdit={false} onChange={vi.fn()} />);
  await screen.findByText('기본 목록');
  expect(screen.queryByRole('button', { name: /연결 테스트/ })).toBeNull();
  expect(screen.getByLabelText('사용할 제공자')).toBeDisabled();
  for (const control of screen.getAllByRole('switch')) expect(control).toBeDisabled();
});
it('hides provider status for a role rejected by the server', async () => {
  vi.mocked(llmApi.providers).mockRejectedValue({ status: 403, message: '권한 없음' });
  render(<LlmSettings config={defaultLlmConfig} canEdit={false} onChange={vi.fn()} />);
  await waitFor(() => expect(llmApi.providers).toHaveBeenCalled());
  expect(screen.queryByText(/SDK 사용 가능/)).toBeNull();
});
