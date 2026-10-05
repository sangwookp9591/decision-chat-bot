"""Seeded stratified random selection from completed capability test groups."""
import random
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[4]
scratch = Path(__file__).resolve().parent
rows = (scratch / 'collected-tests.log').read_text().splitlines()
groups = ['test_ingest_api.py', 'test_parsers.py', 'test_judgment_service.py',
          'test_review_assignment.py', 'test_policy_versions.py', 'test_observe_api.py',
          'test_sse_events.py', 'test_monitoring_collector.py', 'test_rules_integration.py',
          'test_judgment_graph.py']
rng = random.Random(20261005)
selected = [rng.choice([row for row in rows if f'/{name}::' in row]) for name in groups]
command = ['.venv/bin/pytest', '-vv', *selected]
(scratch / 'audit-spec-random-command.txt').write_text('cd backend && ' + ' '.join(command) + '\n')
with (scratch / 'audit-spec-random-tests.log').open('w') as output:
    result = subprocess.run(command, cwd=root / 'backend', stdout=output, stderr=subprocess.STDOUT)
print((scratch / 'audit-spec-random-tests.log').read_text())
raise SystemExit(result.returncode)
