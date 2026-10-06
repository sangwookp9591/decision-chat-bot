"""Shared helpers for the T38 extension scenario: API client, DB queries, evidence ledger.

Secrets (AI_API_KEY) are never read or written here. Evidence holds IDs, counts and short values only.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from pathlib import Path

import httpx

from ildongi.db.driver import get_driver

API = os.getenv("X38_API", "http://127.0.0.1:8138")
TENANT = os.getenv("X38_TENANT", "")
PASSWORD = os.getenv("ILDONGI_DEV_PASSWORD", "dev-only-change-me")
OUT = Path(os.getenv("X38_OUT", "")) if os.getenv("X38_OUT") else None
STATE = (OUT / "state.json") if OUT else None
LEDGER = (OUT / "ledger.json") if OUT else None


def load_state() -> dict:
    return json.loads(STATE.read_text()) if STATE and STATE.exists() else {}


def save_state(state: dict) -> None:
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True))


def record(gate: str, step: str, status: str, evidence) -> None:
    """status: pass | fail | unverified | blocked. Appends to the ledger (never overwritten)."""
    assert status in {"pass", "fail", "unverified", "blocked"}
    rows = json.loads(LEDGER.read_text()) if LEDGER.exists() else []
    rows.append({"gate": gate, "step": step, "status": status, "evidence": evidence,
                 "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    LEDGER.write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    print(f"[{gate}] {status.upper():10} {step}")


def check(gate: str, step: str, ok: bool, evidence) -> bool:
    record(gate, step, "pass" if ok else "fail", evidence)
    return ok


class Client:
    def __init__(self, role: str):
        self.role = role
        self.http = httpx.Client(base_url=API, timeout=60)
        r = self.http.post("/api/auth/login", json={"email": f"{role}@{TENANT}.dev", "password": PASSWORD})
        r.raise_for_status()
        self.csrf = self.http.cookies.get("ildongi_csrf") or ""

    def get(self, path, **kw):
        return self.http.get(path, **kw)

    def post(self, path, key=None, **kw):
        headers = {"X-CSRF-Token": self.csrf, "Idempotency-Key": key or str(uuid.uuid4())}
        return self.http.post(path, headers=headers, **kw)

    def json(self, path, **kw):
        r = self.get(path, **kw)
        r.raise_for_status()
        return r.json()


def run(coro):
    return asyncio.run(coro)


async def _query(cypher: str, **params):
    driver = await get_driver()
    async with driver.session() as session:
        return await (await session.run(cypher, tenant=TENANT, **params)).data()


def q(cypher: str, **params) -> list[dict]:
    """Read-only Cypher against the scenario tenant (callers include `$tenant`)."""
    return run(_query(cypher, **params))


COUNT_QUERIES = {
    "Task": "MATCH (n:Task {tenant_id:$tenant}) RETURN count(n) AS n",
    "Assignment": "MATCH (n:Assignment {tenant_id:$tenant}) RETURN count(n) AS n",
    "Review": "MATCH (n:Review {tenant_id:$tenant}) RETURN count(n) AS n",
    "Event": "MATCH (n:Event {tenant_id:$tenant}) RETURN count(n) AS n",
    "Notification": "MATCH (n:Notification {tenant_id:$tenant}) RETURN count(n) AS n",
    "ReviewDecision": "MATCH (n:ReviewDecision {tenant_id:$tenant}) RETURN count(n) AS n",
    "Judgment": "MATCH (n:Judgment {tenant_id:$tenant}) RETURN count(n) AS n",
    "Request": "MATCH (n:Request {tenant_id:$tenant}) RETURN count(n) AS n",
    "active_run_pointers": "MATCH (r:Request {tenant_id:$tenant}) WHERE r.active_run_id IS NOT NULL "
                           "RETURN count(r) AS n, collect(r.id+'='+r.active_run_id) AS ptr",
}


def side_effect_counts() -> dict:
    out = {}
    for name, cypher in COUNT_QUERIES.items():
        row = q(cypher)[0]
        out[name] = row["n"] if name != "active_run_pointers" else {"n": row["n"], "ptr": sorted(row["ptr"])}
    return out


import hashlib


def snapshot(labels: list[str]) -> dict:
    """Count + SHA-256 of every property of every node with one of the labels (independent of the app's own check)."""
    out = {}
    for label in labels:
        rows = q(f"MATCH (n:{label} {{tenant_id:$tenant}}) RETURN properties(n) AS p ORDER BY n.id")
        blob = json.dumps([r["p"] for r in rows], ensure_ascii=False, sort_keys=True, default=str)
        out[label] = {"count": len(rows), "sha256": hashlib.sha256(blob.encode()).hexdigest()[:16]}
    return out


PROTECTED = ["Task", "Assignment", "Review", "ReviewDecision", "Event", "Request", "Judgment", "Correction"]
RULE_STATE = ["RuleCandidate", "RuleDecision", "RuleVersion", "ConfigVersion"]


def sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()[:16]
