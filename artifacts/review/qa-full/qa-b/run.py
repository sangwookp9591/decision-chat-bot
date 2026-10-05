"""Run browser E2E against an isolated mock service; always stop owned processes.

Usage: backend/.venv/bin/python artifacts/review/qa-full/qa-b/run.py [Playwright arguments]
"""
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'artifacts/review/qa-full/qa-b/runtime'
OUT.mkdir(parents=True)
TENANT = 't-qa-b-' + time.strftime('%m%d%H%M%S')
(OUT / 'STOP').unlink(missing_ok=True)
(OUT / 'tenant.txt').write_text(TENANT)
env = dict(os.environ, JEV_MODE='mock', E2E_TENANT=TENANT, UX2_TENANT=TENANT,
           E2E_REQUESTER=f'requester@{TENANT}.dev', E2E_BASE_URL='http://127.0.0.1:8791',
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
    start('api', [py, '-m', 'uvicorn', 'jevtriage.main:app', '--host', '127.0.0.1', '--port', '11391'], ROOT / 'backend')
    start('worker', [py, str(ROOT / 'scripts/e2e/mock_worker.py'), '--tenant', TENANT, '--tenant', TENANT+'g'], ROOT / 'backend')
    start('vite', ['node', 'node_modules/vite/bin/vite.js', '--config', str(ROOT / 'artifacts/review/qa-full/qa-b/vite.config.ts')], ROOT / 'frontend')
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
        result = subprocess.run(['npx', 'playwright', 'test', '--config='+str(ROOT / 'artifacts/review/qa-full/qa-b/playwright.config.ts'), '--workers=1', '--reporter=list,json',
                                 '--output='+str(OUT / 'results'), *(sys.argv[1:] or ['policy.spec.ts|monitoring.spec.ts|learning-human.spec.ts|evaluation-labels.spec.ts|judgment-map.spec.ts'])], cwd=ROOT / 'frontend', env=env, check=False,
                                stdout=log, stderr=subprocess.STDOUT)
    code = result.returncode
    (OUT / 'run.json').write_text(json.dumps({'tenant': TENANT, 'mode': 'mock-fixture', 'exit_code': code}))
    (OUT / 'ready').write_text(TENANT)
    deadline = time.monotonic() + 1800
    while not (OUT / 'STOP').exists() and time.monotonic() < deadline:
        time.sleep(1)
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
