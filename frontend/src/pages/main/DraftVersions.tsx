export type DraftTaskView = Record<string, unknown>;
export type DraftVersionView = { draft_version: number; source?: string; created_by?: string; created_at?: string | null; tasks: DraftTaskView[] };

const TRACKED: Array<[string, string]> = [['title', '업무명'], ['method', '방식'], ['lead_org', '주관'], ['collab_orgs', '협업'], ['predecessors', '선행'], ['deliverable', '산출물']];
const same = (a: unknown, b: unknown) => JSON.stringify(a ?? null) === JSON.stringify(b ?? null);

export const sourceLabel = (source?: string) => (source === 'reviewer' ? '검토자 수정안' : 'AI 원안');

export function draftTaskLine(task: DraftTaskView) {
  const list = (value: unknown) => (Array.isArray(value) ? value.join(', ') || '없음' : '미정');
  return { title: String(task.title || '업무 미정'), meta: `${String(task.method || '방식 미정')} · 주관 ${String(task.lead_org || '미정')}`, sub: `협업 ${list(task.collab_orgs)} · 선행 ${list(task.predecessors)}` };
}

/** 원안(v1) 대비 바뀐 항목 이름. 같은 draft_task_id가 원안에 없으면 '새 업무'. */
export function changedFields(task: DraftTaskView, original?: DraftTaskView): string[] {
  if (!original) return ['새 업무'];
  return TRACKED.filter(([key]) => !same(task[key], original[key])).map(([, label]) => label);
}

export function DraftVersionCompare({ versions, currentVersion }: { versions: DraftVersionView[]; currentVersion?: number | null }) {
  if (versions.length < 2) return null;
  const original = versions[0];
  return <details className="draft-compare"><summary>원안과 비교 ({versions.length}개 버전)</summary>
    {versions.map((version) => <section key={version.draft_version} className="draft-version" data-draft-version={version.draft_version}>
      <h3>v{version.draft_version} · {sourceLabel(version.source)}{version.draft_version === currentVersion ? ' (현재 적용)' : ''}</h3>
      <small>{version.source === 'reviewer' ? '검토자 수정' : 'AI 자동 생성'}</small>
      {version.tasks.map((task, index) => { const line = draftTaskLine(task); const diff = version === original ? [] : changedFields(task, original.tasks.find((t) => t.draft_task_id === task.draft_task_id));
        return <div className="task-row" key={String(task.id || index)}><strong>{line.title}</strong><span>{line.meta}</span><span>{line.sub}</span>{diff.length > 0 && <span className="draft-changed">원안 대비 변경: {diff.join(', ')}</span>}</div>; })}
    </section>)}
  </details>;
}
