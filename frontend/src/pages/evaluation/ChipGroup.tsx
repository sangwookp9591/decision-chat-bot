import { useId, type KeyboardEvent, type ReactNode } from 'react';
import { evaluationFieldInfo, evaluationFieldLabel } from '../../lib/labels';
import type { LabelField } from './options';

type Props = { field: LabelField; shortcut?: number; value: string | string[]; onChange: (value: string | string[]) => void; disabled?: boolean };

/** One answer field: a fieldset whose legend names it; single fields are a radio group, multi fields toggle chips. */
export function ChipGroup({ field, shortcut, value, onChange, disabled }: Props) {
  const legendId = useId();
  const hintId = useId();
  const info = evaluationFieldInfo[field.key];
  const known = field.kind === 'single' ? [...field.options, field.uncertain] : field.options;
  const current = Array.isArray(value) ? value : value ? [value] : [];
  // A stored value outside the vocabulary stays visible and selectable instead of silently disappearing.
  const extras = current.filter((item) => !known.includes(item));
  const normal = [...field.options, ...extras];
  const uncertain = field.kind === 'single' ? [field.uncertain] : [];
  const all = [...normal, ...uncertain];
  const checked = (option: string) => current.includes(option);
  const tabbable = field.kind === 'single' ? (current.find((item) => all.includes(item)) ?? all[0]) : undefined;

  const onRadioKey = (event: KeyboardEvent<HTMLButtonElement>, option: string) => {
    const at = all.indexOf(option);
    const next = event.key === 'ArrowRight' || event.key === 'ArrowDown' ? (at + 1) % all.length
      : event.key === 'ArrowLeft' || event.key === 'ArrowUp' ? (at - 1 + all.length) % all.length
      : event.key === 'Home' ? 0 : event.key === 'End' ? all.length - 1 : -1;
    if (next < 0) return;
    event.preventDefault(); event.stopPropagation();
    onChange(all[next]);
    event.currentTarget.closest('fieldset')?.querySelectorAll<HTMLButtonElement>('button[data-chip]')[next]?.focus();
  };
  const toggle = (option: string) => onChange(checked(option) ? current.filter((item) => item !== option) : [...current, option]);

  const chip = (option: string, uncertainChip: boolean): ReactNode => {
    const on = checked(option);
    const className = `eval-chip${on ? ' on' : ''}${uncertainChip ? ' uncertain' : ''}`;
    return field.kind === 'single'
      ? <button key={option} type="button" data-chip role="radio" aria-checked={on} tabIndex={option === tabbable ? 0 : -1} disabled={disabled} className={className}
          onClick={() => onChange(option)} onKeyDown={(event) => onRadioKey(event, option)}><span className="eval-chip-mark" aria-hidden="true">{on ? '✓' : ''}</span>{option}</button>
      : <button key={option} type="button" data-chip aria-pressed={on} disabled={disabled} className={className} onClick={() => toggle(option)}><span className="eval-chip-mark" aria-hidden="true">{on ? '✓' : ''}</span>{option}</button>;
  };

  return <fieldset id={`eval-group-${field.key}`} className="eval-field" role={field.kind === 'single' ? 'radiogroup' : 'group'} aria-labelledby={legendId} aria-describedby={hintId}>
    <legend><span className="eval-field-head">
      {shortcut ? <kbd aria-hidden="true">{shortcut}</kbd> : null}
      <span id={legendId}>{evaluationFieldLabel(field.key)}</span>
      {field.kind === 'multi' && <span className="eval-field-note">여러 개 선택 · 없으면 비워 둡니다</span>}
    </span></legend>
    <p id={hintId} className="eval-field-hint">{info?.hint}</p>
    <div className="eval-chips">
      <div className="eval-chip-row">{normal.map((option) => chip(option, false))}</div>
      {uncertain.length > 0 && <><span className="eval-chip-divider" aria-hidden="true" /><div className="eval-chip-row">{uncertain.map((option) => chip(option, true))}</div></>}
    </div>
  </fieldset>;
}
