"""Own only the five child processes; always reap them and leave shared containers up."""
import datetime, json, os, signal, socket, subprocess, sys, time, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now(datetime.UTC).strftime('%Y%m%dT%H%M%SZ')
OUT = ROOT / 'artifacts/demo' / STAMP
OUT.mkdir(parents=True)
(OUT/'raw').mkdir()
env = dict(os.environ, DEMO_OUT=str(OUT), DEMO_TENANT='t-demo-'+STAMP.lower(), DATA_DIR=str(OUT/'raw/data'), JEV_MODE='live', REDIS_URL='redis://127.0.0.1:6379/0', MONITORING_WEBHOOK_URL='', PYTHONDONTWRITEBYTECODE='1')
env['DEMO_COMMIT']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
children=[]
logs=[]
py=str(ROOT/'backend/.venv/bin/python')
def start(name,args,cwd=ROOT):
    log=open(OUT/'raw'/f'{name}.log','w'); logs.append(log)
    p=subprocess.Popen(args,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True); children.append(p)
    return p
try:
    for port in (9191,6491):
        with socket.socket() as sock:
            if sock.connect_ex(('127.0.0.1',port))==0: raise RuntimeError(f'Port {port} already in use; refusing to replace process')
    subprocess.run([py,'scripts/demo/provision.py',env['DEMO_TENANT'],env['DEMO_TENANT']+'b'],cwd=ROOT,env=env,check=True,stdout=subprocess.DEVNULL)
    start('api',[py,'-m','uvicorn','jevtriage.main:app','--host','127.0.0.1','--port','9191'],ROOT/'backend')
    start('worker',[py,'-m','jevtriage.jobs.worker','--tenant',env['DEMO_TENANT']],ROOT/'backend')
    start('collector',[py,'-m','jevtriage.journal.collector'],ROOT/'backend')
    start('watchdog',[py,'-m','jevtriage.journal.watchdog'],ROOT/'backend')
    start('vite',['node','scripts/demo/vite.mjs'])
    for url in ('http://127.0.0.1:9191/api/ready','http://127.0.0.1:6491'):
        for i in range(60):
            try:
                urllib.request.urlopen(url,timeout=2); break
            except Exception: time.sleep(1)
        else: raise RuntimeError('Startup timeout '+url)
    print('DEMO_OUT='+str(OUT),flush=True)
    result=subprocess.run(['node','scripts/demo/record.mjs'],cwd=ROOT,env=env)
    if result.returncode: raise RuntimeError('Recording script failed')
except Exception as exc:
    if not (OUT/'README.md').exists():
        (OUT/'README.md').write_text('# 녹화 실행 실패\n\n'+str(exc)+'\n\n재실행: `bash scripts/demo/record.sh`\n')
    raise
finally:
    for p in reversed(children):
        if p.poll() is None: os.killpg(p.pid,signal.SIGTERM)
    for p in children:
        try:p.wait(timeout=15)
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
    for log in logs:log.close()
    health=subprocess.run(['docker','--context','orbstack','ps','--format','{{.Names}} {{.Status}}'],capture_output=True,text=True).stdout
    (OUT/'health.txt').write_text(health)
    if (OUT/'README.md').exists():
        with (OUT/'README.md').open('a') as report:
            report.write('\n## 종료 확인\n\n소유한 API·worker·collector·watchdog·Vite 자식 프로세스 종료 확인.\n\n```text\n'+health+'```\n')
    print('All demo child processes stopped. '+health,flush=True)
