import { useCallback, useEffect, useState } from 'react';
import { apiFetch, type ApiError } from '../api/client';
import { requestApi, type Judgment, type RequestDetail, type RequestItem } from '../api/requests';
import { useSession } from '../state/session';
import { Button, StatusBadge } from '../components';
import { getStatusPresentation } from '../components/statusLabels';
import './main/main.css';

const stageNames = ['내용 정리', 'Jev 판단', '근거 연결', '업무 나누기', '결과 저장'];
const labels: Record<string, string> = { ai_need: 'AI 필요성', feasibility: '개발 가능성', urgency: '긴급도', lead_org: '주관 조직' };
const classifications: Record<string, string[]> = { ai_need: ['필요', '불필요', '혼합'], feasibility: ['가능', '조건부 가능', '현재 불가'], urgency: ['긴급', '일반'], lead_org: ['AI팀', 'IT팀', '현업'] };
function errorMessage(error: unknown) { return (error as ApiError)?.message || '요청 처리 중 문제가 발생했습니다.'; }
function csrf() { return decodeURIComponent(document.cookie.split('; ').find((part) => part.startsWith('jev_csrf='))?.slice(9) || ''); }
function uploadRequest(data: FormData, onProgress: (value: number) => void, path = '/api/requests') {
  return new Promise<{ request_id: string; status: string; revision: number }>((resolve, reject) => {
    const xhr = new XMLHttpRequest(); xhr.open('POST', path); xhr.withCredentials = true;
    xhr.setRequestHeader('Idempotency-Key', crypto.randomUUID()); if (csrf()) xhr.setRequestHeader('X-CSRF-Token', csrf());
    xhr.upload.onprogress = (event) => { if (event.lengthComputable) onProgress(Math.round(event.loaded / event.total * 100)); };
    xhr.onerror = () => reject(new Error('서버에 연결할 수 없습니다.'));
    xhr.onload = () => { if (xhr.status >= 200 && xhr.status < 300) resolve(JSON.parse(xhr.responseText)); else reject(new Error('요청을 접수하지 못했습니다.')); };
    xhr.send(data);
  });
}

export function Main() {
  const { user } = useSession();
  const [text, setText] = useState(''); const [files, setFiles] = useState<File[]>([]); const [upload, setUpload] = useState<number | null>(null);
  const [requestId, setRequestId] = useState(''); const [detail, setDetail] = useState<RequestDetail | null>(null); const [judgment, setJudgment] = useState<Judgment | null>(null);
  const [runs, setRuns] = useState<Awaited<ReturnType<typeof requestApi.runs>> | null>(null); const [previousJudgment, setPreviousJudgment] = useState<Judgment | null>(null); const [stage, setStage] = useState(''); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const [requests, setRequests] = useState<RequestItem[]>([]); const [source, setSource] = useState(''); const [sourceTitle, setSourceTitle] = useState('');
  useEffect(() => { const queued = sessionStorage.getItem('chat:request'); if (queued) { setText(queued); sessionStorage.removeItem('chat:request'); } const receive = (event: Event) => { setText((event as CustomEvent<string>).detail || ''); document.getElementById('request-text')?.scrollIntoView({ behavior: 'smooth', block: 'center' }); }; window.addEventListener('chat:request', receive); return () => window.removeEventListener('chat:request', receive); }, []);
  useEffect(() => { if (!judgment) return; window.dispatchEvent(new CustomEvent('chat:result', { detail: { urgency: judgment.classifications.urgency, review: Boolean(judgment.review), summary: typeof judgment.summary === 'string' ? judgment.summary : judgment.summary.text } })); }, [judgment]);
  const refresh = useCallback(async (id: string) => {
    const current = await requestApi.detail(id); setDetail(current); let activeRunId = current.request.active_run_id;
    try { const result = await requestApi.judgment(id); setJudgment(result); activeRunId = result.run_id; setStage(''); }
    catch (problem) { if ((problem as ApiError)?.status !== 404) throw problem; }
    try { const history = await requestApi.runs(id); setRuns(history); const previous = history.runs.find((run) => run.id !== activeRunId); setPreviousJudgment(previous ? await requestApi.judgment(id, previous.id) : null); } catch { setPreviousJudgment(null); /* run history is optional for the initial result */ }
    if (['failed', 'cancelled', '실패'].includes(current.request.status)) setError('분석 실행이 실패했습니다. 결과가 저장되지 않았습니다.');
  }, []);
  useEffect(() => { requestApi.list().then((value) => setRequests(value.items)).catch(() => undefined); }, [requestId]);
  useEffect(() => {
    if (!requestId || judgment || error) return;
    let live = true; const sourceEvents = new EventSource('/api/events/stream');
    sourceEvents.addEventListener('run.step', (event) => { try { const parsed = JSON.parse((event as MessageEvent).data); if (parsed.request_id === requestId && parsed.step_name) setStage(({ '입력 정리': '내용 정리', '업무 분해': '업무 나누기' } as Record<string, string>)[parsed.step_name] || parsed.step_name); } catch { /* ignore malformed transient event */ } });
    const timer = window.setInterval(() => { if (live) refresh(requestId).catch((problem) => { setError(errorMessage(problem)); }); }, 1500);
    return () => { live = false; sourceEvents.close(); window.clearInterval(timer); };
  }, [requestId, judgment, error, refresh]);
  async function submit(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setError(''); setJudgment(null); setPreviousJudgment(null); setRuns(null); setDetail(null); setStage(''); setUpload(0);
    try { const form = new FormData(); form.append('text', text); files.forEach((file) => form.append('files', file)); const revising = detail?.request.status === 'needs_file_decision' && requestId; if (revising) form.append('expected_revision', String(detail.request.revision_number || detail.revisions.length)); const accepted = await uploadRequest(form, setUpload, revising ? `/api/requests/${requestId}/revisions` : '/api/requests'); const id = revising ? requestId : accepted.request_id; setRequestId(id); setText(''); setFiles([]); await refresh(id); }
    catch (problem) { setError(errorMessage(problem)); } finally { setBusy(false); setUpload(null); }
  }
  async function excludeUnread() {
    if (!detail || !requestId) return; const failed = detail.attachments.filter((file) => file.status !== 'ok').map((file) => file.id);
    setBusy(true); setError(''); try { const body = { exclude: failed, expected_revision: detail.request.revision_number || detail.revisions.length }; await apiFetch(`/api/requests/${requestId}/file-decision`, { method: 'POST', headers: { 'Idempotency-Key': crypto.randomUUID() }, body: JSON.stringify(body) }); setJudgment(null); setStage(''); await refresh(requestId); } catch (problem) { setError(errorMessage(problem)); } finally { setBusy(false); }
  }
  async function openRequest(id: string) { setRequestId(id); setJudgment(null); setPreviousJudgment(null); setRuns(null); setError(''); setStage(''); try { await refresh(id); } catch (problem) { setError(errorMessage(problem)); } }
  async function reanalyze() { if (!requestId || !detail) return; if (!window.confirm('현재 revision으로 새 분석 실행을 시작할까요? 기존 판단과 검토 기록은 보존됩니다.')) return; setBusy(true); setError(''); try { await requestApi.reanalyze(requestId, detail.request.revision_number || detail.revisions.length); setJudgment(null); setPreviousJudgment(null); setStage(''); setRuns(await requestApi.runs(requestId)); await refresh(requestId); } catch (problem) { setError(errorMessage(problem)); } finally { setBusy(false); } }
  async function openEvidence(output: Judgment['outputs'][number], evidence?: Judgment['outputs'][number]['evidence'][number]) { if (!evidence) { setSourceTitle(`${output.question_id} · 근거 위치`); setSource('이 판단에는 저장된 원문 위치 근거가 없습니다.'); return; } const sourceKind = evidence.source === 'chat' ? '채팅' : '첨부'; setSourceTitle(`${output.question_id} · ${sourceKind} · ${JSON.stringify(evidence.location)}`); setSource(evidence.source_text || '원문 열람 권한이 없어 위치 정보만 표시합니다.'); if (!evidence.source_text && requestId) try { const result = await requestApi.evidence(requestId, evidence.id); setSource(result.source_text || '원문 열람 권한이 없어 위치 정보만 표시합니다.'); } catch { setSource('원문 위치를 확인할 수 없습니다.'); } }
  return <section className="main-page"><div className="main-heading"><div><p className="eyebrow">요청자</p><h1>요청 접수와 판단 결과</h1></div>{judgment && <span className={`environment-badge mode-${judgment.mode}`}>{judgment.mode.toUpperCase()} 연결</span>}</div>
    <div className="main-columns"><div className="main-primary">
      <form className="intake-card" onSubmit={submit}><label htmlFor="request-text">요청 내용</label><textarea id="request-text" value={text} onChange={(event) => setText(event.target.value)} placeholder="필요한 업무와 해결하려는 문제를 적어 주세요" rows={5} />
        {files.length > 0 && <ul className="selected-files">{files.map((file, index) => <li key={`${file.name}-${index}`}>{file.name} · {Math.ceil(file.size / 1024)} KiB</li>)}</ul>}
        <div className="intake-actions"><label className="ui-button secondary attach-button">{detail?.request.status === 'needs_file_decision' ? '읽기 실패 파일 재첨부' : '파일 첨부'}<input aria-label="파일 첨부" type="file" accept=".pdf,.docx,.md" multiple onChange={(event) => setFiles(Array.from(event.target.files || []).slice(0, 5))} /></label><span>PDF · DOCX · MD, 최대 5개 · 파일당 10 MiB · 합계 25 MiB</span><button className="ui-button primary" type="submit" disabled={busy || (!text.trim() && files.length === 0)}>{detail?.request.status === 'needs_file_decision' ? '재첨부 후 새 revision' : '요청 보내기'}</button></div>
      </form>
      {upload !== null && <div className="progress-card" aria-live="polite"><strong>업로드 진행</strong><progress max="100" value={upload} /> <span>{upload}%</span></div>}
      {requestId && <article className="progress-card analysis-card"><div className="card-heading"><h2>분석 진행</h2>{detail && <StatusBadge status={error ? 'failure' : judgment?.review ? 'review' : judgment ? 'success' : 'progress'} label={judgment ? judgment.review ? '검토 대기' : '판단 저장 완료' : error ? '시스템 실패' : detail.request.status === 'needs_file_decision' ? '보완 필요 · 파일 선택' : '분석 중'} />}</div><ol className="stage-list">{stageNames.map((name, index) => <li key={name} className={name === stage ? 'current' : judgment ? 'done' : 'waiting'}><span>{judgment || stageNames.indexOf(stage) > index ? '✓' : index + 1}</span>{name}</li>)}</ol>{detail?.request.status === 'needs_file_decision' && <div className="file-decision"><p>읽지 못한 첨부가 있습니다. 제외하거나 다시 첨부한 뒤 분석을 진행해 주세요.</p><ul>{detail.attachments.filter((file) => file.status !== 'ok').map((file) => <li key={file.id}>{file.filename} — {file.reason || '읽기 실패'}</li>)}</ul><button className="ui-button primary" type="button" disabled={busy} onClick={excludeUnread}>실패 파일 제외 후 분석</button><span>재첨부는 아래 입력에서 새 revision으로 제출할 수 있습니다.</span></div>}</article>}
      {error && <div className="failure-card" role="alert"><StatusBadge status="failure" label="시스템 실패" /><p>{error}</p></div>}
      {judgment && <Result judgment={judgment} previousJudgment={previousJudgment} runs={runs} onEvidence={openEvidence} canReanalyze={Boolean(user?.roles.some((role) => ['requester', 'reviewer', 'operator'].includes(role)))} onReanalyze={() => void reanalyze()} />}
      {source && <aside className="source-panel"><div className="card-heading"><h2>근거 원문</h2><Button type="button" variant="plain" onClick={() => setSource('')}>닫기</Button></div><p>{sourceTitle}</p><blockquote>{source}</blockquote></aside>}
    </div><aside className="request-list"><h2>내 요청</h2>{requests.length ? requests.map((item) => { const state = getStatusPresentation(item.status); return <button type="button" key={item.id} onClick={() => openRequest(item.id)}><code>{item.id}</code><StatusBadge status={state.status} label={state.label} /></button>; }) : <p>접수한 요청이 여기에 표시됩니다.</p>}</aside></div>
  </section>;
}
export function Result({ judgment, previousJudgment, runs, onEvidence, canReanalyze = false, onReanalyze = () => undefined }: { judgment: Judgment; previousJudgment?: Judgment | null; runs: Awaited<ReturnType<typeof requestApi.runs>> | null; onEvidence: (output: Judgment['outputs'][number], evidence?: Judgment['outputs'][number]['evidence'][number]) => void; canReanalyze?: boolean; onReanalyze?: () => void }) {
  const summary = typeof judgment.summary === 'string' ? JSON.parse(judgment.summary) : judgment.summary;
  const selectedRun = runs?.runs.find((run) => run.id === judgment.run_id); const oldRun = runs?.runs.find((run) => run.id !== judgment.run_id);
  return <div className="result-stack"><article className="result-summary"><div className="card-heading"><h2>판단 결과</h2><StatusBadge status={judgment.review ? 'review' : 'success'} label={judgment.review ? '검토 대기' : '자동 처리 가능'} /><span className={`environment-badge mode-${judgment.mode}`}>{judgment.mode.toUpperCase()}</span></div><p className="summary-text">{summary.text || '요약 정보가 없습니다.'}</p><p className="author-line">원문 발췌 · 작성 주체: {summary.author || judgment.author || 'Jev'}</p><code>{judgment.run_id} · revision {judgment.revision_id}</code>{canReanalyze&&<button type="button" className="ui-button secondary" onClick={onReanalyze}>새 실행으로 다시 분석</button>}</article>
    <div className="judgment-grid">{Object.entries(judgment.classifications).map(([key, value]) => { const uncertain = ['정보 부족', '판단 보류', '미정'].includes(String(value)); const selected = String(value) === '조건부' ? '조건부 가능' : String(value); const related = judgment.outputs.filter((output) => output.question_id.includes(key)); return <article className="judgment-card" key={key}><h3>{labels[key] || key}</h3><div className="scale-options">{(classifications[key] || [String(value)]).map((choice) => <span key={choice} className={!uncertain && selected === choice ? 'selected' : ''}>{choice}</span>)}</div>{uncertain && <div className="uncertain-result"><strong>정보 부족·판단 보류</strong><span>{String(value)}</span></div>}<div className="signal-labels">{related.map((output) => <span key={output.id}>{output.confidence !== undefined && `Choice confidence ${(output.confidence * 100).toFixed(0)}%`}{output.noul !== undefined && `Noul 확률 ${JSON.stringify(output.noul)}`}</span>)}</div><div className="evidence-list">{related.length ? related.flatMap((output) => output.evidence.length ? output.evidence.map((evidence) => <button key={evidence.id} type="button" onClick={() => onEvidence(output, evidence)}>{evidence.source === 'chat' ? '채팅' : '첨부'} · {JSON.stringify(evidence.location)} 근거 열기</button>) : [<button key={`${output.id}-none`} type="button" onClick={() => onEvidence(output)}>저장된 근거 위치 없음 · 근거 패널 열기</button>]) : <span>저장된 근거 위치 없음</span>}</div></article>; })}</div>
    <article className="result-summary"><h2>업무 분담</h2>{judgment.draft_tasks.map((task, index) => <div className="task-row" key={String(task.id || index)}><strong>{String(task.title || '업무 미정')}</strong><span>{String(task.method || '방식 미정')} · 주관 {String(task.lead_org || '미정')}</span><span>협업 {Array.isArray(task.collab_orgs) ? task.collab_orgs.join(', ') || '없음' : '미정'} · 선행 {Array.isArray(task.predecessors) ? task.predecessors.join(', ') || '없음' : '미정'}</span></div>)}<p>검토 사유: {judgment.review_reasons.length ? judgment.review_reasons.map(String).join(' · ') : '추가 검토 사유 없음'}</p></article>
    {oldRun && <article className="result-summary"><h2>이전 실행 비교</h2><p>현재 {selectedRun?.id} ({JSON.stringify(selectedRun?.versions || {})}) · 이전 {oldRun.id} ({JSON.stringify(oldRun.versions)})</p>{previousJudgment ? <ul>{Object.entries(judgment.classifications).map(([key, current]) => <li key={key}>{labels[key] || key}: {String(previousJudgment.classifications[key] ?? '—')} → {String(current)}{String(previousJudgment.classifications[key]) === String(current) ? ' (변경 없음)' : ' (변경)'}</li>)}</ul> : <p>이전 실행의 저장 결과가 없어 버전 정보만 표시합니다.</p>}</article>}
  </div>;
}
