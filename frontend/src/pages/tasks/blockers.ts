import type { Task } from '../../api/tasks';
import { blockReasonLabel, displayCodeLabel } from '../../lib/labels';

/** Format the blocker codes calculated by the server for display. */
export function startBlockers(task: Task): string[] {
  return (task.start_blockers || []).map((code) => {
    if (code.startsWith('reason:')) return `본업무 전제 확인 필요: ${displayCodeLabel(code.slice(7))}`;
    return blockReasonLabel(code);
  });
}
