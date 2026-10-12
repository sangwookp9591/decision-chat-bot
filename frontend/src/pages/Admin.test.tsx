import '@testing-library/jest-dom/vitest';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
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

  it.each([true, false])('reloads conflicting changes and clears the draft (self=%s)', async (self) => {
    const target = self ? master : member;
    const current = { ...target, version: target.version + 1, can_read_source: !target.can_read_source };
    vi.mocked(userApi.list).mockResolvedValueOnce({ users: [target], orgs, roles: ROLES })
      .mockResolvedValue({ users: [current], orgs, roles: ROLES });
    vi.mocked(userApi.update).mockRejectedValue({ status: 409, message: 'version conflict' });
    render(<Admin roles={['admin']} selfId="usr_master" />);
    const card = await screen.findByRole('region', { name: `${target.display_name || target.email} 계정` });
    fireEvent.click(within(card).getByRole('switch', { name: '원문 열람' }));
    fireEvent.change(within(card).getByLabelText('변경 사유'), { target: { value: 'update access' } });
    fireEvent.click(within(card).getByRole('button', { name: '변경 저장' }));
    await waitFor(() => expect(userApi.list).toHaveBeenCalledTimes(2));
    const refreshed = screen.getByRole('region', { name: `${target.display_name || target.email} 계정` });
    expect(within(refreshed).getByLabelText('변경 사유')).toHaveValue('');
    expect(within(refreshed).getByRole('switch', { name: '원문 열람' })).toHaveAttribute('aria-checked', String(current.can_read_source));
    expect(within(refreshed).getByRole('button', { name: '변경 저장' })).toBeDisabled();
  });

  it('keeps the saved account version and clears the draft even if refreshing the list fails', async () => {
    vi.mocked(userApi.list).mockResolvedValueOnce({ users: [member], orgs, roles: ROLES })
      .mockRejectedValue({ message: 'list unavailable' });
    vi.mocked(userApi.update).mockResolvedValue({ ...member, can_read_source: true, version: 3 });
    render(<Admin roles={['admin']} selfId="usr_master" />);
    const card = await screen.findByRole('region', { name: 'member@t.dev 계정' });
    fireEvent.click(within(card).getByRole('switch', { name: '원문 열람' }));
    fireEvent.change(within(card).getByLabelText('변경 사유'), { target: { value: 'update access' } });
    fireEvent.click(within(card).getByRole('button', { name: '변경 저장' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('list unavailable');
    const saved = screen.getByRole('region', { name: 'member@t.dev 계정' });
    expect(saved).toHaveTextContent('v3');
    expect(within(saved).getByLabelText('변경 사유')).toHaveValue('');
    expect(within(saved).getByRole('switch', { name: '원문 열람' })).toHaveAttribute('aria-checked', 'true');
    expect(within(saved).getByRole('button', { name: '변경 저장' })).toBeDisabled();
  });

  it('preserves a conflicting draft and reports refresh failure without a success notice', async () => {
    vi.mocked(userApi.list).mockResolvedValueOnce({ users: [member], orgs, roles: ROLES })
      .mockRejectedValue({ message: 'list unavailable' });
    vi.mocked(userApi.update).mockRejectedValue({ status: 409, message: 'version conflict' });
    render(<Admin roles={['admin']} selfId="usr_master" />);
    const card = await screen.findByRole('region', { name: 'member@t.dev 계정' });
    fireEvent.click(within(card).getByRole('switch', { name: '원문 열람' }));
    fireEvent.change(within(card).getByLabelText('변경 사유'), { target: { value: 'update access' } });
    fireEvent.click(within(card).getByRole('button', { name: '변경 저장' }));
    expect(await screen.findByText('list unavailable')).toHaveAttribute('role', 'alert');
    expect(within(card).getByLabelText('변경 사유')).toHaveValue('update access');
    expect(within(card).getByRole('switch', { name: '원문 열람' })).toHaveAttribute('aria-checked', 'true');
    expect(screen.queryByText('다른 관리자가 먼저 변경해 최신 상태를 다시 불러왔습니다.')).not.toBeInTheDocument();
  });

  it('reports a history fetch failure instead of claiming there is no history', async () => {
    vi.mocked(userApi.detail).mockRejectedValue({ message: 'history unavailable' });
    render(<Admin roles={['admin']} selfId="usr_master" />);
    expect(await screen.findByRole('alert')).toHaveTextContent('history unavailable');
    expect(screen.queryByText('아직 변경 이력이 없습니다.')).not.toBeInTheDocument();
  });

  it('keeps issuance open while pending and clears the password after acknowledgement', async () => {
    const created = { ...member, user_id: 'usr_new', email: 'new@t.dev', version: 0 };
    let complete!: (result: Awaited<ReturnType<typeof userApi.create>>) => void;
    vi.mocked(userApi.create).mockImplementation(() => new Promise((resolve) => { complete = resolve; }));
    render(<Admin roles={['admin']} selfId="usr_master" />);
    fireEvent.click(await screen.findByRole('button', { name: '새 계정 발급' }));
    const dialog = screen.getByRole('dialog');
    fireEvent.change(within(dialog).getByLabelText('이메일'), { target: { value: 'new@t.dev' } });
    fireEvent.click(within(dialog).getByRole('button', { name: /it/ }));
    fireEvent.change(within(dialog).getByLabelText('발급 사유'), { target: { value: 'new account' } });
    fireEvent.click(within(dialog).getByRole('button', { name: '발급' }));
    fireEvent.click(within(dialog).getByRole('button', { name: '취소' }));
    fireEvent.click(within(dialog).getByRole('button', { name: '닫기' }));
    fireEvent.keyDown(document, { key: 'Escape' });
    fireEvent.mouseDown(dialog.parentElement!);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    await act(async () => complete({ user: created, temporary_password: 'Tmp-Secret-123' }));
    expect(within(dialog).getByText('Tmp-Secret-123')).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole('button', { name: '확인했습니다' }));
    fireEvent.click(screen.getByRole('button', { name: '새 계정 발급' }));
    expect(screen.queryByText('Tmp-Secret-123')).not.toBeInTheDocument();
    expect(within(screen.getByRole('dialog')).getByLabelText('이메일')).toHaveValue('');
  });
});
