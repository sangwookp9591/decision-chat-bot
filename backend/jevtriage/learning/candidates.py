"""Deterministic candidate generation from observed review corrections."""
from __future__ import annotations

import asyncio
import hashlib
import json
from collections import defaultdict
from typing import Any

from jevtriage.db.tx import read_tx, write_tx
from jevtriage.learning.corrections import list_corrections
from jevtriage.policy.service import get_active_snapshot

TARGETS = {"ai_need": "ai_need", "feasibility": "feasibility", "urgency": "urgency",
           "lead_org": "lead_org"}
FIELDS = set(TARGETS)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


async def _features(tenant: str, request_id: str, run_id: str) -> tuple[dict, list[dict]]:
    async def op(tx):
        row = await (await tx.run(
            "MATCH (j:Judgment {tenant_id:$tenant,request_id:$request,run_id:$run}) RETURN j LIMIT 1",
            tenant=tenant, request=request_id, run=run_id,
        )).single()
        if not row:
            return {}, []
        judgment = dict(row["j"])
        request_row = await (await tx.run(
            "MATCH (r:Request {tenant_id:$tenant,id:$request}) RETURN r.org_ids AS org_ids",
            tenant=tenant, request=request_id,
        )).single()
        judgment["_request_org_ids"] = list(request_row["org_ids"] or []) if request_row else []
        output_rows = await (await tx.run(
            "MATCH (o:ModelOutput {tenant_id:$tenant,run_id:$run}) WHERE o.type='noul' "
            "RETURN o.question_id AS key,o.noul AS value",
            tenant=tenant, run=run_id,
        )).data()
        return judgment, [dict(r) for r in output_rows]
    return await read_tx(tenant, op)


def _feature_predicates(judgment: dict, outputs: list[dict]) -> dict[str, dict]:
    result = {}
    for key in ("ai_need", "feasibility", "urgency", "lead_org"):
        if judgment.get(key) is not None:
            result[key] = {"field": key, "op": "eq", "value": judgment[key]}
    for item in outputs:
        try:
            val = float(item["value"])
        except (TypeError, ValueError):
            continue
        if item.get("key"):
            result[f"signal:{item['key']}"] = {"signal": item["key"], "op": "gte" if val >= .5 else "lte",
                                                "value": .5}
    return result


def _target(field: str, value: Any) -> str | None:
    if field == "lead_org":
        return "lead_org"
    return TARGETS.get(field)


async def generate_candidates(tenant: str) -> list[dict]:
    _, config = await get_active_snapshot(tenant)
    min_support = int((config.get("learning") or {}).get("min_support", 3))
    corrections = await list_corrections(tenant, limit=5000)
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for correction in corrections:
        field = correction.get("field")
        if field not in FIELDS:
            continue
        old, new = correction.get("ai_value"), correction.get("corrected_value")
        if old == new:
            continue
        groups[(field, _json(old), _json(new))].append(correction)
    created = []
    for (field, old_json, new_json), members in groups.items():
        case_data = []
        for item in members:
            judgment, outputs = await _features(tenant, item["request_id"], item["run_id"])
            case_data.append((item, _feature_predicates(judgment, outputs), judgment.get("_request_org_ids", [])))
        common = set.intersection(*(set(features) for _, features, _ in case_data)) if case_data else set()
        common = {key for key in common if all(features[key] == case_data[0][1][key]
                                               for _, features, _ in case_data)}
        scope_all = [case_data[0][1][key] for key in sorted(common)] if case_data else []
        scope = {"all": scope_all}
        # Gather observable review decisions in the tenant; only decisions whose judgment matches
        # every proposed predicate count as counterexamples.
        async def counter_op(tx):
            return await (await tx.run(
                "MATCH (h:ReviewDecision {tenant_id:$tenant}) "
                "OPTIONAL MATCH (h)-[:RECORDED]->(c:Correction {tenant_id:$tenant}) "
                "WITH h,collect(c) AS corrections WHERE h.action IN ['approve','approve_with_changes'] "
                "RETURN h.id AS decision_id,h.action AS action,h.request_id AS request_id,h.run_id AS run_id,"
                "[c IN corrections WHERE c IS NOT NULL | {field:c.field,value:c.corrected_value}] AS edits",
                tenant=tenant,
            )).data()
        decisions = await read_tx(tenant, counter_op)
        support_requests = {item["request_id"] for item, _, _ in case_data}
        counters = []
        for decision in decisions:
            edits = decision.get("edits") or []
            target_edits = [edit for edit in edits if edit.get("field") == field]
            if decision.get("request_id") in support_requests or any(
                    json.loads(edit["value"]) == json.loads(new_json) for edit in target_edits):
                continue
            judgment, outputs = await _features(tenant, decision.get("request_id"), decision.get("run_id"))
            features = _feature_predicates(judgment, outputs)
            if all(features.get(key) == case_data[0][1][key] for key in common):
                counters.append(decision["decision_id"])
        support_ids = [item["id"] for item, _, _ in case_data]
        status = "제안" if len(support_ids) >= min_support else "자료 부족"
        direction = json.loads(new_json)
        rule_id = f"R-{field.upper()}-01"
        proposed_body = {"schema": "rule-v1", "rule_id": rule_id, "version": 1,
                         "effect": "rule", "target": _target(field, direction),
                         "scope": scope, "action": {"set": direction},
                         "candidate_id": "pending", "decision_id": "pending"}
        identity = _json([field, old_json, new_json, scope])
        candidate_id = "cand_" + hashlib.sha256(identity.encode()).hexdigest()[:24]
        proposed_body["candidate_id"] = candidate_id
        organizations = {org for _, _, orgs in case_data for org in orgs}
        uncertainty = {"support_count": len(support_ids), "counter_count": len(counters),
                       "organization_count": len(organizations),
                       "single_organization_bias": len(organizations) == 1, "minimum_support": min_support}
        support_count, counter_count = len(support_ids), len(counters)
        body_json, uncertainty_json = _json(proposed_body), _json(uncertainty)
        async def store(tx, *, candidate_id=candidate_id, field=field, body=body_json,
                        status=status, support_ids=support_ids, counters=counters,
                        support_count=support_count, counter_count=counter_count,
                        uncertainty_json=uncertainty_json):
            await (await tx.run(
                "MERGE (n:RuleCandidate {tenant_id:$tenant,id:$id}) "
                "ON CREATE SET n.field=$field,n.proposed_body=$body,n.status=$status,n.source='ai',"
                "n.author='code:candidate@v1',n.support_count=$support,n.counter_count=$counter,"
                "n.uncertainty=$uncertainty,n.created_at=datetime() "
                "WITH n UNWIND $supports AS cid MATCH (c:Correction {tenant_id:$tenant,id:cid}) "
                "MERGE (n)-[:SUPPORTED_BY {role:'support'}]->(c) "
                "WITH DISTINCT n UNWIND $counters AS did MATCH (d:ReviewDecision {tenant_id:$tenant,id:did}) "
                "MERGE (n)-[:SUPPORTED_BY {role:'counter'}]->(d) RETURN n",
                tenant=tenant,id=candidate_id,field=field,body=body,status=status,
                support=support_count,counter=counter_count,uncertainty=uncertainty_json,
                supports=support_ids,counters=counters,
            )).consume()
        await write_tx(tenant, store)
        created.append({"id":candidate_id,"field":field,"status":status,"source":"ai",
                        "support_count":len(support_ids),"counter_count":len(counters),"uncertainty":uncertainty,
                        "proposed_body":proposed_body})
    return created


async def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", required=True)
    args = parser.parse_args()
    print(json.dumps(await generate_candidates(args.tenant), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
