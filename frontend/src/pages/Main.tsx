import { useCallback, useEffect, useReducer, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { apiFetch, idempotencyKey, type ApiError } from '../api/client';
import { requestApi, type Judgment, type RequestDetail, type RequestItem } from '../api/requests';
import { useSession } from '../state/session';
import { Button, StatusBadge } from '../components';
import { getStatusPresentation } from '../components/statusLabels';
import { infoRequest, resultBadge } from './main/requestState';
import { useEventStream, type StreamEvent } from '../state/events';
import { EvidenceViewer, type ViewerTarget } from '../components/EvidenceViewer';
import { questionLabel } from '../lib/labels';
import { uploadRequest } from './main/uploadRequest';
import { ProvisionalResult, SlowNotice, stepLabel } from './main/ProgressivePanel';
import { Result } from './main/ResultCard';
import { AnalysisBubble, AssistantBubble, FailureBubble, FileDecisionBubble, Greeting, InfoRequestBubble, QuickReplies, UploadBubble, UserBubble, moodAvatar } from './main/Bubbles';
import { Composer } from './main/Composer';
import { MAX_FILES, MOOD_TEXT, composerMode, currentAttachments, judgmentMood, resultMood, userMessages, type PendingSend } from './main/conversation';
import { initialProgress, progressReducer } from '../state/progress';
import './main/main.css';

export { Result } from './main/ResultCard';
const LIST_EVENTS = ['request.received', 'judgment_saved', 'judgment_failed', 'review_decided', 'assignment_created', 'auto_assignment_deferred', 'task.transitioned', 'reanalysis.compared'];
const stageNames = ['내용 정리', 'Jev 판단', '근거 연결', '업무 나누기', '결과 저장'];
function errorMessage(error: unknown) { return (error as ApiError)?.message || '요청 처리 중 문제가 발생했습니다.'; }

/** 요청 접수 = 일동이와의 대화. Everything the user sees is a message derived from server state, so a reload (?request_id=) restores it. */
export function Main() {
  const { user } = useSession();
  const [text, setText] = useState(''); const [files, setFiles] = useState<File[]>([]); const [upload, setUpload] = useState<number | null>(null);
  const [params, setParams] = useSearchParams(); const requestId = params.get('request_id') || '';
  const [detail, setDetail] = useState<RequestDetail | null>(null); const [judgment, setJudgment] = useState<Judgment | null>(null);
  const [runs, setRuns] = useState<Awaited<ReturnType<typeof requestApi.runs>> | null>(null); const [previousJudgment, setPreviousJudgment] = useState<Judgment | null>(null);
  const [progress, dispatch] = useReducer(progressReducer, initialProgress); const progressRef = useRef(progress); progressRef.current = progress;
  const [error, setError] = useState(''); const [retry, setRetry] = useState<'' | 'submit' | 'reanalyze'>(''); const [busy, setBusy] = useState(false); const [notice, setNotice] = useState('');
  const [pending, setPending] = useState<PendingSend | null>(null); const [listOpen, setListOpen] = useState(false);
  const [requests, setRequests] = useState<RequestItem[]>([]); const [source, setSource] = useState(''); const [sourceTitle, setSourceTitle] = useState(''); const [viewer, setViewer] = useState<ViewerTarget | null>(null);
  const textRef = useRef<HTMLTextAreaElement>(null); const attachRef = useRef<HTMLInputElement>(null); const endRef = useRef<HTMLDivElement>(null);
  const resetRun = () => { setJudgment(null); setPreviousJudgment(null); setRuns(null); };
  const canReanalyze = Boolean(user?.roles.some((role) => ['requester', 'reviewer', 'operator'].includes(role)));
  const stage = stepLabel(progress.currentStep);
  const info = infoRequest(detail);
  const mode = composerMode(detail);
  const stepDone = (name: string, index: number) => Boolean(judgment) || progress.phase === 'final' || stageNames.indexOf(stage) > index || progress.steps.some((step) => stepLabel(step.name) === name && step.status === 'succeeded');
  const revisionNumber = detail?.request.revision_number || detail?.revisions.length || 0;
  const messages = userMessages(detail, pending);

  const restoreProgress = useCallback((id: string) => { void Promise.resolve().then(() => requestApi.progress(id)).then((snapshot) => dispatch({ type: 'restore', progress: snapshot })).catch(() => undefined); }, []);
  const refresh = useCallback(async (id: string) => {
    const [current, judgmentResult, history] = await Promise.all([
      requestApi.detail(id),
      requestApi.judgment(id).then((value) => ({ value }), (reason: unknown) => ({ reason })),
      requestApi.runs(id).then((value) => ({ value }), () => ({ value: null })),
    ]);
    setDetail(current); let activeRunId = current.request.active_run_id;
    if ('value' in judgmentResult) { setJudgment(judgmentResult.value); activeRunId = judgmentResult.value.run_id; }
    else if ((judgmentResult.reason as ApiError)?.status !== 404) throw judgmentResult.reason;
    else restoreProgress(id); // still running: rebuild the step timeline and provisional cards from the progress API
    if ('value' in history && history.value) {
      setRuns(history.value); const previous = history.value.runs.find((run) => run.id !== activeRunId);
      try { setPreviousJudgment(previous ? await requestApi.judgment(id, previous.id) : null); } catch { setPreviousJudgment(null); }
    } else { setRuns(null); setPreviousJudgment(null); }
    if (['failed', 'cancelled', '실패'].includes(current.request.status)) setError('분석 실행이 실패했습니다. 결과가 저장되지 않았습니다.');
  }, [restoreProgress]);
  const reloadList = useCallback(() => { requestApi.list().then((value) => setRequests(value.items)).catch(() => undefined); }, []);
  useEffect(() => { reloadList(); }, [requestId, detail?.request.status, reloadList]);
  // The conversation list follows tenant-wide events on its own stream (the detail stream below only exists once a request is open):
  // requests created in another tab show up without a reload. The server scopes the list, so events only say "refetch".
  const listTimer = useRef<number>();
  const onListEvent = useCallback((event: StreamEvent) => {
    if (!LIST_EVENTS.includes(event.type)) return;
    window.clearTimeout(listTimer.current); listTimer.current = window.setTimeout(reloadList, 400);
  }, [reloadList]);
  useEffect(() => () => window.clearTimeout(listTimer.current), []);
  useEventStream({}, undefined, onListEvent, reloadList);
  const inFlight = useRef(false);
  const load = useCallback((id: string) => {
    if (!id || inFlight.current) return;
    inFlight.current = true;
    void refresh(id).catch((problem) => setError(errorMessage(problem))).finally(() => { inFlight.current = false; });
  }, [refresh]);
  const refreshIfPending = useCallback((id: string) => { if (!judgment && !error) load(id); }, [judgment, error, load]);
  // A saved judgment is not final: review decisions, info requests and assignments keep changing the request status.
  const onStreamEvent = useCallback((event: StreamEvent) => {
    dispatch({ type: 'event', event });
    if (['review_decided', 'assignment_created', 'auto_assignment_deferred', 'reanalysis.compared'].includes(event.type)) load(requestId);
    else if (['request.received', 'judgment_saved', 'judgment_failed'].includes(event.type)) refreshIfPending(requestId);
  }, [refreshIfPending, load, requestId]);
  useEventStream({ requestId: requestId || undefined, enabled: Boolean(requestId) }, undefined, onStreamEvent, () => load(requestId));
  useEffect(() => {
    // The open conversation lives in the URL (?request_id=), so reload / back / shared links restore it.
    resetRun(); setDetail(null); setError(''); setRetry(''); setNotice('');
    if (progressRef.current.requestId !== requestId) dispatch({ type: 'reset' }); // an optimistic send just confirmed with this id keeps its state
    if (requestId) load(requestId);
  }, [requestId]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (progress.phase === 'failed' && !judgment) { setError('분석 실행이 실패했습니다. 결과가 저장되지 않았습니다.'); setRetry('reanalyze'); } }, [progress.phase, judgment]);
  useEffect(() => {
    if (!requestId || judgment || error) return;
    const timer = window.setInterval(() => refreshIfPending(requestId), 10000);
    return () => window.clearInterval(timer);
  }, [requestId, judgment, error, refreshIfPending]);
  // Follow the newest message — only when one is added, never when a card fills in place (that would move what is being read).
  const tail = [messages.length, upload !== null, Boolean(detail), Boolean(judgment), Boolean(error), mode, progress.phase === 'preliminary'].join('|');
  useEffect(() => { if (tail !== '0|false|false|false|false|new|false') endRef.current?.scrollIntoView?.({ block: 'end' }); }, [tail]);

  function addFiles(added: File[]) {
    if (!added.length) return;
    const next = [...files, ...added.filter((file) => !files.some((old) => old.name === file.name && old.size === file.size))];
    setFiles(next.slice(0, MAX_FILES));
    setNotice(next.length > MAX_FILES ? `파일은 최대 ${MAX_FILES}개까지 첨부할 수 있어요. 앞에서부터 ${MAX_FILES}개만 담았어요.` : '');
  }
  async function submit() {
    const revising = Boolean(requestId) && mode !== 'new';
    const sent = { text, files };
    setBusy(true); setError(''); setRetry(''); setNotice(''); resetRun(); setUpload(0);
    setPending({ text: text.trim(), files: files.map((file) => file.name), baseRevision: revising ? revisionNumber : 0, requestId: revising ? requestId : '' });
    dispatch({ type: 'optimistic', text: text.trim() || files.map((file) => file.name).join(', '), at: Date.now() });
    setText(''); setFiles([]);
    try {
      const form = new FormData();
      form.append('text', sent.text);
      sent.files.forEach((file) => form.append('files', file));
      if (revising) form.append('expected_revision', String(revisionNumber));
      const accepted = await uploadRequest(form, setUpload, revising ? `/api/requests/${requestId}/revisions` : '/api/requests');
      const id = revising ? requestId : accepted.request_id;
      dispatch({ type: 'accepted', requestId: id });
      setPending((current) => (current ? { ...current, requestId: id } : current));
      if (id === requestId) await refresh(id); else { setDetail(null); setParams({ request_id: id }); }
    } catch (problem) {
      // Roll back: the bubble goes away and the draft returns to the composer, with the cause and a retry.
      dispatch({ type: 'rejected', message: errorMessage(problem) }); setPending(null); setText(sent.text); setFiles(sent.files);
      setError(errorMessage(problem)); setRetry('submit');
    } finally {
      setBusy(false); setUpload(null);
    }
  }
  async function excludeUnread() {
    if (!detail || !requestId) return;
    const failed = currentAttachments(detail).filter((file) => file.status !== 'ok').map((file) => file.id);
    setBusy(true); setError('');
    try {
      await apiFetch(`/api/requests/${requestId}/file-decision`, { method: 'POST', headers: idempotencyKey(), body: JSON.stringify({ exclude: failed, expected_revision: revisionNumber }) });
      resetRun(); await refresh(requestId);
    } catch (problem) { setError(errorMessage(problem)); } finally { setBusy(false); }
  }
  function openRequest(id: string) { setListOpen(false); setPending(null); if (id !== requestId) setParams({ request_id: id }); }
  function startNew() {
    setListOpen(false); setPending(null); setText(''); setFiles([]); setNotice('');
    if (requestId) setParams({}); else { resetRun(); setError(''); dispatch({ type: 'reset' }); }
    window.setTimeout(() => textRef.current?.focus(), 0);
  }
  function pickExample(example: string) { setText(example); window.setTimeout(() => textRef.current?.focus(), 0); }
  async function reanalyze() {
    if (!requestId || !detail) return;
    if (!window.confirm('현재 revision으로 새 분석 실행을 시작할까요? 기존 판단과 검토 기록은 보존됩니다.')) return;
    setBusy(true); setError('');
    try {
      await requestApi.reanalyze(requestId, revisionNumber);
      resetRun(); dispatch({ type: 'reset' }); setRuns(await requestApi.runs(requestId));
      await refresh(requestId);
    } catch (problem) { setError(errorMessage(problem)); } finally { setBusy(false); }
  }
  function openEvidence(output: Judgment['outputs'][number], evidence?: Judgment['outputs'][number]['evidence'][number]) {
    if (!evidence || !requestId || !judgment) { setSourceTitle(`${questionLabel(output.question_id)} · 근거 위치`); setSource('이 판단에는 저장된 원문 위치 근거가 없습니다.'); return; }
    setSource(''); setViewer({ requestId, revision: judgment.revision_id, source: evidence.attachment_id || 'chat', unitId: evidence.id, title: `${questionLabel(output.question_id)} · 근거 원문` });
  }

  const conversing = Boolean(requestId || pending);
  const provisionalMood = resultMood(progress.preliminary?.classifications, false);
  return <section className="main-page chat-page"><div className="main-heading"><div><p className="eyebrow">요청자</p><h1>일동이와 요청 접수</h1></div>{judgment && <span className={`environment-badge mode-${judgment.mode}`}>{judgment.mode.toUpperCase()} 연결</span>}</div>
    <div className="main-columns">
      <div className="main-primary chat-main">
        <div className="chat-log" role="log" aria-live="polite" aria-relevant="additions" aria-label="일동이와의 대화">
          {!conversing && <Greeting onPick={pickExample} />}
          {messages.map((message) => <UserBubble key={message.key} message={message} />)}
          {upload !== null && <UploadBubble percent={upload} />}
          {requestId && <AnalysisBubble stages={stageNames} current={stage} done={stepDone} badge={detail ? resultBadge(detail, judgment, Boolean(error)) : undefined} />}
          {requestId && !judgment && progress.preliminary && <AssistantBubble avatar="thinking" label="일동이의 잠정 답변" className="result-bubble"><p className="bubble-title">잠정 판단을 먼저 보여 드려요{provisionalMood === 'urgent' ? ' · 긴급 신호가 있어요' : ''}</p><ProvisionalResult state={progress} /></AssistantBubble>}
          {judgment && <AssistantBubble avatar={moodAvatar(judgmentMood(judgment))} label="일동이의 답변" className="result-bubble"><p className="bubble-title">{MOOD_TEXT[judgmentMood(judgment)]}</p>
            <Result judgment={judgment} previousJudgment={previousJudgment} runs={runs} onEvidence={openEvidence} state={resultBadge(detail, judgment, false)} /></AssistantBubble>}
          {mode === 'file' && detail && <FileDecisionBubble attachments={currentAttachments(detail)} busy={busy} onExclude={() => void excludeUnread()} onReattach={() => attachRef.current?.click()} />}
          {info && <InfoRequestBubble info={info} onAnswer={() => textRef.current?.focus()} />}
          {error && <FailureBubble message={error} busy={busy} onRetry={retry ? () => { if (retry === 'submit') void submit(); else void reanalyze(); } : undefined} />}
          {requestId && !judgment && !error && <SlowNotice state={progress} />}
          <div ref={endRef} aria-hidden="true" />
        </div>
        {notice && <p className="chat-handoff" role="status">{notice}</p>}
        <div className="composer-dock">{requestId && <QuickReplies canReanalyze={canReanalyze} finalSaved={Boolean(judgment)} busy={busy} onReanalyze={() => void reanalyze()} onNew={startNew} />}
          <Composer mode={mode} text={text} files={files} busy={busy} openRequest={Boolean(requestId)} textRef={textRef} attachRef={attachRef} onText={setText} onAddFiles={addFiles} onRemoveFile={(index) => setFiles(files.filter((_, at) => at !== index))} onSubmit={() => void submit()} /></div>
        <EvidenceViewer target={viewer} onClose={() => setViewer(null)} />{source && <aside className="source-panel"><div className="card-heading"><h2>근거 원문</h2><Button type="button" variant="plain" onClick={() => setSource('')}>닫기</Button></div><p>{sourceTitle}</p><blockquote>{source}</blockquote></aside>}
      </div>
      <aside className="request-list" aria-label="대화 목록"><button type="button" className="list-toggle" aria-expanded={listOpen} aria-controls="conversation-list" onClick={() => setListOpen(!listOpen)}>대화 목록 {listOpen ? '접기' : '펼치기'}<span aria-hidden="true">{listOpen ? '▴' : '▾'}</span></button>
        <div id="conversation-list" className="list-body" data-open={listOpen}><h2>내 요청 대화</h2><Button type="button" variant="plain" className="new-chat" onClick={startNew}>새 대화 열기</Button>
          {requests.length ? requests.map((item) => { const state = getStatusPresentation(item.status); return <button type="button" key={item.id} onClick={() => openRequest(item.id)} aria-current={item.id === requestId ? 'true' : undefined}><code>{item.id}</code><StatusBadge status={state.status} label={state.label} /></button>; }) : <p>접수한 요청이 여기에 표시됩니다.</p>}</div>
      </aside>
    </div>
  </section>;
}
