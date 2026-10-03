import asyncio
from uuid import uuid4

import pytest
import pytest_asyncio

from jevtriage.db.driver import get_driver
from jevtriage.db.events import append_event, list_events
from jevtriage.db.idempotency import IdempotencyConflict, get_or_create
from jevtriage.db.jobs import (
    OwnershipLost,
    claim_or_takeover,
    create_job,
    heartbeat,
    verify_owner_in_tx,
)
from jevtriage.db.requests import StaleRun, add_input_revision, create_request, set_active_run
from jevtriage.db.schema import apply_schema
from jevtriage.db.tx import read_tx, write_tx

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def tenant():
    value = f"t04_{uuid4().hex}"
    await apply_schema()
    yield value
    driver = await get_driver()
    async with driver.session() as session:
        await (await session.run("MATCH (n {tenant_id: $tenant_id}) DETACH DELETE n", tenant_id=value)).consume()


@pytest.mark.asyncio
async def test_schema_twice_and_assignment_contention(tenant):
    await apply_schema()
    await apply_schema()
    request_id = await create_request(tenant, "tester")

    async def assign(_):
        async def op(tx):
            await (await tx.run(
                "MERGE (a:Assignment {tenant_id: $tenant_id, request_id: $request_id}) "
                "ON CREATE SET a.id = $id RETURN a.id AS id",
                tenant_id=tenant, request_id=request_id, id=f"asn_{uuid4().hex}",
            )).consume()

        await write_tx(tenant, op)

    await asyncio.gather(*(assign(i) for i in range(20)))

    async def count(tx):
        result = await tx.run("MATCH (a:Assignment {tenant_id: $tenant_id, request_id: $request_id}) RETURN count(a) AS n", tenant_id=tenant, request_id=request_id)
        return (await result.single(strict=True))["n"]

    assert await read_tx(tenant, count) == 1


@pytest.mark.asyncio
async def test_idempotency_and_event_sequence(tenant):
    created = 0

    async def build(tx):
        nonlocal created
        created += 1
        return {"ok": created}

    first = await get_or_create(tenant, "request", "key", "hash-a", build)
    second = await get_or_create(tenant, "request", "key", "hash-a", build)
    assert first == second == {"ok": 1}
    with pytest.raises(IdempotencyConflict):
        await get_or_create(tenant, "request", "key", "hash-b", build)
    rows = await asyncio.gather(*(append_event(tenant, "test", {"i": i}) for i in range(20)))
    assert sorted(row["seq"] for row in rows) == list(range(1, 21))
    assert [row["seq"] for row in await list_events(tenant)] == list(range(1, 21))


@pytest.mark.asyncio
async def test_expired_job_cannot_revive(tenant):
    job_id = await create_job(tenant, "run_test", "rev_test")
    generation_a = await claim_or_takeover(tenant, job_id, "A", 0.3)
    # Generous margin over the lease so DB transaction latency under load cannot flake.
    await asyncio.sleep(1.2)
    generation_b = await claim_or_takeover(tenant, job_id, "B", 3)
    assert generation_b == generation_a + 1
    with pytest.raises(OwnershipLost):
        await heartbeat(tenant, job_id, "A", generation_a, 3)
    with pytest.raises(OwnershipLost):
        await write_tx(tenant, lambda tx: verify_owner_in_tx(tx, tenant, job_id, "A", generation_a))
    await write_tx(tenant, lambda tx: verify_owner_in_tx(tx, tenant, job_id, "B", generation_b))


@pytest.mark.asyncio
async def test_old_run_cannot_change_pointer(tenant):
    request_id = await create_request(tenant, "tester")
    revision_id, _ = await add_input_revision(tenant, request_id, "tester")

    async def make_run(run_id):
        async def op(tx):
            await (await tx.run(
                "CREATE (:Run {id: $run_id, tenant_id: $tenant_id, request_id: $request_id, input_revision_id: $revision_id, kind: 'normal'})",
                run_id=run_id, tenant_id=tenant, request_id=request_id, revision_id=revision_id,
            )).consume()
        await write_tx(tenant, op)

    await make_run("run_old")
    await make_run("run_new")
    await set_active_run(tenant, request_id, "run_old", revision_id)
    await set_active_run(tenant, request_id, "run_new", revision_id, expected_active_run_id="run_old")
    with pytest.raises(StaleRun):
        await set_active_run(tenant, request_id, "run_old", revision_id, expected_active_run_id="run_old")
