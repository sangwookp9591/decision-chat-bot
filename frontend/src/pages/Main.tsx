import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { apiFetch, csrfToken, idempotencyKey, type ApiError } from '../api/client';
import { requestApi, type Judgment, type RequestDetail, type RequestItem } from '../api/requests';
import { useSession } from '../state/session';
import { Button, StatusBadge, type StatusKind } from '../components';
import { attachmentReasonLabel, getStatusPresentation } from '../components/statusLabels';
import { infoRequest, needsInfo, resultBadge } from './main/requestState';
import { useEventStream } from '../state/events';
import { EvidenceViewer, type ViewerTarget } from '../components/EvidenceViewer';
import { RawDetails } from '../components/RawDetails';
import { locationLabel, questionLabel, reviewReasonLabel } from '../lib/labels';
import './main/main.css';

const stageNames = ['내용 정리', 'Jev 판단', '근거 연결', '업무 나누기', '결과 저장'];
const labels: Record<string, string> = { ai_need: 'AI 필요성', feasibility: '개발 가능성', urgency: '긴급도', lead_org: '주관 조직' };
const classifications: Record<string, string[]> = { ai_need: ['필요', '불필요', '혼합'], feasibility: ['가능', '조건부 가능', '현재 불가'], urgency: ['긴급', '일반'], lead_org: ['AI팀', 'IT팀', '현업'] };
function errorMessage(error: unknown) { return (error as ApiError)?.message || '요청 처리 중 문제가 발생했습니다.'; }
function uploadRequest(data: FormData, onProgress: (value: number) => void, path = '/api/requests') {
  return new Promise<{ request_id: string; status: string; revision: number }>((resolve, reject) => {
    const xhr = new XMLHttpRequest(); xhr.open('POST', path); xhr.withCredentials = true;
    xhr.setRequestHeader('Idempotency-Key', idempotencyKey()['Idempotency-Key']); const token = csrfToken(); if (token) xhr.setRequestHeader('X-CSRF-Token', token);
    xhr.upload.onprogress = (event) => { if (event.lengthComputable) onProgress(Math.round(event.loaded / event.total * 100)); };
    xhr.onerror = () => reject(new Error('서버에 연결할 수 없습니다.'));
    xhr.onload = () => { if (xhr.status >= 200 && xhr.status < 300) resolve(JSON.parse(xhr.responseText)); else reject(new Error('요청을 접수하지 못했습니다.')); };
    xhr.send(data);
  });
}

export function Main() {
  const { user } = useSession();
  const [text, setText] = useState(''); const [files, setFiles] = useState<File[]>([]); const [upload, setUpload] = useState<number | null>(null);
  const [params, setParams] = useSearchParams(); const requestId = params.get('request_id') || ''; const [notice, setNotice] = useState('');
  const [detail, setDetail] = useState<RequestDetail | null>(null); const [judgment, setJudgment] = useState<Judgment | null>(null);
  const [runs, setRuns] = useState<Awaited<ReturnType<typeof requestApi.runs>> | null>(null); const [previousJudgment, setPreviousJudgment] = useState<Judgment | null>(null); const [stage, setStage] = useState(''); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const [requests, setRequests] = useState<RequestItem[]>([]); const [source, setSource] = useState(''); const [sourceTitle, setSourceTitle] = useState(''); const [viewer, setViewer] = useState<ViewerTarget | null>(null);
  const resetRun = () => { setJudgment(null); setPreviousJudgment(null); setRuns(null); setStage(''); };
  const info = infoRequest(detail);
  const revisionNumber = detail?.request.revision_number || detail?.revisions.length || 0;
  useEffect(() => {
    // Text from the chat widget lands in the intake form right away (also when it was sent from another page).
    const receive = (message: string) => { if (!message.trim()) return; setText((current) => current.trim() ? `${current.trim()}\n${message}` : message); setNotice('채팅 내용을 요청 입력에 옮겼습니다. 내용을 확인한 뒤 "요청 보내기"를 눌러 주세요.'); window.setTimeout(() => { const field = document.getElementById('request-text') as HTMLTextAreaElement | null; field?.scrollIntoView?.({ behavior: 'smooth', block: 'center' }); field?.focus(); }, 0); };
    const queued = sessionStorage.getItem('chat:request'); if (queued) { sessionStorage.removeItem('chat:request'); receive(queued); }
    const listener = (event: Event) => receive(String((event as CustomEvent<string>).detail || ''));
    window.addEventListener('chat:request', listener); return () => window.removeEventListener('chat:request', listener);
  }, []);
  useEffect(() => { if (!judgment) return; window.dispatchEvent(new CustomEvent('chat:result', { detail: { urgency: judgment.classifications.urgency, review: Boolean(judgment.review), summary: typeof judgment.summary === 'string' ? judgment.summary : judgment.summary.text } })); }, [judgment]);
  const refresh = useCallback(async (id: string) => {
    const [current, judgmentResult, history] = await Promise.all([
      requestApi.detail(id),
      requestApi.judgment(id).then((value) => ({ value }), (reason: unknown) => ({ reason })),
      requestApi.runs(id).then((value) => ({ value }), () => ({ value: null })),
    ]);
    setDetail(current); let activeRunId = current.request.active_run_id;
    if ('value' in judgmentResult) { setJudgment(judgmentResult.value); activeRunId = judgmentResult.value.run_id; setStage(''); }
    else if ((judgmentResult.reason as ApiError)?.status !== 404) throw judgmentResult.reason;
    if ('value' in history && history.value) {
      setRuns(history.value); const previous = history.value.runs.find((run) => run.id !== activeRunId);
      try { setPreviousJudgment(previous ? await requestApi.judgment(id, previous.id) : null); } catch { setPreviousJudgment(null); }
    } else { setRuns(null); setPreviousJudgment(null); }
    if (['failed', 'cancelled', '실패'].includes(current.request.status)) setError('분석 실행이 실패했습니다. 결과가 저장되지 않았습니다.');
  }, []);
  useEffect(() => { requestApi.list().then((value) => setRequests(value.items)).catch(() => undefined); }, [requestId, detail?.request.status]);
  const inFlight = useRef(false);
  const load = useCallback((id: string) => {
    if (!id || inFlight.current) return;
    inFlight.current = true;
    void refresh(id).catch((problem) => setError(errorMessage(problem))).finally(() => { inFlight.current = false; });
  }, [refresh]);
  const refreshIfPending = useCallback((id: string) => { if (!judgment && !error) load(id); }, [judgment, error, load]);
  // A saved judgment is not final: review decisions, info requests and assignments keep changing the request status.
  const onStreamEvent = useCallback((event: { type: string; step_name?: string }) => {
    if (event.type === 'run.step' && event.step_name) setStage(({ '입력 정리': '내용 정리', '업무 분해': '업무 나누기' } as Record<string, string>)[event.step_name] || event.step_name);
    if (['review_decided', 'assignment_created', 'auto_assignment_deferred', 'reanalysis.compared'].includes(event.type)) load(requestId);
    else refreshIfPending(requestId);
  }, [refreshIfPending, load, requestId]);
  useEventStream({ requestId: requestId || undefined, enabled: Boolean(requestId) }, undefined, onStreamEvent, () => load(requestId));
  useEffect(() => {
    // The selected request lives in the URL (?request_id=), so reload / back / shared links restore it.
    resetRun(); setDetail(null); setError('');
    if (requestId) load(requestId);
  }, [requestId]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!requestId || judgment || error) return;
    const timer = window.setInterval(() => refreshIfPending(requestId), 10000);
    return () => window.clearInterval(timer);
  }, [requestId, judgment, error, refreshIfPending]);
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true); setError(''); setNotice(''); resetRun(); setUpload(0);
    try {
      const form = new FormData();
      form.append('text', text);
      files.forEach((file) => form.append('files', file));
      const revising = Boolean(requestId) && (detail?.request.status === 'needs_file_decision' || needsInfo(detail?.request.status));
      if (revising) form.append('expected_revision', String(revisionNumber));
      const path = revising ? `/api/requests/${requestId}/revisions` : '/api/requests';
      const accepted = await uploadRequest(form, setUpload, path);
      const id = revising ? requestId : accepted.request_id;
      setText(''); setFiles([]);
      if (id === requestId) await refresh(id); else { setDetail(null); setParams({ request_id: id }); }
    } catch (problem) {
      setError(errorMessage(problem));
    } finally {
      setBusy(false); setUpload(null);
    }
  }
  async function excludeUnread() {
    if (!detail || !requestId) return;
    const failed = detail.attachments.filter((file) => file.status !== 'ok').map((file) => file.id);
    setBusy(true); setError('');
    try {
      const body = { exclude: failed, expected_revision: revisionNumber };
      await apiFetch(`/api/requests/${requestId}/file-decision`, {
        method: 'POST', headers: idempotencyKey(), body: JSON.stringify(body),
      });
      resetRun(); await refresh(requestId);
    } catch (problem) {
      setError(errorMessage(problem));
    } finally {
      setBusy(false);
    }
  }
  function openRequest(id: string) { if (id !== requestId) setParams({ request_id: id }); }
  async function reanalyze() {
    if (!requestId || !detail) return;
    if (!window.confirm('현재 revision으로 새 분석 실행을 시작할까요? 기존 판단과 검토 기록은 보존됩니다.')) return;
    setBusy(true); setError('');
    try {
      await requestApi.reanalyze(requestId, revisionNumber);
      resetRun(); setRuns(await requestApi.runs(requestId));
      await refresh(requestId);
    } catch (problem) {
      setError(errorMessage(problem));
    } finally {
      setBusy(false);
    }
  }
  function openEvidence(output: Judgment['outputs'][number], evidence?: Judgment['outputs'][number]['evidence'][number]) {
    if (!evidence || !requestId || !judgment) { setSourceTitle(`${questionLabel(output.question_id)} · 근거 위치`); setSource('이 판단에는 저장된 원문 위치 근거가 없습니다.'); return; }
    setSource(''); setViewer({ requestId, revision: judgment.revision_id, source: evidence.attachment_id || 'chat', unitId: evidence.id, title: `${questionLabel(output.question_id)} · 근거 원문` });
  }
  return <section className="main-page"><div className="main-heading"><div><p className="eyebrow">요청자</p><h1>요청 접수와 판단 결과</h1></div>{judgment && <span className={`environment-badge mode-${judgment.mode}`}>{judgment.mode.toUpperCase()} 연결</span>}</div>
    <div className="main-columns"><div className="main-primary">
      <form className="intake-card" onSubmit={submit}><label htmlFor="request-text">요청 내용</label><textarea id="request-text" value={text} onChange={(event) => setText(event.target.value)} placeholder="필요한 업무와 해결하려는 문제를 적어 주세요" rows={5} />
        {files.length > 0 && <ul className="selected-files">{files.map((file, index) => <li key={`${file.name}-${index}`}>{file.name} · {Math.ceil(file.size / 1024)} KiB</li>)}</ul>}
        <div className="intake-actions"><label className="ui-button secondary attach-button">{detail?.request.status === 'needs_file_decision' ? '읽기 실패 파일 재첨부' : '파일 첨부'}<input aria-label="파일 첨부" type="file" accept=".pdf,.docx,.md" multiple onChange={(event) => setFiles(Array.from(event.target.files || []).slice(0, 5))} /></label><span>PDF · DOCX · MD, 최대 5개 · 파일당 10 MiB · 합계 25 MiB</span><button className="ui-button primary" type="submit" disabled={busy || (!text.trim() && files.length === 0)}>{detail?.request.status === 'needs_file_decision' ? '재첨부 후 새 revision' : needsInfo(detail?.request.status) ? '보완 내용 제출 (새 revision)' : '요청 보내기'}</button></div>
      </form>
      {notice && <p className="chat-handoff" role="status">{notice}</p>}
      {upload !== null && <div className="progress-card" aria-live="polite"><strong>업로드 진행</strong><progress max="100" value={upload} /> <span>{upload}%</span></div>}
      {requestId && <article className="progress-card analysis-card"><div className="card-heading"><h2>분석 진행</h2>{detail && <StatusBadge {...resultBadge(detail, judgment, Boolean(error))} />}</div><ol className="stage-list">{stageNames.map((name, index) => <li key={name} className={name === stage ? 'current' : judgment ? 'done' : 'waiting'}><span>{judgment || stageNames.indexOf(stage) > index ? '✓' : index + 1}</span>{name}</li>)}</ol>{detail?.request.status === 'needs_file_decision' && <div className="file-decision"><p>읽지 못한 첨부가 있습니다. 제외하거나 다시 첨부한 뒤 분석을 진행해 주세요.</p><ul>{detail.attachments.filter((file) => file.status !== 'ok').map((file) => <li key={file.id}>{file.filename} — {attachmentReasonLabel(file.reason)}</li>)}</ul><button className="ui-button primary" type="button" disabled={busy} onClick={excludeUnread}>실패 파일 제외 후 분석</button><span>재첨부는 아래 입력에서 새 revision으로 제출할 수 있습니다.</span></div>}{info && <div className="info-request" role="region" aria-label="보완 요청"><h3>검토자가 보완을 요청했습니다</h3><p>{info.reason || '보완이 필요한 내용을 확인해 주세요.'}</p>{info.needed.length > 0 && <ul>{info.needed.map((item) => <li key={item}>{item}</li>)}</ul>}<button type="button" className="ui-button primary" onClick={() => document.getElementById('request-text')?.focus()}>보완 내용 입력하기</button><span>아래 입력에 내용을 보완해 &quot;보완 내용 제출&quot;을 누르면 같은 요청의 새 revision으로 접수되어 다시 분석합니다.</span></div>}</article>}
      {error && <div className="failure-card" role="alert"><StatusBadge status="failure" label="시스템 실패" /><p>{error}</p></div>}
      {judgment && <Result judgment={judgment} previousJudgment={previousJudgment} runs={runs} onEvidence={openEvidence} state={resultBadge(detail, judgment, false)} canReanalyze={Boolean(user?.roles.some((role) => ['requester', 'reviewer', 'operator'].includes(role)))} onReanalyze={() => void reanalyze()} />}
      <EvidenceViewer target={viewer} onClose={() => setViewer(null)} />{source && <aside className="source-panel"><div className="card-heading"><h2>근거 원문</h2><Button type="button" variant="plain" onClick={() => setSource('')}>닫기</Button></div><p>{sourceTitle}</p><blockquote>{source}</blockquote></aside>}
    </div><aside className="request-list"><h2>내 요청</h2>{requests.length ? requests.map((item) => { const state = getStatusPresentation(item.status); return <button type="button" key={item.id} onClick={() => openRequest(item.id)} aria-current={item.id === requestId ? 'true' : undefined}><code>{item.id}</code><StatusBadge status={state.status} label={state.label} /></button>; }) : <p>접수한 요청이 여기에 표시됩니다.</p>}</aside></div>
  </section>;
}
export function Result({ judgment, previousJudgment, runs, onEvidence, state, canReanalyze = false, onReanalyze = () => undefined }: { judgment: Judgment; state?: { status: StatusKind; label: string }; previousJudgment?: Judgment | null; runs: Awaited<ReturnType<typeof requestApi.runs>> | null; onEvidence: (output: Judgment['outputs'][number], evidence?: Judgment['outputs'][number]['evidence'][number]) => void; canReanalyze?: boolean; onReanalyze?: () => void }) {
  const summary = typeof judgment.summary === 'string' ? JSON.parse(judgment.summary) : judgment.summary;
  const selectedRun = runs?.runs.find((run) => run.id === judgment.run_id); const oldRun = runs?.runs.find((run) => run.id !== judgment.run_id);
  return <div className="result-stack"><article className="result-summary"><div className="card-heading"><h2>판단 결과</h2><StatusBadge {...(state ?? { status: judgment.review ? 'review' : 'success', label: judgment.review ? '검토 대기' : '자동 처리 가능' })} /><span className={`environment-badge mode-${judgment.mode}`}>{judgment.mode.toUpperCase()}</span></div><p className="summary-text">{summary.text || '요약 정보가 없습니다.'}</p><p className="author-line">원문 발췌 · 작성 주체: {summary.author || judgment.author || 'Jev'}</p><code>{judgment.run_id} · revision {judgment.revision_id}</code>{canReanalyze&&<button type="button" className="ui-button secondary" onClick={onReanalyze}>새 실행으로 다시 분석</button>}</article>
    <div className="judgment-grid">{Object.entries(judgment.classifications).map(([key, value]) => { const uncertain = ['정보 부족', '판단 보류', '미정'].includes(String(value)); const selected = String(value) === '조건부' ? '조건부 가능' : String(value); const related = judgment.outputs.filter((output) => output.question_id.includes(key)); return <article className="judgment-card" key={key}><h3>{labels[key] || key}</h3><div className="scale-options">{(classifications[key] || [String(value)]).map((choice) => <span key={choice} className={!uncertain && selected === choice ? 'selected' : ''}>{choice}</span>)}</div>{uncertain && <div className="uncertain-result"><strong>정보 부족·판단 보류</strong><span>{String(value)}</span></div>}<div className="signal-labels">{related.map((output) => <span key={output.id}>{output.confidence !== undefined && `선택 신뢰도 ${(output.confidence * 100).toFixed(0)}%`}{output.noul !== undefined && `Noul 확률 ${JSON.stringify(output.noul)}`}</span>)}</div><div className="evidence-list">{related.length ? related.flatMap((output) => output.evidence.length ? output.evidence.map((evidence) => <button key={evidence.id} type="button" onClick={() => onEvidence(output, evidence)}>{evidence.source === 'chat' ? '채팅' : '첨부'} · {locationLabel(evidence.location)} 근거 열기</button>) : [<button key={`${output.id}-none`} type="button" onClick={() => onEvidence(output)}>저장된 근거 위치 없음 · 근거 패널 열기</button>]) : <span>저장된 근거 위치 없음</span>}</div></article>; })}</div>
    <article className="result-summary"><h2>업무 분담</h2>{judgment.draft_tasks.map((task, index) => <div className="task-row" key={String(task.id || index)}><strong>{String(task.title || '업무 미정')}</strong><span>{String(task.method || '방식 미정')} · 주관 {String(task.lead_org || '미정')}</span><span>협업 {Array.isArray(task.collab_orgs) ? task.collab_orgs.join(', ') || '없음' : '미정'} · 선행 {Array.isArray(task.predecessors) ? task.predecessors.join(', ') || '없음' : '미정'}</span></div>)}<p>검토 사유: {judgment.review_reasons.length ? judgment.review_reasons.map((reason) => reviewReasonLabel(String(reason))).join(' · ') : '추가 검토 사유 없음'}</p>{judgment.review_reasons.length > 0 && <RawDetails>{judgment.review_reasons.map(String).join('\n')}</RawDetails>}</article>
    {oldRun && <article className="result-summary"><h2>이전 실행 비교</h2><p>현재 실행 {selectedRun?.id} · 이전 실행 {oldRun.id}</p><RawDetails label="버전 정보 자세히">{{ current: selectedRun?.versions || {}, previous: oldRun.versions }}</RawDetails>{previousJudgment ? <ul>{Object.entries(judgment.classifications).map(([key, current]) => <li key={key}>{labels[key] || key}: {String(previousJudgment.classifications[key] ?? '—')} → {String(current)}{String(previousJudgment.classifications[key]) === String(current) ? ' (변경 없음)' : ' (변경)'}</li>)}</ul> : <p>이전 실행의 저장 결과가 없어 버전 정보만 표시합니다.</p>}</article>}
  </div>;
}
