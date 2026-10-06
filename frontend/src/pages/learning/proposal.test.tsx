import '@testing-library/jest-dom/vitest';
import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Learning } from '../Learning';

vi.mock('../../api/learning', () => ({ learningApi: {
  orgs: async () => ({ orgs: [{ id: 't-alpha-it', name: 'it' }] }),
  candidates: async () => [], corrections: async () => ({ corrections: [] }),
  rules: async () => ({ rules: [] }),
} }));
vi.mock('../../api/policy', () => ({ policyApi: { active: async () => ({ version: 1, config: {} }) } }));
afterEach(cleanup);
it('reviewer can open a human proposal form', async () => {
  render(<MemoryRouter><Learning roles={['reviewer']} /></MemoryRouter>);
  expect(await screen.findByRole('button', { name: '사람 후보 제안' })).toBeInTheDocument();
});
it('operator cannot propose a candidate', async () => {
  render(<MemoryRouter><Learning roles={['operator']} /></MemoryRouter>);
  await screen.findByRole('heading', { name: '규칙 학습' });
  expect(screen.queryByRole('button', { name: '사람 후보 제안' })).toBeNull();
});

it('offers only action values allowed by the server safety contract', async () => {
  render(<MemoryRouter><Learning roles={['reviewer']} /></MemoryRouter>);
  fireEvent.click(await screen.findByRole('button', { name: '사람 후보 제안' }));
  fireEvent.change(screen.getByLabelText('제안 판단 항목'), { target: { value: 'urgency' } });
  expect(screen.getByRole('option', { name: '긴급' })).toBeInTheDocument();
  expect(screen.queryByRole('option', { name: '일반' })).toBeNull();
  fireEvent.change(screen.getByLabelText('제안 판단 항목'), { target: { value: 'feasibility' } });
  expect(screen.queryByRole('option', { name: '가능' })).toBeNull();
  expect(screen.getByRole('option', { name: '조건부 가능' })).toBeInTheDocument();
});

it('builds keyword and organization ID predicates and locks the form during JSON editing', async () => {
  const { Proposal } = await import('./Proposal');
  const submit = vi.fn();
  render(<Proposal busy={false} onSubmit={submit} onClose={() => {}} />);
  await screen.findByRole('option', { name: 'IT팀' });
  fireEvent.change(screen.getByLabelText('제안 판단 항목'), { target: { value: 'lead_org' } });
  fireEvent.change(screen.getByLabelText('제안 값'), { target: { value: 'IT팀' } });
  fireEvent.change(screen.getByLabelText('원문 키워드'), { target: { value: 'VPN' } });
  fireEvent.keyDown(screen.getByLabelText('원문 키워드'), { key: 'Enter' });
  fireEvent.change(screen.getByLabelText('요청 조직'), { target: { value: 't-alpha-it' } });
  fireEvent.change(screen.getByLabelText('제안 사유'), { target: { value: '운영 규칙 제안' } });
  await screen.findByText('이 항목에서 조회 가능한 수정 기록이 없습니다.');
  fireEvent.submit(screen.getByRole('form', { name: '사람 후보 제안' }));
  expect(submit).toHaveBeenLastCalledWith(expect.objectContaining({ field: 'lead_org', proposed_action: { set: 'IT팀' }, scope: { all: [{ text: { contains_any: ['VPN'] } }, { requester_org: 't-alpha-it' }] } }));
  fireEvent.click(screen.getByText('고급: 조건 JSON'));
  fireEvent.change(screen.getByLabelText('제안 범위'), { target: { value: '{"all":[{"text":{"contains_any":["서버"]}}]}' } });
  expect(screen.getByText('JSON 직접 편집 중')).toBeInTheDocument();
  expect(screen.getByLabelText('원문 키워드')).toBeDisabled();
  fireEvent.submit(screen.getByRole('form', { name: '사람 후보 제안' }));
  expect(submit).toHaveBeenLastCalledWith(expect.objectContaining({ scope: { all: [{ text: { contains_any: ['서버'] } }] } }));
  fireEvent.click(screen.getByRole('button', { name: '조건 폼으로 돌아가기' }));
  expect(screen.getByLabelText('원문 키워드')).not.toBeDisabled();
});

it('caps keyword chips at twenty, supports commas, removes chips and rejects malformed JSON', async () => {
  const { Proposal } = await import('./Proposal');
  const submit = vi.fn();
  render(<Proposal busy={false} onSubmit={submit} onClose={() => {}} />);
  await screen.findByRole('option', { name: 'IT팀' });
  fireEvent.change(screen.getByLabelText('원문 키워드'), { target: { value: Array.from({ length: 20 }, (_, i) => `키${i}`).join(',') } });
  fireEvent.keyDown(screen.getByLabelText('원문 키워드'), { key: ',' });
  fireEvent.change(screen.getByLabelText('원문 키워드'), { target: { value: 'VPN' } });
  fireEvent.keyDown(screen.getByLabelText('원문 키워드'), { key: 'Enter' });
  expect(screen.getByRole('alert')).toHaveTextContent('최대 20개');
  fireEvent.click(screen.getByRole('button', { name: '키워드 키0 삭제' }));
  fireEvent.click(screen.getByRole('button', { name: '키워드 추가' }));
  expect(screen.getByRole('button', { name: '키워드 VPN 삭제' })).toBeInTheDocument();
  fireEvent.click(screen.getByText('고급: 조건 JSON'));
  fireEvent.change(screen.getByLabelText('제안 범위'), { target: { value: 'invalid' } });
  fireEvent.submit(screen.getByRole('form', { name: '사람 후보 제안' }));
  expect(screen.getByRole('alert')).toHaveTextContent('JSON');
  expect(submit).not.toHaveBeenCalled();
});
