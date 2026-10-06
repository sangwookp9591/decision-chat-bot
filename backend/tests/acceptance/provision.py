"""Provision dedicated acceptance tenants (orgs, role accounts, policy) in the shared Neo4j.

Reuses the same data shape as scripts/bootstrap_dev.py but for arbitrary tenant ids, and adds
a few narrowly scoped users used by the permission scenarios. Idempotent.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))

from ildongi.auth.core import hash_password
from ildongi.db.driver import close_driver, get_driver
from ildongi.db.schema import apply_schema
from ildongi.policy.service import bootstrap_policy

ROLES = ("requester", "reviewer", "team_member", "operator", "policy_editor", "rule_admin")
PASSWORD = "dev-only-change-me"


async def provision(tenants: tuple[str, ...], password: str = PASSWORD) -> None:
    await apply_schema()
    driver = await get_driver()
    for tenant in tenants:
        await bootstrap_policy(tenant)
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
                        "MERGE (u:User {id:$uid, tenant_id:$tenant}) "
                        "ON CREATE SET u.email=$email, u.password_hash=$ph, u.disabled=false, "
                        "u.can_read_source=false "
                        "MERGE (u)-[:MEMBER_OF {role:$role}]->(o)",
                        org=org_id, tenant=tenant, uid=f"usr_{tenant}_{role}",
                        email=f"{role}@{tenant}.dev", ph=hash_password(password), role=role,
                    )).consume()
            # A different organisation inside the same tenant (org-boundary tests).
            await (await session.run(
                "MERGE (t:Tenant {id:$tenant, tenant_id:$tenant}) "
                "MERGE (o:Org {id:$org, tenant_id:$tenant, name:'other'}) "
                "MERGE (t)-[:HAS_ORG]->(o)", tenant=tenant, org=f"{tenant}-other")).consume()
            for role in ("requester", "reviewer"):
                await (await session.run(
                    "MATCH (o:Org {id:$org, tenant_id:$tenant}) "
                    "MERGE (u:User {id:$uid, tenant_id:$tenant}) "
                    "ON CREATE SET u.email=$email, u.password_hash=$ph, u.disabled=false, "
                    "u.can_read_source=false "
                    "MERGE (u)-[:MEMBER_OF {role:$role}]->(o)",
                    org=f"{tenant}-other", tenant=tenant, uid=f"usr_{tenant}_outsider_{role}",
                    email=f"outsider_{role}@{tenant}.dev", ph=hash_password(password), role=role,
                )).consume()
            # Source-reading reviewer (can_read_source=true) vs. reviewer without it.
            await (await session.run(
                "MATCH (o:Org {id:$org, tenant_id:$tenant}) "
                "MERGE (u:User {id:$uid, tenant_id:$tenant}) "
                "ON CREATE SET u.email=$email, u.password_hash=$ph, u.disabled=false, "
                "u.can_read_source=true "
                "MERGE (u)-[:MEMBER_OF {role:'reviewer'}]->(o) "
                "MERGE (u)-[:MEMBER_OF {role:'requester'}]->(o)",
                org=f"{tenant}-ai", tenant=tenant, uid=f"usr_{tenant}_source_reader",
                email=f"source_reader@{tenant}.dev", ph=hash_password(password),
            )).consume()
            # An operator who *can* read source (to contrast with the default operator).
            await (await session.run(
                "MATCH (o:Org {id:$org, tenant_id:$tenant}) "
                "MERGE (u:User {id:$uid, tenant_id:$tenant}) "
                "ON CREATE SET u.email=$email, u.password_hash=$ph, u.disabled=false, "
                "u.can_read_source=true "
                "MERGE (u)-[:MEMBER_OF {role:'operator'}]->(o)",
                org=f"{tenant}-ai", tenant=tenant, uid=f"usr_{tenant}_operator_source",
                email=f"operator_source@{tenant}.dev", ph=hash_password(password),
            )).consume()


def main() -> None:
    import os
    base = os.environ.get("ACC_TENANT", "t-acc21")
    tenants = tuple(sys.argv[1:]) or (base, base + "b", base + "p", base + "f", base + "g")
    try:
        asyncio.run(provision(tenants))
    finally:
        asyncio.run(close_driver())
    print("provisioned", ",".join(tenants))


if __name__ == "__main__":
    main()
