"""Observed rule outcomes, separate from operational SLO accounting."""
from __future__ import annotations

from datetime import timedelta

from ildongi.auth.policy import can
from ildongi.db.tx import read_tx
from ildongi.domain.serialize import to_native
from ildongi.policy.service import get_active_snapshot


def _native(value):
    return to_native(value)


def _percentile(values, fraction):
    # Monitoring uses nearest-rank; retain interpolation here because changing
    # this output would change the established learning effects API values.
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    low = int(position)
    return round(ordered[low] + (ordered[min(low + 1, len(ordered) - 1)] - ordered[low]) * (position - low), 2)


def _metrics(rows):
    n = len(rows)
    durations = []
    for row in rows:
        start, committed = _native(row["started_at"]), _native(row["committed_at"])
        if start is not None and committed is not None:
            durations.append((committed - start).total_seconds() * 1000)
    counts = {
        "sample_count": n,
        "labeled_count": sum(row.get("labeled", False) for row in rows),
        "classification_changes": sum(row["changed"] for row in rows),
        "corrections": sum(row["corrected"] for row in rows),
        "review_transitions": sum(row["reviewed"] for row in rows),
        "failures": sum(row["failed"] for row in rows),
        "latency_sample_count": len(durations),
        "latency_p50_ms": _percentile(durations, .5),
        "latency_p95_ms": _percentile(durations, .95),
    }
    for name, field in (("classification_change_rate", "classification_changes"),
                        ("correction_rate", "corrections"),
                        ("review_transition_rate", "review_transitions"),
                        ("failure_rate", "failures")):
        counts[name] = counts[field] / n if n else None
    return counts


def _effect(before, after, minimum):
    if min(before["sample_count"], after["sample_count"],
           before["labeled_count"], after["labeled_count"]) < minimum:
        return "insufficient_sample"
    changes = [after[key] - before[key] for key in ("correction_rate", "failure_rate")]
    if any(value > 0 for value in changes):
        return "worse"
    if all(value < 0 for value in changes):
        return "improved"
    if any(value < 0 for value in changes):
        return "partial"
    return "no_change"


async def rule_effects(tenant: str, rule_id: str, days: int | None = None, principal=None):
    config_version, config = await get_active_snapshot(tenant)
    days = int(config.get("learning", {}).get("effect_window_days", 7)) if days is None else days
    if days < 1 or days > 90:
        raise ValueError("days must be between 1 and 90")
    minimum = int(config.get("learning", {}).get("min_effect_sample", 20))

    async def op(tx):
        published = await (await tx.run(
            "MATCH (r:RuleVersion {tenant_id:$tenant,rule_id:$rule})-[:PUBLISHED_IN]->"
            "(c:ConfigVersion {tenant_id:$tenant}) RETURN min(c.created_at) AS at",
            tenant=tenant, rule=rule_id,
        )).single()
        if not published or published["at"] is None:
            raise LookupError("rule has no publication")
        at = _native(published["at"])
        start, end = at - timedelta(days=days), at + timedelta(days=days)
        rows = await (await tx.run(
            "MATCH (run:Run {tenant_id:$tenant}) "
            "WHERE coalesce(run.run_kind,'production') <> 'shadow' AND run.started_at >= datetime($start) "
            "AND run.started_at < datetime($end) "
            "OPTIONAL MATCH (q:Request {tenant_id:$tenant,id:run.request_id}) "
            "OPTIONAL MATCH (c:Correction {tenant_id:$tenant,run_id:run.id}) "
            "OPTIONAL MATCH (h:ReviewDecision {tenant_id:$tenant,run_id:run.id}) "
            "WHERE h.action IN ['approve','approve_with_changes'] "
            "OPTIONAL MATCH (v:Review {tenant_id:$tenant,run_id:run.id}) "
            "OPTIONAL MATCH (s:RunStep {tenant_id:$tenant,run_id:run.id})"
            "-[a:APPLIED]->(rule:RuleVersion {tenant_id:$tenant,rule_id:$rule}) "
            "RETURN run.id AS id,run.started_at AS started_at,"
            "run.first_judgment_committed_at AS committed_at,run.status AS status,"
            "properties(q) AS request_meta,count(DISTINCT c) AS corrections,"
            "count(DISTINCT v) AS reviews,count(DISTINCT h) AS labels,"
            "collect(DISTINCT {outcome:a.outcome,before:a.before,after:a.after}) AS applications",
            tenant=tenant, rule=rule_id, start=start.isoformat(), end=end.isoformat(),
        )).data()
        shadows = await (await tx.run(
            "MATCH (v:ValidationRun {tenant_id:$tenant}) "
            "WHERE v.rule_version STARTS WITH $prefix AND v.run_kind='shadow' "
            "RETURN count(v) AS n", tenant=tenant, prefix=rule_id + "@",
        )).single()
        return at, start, end, rows, shadows["n"]

    at, start, end, rows, shadows = await read_tx(tenant, op)
    normalized = []
    for row in rows:
        if principal and "rule_admin" not in principal.roles and not can(
            principal, "learn_read", row["request_meta"] or {"tenant_id": tenant}
        ):
            continue
        apps = [a for a in row["applications"] if a["outcome"] in {"used", "out_of_scope"}]
        outcomes = {a["outcome"] for a in apps}
        changed = any(a["outcome"] == "used" and a["before"] != a["after"] for a in apps)
        normalized.append({"started_at": row["started_at"], "committed_at": row["committed_at"],
                           "changed": bool(changed), "corrected": bool(row["corrections"]),
                           "labeled": bool(row["labels"]), "reviewed": bool(row["reviews"]), "failed": row["status"] == "failed",
                           "outcome": "used" if "used" in outcomes else
                           "out_of_scope" if "out_of_scope" in outcomes else None})
    before_rows = [r for r in normalized if _native(r["started_at"]) < at]
    after_rows = [r for r in normalized if _native(r["started_at"]) >= at]
    before, after = _metrics(before_rows), _metrics(after_rows)
    groups = {outcome: _metrics([r for r in after_rows if r["outcome"] == outcome])
              for outcome in ("used", "out_of_scope")}
    return {"rule_id": rule_id, "active_config_version": config_version,
            "published_at": at.isoformat(), "window_days": days,
            "labeled_definition": "approved_human_review_per_run",
            "minimum_sample": minimum, "sample_count": len(normalized),
            "before_after": {"before": before, "after": after,
                             "before_from": start.isoformat(), "before_to": at.isoformat(),
                             "after_from": at.isoformat(), "after_to": end.isoformat()},
            "groups": groups, "effect": _effect(before, after, minimum),
            "shadow_runs_excluded": shadows, "slo_included": False,
            "comparison_conditions": "게시 시각 전후 동일 길이 창의 실제 Run; 게시 후 APPLIED used/out_of_scope 집단; shadow 제외"}
