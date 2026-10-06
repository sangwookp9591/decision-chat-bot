"""Isolated demo accounts; same provisioning shape as bootstrap_dev, no fake judgments."""
import asyncio
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend/tests/acceptance'))
sys.path.insert(0, str(ROOT / 'backend'))
import provision
from ildongi.db.driver import close_driver, get_driver
provision.ROLES = (*provision.ROLES, 'labeler')
async def main():
    await provision.provision(tuple(sys.argv[1:]))
    driver = await get_driver()
    async with driver.session() as session:
        await (await session.run('MATCH (u:User) WHERE u.tenant_id IN $tenants SET u.can_read_source=true', tenants=sys.argv[1:])).consume()
    await close_driver()
asyncio.run(main())
