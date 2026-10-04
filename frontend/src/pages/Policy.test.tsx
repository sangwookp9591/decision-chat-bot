import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Policy } from './Policy';

const mocks = vi.hoisted(() => ({ active: vi.fn(), versions: vi.fn(), validate: vi.fn(), publish: vi.fn(), version: vi.fn(), rollback: vi.fn() }));
vi.mock('../api/policy', () => ({ policyApi: mocks }));
let emit: (event: { type: string; payload?: Record<string, unknown> }) => void = () => undefined;
vi.mock('../state/events', () => ({ useEventStream: (_f: unknown, _s: unknown, onEvent: typeof emit) => { emit = onEvent; return { status: 'connected', lastSeq: 0 }; }, EventConnectionStatus: () => <span>실시간 연결됨</span> }));
const config = { schema_version: 'policy-schema-v1', auto_assign: false, choice_confidence_thresholds: {}, noul_probability_thresholds: {}, risk_clear_max: .2, reviewer_groups: {}, limits: {}, evidence_noul_threshold: .6, catalog_noul_threshold: .6, feature_flags: {}, rules: [] };
beforeEach(() => { cleanup(); vi.clearAllMocks(); sessionStorage.setItem('jevtriage:roles', JSON.stringify(['policy_editor'])); mocks.active.mockResolvedValue({version: 2, config}); mocks.versions.mockResolvedValue({versions:[{version:2,status:'active',reason:'current',created_by:'editor',created_at:'now'}]}); });
afterEach(cleanup);

describe('Policy page', () => {
  it('renders selected-version diff', async () => {
    mocks.version.mockResolvedValue({version:1,status:'superseded',reason:'r',created_by:'u',created_at:'t',config,diff:{risk_clear_max:{before:.2,after:.1}}});
    render(<Policy canEdit />); await screen.findByText('버전 이력'); fireEvent.click(screen.getByRole('button',{name:'v2'}));
    await waitFor(() => expect(mocks.version).toHaveBeenCalledWith(2));
    // The active row is v2; detail mock confirms diff rendering via a selected history entry.
    expect((await screen.findAllByText('위험 없음 확인 상한')).length).toBeGreaterThan(1);
  });
  it('explains a 409 publish conflict and reloads current policy', async () => {
    mocks.validate.mockResolvedValue({valid:true,config,errors:[]});
    mocks.publish.mockRejectedValue({status:409,code:'ACTIVE_VERSION_CONFLICT',message:'활성 버전이 다릅니다.'});
    render(<Policy canEdit />); await screen.findByText('버전 이력');
    fireEvent.click(screen.getByRole('button',{name:'서버 검증'})); await screen.findByText('검증 통과');
    fireEvent.change(screen.getByLabelText('게시 사유 (필수)'),{target:{value:'정책 조정'}});
    fireEvent.click(screen.getByRole('button',{name:'게시'}));
    expect(await screen.findByText(/활성 버전이 변경되었습니다/)).toBeTruthy();
    expect(mocks.active).toHaveBeenCalledTimes(2);
  });
  it('lets the editor clear and retype a JSON value without snapping back (P3-08)', async () => {
    render(<Policy canEdit />); await screen.findByText('버전 이력');
    const field = screen.getByLabelText('위험 없음 확인 상한 (JSON)') as HTMLTextAreaElement;
    fireEvent.change(field, { target: { value: '' } });
    expect(field.value).toBe('');
    expect(screen.getByRole('alert').textContent).toContain('올바른 JSON');
    expect(screen.getByRole('button', { name: '서버 검증' })).toBeEnabled();
    fireEvent.change(field, { target: { value: '0.1' } });
    expect(field.value).toBe('0.1');
    expect(screen.queryByRole('alert')).toBeNull();
    mocks.validate.mockResolvedValue({ valid: true, config, errors: [] });
    fireEvent.click(screen.getByRole('button', { name: '서버 검증' }));
    await waitFor(() => expect(mocks.validate).toHaveBeenCalledWith(expect.objectContaining({ risk_clear_max: 0.1 })));
  });
  it('shows validation errors in Korean with the internal code under technical details (P3-13)', async () => {
    mocks.validate.mockResolvedValue({ valid: false, config, errors: [{ code: 'SCHEMA_INVALID', reason: 'Value error, thresholds must be between 0 and 1' }] });
    render(<Policy canEdit />); await screen.findByText('버전 이력');
    fireEvent.click(screen.getByRole('button', { name: '서버 검증' }));
    const item = (await screen.findByText(/임계값은 0과 1 사이여야 합니다/)).closest('li')!;
    expect(item.querySelector('details code')?.textContent).toContain('SCHEMA_INVALID');
  });
  // F2 (VERIFY-P7): replayed policy.published events overwrote what the editor had just typed.
  describe('policy.published events (F2)', () => {
    const type = (value: string) => { const field = screen.getByLabelText('위험 없음 확인 상한 (JSON)') as HTMLTextAreaElement; fireEvent.change(field, { target: { value } }); return field; };
    it('ignores replayed events at or below the active version and validates exactly what was typed', async () => {
      render(<Policy canEdit />); await screen.findByText('버전 이력');
      const field = type('1.5');
      act(() => { emit({ type: 'policy.published', payload: { version: 1 } }); emit({ type: 'policy.published', payload: { version: 2 } }); });
      await act(async () => undefined);
      expect(mocks.active).toHaveBeenCalledTimes(1);
      expect(field.value).toBe('1.5');
      mocks.validate.mockResolvedValue({ valid: false, config, errors: [] });
      fireEvent.click(screen.getByRole('button', { name: '서버 검증' }));
      await waitFor(() => expect(mocks.validate).toHaveBeenCalledWith(expect.objectContaining({ risk_clear_max: 1.5 })));
    });
    it('does not overwrite an edit in progress with a newer version: asks first, then applies or keeps', async () => {
      render(<Policy canEdit />); await screen.findByText('버전 이력');
      const field = type('0.1');
      mocks.active.mockResolvedValue({ version: 3, config: { ...config, risk_clear_max: 0.5 } });
      act(() => emit({ type: 'policy.published', payload: { version: 3 } }));
      expect(await screen.findByText(/새 버전.*게시/)).toBeTruthy();
      expect(field.value).toBe('0.1');
      fireEvent.click(screen.getByRole('button', { name: '내 편집 유지' }));
      expect(screen.queryByText(/새 버전.*게시/)).toBeNull();
      expect(field.value).toBe('0.1');
      act(() => emit({ type: 'policy.published', payload: { version: 3 } }));
      fireEvent.click(await screen.findByRole('button', { name: '새 버전 반영' }));
      await waitFor(() => expect((screen.getByLabelText('위험 없음 확인 상한 (JSON)') as HTMLTextAreaElement).value).toBe('0.5'));
    });
    it('reloads silently for a newer version when nothing was edited', async () => {
      render(<Policy canEdit />); await screen.findByText('버전 이력');
      mocks.active.mockResolvedValue({ version: 3, config: { ...config, risk_clear_max: 0.5 } });
      act(() => emit({ type: 'policy.published', payload: { version: 3 } }));
      await waitFor(() => expect((screen.getByLabelText('위험 없음 확인 상한 (JSON)') as HTMLTextAreaElement).value).toBe('0.5'));
    });
    it('a slower, older fetch never overwrites a newer one (generation check)', async () => {
      render(<Policy canEdit />); await screen.findByText('버전 이력');
      let releaseOld: (value: unknown) => void = () => undefined;
      mocks.active.mockReturnValueOnce(new Promise((resolve) => { releaseOld = resolve; })).mockResolvedValue({ version: 4, config: { ...config, risk_clear_max: 0.5 } });
      act(() => emit({ type: 'policy.published', payload: { version: 3 } }));
      act(() => emit({ type: 'policy.published', payload: { version: 4 } }));
      await waitFor(() => expect((screen.getByLabelText('위험 없음 확인 상한 (JSON)') as HTMLTextAreaElement).value).toBe('0.5'));
      await act(async () => releaseOld({ version: 3, config: { ...config, risk_clear_max: 0.9 } }));
      expect((screen.getByLabelText('위험 없음 확인 상한 (JSON)') as HTMLTextAreaElement).value).toBe('0.5');
      expect(screen.getByText('v4')).toBeTruthy();
    });
  });
  it('names every editor field in Korean with a short hint and keeps the internal key under 기술 상세 (F6)', async () => {
    render(<Policy canEdit />); await screen.findByText('버전 이력');
    for (const title of ['선택형 판단 최소 확신도', '참여 확률 기준', '확률 불확실 구간', '검토자 그룹', '근거 연결 확률 기준', '기능 사용 여부', '규칙 학습 기준', '개인정보 마스킹', '보관 기간']) expect(screen.getByRole('group', { name: title })).toBeTruthy();
    const group = screen.getByRole('group', { name: '선택형 판단 최소 확신도' });
    expect(group.querySelector('.policy-hint')?.textContent).toMatch(/확신도/);
    expect(group.querySelector('legend')?.textContent).not.toContain('choice_confidence_thresholds');
    expect(group.querySelector('details code')?.textContent).toBe('choice_confidence_thresholds');
    // no English key is used as a visible label
    for (const key of ['noul_uncertain_band', 'learning', 'masking', 'retention']) expect(screen.queryByLabelText(key)).toBeNull();
  });
  const full = { ...config, noul_uncertain_band: [.35, .65], feature_flags: { shadow_compare: true }, learning: { min_support: 3, min_effect_sample: 20, shadow_max_calls: 20, effect_window_days: 7 }, masking: { enabled: true, categories: ['email', 'phone'] }, retention: { event_days: 90, idempotency_days: 30, session_grace_days: 7, login_attempt_window_seconds: 900, journal_days: 90, metrics_days: 90, batch_size: 500 }, limits: { text_chars: 20000, attachments: 5 } };
  describe('field form', () => {
    beforeEach(() => { mocks.active.mockResolvedValue({ version: 2, config: full }); });
    it('edits a number, a band, a switch and a chip and validates exactly those values', async () => {
      render(<Policy canEdit />); await screen.findByText('버전 이력');
      fireEvent.change(screen.getByLabelText('확률 상한'), { target: { value: '0.1' } });
      fireEvent.change(screen.getByLabelText('하한'), { target: { value: '0.2' } });
      fireEvent.click(screen.getByRole('switch', { name: 'shadow_compare' }));
      fireEvent.click(screen.getByRole('button', { name: '전화번호' }));
      fireEvent.click(screen.getByRole('button', { name: '카드번호' }));
      mocks.validate.mockResolvedValue({ valid: true, config, errors: [] });
      fireEvent.click(screen.getByRole('button', { name: '서버 검증' }));
      await waitFor(() => expect(mocks.validate).toHaveBeenCalled());
      expect(mocks.validate.mock.calls[0][0]).toMatchObject({ risk_clear_max: 0.1, noul_uncertain_band: [0.2, 0.65], feature_flags: { shadow_compare: false }, masking: { enabled: true, categories: ['card', 'email'] } });
      expect((screen.getByLabelText('위험 없음 확인 상한 (JSON)') as HTMLTextAreaElement).value).toBe('0.1');
    });
    it('explains why 게시 is disabled and blocks it while a number field is not a number', async () => {
      render(<Policy canEdit />); await screen.findByText('버전 이력');
      expect(screen.getByRole('button', { name: '게시' })).toBeDisabled();
      expect(screen.getByText(/게시할 수 없는 이유: .*서버 검증/)).toBeTruthy();
      fireEvent.change(screen.getByLabelText('확률 상한'), { target: { value: '' } });
      expect(screen.getByText(/숫자를 입력해 주세요/)).toBeTruthy();
      expect(screen.getByText(/게시할 수 없는 이유: 입력 오류/)).toBeTruthy();
      fireEvent.change(screen.getByLabelText('확률 상한'), { target: { value: '0.3' } });
      mocks.validate.mockResolvedValue({ valid: true, config, errors: [] });
      fireEvent.click(screen.getByRole('button', { name: '서버 검증' }));
      await waitFor(() => expect(screen.getByRole('button', { name: '게시' })).toBeEnabled());
      expect(screen.queryByText(/게시할 수 없는 이유/)).toBeNull();
    });
    it('shows the allowed range and warns when the band is inverted', async () => {
      render(<Policy canEdit />); await screen.findByText('버전 이력');
      fireEvent.change(screen.getByLabelText('하한'), { target: { value: '0.9' } });
      expect(screen.getByText('하한은 상한보다 작아야 합니다.')).toBeTruthy();
      expect(screen.getAllByText('0~1').length).toBeGreaterThan(0);
    });
    it('is read-only without the editor role', async () => {
      render(<Policy />); await screen.findByText('버전 이력');
      expect(screen.getByLabelText('확률 상한')).toBeDisabled();
      expect(screen.getByRole('switch', { name: 'shadow_compare' })).toBeDisabled();
      expect(screen.queryByRole('button', { name: '게시' })).toBeNull();
    });
  });
});
