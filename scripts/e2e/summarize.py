"""Roll up latest executed outcomes by file/test/browser; never turn an unrun test green."""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/review/e2e-all'
rows = {}


def specs(suite, parents=()):
    name = re.sub(r'^\[(?:ui|r)\d+\]\s*', '', suite.get('title', ''))
    chain = parents + ((name,) if name and not name.endswith('.spec.ts') else ())
    for spec in suite.get('specs', []):
        yield spec, ' > '.join((*chain, spec['title']))
    for child in suite.get('suites', []):
        yield from specs(child, chain)


paths = [*OUT.glob('*.json'), *OUT.glob('20*/results.json'), *OUT.glob('20*/extension/*.json')]
for path in sorted(paths, key=lambda p: p.stat().st_mtime):
    if path.name.startswith('live-'):
        continue
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or 'suites' not in data:
        continue
    for suite in data['suites']:
        for spec, title in specs(suite):
            for test in spec['tests']:
                key = (spec['file'].removeprefix('e2e/'), title, test['projectName'])
                log = str(path.relative_to(OUT).with_suffix('.log'))
                rows.setdefault(key, {'status': 'not run', 'log': log})
                result = (test.get('results') or [{}])[-1]
                status = result.get('status')
                annotations = test.get('annotations', []) + result.get('annotations', [])
                reasons = [a.get('description', '') for a in annotations if a['type'] == 'skip']
                if status == 'skipped' and (not reasons or 'phase' in ' '.join(reasons) or 'ui2/ui3' in ' '.join(reasons) or 'run once' in ' '.join(reasons)):
                    continue
                if status not in ('passed', 'failed', 'timedOut', 'interrupted', 'skipped'):
                    continue
                # A later unrelated phase skip cannot erase a real execution.
                if status == 'skipped' and rows[key]['status'] in ('passed', 'failed', 'timedOut'):
                    continue
                rows[key] = {'status': status, 'log': log, 'reason': '; '.join(dict.fromkeys(reasons)),
                             'duration_ms': result.get('duration', 0)}

counts = defaultdict(Counter)
skip_reasons = defaultdict(set)
for (file, title, browser), result in rows.items():
    counts[(file, browser)][result['status']] += 1
    if result['status'] == 'skipped':
        skip_reasons[(file, browser)].add(result.get('reason', ''))
lines = ['| 파일 | 브라우저 | 통과 | 실패 | skip | 미실행 | skip 사유 |', '|---|---|---:|---:|---:|---:|---|']
for (file, browser), count in sorted(counts.items()):
    reason = '; '.join(sorted(skip_reasons[(file, browser)]))
    lines.append(f'| {file} | {browser} | {count["passed"]} | {count["failed"] + count["timedOut"] + count["interrupted"]} | {count["skipped"]} | {count["not run"]} | {reason} |')
(OUT / 'TABLE.md').write_text('\n'.join(lines)+'\n')
(OUT / 'latest-results.json').write_text(json.dumps([{'file': f, 'title': t, 'browser': b, **v} for (f,t,b),v in sorted(rows.items())], ensure_ascii=False, indent=2))
print(Counter(v['status'] for v in rows.values()))
for key, value in rows.items():
    if value['status'] != 'passed':
        print(key, value['status'], value.get('reason', ''), value['log'])
