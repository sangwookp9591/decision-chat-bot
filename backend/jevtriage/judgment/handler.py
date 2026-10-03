"""Registered worker entrypoint for judgment jobs."""
import json

from jevtriage.judgment.service import execute_judgment


async def handle_judgment(ctx):
    if ctx.versions.get("config") is None:
        async def fix_at_start(tx):
            row = await (await tx.run(
                "MATCH (r:Run {tenant_id:$tenant,id:$run}) "
                "OPTIONAL MATCH (c:ConfigVersion {tenant_id:$tenant}) "
                "WHERE c.created_at <= r.started_at "
                "RETURN r.versions_json AS versions,c.version AS version "
                "ORDER BY version DESC LIMIT 1",
                tenant=ctx.tenant_id, run=ctx.run_id,
            )).single(strict=True)
            versions = json.loads(row["versions"] or "{}")
            if versions.get("config") is None:
                versions["config"] = row["version"] or 0
                versions["policy"] = versions["config"]
                await (await tx.run(
                    "MATCH (r:Run {tenant_id:$tenant,id:$run}) "
                    "SET r.versions_json=$versions,r.policy_version=$version,r.config_version=$version",
                    tenant=ctx.tenant_id, run=ctx.run_id, versions=json.dumps(versions),
                    version=versions["config"],
                )).consume()
            return versions
        ctx.versions = await ctx.commit(fix_at_start, affects_request=True)
    await execute_judgment(ctx)
