import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

// vitest strips CSS from ?raw imports, so read the file directly (run from frontend/).
const css = readFileSync('src/styles/tokens.css', 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
function block(selector: string): Record<string, string> {
  const start = css.indexOf(`${selector} {`); const body = css.slice(css.indexOf('{', start) + 1, css.indexOf('\n}', start));
  return Object.fromEntries([...body.matchAll(/(--[\w-]+):\s*([^;]+);/g)].map((m) => [m[1], m[2].trim()]));
}
function theme(overrides: Record<string, string> = {}) {
  const vars = { ...block(':root'), ...overrides };
  const resolve = (name: string, depth = 0): string => { const v = vars[name]; const ref = v?.match(/^var\((--[\w-]+)\)$/); return ref && depth < 5 ? resolve(ref[1], depth + 1) : v; };
  return resolve;
}
const lum = (hex: string) => { const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)); return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]; };
const ratio = (a: string, b: string) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };

describe('design tokens — AA contrast (4.5:1 for text)', () => {
  const light = theme();
  const dark = theme(block(":root[data-theme='dark']"));
  const pairs: [string, string][] = [
    ['--color-on-primary', '--color-primary'], ['--color-ink', '--color-surface'], ['--color-ink', '--color-ground'],
    ['--color-ink-2', '--color-surface'], ['--color-ink-2', '--color-ground'], ['--color-caption', '--color-surface'], ['--color-caption', '--color-ground'], ['--color-caption', '--color-surface-2'],
    ['--color-primary-ink', '--color-surface'], ['--color-primary-ink', '--color-ground'], ['--color-primary-ink', '--color-primary-tint'], ['--color-primary-ink', '--status-active-bg'],
    ['--status-success-text', '--status-success-bg'], ['--status-fail', '--status-fail-bg'], ['--status-fail', '--color-surface'], ['--status-warn', '--status-warn-bg'], ['--status-review-text', '--status-review-bg'],
    ['--color-ink-2', '--color-fill'],
    ['--color-on-secondary', '--color-secondary'], ['--color-on-danger', '--status-fail'], ['--color-secondary-ink', '--color-secondary-tint'], ['--color-secondary-ink', '--color-surface'], ['--color-secondary-ink', '--color-ground'],
  ];
  it.each(pairs)('light %s on %s', (fg, bg) => expect(ratio(light(fg), light(bg))).toBeGreaterThanOrEqual(4.5));
  it.each(pairs.filter(([fg]) => fg !== '--color-on-primary'))('dark %s on %s', (fg, bg) => expect(ratio(dark(fg), dark(bg))).toBeGreaterThanOrEqual(4.5));
  it('keeps the brand colors and the on-orange text rule', () => {
    expect(light('--color-primary')).toBe('#F15921'); expect(light('--color-secondary')).toBe('#0E7C86'); expect(light('--color-on-primary')).toBe('#1B1712');
  });
  it('matches TDS light greys', () => { expect(light('--color-ground')).toBe('#f2f4f6'); expect(light('--color-line')).toBe('#e5e8eb'); expect(light('--color-ink')).toBe('#191f28'); });
});
