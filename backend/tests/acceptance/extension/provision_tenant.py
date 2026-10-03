"""Create a dedicated tenant (orgs, six role accounts, default policy) for the T38 extension scenario.

Usage: .venv/bin/python tests/acceptance/extension/provision_tenant.py <tenant-id>
Accounts: <role>@<tenant>.dev with the local development password (never the Jev key).
"""
import asyncio
import os
import sys

from jevtriage.auth.core import hash_password
from jevtriage.db.driver import close_driver, get_driver
from jevtriage.db.schema import apply_schema
from jevtriage.policy.service import bootstrap_policy

ROLES = ("requester", "reviewer", "team_member", "operator", "policy_editor", "rule_admin")


async def provision(tenant: str, password: str) -> None:
    await apply_schema()
    await bootstrap_policy(tenant)
    driver = await get_driver()
    async with driver.session() as session:
        for org_name in ("ai", "it", "business"):
            org_id = f"{tenant}-{org_name}"
            await (await session.run(
                "MERGE (t:Tenant {id:$tenant, tenant_id:$tenant}) "
                "MERGE (o:Org {id:$org, tenant_id:$tenant, name:$org_name}) "
                "MERGE (t)-[:HAS_ORG]->(o)", tenant=tenant, org=org_id, org_name=org_name)).consume()
            for role in ROLES:
                await (await session.run(
                    "MATCH (o:Org {id:$org, tenant_id:$tenant}) "
                    "MERGE (u:User {id:$user_id, tenant_id:$tenant}) "
                    "ON CREATE SET u.email=$email, u.password_hash=$hash, u.disabled=false, u.can_read_source=false "
                    "MERGE (u)-[:MEMBER_OF {role:$role}]->(o)",
                    org=org_id, tenant=tenant, user_id=f"usr_{tenant}_{role}",
                    email=f"{role}@{tenant}.dev", hash=hash_password(password), role=role)).consume()


if __name__ == "__main__":
    try:
        asyncio.run(provision(sys.argv[1], os.getenv("JEVTRIAGE_DEV_PASSWORD", "dev-only-change-me")))
        print("provisioned", sys.argv[1])
    finally:
        asyncio.run(close_driver())
