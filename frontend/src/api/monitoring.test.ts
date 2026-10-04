import { afterEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({ fetch: vi.fn() }));
vi.mock('./client', () => ({ apiFetch: mocks.fetch }));
import { monitoringApi } from './monitoring';

afterEach(() => vi.clearAllMocks());
describe('monitoringApi request de-duplication (F3)', () => {
  it('shares one in-flight request between identical calls and forgets it once settled', async () => {
    let release: (value: unknown) => void = () => undefined;
    mocks.fetch.mockReturnValueOnce(new Promise((resolve) => { release = resolve; })).mockResolvedValue({ again: true });
    const first = monitoringApi.slo(); const second = monitoringApi.slo();
    expect(mocks.fetch).toHaveBeenCalledTimes(1);
    release({ ok: 1 });
    expect(await first).toEqual({ ok: 1 }); expect(await second).toEqual({ ok: 1 });
    await monitoringApi.slo();
    expect(mocks.fetch).toHaveBeenCalledTimes(2);
  });
  it('keeps requests with different filters apart', async () => {
    mocks.fetch.mockResolvedValue({});
    void monitoringApi.summary({ from: 'a' }); void monitoringApi.summary({ from: 'b' });
    expect(mocks.fetch).toHaveBeenCalledTimes(2);
  });
  it('does not cache a failure', async () => {
    mocks.fetch.mockRejectedValueOnce(new Error('boom')).mockResolvedValue({ ok: 1 });
    await expect(monitoringApi.alerts()).rejects.toThrow('boom');
    expect(await monitoringApi.alerts()).toEqual({ ok: 1 });
  });
});
