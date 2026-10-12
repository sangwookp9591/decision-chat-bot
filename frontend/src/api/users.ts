import { apiFetch } from './client';

export type AdminUser = { user_id: string; email: string | null; display_name: string | null; disabled: boolean; can_read_source: boolean; version: number; roles: string[]; org_ids: string[] };
export type AdminOrg = { id: string; name: string };
export type UserState = Pick<AdminUser, 'roles' | 'org_ids' | 'disabled' | 'can_read_source'>;
export type UserHistory = { id: string; actor_id: string; action: string; reason: string; before: UserState | null; after: UserState | null; at: string };
export type UserCommand = UserState & { version: number; reason: string };
export type NewUser = { email: string; display_name: string | null; roles: string[]; org_ids: string[]; can_read_source: boolean; reason: string };

export const userApi = {
  list: () => apiFetch<{ users: AdminUser[]; orgs: AdminOrg[]; roles: string[] }>('/api/admin/users'),
  create: (body: NewUser) => apiFetch<{ user: AdminUser; temporary_password: string }>('/api/admin/users', { method: 'POST', body: JSON.stringify(body) }),
  detail: (id: string) => apiFetch<{ user: AdminUser; history: UserHistory[] }>(`/api/admin/users/${encodeURIComponent(id)}`),
  update: (id: string, command: UserCommand) => apiFetch<AdminUser>(`/api/admin/users/${encodeURIComponent(id)}`, { method: 'POST', body: JSON.stringify(command) }),
};
