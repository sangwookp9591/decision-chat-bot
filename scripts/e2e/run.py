"""Run browser E2E against an isolated mock service; always stop owned processes.

Usage: backend/.venv/bin/python scripts/e2e/run.py [Playwright arguments]
"""
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/review/e2e-all' / time.strftime('%Y%m%dT%H%M%S')
OUT.mkdir(parents=True)
TENANT = 't-e2e-' + time.strftime('%m%d%H%M%S')
env = dict(os.environ, AI_MODE='mock', E2E_TENANT=TENANT, UX2_TENANT=TENANT,
           E2E_REQUESTER=f'requester@{TENANT}.dev', E2E_BASE_URL='http://127.0.0.1:8491',
           DATA_DIR=str(OUT / 'data'), REDIS_URL='', A11Y_SHOT_DIR=str(OUT / 'a11y'),
           CHAT_SHOT_DIR=str(OUT / 'chat'), POLISH_SHOT_DIR=str(OUT / 'polish'),
           ACC_UI_OUT=str(OUT / 'acceptance'), ACC_RECORDS=str(OUT / 'gate-records.jsonl'), REM_SHOT_DIR=str(OUT / 'rem'),
           PLAYWRIGHT_JSON_OUTPUT_NAME=str(OUT / 'results.json'))
py = str(ROOT / 'backend/.venv/bin/python')
processes = []

def start(name, args, cwd, extra=None):
    with open(OUT / f'{name}.log', 'w') as log:
        process = subprocess.Popen(args, cwd=cwd, env=dict(env, **(extra or {})),
                                   stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
    processes.append(process)
    if name == 'api':
        env['E2E_API_PID'] = str(process.pid)

try:
    subprocess.run([py, str(ROOT / 'scripts/e2e/seed.py')], cwd=ROOT, env=env, check=True)
    start('api', [py, '-m', 'uvicorn', 'ildongi.main:app', '--host', '127.0.0.1', '--port', '11091'], ROOT / 'backend')
    start('worker', [py, str(ROOT / 'scripts/e2e/mock_worker.py'), '--tenant', TENANT, '--tenant', TENANT+'g'], ROOT / 'backend')
    start('fault-worker', [py, '-m', 'ildongi.jobs.worker', '--tenant', TENANT+'f', '--max-attempts', '1'], ROOT / 'backend', {'AI_MOCK_FAULT': 'schema'})
    start('vite', ['node', 'node_modules/vite/bin/vite.js', '--config', 'e2e/vite.all.config.ts'], ROOT / 'frontend')
    for _ in range(100):
        if any(p.poll() is not None for p in processes):
            raise RuntimeError('Owned service exited; see logs')
        try:
            urllib.request.urlopen(env['E2E_BASE_URL'], timeout=1)
            break
        except OSError:
            time.sleep(.2)
    print('Browser log:', OUT / 'results.log', flush=True)
    with open(OUT / 'results.log', 'w') as log:
        result = subprocess.run(['npx', 'playwright', 'test', '--config=e2e/all.config.ts', '--workers=1', '--reporter=list,json',
                                 '--output='+str(OUT / 'results'), *(sys.argv[1:] or ['--grep-invert', r'T38|\[X0|\[F[345]'])], cwd=ROOT / 'frontend', env=env, check=False,
                                stdout=log, stderr=subprocess.STDOUT)
    extension = subprocess.run([py, str(ROOT / 'scripts/e2e/extension_suite.py')], cwd=ROOT, env=env, check=False) if len(sys.argv) == 1 else None
    code = max(result.returncode, extension.returncode if extension else 0)
    (OUT / 'run.json').write_text(json.dumps({'tenant': TENANT, 'mode': 'mock-fixture', 'exit_code': code}))
    sys.exit(code)
finally:
    for process in reversed(processes):
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
    for process in processes:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    print('Evidence:', OUT)
