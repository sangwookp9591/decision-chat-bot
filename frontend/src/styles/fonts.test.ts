import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

// Pretendard Variable dynamic-subset, trimmed: the unicode-range split is kept, only the weights the UI uses (400–700) and the
// slices that carry the app's characters or the common Hangul tiers are shipped. Regenerate with `node scripts/build-fonts-css.mjs`.
const fontCss = readFileSync('src/styles/pretendard-subset.css', 'utf8');
const faces = [...fontCss.matchAll(/@font-face\{[^}]*\}/g)].map((m) => m[0]);
const ranges = faces.flatMap((f) => (f.match(/unicode-range:([^;}]*)/)?.[1] ?? '').split(',').map((s) => s.trim().replace('U+', '').split('-').map((h) => parseInt(h, 16))));
const covered = (cp: number) => ranges.some(([a, b]) => cp >= a && cp <= (b ?? a));
function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) { const p = join(dir, name); if (statSync(p).isDirectory()) walk(p, out); else if (/\.(tsx?|css)$/.test(name) && !/\.test\./.test(name)) out.push(p); }
  return out;
}

describe('font subset', () => {
  it('keeps unicode-range slicing with far fewer faces than the 92 upstream', () => {
    expect(faces.length).toBeGreaterThan(10); expect(faces.length).toBeLessThanOrEqual(30);
    for (const f of faces) expect(f).toMatch(/unicode-range:/);
  });
  it('declares only the used weight range 400–700', () => { for (const f of faces) expect(f).toContain('font-weight:400 700'); });
  it('the app imports the trimmed file, not the upstream 92-face CSS', () => {
    const style = readFileSync('src/style.css', 'utf8');
    expect(style).toContain('./styles/pretendard-subset.css'); expect(style).not.toContain('pretendardvariable-dynamic-subset.css');
  });
  it('covers every non-ASCII character that appears in app source', () => {
    const missing = new Set<string>();
    for (const file of walk('src')) for (const ch of readFileSync(file, 'utf8')) { const cp = ch.codePointAt(0)!; if (cp >= 0x2000 && cp <= 0xd7a3 && cp >= 0xac00 && !covered(cp)) missing.add(ch); }
    expect([...missing]).toEqual([]);
  });
  it('uses no font weight outside the shipped range', () => {
    const bad: string[] = [];
    for (const file of walk('src').filter((p) => p.endsWith('.css'))) for (const m of strip(readFileSync(file, 'utf8')).matchAll(/font-weight:\s*(\d+)/g)) if (+m[1] > 700 || +m[1] < 400) bad.push(`${file}:${m[1]}`);
    expect(bad).toEqual([]);
  });
});
function strip(s: string) { return s.replace(/\/\*[\s\S]*?\*\//g, ''); }
