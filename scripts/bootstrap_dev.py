#!/usr/bin/env python3
"""Create idempotent local development tenants, orgs, users, and memberships."""
import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from jevtriage.auth.core import hash_password
from jevtriage.db.driver import close_driver, get_driver
from jevtriage.db.schema import apply_schema
from jevtriage.policy.service import bootstrap_policy

ROLES = ("requester", "reviewer", "team_member", "operator", "policy_editor", "rule_admin")


async def bootstrap(password: str) -> None:
    await apply_schema()
    await bootstrap_policy("t-alpha")
    await bootstrap_policy("t-beta")
    driver = await get_driver()
    async with driver.session() as session:
        for tenant in ("t-alpha", "t-beta"):
            for org_name in ("ai", "it", "business"):
                org_id = f"{tenant}-{org_name}"
                await (await session.run(
                    "MERGE (t:Tenant {id:$tenant, tenant_id:$tenant}) "
                    "MERGE (o:Org {id:$org, tenant_id:$tenant, name:$org_name}) "
                    "MERGE (t)-[:HAS_ORG]->(o)", tenant=tenant, org=org_id, org_name=org_name
                )).consume()
                for role in ROLES:
                    email = f"{role}@{tenant}.dev"
                    user_id = f"usr_{tenant}_{role}"
                    await (await session.run(
                        "MATCH (o:Org {id:$org, tenant_id:$tenant}) "
                        "MERGE (u:User {id:$user_id, tenant_id:$tenant}) "
                        "ON CREATE SET u.email=$email, u.password_hash=$password_hash, u.disabled=false, u.can_read_source=false "
                        "MERGE (u)-[m:MEMBER_OF {role:$role}]->(o)",
                        org=org_id, tenant=tenant, user_id=user_id, email=email,
                        password_hash=hash_password(password), role=role,
                    )).consume()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", default=os.getenv("JEVTRIAGE_DEV_PASSWORD", "dev-only-change-me"))
    args = parser.parse_args()
    try:
        asyncio.run(bootstrap(args.password))
    finally:
        asyncio.run(close_driver())


if __name__ == "__main__":
    main()
