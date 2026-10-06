"""Tenant and organization read boundary for versioned rules."""
from ildongi.auth.policy import can, redact_source


def readable_rule(principal, detail):
    versions = []
    for version in detail["versions"]:
        orgs = [p["requester_org"] for p in version["body"].get("scope", {}).get("all", [])
                if "requester_org" in p]
        if can(principal, "rule:read", {"tenant_id": principal.tenant_id, "org_ids": orgs}):
            versions.append(version)
    return redact_source(principal, {**detail, "versions": versions}) if versions else None
