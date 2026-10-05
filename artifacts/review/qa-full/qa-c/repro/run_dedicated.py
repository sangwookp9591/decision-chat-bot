"""Run fault + full regression + QA probes on an already-owned dedicated 7688 DB.

Start jevtriage-qa-c-neo4j on OrbStack with heap max 512m/pagecache 256m, then
execute backend/.venv/bin/python artifacts/review/qa-full/qa-c/repro/run_dedicated.py.
This runner only owns its subprocesses; it never stops a shared container.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

from neo4j import GraphDatabase

ROOT=Path(__file__).resolve().parents[5]
QA=Path(__file__).resolve().parents[1]
EVIDENCE=QA/'evidence'
EVIDENCE.mkdir(exist_ok=True)
ENV={**os.environ,'DOCKER_CONTEXT':'orbstack','NEO4J_URI':'bolt://127.0.0.1:7688',
     'NEO4J_PASSWORD':'development-only','JEV_MODE':'mock','REDIS_URL':'redis://127.0.0.1:11493/15',
     'DATA_DIR':str(EVIDENCE/'data'),'NEO4J_WRITE_TIMEOUT_SECONDS':'30',
     'PYTHONPATH':str(ROOT/'backend')+os.pathsep+str(QA/'repro')}
with GraphDatabase.driver(ENV['NEO4J_URI'],auth=('neo4j','development-only'),connection_timeout=3) as driver:
    for _ in range(600):
        try:
            driver.verify_connectivity()
            break
        except Exception:  # noqa: BLE001 - readiness retries never classify a product failure
            time.sleep(1)
    else:
        raise SystemExit('dedicated database did not become ready')

def run(name,args,env=ENV):
    with (EVIDENCE/(name+'.log')).open('w') as log:
        result=subprocess.run(args,cwd=ROOT/'backend',env=env,stdout=log,stderr=subprocess.STDOUT,check=False)
    print(name,result.returncode,flush=True)
    return result.returncode

fault=EVIDENCE/'fault'
fault.mkdir(exist_ok=True)
fault_env={**ENV,'T22_EVIDENCE_DIR':str(fault),'T22_FAULT_CONTAINER':'jevtriage-qa-c-neo4j',
           'DATA_DIR':str(fault/'data'),'REDIS_URL':''}
results={}
results['fault']=run('fault-final',[sys.executable,'-m','pytest','-q','tests/fault/scenarios.py',
          '-p','qa_fault_plugin','--tb=short','--junitxml='+str(fault/'junit.xml')],fault_env)
results['full_regression']=run('backend-full-pytest',[sys.executable,'-m','pytest','-q','--tb=short'],{**ENV,'REDIS_URL':''})
results['qa']=run('qa-pytest',[sys.executable,'-m','pytest','-q',str(QA/'repro'),
                             '--tb=short','--junitxml='+str(EVIDENCE/'qa-junit.xml')])
import json

(EVIDENCE/'run-exit-codes.json').write_text(json.dumps(results,indent=2))
