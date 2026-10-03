import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Policy } from './Policy';

const mocks = vi.hoisted(() => ({ active: vi.fn(), versions: vi.fn(), validate: vi.fn(), publish: vi.fn(), version: vi.fn(), rollback: vi.fn() }));
vi.mock('../api/policy', () => ({ policyApi: mocks }));
vi.mock('../state/events', () => ({ useEventStream: () => ({ status: 'connected', lastSeq: 0 }), EventConnectionStatus: () => <span>실시간 연결됨</span> }));
const config = { schema_version: 'policy-schema-v1', auto_assign: false, choice_confidence_thresholds: {}, noul_probability_thresholds: {}, risk_clear_max: .2, reviewer_groups: {}, limits: {}, evidence_noul_threshold: .6, catalog_noul_threshold: .6, feature_flags: {}, rules: [] };
beforeEach(() => { cleanup(); vi.clearAllMocks(); sessionStorage.setItem('jevtriage:roles', JSON.stringify(['policy_editor'])); mocks.active.mockResolvedValue({version: 2, config}); mocks.versions.mockResolvedValue({versions:[{version:2,status:'active',reason:'current',created_by:'editor',created_at:'now'}]}); });
afterEach(cleanup);

describe('Policy page', () => {
  it('renders selected-version diff', async () => {
    mocks.version.mockResolvedValue({version:1,status:'superseded',reason:'r',created_by:'u',created_at:'t',config,diff:{risk_clear_max:{before:.2,after:.1}}});
    render(<Policy canEdit />); await screen.findByText('버전 이력'); fireEvent.click(screen.getByRole('button',{name:'v2'}));
    await waitFor(() => expect(mocks.version).toHaveBeenCalledWith(2));
    // The active row is v2; detail mock confirms diff rendering via a selected history entry.
    expect((await screen.findAllByText('risk_clear_max')).length).toBeGreaterThan(1);
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
    const field = screen.getByLabelText('risk_clear_max') as HTMLTextAreaElement;
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
});
