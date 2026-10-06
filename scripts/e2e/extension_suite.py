"""Self-contained extension fixture and browser phases, using the runner's mock API."""
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ['ACC_UI_OUT']).parent / 'extension'
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'screenshots').mkdir(exist_ok=True)
TENANT = os.environ['E2E_TENANT'] + 'x'
env = {**os.environ, 'X38_TENANT': TENANT, 'X38_OUT': str(OUT),
       'X38_API': os.environ['E2E_BASE_URL'], 'X38_SUFFIX': 'ui1'}
assert env['AI_MODE'] == 'mock'
py = str(ROOT / 'backend/.venv/bin/python')
worker = None
restarted_api = None
exit_codes = []


def stages(*names, suffix='ui1'):
    with open(OUT / ('setup-' + '-'.join(names) + '.log'), 'w') as log:
        subprocess.run([py, str(ROOT / 'scripts/e2e/extension_seed.py'), *names], cwd=ROOT / 'backend',
                       env={**env, 'X38_SUFFIX': suffix}, stdout=log, stderr=subprocess.STDOUT, check=True)


def browser(phase, truth, spec, grep):
    with open(OUT / f'{phase}.log', 'w') as log:
        result = subprocess.run(['npx', 'playwright', 'test', '--config=e2e/all.config.ts', spec,
                                 '--grep', grep, '--workers=1', '--reporter=list,json',
                                 '--output='+str(OUT / f'{phase}-results')], cwd=ROOT / 'frontend',
                                env={**env, 'X38_PHASE': phase, 'X38_TRUTH': truth,
                                     'PLAYWRIGHT_JSON_OUTPUT_NAME': str(OUT / f'{phase}.json')},
                                stdout=log, stderr=subprocess.STDOUT, check=False)
    exit_codes.append(result.returncode)


try:
    subprocess.run([py, 'tests/acceptance/provision.py', TENANT, TENANT+'i'], cwd=ROOT / 'backend', env=env, check=True)
    def start_worker():
        return subprocess.Popen([py, str(ROOT / 'scripts/e2e/mock_worker.py'), '--tenant', TENANT, '--tenant', TENANT+'i'],
                                cwd=ROOT / 'backend', env=env, stdout=open(OUT / 'worker.log', 'a'), stderr=subprocess.STDOUT)
    worker = start_worker()
    stages('seed', 'corrections', 'rules', 'apply', 'insufficient', 'chain_lead', 'chain_evidence', 'graph', 'evidence_layer', 'invariants', 'export')
    browser('ui1', 'ui1', 'extension/extension.spec.ts$', 'before stop')
    browser('r1', 'ui1', 'extension/extension-r.spec.ts$', 'T38-R fixes')
    stages('lifecycle', 'graph', 'snapshot', suffix='pre')
    browser('ui2', 'pre', 'extension/extension.spec.ts$', 'map filters|lifecycle and persistence')
    worker.send_signal(signal.SIGTERM)
    worker.wait(timeout=30)
    worker = start_worker()
    if env.get('E2E_API_PID'):
        os.kill(int(env['E2E_API_PID']), signal.SIGTERM)
        time.sleep(2)
        with open(OUT / 'api-restarted.log', 'w') as log:
            restarted_api = subprocess.Popen([py, '-m', 'uvicorn', 'ildongi.main:app', '--host', '127.0.0.1', '--port', '11091'], cwd=ROOT / 'backend', env=env, stdout=log, stderr=subprocess.STDOUT)
        for _ in range(100):
            if restarted_api.poll() is not None:
                raise RuntimeError('Restarted API exited')
            try:
                urllib.request.urlopen('http://127.0.0.1:11091/api/health', timeout=1)
                break
            except OSError:
                time.sleep(.2)
    browser('r3', 'pre', 'extension/extension-r.spec.ts$', 'after restart')
finally:
    if restarted_api and restarted_api.poll() is None:
        restarted_api.send_signal(signal.SIGTERM)
        restarted_api.wait(timeout=30)
    if worker and worker.poll() is None:
        worker.send_signal(signal.SIGTERM)
        worker.wait(timeout=30)
sys.exit(max(exit_codes, default=1))
