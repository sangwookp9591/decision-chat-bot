import { useEffect, useState } from 'react';
import { caseApi, caseStatusLabel, type CaseCommand, type CaseStatus, type DecisionCase } from '../api/cases';
import type { ApiError } from '../api/client';
import { Button } from '../components';
import { EmptyCard, Select, TextField } from '../components/fields';
import { formatTime } from '../lib/format';
import './review/review.css';

const fieldLabels: Record<string, string> = { ai_need: 'AI 필요성', feasibility: '개발 가능성', urgency: '긴급도', lead_org: '담당 조직' };
const split = (value: string) => value.split(',').map((x) => x.trim()).filter(Boolean);
const statuses: Array<[CaseStatus | '', string]> = [['', '전체'], ['recorded', caseStatusLabel.recorded], ['confirmed', caseStatusLabel.confirmed], ['verified', caseStatusLabel.verified], ['retired', caseStatusLabel.retired]];

/** 검토자의 판단 사례: 적용 조건·예외 확인, 실제 결과 기록, 폐기와 되돌리기. */
export function Cases() {
  const [status, setStatus] = useState<CaseStatus | ''>('');
  const [rows, setRows] = useState<DecisionCase[] | null>(null);
  const [error, setError] = useState('');
  async function refresh() { try { setRows((await caseApi.list(status)).cases); setError(''); } catch (e) { setError((e as ApiError).message); } }
  useEffect(() => { void refresh(); }, [status]); // eslint-disable-line react-hooks/exhaustive-deps
  return <section className="review-page">
    <header><div><p className="eyebrow">암묵지 자산화</p><h1>판단 사례</h1><p>검토자가 AI 원안을 고친 판단을 사유·출처와 함께 남깁니다. 사례는 새 검토에서 참고 선례로만 보이며, 값을 자동으로 바꾸지 않습니다.</p></div></header>
    <Select label="상태" aria-label="사례 상태 필터" value={status} onChange={(e) => setStatus(e.target.value as CaseStatus | '')}>{statuses.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select>
    {error && <p role="alert">{error}</p>}
    {rows && !rows.length && <EmptyCard title="아직 판단 사례가 없습니다">검토에서 분류를 수정 승인하면 사유와 함께 사례가 기록됩니다.</EmptyCard>}
    {rows?.map((c) => <CaseCard key={`${c.id}@${c.version}`} item={c} onChanged={refresh} />)}
  </section>;
}

function CaseCard({ item, onChanged }: { item: DecisionCase; onChanged: () => Promise<void> }) {
  const [conditions, setConditions] = useState(item.conditions.join(', '));
  const [exceptions, setExceptions] = useState(item.exceptions.join(', '));
  const [note, setNote] = useState('');
  const [toVersion, setToVersion] = useState('');
  const [message, setMessage] = useState('');
  async function act(action: 'confirm' | 'outcome' | 'retire' | 'revert', extra: Omit<CaseCommand, 'version'>) {
    try { await caseApi.act(item.id, action, { version: item.version, ...extra }); await onChanged(); } catch (e) { setMessage((e as ApiError).message || '저장하지 못했습니다.'); }
  }
  const retired = item.status === 'retired';
  return <article className="review-task" aria-label={`판단 사례 ${item.situation}`}>
    <p><b>{fieldLabels[item.field] || item.field}</b> · AI 원안 {String(item.ai_value ?? '—')} → 검토자 판단 <b>{String(item.corrected_value ?? '—')}</b> · {caseStatusLabel[item.status]} · v{item.version}</p>
    <p>“{item.situation || '제목 없는 요청'}” · 사유: {item.reason}</p>
    <small>출처 요청 <a href={`/review?request_id=${encodeURIComponent(item.request_id)}`}>{item.request_id}</a> · 기록자 {item.owner} · {formatTime(item.created_at)} · 참고 {item.consulted}회 / 따름 {item.followed}회{item.outcome ? ` · 결과 ${item.outcome === 'held' ? '유효' : '실패'}: ${item.outcome_note}` : ' · 실제 결과 미기록'}</small>
    {message && <p role="alert">{message}</p>}
    <TextField label="적용 조건 키워드" hint="요청 원문에 하나라도 있으면 선례로 보여 줍니다. 쉼표로 구분합니다." value={conditions} disabled={retired} onChange={(e) => setConditions(e.target.value)} />
    <TextField label="예외 키워드" hint="하나라도 있으면 '적용 금지'로 표시합니다." value={exceptions} disabled={retired} onChange={(e) => setExceptions(e.target.value)} />
    <TextField label="결과·폐기 메모" value={note} onChange={(e) => setNote(e.target.value)} />
    <div className="review-actions">
      <Button type="button" variant="secondary" disabled={retired || !split(conditions).length} onClick={() => void act('confirm', { conditions: split(conditions), exceptions: split(exceptions) })}>조건 확인</Button>
      <Button type="button" variant="plain" disabled={retired || !note.trim()} onClick={() => void act('outcome', { outcome: 'held', note })}>결과 유효</Button>
      <Button type="button" variant="plain" disabled={retired || !note.trim()} onClick={() => void act('outcome', { outcome: 'failed', note })}>결과 실패(폐기)</Button>
      <Button type="button" variant="plain" disabled={retired || !note.trim()} onClick={() => void act('retire', { reason: note })}>폐기</Button>
    </div>
    {(item.history?.length || 0) > 1 && <details><summary>변경 이력 {item.history!.length}건</summary>
      <ol>{item.history!.map((h) => <li key={h.version}>v{h.version} · {h.action} · {caseStatusLabel[h.status]} · {h.by} · {formatTime(h.at)}{h.note ? ` · ${h.note}` : ''}</li>)}</ol>
      <div className="review-actions"><Select label="되돌릴 버전" value={toVersion} onChange={(e) => setToVersion(e.target.value)}><option value="">선택</option>{item.history!.filter((h) => h.version !== item.version).map((h) => <option key={h.version} value={h.version}>v{h.version}</option>)}</Select><Button type="button" variant="plain" disabled={!toVersion} onClick={() => void act('revert', { to_version: Number(toVersion) })}>되돌리기</Button></div>
    </details>}
  </article>;
}
