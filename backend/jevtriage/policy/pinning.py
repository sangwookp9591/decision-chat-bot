"""Pin the policy version once, in the transaction that creates a run."""
import json


async def pin_config_for_run_in_tx(tx, tenant: str, run_id: str) -> int:
    row = await (await tx.run(
        "MATCH (r:Run {tenant_id:$tenant,id:$run}) RETURN r.versions_json AS versions,"
        "r.config_version AS config_version,r.policy_version AS policy_version",
        tenant=tenant, run=run_id,
    )).single(strict=True)
    versions = json.loads(row["versions"] or "{}")
    version = next((value for value in (
        versions.get("config_version"), versions.get("config"),
        versions.get("policy"), row["config_version"], row["policy_version"],
    ) if value is not None), None)
    if version is None:
        active = await (await tx.run(
            "MATCH (c:ConfigVersion {tenant_id:$tenant,status:'active'}) "
            "RETURN c.version AS version ORDER BY c.version DESC LIMIT 1",
            tenant=tenant,
        )).single()
        version = active["version"] if active else 0
    version = int(version)
    # "config" is the key existing API clients read; "config_version" is the internal name.
    if (versions.get("config_version") != version or versions.get("config") != version
            or row["config_version"] != version):
        versions["config_version"] = version
        versions["config"] = version
        await (await tx.run(
            "MATCH (r:Run {tenant_id:$tenant,id:$run}) "
            "SET r.versions_json=$versions,r.config_version=$version,r.policy_version=$version",
            tenant=tenant, run=run_id, versions=json.dumps(versions), version=version,
        )).consume()
    return version
