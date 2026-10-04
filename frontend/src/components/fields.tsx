import { useEffect, useId, useMemo, useRef, useState, type ReactNode } from 'react';
import './fields.css';

/** Shared form controls: one label/hint/error layout, 44px touch targets, one focus ring. */
type Ids = { id: string; describedBy?: string; invalid: boolean };

export function Field({ label, hint, error, className = '', children }: { label: ReactNode; hint?: ReactNode; error?: string; className?: string; children: (ids: Ids) => ReactNode }) {
  const id = useId();
  const describedBy = [hint ? `${id}-hint` : '', error ? `${id}-err` : ''].filter(Boolean).join(' ') || undefined;
  return <div className={`fld ${className}`}>
    <label className="fld-label" htmlFor={id}>{label}</label>
    {hint && <small className="fld-hint" id={`${id}-hint`}>{hint}</small>}
    {children({ id, describedBy, invalid: Boolean(error) })}
    {error && <small className="fld-error" id={`${id}-err`} role="alert">{error}</small>}
  </div>;
}

type InputProps = Omit<React.InputHTMLAttributes<HTMLInputElement>, 'id'>;
export function TextField({ label, hint, error, className, ...props }: InputProps & { label: ReactNode; hint?: ReactNode; error?: string }) {
  return <Field label={label} hint={hint} error={error} className={className}>{(ids) => <input {...props} id={ids.id} className="fld-control" aria-describedby={ids.describedBy} aria-invalid={ids.invalid || undefined} />}</Field>;
}

export function Select({ label, hint, error, className, children, ...props }: Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'id'> & { label: ReactNode; hint?: ReactNode; error?: string }) {
  return <Field label={label} hint={hint} error={error} className={className}>{(ids) => <span className="fld-select"><select {...props} id={ids.id} className="fld-control" aria-describedby={ids.describedBy} aria-invalid={ids.invalid || undefined}>{children}</select></span>}</Field>;
}

export function Checkbox({ label, checked, onChange, disabled }: { label: ReactNode; checked: boolean; onChange: (checked: boolean) => void; disabled?: boolean }) {
  return <label className="fld-check"><input type="checkbox" checked={checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)} /><span aria-hidden="true" className="fld-box" /><span>{label}</span></label>;
}

/** On/off switch (role=switch) with its name beside it. */
export function Switch({ label, checked, onChange, disabled, hint }: { label: ReactNode; checked: boolean; onChange: (checked: boolean) => void; disabled?: boolean; hint?: ReactNode }) {
  const id = useId();
  return <div className="fld-switch-row">
    <span className="fld-switch-text"><span id={`${id}-l`}>{label}</span>{hint && <small className="fld-hint">{hint}</small>}</span>
    <button type="button" role="switch" aria-checked={checked} aria-labelledby={`${id}-l`} disabled={disabled} className="fld-switch" onClick={() => onChange(!checked)}><span aria-hidden="true" /></button>
    <span className="fld-switch-state" aria-hidden="true">{checked ? '켜짐' : '꺼짐'}</span>
  </div>;
}

/** Multi-select chips (each chip is a toggle button). */
export function ChipGroup({ label, options, value, onChange, disabled }: { label: ReactNode; options: Array<{ value: string; label: string }>; value: string[]; onChange: (next: string[]) => void; disabled?: boolean }) {
  const id = useId();
  return <div className="fld" role="group" aria-labelledby={`${id}-l`}>
    <span className="fld-label" id={`${id}-l`}>{label}</span>
    <div className="fld-chips">{options.map((o) => { const on = value.includes(o.value); return <button key={o.value} type="button" className={`fld-chip${on ? ' on' : ''}`} aria-pressed={on} disabled={disabled} onClick={() => onChange(on ? value.filter((v) => v !== o.value) : [...value, o.value])}>{on && <span aria-hidden="true">✓ </span>}{o.label}</button>; })}</div>
  </div>;
}

/** Number input with a unit and a visible allowed range. Keeps the raw text while typing. */
export function NumberField({ label, hint, value, onChange, min, max, step, unit, disabled, error, compact, onInvalid }: { label: ReactNode; hint?: ReactNode; value: number; onChange: (value: number) => void; onInvalid?: () => void; min?: number; max?: number; step?: number; unit?: string; disabled?: boolean; error?: string; compact?: boolean }) {
  const [text, setText] = useState(String(value));
  useEffect(() => { if (Number(text) !== value) setText(String(value)); }, [value]); // eslint-disable-line react-hooks/exhaustive-deps
  const range = min !== undefined && max !== undefined ? `${min}~${max}` : min !== undefined ? `${min} 이상` : max !== undefined ? `${max} 이하` : '';
  const out = text.trim() !== '' && ((min !== undefined && Number(text) < min) || (max !== undefined && Number(text) > max));
  const message = error || (text.trim() === '' || Number.isNaN(Number(text)) ? '숫자를 입력해 주세요.' : out ? `허용 범위는 ${range}입니다.` : '');
  return <Field label={label} hint={hint} error={message} className={compact ? 'fld-compact' : ''}>{(ids) => <span className="fld-number"><input id={ids.id} className="fld-control" type="number" inputMode="decimal" min={min} max={max} step={step} value={text} disabled={disabled} aria-describedby={ids.describedBy} aria-invalid={ids.invalid || undefined}
    onChange={(e) => { setText(e.target.value); if (e.target.value.trim() !== '' && !Number.isNaN(Number(e.target.value))) onChange(Number(e.target.value)); else onInvalid?.(); }} />{unit && <span className="fld-unit">{unit}</span>}{range && <span className="fld-range">{range}</span>}</span>}</Field>;
}

/** Searchable single choice (combobox + listbox). Opens on focus, filters as you type, Enter picks, Esc closes. */
export function SearchSelect({ label, options, value, onChange, placeholder = '검색하거나 선택', emptyText = '일치하는 항목이 없습니다', disabled, className }: { label: string; options: Array<{ value: string; label: string }>; value: string; onChange: (value: string) => void; placeholder?: string; emptyText?: string; disabled?: boolean; className?: string }) {
  const id = useId();
  const current = options.find((o) => o.value === value);
  const [query, setQuery] = useState<string | null>(null); // null = show the chosen label
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const shown = useMemo(() => { const q = (query ?? '').trim().toLowerCase(); return q ? options.filter((o) => o.label.toLowerCase().includes(q) || o.value.toLowerCase().includes(q)) : options; }, [options, query]);
  useEffect(() => {
    if (!open) return;
    const away = (e: MouseEvent) => { if (!root.current?.contains(e.target as Node)) { setOpen(false); setQuery(null); } };
    document.addEventListener('mousedown', away); return () => document.removeEventListener('mousedown', away);
  }, [open]);
  function pick(o: { value: string }) { onChange(o.value); setOpen(false); setQuery(null); }
  return <div className={`fld fld-search ${className || ''}`} ref={root}>
    <label className="fld-label" htmlFor={id}>{label}</label>
    <span className="fld-select"><input id={id} className="fld-control" role="combobox" aria-expanded={open} aria-controls={`${id}-list`} aria-autocomplete="list" aria-activedescendant={open && shown[active] ? `${id}-o${active}` : undefined} autoComplete="off" disabled={disabled}
      placeholder={placeholder} value={query ?? current?.label ?? (value || '')} onFocus={(e) => { setOpen(true); e.currentTarget.select(); }}
      onChange={(e) => { setQuery(e.target.value); setActive(0); setOpen(true); }}
      onKeyDown={(e) => {
        if (e.key === 'ArrowDown') { e.preventDefault(); setOpen(true); setActive((a) => Math.min(a + 1, shown.length - 1)); }
        else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
        else if (e.key === 'Enter' && open && shown[active]) { e.preventDefault(); pick(shown[active]); }
        else if (e.key === 'Escape') { setOpen(false); setQuery(null); }
      }} /></span>
    {open && <ul className="fld-list" role="listbox" id={`${id}-list`} aria-label={`${label} 목록`}>
      {shown.length ? shown.map((o, i) => <li key={o.value} id={`${id}-o${i}`} role="option" aria-selected={o.value === value} className={i === active ? 'active' : ''} onMouseDown={(e) => { e.preventDefault(); pick(o); }} onMouseEnter={() => setActive(i)}>{o.label}</li>) : <li className="fld-list-empty" aria-disabled="true">{emptyText}</li>}
    </ul>}
  </div>;
}

const pad = (n: number) => String(n).padStart(2, '0');
type Parts = { y: string; mo: string; d: string; h: string; mi: string };
const split = (value: string): Parts => { const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(value); return m ? { y: m[1], mo: String(+m[2]), d: String(+m[3]), h: m[4], mi: m[5] } : { y: '', mo: '', d: '', h: '', mi: '' }; };
/** '' unless every part is a real calendar date and clock time. */
export function joinDateTime(p: Parts): string {
  const [y, mo, d, h, mi] = [p.y, p.mo, p.d, p.h, p.mi].map((x) => (x.trim() === '' ? NaN : Number(x)));
  if ([y, mo, d, h, mi].some((n) => !Number.isInteger(n)) || y < 1970 || y > 2999 || mo < 1 || mo > 12 || h < 0 || h > 23 || mi < 0 || mi > 59 || d < 1 || d > new Date(y, mo, 0).getDate()) return '';
  return `${y}-${pad(mo)}-${pad(d)}T${pad(h)}:${pad(mi)}`;
}

/** Date + time in Korean order (연·월·일·시·분), independent of the browser's locale. Value: 'YYYY-MM-DDTHH:mm' or ''. */
export function DateTimeField({ label, value, onChange, invalid }: { label: string; value: string; onChange: (value: string) => void; invalid?: boolean }) {
  const [parts, setParts] = useState<Parts>(() => split(value));
  useEffect(() => { if (value && value !== joinDateTime(parts)) setParts(split(value)); }, [value]); // eslint-disable-line react-hooks/exhaustive-deps
  const bad = invalid ?? !value;
  const seg = (key: keyof Parts, unit: string, width: string, min: number, max: number) => <label className={`fld-seg ${width}`}>
    <input type="number" inputMode="numeric" min={min} max={max} aria-label={`${label} ${unit}`} aria-invalid={bad || undefined} className="fld-control" value={parts[key]}
      onChange={(e) => { const next = { ...parts, [key]: e.target.value }; setParts(next); onChange(joinDateTime(next)); }} /><span aria-hidden="true">{unit}</span></label>;
  return <div className="fld fld-datetime" role="group" aria-label={label}>
    <span className="fld-label" aria-hidden="true">{label}</span>
    <div className="fld-segs">{seg('y', '년', 'w4', 1970, 2999)}{seg('mo', '월', 'w2', 1, 12)}{seg('d', '일', 'w2', 1, 31)}{seg('h', '시', 'w2', 0, 23)}{seg('mi', '분', 'w2', 0, 59)}</div>
  </div>;
}

/** Period picker: two DateTimeFields and the shared problem message. */
export function DateRange({ from, to, onChange, problem }: { from: string; to: string; onChange: (range: { from: string; to: string }) => void; problem?: string }) {
  return <div className="fld-range-group">
    <DateTimeField label="시작" value={from} onChange={(v) => onChange({ from: v, to })} />
    <span className="fld-range-sep" aria-hidden="true">~</span>
    <DateTimeField label="종료" value={to} onChange={(v) => onChange({ from, to: v })} />
    {problem && <small className="fld-error fld-range-error" role="alert">{problem}</small>}
  </div>;
}

/** Empty list/area: what will appear here and what to do next. */
export function EmptyCard({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return <div className="fld-empty"><span aria-hidden="true">◇</span><strong>{title}</strong>{children && <p>{children}</p>}{action && <div className="fld-empty-action">{action}</div>}</div>;
}

/** Row of filter controls that wraps neatly; the last child (the action) stays at the end of the row. */
export function FilterBar({ children, label, onSubmit }: { children: ReactNode; label?: string; onSubmit?: (e: React.FormEvent) => void }) {
  return <form className="fld-filterbar" aria-label={label} onSubmit={(e) => { e.preventDefault(); onSubmit?.(e); }}>{children}</form>;
}
