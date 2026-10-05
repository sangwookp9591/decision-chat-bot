import asyncio, sys
from pathlib import Path
root=Path.cwd()
sys.path[:0]=[str(root/'backend'),str(root/'backend/tests/acceptance')]
import provision
from jevtriage.db.driver import close_driver
provision.ROLES=(*provision.ROLES,'labeler')
async def main():
 await provision.provision(('t-audit-e2e-1005',))
 await close_driver()
asyncio.run(main())
print('provisioned t-audit-e2e-1005 (7 roles)')
