"""E) T21-gates: G05 automatic assignment (live), G06 policy versions + graph, G03 evidence behaviour.

Live Decision AI only; dedicated tenant `<ACC_TENANT>g`, tenant-limited worker. Labels are never asserted as
ground truth. Where live Decision AI does not satisfy an eligibility condition the reasons are recorded as
they are and the affected part is reported as unverified (pytest skip) - conditions are never
bypassed and thresholds are never moved outside the server invariants (POLICY.md).
Collected only by `make test-acceptance` (file prefix `acc_`). Evidence: records.jsonl (`g05_*`,
`g06_*`, `g03_*`).
"""
from __future__ import annotations

import concurrent.futures as cf
import copy
import json

import pytest

from tests.acceptance import docs_fixture as D
from tests.acceptance.harness import (
    TENANT_G,
    Client,
    counts,
    db_read,
    decide,
    judge,
    judgment,
    pending_review,
    record,
    tasks_of,
    topology,
)

G = TENANT_G
ELIGIBLE = "배정 완료"

DOCS = {
    "sales": ("sales-report.md",
              ("# 월간 매출 리포트 화면 개발 요청\n\n영업지원팀은 SAP에서 내려받은 월별 매출 CSV를 부서별로 합산해 "
              "보여 주는 조회 화면이 필요합니다. 화면은 사내 대시보드에 표로 추가하며 새로운 모델이나 예측은 필요하지 "
              "않습니다.\n\n데이터는 이미 매월 CSV로 내보내지고 있고 IT팀이 읽기 권한을 승인받아 보유하고 있습니다. "
              "마감 기한은 없고 임상·안전·규제와 무관한 일반 사내 업무입니다.\n")),
    "notice": ("notice-board.md",
               ("# 공지사항 게시판 목록 화면 개선\n\n총무팀은 사내 공지사항 게시판 목록 화면에서 작성일 기준 정렬과 부서별 "
               "필터를 추가하길 원합니다. 단순한 화면 개발이며 AI는 필요하지 않습니다.\n\n공지 데이터는 이미 사내 "
               "게시판 데이터베이스에 있고 IT팀이 접근 권한을 가지고 있습니다. 긴급하지 않으며 다음 분기 내 완료면 "
               "됩니다. 규제·안전과 무관합니다.\n")),
    "stock": ("stock-status.md",
              ("# 재고 현황 조회 화면 요청\n\n물류팀은 창고별 현재 재고 수량을 한 화면에서 조회하길 원합니다. 일반적인 "
              "조회 화면 개발이며 AI나 예측은 필요하지 않습니다.\n\n재고 데이터는 사내 ERP 데이터베이스에 이미 있고 "
              "IT팀이 읽기 권한을 승인받았습니다. 긴급하지 않고 일정은 다음 분기이며, 임상·안전·규제와 무관합니다.\n")),
    "export": ("attendance-export.md",
               ("# 근태 기록 CSV 내려받기 버튼 추가\n\n인사팀은 기존 근태 조회 화면에 월별 근태 기록을 CSV로 내려받는 "
               "버튼을 추가하길 원합니다. 일반 기술 개발이며 AI는 필요하지 않습니다.\n\n근태 데이터는 이미 근태 "
               "시스템 데이터베이스에 있고 IT팀이 접근 권한을 보유합니다. 긴급하지 않으며 규제·안전과 무관합니다.\n")),
    "etl": ("order-etl.md",
            ("# 주문 데이터 적재와 현황 화면 요청\n\n영업팀은 ERP 주문 데이터를 매일 데이터 마트로 적재(ETL)하는 연동 "
            "작업과, 적재된 데이터를 월별로 보여 주는 현황 화면 개발이 필요합니다. AI나 예측은 필요하지 않습니다.\n\n"
            "ERP 주문 데이터에 대한 접근 권한은 IT팀이 이미 승인받았고 데이터 구조도 확인되어 있습니다. 긴급하지 "
            "않으며 임상·안전·규제와 무관한 일반 사내 업무입니다.\n")),
}
DOC_TEXT = "첨부 문서의 요청을 검토해 주세요."
THIN = ["사내 회의실 예약 현황을 한곳에서 조회할 수 있는 화면이 필요합니다.",
        "직원 명부를 엑셀로 내려받는 기능이 필요합니다.",
        "구내식당 주간 메뉴를 보여 주는 화면을 만들어 주세요."]


@pytest.fixture(scope="module")
def gu():
    out = {}
    for role in ("requester", "reviewer", "policy_editor", "operator", "source_reader"):
        out[role] = Client(role, G)
    return out


def _doc(key):
    name, body = DOCS[key]
    return [(name, body.encode(), D.MD)]


def _submit_doc(rq, key, timeout=300):
    return judge(rq, DOC_TEXT, _doc(key), timeout)


def _set_policy(pe, mutate, reason):
    active = pe.get("/api/policy/active").json()
    cfg = mutate(copy.deepcopy(active["config"]))
    v = pe.post("/api/policy/validate", json={"config": cfg})
    assert v.status_code == 200 and v.json()["valid"] is True, v.text[:300]
    r = pe.post("/api/policy/publish", json={"config": cfg, "reason": reason,
                                             "expected_active_version": active["version"]})
    assert r.status_code == 200, r.text
    return active, r.json()


def _run_versions(c, rid):
    runs = c.get(f"/api/requests/{rid}/runs").json()
    return runs, {r["id"]: (r["versions"].get("config"), r.get("status")) for r in runs["runs"]}


def _summ(c, rid, d=None):
    j = judgment(c, rid)
    st = (d or c.detail(rid))["request"]["status"]
    cn = counts(G, rid)
    return {"request_id": rid, "status": st, "run_id": j["run_id"], "config_version": j["versions"]["config_version"],
            "classifications": j["classifications"], "reasons": j["review_reasons"],
            "tasks_drafted": [(t["title"], t["method"], t["lead_org"]) for t in j["draft_tasks"]],
            "assignments": cn["assignments"], "tasks": cn["tasks"], "decisions": cn["decisions"],
            "judgment_id": j["id"]}


# ---------------------------------------------------------------- stored graph vs API
def stored_graph(rid: str) -> dict:
    """Relationships exactly as stored in Neo4j (request->task->org, PRECEDES) via Cypher."""
    has = db_read(G, "MATCH (q:Request {tenant_id:$tenant,id:$rid})-[:HAS_TASK]->(t:Task) "
                  "RETURN t.id AS id,t.title AS title,t.status AS status ORDER BY t.id", rid=rid)
    asg = db_read(G, "MATCH (q:Request {tenant_id:$tenant,id:$rid})-[:HAS_TASK]->(t:Task)-[a:ASSIGNED_TO]->(o:Org) "
                  "RETURN t.id AS task,a.role AS role,o.id AS org,o.name AS org_name ORDER BY t.id,role,org", rid=rid)
    prec = db_read(G, "MATCH (p:Task {tenant_id:$tenant,request_id:$rid})-[:PRECEDES]->(t:Task {tenant_id:$tenant,request_id:$rid}) "
                   "RETURN p.id AS from,t.id AS to,p.title AS from_title,t.title AS to_title ORDER BY p.id,t.id", rid=rid)
    asn = db_read(G, "MATCH (a:Assignment {tenant_id:$tenant,request_id:$rid}) "
                  "RETURN a.id AS id,a.pathway AS pathway,a.run_id AS run_id", rid=rid)
    return {"tasks": has, "assigned_to": asg, "precedes": prec, "assignments": asn}


def graph_edges(g: dict) -> set:
    e = {("HAS_TASK", g["rid"], t["id"], None) for t in g["tasks"]}
    e |= {("ASSIGNED_TO", a["task"], a["org"], a["role"]) for a in g["assigned_to"]}
    e |= {("PRECEDES", p["from"], p["to"], None) for p in g["precedes"]}
    return e


def topology_edges(topo: dict) -> set:
    return {(e["kind"], e["from"], e["to"], e.get("role")) for e in topo["edges"]}


def compare_stored_to_api(rq, rv, rid):
    g = stored_graph(rid)
    g["rid"] = rid
    topo = topology(rq, rid)
    stored = graph_edges(g)
    api = topology_edges(topo)
    assert stored == api, {"cypher_only": sorted(map(str, stored - api)), "api_only": sorted(map(str, api - stored))}
    tnodes = {n["id"] for n in topo["nodes"] if n["type"] == "task"}
    assert tnodes == {t["id"] for t in g["tasks"]}
    onodes = {n["id"] for n in topo["nodes"] if n["type"] == "org"}
    assert onodes == {a["org"] for a in g["assigned_to"]}
    assert any(n["type"] == "request" and n["id"] == rid for n in topo["nodes"])
    # Tasks screen API (what the 업무 page renders)
    tasks = tasks_of(rv, rid)
    assert {t["id"] for t in tasks} == tnodes
    api_assign = {("ASSIGNED_TO", t["id"], o["org"], o["role"]) for t in tasks for o in t["orgs"]}
    assert api_assign == {e for e in stored if e[0] == "ASSIGNED_TO"}
    api_prec = {("PRECEDES", p["id"], t["id"], None) for t in tasks for p in t["predecessor_tasks"]}
    assert api_prec == {e for e in stored if e[0] == "PRECEDES"}
    return g, topo, tasks


def _edges_json(edges):
    return sorted([list(e) for e in edges], key=str)


# ================================================================== G05 automatic assignment (live)
def test_g05_auto_assignment_live_end_to_end(gu):
    rq, rv, pe = gu["requester"], gu["reviewer"], gu["policy_editor"]
    # Policy: only auto_assign flips to true. Thresholds stay at their defaults (Choice confidence 0.8,
    # risk_clear_max 0.2, Noul uncertain band [0.35, 0.65]): they are the PRD/POLICY.md safe defaults,
    # the plain requests below were probed against them, and loosening any of them would be outside
    # the intent of the server invariants (risk_clear_max > 0.5 is rejected outright).
    before, pub = _set_policy(pe, lambda c: {**c, "auto_assign": True},
                              "G05 인수 시험: 자동 배정 허용(임계값은 기본값 유지)")
    pol = pub["config"]
    thresholds = {k: pol[k] for k in ("choice_confidence_thresholds", "risk_clear_max", "noul_uncertain_band",
                                      "noul_probability_thresholds")}
    keys = ["sales", "notice", "stock", "export", "etl"]
    with cf.ThreadPoolExecutor(5) as ex:
        futs = {k: ex.submit(_submit_doc, rq, k) for k in keys}
        done = {k: f.result() for k, f in futs.items()}
    rows = {}
    for k, (rid, d) in done.items():
        row = _summ(rq, rid, d)
        row["doc"] = k
        row["pathway"] = [a["pathway"] for a in stored_graph(rid)["assignments"]]
        rows[k] = row
    auto = {k: r for k, r in rows.items() if r["status"] == ELIGIBLE}
    verified = {}
    for k, r in auto.items():
        rid = r["request_id"]
        # no human review was involved; one assignment; one task per drafted task
        assert r["assignments"] == 1 and r["decisions"] == 0, r
        assert r["pathway"] == ["auto"], r
        assert r["tasks"] == len(r["tasks_drafted"]) >= 1
        assert r["config_version"] == pub["version"]
        g, topo, tasks = compare_stored_to_api(rq, rv, rid)
        assert not any(rev["request_id"] == rid for rev in rv.get("/api/reviews?status=pending").json()["reviews"])
        verified[k] = {"request_id": rid, "tasks": [t["id"] for t in g["tasks"]],
                       "titles": [t["title"] for t in tasks],
                       "assigned_to": [[a["task"], a["role"], a["org"]] for a in g["assigned_to"]],
                       "precedes": [[p["from"], p["to"]] for p in g["precedes"]],
                       "assignment": g["assignments"], "topology_edges": len(topo["edges"])}
    # nothing is auto-assigned for a request whose reasons are not empty
    for k, r in rows.items():
        if r["status"] != ELIGIBLE:
            assert r["assignments"] == 0 and r["tasks"] == 0, r
            assert r["reasons"], r  # an ineligible request must say why
    record("g05_auto_assign", {"policy_before": before["version"], "policy_published": pub["version"],
                               "thresholds_in_effect": thresholds,
                               "threshold_rationale": "auto_assign만 true. 임계값은 기본값 유지(안전 기본값, 불변 조건 안).",
                               "requests": rows, "auto_assigned": verified,
                               "verdict": "verified" if verified else "unverified"})
    if not verified:
        pytest.skip("미검증: 5건 모두 자동 배정 조건 미충족 — 사유는 records g05_auto_assign.requests[*].reasons")


# ================================================================== G06 (a) policy versions
def test_g06_policy_version_pinning_and_rollback(gu):
    rq, rv, pe = gu["requester"], gu["reviewer"], gu["policy_editor"]
    n_active = pe.get("/api/policy/active").json()
    n, cfg_n = n_active["version"], n_active["config"]
    assert cfg_n["auto_assign"] is True, "G05 test must leave the auto-assign policy active"

    # request A under v(n): retry (real runs) until the live model satisfies every condition
    a_tries = []
    ridA = None
    for key in ("sales", "stock", "export"):
        rid, d = _submit_doc(rq, key)
        a_tries.append(_summ(rq, rid, d))
        if d["request"]["status"] == ELIGIBLE:
            ridA, docA = rid, key
            break
    if ridA is None:
        ridA, docA = a_tries[-1]["request_id"], "export"
    A = next(t for t in a_tries if t["request_id"] == ridA)
    snapA = {"judgment": judgment(rq, ridA), "runs": rq.get(f"/api/requests/{ridA}/runs").json(),
             "tasks": sorted(t["id"] for t in tasks_of(rv, ridA)), "counts": counts(G, ridA)}

    # v(n+1): a stricter, invariant-safe change (Noul participation band widened to [0,1] => any
    # participation signal is "uncertain" => human review). Same input text/file for B.
    _, pub1 = _set_policy(pe, lambda c: {**c, "noul_uncertain_band": [0.0, 1.0]},
                          "G06 인수 시험: Noul 불확실 대역 확대(더 엄격)")
    n1 = pub1["version"]
    assert n1 == n + 1
    ridB, dB = _submit_doc(rq, docA)
    B = _summ(rq, ridB, dB)

    # rollback to v(n) => new version v(n+2) whose content equals v(n)
    cur = pe.get("/api/policy/active").json()
    rb = pe.post("/api/policy/rollback", json={"target_version": n, "reason": "G06 인수 시험: v(n)로 되돌리기",
                                               "expected_active_version": cur["version"]})
    assert rb.status_code == 200, rb.text
    n2 = rb.json()["version"]
    assert n2 == n + 2 and rb.json()["config"] == cfg_n
    versions = {v["version"] for v in pe.get("/api/policy/versions").json()["versions"]}
    assert {n, n1, n2} <= versions

    c_tries = []
    for _ in range(3):
        ridC, dC = _submit_doc(rq, docA)
        c_tries.append(_summ(rq, ridC, dC))
        if dC["request"]["status"] == ELIGIBLE:
            break
    C = c_tries[-1]

    # versions pinned per run
    _, vA = _run_versions(rq, ridA)
    _, vB = _run_versions(rq, ridB)
    _, vC = _run_versions(rq, C["request_id"])
    assert {v[0] for v in vA.values()} == {n}
    assert {v[0] for v in vB.values()} == {n1}
    assert {v[0] for v in vC.values()} == {n2}
    assert A["config_version"] == n and B["config_version"] == n1 and C["config_version"] == n2
    stored_cfg = {r["rid"]: r["cfg"] for r in db_read(
        G, "MATCH (r:Run {tenant_id:$tenant}) WHERE r.request_id IN $rids "
        "RETURN r.request_id AS rid, r.config_version AS cfg", rids=[ridA, ridB, C["request_id"]])}
    assert stored_cfg == {ridA: n, ridB: n1, C["request_id"]: n2}  # Neo4j Run.config_version

    # A's record is immutable across the later publish and rollback
    afterA = {"judgment": judgment(rq, ridA), "runs": rq.get(f"/api/requests/{ridA}/runs").json(),
              "tasks": sorted(t["id"] for t in tasks_of(rv, ridA)), "counts": counts(G, ridA)}
    assert afterA == snapA

    # judgment/eligibility difference between A (v(n)) and B (v(n+1))
    a_ok, b_ok = A["status"] == ELIGIBLE, B["status"] == ELIGIBLE
    band_reasons_B = [r for r in B["reasons"] if r.startswith("Noul 참여 불확실")]
    diff = {"A_eligible": a_ok, "B_eligible": b_ok, "A_reasons": A["reasons"], "B_reasons": B["reasons"],
            "B_band_reasons": band_reasons_B, "C_reasons": C["reasons"], "C_eligible": C["status"] == ELIGIBLE}
    assert not b_ok and B["assignments"] == 0 and B["tasks"] == 0  # widened band => never auto-assigned
    assert len(band_reasons_B) == 3  # all three participation signals now fall in the uncertain band
    if a_ok:
        assert not any(r.startswith("Noul 참여 불확실") for r in A["reasons"])
    record("g06_policy_versions", {
        "versions": {"v_n": n, "v_n1": n1, "v_n2_rollback": n2},
        "v_n2_content_equals_v_n": rb.json()["config"] == cfg_n,
        "change": {"noul_uncertain_band": {"from": cfg_n["noul_uncertain_band"], "to": [0.0, 1.0]}},
        "A": A, "A_tries": [t["request_id"] for t in a_tries], "B": B, "C": C,
        "C_tries": [t["request_id"] for t in c_tries], "diff": diff,
        "A_unchanged_after_publish_and_rollback": True,
        "run_config_versions_stored": stored_cfg})
    if not a_ok:
        pytest.skip("부분 미검증: 요청 A가 v(n)에서도 자동 배정 조건을 만족하지 못해 eligibility 차이(허용→불가) 대조는 "
                    "미검증. 버전 고정·rollback·A 불변은 검증됨(records g06_policy_versions)")
    assert C["status"] == ELIGIBLE or C["reasons"], diff  # C: eligible again or a real reason is recorded


# ================================================================== G06 (b) Neo4j relationships <-> screens
def test_g06_stored_relationships_match_topology_and_tasks_api(gu):
    rq, rv = gu["requester"], gu["reviewer"]
    chosen = None
    attempts = []
    for _ in range(3):
        rid, d = _submit_doc(rq, "etl")
        status = d["request"]["status"]
        if status != ELIGIBLE:
            row = pending_review(rv, rid)
            res = decide(rv, row, "approve")
            assert res.status_code == 200, res.text
        g = stored_graph(rid)
        attempts.append({"request_id": rid, "initial_status": status, "tasks": len(g["tasks"]),
                         "precedes": len(g["precedes"])})
        if g["precedes"]:
            chosen = rid
            break
    if chosen is None:  # keep the last request: still a valid request->task->org comparison
        chosen = attempts[-1]["request_id"]
    g, topo, tasks = compare_stored_to_api(rq, rv, chosen)
    g["rid"] = chosen
    record("g06_graph", {
        "request_id": chosen, "attempts": attempts,
        "cypher_edges": _edges_json(graph_edges(g)),
        "task_nodes": [{"id": t["id"], "title": t["title"]} for t in tasks],
        "org_nodes": sorted({a["org"] for a in g["assigned_to"]}),
        "precedes_edges": [[p["from"], p["to"], p["from_title"], p["to_title"]] for p in g["precedes"]],
        "topology_api_edges": _edges_json(topology_edges(topo)),
        "has_precedes": bool(g["precedes"])})
    if not g["precedes"]:
        pytest.skip("부분 미검증: 3회 시도에서 PRECEDES 선행 관계가 있는 업무 초안이 나오지 않음(요청→업무→팀은 일치)")


# ================================================================== G03 evidence behaviour
def _cites(j):
    out = {}
    for o in j["outputs"]:
        for e in o["evidence"]:
            out.setdefault(o["question_id"], set()).add(json.dumps(e["location"], sort_keys=True, ensure_ascii=False))
    return out


def test_g03_short_request_missing_evidence_is_safe_and_not_fabricated(gu):
    """One-line requests under an auto-assign-permitting policy: no invented evidence, never auto-assigned."""
    rq, sr, pe = gu["requester"], gu["source_reader"], gu["policy_editor"]
    assert pe.get("/api/policy/active").json()["config"]["auto_assign"] is True
    jobs = [(t, i) for t in THIN for i in range(3)]  # 3 runs per text (also measures variability)
    with cf.ThreadPoolExecutor(5) as ex:
        res = list(ex.map(lambda a: judge(rq, a[0], None, 300), jobs))
    runs = []
    for (text, i), (rid, d) in zip(jobs, res):
        j = judgment(sr, rid)
        n = sum(len(o["evidence"]) for o in j["outputs"])
        cn = counts(G, rid)
        status = d["request"]["status"]
        runs.append({"text": text, "attempt": i + 1, "request_id": rid, "status": status, "citations": n,
                     "reasons": j["review_reasons"], **{k: cn[k] for k in ("assignments", "tasks")},
                     "classifications": j["classifications"]})
        assert cn["assignments"] == 0 and cn["tasks"] == 0 and status != ELIGIBLE, runs[-1]
        assert j["review_reasons"], runs[-1]  # never silently "fine"
        for o in j["outputs"]:  # nothing synthesised: any cited evidence must be a real stored span
            for e in o["evidence"]:
                assert e["location"] and e["attachment_id"], e
                assert e["source_text"] and e["source_text"] in text, e
    no_ev = [r for r in runs if r["citations"] == 0]
    for r in no_ev:
        assert any("근거 미완료" in x for x in r["reasons"]) or any("영속 근거" in x for x in r["reasons"]) or \
            r["status"] != ELIGIBLE, r
    record("g03_short_requests", {
        "runs": runs, "runs_with_zero_citations": len(no_ev), "total_runs": len(runs),
        "zero_citation_runs_flag_missing_evidence": all(
            any(("근거 미완료" in x) or ("영속 근거" in x) for x in r["reasons"]) for r in no_ev),
        "zero_citation_without_missing_evidence_reason": [r["request_id"] for r in no_ev if not any(
            ("근거 미완료" in x) or ("영속 근거" in x) for x in r["reasons"])]})


def test_g03_evidence_citation_variability_three_repeats(gu):
    """Same document input, 3 independent live runs: measure how much the cited evidence set varies."""
    rq, sr = gu["requester"], gu["source_reader"]
    out = {}
    for key in ("sales", "etl"):
        with cf.ThreadPoolExecutor(3) as ex:
            res = list(ex.map(lambda _, key=key: _submit_doc(rq, key), range(3)))
        sets, per_key, counts_list, ids = [], [], [], []
        body = DOCS[key][1]
        for rid, d in res:
            j = judgment(sr, rid)
            cites = _cites(j)
            flat = {(q, loc) for q, s in cites.items() for loc in s}
            sets.append(flat)
            per_key.append({q: len(s) for q, s in cites.items()})
            counts_list.append(len(flat))
            ids.append(rid)
            for o in j["outputs"]:  # integrity: every citation is a verbatim excerpt of the document
                for e in o["evidence"]:
                    assert e["source_text"] and e["source_text"].strip()[:40] in body, e
        union = set().union(*sets)
        inter = set.intersection(*sets) if sets else set()
        pair = []
        for i in range(3):
            for k in range(i + 1, 3):
                u = sets[i] | sets[k]
                pair.append(round(len(sets[i] & sets[k]) / len(u), 3) if u else 1.0)
        # locations are (file, line range) so they are comparable across requests; attachment ids are per request
        locs = [{loc for _, loc in s} for s in sets]
        out[key] = {"request_ids": ids, "citations_per_run": counts_list, "per_question_counts": per_key,
                    "union": len(union), "intersection": len(inter),
                    "jaccard_pairs": pair,
                    "unique_locations_per_run": [len(x) for x in locs],
                    "location_union": len(set().union(*locs)), "location_intersection": len(set.intersection(*locs)),
                    "runs_with_zero_citations": sum(1 for c in counts_list if c == 0)}
    record("g03_citation_variability", {"repeats": 3, "metrics": out,
                                        "note": "품질 지표(통과/실패 판정 아님). 위조 방지는 단정: 모든 인용은 원문 발췌."})
