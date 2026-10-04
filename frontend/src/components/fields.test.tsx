import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { useState } from 'react';
import { Checkbox, DateRange, DateTimeField, EmptyCard, joinDateTime, NumberField, SearchSelect, Select, Switch } from './fields';

afterEach(cleanup);

describe('joinDateTime', () => {
  it('accepts real calendar dates and clock times only', () => {
    expect(joinDateTime({ y: '2026', mo: '10', d: '4', h: '9', mi: '5' })).toBe('2026-10-04T09:05');
    expect(joinDateTime({ y: '2026', mo: '2', d: '30', h: '0', mi: '0' })).toBe('');
    expect(joinDateTime({ y: '2026', mo: '13', d: '1', h: '0', mi: '0' })).toBe('');
    expect(joinDateTime({ y: '2026', mo: '1', d: '1', h: '24', mi: '0' })).toBe('');
    expect(joinDateTime({ y: '', mo: '1', d: '1', h: '0', mi: '0' })).toBe('');
  });
});

describe('DateRange', () => {
  function Harness({ onValue }: { onValue: (v: { from: string; to: string }) => void }) {
    const [range, setRange] = useState({ from: '2026-10-01T09:00', to: '2026-10-04T18:30' });
    return <DateRange from={range.from} to={range.to} onChange={(r) => { setRange(r); onValue(r); }} problem="" />;
  }
  it('shows Korean-ordered segments (년 월 일 시 분) and emits ISO-like local values', () => {
    const seen = vi.fn();
    render(<Harness onValue={seen} />);
    expect(screen.getByLabelText('시작 년')).toHaveValue(2026);
    expect(screen.getByLabelText('종료 시')).toHaveValue(18);
    fireEvent.change(screen.getByLabelText('시작 일'), { target: { value: '2' } });
    expect(seen).toHaveBeenLastCalledWith({ from: '2026-10-02T09:00', to: '2026-10-04T18:30' });
    fireEvent.change(screen.getByLabelText('시작 월'), { target: { value: '' } });
    expect(seen).toHaveBeenLastCalledWith({ from: '', to: '2026-10-04T18:30' });
    // the typed digits stay on screen while the value is incomplete
    expect(screen.getByLabelText('시작 일')).toHaveValue(2);
    expect(screen.getByLabelText('시작 월')).toHaveAttribute('aria-invalid', 'true');
  });
  it('is a labelled group', () => {
    render(<DateTimeField label="시작" value="2026-10-01T09:00" onChange={() => undefined} />);
    expect(screen.getByRole('group', { name: '시작' })).toBeInTheDocument();
  });
});

describe('SearchSelect', () => {
  const options = [{ value: 'req_1', label: 'req_1 · 접수' }, { value: 'req_22', label: 'req_22 · 완료' }, { value: 'abc', label: 'abc · 실패' }];
  it('filters while typing, picks with Enter and closes on Escape', () => {
    const onChange = vi.fn();
    render(<SearchSelect label="요청 선택" options={options} value="" onChange={onChange} />);
    const box = screen.getByRole('combobox', { name: '요청 선택' });
    fireEvent.focus(box);
    expect(screen.getAllByRole('option')).toHaveLength(3);
    fireEvent.change(box, { target: { value: 'req_2' } });
    expect(screen.getAllByRole('option').map((o) => o.textContent)).toEqual(['req_22 · 완료']);
    fireEvent.keyDown(box, { key: 'Enter' });
    expect(onChange).toHaveBeenCalledWith('req_22');
    expect(screen.queryByRole('listbox')).toBeNull();
    fireEvent.focus(box); fireEvent.keyDown(box, { key: 'Escape' });
    expect(screen.queryByRole('listbox')).toBeNull();
  });
  it('says so when nothing matches and shows the chosen label', () => {
    const { rerender } = render(<SearchSelect label="요청 선택" options={options} value="abc" onChange={() => undefined} />);
    expect(screen.getByRole('combobox')).toHaveValue('abc · 실패');
    rerender(<SearchSelect label="요청 선택" options={options} value="abc" onChange={() => undefined} />);
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'zzz' } });
    expect(screen.getByText('일치하는 항목이 없습니다')).toBeInTheDocument();
  });
});

describe('NumberField', () => {
  it('shows the allowed range, reports only valid numbers and flags out-of-range text', () => {
    const onChange = vi.fn(), onInvalid = vi.fn();
    render(<NumberField label="확률" value={0.5} min={0} max={1} step={0.05} onChange={onChange} onInvalid={onInvalid} />);
    expect(screen.getByText('0~1')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('확률'), { target: { value: '' } });
    expect(onInvalid).toHaveBeenCalled(); expect(onChange).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toHaveTextContent('숫자를 입력');
    fireEvent.change(screen.getByLabelText('확률'), { target: { value: '1.5' } });
    expect(onChange).toHaveBeenCalledWith(1.5);
    expect(screen.getByRole('alert')).toHaveTextContent('허용 범위는 0~1');
  });
});

describe('Switch, Checkbox, Select, EmptyCard', () => {
  it('toggle with the keyboard-accessible controls', () => {
    const onSwitch = vi.fn(), onCheck = vi.fn(), onSelect = vi.fn();
    render(<><Switch label="마스킹 사용" checked onChange={onSwitch} /><Checkbox label="긴급 우선" checked={false} onChange={onCheck} /><Select label="상태" value="a" onChange={(e) => onSelect(e.target.value)}><option value="a">대기</option><option value="b">승인</option></Select><EmptyCard title="없음" action={<a href="/x">이동</a>}>설명</EmptyCard></>);
    fireEvent.click(screen.getByRole('switch', { name: '마스킹 사용' })); expect(onSwitch).toHaveBeenCalledWith(false);
    fireEvent.click(screen.getByRole('checkbox', { name: '긴급 우선' })); expect(onCheck).toHaveBeenCalledWith(true);
    fireEvent.change(screen.getByLabelText('상태'), { target: { value: 'b' } }); expect(onSelect).toHaveBeenCalledWith('b');
    expect(screen.getByText('설명')).toBeInTheDocument(); expect(screen.getByRole('link', { name: '이동' })).toBeInTheDocument();
  });
});
