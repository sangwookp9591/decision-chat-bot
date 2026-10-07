"""Authentication service for explicitly opted-in development integrations."""

from ildongi.auth.store import dev_user_record
from ildongi.auth.types import Principal


async def dev_principal(email: str) -> Principal:
    row = await dev_user_record(email)
    if row is None:
        raise ValueError("MCP 개발 사용자가 없거나 비활성 상태입니다.")
    return Principal(row["tenant_id"], row["user_id"], tuple(row["org_ids"]),
                     frozenset(row["roles"]), bool(row["can_read_source"]))
