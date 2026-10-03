"""Provision tenant t-ux2 (role accounts) and seed a rule with three versions for the judgment-map E2E.

Run with backend/.venv/bin/python from the backend directory. Idempotent: earlier seed nodes are replaced.
"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend" / "tests" / "acceptance"))

from provision import provision  # noqa: E402

from jevtriage.db.driver import close_driver  # noqa: E402
from jevtriage.db.tx import write_tx  # noqa: E402

TENANT = sys.argv[1] if len(sys.argv) > 1 else "t-ux2"
RULE = "R-UX-01"


async def seed() -> None:
    await provision((TENANT,))

    async def op(tx):
        await (await tx.run("MATCH (n {tenant_id:$t}) WHERE n.id STARTS WITH 'ux2seed_' OR n.rule_id=$rule DETACH DELETE n",
                            t=TENANT, rule=RULE)).consume()
        await (await tx.run(
            "CREATE (rq:Request {id:'ux2seed_req',tenant_id:$t,created_by:'x',org_ids:[$org],status:'completed',created_at:datetime()}) "
            "CREATE (run:Run {id:'ux2seed_run',tenant_id:$t,request_id:'ux2seed_req'}) "
            "CREATE (c:Correction {id:'ux2seed_c1',tenant_id:$t,request_id:'ux2seed_req',run_id:'ux2seed_run',field:'lead_org',"
            "ai_value:'\"AI팀\"',corrected_value:'\"IT팀\"',corrected_by:'rev',corrected_at:datetime(),config_version:1}) "
            "CREATE (cand:RuleCandidate {id:'ux2seed_cand',tenant_id:$t,field:'lead_org',status:'approved',source:'ai',"
            "author:'code:candidate@v1',proposed_body:'{}',created_at:datetime()}) CREATE (cand)-[:SUPPORTED_BY {role:'support'}]->(c)",
            t=TENANT, org=f"{TENANT}-ai")).consume()
        for n, status, run in ((1, "reverted", True), (2, "published", True), (3, "validating", False)):
            await (await tx.run(
                "MATCH (cand:RuleCandidate {id:'ux2seed_cand',tenant_id:$t}) "
                "CREATE (d:RuleDecision {id:$dec,tenant_id:$t,action:'approve',decided_by:'admin',reason:'검토',confirmed_scope:'{}',decided_at:datetime()}) "
                "CREATE (d)-[:DECIDES]->(cand) "
                "CREATE (rv:RuleVersion {id:$rv,tenant_id:$t,rule_id:$rule,version:$n,status:$status,"
                "body:'{\"effect\":\"rule\",\"target\":\"lead_org\",\"scope\":{},\"action\":{\"set\":\"IT팀\"}}',created_at:datetime()}) "
                "CREATE (rv)-[:DERIVED_FROM]->(d)",
                t=TENANT, dec=f"ux2seed_dec{n}", rv=f"{RULE}@{n}", rule=RULE, n=n, status=status)).consume()
            if run:
                await (await tx.run(
                    "MATCH (r:Run {id:'ux2seed_run',tenant_id:$t}), (rv:RuleVersion {id:$rv,tenant_id:$t}) "
                    "CREATE (s:RunStep {id:$step,tenant_id:$t,run_id:'ux2seed_run',name:$name,kind:'rule',status:'succeeded',started_at:datetime(),actor:'worker'}) "
                    "CREATE (r)-[:HAS_STEP]->(s) CREATE (s)-[:APPLIED {outcome:'used',before:'\"AI팀\"',after:'\"IT팀\"',rule_version:$rv}]->(rv)",
                    t=TENANT, rv=f"{RULE}@{n}", step=f"ux2seed_step{n}", name=f"규칙 적용 v{n}")).consume()

    await write_tx(TENANT, op)


try:
    asyncio.run(seed())
finally:
    asyncio.run(close_driver())
print("seeded", TENANT)
