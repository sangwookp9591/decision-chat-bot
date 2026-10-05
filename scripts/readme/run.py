"""Run an isolated LIVE README capture; reap only processes started here."""
import datetime
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(tempfile.mkdtemp(prefix='jev-readme-'))
TENANT = 't-readme-' + datetime.datetime.now(datetime.UTC).strftime('%m%d%H%M%S')
env = dict(os.environ, README_OUT=str(OUT), README_TENANT=TENANT, DATA_DIR=str(OUT/'data'), JEV_MODE='live', REDIS_URL='redis://127.0.0.1:6379/0', MONITORING_WEBHOOK_URL='', PYTHONDONTWRITEBYTECODE='1')
py = str(ROOT/'backend/.venv/bin/python')
children, logs = [], []
def start(name, args, cwd=ROOT):
    log = (OUT/f'{name}.log').open('w'); logs.append(log)
    child = subprocess.Popen(args, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    children.append(child)
try:
    for port in (10491, 7791):
        with socket.socket() as sock:
            if sock.connect_ex(('127.0.0.1', port)) == 0:
                raise RuntimeError(f'Port {port} occupied; refusing to replace process')
    subprocess.run([py,'scripts/demo/provision.py',TENANT],cwd=ROOT,env=env,check=True,stdout=subprocess.DEVNULL)
    start('api',[py,'-m','uvicorn','jevtriage.main:app','--host','127.0.0.1','--port','10491'],ROOT/'backend')
    start('worker',[py,'-m','jevtriage.jobs.worker','--tenant',TENANT],ROOT/'backend')
    start('collector',[py,'-m','jevtriage.journal.collector'],ROOT/'backend')
    start('watchdog',[py,'-m','jevtriage.journal.watchdog'],ROOT/'backend')
    start('vite',['node','scripts/readme/vite.mjs'])
    for url in ('http://127.0.0.1:10491/api/ready','http://127.0.0.1:7791'):
        for _ in range(60):
            try:
                urllib.request.urlopen(url,timeout=2); break
            except Exception:
                time.sleep(1)
        else:
            raise RuntimeError('Startup timeout '+url)
    (Path('/tmp')/'jev-readme-session.json').write_text(json.dumps({'out':str(OUT),'tenant':TENANT}))
    print('READY '+str(OUT),flush=True)
    subprocess.run([py,'scripts/readme/seed.py'],cwd=ROOT,env=env,check=True)
    if '--manual' in sys.argv:
        while not (OUT/'stop').exists():
            time.sleep(1)
    else:
        with (ROOT/'scripts/readme/capture.mjs').open() as script:
            subprocess.run(['ego-browser','nodejs'],stdin=script,cwd=ROOT,env=env,check=True)
        subprocess.run([py,'scripts/readme/optimize.py',str(OUT)],cwd=ROOT,check=True)
finally:
    for child in reversed(children):
        if child.poll() is None:
            os.killpg(child.pid,signal.SIGTERM)
    for child in children:
        try:
            child.wait(timeout=15)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid,signal.SIGKILL); child.wait()
    for log in logs:
        log.close()
    print('README child processes stopped; shared containers unchanged.',flush=True)
