"""Offline backup/load count and canonical property comparison on owned QA containers."""
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from neo4j import GraphDatabase

ROOT=Path(__file__).resolve().parents[5]
EVIDENCE=Path(__file__).resolve().parents[1]/'evidence'
SOURCE=ROOT/'.data/neo4j-fault'
DUMP=ROOT/'.data/qa-c-backup'
RESTORE=ROOT/'.data/qa-c-restore'
APP=EVIDENCE/'data'
APP_RESTORE=ROOT/'.data/qa-c-restore-app'
ENV={**os.environ,'DOCKER_CONTEXT':'orbstack'}
NAME='jevtriage-qa-c-neo4j'
RESTORED='jevtriage-qa-c-restored'


def call(args):
    with (EVIDENCE/'backup-restore.log').open('a') as log:
        return subprocess.run(args,env=ENV,stdout=log,stderr=subprocess.STDOUT,check=True)


def graph():
    with GraphDatabase.driver('bolt://127.0.0.1:7688',auth=('neo4j','development-only'),connection_timeout=3) as d:
        for _ in range(600):
            try:
                d.verify_connectivity()
                break
            except Exception:  # noqa: BLE001 - bounded readiness only
                time.sleep(1)
        else:
            raise RuntimeError('restored QA DB failed to start')
        with d.session() as s:
            nodes=[dict(r) for r in s.run('MATCH (n) RETURN labels(n) AS labels,properties(n) AS properties ORDER BY n.id')]
            rels=[dict(r) for r in s.run('MATCH (a)-[r]->(b) RETURN a.id AS source,b.id AS target,type(r) AS type,properties(r) AS properties ORDER BY source,target,type')]
        def digest(rows):
            canonical=sorted(json.dumps(r,default=str,sort_keys=True) for r in rows)
            return hashlib.sha256('\n'.join(canonical).encode()).hexdigest()
        return {'nodes':len(nodes),'relationships':len(rels),'node_sha256':digest(nodes),'relationship_sha256':digest(rels)}


def files(folder):
    return {str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.rglob('*')) if p.is_file()}

before=graph()
app_before=files(APP)
assert not APP_RESTORE.exists()
for p in (DUMP,RESTORE):
    assert not p.exists(), 'backup/restore QA destination must be new'
    p.mkdir(mode=0o777)
    p.chmod(0o777)
try:
    call(['docker','stop',NAME])
    shutil.copytree(APP,DUMP/'application')
    shutil.copytree(DUMP/'application',APP_RESTORE)
    app_after=files(APP_RESTORE)
    call(['docker','run','--rm','--user','neo4j','-v',str(SOURCE)+':/data','-v',str(DUMP)+':/backups',
          'neo4j:5.26.0-community','neo4j-admin','database','dump','neo4j','--to-path=/backups'])
    dump_sha=hashlib.sha256((DUMP/'neo4j.dump').read_bytes()).hexdigest()
    call(['docker','run','--rm','--user','neo4j','-v',str(RESTORE)+':/data','-v',str(DUMP)+':/backups:ro',
          'neo4j:5.26.0-community','neo4j-admin','database','load','neo4j','--from-path=/backups'])
    call(['docker','run','-d','--name',RESTORED,'-p','127.0.0.1:7688:7687',
          '-e','NEO4J_AUTH=neo4j/development-only','-e','NEO4J_server_memory_heap_initial__size=256m',
          '-e','NEO4J_server_memory_heap_max__size=512m','-e','NEO4J_server_memory_pagecache_size=256m',
          '-v',str(RESTORE)+':/data','neo4j:5.26.0-community'])
    after=graph()
    result={'method':'Neo4j Community offline database dump/load','before':before,'after':after,
            'dump_sha256':dump_sha,'equal':before==after,'application_file_count':len(app_before),'application_files_equal':app_before==app_after,'application_file_hashes':app_after,'scope':'Neo4j neo4j database plus dedicated application data; system auth excluded'}
    (EVIDENCE/'backup-restore.json').write_text(json.dumps(result,indent=2))
    assert before==after and app_before==app_after
finally:
    subprocess.run(['docker','stop',RESTORED],env=ENV,capture_output=True,check=False)
    subprocess.run(['docker','rm',RESTORED],env=ENV,capture_output=True,check=False)
    subprocess.run(['docker','rm',NAME],env=ENV,capture_output=True,check=False)
    for p in (DUMP,RESTORE,SOURCE,APP_RESTORE):
        if p.exists():
            shutil.rmtree(p)
