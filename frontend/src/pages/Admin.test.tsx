import '@testing-library/jest-dom/vitest';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { Admin, describeChange } from './Admin';
import { userApi } from '../api/users';

vi.mock('../api/users', async (original) => ({ ...(await original<typeof import('../api/users')>()), userApi: { list: vi.fn(), detail: vi.fn(), update: vi.fn(), create: vi.fn() } }));
const ROLES = ['requester', 'reviewer', 'team_member', 'operator', 'policy_editor', 'rule_admin', 'labeler', 'admin'];
const orgs = [{ id: 't-ai', name: 'ai' }, { id: 't-it', name: 'it' }];
const master = { user_id: 'usr_master', email: 'master@t.dev', display_name: '마스터', disabled: false, can_read_source: true, version: 0, roles: ROLES, org_ids: ['t-ai', 't-it'] };
const member = { user_id: 'usr_member', email: 'member@t.dev', display_name: null, disabled: false, can_read_source: false, version: 2, roles: ['requester'], org_ids: ['t-ai'] };
beforeEach(() => {
  cleanup(); vi.clearAllMocks();
  vi.mocked(userApi.list).mockResolvedValue({ users: [master, member], orgs, roles: ROLES });
  vi.mocked(userApi.detail).mockResolvedValue({ user: member, history: [] });
  vi.mocked(userApi.update).mockResolvedValue({ ...member, version: 3 });
});

describe('account administration', () => {
  it('describes a change in plain words', () => {
    expect(describeChange(member, { ...member, roles: ['requester', 'reviewer'], can_read_source: true, disabled: true }))
      .toEqual(['역할 추가: 검토자', '원문 열람 켬', '계정 사용 중지']);
  });

  it('tells non-admins they need the admin role and never calls the API', () => {
    render(<Admin roles={['reviewer']} />);
    expect(screen.getByText('관리자 권한이 필요합니다')).toBeInTheDocument();
    expect(userApi.list).not.toHaveBeenCalled();
  });

  it('locks the admin role and suspension on my own account', async () => {
    render(<Admin roles={['admin']} selfId="usr_master" />);
    const card = await screen.findByRole('region', { name: '마스터 계정' });
    expect(within(card).getByRole('checkbox', { name: /^관리자 / })).toBeDisabled();
    expect(within(card).getByRole('switch', { name: '계정 사용 중지' })).toBeDisabled();
  });

  it('grants a role with a reason and sends the current version', async () => {
    render(<Admin roles={['admin']} selfId="usr_master" />);
    fireEvent.click(await screen.findByRole('button', { name: /member@t\.dev/ }));
    const card = screen.getByRole('region', { name: 'member@t.dev 계정' });
    const save = within(card).getByRole('button', { name: '변경 저장' });
    expect(save).toBeDisabled();
    fireEvent.click(within(card).getByRole('checkbox', { name: /검토자/ }));
    expect(within(card).getByRole('list', { name: '바뀔 내용' })).toHaveTextContent('역할 추가: 검토자');
    expect(save).toBeDisabled(); // reason still missing
    fireEvent.change(within(card).getByLabelText('변경 사유'), { target: { value: '검토 배정' } });
    fireEvent.click(save);
    await waitFor(() => expect(userApi.update).toHaveBeenCalledWith('usr_member', { roles: ['requester', 'reviewer'], org_ids: ['t-ai'], disabled: false, can_read_source: false, version: 2, reason: '검토 배정' }));
  });

  it('issues an account and shows the temporary password once', async () => {
    const created = { ...member, user_id: 'usr_new', email: 'new@t.dev', version: 0, roles: ['reviewer'] };
    vi.mocked(userApi.create).mockResolvedValue({ user: created, temporary_password: 'Tmp-Secret-123' });
    render(<Admin roles={['admin']} selfId="usr_master" />);
    fireEvent.click(await screen.findByRole('button', { name: '새 계정 발급' }));
    const dialog = await screen.findByRole('dialog');
    const issue = within(dialog).getByRole('button', { name: '발급' });
    expect(issue).toBeDisabled();
    fireEvent.change(within(dialog).getByLabelText('이메일'), { target: { value: 'new@t.dev' } });
    fireEvent.click(within(dialog).getByRole('checkbox', { name: /요청자/ })); // default off
    fireEvent.click(within(dialog).getByRole('checkbox', { name: /검토자/ }));
    fireEvent.click(within(dialog).getByRole('button', { name: /it/ }));
    fireEvent.change(within(dialog).getByLabelText('발급 사유'), { target: { value: '입사' } });
    fireEvent.click(issue);
    await waitFor(() => expect(userApi.create).toHaveBeenCalledWith({ email: 'new@t.dev', display_name: null, roles: ['reviewer'], org_ids: ['t-it'], can_read_source: false, reason: '입사' }));
    expect(await within(dialog).findByText('Tmp-Secret-123')).toBeInTheDocument();
    expect(dialog).toHaveTextContent('다시 볼 수 없습니다');
  });
});
