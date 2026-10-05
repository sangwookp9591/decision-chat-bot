import { useCallback, useEffect, useLayoutEffect, useReducer, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { apiFetch, idempotencyKey, type ApiError } from '../api/client';
import { requestApi, type Judgment, type RequestDetail, type RequestItem } from '../api/requests';
import { useSession } from '../state/session';
import { Button, Drawer } from '../components';
import { infoRequest, resultBadge } from './main/requestState';
import { useEventStream, type StreamEvent } from '../state/events';
import { EvidenceViewer, type ViewerTarget } from '../components/EvidenceViewer';
import { questionLabel } from '../lib/labels';
import { uploadRequest } from './main/uploadRequest';
import { ProvisionalResult, SlowNotice, stepLabel } from './main/ProgressivePanel';
import { Result, ResultBrief, answerText } from './main/ResultCard';
import { RequestList, useRequestTitles } from './main/RequestList';
import { MOTION, prefersReducedMotion } from '../lib/motion';
import { AnalysisBubble, AnswerActions, AssistantBubble, ExampleChips, FailureBubble, FileDecisionBubble, GreetingHead, InfoRequestBubble, TypingBubble, UploadBubble, UserBubble, moodAvatar } from './main/Bubbles';
import { ArrowDownIcon, MenuIcon, PlusIcon } from './main/icons';
import { Composer } from './main/Composer';
import { MAX_FILES, MOOD_TEXT, composerMode, currentAttachments, judgmentMood, resultMood, userMessages, type PendingSend } from './main/conversation';
import { initialProgress, progressReducer } from '../state/progress';
import './main/main.css';

export { Result } from './main/ResultCard';
const LIST_EVENTS = ['request.received', 'judgment_saved', 'judgment_failed', 'judgment.cancelled', 'review_decided', 'assignment_created', 'auto_assignment_deferred', 'task.transitioned', 'reanalysis.compared'];
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
  const [pending, setPending] = useState<PendingSend | null>(null); const [listOpen, setListOpen] = useState(false); const [detailOpen, setDetailOpen] = useState(false);
  const [requests, setRequests] = useState<RequestItem[]>([]); const [source, setSource] = useState(''); const [sourceTitle, setSourceTitle] = useState(''); const [viewer, setViewer] = useState<ViewerTarget | null>(null);
  const textRef = useRef<HTMLTextAreaElement>(null); const attachRef = useRef<HTMLInputElement>(null); const pageRef = useRef<HTMLElement>(null); const scrollRef = useRef<HTMLDivElement>(null);
  const atBottom = useRef(true); const openedAt = useRef(Date.now()); const [unread, setUnread] = useState(false); const [away, setAway] = useState(false); const [copied, setCopied] = useState(false);
  const dockRef = useRef<HTMLDivElement>(null); const dockTop = useRef<number | null>(null); const wasEmpty = useRef(true);
  const { titles, want } = useRequestTitles(detail);
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
    if (['failed', '실패'].includes(current.request.status)) setError('분석 실행이 실패했습니다. 결과가 저장되지 않았습니다.');
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
    if (event.run_id && detail?.request.active_run_id && event.run_id !== detail.request.active_run_id) return;
    dispatch({ type: 'event', event });
    if (['review_decided', 'assignment_created', 'auto_assignment_deferred', 'reanalysis.compared'].includes(event.type)) load(requestId);
    else if (['request.received', 'judgment_saved', 'judgment_failed', 'judgment.cancelled'].includes(event.type)) refreshIfPending(requestId);
  }, [refreshIfPending, load, requestId, detail?.request.active_run_id]);
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
  // The page is exactly one screen tall: the chat scrolls inside it. Height = viewport minus whatever the shell puts above this section.
  useLayoutEffect(() => {
    const fit = () => { const page = pageRef.current; if (page) page.style.setProperty('--shell-top', `${Math.max(0, Math.round(page.getBoundingClientRect().top + window.scrollY))}px`); };
    fit(); const frame = window.requestAnimationFrame?.(fit); window.addEventListener('resize', fit);
    return () => { window.removeEventListener('resize', fit); if (frame) window.cancelAnimationFrame(frame); };
  }, []);
  const scrollToEnd = useCallback((smooth: boolean) => {
    const el = scrollRef.current; if (!el) return;
    const behavior = smooth && !prefersReducedMotion() ? 'smooth' : 'auto';
    if (typeof el.scrollTo === 'function') el.scrollTo({ top: el.scrollHeight, behavior }); else el.scrollTop = el.scrollHeight;
  }, []);
  const onScrollLog = useCallback(() => {
    const el = scrollRef.current; if (!el) return;
    atBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    setAway(!atBottom.current);
    if (atBottom.current) setUnread(false);
  }, []);
  // Follow the newest message — only when one is added, never when a card fills in place (that would move what is being read).
  // Someone reading above the bottom is not pulled down: they get a "새 메시지" pill instead.
  useEffect(() => { openedAt.current = Date.now(); atBottom.current = true; setUnread(false); setAway(false); }, [requestId]);
  const tail = [messages.length, upload !== null, Boolean(detail), Boolean(judgment), Boolean(error), mode, progress.phase === 'preliminary'].join('|');
  useEffect(() => {
    if (tail === '0|false|false|false|false|new|false') return;
    if (atBottom.current) scrollToEnd(Date.now() - openedAt.current > 800); else setUnread(true);
  }, [tail, scrollToEnd]);

  function addFiles(added: File[]) {
    if (!added.length) return;
    const next = [...files, ...added.filter((file) => !files.some((old) => old.name === file.name && old.size === file.size))];
    setFiles(next.slice(0, MAX_FILES));
    setNotice(next.length > MAX_FILES ? `파일은 최대 ${MAX_FILES}개까지 첨부할 수 있어요. 앞에서부터 ${MAX_FILES}개만 담았어요.` : '');
  }
  async function submit() {
    const revising = Boolean(requestId) && mode !== 'new';
    const sent = { text, files };
    setBusy(true); setError(''); setRetry(''); setNotice(''); resetRun(); setUpload(0); atBottom.current = true; // your own message always follows
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
  function openRequest(id: string) { setListOpen(false); setDetailOpen(false); setPending(null); if (id !== requestId) setParams({ request_id: id }); }
  function startNew() {
    setListOpen(false); setDetailOpen(false); setPending(null); setText(''); setFiles([]); setNotice('');
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
  async function cancel() {
    const runId = detail?.request.active_run_id;
    if (!requestId || !runId || busy) return;
    setBusy(true); setNotice('');
    try {
      const result = await requestApi.cancel(requestId, runId);
      if (result.status === 'cancelled') {
        dispatch({ type: 'event', event: { type: 'judgment.cancelled', request_id: requestId, run_id: runId } });
        setDetail((current) => current ? { ...current, request: { ...current.request, status: 'cancelled' } } : current);
      } else await refresh(requestId);
    } catch (problem) { setNotice(errorMessage(problem)); } finally { setBusy(false); }
  }
  function openEvidence(output: Judgment['outputs'][number], evidence?: Judgment['outputs'][number]['evidence'][number]) {
    // The viewer stacks on top of an open detail drawer; Escape closes only the top dialog.
    if (!evidence || !requestId || !judgment) { setSourceTitle(`${questionLabel(output.question_id)} · 근거 위치`); setSource('이 판단에는 저장된 원문 위치 근거가 없습니다.'); return; }
    setSource(''); setViewer({ requestId, revision: judgment.revision_id, source: evidence.attachment_id || 'chat', unitId: evidence.id, title: `${questionLabel(output.question_id)} · 근거 원문` });
  }
  const closeEvidence = useCallback(() => { setViewer(null); setSource(''); }, []);
  const closeDetail = useCallback(() => setDetailOpen(false), []);
  const closeList = useCallback(() => setListOpen(false), []);
  const cancelled = progress.phase === 'cancelled' || detail?.request.status === 'cancelled';
  const canCancel = Boolean(requestId && detail?.request.active_run_id && !judgment && !cancelled && !error && !['failed', 'final'].includes(progress.phase) && ['judgment_pending', 'processing', 'received'].includes(detail.request.status));
  const typing = Boolean(requestId) && !judgment && !error && !cancelled && mode === 'new' && !info && !progress.preliminary;
  const answering = Boolean(judgment) || Boolean(requestId && progress.preliminary);
  async function copyAnswer() {
    if (!judgment) return;
    try { await navigator.clipboard.writeText(answerText(judgment)); setCopied(true); window.setTimeout(() => setCopied(false), 1600); } catch { setNotice('복사하지 못했어요. 브라우저의 클립보드 권한을 확인해 주세요.'); }
  }
  function openFirstEvidence() {
    if (!judgment) return;
    const output = judgment.outputs.find((item) => item.evidence.length) ?? judgment.outputs[0];
    if (output) openEvidence(output, output.evidence[0]); else setDetailOpen(true);
  }
  const listProps = { items: requests, currentId: requestId, titles, want, onOpen: openRequest, onNew: startNew };

  const conversing = Boolean(requestId || pending);
  const empty = !conversing;
  // First message: the centered composer glides to the bottom (FLIP) instead of jumping.
  useLayoutEffect(() => {
    const el = dockRef.current; if (!el) return;
    if (empty) { dockTop.current = el.getBoundingClientRect().top; wasEmpty.current = true; return; }
    if (wasEmpty.current && dockTop.current !== null && typeof el.animate === 'function' && !prefersReducedMotion()) {
      const dy = dockTop.current - el.getBoundingClientRect().top;
      if (Math.abs(dy) > 4) el.animate([{ transform: `translateY(${dy}px)` }, { transform: 'none' }], { duration: MOTION.slow, easing: MOTION.easeSpring });
    }
    wasEmpty.current = false;
  });
  const provisionalMood = resultMood(progress.preliminary?.classifications, false);
  return <section ref={pageRef} className="main-page chat-page">
    <aside className="request-list" aria-label="대화 목록"><RequestList {...listProps} /></aside>
    <div className="chat-surface">
      <div className="main-heading"><button type="button" className="icon-button menu-button" aria-label="내 요청" aria-haspopup="dialog" aria-expanded={listOpen} onClick={() => setListOpen(true)}><MenuIcon /></button>
        <h1>일동이와 요청 접수</h1>
        <div className="heading-actions">{judgment && <span className={`environment-badge mode-${judgment.mode}`}>{judgment.mode.toUpperCase()} 연결</span>}
          <button type="button" className="icon-button new-button" aria-label="새 요청 시작" onClick={startNew}><PlusIcon /></button></div></div>
      <div className="main-primary chat-main" data-empty={empty || undefined}>
        <div className="chat-viewport"><div className="chat-scroll" ref={scrollRef} onScroll={onScrollLog}>
          <div className="chat-log" role="log" aria-live="polite" aria-relevant="additions" aria-label="일동이와의 대화">
            {empty && <GreetingHead />}
            {messages.map((message) => <UserBubble key={message.key} message={message} />)}
            {upload !== null && <UploadBubble percent={upload} />}
            {requestId && <AnalysisBubble stages={stageNames} current={stage} done={stepDone} cancelled={cancelled} badge={detail ? resultBadge(detail, judgment, Boolean(error)) : undefined} />}
            {cancelled && <div className="cancelled-notice" role="status"><strong>취소됨</strong><span>분석을 중단했어요.</span>{canReanalyze && <Button type="button" variant="plain" color="primary" tone="weak" disabled={busy} onClick={() => void reanalyze()}>다시 분석</Button>}</div>}
            {answering && <AssistantBubble avatar={judgment ? moodAvatar(judgmentMood(judgment)) : 'thinking'} label={judgment ? '일동이의 답변' : '일동이의 잠정 답변'} className="result-bubble">
              <p className="bubble-title">{judgment ? MOOD_TEXT[judgmentMood(judgment)] : `잠정 판단을 먼저 보여 드려요${provisionalMood === 'urgent' ? ' · 긴급 신호가 있어요' : ''}`}</p>
              <div className={cancelled ? 'cancelled-result' : undefined}>{judgment ? <ResultBrief judgment={judgment} onEvidence={openEvidence} onDetail={() => setDetailOpen(true)} state={resultBadge(detail, judgment, false)} /> : <ProvisionalResult state={progress} cancelled={cancelled} />}</div>
              {!cancelled && <AnswerActions canReanalyze={canReanalyze} finalSaved={Boolean(judgment)} busy={busy} copied={copied} onCopy={() => void copyAnswer()} onReanalyze={() => void reanalyze()} onEvidence={openFirstEvidence} />}</AssistantBubble>}
            {mode === 'file' && detail && <FileDecisionBubble attachments={currentAttachments(detail)} busy={busy} onExclude={() => void excludeUnread()} onReattach={() => attachRef.current?.click()} />}
            {info && <InfoRequestBubble info={info} onAnswer={() => textRef.current?.focus()} />}
            {error && <FailureBubble message={error} busy={busy} onRetry={retry ? () => { if (retry === 'submit') void submit(); else void reanalyze(); } : undefined} />}
            {requestId && !judgment && !error && <SlowNotice state={progress} />}
            {typing && <TypingBubble />}
          </div>
        </div>
        {away && <button type="button" className="scroll-down" aria-label={unread ? '새 메시지 보기' : '맨 아래로'} data-unread={unread || undefined} onClick={() => { atBottom.current = true; setUnread(false); setAway(false); scrollToEnd(true); }}><ArrowDownIcon /></button>}</div>
        {notice && <p className="chat-handoff" role="status">{notice}</p>}
        <div className="composer-dock" ref={dockRef}>
          <Composer mode={mode} text={text} files={files} busy={busy} openRequest={Boolean(requestId)} canCancel={canCancel} textRef={textRef} attachRef={attachRef} onText={setText} onAddFiles={addFiles} onRemoveFile={(index) => setFiles(files.filter((_, at) => at !== index))} onSubmit={() => void submit()} onCancel={() => void cancel()} /></div>
        {empty && <ExampleChips onPick={pickExample} />}
      </div>
    </div>
    <Drawer open={listOpen} title="내 요청 대화" onClose={closeList}><RequestList {...listProps} hideTitle /></Drawer>
    <Drawer open={detailOpen && Boolean(judgment)} title="판단 상세" onClose={closeDetail}>{judgment && <Result judgment={judgment} previousJudgment={previousJudgment} runs={runs} onEvidence={openEvidence} state={resultBadge(detail, judgment, false)} />}</Drawer>
    <EvidenceViewer target={viewer} onClose={closeEvidence} />
    <Drawer open={Boolean(source)} title="근거 원문" onClose={closeEvidence}><p>{sourceTitle}</p><blockquote className="source-quote">{source}</blockquote></Drawer>
  </section>;
}
