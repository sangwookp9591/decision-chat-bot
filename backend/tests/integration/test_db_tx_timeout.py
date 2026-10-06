import asyncio
from contextlib import suppress
from uuid import uuid4

import pytest
from neo4j.exceptions import ClientError, Neo4jError

from ildongi.db.tx import write_tx
from ildongi.jobs.worker import Worker
from ildongi.journal.writer import JournalWriter


@pytest.mark.asyncio
async def test_claim_loop_retries_terminated_lock_transaction(tmp_path):
    worker = Worker(tenants=[f"retry_{uuid4().hex}"], poll_seconds=0.01,
                    journal=JournalWriter(tmp_path))
    calls = 0

    async def claim():
        nonlocal calls
        calls += 1
        if calls == 1:
            error = ClientError("terminated lock transaction")
            error._neo4j_code = "Neo.ClientError.Transaction.LockClientStopped"
            raise error
        worker.stop()

    worker.claim_next = claim
    await asyncio.wait_for(worker.run(), 2)
    assert calls == 2


@pytest.mark.asyncio
async def test_write_timeout_ends_lock_wait_without_a_false_commit():
    tenant = f"tx_timeout_{uuid4().hex}"
    job_id = f"job_{uuid4().hex}"

    async def create(tx):
        await (await tx.run(
            "CREATE (:Job {id:$job_id, tenant_id:$tenant, status:'pending'})",
            job_id=job_id, tenant=tenant,
        )).consume()

    await write_tx(tenant, create)
    entered = asyncio.Event()
    release = asyncio.Event()

    async def hold(tx):
        await (await tx.run(
            "MATCH (j:Job {id:$job_id,tenant_id:$tenant}) SET j._lock=randomUUID()",
            job_id=job_id, tenant=tenant,
        )).consume()
        entered.set()
        await release.wait()

    holder = asyncio.create_task(write_tx(tenant, hold, timeout_seconds=3))
    try:
        await asyncio.wait_for(entered.wait(), 2)

        async def claim(tx):
            await (await tx.run(
                "MATCH (j:Job {id:$job_id,tenant_id:$tenant}) SET j.status='running'",
                job_id=job_id, tenant=tenant,
            )).consume()

        with pytest.raises(Neo4jError):
            await asyncio.wait_for(write_tx(tenant, claim, timeout_seconds=0.2), 2)
    finally:
        release.set()
        with suppress(Neo4jError):
            await holder

        await asyncio.wait_for(write_tx(tenant, claim, timeout_seconds=1), 2)

        async def cleanup(tx):
            await (await tx.run(
                "MATCH (j:Job {id:$job_id,tenant_id:$tenant}) DELETE j",
                job_id=job_id, tenant=tenant,
            )).consume()

        await write_tx(tenant, cleanup)


@pytest.mark.asyncio
async def test_expired_running_job_is_found_within_poll_ceiling(tmp_path):
    tenant = f"lease_poll_{uuid4().hex}"
    job_id = f"job_{uuid4().hex}"
    claimed = asyncio.Event()
    generations = []

    class ProbeWorker(Worker):
        async def process_job(self, tenant_id, claimed_job_id, generation=None):
            generations.append(generation)
            claimed.set()
            self.stop()

    worker = ProbeWorker(tenants=[tenant], poll_seconds=0.05,
                         max_poll_seconds=1.0, journal=JournalWriter(tmp_path))
    task = asyncio.create_task(worker.run())
    try:
        await asyncio.sleep(0.15)

        async def create_expired(tx):
            await (await tx.run(
                "CREATE (:Job {id:$job_id, tenant_id:$tenant, status:'running', "
                "owner_id:'stopped', lease_generation:1, created_at:datetime(), "
                "lease_expires_at:datetime()-duration({seconds:1})})",
                job_id=job_id, tenant=tenant,
            )).consume()

        await write_tx(tenant, create_expired)
        await asyncio.wait_for(claimed.wait(), worker.max_poll_seconds + 0.5)
        assert generations == [2]
    finally:
        worker.stop()
        await task

        async def cleanup(tx):
            await (await tx.run(
                "MATCH (j:Job {id:$job_id,tenant_id:$tenant}) DELETE j",
                job_id=job_id, tenant=tenant,
            )).consume()

        await write_tx(tenant, cleanup)
