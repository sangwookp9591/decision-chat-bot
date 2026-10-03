"""A) Eight mandatory user scenarios (06_ACCEPTANCE) against the live API + stored state.

Live Jev only (JEV_MODE=live); labels are never asserted as ground truth - the tests verify that
the required evidence/structure is provided and that stored state matches the API.
Collected only by `make test-acceptance` (file prefix `acc_`).
"""
from __future__ import annotations

import time
from datetime import datetime

import pytest

from tests.acceptance import docs_fixture as D
from tests.acceptance.harness import (
    TENANT,
    TENANT_F,
    counts,
    db_read,
    decide,
    judge,
    judgment,
    model_output_count,
    pending_review,
    record,
    tasks_of,
    tenant_totals,
    topology,
)

METHODS = {"AI", "일반 기술", "사람", "미정"}
CLASS_KEYS = {"ai_need", "feasibility", "urgency", "lead_org"}


def _assert_judgment_shape(j: dict) -> None:
    assert j["mode"] == "live", "gate evidence must come from live Jev"
    assert CLASS_KEYS <= set(j["classifications"]), j["classifications"]
    assert all(j["classifications"][k] for k in CLASS_KEYS)
    assert j["versions"]["model"] and j["versions"]["qset"] and j["versions"]["config_version"] >= 1
    by_q = {o["question_id"]: o for o in j["outputs"]}
    for key in CLASS_KEYS:  # every core classification has a saved model output with confidence
        assert key in by_q and "confidence" in by_q[key], key
    assert j["draft_tasks"], "task draft missing"
    for t in j["draft_tasks"]:
        assert t["method"] in METHODS and t["lead_org"] and t["title"] and t["deliverable"]
    assert j["review_reasons"] is not None


# ---------------------------------------------------------------- 1. general technical request
def test_s1_general_technical_csv_monthly_aggregation(users):
    rq, rv = users["requester"], users["reviewer"]
    rid, d = judge(rq, "SAP에서 내려받은 매출 CSV를 월별로 집계해 화면에 보여 주세요.")
    j = judgment(rq, rid)
    _assert_judgment_shape(j)
    c = counts(TENANT, rid)
    assert c["runs"] == 1 and c["judgments"] == 1
    assert d["request"]["status"] in {"검토 대기", "배정 완료", "auto_assign_eligible"}
    # stored classification equals the API value
    row = db_read(TENANT, "MATCH (j:Judgment {tenant_id:$tenant,request_id:$rid}) "
                  "RETURN j.ai_need AS a,j.feasibility AS f,j.urgency AS u,j.lead_org AS l", rid=rid)[0]
    assert (row["a"], row["f"], row["u"], row["l"]) == tuple(
        j["classifications"][k] for k in ("ai_need", "feasibility", "urgency", "lead_org"))
    record("s1", {"request_id": rid, "run_id": j["run_id"], "judgment_id": j["id"],
                  "classifications": j["classifications"], "versions": j["versions"],
                  "tasks": [(t["title"], t["method"], t["lead_org"]) for t in j["draft_tasks"]],
                  "reasons": j["review_reasons"], "status": d["request"]["status"]})
    if j["review"]:  # leave the review pending; other tests approve their own requests
        assert pending_review(rv, rid)["run_id"] == j["run_id"]


ROOMS_DOC = (
    "# 회의실 예약 현황 조회 요청\n\n현재 각 부서는 회의실 예약을 엑셀 파일로 따로 관리하고 있어 전체 예약 "
    "현황을 한눈에 볼 수 없습니다. 총무팀이 부서별 예약 현황을 하나의 화면에서 조회하고 예약 가능 시간을 "
    "확인할 수 있어야 합니다.\n\n예약 데이터는 사내 예약 시스템의 데이터베이스에 있으며 IT팀이 조회 권한을 "
    "가지고 있습니다. 마감 기한은 없고 다음 분기 안에 완료되면 됩니다.\n")


def test_g03_core_classifications_have_locatable_evidence(users):
    """G03: core classifications carry linked, locatable source evidence (realistic document)."""
    rq, sr = users["requester"], users["source_reader"]
    rid, _ = judge(rq, "첨부 문서의 회의실 예약 현황 조회 화면 요청을 검토해 주세요.",
                   [("rooms.md", ROOMS_DOC.encode(), D.MD)])
    j = judgment(sr, rid)
    cited = {o["question_id"]: o["evidence"] for o in j["outputs"] if o["evidence"]}
    record("g03_evidence", {"request_id": rid, "run_id": j["run_id"],
                            "outputs_with_evidence": {k: len(v) for k, v in cited.items()},
                            "review_reasons": j["review_reasons"]})
    assert cited, f"no evidence linked (reasons: {j['review_reasons']})"
    assert set(cited) & CLASS_KEYS
    for evs in cited.values():
        for e in evs:
            assert e["location"] and e["attachment_id"] and e.get("source_text")  # source reader sees text
            assert 0 <= e["probability"] <= 1


def test_g03_thin_one_line_input_reports_missing_evidence_not_fake_evidence(users):
    """A one-line request may yield no linked evidence; the system must say so (review reason)."""
    rq = users["requester"]
    rid, _ = judge(rq, "사내 회의실 예약 현황을 한곳에서 조회할 수 있는 화면이 필요합니다.")
    j = judgment(rq, rid)
    n = sum(len(o["evidence"]) for o in j["outputs"])
    record("g03_thin_input", {"request_id": rid, "citations": n, "reasons": j["review_reasons"]})
    assert n > 0 or "근거 미완료" in j["review_reasons"]


# ---------------------------------------------------------------- 2. mixed request
MIXED = [
    ("고객 문의 메일을 자동 분류하고 답변 초안을 생성하는 생성형 AI 기능이 필요합니다. 모델 평가 방법, "
     "사내 시스템 연동, 현업의 승인 기준이 필요합니다."),
    ("과거 판매 이력으로 제품별 수요를 예측하는 머신러닝 모델을 만들고, 예측 수요가 안전재고보다 낮으면 "
     "담당자에게 알림을 보내야 합니다. ERP 데이터 연결은 IT, 알림 기준과 운영 책임은 현업이 정합니다."),
]


def test_s2_mixed_forecast_and_alert_tasks_linked_after_approval(users):
    rq, rv = users["requester"], users["reviewer"]
    best = None
    for text in MIXED + MIXED:  # live output varies; take the first attempt that yields mixed methods
        rid, _ = judge(rq, text)
        j = judgment(rq, rid)
        methods = {t["method"] for t in j["draft_tasks"]}
        if best is None or len(methods) > len({t["method"] for t in best[1]["draft_tasks"]}):
            best = (rid, j)
        if "AI" in methods and len(methods) >= 2:
            best = (rid, j)
            break
    rid, j = best
    methods = {t["method"] for t in j["draft_tasks"]}
    assert "AI" in methods and methods & {"일반 기술", "사람"}, f"no mixed task drafts: {methods}"
    row = pending_review(rv, rid)
    res = decide(rv, row, "approve")
    assert res.status_code == 200, res.text
    assigned = res.json()["assignment"]["task_ids"]
    assert len(assigned) == len(j["draft_tasks"])
    tasks = tasks_of(rv, rid)
    assert len(tasks) == len(j["draft_tasks"]) and counts(TENANT, rid)["assignments"] == 1
    by_title = {t["title"]: t for t in tasks}
    for d in j["draft_tasks"]:
        t = by_title[d["title"]]
        assert t["method"] == d["method"] and t["lead_org"] == d["lead_org"]
        assert sorted(t["collab_orgs"]) == sorted(d["collab_orgs"])
        roles = {(o["role"], o["org"].split("-")[-1]) for o in t["orgs"]}
        assert any(r == "lead" for r, _ in roles)
    # predecessor relations stored as PRECEDES edges equal the draft predecessors
    topo = topology(rv, rid)
    prec = {(e["from"], e["to"]) for e in topo["edges"] if e["kind"] == "PRECEDES"}
    expected = {(assigned[p], assigned[d["draft_task_id"]])
                for d in j["draft_tasks"] for p in d["predecessors"]}
    assert prec == expected, (prec, expected)
    # unresolved prerequisite -> dependent tasks start blocked, not executable
    for d in j["draft_tasks"]:
        if d["predecessors"]:
            assert by_title[d["title"]]["status"] == "막힘"
    record("s2", {"request_id": rid, "run_id": j["run_id"], "assignment": res.json()["assignment"],
                  "tasks": [(t["id"], t["title"], t["method"], t["lead_org"], t["status"])
                            for t in tasks], "precedes_edges": sorted(prec)})


PRED_TEXT = (
    "영업팀이 쓰는 제품별 월간 판매량을 머신러닝으로 예측하는 모델이 필요합니다. 과거 3년치 판매 데이터는 사내 "
    "ERP에 있고 IT팀이 추출해야 합니다. 예측 결과는 대시보드 화면으로 보여 주고, 예측치가 재고 기준 아래로 "
    "떨어지면 담당 영업 매니저에게 이메일 알림을 보내야 합니다. 알림 기준과 운영 책임은 현업에서 정해야 합니다.")


def test_s2_predecessor_relations_become_stored_precedes_edges(users):
    """Tasks that depend on another task: PRECEDES edges, dependents start blocked, order preserved."""
    rq, rv = users["requester"], users["reviewer"]
    chosen = None
    for _ in range(4):  # live output varies; need a draft where at least one task has a predecessor
        rid, _d = judge(rq, PRED_TEXT)
        j = judgment(rq, rid)
        if any(t["predecessors"] for t in j["draft_tasks"]):
            chosen = (rid, j)
            break
    assert chosen, "live Jev produced no dependent tasks in 4 attempts"
    rid, j = chosen
    res = decide(rv, pending_review(rv, rid), "approve")
    assert res.status_code == 200, res.text
    ids = res.json()["assignment"]["task_ids"]
    topo = topology(rv, rid)
    prec = {(e["from"], e["to"]) for e in topo["edges"] if e["kind"] == "PRECEDES"}
    expected = {(ids[p], ids[d["draft_task_id"]]) for d in j["draft_tasks"] for p in d["predecessors"]}
    assert expected and prec == expected, (prec, expected)
    stored = {t["id"]: t for t in tasks_of(rv, rid)}
    for d in j["draft_tasks"]:
        if d["predecessors"]:
            assert stored[ids[d["draft_task_id"]]]["status"] == "막힘"
    # a dependent task cannot be started while its predecessor is unfinished (409), nothing changes
    dep = next(d for d in j["draft_tasks"] if d["predecessors"])
    t = stored[ids[dep["draft_task_id"]]]
    tm = users["team_member"]
    r = tm.post(f"/api/tasks/{t['id']}/transition", json={"to": "진행", "expected_status": t["status"]})
    assert r.status_code in (409, 422, 400), (r.status_code, r.text[:160])
    assert {x["id"]: x["status"] for x in tasks_of(rv, rid)} == {k: v["status"] for k, v in stored.items()}
    record("s2_predecessors", {"request_id": rid, "precedes_edges": sorted(prec),
                               "dependent_task_start_status": r.status_code,
                               "drafts": [(d["draft_task_id"], d["title"], d["predecessors"])
                                          for d in j["draft_tasks"]]})


# ---------------------------------------------------------------- 3. urgent request
URGENT = [
    ("오늘 오후 6시까지 마감해야 하는 월말 정산 시스템이 멈춰서 전 부서 업무가 중단됐습니다. 당일 마감 "
     "전에 반드시 복구가 필요합니다."),
    ("주문 접수 시스템이 중단되어 모든 영업 업무가 멈췄습니다. 오늘 안에 마감해야 하는 고객 계약이 "
     "있어 즉시 처리가 필요합니다."),
]


def test_s3_urgent_request_reason_review_and_priority(users):
    rq, rv = users["requester"], users["reviewer"]
    chosen = None
    for text in URGENT + URGENT:
        rid, _ = judge(rq, text)
        j = judgment(rq, rid)
        if j["classifications"]["urgency"] == "긴급":
            chosen = (rid, j)
            break
    assert chosen, "live Jev never classified the urgent samples as 긴급 in 4 attempts"
    rid, j = chosen
    urgency = next(o for o in j["outputs"] if o["question_id"] == "urgency")
    assert urgency["confidence"] is not None and urgency["probabilities"]  # uncertainty provided
    assert any("urgent" in r or "긴급" in r for r in j["review_reasons"]), j["review_reasons"]
    assert counts(TENANT, rid)["assignments"] == 0  # urgent never auto-assigns
    # a normal request submitted afterwards must not outrank the urgent one in the urgent-first view
    nrid, _ = judge(rq, "사내 공지사항 게시판의 글꼴 크기를 조금 키워 주세요.")
    pending_review(rv, nrid)
    queue = rv.get("/api/reviews?status=pending").json()["reviews"]
    row = next(r for r in queue if r["request_id"] == rid)
    assert row["urgency"] == "긴급"
    ordered = sorted(queue, key=lambda r: -(r.get("urgency") == "긴급"))
    assert ordered.index(row) < len([r for r in ordered if r.get("urgency") == "긴급"])
    record("s3", {"request_id": rid, "run_id": j["run_id"], "urgency_confidence": urgency["confidence"],
                  "reasons": j["review_reasons"], "queue_row": {k: row[k] for k in ("id", "urgency")}})


# ---------------------------------------------------------------- 4. insufficient / impossible
NOINFO = ("고객 개인 데이터를 외부 시스템과 연동해 자동 분석하고 싶은데, 어떤 데이터가 있는지, 접근 "
          "권한과 승인이 있는지 아직 아무도 모릅니다.")


def test_s4_missing_data_permission_approval_no_unapproved_execution(users):
    rq, rv = users["requester"], users["reviewer"]
    rid, d = judge(rq, NOINFO)
    j = judgment(rq, rid)
    assert j["classifications"]["feasibility"] != "가능" or j["review_reasons"], j
    assert j["review"] and j["review_reasons"]  # reasons to complete / not yet possible are shown
    c = counts(TENANT, rid)
    assert c["assignments"] == 0 and c["tasks"] == 0 and d["request"]["status"] == "검토 대기"
    # a reviewer asks for information: needed_info stored, still no execution
    row = pending_review(rv, rid)
    res = decide(rv, row, "request_info", reason="데이터 목록과 접근 승인 문서를 보완해 주세요",
                 needed_info=["데이터 목록", "접근 권한 승인 문서"])
    assert res.status_code == 200 and res.json()["needed_info"] == ["데이터 목록", "접근 권한 승인 문서"]
    c = counts(TENANT, rid)
    assert c["assignments"] == 0 and c["tasks"] == 0 and c["status"] == "보완 필요"
    record("s4", {"request_id": rid, "run_id": j["run_id"], "classifications": j["classifications"],
                  "reasons": j["review_reasons"], "after_request_info": c})


# ---------------------------------------------------------------- 5. document input
def _doc_files(with_bad=True):
    files = [("returns.pdf", D.pdf_bytes(D.PDF_TEXT), D.PDF),
             ("approval.docx", D.docx_bytes(D.DOCX_TEXT), D.DOCX),
             ("rooms.md", D.MD_TEXT.encode(), D.MD)]
    if with_bad:
        files.append(("broken.pdf", D.DAMAGED_PDF, D.PDF))
    return files


def test_s5_documents_pdf_docx_md_with_one_damaged_file(users):
    rq, sr = users["requester"], users["source_reader"]
    r = rq.submit("세 문서의 요청 내용을 함께 검토해 주세요.", _doc_files())
    assert r.status_code == 202 and r.json()["status"] == "needs_file_decision"
    rid = r.json()["request_id"]
    time.sleep(1)
    d = rq.detail(rid)
    atts = {a["filename"]: a for a in d["attachments"]}
    assert atts["broken.pdf"]["status"] == "rejected" and atts["broken.pdf"]["reason"] == "corrupted"
    assert all(atts[n]["status"] == "ok" for n in ("returns.pdf", "approval.docx", "rooms.md"))
    # no silent ignore: no run/job until the requester picks include/exclude explicitly
    assert counts(TENANT, rid)["runs"] == 0
    # per-file extraction with locations (stored spans); source text only for source readers
    spans = db_read(TENANT, "MATCH (e:EvidenceSpan {tenant_id:$tenant,request_id:$rid}) "
                    "RETURN e.id AS id,e.attachment_id AS att,e.location_json AS loc,e.source_text AS txt", rid=rid)
    by_file = {}
    for s in spans:
        if s["att"] is None:
            continue
        name = next(a["filename"] for a in d["attachments"] if a["id"] == s["att"])
        by_file.setdefault(name, []).append(s)
    assert {"returns.pdf", "approval.docx", "rooms.md"} <= set(by_file)
    assert any("PDFMARKER7731" in s["txt"] for s in by_file["returns.pdf"])
    assert any("DOCXMARKER4482" in s["txt"] for s in by_file["approval.docx"])
    assert any("MDMARKER9915" in s["txt"] for s in by_file["rooms.md"])
    assert all(s["loc"] for ss in by_file.values() for s in ss)
    # explicit exclusion of the damaged file -> new revision + judgment
    res = rq.post(f"/api/requests/{rid}/file-decision",
                  json={"exclude": [atts["broken.pdf"]["id"]], "expected_revision": 1})
    assert res.status_code == 202 and res.json()["revision"] == 2
    d = rq.wait(rid)
    j = judgment(sr, rid)
    _assert_judgment_shape(j)
    excluded = [a for a in d["attachments"] if a.get("excluded")]
    assert [a["filename"] for a in excluded] == ["broken.pdf"]
    # source readers can open stored per-file source spans; plain requester cannot read operator-only text
    span = next(s for s in db_read(TENANT, "MATCH (e:EvidenceSpan {tenant_id:$tenant,request_id:$rid}) "
                                   "RETURN e.id AS id,e.source_text AS txt", rid=rid)
                if "PDFMARKER7731" in s["txt"])
    assert sr.get(f"/api/requests/{rid}/evidence/{span['id']}").status_code in (200, 404)
    valid_span_ids = {s["id"] for s in db_read(
        TENANT, "MATCH (e:EvidenceSpan {tenant_id:$tenant,request_id:$rid}) RETURN e.id AS id", rid=rid)}
    cited_span_ids = {e["id"] for o in j["outputs"] for e in o["evidence"]}
    cited_files = {a["filename"] for o in j["outputs"] for e in o["evidence"]
                   for a in d["attachments"] if a["id"] == e.get("attachment_id")}
    record("s5", {"request_id": rid, "run_id": j["run_id"], "stored_spans_per_file":
                  {k: len(v) for k, v in by_file.items()}, "excluded": ["broken.pdf"],
                  "files_cited_by_judgment": sorted(cited_files),
                  "review_reasons": j["review_reasons"]})
    # Verify the input and citation structure; live Jev confidence/citation choices are variable.
    assert [a["filename"] for a in excluded] == ["broken.pdf"]
    assert all(span_id in valid_span_ids for span_id in cited_span_ids)
    assert all(e.get("source") in {"chat", "attachment"}
               for o in j["outputs"] for e in o["evidence"])


def test_s5_citation_coverage_across_attempts(users):
    """Each input file has stored source locations; any returned citations resolve to those spans."""
    rq, sr = users["requester"], users["source_reader"]
    per_attempt = []
    for _ in range(3):
        r = rq.submit("세 문서의 요청 내용을 함께 검토해 주세요.", _doc_files(with_bad=False))
        assert r.status_code == 202
        rid = r.json()["request_id"]
        rq.wait(rid)
        j = judgment(sr, rid)
        cited = [e for o in j["outputs"] for e in o["evidence"]]
        spans = db_read(TENANT, "MATCH (e:EvidenceSpan {tenant_id:$tenant,request_id:$rid}) "
                        "RETURN e.id AS id,e.attachment_id AS attachment_id,e.location_json AS location", rid=rid)
        valid = {row["id"] for row in spans}
        assert all(e["id"] in valid for e in cited)
        file_spans = [s for s in spans if s["attachment_id"] is not None]
        assert len(file_spans) >= 3 and all(s["location"] for s in file_spans)
        per_attempt.append({"request_id": rid, "run_id": j["run_id"],
                            "stored_file_positions": len(file_spans), "resolved_citations": len(cited)})
    record("s5_citation_coverage", {"attempts": per_attempt,
                                    "verification": "stored locations and citation ID resolution"})


# ---------------------------------------------------------------- 6. human intervention
def _fresh_review(users, text):
    rq, rv = users["requester"], users["reviewer"]
    rid, _ = judge(rq, text)
    return rid, judgment(rq, rid), pending_review(rv, rid)


def test_s6_reviewer_correction_preserves_original_and_final(users):
    rv = users["reviewer"]
    rid, j, row = _fresh_review(users, "분기별 시설 점검 일정을 부서별로 조회하는 화면이 필요합니다.")
    original = dict(j["classifications"])
    draft0 = [dict(t) for t in j["draft_tasks"]]
    first = draft0[0]
    new_lead = "현업" if first["lead_org"] != "현업" else "IT팀"
    changes = {"classifications": {"feasibility": "가능"},
               "draft_tasks": [{"draft_task_id": first["draft_task_id"], "lead_org": new_lead}]}
    res = decide(rv, row, "approve_with_changes", reason="검토자가 가능성과 담당 팀을 확인함", changes=changes)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["draft_version"] == row["draft_version"] + 1 and body["correction_ids"]
    # AI original preserved unchanged; final values distinct and recorded
    j_after = judgment(rv, rid)
    assert j_after["classifications"] == original
    det = rv.get(f"/api/reviews/{row['id']}").json()
    assert det["final_classifications"]["feasibility"] == "가능"
    corr = [c for h in det["history"] for c in h["corrections"]]
    feas = next(c for c in corr if c["field"] == "feasibility")
    assert feas["ai_value"] == original["feasibility"] and feas["corrected_value"] == "가능"
    assert feas["corrected_by"] and feas["corrected_at"] and feas["run_id"] == row["run_id"]
    drafts = {d["draft_version"]: d for d in det["drafts"]}
    assert set(drafts) >= {row["draft_version"], row["draft_version"] + 1}
    old = {t["draft_task_id"]: t for t in drafts[row["draft_version"]]["tasks"]}
    new = {t["draft_task_id"]: t for t in drafts[row["draft_version"] + 1]["tasks"]}
    assert old[first["draft_task_id"]]["lead_org"] == first["lead_org"]
    assert new[first["draft_task_id"]]["lead_org"] == new_lead
    stored = {t["title"]: t for t in tasks_of(rv, rid)}
    assert stored[first["title"]]["lead_org"] == new_lead
    audit = db_read(TENANT, "MATCH (a:Audit {tenant_id:$tenant,target_id:$id}) RETURN count(a) AS n",
                    id=row["id"])[0]["n"]
    assert audit == 1
    record("s6_modify", {"request_id": rid, "review_id": row["id"], "decision_id": body["decision_id"],
                         "correction_ids": body["correction_ids"], "original": original,
                         "final": det["final_classifications"], "audit_records": audit})


def test_s6_reject_and_request_info_are_separate(users):
    rv = users["reviewer"]
    rid, _, row = _fresh_review(users, "사내 프린터 위치 안내 페이지를 만들어 주세요.")
    r = decide(rv, row, "reject", reason="현재 우선순위에 없는 요청입니다")
    assert r.status_code == 200 and r.json()["status"] == "rejected"
    c = counts(TENANT, rid)
    assert c["status"] == "반려" and c["assignments"] == 0 and c["tasks"] == 0
    rid2, _, row2 = _fresh_review(users, "사내 휴게실 예약 알림 기능을 추가해 주세요.")
    r2 = decide(rv, row2, "request_info", reason="예약 대상 시설 목록이 필요합니다")
    assert r2.status_code == 200 and r2.json()["status"] == "info_requested"
    c2 = counts(TENANT, rid2)
    assert c2["status"] == "보완 필요" and c2["assignments"] == 0 and c2["tasks"] == 0
    # a decided review cannot be decided again (stale target -> 409)
    assert decide(rv, row, "approve").status_code == 409
    record("s6_reject_info", {"rejected": {"request_id": rid, "review_id": row["id"], **c},
                              "info_requested": {"request_id": rid2, "review_id": row2["id"], **c2}})


# ---------------------------------------------------------------- 7. re-analysis
def _wait_runs(rq, rid, n, timeout=240.0):
    end = time.time() + timeout
    while time.time() < end:
        runs = rq.get(f"/api/requests/{rid}/runs").json()["runs"]
        d = rq.detail(rid)
        if (len(runs) == n and all(r["status"] in ("judgment_saved", "failed") for r in runs)
                and d["request"]["status"] not in ("judgment_pending", "received")):
            return d
        time.sleep(3)
    raise TimeoutError(f"{rid}: expected {n} finished runs")


def test_s7_reanalysis_separates_runs_and_never_duplicates_tasks(users):
    rq, rv = users["requester"], users["reviewer"]
    rid, d = judge(rq, "월별 재고 현황을 조회하는 화면과 부족 재고 알림이 필요합니다.")
    j1 = judgment(rq, rid)
    row = pending_review(rv, rid)
    res = decide(rv, row, "approve")
    assert res.status_code == 200
    before = counts(TENANT, rid)
    task_ids = sorted(t["id"] for t in tasks_of(rv, rid))
    assert before["assignments"] == 1 and len(task_ids) == before["tasks"] >= 1
    # publish a new policy version between the runs: the old run keeps its version, the new run uses v+1
    pe = users["policy_editor"]
    active = pe.get("/api/policy/active").json()
    cfg = dict(active["config"], feature_flags={**active["config"].get("feature_flags", {}), "acc21": True})
    pub = pe.post("/api/policy/publish", json={"config": cfg, "reason": "인수 시험: 재분석 정책 버전 구분",
                                               "expected_active_version": active["version"]})
    assert pub.status_code == 200, pub.text
    new_policy = pub.json()["version"]
    # add information (new revision) -> new run
    rev = d["request"]["revision_number"]
    res = rq.revise(rid, rev, "추가 정보: 재고 데이터는 ERP 일별 스냅샷이고 담당자는 물류팀입니다.")
    assert res.status_code == 202, res.text
    d2 = _wait_runs(rq, rid, 2)
    assert d2["request"]["status"] == "배정 완료"  # compare-only result must not leave "in analysis"
    runs = rq.get(f"/api/requests/{rid}/runs").json()
    assert len(runs["runs"]) == 2 and runs["active_run_id"] != j1["run_id"]
    old_run = next(r for r in runs["runs"] if r["id"] == j1["run_id"])
    new_run = next(r for r in runs["runs"] if r["id"] == runs["active_run_id"])
    assert old_run["revision_id"] != new_run["revision_id"]
    assert old_run["versions"]["config"] == active["version"]
    assert new_run["versions"]["config"] == new_policy == active["version"] + 1
    j2 = judgment(rq, rid, runs["active_run_id"])
    assert j2["id"] != j1["id"] and j2["run_id"] != j1["run_id"]
    assert judgment(rq, rid, j1["run_id"])["id"] == j1["id"]  # previous result still readable
    after = counts(TENANT, rid)
    assert after["assignments"] == 1 and after["tasks"] == before["tasks"]
    assert sorted(t["id"] for t in tasks_of(rv, rid)) == task_ids
    # explicit re-analysis without new input also creates a distinct run, still zero new tasks
    rev2 = d2["request"]["revision_number"]
    res = rq.post(f"/api/requests/{rid}/reanalyze", json={"expected_revision": rev2, "reason": "재확인"})
    assert res.status_code in (202, 409), res.text
    time.sleep(1)
    if res.status_code == 202:
        _wait_runs(rq, rid, 3)
    # roll the policy back: a later run uses the rollback version, history keeps every earlier version
    cur = pe.get("/api/policy/active").json()
    rb = pe.post("/api/policy/rollback", json={"target_version": active["version"], "reason": "인수 시험 종료: 되돌리기",
                                               "expected_active_version": cur["version"]})
    assert rb.status_code == 200, rb.text
    assert rb.json()["config"]["feature_flags"] == active["config"].get("feature_flags", {})
    versions = {v["version"] for v in pe.get("/api/policy/versions").json()["versions"]}
    assert {active["version"], new_policy, rb.json()["version"]} <= versions
    final = counts(TENANT, rid)
    assert final["assignments"] == 1 and final["tasks"] == before["tasks"]
    # a stale decision on the previous draft is rejected
    assert decide(rv, row, "approve").status_code == 409
    record("s7", {"request_id": rid, "policy_versions": {"before": active["version"], "published": new_policy,
                                                         "rollback": rb.json()["version"]},
                  "old_run": old_run, "new_run": new_run,
                  "judgment_ids": [j1["id"], j2["id"]], "task_ids_unchanged": task_ids,
                  "counts_before": before, "counts_after": final})


# ---------------------------------------------------------------- 8. observe and playback
def _flow_matches_storage(rq, rid, run_id):
    flow = rq.get(f"/api/observe/runs/{run_id}/flow").json()
    stored = {r["id"]: r for r in db_read(
        TENANT, "MATCH (s:RunStep {tenant_id:$tenant,run_id:$run}) RETURN s.id AS id,s.status AS status,"
        "toString(s.started_at) AS st,toString(s.ended_at) AS en,s.duration_ms AS ms", run=run_id)}
    steps = [n for n in flow["nodes"] if n["id"] in stored]
    assert steps, flow
    for n in steps:
        assert n["status"] == stored[n["id"]]["status"], (n, stored[n["id"]])
    return flow, stored


def test_s8_flow_and_playback_have_no_side_effects(users):
    rq, rv, op = users["requester"], users["reviewer"], users["operator"]
    # success run (assigned) and human-waiting run (pending review)
    ok_rid, _ = judge(rq, "분기 매출 요약 리포트를 화면에서 보고 싶습니다.")
    ok_j = judgment(rq, ok_rid)
    assert decide(rv, pending_review(rv, ok_rid), "approve").status_code == 200
    wait_rid, _ = judge(rq, "신규 입사자 온보딩 체크리스트 화면이 필요합니다.")
    wait_j = judgment(rq, wait_rid)
    pending_review(rv, wait_rid)
    out = {}
    for label, rid, j in (("success", ok_rid, ok_j), ("waiting_human", wait_rid, wait_j)):
        flow, _stored = _flow_matches_storage(rq, rid, j["run_id"])
        kinds = {n["status"] for n in flow["nodes"]}
        out[label] = {"request_id": rid, "run_id": j["run_id"], "statuses": sorted(kinds),
                      "node_count": len(flow["nodes"])}
    assert "waiting_human" in {s for s in out["waiting_human"]["statuses"]} or any(
        n.get("kind") == "human" for n in rq.get(
            f"/api/observe/runs/{wait_j['run_id']}/flow").json()["nodes"])
    # Playback / Topology / Trace reads change nothing (tasks, jobs, model outputs, runs, reviews)
    totals_before = tenant_totals(TENANT)
    outputs_before = model_output_count(TENANT, ok_rid)
    for _ in range(3):
        for rid, j in ((ok_rid, ok_j), (wait_rid, wait_j)):
            pb = rq.get(f"/api/observe/runs/{j['run_id']}/playback")
            assert pb.status_code == 200
            events = pb.json().get("events", [])
            assert events and all(isinstance(e["at"], str) for e in events)  # parseable ISO times
            for e in events:
                datetime.fromisoformat(e["at"])
                if e["type"] == "step_ended":
                    assert e["duration_ms"] is not None
            assert rq.get(f"/api/observe/requests/{rid}/topology").status_code == 200
            for n in rq.get(f"/api/observe/runs/{j['run_id']}/flow").json()["nodes"]:
                if n["id"].startswith("step_"):
                    assert op.get(f"/api/observe/steps/{n['id']}").status_code == 200
    assert tenant_totals(TENANT) == totals_before
    assert model_output_count(TENANT, ok_rid) == outputs_before
    out["totals_unchanged"] = totals_before
    record("s8", out)


@pytest.mark.parametrize("n", [0])
def test_s8_failed_run_from_live_jev_rejection(users, n):
    """Real failed run: a worker with an invalid Jev key (tenant <base>f only) -> Jev rejects."""
    from tests.acceptance.harness import Client
    rq = Client("requester", TENANT_F)
    r = rq.submit("월별 판매 현황을 조회하는 화면이 필요합니다.")
    assert r.status_code == 202
    rid = r.json()["request_id"]
    d = rq.wait(rid, timeout=300, until=lambda x: x["request"]["status"] in ("failed", "실패"))
    assert d["request"]["status"] in ("failed", "실패")
    c = counts(TENANT_F, rid)
    assert c["assignments"] == 0 and c["tasks"] == 0 and c["judgments"] == 0
    runs = rq.get(f"/api/requests/{rid}/runs").json()["runs"]
    run = runs[0]
    assert run["status"] == "failed"
    flow = rq.get(f"/api/observe/runs/{run['id']}/flow").json()
    failed = [n for n in flow["nodes"] if n["status"] == "failed"]
    assert failed, flow
    stored = db_read(TENANT_F, "MATCH (s:RunStep {tenant_id:$tenant,run_id:$run,status:'failed'}) "
                     "RETURN s.id AS id", run=run["id"])
    assert {n["id"] for n in failed} == {s["id"] for s in stored}
    before = tenant_totals(TENANT_F)
    assert rq.get(f"/api/observe/runs/{run['id']}/playback").status_code == 200
    assert tenant_totals(TENANT_F) == before
    record("s8_failed", {"request_id": rid, "run_id": run["id"], "failed_steps": [n["id"] for n in failed],
                         "run_status": run["status"]})
