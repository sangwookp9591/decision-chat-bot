import type { Task } from '../../api/tasks';
import { blockReasonLabel } from '../../lib/labels';

const done = (status: unknown) => status === '완료' || status === 'completed';

/** What still keeps a task from starting; mirrors the server rule (the server stays the authority and answers 409). */
export function startBlockers(task: Task): string[] {
  const waiting = task.predecessor_tasks.filter((p) => !done(p.status));
  const codes = (task.block_reasons || []).filter((code) => code !== 'predecessor_incomplete' || waiting.length > 0);
  const items = codes.map(blockReasonLabel);
  if (waiting.length) items.push(`선행 업무 완료 필요: ${waiting.map((p) => p.title).join(', ')}`);
  if (task.reason) items.push(`본업무 전제 확인 필요: ${task.reason}`);
  return [...new Set(items)];
}
