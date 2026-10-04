"""One request, role, and source authorization contract for API callers."""
from __future__ import annotations

from typing import Any

from jevtriage.auth.types import Principal

SOURCE_FIELDS = frozenset({"text", "source_text", "extracted_text", "raw_text", "preview"})


def _request_scope(principal: Principal, meta: dict[str, Any]) -> bool:
    if meta.get("tenant_id") != principal.tenant_id:
        return False
    if "operator" in principal.roles:
        return True
    orgs = set(meta.get("org_ids") or ()) | set(meta.get("shared_org_ids") or ())
    return meta.get("created_by") == principal.user_id or bool(orgs.intersection(principal.org_ids))


def can(principal: Principal, action: str, resource_meta: dict[str, Any]) -> bool:
    """Evaluate a named action against resource metadata from the tenant store."""
    if resource_meta.get("tenant_id") != principal.tenant_id:
        return False
    roles = principal.roles
    if action == "view_request":
        return _request_scope(principal, resource_meta)
    if action == "request:read":
        # Authors can read their own submitted source, independently of an
        # organization-wide source-reading grant.
        return resource_meta.get("created_by") == principal.user_id
    if action == "read_source":
        return (principal.can_read_source and
                (_request_scope(principal, resource_meta) or can(principal, "review", resource_meta)))
    if action == "review":
        required = resource_meta.get("required_reviewer_org")
        return ("reviewer" in roles and bool(required)
                and required in principal.org_ids)
    if action in {"view_task", "view_trace"}:
        if action == "view_task" and "team_member" in roles and not roles.intersection({"reviewer", "operator"}):
            return bool(set(resource_meta.get("task_org_ids") or ()).intersection(principal.org_ids))
        return _request_scope(principal, resource_meta)
    if action == "transition_task":
        return ("team_member" in roles
                and bool(set(resource_meta.get("task_org_ids") or ()).intersection(principal.org_ids)))
    if action == "view_graph" and not any(key in resource_meta for key in ("created_by", "org_ids", "shared_org_ids")):
        return bool(roles.intersection({"reviewer", "rule_admin", "operator"}))
    if action in {"view_graph", "learn_read"}:
        return bool(roles.intersection({"reviewer", "rule_admin", "operator"})) and _request_scope(principal, resource_meta)
    if action == "learn_admin":
        return "rule_admin" in roles
    if action == "learn_propose":
        return bool(roles.intersection({"reviewer", "rule_admin"}))
    tenant_roles = {"policy_edit": {"policy_editor"}, "monitoring_read": {"operator"}}
    if action == "eval_label":
        return bool(roles.intersection({"labeler", "reviewer"}))
    if action in tenant_roles:
        return bool(roles.intersection(tenant_roles[action]))
    raise ValueError(f"Unknown authorization action: {action}")


def scope_filter_cypher(principal: Principal) -> str:
    """Cypher equivalent of the view_request tenant and organization predicate."""
    if "operator" in principal.roles:
        return "r.tenant_id = $tenant_id"
    return ("r.tenant_id = $tenant_id AND (r.created_by = $user_id OR "
            "any(org_id IN coalesce(r.org_ids, []) + coalesce(r.shared_org_ids, []) "
            "WHERE org_id IN $org_ids))")


def redact_source(principal: Principal, payload: Any) -> Any:
    """Copy an API payload without raw source fields for non-source readers."""
    if principal.can_read_source:
        return payload
    if isinstance(payload, dict):
        return {key: redact_source(principal, value) for key, value in payload.items()
                if key not in SOURCE_FIELDS}
    if isinstance(payload, list):
        return [redact_source(principal, value) for value in payload]
    if isinstance(payload, tuple):
        return tuple(redact_source(principal, value) for value in payload)
    return payload
