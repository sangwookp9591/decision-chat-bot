"""Compare persisted judgments without changing production decisions."""
from __future__ import annotations

import asyncio
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from uuid import uuid4

from jevtriage.config import get_settings
from jevtriage.db.tx import read_tx, write_tx
from jevtriage.domain.serialize import json_value
from jevtriage.journal.writer import JournalWriter
from jevtriage.judgment.jev_client import JevClient
from jevtriage.judgment.pipeline import run_judgment
from jevtriage.judgment.store import load_input
from jevtriage.learning.apply import apply_rules
from jevtriage.policy.service import get_active_snapshot


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


async def _protected_snapshot(tx, tenant):
    # Properties as well as counts matter: an in-place edit is a side effect too.
    rows = await (await tx.run(
        "MATCH (n {tenant_id:$tenant}) WHERE n:Task OR n:Assignment OR n:Review "
        "OR n:Event OR n:Request OR n:Judgment "
        "RETURN labels(n) AS labels,properties(n) AS properties ORDER BY labels, n.id",
        tenant=tenant,
    )).data()
    canonical = _json(rows).encode()
    return {"count": len(rows), "sha256": hashlib.sha256(canonical).hexdigest()}


def _answers(outputs):
    result = {}
    for output in outputs:
        typ = output.get("type")
        answer = {"type": typ}
        if typ == "choice":
            answer["choice"] = output.get("value")
        elif typ == "score":
            answer["score"] = output.get("value")
        elif typ == "noul":
            answer["noul"] = output.get("noul")
        result[output["question_id"]] = answer
    return result


def _human_truth(judgment, corrections):
    truth = {k: judgment.get(k) for k in ("ai_need", "feasibility", "urgency", "lead_org")}
    for correction in corrections:
        if correction["field"] in truth:
            value = correction["corrected_value"]
            truth[correction["field"]] = json.loads(value) if isinstance(value, str) else value
    return truth


class _LimitedClient:
    def __init__(self, inner, limit, guidance):
        self.inner, self.limit, self.guidance = inner, limit, guidance
        self.calls = 0
        self.usage = Counter()

    def ask(self, state, question_map):
        if self.calls >= self.limit:
            raise RuntimeError("shadow_max_calls_exceeded")
        self.calls += 1
        answer = self.inner.ask({**state, "operating_guidance": self.guidance}, question_map)
        self.usage.update(answer.usage)
        return answer


async def validate_rules(tenant: str, actor: str, rule_id: str, version: int,
                         start: datetime, end: datetime, scope_filter=None,
                         max_calls: int | None = None, client=None):
    if start.tzinfo is None or end.tzinfo is None or start >= end or max_calls is not None and max_calls < 0:
        raise ValueError("invalid validation range or call limit")
    base_version, base_config = await get_active_snapshot(tenant)
    limit = int(base_config.get("learning", {}).get("shadow_max_calls", 20))
    if max_calls is not None:
        limit = min(limit, max_calls)

    async def load(tx):
        row = await (await tx.run(
            "MATCH (r:RuleVersion {tenant_id:$tenant,id:$rid}) RETURN r.body AS body",
            tenant=tenant, rid=f"{rule_id}@{version}",
        )).single()
        if row is None:
            return None
        judgments = await (await tx.run(
            "MATCH (j:Judgment {tenant_id:$tenant}) "
            "WHERE j.created_at >= datetime($start) AND j.created_at < datetime($end) "
            "AND ($scope IS NULL OR j.request_id=$scope) "
            "OPTIONAL MATCH (o:ModelOutput {tenant_id:$tenant,run_id:j.run_id}) "
            "OPTIONAL MATCH (t:DraftTask {tenant_id:$tenant,run_id:j.run_id,draft_version:1}) "
            "OPTIONAL MATCH (h:ReviewDecision {tenant_id:$tenant,run_id:j.run_id}) "
            "WHERE h.action IN ['approve','approve_with_changes'] "
            "OPTIONAL MATCH (h)-[:RECORDED]->(c:Correction {tenant_id:$tenant}) "
            "RETURN j,collect(DISTINCT o) AS outputs,collect(DISTINCT t) AS tasks,"
            "collect(DISTINCT h) AS decisions,collect(DISTINCT c) AS corrections "
            "ORDER BY j.created_at,j.id",
            tenant=tenant, start=start.isoformat(), end=end.isoformat(), scope=scope_filter,
        )).data()
        orgs = await (await tx.run(
            "MATCH (q:Request {tenant_id:$tenant}) RETURN q.id AS id,q.org_ids AS orgs",
            tenant=tenant,
        )).data()
        return {"body": json.loads(row["body"]) if isinstance(row["body"], str) else row["body"],
                "judgments": judgments, "orgs": {r["id"]: r["orgs"] or [] for r in orgs},
                "protected": await _protected_snapshot(tx, tenant)}

    data = await read_tx(tenant, load)
    if data is None:
        raise LookupError("rule version not found")
    candidate = [r for r in base_config.get("rules", []) if r["rule_id"] != rule_id] + [data["body"]]
    context = data["body"].get("effect") == "context"
    if context and client is None:
        settings = get_settings()
        client = JevClient(api_key=settings.jev_api_key.get_secret_value(), mode=settings.jev_mode)
    limited = _LimitedClient(client, limit, [data["body"]["context_text"]]) if context else None
    changed, changes, labeled, fix_base, fix_candidate = 0, Counter(), 0, 0, 0
    failures = []
    for row in data["judgments"]:
        j = row["j"]
        try:
            result = {"classifications": {k: j.get(k) for k in ("ai_need", "feasibility", "urgency", "lead_org")},
                      "draft_tasks": [dict(t) for t in row["tasks"]]}
            orgs = data["orgs"].get(j["request_id"], [])
            features = {"requester_orgs": orgs,
                        "signals": {k: v["noul"] for k, v in _answers(row["outputs"]).items()
                                    if v["type"] == "noul"}}
            before, _ = apply_rules(result, base_config.get("rules", []), features=features)
            if context and all(c.get("requester_org") in orgs for c in data["body"]["scope"]["all"]):
                units, chat, _ = await load_input(tenant, j["request_id"], j["revision_id"])
                rerun = await asyncio.to_thread(run_judgment, units, chat, base_config, limited)
                result = rerun
                features["signals"] = {k: v["noul"] for k, v in rerun["raw_model_output"]["answers"].items()
                                       if v.get("type") == "noul"}
            after, _ = apply_rules(result, candidate, features=features)
            base_classes, candidate_classes = before["classifications"], after["classifications"]
            if candidate_classes != base_classes:
                changed += 1
                changes.update(f"{k}:{v}" for k, v in candidate_classes.items() if v != base_classes.get(k))
            if row["decisions"]:
                labeled += 1
                truth = _human_truth(j, row["corrections"])
                fix_base += any(base_classes.get(k) != v for k, v in truth.items())
                fix_candidate += any(candidate_classes.get(k) != v for k, v in truth.items())
        except Exception as exc:  # noqa: BLE001 - one failed sample is recorded; the validation run continues
            failures.append({"judgment_id": j["id"], "error": type(exc).__name__,
                             "reason": "shadow_max_calls_exceeded" if str(exc) == "shadow_max_calls_exceeded" else "shadow_call_failed"})
    validation_id = f"val_{uuid4().hex}"
    run_id = f"run_shadow_{uuid4().hex}"
    async def save(tx):
        side = int(await _protected_snapshot(tx, tenant) != data["protected"])
        status = "failed" if side or failures else "completed"
        await (await tx.run(
            "MATCH (rv:RuleVersion {tenant_id:$tenant,id:$rid}) "
            "CREATE (v:ValidationRun {id:$id,tenant_id:$tenant,rule_version:$rid,"
            "base_config_version:$base,candidate_config_version:$candidate,"
            "from_at:datetime($start),to_at:datetime($end),scope_filter:$scope,"
            "sample_count:$samples,labeled_count:$labeled,changed_count:$changed,"
            "changes_by_value:$changes,human_correction_needed_base:$hb,"
            "human_correction_needed_candidate:$hc,review_transition_base:0,"
            "review_transition_candidate:0,failures:$failures,side_effects:$side,"
            "max_calls:$limit,calls:$calls,usage:$usage,status:$status,run_kind:'shadow',"
            "created_by:$actor,created_at:datetime()})-[:VALIDATES]->(rv) "
            "CREATE (run:Run {id:$run_id,tenant_id:$tenant,run_kind:'shadow',status:$status,created_at:datetime()}) "
            "CREATE (v)-[:HAS_SHADOW_RUN]->(run)",
            tenant=tenant, rid=f"{rule_id}@{version}", id=validation_id, run_id=run_id, base=base_version,
            candidate=f"{base_version}+{rule_id}@{version}", start=start.isoformat(),
            end=end.isoformat(), scope=scope_filter, samples=len(data["judgments"]),
            labeled=labeled, changed=changed, changes=_json(dict(changes)), hb=fix_base,
            hc=fix_candidate, failures=_json(failures), side=side, limit=limit,
            calls=limited.calls if limited else 0, usage=_json(dict(limited.usage) if limited else {}),
            status=status, actor=actor,
        )).consume()
        return side, status
    side, status = await write_tx(tenant, save)
    JournalWriter().append({"event_id": f"evt_{uuid4().hex}", "attempt_id": f"att_{uuid4().hex}",
                            "run_id": run_id, "tenant_id": tenant, "kind": "shadow_validation",
                            "run_kind": "shadow", "ts": datetime.now(UTC).isoformat()})
    return {"id": validation_id, "run_id": run_id, "rule_version": f"{rule_id}@{version}", "base_config_version": base_version,
            "candidate_config_version": f"{base_version}+{rule_id}@{version}",
            "from": start.isoformat(), "to": end.isoformat(), "scope_filter": scope_filter,
            "sample_count": len(data["judgments"]), "labeled_count": labeled,
            "changed_count": changed, "changes_by_value": dict(changes),
            "human_correction_needed_base": fix_base,
            "human_correction_needed_candidate": fix_candidate,
            "review_transition_base": 0, "review_transition_candidate": 0,
            "failures": failures, "side_effects": side, "status": status,
            "max_calls": limit, "calls": limited.calls if limited else 0,
            "usage": dict(limited.usage) if limited else {}}


async def validation_detail(tenant: str, validation_id: str) -> dict | None:
    async def op(tx):
        row = await (await tx.run(
            "MATCH (v:ValidationRun {tenant_id:$tenant,id:$id}) "
            "RETURN properties(v) AS validation",
            tenant=tenant, id=validation_id,
        )).single()
        return dict(row["validation"]) if row else None
    return json_value(await read_tx(tenant, op))


async def rule_validations(tenant: str, rule_id: str, version: int) -> list[dict]:
    async def op(tx):
        rows = await (await tx.run(
            "MATCH (v:ValidationRun {tenant_id:$tenant})-[:VALIDATES]->"
            "(:RuleVersion {tenant_id:$tenant,id:$rule}) "
            "RETURN properties(v) AS validation ORDER BY v.created_at DESC,v.id DESC",
            tenant=tenant, rule=f"{rule_id}@{version}",
        )).data()
        return [dict(row["validation"]) for row in rows]
    return json_value(await read_tx(tenant, op))
