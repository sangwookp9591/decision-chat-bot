import '@testing-library/jest-dom/vitest';
import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Learning } from '../Learning';

vi.mock('../../api/learning', () => ({ learningApi: {
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
