import { useState } from 'react';
import { llmApi } from '../../api/llm';
import type { ApiError } from '../../api/client';
import { authorLabel } from '../../lib/assist';

type Candidate = { id: string; explanation?: string | null; explanation_author?: string | null };
export function Explanation({ candidate, enabled, canEdit }: { candidate: Candidate; enabled: boolean; canEdit: boolean }) {
  const [result, setResult] = useState<{ explanation: string; author: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function generate() {
    setBusy(true); setError('');
    try { setResult(await llmApi.explainCandidate(candidate.id)); }
    catch (e) { setError((e as ApiError).message); }
    finally { setBusy(false); }
  }
  const text = result?.explanation || candidate.explanation;
  return <section aria-label="규칙 후보 설명"><h3>규칙 후보 설명</h3>
    {enabled && canEdit && <button type="button" className="ui-button secondary" disabled={busy} onClick={() => void generate()}>설명 만들기</button>}
    <div aria-live="polite">{busy && <p>설명 작성 중…</p>}{error && <p role="alert">{error}</p>}
      {text && <><p>{text}</p><small>{authorLabel(result?.author || candidate.explanation_author || '')}</small></>}</div>
  </section>;
}
