"""Index plans and atomic worker discovery contracts on Neo4j 5."""

import asyncio
from uuid import uuid4

import pytest

from jevtriage.db.driver import get_driver
from jevtriage.db.jobs import create_job
from jevtriage.db.schema import apply_schema
from jevtriage.jobs.worker import Worker

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_schema_indexes_are_idempotent_and_seekable():
    await apply_schema()
    await apply_schema()
    driver = await get_driver()
    patterns = [
        ("Session", "s.token_hash=$value", "hash"),
        ("User", "s.email=$value", "user@example.com"),
        ("LoginAttempt", "s.tenant_id=$tenant AND s.email=$value", "user@example.com"),
        ("Judgment", "s.tenant_id=$tenant AND s.run_id=$value", "run"),
        ("ModelOutput", "s.tenant_id=$tenant AND s.run_id=$value", "run"),
        ("Event", "s.tenant_id=$tenant AND s.seq>$value", 1),
        ("Event", "s.tenant_id=$tenant AND s.request_id=$value", "req"),
        ("Job", "s.status=$tenant AND s.lease_expires_at<datetime()", "running"),
        ("Review", "s.tenant_id=$tenant AND s.request_id=$value AND s.status=$status", "req"),
        ("Task", "s.tenant_id=$tenant AND s.request_id=$value", "req"),
    ]
    async with driver.session() as session:
        names = {row["name"] for row in await (await session.run("SHOW INDEXES YIELD name RETURN name")).data()}
        assert "session_token_hash_unique" in names
        assert "user_email_unique" in names
        for label, predicate, value in patterns:
            result = await session.run(
                f"EXPLAIN MATCH (s:{label}) WHERE {predicate} RETURN s LIMIT 1",
                tenant="running" if label == "Job" else "tenant", value=value, status="pending",
            )
            summary = await result.consume()
            def operators(node):
                return [node["operatorType"], *(op for child in node.get("children", [])
                                                for op in operators(child))]

            plan = operators(summary.plan)
            assert any("IndexSeek" in op or "IndexRangeSeek" in op for op in plan), (label, predicate, plan)
            assert not any("NodeByLabelScan" in op or "AllNodesScan" in op for op in plan), (label, plan)


async def test_worker_claims_one_eligible_job_and_increments_generation():
    tenant = f"schema_{uuid4().hex}"
    job_id = await create_job(tenant, "run", "revision")
    worker = Worker(tenants=[tenant])
    try:
        claimed = await worker.claim_next()
        assert claimed == {"job_id": job_id, "tenant_id": tenant, "generation": 1}
        assert await worker.claim_next() is None
    finally:
        driver = await get_driver()
        async with driver.session() as session:
            await (await session.run("MATCH (j:Job {tenant_id:$tenant}) DETACH DELETE j", tenant=tenant)).consume()


async def test_parallel_workers_claim_one_job_once():
    tenant = f"schema_{uuid4().hex}"
    job_id = await create_job(tenant, "run", "revision")
    try:
        first, second = await asyncio.gather(
            Worker(tenants=[tenant]).claim_next(), Worker(tenants=[tenant]).claim_next(),
        )
        assert sorted(row["job_id"] for row in (first, second) if row) == [job_id]
    finally:
        driver = await get_driver()
        async with driver.session() as session:
            await (await session.run("MATCH (j:Job {tenant_id:$tenant}) DETACH DELETE j", tenant=tenant)).consume()
