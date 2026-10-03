"""Real-process fault tests, selected only by ``make test-fault``."""
from __future__ import annotations

import asyncio
import json
import os
import signal
import socket
import sqlite3
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from jevtriage.auth.core import hash_password
from jevtriage.db.schema import apply_schema
from jevtriage.db.tx import read_tx, write_tx
from jevtriage.policy.service import bootstrap_policy

pytestmark = pytest.mark.asyncio
ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(os.environ["T22_EVIDENCE_DIR"])
CONTAINER = os.environ["T22_FAULT_CONTAINER"]
TENANT = f"t22_{uuid4().hex[:12]}"
PASSWORD = "dev-only-change-me"


def record(name: str, status: str, **details) -> None:
    path = EVIDENCE / "scenarios.jsonl"
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"scenario": name, "status": status, **details},
                                ensure_ascii=False, default=str) + "\n")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


async def wait_until(predicate, timeout=15, interval=0.1):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = await predicate()
        if value:
            return value
        await asyncio.sleep(interval)
    raise AssertionError(f"condition not met within {timeout}s")


class Harness:
    def __init__(self):
        self.port = free_port()
        self.procs = {}
        self.logs = {}
        self.base = f"http://127.0.0.1:{self.port}"
        self.data = Path(os.environ["DATA_DIR"])

    def start(self, name, module, *args, extra_env=None):
        if name in self.procs:
            self.stop(name)
        env = {**os.environ, **(extra_env or {})}
        path = EVIDENCE / f"{name}.log"
        log = path.open("a", encoding="utf-8")
        proc = subprocess.Popen([sys.executable, "-m", module, *map(str, args)],
                                cwd=ROOT / "backend", env=env, stdout=log,
                                stderr=subprocess.STDOUT, start_new_session=True)
        self.procs[name], self.logs[name] = proc, log
        return proc

    def stop(self, name, sig=signal.SIGTERM):
        proc = self.procs.pop(name, None)
        if proc:
            if proc.poll() is None:
                os.killpg(proc.pid, sig)
                try:
                    proc.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait(timeout=5)
            self.logs.pop(name).close()

    async def api(self):
        self.start("api", "uvicorn", "jevtriage.main:app", "--host", "127.0.0.1",
                   "--port", self.port, "--no-access-log")
        async with httpx.AsyncClient(base_url=self.base) as client:
            async def ready():
                try:
                    return (await client.get("/api/ready", timeout=1)).status_code == 200
                except httpx.HTTPError:
                    return False
            await wait_until(ready, timeout=20)

    def worker(self, name="worker", *, fault="", delay="0", lease="2"):
        return self.start(name, "jevtriage.jobs.worker", "--tenant", TENANT,
                          "--lease-seconds", lease, "--poll-seconds", "0.1",
                          "--deadline-seconds", "30", "--max-attempts", "3",
                          extra_env={"JEV_MOCK_FAULT": fault,
                                     "JEV_MOCK_DELAY_SECONDS": delay})

    async def login(self, role):
        client = httpx.AsyncClient(base_url=self.base, timeout=20)
        response = await client.post("/api/auth/login", json={
            "email": f"{role}@{TENANT}.dev", "password": PASSWORD})
        assert response.status_code == 200, (role, response.status_code, response.text)
        client.headers["X-CSRF-Token"] = client.cookies["jev_csrf"]
        return client

    async def submit(self, client, text="Test request for a monthly CSV dashboard"):
        key = uuid4().hex
        response = await client.post("/api/requests", data={"text": text},
                                     headers={"Idempotency-Key": key})
        assert response.status_code == 202, (response.status_code, response.text)
        return response.json()

    async def graph(self, query, **params):
        async def op(tx):
            rows = await tx.run(query, tenant=TENANT, **params)
            return [dict(row) async for row in rows]
        return await read_tx(TENANT, op)

    async def run_state(self, request_id):
        rows = await self.graph(
            "MATCH (q:Request {tenant_id:$tenant,id:$id}) "
            "MATCH (r:Run {tenant_id:$tenant,id:q.active_run_id}) "
            "OPTIONAL MATCH (j:Job {tenant_id:$tenant,run_id:r.id}) "
            "RETURN q.status AS request_status,r.id AS run_id,r.status AS run_status,"
            "r.versions_json AS versions,r.attempts_json AS attempts,j.status AS job_status,"
            "j.owner_id AS owner,j.lease_generation AS generation",
            id=request_id)
        return rows[0] if rows else None

    async def terminal(self, request_id, timeout=20):
        async def done():
            state = await self.run_state(request_id)
            return state if state and state["run_status"] in {"failed", "judgment_saved"} else None
        return await wait_until(done, timeout=timeout)

    def journal(self):
        path = self.data / "journal" / "current.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


@pytest.fixture(scope="module")
async def harness():
    await apply_schema()
    await bootstrap_policy(TENANT)
    password_hash = hash_password(PASSWORD)
    async def create_users(tx):
        orgs = [f"{TENANT}-{name}" for name in ("business", "it", "ai")]
        await (await tx.run(
            "MERGE (t:Tenant {id:$tenant,tenant_id:$tenant}) "
            "WITH t UNWIND $orgs AS org "
            "MERGE (o:Org {id:org,tenant_id:$tenant}) MERGE (t)-[:HAS_ORG]->(o)",
            tenant=TENANT, orgs=orgs)).consume()
        await (await tx.run(
            "UNWIND $roles AS role "
            "CREATE (u:User {id:randomUUID(),tenant_id:$tenant,email:role+'@'+$tenant+'.dev',"
            "password_hash:$password_hash,disabled:false,can_read_source:false}) "
            "WITH u,role MATCH (o:Org {tenant_id:$tenant}) WHERE o.id IN $orgs "
            "CREATE (u)-[:MEMBER_OF {role:CASE WHEN role='reviewer2' THEN 'reviewer' ELSE role END}]->(o)",
            tenant=TENANT, orgs=orgs,
            roles=["requester", "reviewer", "reviewer2", "operator", "policy_editor"],
            password_hash=password_hash)).consume()
    await write_tx(TENANT, create_users)
    h = Harness()
    h.start("collector", "jevtriage.journal.collector", "--interval", "0.2")
    h.start("watchdog", "jevtriage.journal.watchdog", "--interval", "0.5",
            "--stale-seconds", "2")
    await h.api()
    yield h
    for name in list(h.procs):
        h.stop(name, signal.SIGKILL)
    record("process_cleanup", "pass", remaining={n: p.poll() for n, p in h.procs.items()})


@pytest.mark.parametrize("fault", ["timeout", "429", "529", "schema"])
async def test_jev_faults(harness, fault):
    h = harness
    client = await h.login("requester")
    try:
        request = await h.submit(client, f"Jev fault {fault} {uuid4().hex}")
        h.worker(f"worker_jev_{fault}", fault=fault)
        state = await h.terminal(request["request_id"])
        assignments = await h.graph(
            "MATCH (a:Assignment {tenant_id:$tenant,request_id:$id}) RETURN count(a) AS n",
            id=request["request_id"])
        assert state["run_status"] == "failed" and assignments[0]["n"] == 0
        record(f"jev_{fault}", "pass", request_id=request["request_id"], state=state["run_status"],
               assignments=0, mode="mock")
    finally:
        h.stop(f"worker_jev_{fault}")
        await client.aclose()


async def test_parser_and_db_outage(harness):
    h = harness
    client = await h.login("requester")
    try:
        bad = await client.post("/api/requests", data={"text": "Inspect attachment"},
                                files={"files": ("broken.pdf", b"%PDF-1.7 corrupt", "application/pdf")},
                                headers={"Idempotency-Key": uuid4().hex})
        assert bad.status_code == 202
        assert bad.json()["status"] == "needs_file_decision"
        await asyncio.to_thread(subprocess.run, ["docker", "pause", CONTAINER], check=True, capture_output=True)
        try:
            failed = await client.post("/api/requests", data={"text": "DB outage request"},
                                       headers={"Idempotency-Key": uuid4().hex}, timeout=40)
            assert failed.status_code == 503, (failed.status_code, failed.text)
        finally:
            await asyncio.to_thread(subprocess.run, ["docker", "unpause", CONTAINER], check=True, capture_output=True)
        async with httpx.AsyncClient(base_url=h.base) as probe:
            async def ready():
                try:
                    return (await probe.get("/api/ready", timeout=2)).status_code == 200
                except httpx.HTTPError:
                    return False
            await wait_until(ready, timeout=20)
        recovered = await h.submit(client, "Recovered intake")
        rows = h.journal()
        assert any(r["kind"] == "request_failed" and r.get("status_code") == 503 for r in rows)
        from datetime import timedelta

        from jevtriage.monitoring.aggregates import events_between, summarize
        async def collected():
            collected_rows = events_between(h.data, datetime.now(UTC) - timedelta(minutes=5),
                                            datetime.now(UTC))
            result = summarize(collected_rows)
            return result if result["availability"]["unknown_validity"] >= 1 else None
        metrics = await wait_until(collected)
        record("parser_db_outage", "pass", damaged_request=bad.json()["request_id"],
               recovered_request=recovered["request_id"], http_status=failed.status_code,
               unknown_validity=metrics["availability"]["unknown_validity"])
    finally:
        await client.aclose()


async def test_worker_handoff_and_kill_recovery(harness):
    h = harness
    client = await h.login("requester")
    try:
        first = await h.submit(client, "Worker lease handoff")
        a = h.worker("worker_a", delay="5", lease="1")
        async def running_first():
            state = await h.run_state(first["request_id"])
            if not state or state["job_status"] != "running":
                return None
            steps = await h.graph(
                "MATCH (s:RunStep {tenant_id:$tenant,run_id:$run,status:'running'}) "
                "WHERE s.name='Jev 판단' RETURN count(s) AS n", run=state["run_id"])
            return state if steps[0]["n"] else None
        await wait_until(running_first)
        os.killpg(a.pid, signal.SIGSTOP)
        await asyncio.sleep(1.5)
        h.worker("worker_b", lease="2")
        completed = await h.terminal(first["request_id"], timeout=35)
        os.killpg(a.pid, signal.SIGCONT)
        await asyncio.sleep(5.2)
        final = await h.run_state(first["request_id"])
        attempts = json.loads(final["attempts"])
        rows = h.journal()
        committed = await h.graph(
            "MATCH (j:Judgment {tenant_id:$tenant,run_id:$run}) RETURN count(j) AS n",
            run=final["run_id"])
        assert completed["run_status"] == final["run_status"] == "judgment_saved"
        assert len(attempts) == 2 and attempts[0]["status"] == "interrupted"
        assert committed[0]["n"] == 1
        assert any(r["kind"] == "ownership_lost" and r.get("run_id") == final["run_id"]
                   for r in rows)
        record("worker_sigstop_handoff", "pass", run_id=final["run_id"],
               generations=[item["generation"] for item in attempts], judgments=1)
        h.stop("worker_a", signal.SIGKILL)
        h.stop("worker_b")

        second = await h.submit(client, "Worker process killed")
        h.worker("worker_killed", delay="5", lease="1")
        async def running_second():
            state = await h.run_state(second["request_id"])
            if not state or state["job_status"] != "running":
                return None
            steps = await h.graph(
                "MATCH (s:RunStep {tenant_id:$tenant,run_id:$run,status:'running'}) "
                "WHERE s.name='Jev 판단' RETURN count(s) AS n", run=state["run_id"])
            return state if steps[0]["n"] else None
        await wait_until(running_second)
        h.stop("worker_killed", signal.SIGKILL)
        await asyncio.sleep(1.5)
        h.worker("worker_restarted", lease="2")
        recovered = await h.terminal(second["request_id"], timeout=20)
        assert recovered["run_status"] == "judgment_saved"
        assert len(json.loads(recovered["attempts"])) == 2
        record("worker_sigkill_recovery", "pass", run_id=recovered["run_id"])
    finally:
        for name in ("worker_a", "worker_b", "worker_killed", "worker_restarted"):
            h.stop(name, signal.SIGKILL)
        await client.aclose()


async def test_api_restart_and_sse_recovery(harness):
    h = harness
    client = await h.login("requester")
    try:
        request = await h.submit(client, "API restart while judgment is active")
        h.worker("worker_restart", delay="2", lease="4")
        before = await h.run_state(request["request_id"])
        async with client.stream("GET", "/api/events/stream?after=0&max_events=1") as stream:
            assert stream.status_code == 200
            async for line in stream.aiter_lines():
                if line.startswith("id: "):
                    cursor = int(line[4:])
                    break
            else:
                raise AssertionError("SSE did not yield an event")
        h.stop("api", signal.SIGKILL)
        t0 = time.monotonic()
        await h.api()
        startup_ms = round((time.monotonic() - t0) * 1000)
        async with (httpx.AsyncClient(base_url=h.base, cookies=client.cookies, timeout=20) as reconnect,
                    reconnect.stream("GET", "/api/events/stream?max_events=1",
                                     headers={"Last-Event-ID": str(cursor)}) as stream):
                assert stream.status_code == 200
                async for line in stream.aiter_lines():
                    if line.startswith("id: "):
                        recovered_cursor = int(line[4:])
                        break
                else:
                    raise AssertionError("SSE did not recover")
        latency = round((time.monotonic() - t0) * 1000)
        after_restart = await h.terminal(request["request_id"])
        terminal_ms = round((time.monotonic() - t0) * 1000)
        detail = await client.get(f"/api/requests/{request['request_id']}")
        runs = await client.get(f"/api/requests/{request['request_id']}/runs")
        flow = await client.get(f"/api/observe/runs/{after_restart['run_id']}/flow")
        snapshot = await client.get("/api/events/snapshot",
                                    params={"request_id": request["request_id"]})
        assert detail.status_code == runs.status_code == flow.status_code == snapshot.status_code == 200
        assert recovered_cursor > cursor
        assert before["run_id"] == after_restart["run_id"]
        assert snapshot.json()["status"] == detail.json()["request"]["status"]
        assert snapshot.json()["latest_seq"] >= recovered_cursor
        record("api_restart_sse", "pass", run_id=before["run_id"],
               cursor_before=cursor, cursor_after=recovered_cursor,
               recovery_ms=latency, startup_ms=startup_ms, terminal_ms=terminal_ms,
               sample_size=1, slo_threshold_ms=5000)
    finally:
        h.stop("worker_restart")
        await client.aclose()


async def test_policy_version_pinned_and_rollback(harness):
    h = harness
    requester = await h.login("requester")
    editor = await h.login("policy_editor")
    try:
        first = await h.submit(requester, "Policy version before publication")
        h.worker("worker_policy_old", delay="3", lease="5")
        async def started():
            state = await h.run_state(first["request_id"])
            return state if state and state["job_status"] == "running" else None
        await wait_until(started)
        active = (await editor.get("/api/policy/active")).json()
        config = {**active["config"], "evidence_noul_threshold": 0.7}
        published = await editor.post("/api/policy/publish", json={
            "config": config, "reason": "fault test", "expected_active_version": active["version"]},
            headers={"Idempotency-Key": uuid4().hex})
        assert published.status_code == 200, published.text
        version_new = published.json()["version"]
        h.stop("worker_policy_old", signal.SIGKILL)
        await asyncio.sleep(5.2)
        h.worker("worker_policy_new", lease="5")
        first_state = await h.terminal(first["request_id"])
        second = await h.submit(requester, "Policy version after publication")
        second_state = await h.terminal(second["request_id"])
        rollback = await editor.post("/api/policy/rollback", json={
            "target_version": active["version"], "reason": "fault test rollback",
            "expected_active_version": version_new},
            headers={"Idempotency-Key": uuid4().hex})
        assert rollback.status_code == 200, rollback.text
        third = await h.submit(requester, "Policy version after rollback")
        third_state = await h.terminal(third["request_id"])
        versions = [json.loads(s["versions"])["config"] for s in
                    (first_state, second_state, third_state)]
        assert versions == [active["version"], version_new, rollback.json()["version"]]
        record("policy_during_run", "pass", versions=versions,
               run_ids=[first_state["run_id"], second_state["run_id"], third_state["run_id"]])
    finally:
        h.stop("worker_policy_old", signal.SIGKILL)
        h.stop("worker_policy_new")
        await requester.aclose()
        await editor.aclose()


async def test_parallel_review_and_idempotent_retry(harness):
    h = harness
    requester = await h.login("requester")
    reviewer_a = await h.login("reviewer")
    reviewer_b = await h.login("reviewer2")
    try:
        request = await h.submit(requester, "Reviewer race on draft tasks")
        h.worker("worker_review")
        state = await h.terminal(request["request_id"])
        queue = await reviewer_a.get("/api/reviews")
        assert queue.status_code == 200
        target = next(r for r in queue.json()["reviews"]
                      if r["request_id"] == request["request_id"])
        command = {"action": "approve", "request_id": request["request_id"],
                   "input_revision": target["revision_id"], "run_id": state["run_id"],
                   "draft_version": target["draft_version"],
                   "review_version": target["review_version"]}
        key = uuid4().hex
        async def approve(index):
            client = reviewer_a if index % 2 == 0 else reviewer_b
            return await client.post(f"/api/reviews/{target['id']}/decision", json=command,
                                     headers={"Idempotency-Key": key if index == 0 else uuid4().hex})
        results = await asyncio.gather(*(approve(i) for i in range(20)))
        statuses = [result.status_code for result in results]
        assert statuses.count(200) == 1 and set(statuses) <= {200, 409}, [
            (result.status_code, result.text) for result in results]
        retry = await reviewer_a.post(f"/api/reviews/{target['id']}/decision", json=command,
                                      headers={"Idempotency-Key": key})
        assert retry.status_code == 200
        counts = await h.graph(
            "MATCH (q:Request {tenant_id:$tenant,id:$id}) "
            "OPTIONAL MATCH (a:Assignment {tenant_id:$tenant,request_id:$id}) "
            "OPTIONAL MATCH (t:Task {tenant_id:$tenant,request_id:$id}) "
            "RETURN count(DISTINCT a) AS assignments,count(DISTINCT t) AS tasks,"
            "count(DISTINCT t.draft_task_id) AS distinct_drafts", id=request["request_id"])
        assert counts[0]["assignments"] == 1
        assert counts[0]["tasks"] == counts[0]["distinct_drafts"]
        old = await h.submit(requester, "Stale draft after reanalysis")
        old_state = await h.terminal(old["request_id"])
        queue = (await reviewer_a.get("/api/reviews")).json()["reviews"]
        old_review = next(r for r in queue if r["request_id"] == old["request_id"])
        changed = await requester.post(f"/api/requests/{old['request_id']}/reanalyze",
                                       json={"expected_revision": 1, "reason": "new run"},
                                       headers={"Idempotency-Key": uuid4().hex})
        assert changed.status_code == 202
        stale = await reviewer_a.post(f"/api/reviews/{old_review['id']}/decision", json={
            "action": "approve", "request_id": old["request_id"],
            "input_revision": old_review["revision_id"], "run_id": old_state["run_id"],
            "draft_version": old_review["draft_version"],
            "review_version": old_review["review_version"]},
            headers={"Idempotency-Key": uuid4().hex})
        assert stale.status_code == 409, stale.text
        record("parallel_review", "pass", request_id=request["request_id"],
               statuses=statuses, counts=counts[0], retry_status=retry.status_code,
               stale_approval_status=stale.status_code)
    finally:
        h.stop("worker_review")
        await requester.aclose()
        await reviewer_a.aclose()
        await reviewer_b.aclose()


async def test_observation_outages_and_reconciliation(harness):
    h = harness
    requester = await h.login("requester")
    try:
        h.stop("collector", signal.SIGKILL)
        async def collector_alert():
            return list((h.data / "alerts").glob("alert_*.json")) and any(
                json.loads(path.read_text()).get("kind") == "collector_stopped"
                for path in (h.data / "alerts").glob("alert_*.json"))
        await wait_until(collector_alert, timeout=8)
        h.start("collector", "jevtriage.journal.collector", "--interval", "0.2")
        journal_dir = h.data / "journal"
        old_mode = journal_dir.stat().st_mode & 0o777
        journal_dir.chmod(0)
        try:
            broken = await requester.post("/api/requests", data={"text": "Journal outage"},
                                          headers={"Idempotency-Key": uuid4().hex})
            assert broken.status_code >= 500
            async def write_alert():
                return any(json.loads(path.read_text()).get("kind") == "journal_write_failure"
                           for path in (h.data / "alerts").glob("alert_*.json"))
            await wait_until(write_alert, timeout=9)
        finally:
            journal_dir.chmod(old_mode)
        recovered = await h.submit(requester, "Journal recovered")
        await asyncio.sleep(1)
        database = sqlite3.connect(h.data / "metrics" / "metrics.db")
        try:
            count_before = database.execute("SELECT count(*) FROM events").fetchone()[0]
        finally:
            database.close()
        line = next(line for line in (journal_dir / "current.jsonl").read_text().splitlines()
                    if json.loads(line).get("request_id") == recovered["request_id"])
        with (journal_dir / "current.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        await asyncio.sleep(1)
        database = sqlite3.connect(h.data / "metrics" / "metrics.db")
        try:
            count_after = database.execute("SELECT count(*) FROM events").fetchone()[0]
            duplicate_ids = database.execute(
                "SELECT count(*) FROM (SELECT event_id FROM events GROUP BY event_id HAVING count(*)>1)"
            ).fetchone()[0]
        finally:
            database.close()
        assert duplicate_ids == 0 and count_after >= count_before
        from datetime import timedelta

        from jevtriage.monitoring.aggregates import events_between
        from jevtriage.monitoring.api import reconcile_commits
        collected = events_between(h.data, datetime.now(UTC) - timedelta(minutes=10),
                                   datetime.now(UTC))
        reconciliation = await reconcile_commits(TENANT, collected)
        assert recovered["request_id"] not in reconciliation["request_commits_missing_journal"]
        assert recovered["request_id"] not in reconciliation["journal_success_missing_db"]
        assert not reconciliation["run_commits_missing_journal"]
        record("observation_outages", "pass", collector_alert=True,
               journal_write_alert=True, duplicate_ids=duplicate_ids,
               collected_before=count_before, collected_after=count_after,
               reconciliation=reconciliation)
    finally:
        h.start("collector", "jevtriage.journal.collector", "--interval", "0.2")
        await requester.aclose()


async def test_information_wait_and_late_recovery(harness):
    h = harness
    requester = await h.login("requester")
    reviewer = await h.login("reviewer")
    try:
        incomplete = await h.submit(requester, "Need an analysis, details will follow")
        h.worker("worker_information")
        saved = await h.terminal(incomplete["request_id"])
        assert saved["run_status"] == "judgment_saved"
        evidence = await h.graph(
            "MATCH (j:Judgment {tenant_id:$tenant,request_id:$id}) "
            "OPTIONAL MATCH (o:ModelOutput {tenant_id:$tenant,run_id:j.run_id}) "
            "RETURN j.id AS judgment,j.feasibility AS feasibility,count(o) AS outputs",
            id=incomplete["request_id"])
        assert evidence and evidence[0]["outputs"] >= 4
        assert evidence[0]["feasibility"] == "정보 부족"
        queue = (await reviewer.get("/api/reviews")).json()["reviews"]
        target = next(r for r in queue if r["request_id"] == incomplete["request_id"])
        command = {"action": "request_info", "request_id": incomplete["request_id"],
                   "input_revision": target["revision_id"], "run_id": saved["run_id"],
                   "draft_version": target["draft_version"],
                   "review_version": target["review_version"],
                   "reason": "Need source details", "needed_info": ["Source system and owner"]}
        decision = await reviewer.post(f"/api/reviews/{target['id']}/decision", json=command,
                                       headers={"Idempotency-Key": uuid4().hex})
        assert decision.status_code == 200, decision.text
        detail = await requester.get(f"/api/requests/{incomplete['request_id']}")
        assert detail.status_code == 200 and detail.json()["request"]["status"] == "보완 필요"
        record("information_wait", "pass", request_id=incomplete["request_id"],
               judgment_id=evidence[0]["judgment"], outputs=evidence[0]["outputs"])
        h.stop("worker_information")

        late = await h.submit(requester, "Retry after model timeout")
        received = next(r for r in reversed(h.journal())
                        if r["kind"] == "request_received" and r.get("tenant_id") == TENANT)
        h.worker("worker_late_failure", fault="timeout")
        failed = await h.terminal(late["request_id"])
        assert failed["run_status"] == "failed"
        h.stop("worker_late_failure")
        started = datetime.fromisoformat(received["ts"])
        remaining = 121 - (datetime.now(UTC) - started).total_seconds()
        if remaining > 0:
            await asyncio.sleep(remaining)
        retry = await requester.post(f"/api/requests/{late['request_id']}/reanalyze",
                                     json={"expected_revision": 1, "reason": "model recovered"},
                                     headers={"Idempotency-Key": uuid4().hex})
        assert retry.status_code == 202, retry.text
        h.worker("worker_late_recovery")
        recovered = await h.terminal(late["request_id"])
        assert recovered["run_status"] == "judgment_saved"
        await asyncio.sleep(1)
        operator = await h.login("operator")
        try:
            summary = await operator.get("/api/monitoring/summary")
            assert summary.status_code == 200
            metrics = summary.json()["judgment"]
            assert metrics["failed_120s"] >= 1 and metrics["late_recoveries"] >= 1
            from datetime import timedelta

            from jevtriage.monitoring.aggregates import events_between, summarize
            collected = events_between(h.data, datetime.now(UTC) - timedelta(minutes=10),
                                       datetime.now(UTC))
            intake_attempts = {row["attempt_id"] for row in collected
                               if row.get("request_id") == late["request_id"]
                               and row["kind"] == "request_completed"}
            specific = summarize([row for row in collected
                                  if row.get("request_id") == late["request_id"]
                                  or row["attempt_id"] in intake_attempts])
            assert specific["judgment"]["eligible_requests"] == 1
            assert specific["judgment"]["failed_120s"] == 1
            assert specific["judgment"]["late_recoveries"] == 1
            record("late_recovery", "pass", request_id=late["request_id"],
                   first_run=failed["run_id"], recovery_run=recovered["run_id"],
                   failed_120s=metrics["failed_120s"], late_recoveries=metrics["late_recoveries"],
                   request_metrics=specific["judgment"],
                   wait_seconds=121)
        finally:
            await operator.aclose()
    finally:
        for name in ("worker_information", "worker_late_failure", "worker_late_recovery"):
            h.stop(name)
        await requester.aclose()
        await reviewer.aclose()
