import type { ReactNode } from 'react';
import { Button, StatusBadge, type StatusKind } from '../../components';
import { Mascot, type MascotKind } from '../../components/Mascot';
import { attachmentReasonLabel } from '../../components/statusLabels';
import type { RequestAttachment } from '../../api/requests';
import { EXAMPLE_REQUESTS, type ResultMood, type UserMessage } from './conversation';
import { shortId } from './listFormat';
import { CheckIcon, CopyIcon, EvidenceIcon, RefreshIcon } from './icons';

/** 일동이's turn: a small mascot in a fixed column so swapping it (thinking → result icon) never moves the text, which flows full width without a bubble. */
export function AssistantBubble({ avatar, label, children, className = '' }: { avatar: MascotKind | 'urgent' | 'none'; label: string; children: ReactNode; className?: string }) {
  return <div className={`chat-row assistant ${className}`} role="group" aria-label={label}>
    <span className="chat-avatar">{avatar === 'urgent' ? <span className="avatar-warning" aria-hidden="true">⚠</span> : avatar === 'none' ? null : <Mascot kind={avatar} size={32} />}</span>
    <div className="bubble">{children}</div>
  </div>;
}
export const moodAvatar = (mood: ResultMood): MascotKind | 'urgent' => (mood === 'urgent' ? 'urgent' : mood === 'review' ? 'surprised' : 'like');

export function UserBubble({ message }: { message: UserMessage }) {
  return <div className="chat-row user" role="group" aria-label={message.revision > 1 ? `내 보완 답변 (revision ${message.revision})` : '내가 보낸 요청'} data-pending={message.pending || undefined}>
    <div className="bubble">
      {message.text ? <p className="bubble-text">{message.text}</p> : !message.pending && message.files.length === 0 && <p className="bubble-text bubble-redacted">내용은 원문 열람 권한이 있는 분에게만 보여요</p>}
      {message.files.length > 0 && <ul className="chip-list" aria-label="첨부 파일">{message.files.map((file) => <li key={file.id} className="file-chip">{file.name}</li>)}</ul>}
      <span className="bubble-meta" role={message.pending ? 'status' : undefined}>{message.pending && !message.requestId ? '보내는 중…' : <>{message.revision > 1 ? `revision ${message.revision} 접수됨` : '접수됨'}{message.requestId && <> · <code title={message.requestId}>{shortId(message.requestId)}</code></>}</>}</span>
    </div>
  </div>;
}

/** Empty conversation: who 일동이 is and what to ask. The composer sits right below it (centered) until the first message is sent. */
export function GreetingHead() {
  return <section className="chat-greeting" aria-label="일동이 인사">
    <Mascot kind="wave" size={96} />
    <h2>안녕하세요, 일동이예요</h2>
    <p>무엇을 도와드릴까요? 업무 요청을 적거나 문서를 올려 주세요.<br />AI·일반 개발·사람이 맡을 일을 나눠 드려요.</p>
  </section>;
}
export function ExampleChips({ onPick }: { onPick: (text: string) => void }) {
  return <div className="example-chips" role="group" aria-label="예시 요청"><span>이렇게 요청해 보세요</span>
    {EXAMPLE_REQUESTS.map((example) => <button key={example} type="button" className="example-chip" onClick={() => onPick(example)}>{example}</button>)}
  </div>;
}

/** Three bouncing dots while 일동이 is working; the label carries the meaning, the dots are decoration. */
export function TypingBubble() {
  return <AssistantBubble avatar="none" label="일동이가 입력 중" className="typing-bubble"><span className="typing-dots" aria-hidden="true"><i className="typing-dot" /><i className="typing-dot" /><i className="typing-dot" /></span></AssistantBubble>;
}

export function UploadBubble({ percent }: { percent: number }) {
  return <AssistantBubble avatar="hello" label="업로드 진행"><strong>요청을 올리고 있어요</strong><div className="upload-row"><progress max="100" value={percent} aria-label="업로드 진행률" /><span>{percent}%</span></div></AssistantBubble>;
}

export function AnalysisBubble({ stages, current, done, badge }: { stages: readonly string[]; current: string; done: (name: string, index: number) => boolean; badge?: { status: StatusKind; label: string } }) {
  const finished = stages.every(done);
  return <AssistantBubble avatar={finished ? 'hello' : 'thinking'} label="분석 진행" className="analysis-bubble">
    <div className="card-heading"><h2>분석 진행</h2>{badge && <StatusBadge {...badge} />}</div>
    <p className="thinking-line">{finished ? '분석을 마쳤어요' : '요청을 살펴보고 있어요'}</p>
    <ol className="stage-list">{stages.map((name, index) => <li key={name} className={done(name, index) ? 'done' : name === current ? 'current' : 'waiting'}><span aria-hidden="true">{done(name, index) ? '✓' : index + 1}</span>{name}<span className="sr-only">{done(name, index) ? ' 완료' : name === current ? ' 진행 중' : ' 대기'}</span></li>)}</ol>
  </AssistantBubble>;
}

export function FileDecisionBubble({ attachments, busy, onExclude, onReattach }: { attachments: RequestAttachment[]; busy: boolean; onExclude: () => void; onReattach: () => void }) {
  return <AssistantBubble avatar="surprised" label="읽기 실패 파일" className="file-decision">
    <strong>이 파일을 읽지 못했어요</strong>
    <ul>{attachments.filter((file) => file.status !== 'ok').map((file) => <li key={file.id}>{file.filename} — {attachmentReasonLabel(file.reason)}</li>)}</ul>
    <p className="bubble-hint">제외하고 나머지로 분석하거나, 읽을 수 있는 파일로 다시 첨부해 주세요.</p>
    <div className="bubble-actions"><Button type="button" disabled={busy} onClick={onExclude}>제외하고 진행</Button><Button type="button" variant="plain" disabled={busy} onClick={onReattach}>다시 첨부</Button></div>
  </AssistantBubble>;
}

export function InfoRequestBubble({ info, onAnswer }: { info: { reason: string; needed: string[] }; onAnswer: () => void }) {
  return <AssistantBubble avatar="surprised" label="보완 요청" className="info-request">
    <strong>검토자가 보완을 요청했어요</strong>
    <p>{info.reason || '보완이 필요한 내용을 확인해 주세요.'}</p>
    {info.needed.length > 0 && <ul>{info.needed.map((item) => <li key={item}>{item}</li>)}</ul>}
    <p className="bubble-hint">아래 입력창에 답을 적어 보내면 같은 요청의 새 revision으로 접수되어 다시 분석해요.</p>
    <div className="bubble-actions"><Button type="button" variant="plain" onClick={onAnswer}>답변 입력하기</Button></div>
  </AssistantBubble>;
}

export function FailureBubble({ message, busy, onRetry }: { message: string; busy: boolean; onRetry?: () => void }) {
  return <AssistantBubble avatar="none" label="처리 실패" className="failure-bubble">
    <div className="failure-card" role="alert"><StatusBadge status="failure" label="시스템 실패" /><p>{message}</p>{onRetry && <Button type="button" variant="secondary" disabled={busy} onClick={onRetry}>다시 시도</Button>}</div>
  </AssistantBubble>;
}

const IconButton = ({ label, onClick, disabled, children }: { label: string; onClick: () => void; disabled?: boolean; children: ReactNode }) =>
  <button type="button" className="icon-button" aria-label={label} title={label} disabled={disabled} onClick={onClick}>{children}</button>;

/**
 * Small action row under 일동이's answer: copy, re-analyze, source. Rendered from the first provisional card on (disabled until the final judgment
 * is saved) so the row's slot never appears late and moves nothing.
 */
export function AnswerActions({ canReanalyze, finalSaved, busy, copied, onCopy, onReanalyze, onEvidence }: { canReanalyze: boolean; finalSaved: boolean; busy: boolean; copied: boolean; onCopy: () => void; onReanalyze: () => void; onEvidence: () => void }) {
  return <div className="answer-actions" role="group" aria-label="답변 동작">
    <IconButton label={copied ? '복사됨' : '답변 복사'} disabled={!finalSaved} onClick={onCopy}>{copied ? <CheckIcon /> : <CopyIcon />}</IconButton>
    {canReanalyze && <IconButton label="다시 분석" disabled={!finalSaved || busy} onClick={onReanalyze}><RefreshIcon /></IconButton>}
    <IconButton label="근거 보기" disabled={!finalSaved} onClick={onEvidence}><EvidenceIcon /></IconButton>
  </div>;
}
