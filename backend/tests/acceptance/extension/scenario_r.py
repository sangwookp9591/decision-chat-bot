"""T38-R: additional stages for the re-run after FIX-S/O/C/E/SSE/R (live Decision AI, real Neo4j).

Run from backend/ (same X38_* env as scenario.py):
  .venv/bin/python -m tests.acceptance.extension.scenario_r <stage> [<stage> ...]
Stages: invariants trace_detail insufficient chain_lead evidence_layer
`scenario_r.main()` also exposes the scenario.py stages (seed corrections rules apply ... ) so one entry point drives a full run.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time

import httpx

from ildongi.db.driver import get_driver
from tests.acceptance.extension import scenario as S
from tests.acceptance.extension.lib import (
    API,
    PASSWORD,
    TENANT,
    Client,
    check,
    load_state,
    q,
    record,
    save_state,
    snapshot,
)

INV_TENANT = TENANT + "i"

BAD_URGENCY = {"rule_id": "R-URGENCY-91", "version": 1, "effect": "rule", "target": "urgency", "scope": {"all": []},
               "action": {"set": "판단 보류"}, "candidate_id": "cand_direct_db", "decision_id": "rdec_direct_db"}
BAD_FEAS = {"rule_id": "R-FEASIBILITY-92", "version": 1, "effect": "rule", "target": "feasibility", "scope": {"all": []},
            "action": {"set": "가능"}, "candidate_id": "cand_direct_db", "decision_id": "rdec_direct_db"}


class TClient(Client):
    """Same as lib.Client but for an explicit tenant."""
    def __init__(self, role: str, tenant: str):
        self.role = role
        self.http = httpx.Client(base_url=API, timeout=60)
        r = self.http.post("/api/auth/login", json={"email": f"{role}@{tenant}.dev", "password": PASSWORD})
        r.raise_for_status()
        self.csrf = self.http.cookies.get("ildongi_csrf") or ""


async def _qt(tenant: str, cypher: str, **params):
    driver = await get_driver()
    async with driver.session() as session:
        return await (await session.run(cypher, tenant=tenant, **params)).data()


def qt(tenant: str, cypher: str, **params) -> list[dict]:
    return asyncio.run(_qt(tenant, cypher, **params))


def code_of(resp) -> str:
    try:
        body = resp.json()
        detail = body.get("detail", body)
        return detail.get("code") if isinstance(detail, dict) else str(detail)[:80]
    except Exception:  # noqa: BLE001
        return resp.text[:80]


def stage_invariants() -> None:
    """F4: weakening rules are refused (422) at candidate save, at Config publish, at rule-version publish;
    a violating rule written straight into the DB is recorded as blocked_by_invariant when a request runs."""
    state = load_state()
    reviewer, admin, editor = Client("reviewer"), Client("rule_admin"), Client("policy_editor")
    cfg0 = admin.json("/api/policy/active")["version"]
    n_cand0 = q("MATCH (c:RuleCandidate {tenant_id:$tenant}) RETURN count(c) AS n")[0]["n"]
    snap0 = snapshot(["RuleVersion", "ConfigVersion", "RuleDecision"])
    attempts = []
    for field, value in [("feasibility", "가능"), ("urgency", "일반"), ("urgency", "판단 보류")]:
        for role_name, c in (("reviewer", reviewer), ("rule_admin", admin)):
            r = c.post("/api/learning/candidates", json={"field": field, "proposed_action": {"set": value}, "scope": {"all": []},
                                                         "rationale": f"T38-R 약화 규칙 저장 시험 {field}→{value}", "supporting_correction_ids": []})
            attempts.append({"role": role_name, "field": field, "value": value, "status": r.status_code, "code": code_of(r)})
    # Config-level publish with a weakening rule (policy_editor path is closed to rules entirely; rule_admin has no /policy/publish).
    active = admin.json("/api/policy/active")
    cfg_attempts = []
    for label, rule in (("urgency→판단 보류", BAD_URGENCY), ("feasibility→가능", BAD_FEAS)):
        probe = {**active["config"], "rules": [*active["config"]["rules"], rule]}
        pe = editor.post("/api/policy/publish", json={"config": probe, "reason": f"T38-R 약화 규칙 게시 시도 {label}", "expected_active_version": cfg0})
        va = editor.post("/api/policy/validate", json={"config": probe})
        cfg_attempts.append({"rule": label, "publish_status": pe.status_code, "publish_code": code_of(pe), "validate_status": va.status_code, "validate_body": va.text[:160]})
    n_cand1 = q("MATCH (c:RuleCandidate {tenant_id:$tenant}) RETURN count(c) AS n")[0]["n"]
    snap1 = snapshot(["RuleVersion", "ConfigVersion", "RuleDecision"])
    check("F4", "candidate save: feasibility→가능, urgency→일반, urgency→판단 보류 are 422 RULE_INVARIANT for reviewer and rule_admin; no candidate stored",
          all(a["status"] == 422 and a["code"] == "RULE_INVARIANT" for a in attempts) and n_cand0 == n_cand1,
          {"attempts": attempts, "candidates_before": n_cand0, "candidates_after": n_cand1})
    check("F4", "Config publish/validate with weakening rule is refused (422) and no Config version is created",
          all(a["publish_status"] == 422 for a in cfg_attempts) and snap0 == snap1 and admin.json("/api/policy/active")["version"] == cfg0,
          {"attempts": cfg_attempts, "active_config": cfg0})

    # --- second tenant: DB-injected violating records --------------------------------------------------
    adm = TClient("rule_admin", INV_TENANT)
    t = INV_TENANT
    cfg = adm.json("/api/policy/active")
    cfgv = cfg["version"]
    qt(t, "MATCH (n:Tenant {id:$tenant}) RETURN n")
    for rule in (BAD_URGENCY, BAD_FEAS):
        qt(t, "MERGE (r:RuleVersion {id:$id,tenant_id:$tenant}) SET r.rule_id=$rid,r.version=1,r.status='validated',r.body=$body,"
              "r.created_at=datetime()", id=f"{rule['rule_id']}@1", rid=rule["rule_id"],
           body=json.dumps({"schema": "rule-v1", **rule}, ensure_ascii=False))
    # publish path: validated-but-violating RuleVersion (injected) must be refused by the publish endpoint
    pub = []
    for rule in (BAD_URGENCY, BAD_FEAS):
        r = adm.post(f"/api/learning/rules/{rule['rule_id']}/versions/1/publish", json={"expected_active_config_version": cfgv, "reason": "T38-R DB 직접 삽입 위반 규칙 게시 시도"})
        pub.append({"rule": rule["rule_id"], "status": r.status_code, "code": code_of(r)})
    check("F4", "publish of a DB-injected violating rule version is refused (422 RULE_INVARIANT); Config unchanged",
          all(p["status"] == 422 and p["code"] == "RULE_INVARIANT" for p in pub) and adm.json("/api/policy/active")["version"] == cfgv,
          {"attempts": pub, "config": cfgv, "tenant": t})
    # apply path: put both violating rules straight into a new active ConfigVersion (bypassing every API)
    row = qt(t, "MATCH (c:ConfigVersion {tenant_id:$tenant,status:'active'}) RETURN c.config_json AS cfg,c.version AS v")[0]
    conf = json.loads(row["cfg"])
    conf["rules"] = [BAD_URGENCY, BAD_FEAS]
    newv = row["v"] + 1
    qt(t, "MATCH (p:Policy {tenant_id:$tenant}) SET p.next_version=$next,p.active_version=$v WITH p "
          "MATCH (old:ConfigVersion {tenant_id:$tenant,status:'active'}) SET old.status='superseded' "
          "CREATE (:ConfigVersion {id:$id,tenant_id:$tenant,version:$v,status:'active',created_by:'t38r:db-direct',reason:'T38-R direct DB violation',"
          "config_json:$cfg,diff_json:'{}',created_at:datetime()})", next=newv + 1, v=newv, id=f"cfg_{t}_{newv}", cfg=json.dumps(conf, ensure_ascii=False))
    for rule in (BAD_URGENCY, BAD_FEAS):
        qt(t, "MATCH (r:RuleVersion {tenant_id:$tenant,id:$id}) SET r.status='published'", id=f"{rule['rule_id']}@1")
    requester, reviewer_i = TClient("requester", t), TClient("reviewer", t)
    rid = S.submit(requester, "t38r-invariant-direct-db")
    end = time.time() + 300
    review = None
    while time.time() < end and not review:
        review = next((x for x in reviewer_i.json("/api/reviews?status=pending")["reviews"] if x["request_id"] == rid), None)
        time.sleep(3)
    assert review, "judgment with injected rules did not reach review"
    j = reviewer_i.json(f"/api/requests/{rid}/judgment")
    rows = qt(t, "MATCH (s:RunStep {tenant_id:$tenant,run_id:$run})-[a:APPLIED]->(rv:RuleVersion) RETURN s.id AS step,rv.id AS rule,a.outcome AS outcome,a.before AS before,a.after AS after ORDER BY rule", run=j["run_id"])
    raw = {r["question_id"]: r["value"] for r in qt(t, "MATCH (o:ModelOutput {tenant_id:$tenant,run_id:$run}) WHERE o.question_id IN ['urgency','feasibility'] RETURN o.question_id AS question_id,o.value AS value", run=j["run_id"])}
    step_detail = reviewer_i.json(f"/api/observe/steps/{rows[0]['step']}") if rows else {}
    api_fx = {(e["rule_version"], e["outcome"]) for e in j["rule_effects"]}
    ok = (len(rows) == 2 and all(r["outcome"] == "blocked_by_invariant" and r["before"] == r["after"] for r in rows)
          and j["classifications"]["urgency"] == raw["urgency"] and j["classifications"]["feasibility"] == raw["feasibility"]
          and api_fx == {(r["rule"], "blocked_by_invariant") for r in rows}
          and {(a["rule_version"], a["outcome"]) for a in step_detail.get("rule_applications", [])} == api_fx)
    check("F4", "DB-injected violating rules (urgency→판단 보류, feasibility→가능) are recorded blocked_by_invariant at apply time; classification = model output; APPLIED = Judgment API = Trace step API",
          ok, {"tenant": t, "request": rid, "run": j["run_id"], "config_version": newv, "applied": rows, "model_raw": raw,
               "final": {k: j["classifications"][k] for k in ("urgency", "feasibility")}, "api_rule_effects": j["rule_effects"],
               "trace_step_applications": step_detail.get("rule_applications")})
    state["invariants"] = {"tenant": t, "request": rid, "run": j["run_id"], "step": rows[0]["step"] if rows else None, "config": newv,
                           "rules": [f"{r['rule_id']}@1" for r in (BAD_URGENCY, BAD_FEAS)]}
    save_state(state)


def stage_trace_detail() -> None:
    """F3: Trace step detail API shows rule_id@version, outcome, before/after per application, equal to stored APPLIED rows."""
    state = load_state()
    reviewer = Client("reviewer")
    out = {}
    ok_all = True
    for label, rid in [("in_scope", state["post_requests"]["in_scope"][0]), ("out_of_scope", state["post_requests"]["out_of_scope"])]:
        rep = state["post_requests"]["report"][rid]
        step = rep["step_ids_in_applied"][0]
        api = reviewer.json(f"/api/observe/steps/{step}")
        db = q("MATCH (s:RunStep {tenant_id:$tenant,id:$step})-[a:APPLIED]->(rv:RuleVersion) RETURN rv.id AS rule,rv.rule_id AS rule_id,rv.version AS version,a.outcome AS outcome,a.before AS before,a.after AS after ORDER BY rule", step=step)
        got = sorted([(a["rule_version"], a["outcome"], json.dumps(a["before"], ensure_ascii=False), json.dumps(a["after"], ensure_ascii=False)) for a in api.get("rule_applications", [])])
        exp = sorted([(r["rule"], r["outcome"], r["before"], r["after"]) for r in db])
        flow = reviewer.json(f"/api/observe/runs/{rep['run_id']}/flow")
        node = next(n for n in flow["nodes"] if n["id"] == step)
        ok = got == exp and bool(exp) and api["config_version"] == state["pub_config"] and api.get("output_summary") is not None
        ok_all &= ok
        out[label] = {"request": rid, "run": rep["run_id"], "step": step, "api_rule_applications": api.get("rule_applications"),
                      "db_applied": db, "config_version": api["config_version"], "flow_node_kind": node.get("kind"), "equal": got == exp}
    check("F3", "Trace step detail API rule_applications (rule_id@version, outcome, before/after) == stored APPLIED rows (in-scope: used 불필요→필요; out-of-scope: out_of_scope)",
          ok_all, out)
    state["trace_detail_api"] = out
    save_state(state)


def stage_insufficient() -> None:
    """F5: approving a '자료 부족' candidate needs explicit acknowledgement (+reason ≥10 chars); label shown afterwards."""
    state = load_state()
    admin = Client("rule_admin")
    cid = state["cand_z"]
    before = snapshot(["RuleDecision", "RuleVersion", "ConfigVersion"])
    detail0 = admin.json(f"/api/learning/candidates/{cid}")
    r_no = admin.post(f"/api/learning/candidates/{cid}/decision", json={"action": "approve", "reason": "T38-R 자료 부족이지만 승인 시도"})
    r_short = admin.post(f"/api/learning/candidates/{cid}/decision", json={"action": "approve", "reason": "짧은 사유", "acknowledge_insufficient": True})
    after_fail = snapshot(["RuleDecision", "RuleVersion", "ConfigVersion"])
    check("F5", "자료 부족 candidate approval without acknowledgement → 422 INSUFFICIENT_ACK_REQUIRED; with acknowledgement but reason <10 chars → 422; nothing stored",
          detail0["status"] == "자료 부족" and r_no.status_code == 422 and code_of(r_no) == "INSUFFICIENT_ACK_REQUIRED"
          and r_short.status_code == 422 and code_of(r_short) == "INSUFFICIENT_ACK_REQUIRED" and before == after_fail,
          {"candidate": cid, "status": detail0["status"], "no_ack": [r_no.status_code, code_of(r_no)], "short_reason": [r_short.status_code, code_of(r_short)]})
    reason = "T38-R: 표본 2건뿐임을 확인하고 자료 부족 상태로 승인"
    ok_dec = admin.post(f"/api/learning/candidates/{cid}/decision", json={"action": "approve", "reason": reason, "acknowledge_insufficient": True})
    assert ok_dec.status_code == 200, ok_dec.text
    dec = ok_dec.json()
    detail1 = admin.json(f"/api/learning/candidates/{cid}")
    drow = q("MATCH (d:RuleDecision {tenant_id:$tenant,id:$id}) RETURN d.insufficient_approved AS ins,d.action AS action,d.reason AS reason", id=dec["decision_id"])[0]
    audit = S._audit("RuleCandidate", cid)
    check("F5", "acknowledged approval stored: decision.insufficient_approved=true, response/candidate detail show '자료 부족 상태로 승인됨', audit has reason",
          dec.get("insufficient_approved") is True and dec.get("insufficient_approval_label") == "자료 부족 상태로 승인됨"
          and detail1.get("insufficient_approved") is True and detail1.get("insufficient_approval_label") == "자료 부족 상태로 승인됨"
          and drow["ins"] is True and any(a["reason"] == reason for a in audit),
          {"decision": dec["decision_id"], "label": detail1.get("insufficient_approval_label"), "db": drow, "audit": [(a["action"], a["actor"], a["reason"]) for a in audit]})
    rule_id = "R-AI_NEED-02"
    v_no = admin.post(f"/api/learning/rules/{rule_id}/versions", json={"decision_id": dec["decision_id"], "reason": reason, "body": {}})
    v_ok = admin.post(f"/api/learning/rules/{rule_id}/versions", json={"decision_id": dec["decision_id"], "reason": reason, "body": {}, "acknowledge_insufficient": True})
    assert v_ok.status_code == 200, v_ok.text
    ver = v_ok.json()["version"]
    rd = admin.json(f"/api/learning/rules/{rule_id}")
    shown = next(v for v in rd["versions"] if v["version"] == ver)
    check("F5", "rule version from an insufficient approval: refused without acknowledgement (422), created with it; version list shows the label",
          v_no.status_code == 422 and code_of(v_no) == "INSUFFICIENT_ACK_REQUIRED" and v_ok.json().get("insufficient_approval_label") == "자료 부족 상태로 승인됨"
          and shown["insufficient_approved"] is True and shown["insufficient_approval_label"] == "자료 부족 상태로 승인됨",
          {"no_ack": [v_no.status_code, code_of(v_no)], "version": f"{rule_id}@{ver}", "label": shown["insufficient_approval_label"]})
    state["z_rule"] = {"rule_id": rule_id, "version": ver, "decision": dec["decision_id"], "reason": reason}
    save_state(state)


# --- lead_org chain ------------------------------------------------------------------------------------
MED_TEXT = ("임상시험 이상반응 보고서를 자동으로 분류하고 안전성 담당자에게 전달하는 기능이 필요합니다. 규제 보고 기한 확인이 필요합니다. ({label})")
ORGS = ("AI팀", "IT팀", "현업")


def submit_text_only(client: Client, label: str) -> str:
    r = client.post("/api/requests", data={"text": MED_TEXT.format(label=label)})
    r.raise_for_status()
    body = r.json()
    return body.get("request_id") or body["id"]


def submit_variant(client: Client, label: str) -> str:
    """Text-only request whose live judgment cites chat sentences for feasibility (and sometimes urgency)."""
    r = client.post("/api/requests", data={"text": f"사내 회의실 예약 현황을 부서별로 조회하고 예약 가능 시간을 확인하는 화면이 필요합니다. ({label})"})
    r.raise_for_status()
    body = r.json()
    return body.get("request_id") or body["id"]


def _chain(key: str, field: str, rule_id: str, tag: str, submit_fn, pick_target, require_spans: bool) -> None:
    """Correction → candidate → rule → shadow validation → publish → applied to a new request, for one classification field."""
    state = load_state()
    reviewer, admin, requester = Client("reviewer"), Client("rule_admin"), Client("requester")
    if f"{key}_probe" not in state:
        state[f"{key}_probe"] = [submit_fn(requester, f"{tag}-probe-{i}") for i in range(6)]
        save_state(state)
    probe = state[f"{key}_probe"]
    reviews = S.wait_reviews(reviewer, probe)
    orig = {}
    for rid, rv in reviews.items():
        d = reviewer.json(f"/api/reviews/{rv['id']}")
        orig[rid] = {"review_id": rv["id"], "value": d["final_classifications"][field]}
    groups: dict[str, list[str]] = {}
    for rid, o in orig.items():
        groups.setdefault(o["value"], []).append(rid)
    original, members = max(groups.items(), key=lambda kv: len(kv[1]))
    if len(members) < 4:
        record(tag.upper(), f"need >=4 requests with the same original {field}", "blocked", {"groups": {k: len(v) for k, v in groups.items()}, "orig": orig})
        return
    target = pick_target(original)
    for rid in members[:3]:
        S.decide(reviewer, orig[rid]["review_id"], "approve_with_changes", f"T38-R: {field} 수정(같은 방향)", {"classifications": {field: target}})
    S.decide(reviewer, orig[members[3]]["review_id"], "approve", f"T38-R: {field} 반례 — 수정 없이 승인")
    for rid in probe:
        if rid not in members[:4]:
            S.decide(reviewer, orig[rid]["review_id"], "approve", "T38-R: 그 외 요청 — 수정 없이 승인")
    cors = q("MATCH (c:Correction {tenant_id:$tenant,field:$f}) RETURN c.id AS id,c.request_id AS r,c.evidence_span_ids AS spans", f=field)
    spans = {c["r"]: list(c["spans"] or []) for c in cors}
    span_src = q("MATCH (e:EvidenceSpan {tenant_id:$tenant}) WHERE e.id IN $ids RETURN e.id AS id,e.source AS source", ids=sorted({x for v in spans.values() for x in v}))
    cite_ok = all(sorted(c["spans"] or []) == sorted(x["e"] for x in q(
        "MATCH (c:Correction {tenant_id:$tenant,id:$id})-[:CORRECTS]->(:ModelOutput)-[:CITES]->(e:EvidenceSpan) RETURN e.id AS e", id=c["id"])) for c in cors)
    check("X01", f"{field} corrections ({tag}, text-only requests): Correction.evidence_span_ids == CITES targets of the corrected ModelOutput"
          + ("; every correction has chat-sentence spans" if require_spans else "; the live model cited no span for this field, so no spans are expected"),
          len(cors) == 3 and cite_ok and (not require_spans or (all(spans[r] for r in members[:3]) and span_src and all(s["source"] == "chat" for s in span_src))),
          {"original": original, "target": target, "corrections": {c["id"]: {"request": c["r"], "spans": list(c["spans"] or [])} for c in cors}, "span_sources": span_src})
    reviewer.post("/api/learning/candidates/generate")
    cands = [c for c in reviewer.json(f"/api/learning/candidates?field={field}")["candidates"] if c["field"] == field]
    cand = max(cands, key=lambda c: c["support_count"])
    detail = reviewer.json(f"/api/learning/candidates/{cand['id']}")
    sup_db = sorted(e["id"] for e in q("MATCH (:RuleCandidate {tenant_id:$tenant,id:$id})-[:SUPPORTED_BY {role:'support'}]->(x) RETURN x.id AS id", id=cand["id"]))
    check("X02", f"{field} candidate: support == the 3 Correction IDs, status 제안, scope/uncertainty present, action = set {target}",
          sup_db == sorted(c["id"] for c in cors) and detail["status"] == "제안" and bool(detail["proposed_body"]["scope"]["all"]) and detail["uncertainty"]["support_count"] == 3
          and detail["proposed_body"]["action"] == {"set": target},
          {"candidate": cand["id"], "status": detail["status"], "action": detail["proposed_body"]["action"], "support": sup_db,
           "counter_count": detail["uncertainty"]["counter_count"], "scope": detail["proposed_body"]["scope"], "uncertainty": detail["uncertainty"]})
    cfg = admin.json("/api/policy/active")["version"]
    d = admin.post(f"/api/learning/candidates/{cand['id']}/decision", json={"action": "approve", "reason": f"T38-R: {field} 후보 승인"})
    assert d.status_code == 200, d.text
    v = admin.post(f"/api/learning/rules/{rule_id}/versions", json={"decision_id": d.json()["decision_id"], "reason": "T38-R: 버전 생성", "body": {}})
    assert v.status_code == 200, v.text
    ver = v.json()["version"]
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 60))
    val = admin.post(f"/api/learning/rules/{rule_id}/versions/{ver}/validate", json={"from": "2026-01-01T00:00:00Z", "to": now})
    assert val.status_code == 200, val.text
    vv = val.json()
    admin.post(f"/api/learning/rules/{rule_id}/versions/{ver}/mark-validated", json={"validation_id": vv["id"], "reason": "T38-R: 부작용 0건"}).raise_for_status()
    pub = admin.post(f"/api/learning/rules/{rule_id}/versions/{ver}/publish", json={"expected_active_config_version": cfg, "reason": "T38-R: 게시"})
    assert pub.status_code == 200, pub.text
    state[key] = {"rule_id": rule_id, "field": field, "version": ver, "ref": f"{rule_id}@{ver}", "candidate": cand["id"], "decision": d.json()["decision_id"],
                  "config": pub.json()["config_version"], "validation": vv["id"], "validation_run": vv.get("run_id"),
                  "corrections": [c["id"] for c in cors], "span_ids": sorted({x for s_ in spans.values() for x in s_}),
                  "original": original, "target": target, "probe_originals": orig}
    check("X04", f"{field} rule validated by shadow: side_effects=0, completed, sample counts recorded, shadow Run id != ValidationRun id",
          vv["side_effects"] == 0 and vv["status"] == "completed" and vv["run_id"] != vv["id"] and vv["run_id"].startswith("run_shadow_"),
          {k: vv[k] for k in ("id", "run_id", "sample_count", "labeled_count", "changed_count", "side_effects", "status", "calls")})
    rid = submit_fn(requester, f"{tag}-after-publish")
    S.wait_reviews(reviewer, [rid])
    j = reviewer.json(f"/api/requests/{rid}/judgment")
    rows = q("MATCH (s:RunStep {tenant_id:$tenant,run_id:$run})-[a:APPLIED]->(rv:RuleVersion) RETURN s.id AS step,rv.id AS rule,a.outcome AS outcome,a.before AS b,a.after AS a ORDER BY rule", run=j["run_id"])
    raw = q("MATCH (o:ModelOutput {tenant_id:$tenant,run_id:$run,question_id:$f}) RETURN o.value AS v", run=j["run_id"], f=field)[0]["v"]
    state[key]["post_request"] = {"request_id": rid, "run_id": j["run_id"], "applied": rows, "final": j["classifications"][field], "model_raw": raw}
    mine = next((r_ for r_ in rows if r_["rule"] == state[key]["ref"]), None)
    others = {(r_["rule"], r_["outcome"]) for r_ in rows}
    check("X05", f"{field} rule applied to a new text-only request: APPLIED used (before→after) == Judgment API rule_effects; value changed from the model output; every active rule evaluated",
          bool(mine) and mine["outcome"] == "used" and json.loads(mine["b"]) == raw != json.loads(mine["a"]) == target == j["classifications"][field]
          and others == {(e["rule_version"], e["outcome"]) for e in j["rule_effects"]} and len(rows) == len(j["rule_effects"]) >= 2,
          {"request": rid, "run": j["run_id"], "applied": rows, "api": j["rule_effects"], "model_raw": raw, "final": j["classifications"][field]})
    save_state(state)


def stage_chain_lead() -> None:
    """lead_org correction path (text-only medical requests): the live model cites no span for lead_org."""
    _chain("rule_lead", "lead_org", "R-LEAD_ORG-01", "lead", submit_text_only, lambda o: "IT팀" if o == "AI팀" else ("현업" if o == "IT팀" else "IT팀"), False)


def stage_chain_evidence() -> None:
    """Evidence-backed chain (feasibility 정보 부족 → 조건부 가능, a stricter allowed value): corrections on cited outputs → rule → applied."""
    _chain("rule2", "feasibility", "R-FEASIBILITY-01", "feas", submit_variant, lambda o: "조건부 가능", True)


def stage_evidence_layer() -> None:
    """Evidence layer: text-only request's chat EvidenceSpans are real nodes in the judgment map and trace back from the business step."""
    state = load_state()
    admin = Client("rule_admin")
    r2 = state["rule2"]
    post = r2["post_request"]
    g = admin.json(f"/api/graph/judgment?request_id={post['request_id']}")
    span_nodes = [n for n in g["nodes"] if n["kind"] == "EvidenceSpan"]
    db_spans = q("MATCH (e:EvidenceSpan {tenant_id:$tenant,request_id:$r}) RETURN e.id AS id,e.source AS source,e.source_text AS text", r=post["request_id"])
    attach = q("MATCH (a:Attachment {tenant_id:$tenant,request_id:$r}) RETURN count(a) AS n", r=post["request_id"])[0]["n"]
    layer1 = next((layer for layer in g["layers"] if layer["layer"] == 1), {})
    cited = {x["e"] for x in q("MATCH (o:ModelOutput {tenant_id:$tenant,run_id:$run})-[:CITES]->(e:EvidenceSpan) RETURN DISTINCT e.id AS e", run=post["run_id"])}
    api_ids = {n["id"] for n in span_nodes}
    check("EVID", "text-only request (0 attachments): judgment map evidence layer shows the chat EvidenceSpan nodes cited by the run (API span node ids ⊇ Cypher CITES targets of the run; extra nodes = spans of the rule's supporting corrections)",
          attach == 0 and bool(cited) and cited <= api_ids <= ({s_["id"] for s_ in db_spans} | set(r2["span_ids"])) and all(s_["source"] == "chat" for s_ in db_spans)
          and layer1.get("count", 0) >= len(span_nodes),
          {"request": post["request_id"], "attachments": attach, "stored_spans": len(db_spans), "cited_by_run": sorted(cited), "api_span_nodes": sorted(api_ids), "support_correction_spans": r2["span_ids"],
           "layer1": layer1, "sources": sorted({s_["source"] for s_ in db_spans})})
    step = next(r_["step"] for r_ in post.get("applied_steps", [])) if post.get("applied_steps") else q(
        "MATCH (s:RunStep {tenant_id:$tenant,run_id:$run})-[:APPLIED {outcome:'used'}]->(:RuleVersion {id:$ref}) RETURN s.id AS id", run=post["run_id"], ref=r2["ref"])[0]["id"]
    chain = q("MATCH (s:RunStep {tenant_id:$tenant,id:$step})-[:APPLIED {outcome:'used'}]->(rv:RuleVersion {id:$ref})-[:DERIVED_FROM]->(d:RuleDecision)-[:DECIDES]->(c:RuleCandidate)"
              "-[:SUPPORTED_BY {role:'support'}]->(cor:Correction)-[:CORRECTS]->(o:ModelOutput)-[:CITES]->(e:EvidenceSpan) "
              "RETURN s.id AS step,rv.id AS rv,d.id AS d,c.id AS c,cor.id AS cor,o.id AS o,e.id AS e,e.source AS source", step=step, ref=r2["ref"])
    up = admin.json(f"/api/graph/judgment/path?node_id={step}&direction=up&depth=8&limit=200")
    api_paths = {tuple(sorted(p["node_ids"])) for p in up["paths"]}
    ok = bool(chain) and all(c_["source"] == "chat" and tuple(sorted([c_["step"], c_["rv"], c_["d"], c_["c"], c_["cor"], c_["o"], c_["e"]])) in api_paths for c_ in chain)
    check("EVID", "business step → rule version → decision → candidate → correction → model output → chat EvidenceSpan: Cypher chain == /graph/judgment/path (UI-independent)",
          ok, {"step": step, "chains": chain, "api_paths": len(up["paths"])})
    state["trace"] = {"step": step, "span": chain[0]["e"] if chain else None, "chain": {k: v for k, v in (chain[0] if chain else {}).items() if k != "source"}}
    state["evidence_layer"] = {"request": post["request_id"], "cited": sorted(cited), "api_span_nodes": sorted(api_ids)}
    save_state(state)


STAGES = {"invariants": stage_invariants, "trace_detail": stage_trace_detail, "insufficient": stage_insufficient,
          "chain_lead": stage_chain_lead, "chain_evidence": stage_chain_evidence, "evidence_layer": stage_evidence_layer}


def main() -> None:
    for name in sys.argv[1:]:
        (STAGES.get(name) or S.STAGES[name])()




def stage_lead_retest() -> None:
    """Retest of the lead_org X01 span check with the correct expectation (Decision AI cites no span for lead_org; the first check wrongly required spans)."""
    state = load_state()
    r = state["rule_lead"]
    cors = q("MATCH (c:Correction {tenant_id:$tenant,field:'lead_org'}) RETURN c.id AS id,c.request_id AS r,c.evidence_span_ids AS spans")
    cites = {c["id"]: [x["e"] for x in q("MATCH (c:Correction {tenant_id:$tenant,id:$id})-[:CORRECTS]->(:ModelOutput)-[:CITES]->(e:EvidenceSpan) RETURN e.id AS e", id=c["id"])] for c in cors}
    check("X01", "(retest) lead_org corrections: Correction.evidence_span_ids == CITES targets of the corrected ModelOutput (both empty: Decision AI cites no span for lead_org)",
          len(cors) == 3 and all(sorted(c["spans"] or []) == sorted(cites[c["id"]]) for c in cors) and sorted(c["id"] for c in cors) == sorted(r["corrections"]),
          {"corrections": {c["id"]: {"request": c["r"], "spans": list(c["spans"] or []), "cites": cites[c["id"]]} for c in cors}})


STAGES["lead_retest"] = stage_lead_retest


def stage_insufficient_ui_setup() -> None:
    """A human-proposed candidate without supporting corrections is stored as '자료 부족'; the browser test approves it with the acknowledgement."""
    state = load_state()
    reviewer = Client("reviewer")
    r = reviewer.post("/api/learning/candidates", json={"field": "ai_need", "proposed_action": {"set": "혼합"}, "scope": {"all": [{"field": "lead_org", "op": "eq", "value": "현업"}]},
                                                       "rationale": "T38-R: 화면에서 자료 부족 확인 흐름을 시험하기 위한 사람 제안(지지 수정 0건)", "supporting_correction_ids": []})
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    state["cand_ins_ui"] = cid
    save_state(state)
    record("F5", "human candidate without supporting corrections is stored as '자료 부족' (UI approval target)", "pass" if r.json()["status"] == "자료 부족" else "fail",
           {"candidate": cid, "status": r.json()["status"]})


def stage_insufficient_ui_verify() -> None:
    """After the browser approved cand_ins_ui with the checkbox: DB == API == label."""
    state = load_state()
    admin = Client("rule_admin")
    cid = state["cand_ins_ui"]
    detail = admin.json(f"/api/learning/candidates/{cid}")
    d = q("MATCH (d:RuleDecision {tenant_id:$tenant})-[:DECIDES]->(:RuleCandidate {id:$cid}) RETURN d.id AS id,d.insufficient_approved AS ins,d.reason AS reason,d.decided_by AS by", cid=cid)
    v = q("MATCH (r:RuleVersion {tenant_id:$tenant})-[:DERIVED_FROM]->(d:RuleDecision {id:$d}) RETURN r.id AS id,r.status AS status", d=d[0]["id"] if d else "")
    check("F5", "browser approval of the 자료 부족 candidate stored: decision.insufficient_approved=true with a ≥10-char reason, rule version (validating) created, API shows the label",
          bool(d) and d[0]["ins"] is True and len(d[0]["reason"]) >= 10 and bool(v) and detail.get("insufficient_approval_label") == "자료 부족 상태로 승인됨",
          {"candidate": cid, "decision": d, "versions": v, "label": detail.get("insufficient_approval_label"), "status": detail["status"]})


STAGES["insufficient_ui_setup"] = stage_insufficient_ui_setup
STAGES["insufficient_ui_verify"] = stage_insufficient_ui_verify


def stage_diff_new_traffic() -> None:
    """X08: snapshot.pre (before restart) vs snapshot.post2 (after restart AND one new request): graph/DB changes are limited to additions made by that request."""
    from tests.acceptance.extension.lib import OUT
    a = json.loads((OUT / "snap.pre.json").read_text())
    b = json.loads((OUT / "snap.post2.json").read_text())
    new_req = load_state()["post_restart"]["request"]
    new_runs = {r["run"] for r in b["db"]["applied"]} - {r["run"] for r in a["db"]["applied"]}
    removed, added_unexplained = {}, {}
    for name, g in a["api"]["graph"].items():
        now = b["api"]["graph"][name]
        removed[name] = sorted(set(g["nodes"]) - set(now["nodes"]))
        added = sorted(set(now["nodes"]) - set(g["nodes"]))
        owner = {r["id"] for r in q("MATCH (n {tenant_id:$tenant}) WHERE n.id IN $ids AND (n.request_id=$req OR n.run_id IN $runs OR n.id=$req) RETURN n.id AS id", ids=added, req=new_req, runs=sorted(new_runs))}
        added_unexplained[name] = [i for i in added if i not in owner and not i.startswith("group:")]
    unchanged_db = {k: a["db"][k] == b["db"][k] for k in ("corrections", "candidates", "validations", "configs")}
    keep = lambda rows: [{k: r[k] for k in ("id", "rule_id", "version", "status", "body", "configs")} for r in rows]  # application counts legitimately grow with new traffic
    unchanged_db["rule_versions(id,status,body,configs)"] = keep(a["db"]["rule_versions"]) == keep(b["db"]["rule_versions"])
    grew = {r["id"]: r["applications"] - next(x["applications"] for x in a["db"]["rule_versions"] if x["id"] == r["id"]) for r in b["db"]["rule_versions"]}
    check("X08", "after restart + one new request, stored learning state is unchanged (corrections, candidates, rule versions, validations, Configs equal) and graph differences are only the new request's own nodes (none removed)",
          all(unchanged_db.values()) and not any(removed.values()) and not any(added_unexplained.values()),
          {"unchanged_db": unchanged_db, "removed": removed, "added_not_owned_by_new_request": added_unexplained, "new_request": new_req, "application_count_growth_per_rule_version": grew})


STAGES["diff_new_traffic"] = stage_diff_new_traffic


def stage_f6() -> None:
    """F6: shadow Run id is separate from the ValidationRun id (DB relation, no Run under a validation id, journal rows keyed by the shadow run id)."""
    admin = Client("rule_admin")
    rows = q("MATCH (v:ValidationRun {tenant_id:$tenant}) OPTIONAL MATCH (v)-[:HAS_SHADOW_RUN]->(r:Run {tenant_id:$tenant}) "
             "RETURN v.id AS validation,v.run_kind AS vkind,v.rule_version AS rule,r.id AS run,r.run_kind AS rkind ORDER BY v.created_at")
    clash = q("MATCH (r:Run {tenant_id:$tenant}) MATCH (v:ValidationRun {tenant_id:$tenant,id:r.id}) RETURN count(r) AS n")[0]["n"]
    journal = [json.loads(line) for line in (__import__("pathlib").Path(os.environ["DATA_DIR"]) / "journal" / "current.jsonl").read_text().splitlines() if "shadow_validation" in line]
    by_run = {j["run_id"]: j for j in journal if j.get("tenant_id") == TENANT}
    api_ok = all(admin.json(f"/api/learning/validations/{r['validation']}")["id"] == r["validation"] for r in rows)
    check("F6", "every ValidationRun has its own shadow Run (id run_shadow_*, run_kind=shadow, != ValidationRun id); no Run shares a ValidationRun id; journal shadow rows are keyed by the shadow run id and tagged run_kind=shadow",
          bool(rows) and all(r["run"] and r["run"] != r["validation"] and r["run"].startswith("run_shadow_") and r["rkind"] == "shadow" and r["vkind"] == "shadow" for r in rows)
          and clash == 0 and all(r["run"] in by_run and by_run[r["run"]].get("run_kind") == "shadow" and r["validation"] not in by_run for r in rows) and api_ok,
          {"validations": [{"validation": r["validation"], "shadow_run": r["run"], "rule": r["rule"]} for r in rows], "id_clashes": clash,
           "journal_rows_for_tenant": len(by_run)})
    v = rows[0]["validation"]
    d = admin.json(f"/api/learning/validations/{v}")
    dbrow = q("MATCH (v:ValidationRun {tenant_id:$tenant,id:$id}) RETURN properties(v) AS p", id=v)[0]["p"]
    keys = ["sample_count", "labeled_count", "changed_count", "side_effects", "status", "run_kind", "base_config_version", "candidate_config_version", "max_calls", "calls",
            "human_correction_needed_base", "human_correction_needed_candidate"]
    check("X04", "ValidationRun (POST result == GET API == DB): conditions, sample counts, side_effects=0, run_kind=shadow",
          all(d.get(k) == dbrow.get(k) for k in keys) and d["side_effects"] == 0 and d["run_kind"] == "shadow" and rows[0]["rkind"] == "shadow",
          {"retest_of_first_attempt": "first attempt looked up Run by ValidationRun id (stale after the F6 id split); retested via HAS_SHADOW_RUN", "validation": v, "shadow_run": rows[0]["run"],
           "api_equals_db": {k: d.get(k) == dbrow.get(k) for k in keys}})


STAGES["f6"] = stage_f6


def stage_f7() -> None:
    """F7: Flow/step API serialise Neo4j DateTime as ISO strings (previously internal `_DateTime__date…` structures)."""
    import re
    state = load_state()
    reviewer = Client("reviewer")
    pr = state["post_requests"]
    rep = pr["report"][pr["in_scope"][0]]
    flow = reviewer.json(f"/api/observe/runs/{rep['run_id']}/flow")
    step = reviewer.json(f"/api/observe/steps/{rep['step_ids_in_applied'][0]}")
    iso = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
    bad = [(n["id"], k, n.get(k)) for n in flow["nodes"] for k in ("started_at", "ended_at") if n.get(k) is not None and not (isinstance(n[k], str) and iso.match(n[k]))]
    raw = json.dumps([flow, step], ensure_ascii=False)
    check("F7", "Flow nodes and step detail serialise started_at/ended_at as ISO-8601 strings (no `_DateTime__` internals)",
          not bad and "_DateTime__" not in raw and all(isinstance(n.get("started_at"), str) for n in flow["nodes"]) and isinstance(step.get("started_at"), str),
          {"run": rep["run_id"], "nodes": len(flow["nodes"]), "sample": [(n["id"], n.get("started_at"), n.get("ended_at")) for n in flow["nodes"][:2]], "bad": bad})


STAGES["f7"] = stage_f7


if __name__ == "__main__":
    main()
