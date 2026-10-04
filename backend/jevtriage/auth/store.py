"""Authentication reads and session writes used by the HTTP boundary."""

from jevtriage.db.tx import cross_tenant_tx, read_tx


async def tenant_for_email(email: str) -> str:
    async def query(tx):
        user = await (await tx.run(
            "MATCH (u:User {email:$email}) RETURN u.tenant_id AS tenant_id LIMIT 1",
            email=email.lower(),
        )).single()
        return user
    user = await cross_tenant_tx("auth.login_tenant", query)
    return user["tenant_id"] if user else "unknown"


async def delete_session(token_hash: str) -> None:
    async def query(tx):
        await (await tx.run(
            "MATCH (s:Session {token_hash:$hash}) DETACH DELETE s", hash=token_hash,
        )).consume()
    await cross_tenant_tx("auth.revoke_session", query, write=True)


async def display_name(tenant_id: str, user_id: str) -> str | None:
    async def query(tx):
        record = await (await tx.run(
            "MATCH (u:User {id:$user_id,tenant_id:$tenant_id}) "
            "RETURN u.display_name AS display_name",
            user_id=user_id, tenant_id=tenant_id,
        )).single()
        return record
    record = await read_tx(tenant_id, query)
    return record["display_name"] if record else None
