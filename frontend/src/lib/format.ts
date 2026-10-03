export function formatTime(value: unknown, options: Intl.DateTimeFormatOptions = {}): string {
  if (value === null || value === undefined || value === '') return '—';
  const date = value instanceof Date ? value : new Date(String(value));
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString('ko-KR', options);
}

export function percent(value: number | null | undefined, digits = 1, missing = '미수집'): string {
  return value === null || value === undefined ? missing : `${(value * 100).toFixed(digits)}%`;
}
