"""Judgment graph/path/node API against real Neo4j with seeded stored relationships."""
from __future__ import annotations

from uuid import uuid4

import httpx
import pytest
import pytest_asyncio

from ildongi.auth.core import Principal, get_principal
from ildongi.db.schema import apply_schema
from ildongi.db.tx import cross_tenant_tx, read_tx, write_tx
from ildongi.main import create_app

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def world():
    key = uuid4().hex[:10]
    tenant, other = f"graph_{key}", f"graph_other_{key}"
    ids = {name: f"{name}_{key}" for name in (
        "req1", "req2", "run1", "run2", "run3", "j1", "mo1", "mo2", "es1", "rd1", "c1", "c9",
        "cand1", "dec1", "val1", "step_ai", "step_rule", "step_oos")}
    ids["rv"] = f"R-ROUTE-07@{key}"
    ids["rule"] = "R-ROUTE-07"
    ids["cfg"] = f"cfg_{tenant}_2"
    await apply_schema()

    async def seed(tx):
        await (await tx.run(
            "CREATE (rq1:Request {id:$req1,tenant_id:$tenant,created_by:'u1',org_ids:['org_a'],created_at:datetime()}) "
            "CREATE (rq2:Request {id:$req2,tenant_id:$tenant,created_by:'u2',org_ids:['org_b'],created_at:datetime()}) "
            "CREATE (r1:Run {id:$run1,tenant_id:$tenant,request_id:$req1}) "
            "CREATE (r2:Run {id:$run2,tenant_id:$tenant,request_id:$req2}) "
            "CREATE (r3:Run {id:$run3,tenant_id:$tenant,request_id:$req2}) "
            "CREATE (j:Judgment {id:$j1,tenant_id:$tenant,request_id:$req1,run_id:$run1}) "
            "CREATE (r1)-[:PRODUCED]->(j) "
            "CREATE (mo1:ModelOutput {id:$mo1,tenant_id:$tenant,question_id:'lead_org',type:'Choice',value:'AI팀',confidence:0.72,model:'ai-test',run_id:$run1}) "
            "CREATE (mo2:ModelOutput {id:$mo2,tenant_id:$tenant,question_id:'feasibility',type:'Choice',value:'조건부 가능',confidence:0.67,model:'ai-test',run_id:$run1}) "
            "CREATE (mo1)-[:OF_JUDGMENT]->(j) CREATE (mo2)-[:OF_JUDGMENT]->(j) "
            "CREATE (es:EvidenceSpan {id:$es1,tenant_id:$tenant,request_id:$req1,revision_id:'rev_1',attachment_id:'att_1',location_json:'{\"page\":3}',source_text:'원문 비공개 텍스트'}) "
            "CREATE (mo1)-[:CITES {prob:0.9}]->(es) "
            "CREATE (rd:ReviewDecision {id:$rd1,tenant_id:$tenant,request_id:$req1,run_id:$run1,action:'approve_with_changes',actor_id:'rev1',review_version:1,created_at:datetime()}) "
            "CREATE (c1:Correction {id:$c1,tenant_id:$tenant,request_id:$req1,run_id:$run1,field:'lead_org',ai_value:'\"AI팀\"',corrected_value:'\"IT팀\"',corrected_by:'rev1',corrected_at:datetime(),config_version:1}) "
            "CREATE (rd)-[:RECORDED]->(c1) CREATE (c1)-[:CORRECTS]->(mo1) "
            "CREATE (c9:Correction {id:$c9,tenant_id:$tenant,request_id:$req2,run_id:$run2,field:'urgency',ai_value:'\"일반\"',corrected_value:'\"긴급\"',corrected_by:'rev2',corrected_at:datetime(),config_version:1}) "
            "CREATE (cand:RuleCandidate {id:$cand1,tenant_id:$tenant,field:'lead_org',status:'제안',source:'ai',author:'code:candidate@v1',proposed_body:'{\"action\":{\"set\":\"IT팀\"}}',created_at:datetime()}) "
            "CREATE (cand)-[:SUPPORTED_BY {role:'support'}]->(c1) "
            "CREATE (dec:RuleDecision {id:$dec1,tenant_id:$tenant,action:'approve',decided_by:'admin',reason:'검토',confirmed_scope:'{\"all\":[]}',decided_at:datetime()}) "
            "CREATE (dec)-[:DECIDES]->(cand) "
            "CREATE (rv:RuleVersion {id:$rv,tenant_id:$tenant,rule_id:$rule,version:1,status:'published',body:'{\"effect\":\"rule\",\"target\":\"lead_org\",\"scope\":{\"all\":[]},\"action\":{\"set\":\"IT팀\"}}',created_at:datetime()}) "
            "CREATE (rv)-[:DERIVED_FROM]->(dec) "
            "CREATE (val:ValidationRun {id:$val1,tenant_id:$tenant,status:'completed',side_effects:0,created_at:datetime()}) "
            "CREATE (val)-[:VALIDATES]->(rv) "
            "CREATE (cfg:ConfigVersion {id:$cfg,tenant_id:$tenant,version:2,status:'active',created_by:'admin',reason:'게시',created_at:datetime()}) "
            "CREATE (rv)-[:PUBLISHED_IN]->(cfg) "
            "CREATE (s1:RunStep {id:$step_ai,tenant_id:$tenant,run_id:$run1,name:'Decision AI 판단',kind:'ai',status:'succeeded',started_at:datetime(),actor:'worker'}) "
            "CREATE (r1)-[:HAS_STEP]->(s1) CREATE (s1)-[:USED_OUTPUT]->(mo1) CREATE (s1)-[:USED_OUTPUT]->(mo2) "
            "CREATE (s2:RunStep {id:$step_rule,tenant_id:$tenant,run_id:$run2,name:'규칙 적용',kind:'rule',status:'succeeded',started_at:datetime(),actor:'worker'}) "
            "CREATE (r2)-[:HAS_STEP]->(s2) CREATE (s2)-[:APPLIED {outcome:'used',before:'\"AI팀\"',after:'\"IT팀\"',rule_version:$rv}]->(rv) "
            "CREATE (s3:RunStep {id:$step_oos,tenant_id:$tenant,run_id:$run3,name:'규칙 적용',kind:'rule',status:'succeeded',started_at:datetime(),actor:'worker'}) "
            "CREATE (r3)-[:HAS_STEP]->(s3) CREATE (s3)-[:APPLIED {outcome:'out_of_scope',before:'\"AI팀\"',after:'\"AI팀\"',rule_version:$rv}]->(rv)",
            tenant=tenant, **ids)).consume()
        await (await tx.run(
            "CREATE (:Request {id:'req_other',tenant_id:$o,created_by:'z',org_ids:[],created_at:datetime()}) "
            "CREATE (:Correction {id:$id,tenant_id:$o,request_id:'req_other',run_id:'run_other',field:'x',corrected_by:'z',corrected_at:datetime()})",
            id=f"cor_other_{key}", o=other)).consume()
    await cross_tenant_tx("integration-fixture-seed", seed, write=True)
    yield {"tenant": tenant, "other": other, "ids": ids, "key": key}
    for value in (tenant, other):
        await write_tx(value, lambda tx, value=value: tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=value))


def client_for(principal: Principal):
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: principal
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def operator(world, **extra):
    return Principal(world["tenant"], "op", (), frozenset({"operator"}), **extra)


async def db_edge_count(world, id_list):
    async def op(tx):
        row = await (await tx.run(
            "MATCH (a {tenant_id:$tenant})-[r:CITES|CORRECTS|RECORDED|SUPPORTED_BY|DECIDES|DERIVED_FROM|PUBLISHED_IN|VALIDATES|APPLIED|USED_OUTPUT]->(b {tenant_id:$tenant}) "
            "WHERE a.id IN $ids AND b.id IN $ids RETURN count(r) AS n", tenant=world["tenant"], ids=id_list)).single()
        return row["n"]
    return await read_tx(world["tenant"], op)


async def test_rule_graph_matches_stored_nodes_and_edges_exactly(world):
    i = world["ids"]
    async with client_for(operator(world)) as client:
        body = (await client.get("/api/graph/judgment", params={"rule_id": "R-ROUTE-07"})).json()
    nodes = {n["id"] for n in body["nodes"]}
    assert nodes == {i[k] for k in ("rv", "dec1", "cand1", "c1", "mo1", "es1", "val1", "cfg", "step_rule", "step_oos")}
    kinds = {n["id"]: (n["kind"], n["layer"]) for n in body["nodes"]}
    assert kinds[i["es1"]] == ("EvidenceSpan", 1) and kinds[i["cand1"]] == ("RuleCandidate", 2)
    assert kinds[i["dec1"]] == ("RuleDecision", 3) and kinds[i["cfg"]] == ("ConfigVersion", 4)
    assert kinds[i["step_oos"]] == ("RunStep", 5)
    expected_edges = {
        f"DERIVED_FROM:{i['rv']}->{i['dec1']}", f"DECIDES:{i['dec1']}->{i['cand1']}",
        f"SUPPORTED_BY:{i['cand1']}->{i['c1']}", f"CORRECTS:{i['c1']}->{i['mo1']}",
        f"CITES:{i['mo1']}->{i['es1']}", f"VALIDATES:{i['val1']}->{i['rv']}",
        f"PUBLISHED_IN:{i['rv']}->{i['cfg']}", f"APPLIED:{i['step_rule']}->{i['rv']}",
        f"APPLIED:{i['step_oos']}->{i['rv']}"}
    assert {e["id"] for e in body["edges"]} == expected_edges
    assert body["edge_count"] == await db_edge_count(world, sorted(nodes)) == 9
    applied = {e["source"]: e["props"]["outcome"] for e in body["edges"] if e["type"] == "APPLIED"}
    assert applied == {i["step_rule"]: "used", i["step_oos"]: "out_of_scope"}
    # No fabricated link: the step that used the model output is not related to the rule here.
    assert not any(e["source"] == i["step_ai"] for e in body["edges"])
    assert [layer["count"] for layer in body["layers"]] == [3, 1, 1, 3, 2]


async def test_request_graph_has_isolated_nodes_and_no_synthesized_edges(world):
    i = world["ids"]
    async with client_for(operator(world)) as client:
        body = (await client.get("/api/graph/judgment", params={"request_id": i["req1"]})).json()
    nodes = {n["id"] for n in body["nodes"]}
    assert {i["mo1"], i["mo2"], i["es1"], i["c1"], i["rd1"], i["step_ai"]} <= nodes
    assert i["c9"] not in nodes  # another request's correction without any relationship
    mo2_edges = [e for e in body["edges"] if i["mo2"] in (e["source"], e["target"])]
    assert [e["type"] for e in mo2_edges] == ["USED_OUTPUT"]  # mo2 cites nothing; no CITES invented
    assert body["edge_count"] == await db_edge_count(world, sorted(nodes))
    # An unrelated, relationship-less correction renders as a node without edges.
    async with client_for(operator(world)) as client:
        lone = (await client.get("/api/graph/judgment", params={"request_id": i["req2"]})).json()
    c9 = next(n for n in lone["nodes"] if n["id"] == i["c9"])
    assert c9["upstream_count"] == c9["downstream_count"] == 0


async def test_path_both_directions_with_depth_and_limits(world):
    i = world["ids"]
    async with client_for(operator(world)) as client:
        up = (await client.get("/api/graph/judgment/path", params={"node_id": i["step_rule"], "direction": "up"})).json()
        down = (await client.get("/api/graph/judgment/path", params={"node_id": i["es1"], "direction": "down"})).json()
        both = (await client.get("/api/graph/judgment/path", params={"node_id": i["rv"], "direction": "both"})).json()
        short = (await client.get("/api/graph/judgment/path", params={"node_id": i["step_rule"], "direction": "up", "depth": 2})).json()
        capped = (await client.get("/api/graph/judgment/path", params={"node_id": i["es1"], "direction": "down", "limit": 2})).json()
    assert [p["node_ids"] for p in up["paths"]] == [[i["step_rule"], i["rv"], i["dec1"], i["cand1"], i["c1"], i["mo1"], i["es1"]]]
    assert up["downstream_ids"] == []
    ends = sorted(p["node_ids"][-1] for p in down["paths"])
    assert ends == sorted([i["step_ai"], i["rd1"], i["val1"], i["step_rule"], i["step_oos"], i["cfg"]])
    assert all(p["node_ids"][:3] == [i["es1"], i["mo1"]] or p["node_ids"][:2] == [i["es1"], i["mo1"]] for p in down["paths"])
    assert {p["direction"] for p in both["paths"]} == {"up", "down"}
    assert sum(1 for p in both["paths"] if p["direction"] == "up") == 1
    assert sum(1 for p in both["paths"] if p["direction"] == "down") == 4
    assert [p["node_ids"] for p in short["paths"]] == [[i["step_rule"], i["rv"], i["dec1"]]]
    assert capped["truncated"] is True and len(capped["paths"]) == 2


async def test_node_detail_counts_and_source_link_permission(world):
    i = world["ids"]
    async with client_for(operator(world, can_read_source=True)) as client:
        step = (await client.get(f"/api/graph/judgment/nodes/{i['step_rule']}")).json()
        span = (await client.get(f"/api/graph/judgment/nodes/{i['es1']}")).json()
        rv = (await client.get(f"/api/graph/judgment/nodes/{i['rv']}")).json()
    assert step["upstream_count"] == 6 and step["downstream_count"] == 0
    assert [u["id"] for u in step["upstream"]] == [i["rv"]]
    assert step["refs"]["run_id"] == i["run2"] and step["layer"] == 5
    assert span["source_link"] == f"/api/requests/{i['req1']}/evidence/{i['es1']}"
    assert "source_text" not in str(span)
    # the viewer anchor (unit = span id, revision, source) is a reference, not source text
    assert span["refs"]["span_id"] == i["es1"] and span["refs"]["revision_id"] == "rev_1"
    assert span["refs"]["source"] == "att_1"
    assert rv["downstream_count"] == 4 and rv["refs"]["rule_id"] == "R-ROUTE-07"
    async with client_for(operator(world, can_read_source=False)) as client:
        hidden = (await client.get(f"/api/graph/judgment/nodes/{i['es1']}")).json()
    assert hidden["source_link"] is None and hidden["can_read_source"] is False
    assert hidden["refs"]["source"] == "att_1" and hidden["refs"]["span_id"] == i["es1"]


async def test_authorization_and_tenant_boundaries(world):
    i = world["ids"]
    async with client_for(Principal(world["tenant"], "u", ("org_a",), frozenset({"requester"}))) as client:
        assert (await client.get("/api/graph/judgment", params={"request_id": i["req1"]})).status_code == 403
        assert (await client.get(f"/api/graph/judgment/nodes/{i['rv']}")).status_code == 403
    async with client_for(Principal(world["other"], "o", (), frozenset({"operator"}))) as client:
        assert (await client.get(f"/api/graph/judgment/nodes/{i['rv']}")).status_code == 404
        assert (await client.get("/api/graph/judgment/path", params={"node_id": i["rv"]})).status_code == 404
        body = (await client.get("/api/graph/judgment", params={"rule_id": "R-ROUTE-07"})).json()
        assert body["nodes"] == []
        mine = (await client.get("/api/graph/judgment")).json()
        assert [n["id"] for n in mine["nodes"]] == [f"cor_other_{world['key']}"]
    # A reviewer of org_b cannot see org_a's request-bound nodes or paths through them.
    reviewer = Principal(world["tenant"], "rev", ("org_b",), frozenset({"reviewer"}))
    async with client_for(reviewer) as client:
        assert (await client.get("/api/graph/judgment", params={"request_id": i["req1"]})).status_code == 404
        graph = (await client.get("/api/graph/judgment", params={"rule_id": "R-ROUTE-07"})).json()
        ids = {n["id"] for n in graph["nodes"]}
        assert not ids & {i["c1"], i["mo1"], i["es1"]}
        assert {i["rv"], i["dec1"], i["step_rule"]} <= ids
        path = (await client.get("/api/graph/judgment/path", params={"node_id": i["step_rule"], "direction": "up"})).json()
        assert path["paths"] == []  # the only upward path crosses hidden nodes
        assert (await client.get(f"/api/graph/judgment/nodes/{i['mo1']}")).status_code == 404
