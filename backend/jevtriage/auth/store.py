"""Authentication reads and session writes used by the HTTP boundary."""

from jevtriage.db.driver import get_driver


async def tenant_for_email(email: str) -> str:
    driver = await get_driver()
    async with driver.session() as session:
        user = await (await session.run(
            "MATCH (u:User {email:$email}) RETURN u.tenant_id AS tenant_id LIMIT 1",
            email=email.lower(),
        )).single()
    return user["tenant_id"] if user else "unknown"


async def delete_session(token_hash: str) -> None:
    driver = await get_driver()
    async with driver.session() as session:
        await (await session.run(
            "MATCH (s:Session {token_hash:$hash}) DETACH DELETE s", hash=token_hash,
        )).consume()


async def display_name(tenant_id: str, user_id: str) -> str | None:
    driver = await get_driver()
    async with driver.session() as session:
        record = await (await session.run(
            "MATCH (u:User {id:$user_id,tenant_id:$tenant_id}) "
            "RETURN u.display_name AS display_name",
            user_id=user_id, tenant_id=tenant_id,
        )).single()
    return record["display_name"] if record else None
