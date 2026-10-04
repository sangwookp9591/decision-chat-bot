import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

// Screen styles (everything except the requester chat, which CHAT-POLISH owns) read design tokens by name.
// The only allowed literals live in *-stage.css: the judgment map's fixed dark scene is independent of the app theme.
const strip = (s: string) => s.replace(/\/\*[\s\S]*?\*\//g, '');
const css = (path: string) => strip(readFileSync(path, 'utf8'));
const screenCss = [
  'src/style.css', 'src/components/EvidenceViewer.css', 'src/components/ui.css', 'src/components/fields.css',
  ...['review', 'tasks', 'observatory', 'monitoring', 'policy', 'learning', 'evaluation', 'judgment-map'].map((d) => `src/pages/${d}/${d}.css`),
];
const literalColor = /#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(/g;

describe('screen CSS has no hard-coded design values', () => {
  it.each(screenCss)('%s uses tokens for color, radius and font', (file) => {
    const text = css(file);
    expect(text.match(literalColor) ?? [], 'literal colors').toEqual([]);
    expect(text.match(/border-radius:\s*[1-9]\d*px/g) ?? [], 'fixed radii').toEqual([]);
    expect(text.match(/font-family:\s*(?!var\()[^;}]+/g) ?? [], 'direct font-family').toEqual([]);
  });
  it('fixed dark stage literals are fenced into a separate file', () => {
    const stage = readdirSync('src/pages/judgment-map').filter((f) => f.endsWith('-stage.css'));
    expect(stage).toEqual(['judgment-map-stage.css']);
  });
});

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) { const p = join(dir, name); if (statSync(p).isDirectory()) walk(p, out); else out.push(p); }
  return out;
}

describe('page eyebrows are short Korean labels, not English caps', () => {
  const pages = walk('src/pages').concat(walk('src/layout')).filter((p) => /\.tsx$/.test(p) && !/\.test\./.test(p) && !p.includes('/main/') && !p.endsWith('Main.tsx'));
  it.each(pages)('%s', (file) => {
    for (const m of readFileSync(file, 'utf8').matchAll(/className="eyebrow">([^<]*)</g)) expect(m[1], 'eyebrow text').not.toMatch(/[A-Z]{3,}/);
  });
});

describe('dark theme follows the OS without data-theme', () => {
  const tokens = css('src/styles/tokens.css');
  it('has an automatic prefers-color-scheme block that respects a manual light choice', () => {
    expect(tokens).toMatch(/@media \(prefers-color-scheme: dark\)\s*\{\s*:root:not\(\[data-theme='light'\]\)/);
  });
  it('keeps manual data-theme dark', () => { expect(tokens).toContain(":root[data-theme='dark']"); });
});

describe('entrance motion stays deterministic for first paint and axe', () => {
  const motion = css('src/styles/motion.css');
  it('list stagger only runs after the first in-app navigation', () => {
    expect(motion).toMatch(/:root\[data-motion='route'\]\s*\.m-stagger\s*>\s*\*\s*\{/);
    expect(motion).not.toMatch(/(^|\n)\.m-stagger\s*>\s*\*\s*\{/);
  });
  it('reduced motion collapses every animation and transition', () => { expect(motion).toMatch(/prefers-reduced-motion: reduce[\s\S]*animation-duration: 0\.001ms !important[\s\S]*transition-duration: 0\.001ms !important/); });
});
