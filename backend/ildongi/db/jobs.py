"""Lease primitives. Call verify_owner_in_tx inside every result-writing transaction."""

from ildongi.db.locks import lock_node_in_tx
from ildongi.db.tx import db_now_in_tx, write_tx
from ildongi.domain.ids import new_id


class OwnershipLost(RuntimeError):
    pass


async def create_job(tenant_id: str, run_id: str, input_revision_id: str, *, job_id: str | None = None) -> str:
    job_id = job_id or new_id("job")

    async def op(tx):
        await (await tx.run(
            "CREATE (j:Job {id: $job_id, tenant_id: $tenant_id, run_id: $run_id, "
            "input_revision_id: $revision_id, status: 'pending', lease_generation: 0, "
            "created_by: 'system', created_at: datetime()})",
            job_id=job_id, tenant_id=tenant_id, run_id=run_id, revision_id=input_revision_id,
        )).consume()
        return job_id

    return await write_tx(tenant_id, op)


async def claim_or_takeover(tenant_id: str, job_id: str, owner_id: str, lease_seconds: float) -> int:
    if lease_seconds <= 0:
        raise ValueError("lease_seconds must be positive")

    async def op(tx):
        job = await lock_node_in_tx(tx, tenant_id, "Job", job_id)
        now = await db_now_in_tx(tx)
        if job["status"] not in ("pending", "running"):
            raise OwnershipLost("job is terminal")
        if job["status"] == "running" and job["lease_expires_at"] > now:
            raise OwnershipLost("lease is active")
        result = await tx.run(
            "MATCH (j:Job {id: $job_id, tenant_id: $tenant_id}) "
            "SET j.owner_id = $owner_id, j.status = 'running', "
            "j.lease_generation = j.lease_generation + 1, "
            "j.lease_expires_at = datetime() + duration({milliseconds: $ms}) "
            "RETURN j.lease_generation AS generation",
            job_id=job_id, tenant_id=tenant_id, owner_id=owner_id,
            ms=max(1, round(lease_seconds * 1000)),
        )
        return (await result.single(strict=True))["generation"]

    return await write_tx(tenant_id, op)


async def verify_owner_in_tx(tx, tenant_id: str, job_id: str, owner_id: str, generation: int) -> None:
    job = await lock_node_in_tx(tx, tenant_id, "Job", job_id)
    now = await db_now_in_tx(tx)
    if (job["status"] != "running" or job["owner_id"] != owner_id
            or job["lease_generation"] != generation or job["lease_expires_at"] <= now):
        raise OwnershipLost("job lease ownership lost")


async def heartbeat(tenant_id: str, job_id: str, owner_id: str, generation: int, lease_seconds: float) -> None:
    if lease_seconds <= 0:
        raise ValueError("lease_seconds must be positive")

    async def op(tx):
        await verify_owner_in_tx(tx, tenant_id, job_id, owner_id, generation)
        await (await tx.run(
            "MATCH (j:Job {id: $job_id, tenant_id: $tenant_id}) "
            "SET j.lease_expires_at = datetime() + duration({milliseconds: $ms})",
            job_id=job_id, tenant_id=tenant_id, ms=max(1, round(lease_seconds * 1000)),
        )).consume()

    await write_tx(tenant_id, op)
