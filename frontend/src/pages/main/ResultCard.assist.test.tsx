import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { Result } from './ResultCard';
import type { Judgment } from '../../api/requests';

afterEach(cleanup);
it('renders author, extractive base, display-only questions and task description', () => {
  const judgment: Judgment = { id: 'j', request_id: 'req', revision_id: 'rev', run_id: 'run', classifications: { feasibility: '판단 보류' }, risk_confirmed: false, risks: [], author: 'llm:anthropic/claude-opus-5-5', mode: 'mock', versions: {}, outputs: [], review_reasons: [], review: null, summary: { text: '다듬은 요약', author: 'llm:anthropic/claude-opus-5-5', base: { text: '원문 발췌 문장', author: 'code:extractive@1' } }, questions: { items: ['필요한 정보는 무엇인가요?', '<script>unsafe</script>'], author: 'llm:anthropic/claude-opus-5-5' }, draft_tasks: [{ title: '고정된 제목', description: '업무 설명 초안' }] };
  render(<Result judgment={judgment} runs={null} onEvidence={vi.fn()} />);
  expect(screen.getByText('글쓰기 보조(Claude · claude-opus-5-5)가 다듬음')).toBeVisible();
  fireEvent.click(screen.getByText('원문 발췌 보기'));
  expect(screen.getByText('원문 발췌 문장')).toBeVisible();
  expect(screen.getByText('필요한 정보는 무엇인가요?')).toBeVisible();
  expect(screen.getByText('판단은 보류 상태로 남습니다. 질문은 자동으로 보내지 않습니다.')).toBeVisible();
  expect(screen.getByText('업무 설명 초안')).toBeVisible();
  expect(document.querySelector('script')).toBeNull();
});

it('renders redacted questions and task descriptions as absent', () => {
  const judgment: Judgment = { id: 'j', request_id: 'req', revision_id: 'rev', run_id: 'run', classifications: {}, risk_confirmed: false, risks: [], author: 'code', mode: 'live', versions: {}, outputs: [], review_reasons: [], review: null, summary: {}, questions: null, draft_tasks: [{ title: '업무' }] };
  render(<Result judgment={judgment} runs={null} onEvidence={vi.fn()} />);
  expect(screen.getByText('업무 분담')).toBeVisible();
  expect(screen.queryByText('추가로 확인하면 좋은 정보')).not.toBeInTheDocument();
});
