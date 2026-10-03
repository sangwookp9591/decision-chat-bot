"""HTTP harness for acceptance tests against a *running* API + tenant-limited worker.

Environment (all optional): ACC_API (default http://127.0.0.1:8121), ACC_TENANT (t-acc21),
ACC_TENANT_B (t-acc21b), ACC_OUT (evidence directory), ACC_PASSWORD.
Nothing here reads or prints JEV_API_KEY.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

import httpx

API = os.environ.get("ACC_API", "http://127.0.0.1:8121")
TENANT = os.environ.get("ACC_TENANT", "t-acc21")
TENANT_B = os.environ.get("ACC_TENANT_B", TENANT + "b")   # other tenant (isolation)
TENANT_P = TENANT + "p"   # policy / auto-assign tests
TENANT_G = TENANT + "g"   # T21-gates (G03/G05/G06) tenant
TENANT_F = TENANT + "f"   # worker with an invalid Jev key (real failed runs)
PASSWORD = os.environ.get("ACC_PASSWORD", "dev-only-change-me")
OUT = Path(os.environ.get("ACC_OUT", "")) if os.environ.get("ACC_OUT") else None
PROCESSING = {"judgment_pending", "received"}


class Client:
    def __init__(self, role: str, tenant: str = TENANT, base: str = API):
        self.role, self.tenant = role, tenant
        self.http = httpx.Client(base_url=base, timeout=60.0)
        r = self.http.post("/api/auth/login", json={"email": f"{role}@{tenant}.dev", "password": PASSWORD})
        assert r.status_code == 200, f"login {role}@{tenant}: {r.status_code}"
        self.me = self.http.get("/api/auth/me").json()

    @property
    def csrf(self) -> str:
        return self.http.cookies.get("jev_csrf") or ""

    def _h(self, extra: dict | None = None, write: bool = True) -> dict:
        h = dict(extra or {})
        if write:
            h.setdefault("X-CSRF-Token", self.csrf)
        return h

    def get(self, path: str, **kw) -> httpx.Response:
        return self.http.get(path, **kw)

    def post(self, path: str, *, key: str | None = None, **kw) -> httpx.Response:
        headers = self._h({"Idempotency-Key": key or uuid.uuid4().hex})
        return self.http.post(path, headers=headers, **kw)

    def submit(self, text: str = "", files: list[tuple[str, bytes, str]] | None = None,
               key: str | None = None) -> httpx.Response:
        mp = [("files", (n, b, m)) for n, b, m in (files or [])]
        return self.post("/api/requests", key=key, data={"text": text}, files=mp or None)

    def revise(self, rid: str, expected_revision: int, text: str = "",
               files: list[tuple[str, bytes, str]] | None = None) -> httpx.Response:
        mp = [("files", (n, b, m)) for n, b, m in (files or [])]
        return self.post(f"/api/requests/{rid}/revisions",
                         data={"text": text, "expected_revision": str(expected_revision)},
                         files=mp or None)

    def detail(self, rid: str) -> dict:
        r = self.get(f"/api/requests/{rid}")
        assert r.status_code == 200, (r.status_code, r.text[:200])
        return r.json()

    def wait(self, rid: str, timeout: float = 240.0, until=None) -> dict:
        """Poll until the request leaves processing states (or `until(detail)` is true)."""
        end = time.time() + timeout
        d: dict = {}
        while time.time() < end:
            d = self.detail(rid)
            status = (d.get("request") or {}).get("status")
            if until is not None:
                if until(d):
                    return d
            elif status not in (None, "judgment_pending", "received"):
                return d
            time.sleep(3)
        raise TimeoutError(f"request {rid} still {d.get('request', {}).get('status')}")


def idem() -> str:
    return uuid.uuid4().hex


def record(name: str, data) -> None:
    """Append a non-sensitive evidence record (ids, statuses, counts) to ACC_OUT."""
    if OUT is None:
        return
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "records.jsonl").open("a") as fh:
        fh.write(json.dumps({"name": name, "data": data}, ensure_ascii=False, default=str) + "\n")


# ---- stored-state verification (read-only Cypher through the public read_tx helper) ----
def db_read(tenant: str, cypher: str, **params) -> list[dict]:
    import asyncio

    async def go():
        from jevtriage.db.driver import close_driver
        from jevtriage.db.tx import read_tx

        async def q(tx):
            return await (await tx.run(cypher, tenant=tenant, **params)).data()

        try:
            return await read_tx(tenant, q)
        finally:
            await close_driver()

    return asyncio.run(go())


def db_write(tenant: str, cypher: str, **params) -> None:
    import asyncio

    async def go():
        from jevtriage.db.driver import close_driver
        from jevtriage.db.tx import write_tx

        async def q(tx):
            await (await tx.run(cypher, tenant=tenant, **params)).consume()

        try:
            await write_tx(tenant, q)
        finally:
            await close_driver()

    asyncio.run(go())


def counts(tenant: str, rid: str) -> dict:
    rows = db_read(
        tenant,
        "MATCH (q:Request {tenant_id:$tenant,id:$rid}) "
        "OPTIONAL MATCH (a:Assignment {tenant_id:$tenant,request_id:$rid}) "
        "WITH q,count(DISTINCT a) AS assignments "
        "OPTIONAL MATCH (t:Task {tenant_id:$tenant,request_id:$rid}) "
        "WITH q,assignments,count(DISTINCT t) AS tasks "
        "OPTIONAL MATCH (r:Run {tenant_id:$tenant,request_id:$rid}) "
        "WITH q,assignments,tasks,count(DISTINCT r) AS runs "
        "OPTIONAL MATCH (j:Judgment {tenant_id:$tenant,request_id:$rid}) "
        "WITH q,assignments,tasks,runs,count(DISTINCT j) AS judgments "
        "OPTIONAL MATCH (d:ReviewDecision {tenant_id:$tenant,request_id:$rid}) "
        "RETURN assignments,tasks,runs,judgments,count(DISTINCT d) AS decisions,q.status AS status",
        rid=rid,
    )
    return rows[0] if rows else {}


def model_output_count(tenant: str, rid: str) -> int:
    return db_read(tenant, "MATCH (r:Run {tenant_id:$tenant,request_id:$rid}) "
                   "OPTIONAL MATCH (o:ModelOutput {tenant_id:$tenant,run_id:r.id}) "
                   "RETURN count(o) AS n", rid=rid)[0]["n"]


def tenant_totals(tenant: str) -> dict:
    """Tenant-wide counters used to prove a read-only action changed nothing."""
    q = ("RETURN {tasks: COUNT { (:Task {tenant_id:$tenant}) }, "
         "assignments: COUNT { (:Assignment {tenant_id:$tenant}) }, "
         "outputs: COUNT { (:ModelOutput {tenant_id:$tenant}) }, "
         "runs: COUNT { (:Run {tenant_id:$tenant}) }, "
         "jobs: COUNT { (:Job {tenant_id:$tenant}) }, "
         "steps: COUNT { (:RunStep {tenant_id:$tenant}) }, "
         "reviews: COUNT { (:Review {tenant_id:$tenant}) }, "
         "decisions: COUNT { (:ReviewDecision {tenant_id:$tenant}) }, "
         "corrections: COUNT { (:Correction {tenant_id:$tenant}) }} AS c")
    return db_read(tenant, q)[0]["c"]


# ---- flow helpers ----
def judge(c: Client, text: str, files=None, timeout: float = 240.0) -> tuple[str, dict]:
    r = c.submit(text, files)
    assert r.status_code == 202, (r.status_code, r.text[:300])
    rid = r.json()["request_id"]
    return rid, c.wait(rid, timeout=timeout)


def judgment(c: Client, rid: str, run_id: str | None = None) -> dict:
    r = c.get(f"/api/requests/{rid}/judgment", params={"run_id": run_id} if run_id else None)
    assert r.status_code == 200, (r.status_code, r.text[:300])
    return r.json()


def pending_review(rv: Client, rid: str, timeout: float = 90.0) -> dict:
    end = time.time() + timeout
    while time.time() < end:
        for row in rv.get("/api/reviews?status=pending").json()["reviews"]:
            if row["request_id"] == rid:
                return row
        time.sleep(2)
    raise TimeoutError(f"no pending review for {rid}")


def decision_body(row: dict, action: str, **extra) -> dict:
    body = {"action": action, "request_id": row["request_id"], "input_revision": row["revision_id"],
            "run_id": row["run_id"], "draft_version": row["draft_version"],
            "review_version": row["review_version"]}
    body.update(extra)
    return body


def decide(c: Client, row: dict, action: str, key: str | None = None, **extra) -> httpx.Response:
    return c.post(f"/api/reviews/{row['id']}/decision", key=key,
                  json=decision_body(row, action, **extra))


def tasks_of(c: Client, rid: str) -> list[dict]:
    return c.get("/api/tasks", params={"request_id": rid}).json()["tasks"]


def topology(c: Client, rid: str) -> dict:
    return c.get(f"/api/observe/requests/{rid}/topology", params={"kind": "business"}).json()
