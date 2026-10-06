"""B) Safety, permissions, duplicate prevention and key protection (G04/G05/G11 + G06 invariants)."""
from __future__ import annotations

import concurrent.futures as cf
import io
import json
import time
from pathlib import Path

import pytest
from pypdf import PdfWriter

from tests.acceptance import docs_fixture as D
from tests.acceptance.harness import (
    API,
    TENANT,
    TENANT_P,
    Client,
    counts,
    db_read,
    db_write,
    decide,
    judge,
    judgment,
    pending_review,
    record,
    tenant_totals,
)

ROOT = Path(__file__).resolve().parents[3]
PTENANT = TENANT_P
DOC = ("# 회의실 예약 현황 조회 요청\n\n각 부서가 엑셀로 따로 관리하는 회의실 예약 현황을 하나의 화면에서 "
       "조회하고 예약 가능 시간을 확인해야 합니다. 예약 데이터는 IT팀이 조회 권한을 가진 시스템에 있습니다.\n")


@pytest.fixture(scope="module")
def sample(users):
    """One judged request (with a document) that stays pending review, for permission probes."""
    rq = users["requester"]
    rid, _ = judge(rq, "첨부 문서의 회의실 예약 현황 요청을 검토해 주세요.", [("rooms.md", DOC.encode(), D.MD)])
    j = judgment(rq, rid)
    row = pending_review(users["reviewer"], rid)
    span = db_read(TENANT, "MATCH (e:EvidenceSpan {tenant_id:$tenant,request_id:$rid}) "
                   "RETURN e.id AS id LIMIT 1", rid=rid)[0]["id"]
    step = db_read(TENANT, "MATCH (s:RunStep {tenant_id:$tenant,run_id:$run}) RETURN s.id AS id LIMIT 1",
                   run=j["run_id"])[0]["id"]
    return {"rid": rid, "run": j["run_id"], "review": row, "span": span, "step": step,
            "revision": row["revision_id"]}


# ------------------------------------------------------------------ tenant / organisation isolation
def _all_paths(s):
    rid, run = s["rid"], s["run"]
    return [("GET", f"/api/requests/{rid}"), ("GET", f"/api/requests/{rid}/judgment"),
            ("GET", f"/api/requests/{rid}/runs"), ("GET", f"/api/requests/{rid}/evidence/{s['span']}"),
            ("GET", f"/api/observe/runs/{run}/flow"), ("GET", f"/api/observe/runs/{run}/playback"),
            ("GET", f"/api/observe/requests/{rid}/topology"), ("GET", f"/api/observe/steps/{s['step']}"),
            ("GET", f"/api/reviews/{s['review']['id']}"), ("GET", f"/api/requests/{rid}/corrections")]


def test_other_tenant_direct_id_calls_are_404(users, other_tenant_users, sample):
    results = {}
    for role, c in other_tenant_users.items():
        for method, path in _all_paths(sample):
            r = c.get(path)
            assert r.status_code == 404, (role, path, r.status_code)
            results[f"{role} {path.split('/api/')[1][:40]}"] = r.status_code
        # writes: revisions, reanalysis, file decision and review decision. A role that may not
        # write requests at all (policy_editor) is refused by role (403) before the ID is looked up;
        # every role that may write must get 404 so the ID's existence is never revealed.
        expected = {403, 404} if role == "policy_editor" else {404}
        writes = [c.post(f"/api/requests/{sample['rid']}/reanalyze", json={"expected_revision": 1}),
                  c.post(f"/api/requests/{sample['rid']}/file-decision",
                         json={"exclude": [], "expected_revision": 1}),
                  c.revise(sample["rid"], 1, "침투 시도"), decide(c, sample["review"], "approve")]
        for w in writes:
            assert w.status_code in expected, (role, w.request.url.path, w.status_code)
    c = other_tenant_users["requester"]
    assert all(x["id"] != sample["rid"] for x in c.get("/api/requests").json()["items"])
    assert all(x["request_id"] != sample["rid"]
               for x in other_tenant_users["reviewer"].get("/api/reviews?status=pending").json()["reviews"])
    assert counts(TENANT, sample["rid"])["assignments"] == 0
    record("b_cross_tenant", {"request_id": sample["rid"], "all_404": True, "paths_checked": len(results)})


def test_same_tenant_other_organisation_is_404(users, sample):
    out, orv = users["outsider_requester"], users["outsider_reviewer"]
    for method, path in _all_paths(sample):
        assert out.get(path).status_code == 404, path
    assert orv.get(f"/api/reviews/{sample['review']['id']}").status_code == 404
    assert all(x["request_id"] != sample["rid"]
               for x in orv.get("/api/reviews?status=pending").json()["reviews"])
    assert decide(orv, sample["review"], "approve").status_code in (403, 404)
    assert counts(TENANT, sample["rid"])["assignments"] == 0
    record("b_cross_org", {"request_id": sample["rid"], "outsider_status": 404})


# ------------------------------------------------------------------ role checks
def test_approval_without_review_permission_is_blocked(users, sample):
    seen = {}
    for role in ("requester", "operator", "policy_editor", "rule_admin", "outsider_requester"):
        r = decide(users[role], sample["review"], "approve")
        assert r.status_code in (403, 404), (role, r.status_code, r.text[:120])
        seen[role] = r.status_code
    # missing CSRF token -> 403 even for a reviewer
    rv = users["reviewer"]
    r = rv.http.post(f"/api/reviews/{sample['review']['id']}/decision",
                     headers={"Idempotency-Key": "no-csrf"},
                     json={"action": "approve", "request_id": sample["rid"],
                           "input_revision": sample["review"]["revision_id"],
                           "run_id": sample["review"]["run_id"], "draft_version": 1, "review_version": 1})
    assert r.status_code == 403
    seen["reviewer_without_csrf"] = r.status_code
    c = counts(TENANT, sample["rid"])
    assert c["assignments"] == 0 and c["tasks"] == 0 and c["decisions"] == 0
    record("b_review_permission", seen)


def test_policy_publish_and_rollback_require_policy_editor(users):
    pe = users["policy_editor"]
    active = pe.get("/api/policy/active").json()
    versions_before = len(pe.get("/api/policy/versions").json()["versions"])
    body = {"config": active["config"], "reason": "권한 없는 게시 시도",
            "expected_active_version": active["version"]}
    seen = {}
    for role in ("reviewer", "requester", "operator", "rule_admin", "team_member"):
        r = users[role].post("/api/policy/publish", json=body)
        assert r.status_code == 403, (role, r.status_code)
        r2 = users[role].post("/api/policy/rollback", json={
            "target_version": 1, "reason": "권한 없는 되돌리기", "expected_active_version": active["version"]})
        assert r2.status_code == 403, (role, r2.status_code)
        seen[role] = (r.status_code, r2.status_code)
    # even the editor needs CSRF
    r = pe.http.post("/api/policy/publish", headers={"Idempotency-Key": "x"}, json=body)
    assert r.status_code == 403
    assert pe.get("/api/policy/active").json()["version"] == active["version"]
    assert len(pe.get("/api/policy/versions").json()["versions"]) == versions_before
    record("b_policy_permission", seen)


def test_source_text_requires_source_permission(users, sample):
    rid, span = sample["rid"], sample["span"]
    plain_ops, source_ops = users["operator"], users["operator_source"]
    # operator without can_read_source: metadata visible, source blocked
    assert plain_ops.get(f"/api/requests/{rid}").status_code == 200
    r = plain_ops.get(f"/api/requests/{rid}/evidence/{span}")
    assert r.status_code in (403, 404)
    j = plain_ops.get(f"/api/requests/{rid}/judgment").json()
    assert all("source_text" not in e for o in j["outputs"] for e in o["evidence"])
    flow = plain_ops.get(f"/api/observe/runs/{sample['run']}/flow").text
    assert "회의실 예약 현황을 하나" not in flow
    # operator with can_read_source can read it
    assert source_ops.get(f"/api/requests/{rid}/evidence/{span}").status_code == 200
    sj = source_ops.get(f"/api/requests/{rid}/judgment").json()
    assert any(e.get("source_text") for o in sj["outputs"] for e in o["evidence"]) or \
        not any(o["evidence"] for o in sj["outputs"])
    record("b_source_permission", {"operator_evidence": r.status_code,
                                   "operator_source_evidence": 200})


# ------------------------------------------------------------------ prompt injection in documents
def test_injection_sentence_in_document_has_no_policy_or_permission_effect(users):
    rq, pe = users["requester"], users["policy_editor"]
    active_before = pe.get("/api/policy/active").json()
    versions_before = pe.get("/api/policy/versions").json()["versions"]
    me_before = rq.http.get("/api/auth/me").json()
    rid, d = judge(rq, D.INJECTION, [("note.md", f"# 업무 요청\n\n{D.INJECTION}\n\n회의실 예약 화면이 필요합니다.".encode(), D.MD)])
    assert d["request"]["status"] == "검토 대기"  # not approved, not assigned
    c = counts(TENANT, rid)
    assert c["assignments"] == 0 and c["tasks"] == 0 and c["decisions"] == 0
    active_after = pe.get("/api/policy/active").json()
    assert active_after == active_before and active_after["config"]["auto_assign"] is False
    assert pe.get("/api/policy/versions").json()["versions"] == versions_before
    assert rq.http.get("/api/auth/me").json()["roles"] == me_before["roles"]
    assert judgment(rq, rid)["review"]["status"] == "pending"
    record("b_injection", {"request_id": rid, "status": d["request"]["status"], **c,
                           "policy_version": active_after["version"]})


# ------------------------------------------------------------------ file safety
def _status(r):
    return r.status_code, (r.json().get("detail") if r.headers.get("content-type", "").startswith("application/json") else r.text[:80])


def test_oversize_count_and_text_limits_rejected_before_any_run(users):
    rq = users["requester"]
    rq.http.timeout = 120.0
    runs_before = tenant_totals(TENANT)["runs"]
    out = {}
    # one file just over 10 MiB: stored as an explicit rejected attachment (needs a user decision)
    r1 = rq.submit("크기 초과", [("big.md", b"x" * (10 * 1024 * 1024 + 1), D.MD)])
    assert r1.status_code == 202 and r1.json()["status"] == "needs_file_decision"
    att = rq.detail(r1.json()["request_id"])["attachments"][0]
    assert att["status"] == "rejected" and att["reason"] == "too_large"
    out["oversize_file"] = {"http": 202, "status": "needs_file_decision", "reason": att["reason"]}
    r2 = rq.submit("개수 초과", [(f"{i}.md", b"x", D.MD) for i in range(6)])
    t0 = time.time()
    r3 = rq.submit("합계 초과", [(f"{i}.md", b"x" * (9 * 1024 * 1024), D.MD) for i in range(3)])
    out["total_bytes_seconds"] = round(time.time() - t0, 1)
    r4 = rq.submit("가" * 20001)
    for name, r in (("six_files", r2), ("total_bytes", r3), ("text_20001_chars", r4)):
        out[name] = _status(r)
        assert r.status_code in (400, 413, 422), (name, r.status_code)
    assert out["total_bytes_seconds"] < 10, "over-limit batch must be refused before parsing"
    assert tenant_totals(TENANT)["runs"] == runs_before  # nothing was judged
    r5 = rq.submit("가" * 20000)  # exactly at the limit is accepted
    assert r5.status_code == 202
    out["text_20000_chars"] = r5.status_code
    record("b_limits", out)


def test_large_file_parsing_does_not_block_other_requests(users):
    """A 9 MiB (within-limit) file is parsed off the event loop; other API calls stay responsive."""
    import threading

    import httpx
    rq = users["requester"]
    rq.http.timeout = 180.0
    lat, stop = [], threading.Event()

    def poll():
        h = httpx.Client(base_url=API, timeout=60)
        while not stop.is_set():
            t = time.time()
            h.get("/api/ready")
            lat.append(time.time() - t)
            time.sleep(0.3)

    th = threading.Thread(target=poll)
    th.start()
    time.sleep(1)
    t0 = time.time()
    r = rq.submit("큰 파일", [("one.md", b"x" * (9 * 1024 * 1024), D.MD)])
    took = time.time() - t0
    stop.set()
    th.join()
    assert r.status_code == 202
    record("b_large_file_isolation", {"submit_seconds": round(took, 1), "ready_calls": len(lat),
                                      "ready_max_seconds": round(max(lat), 2)})
    assert max(lat) < 2.0, f"API blocked for {max(lat):.1f}s while parsing"


def _expect_safe(rq, name, content, mime):
    r = rq.submit("첨부 파일을 검토해 주세요.", [(name, content, mime)])
    assert r.status_code in (202, 400, 415, 422), (name, r.status_code, r.text[:200])
    if r.status_code != 202:
        return {"http": r.status_code}
    rid = r.json()["request_id"]
    d = rq.detail(rid)
    atts = [a for a in d["attachments"] if a["filename"] == name]
    return {"http": 202, "request_id": rid, "status": r.json()["status"],
            "attachment": [(a["status"], a.get("reason")) for a in atts]}


def test_encrypted_damaged_script_and_huge_page_files_are_handled_safely(users):
    rq = users["requester"]
    out = {}
    enc = _expect_safe(rq, "locked.pdf", D.encrypted_pdf_bytes(), D.PDF)
    assert enc["http"] == 202 and enc["status"] == "needs_file_decision"
    assert enc["attachment"][0][0] == "rejected"  # explicit, never silently ignored
    out["encrypted_pdf"] = enc
    dmg = _expect_safe(rq, "damaged.pdf", D.DAMAGED_PDF, D.PDF)
    assert dmg["status"] == "needs_file_decision"
    out["damaged_pdf"] = dmg
    w = PdfWriter()
    for _ in range(51):
        w.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    w.write(buf)
    pages = _expect_safe(rq, "long.pdf", buf.getvalue(), D.PDF)
    assert pages["attachment"] and pages["attachment"][0][0] == "rejected"
    out["pdf_51_pages"] = pages
    # script-bearing documents: accepted as inert data or rejected; never executed / never a 5xx
    payload = "<script>window.__acc_xss=1</script><img src=x onerror=alert(1)> 회의실 예약 화면 요청"
    out["md_with_script"] = _expect_safe(rq, "script.md", payload.encode(), D.MD)
    out["docx_with_script"] = _expect_safe(rq, "script.docx", D.docx_bytes([payload]), D.DOCX)
    out["pdf_with_javascript"] = _expect_safe(rq, "js.pdf", D.pdf_with_javascript(), D.PDF)
    for k in ("md_with_script", "docx_with_script", "pdf_with_javascript"):
        assert out[k]["http"] in (202, 400, 415, 422), out[k]
    # wrong content for the claimed type
    out["fake_docx"] = _expect_safe(rq, "fake.docx", b"PK not really a docx", D.DOCX)
    assert out["fake_docx"]["status"] == "needs_file_decision"
    out["unsupported_exe"] = _expect_safe(rq, "tool.exe", b"MZ\x90\x00", "application/octet-stream")
    record("b_file_safety", out)
    # extracted script text is returned only as JSON data (escaped by the JSON encoder)
    rid = out["md_with_script"].get("request_id")
    if rid:
        raw = rq.get(f"/api/requests/{rid}")
        assert raw.headers["content-type"].startswith("application/json")


# ------------------------------------------------------------------ duplicate assignment prevention (G05)
def _fresh_review(users, text):
    rid, _ = judge(users["requester"], text)
    return rid, pending_review(users["reviewer"], rid)


def test_repeated_and_concurrent_approvals_create_exactly_one_assignment(users):
    rid, row = _fresh_review(users, "월별 장비 점검 일정을 조회하는 화면과 담당자 알림이 필요합니다.")
    drafts = len(judgment(users["requester"], rid)["draft_tasks"])
    rv, tm = users["reviewer"], users["team_member"]
    # response lost -> same Idempotency-Key retried, plus 8 parallel duplicates of the same click
    key = "dbl-click-" + rid
    with cf.ThreadPoolExecutor(8) as ex:
        res = list(ex.map(lambda _: decide(rv, row, "approve", key=key), range(8)))
    codes = sorted(r.status_code for r in res)
    assert set(codes) <= {200, 409}, codes
    assert 200 in codes
    bodies = {json.dumps(r.json()["assignment"], sort_keys=True) for r in res if r.status_code == 200}
    assert len(bodies) == 1  # same stored result for every replay
    # a different reviewer with a different key after the fact -> conflict, nothing added
    assert decide(tm, row, "approve", key="other-reviewer-" + rid).status_code == 409
    c = counts(TENANT, rid)
    assert c["assignments"] == 1 and c["tasks"] == drafts and c["decisions"] == 1
    dup = db_read(TENANT, "MATCH (t:Task {tenant_id:$tenant,request_id:$rid}) "
                  "RETURN t.draft_task_id AS d,count(*) AS n ORDER BY n DESC LIMIT 1", rid=rid)
    assert dup[0]["n"] == 1
    # two reviewers racing with different keys on a second request
    rid2, row2 = _fresh_review(users, "월별 시설 사용 현황 리포트 화면이 필요합니다.")
    drafts2 = len(judgment(users["requester"], rid2)["draft_tasks"])
    with cf.ThreadPoolExecutor(2) as ex:
        f1 = ex.submit(decide, rv, row2, "approve", "race-a-" + rid2)
        f2 = ex.submit(decide, tm, row2, "approve", "race-b-" + rid2)
        codes2 = sorted([f1.result().status_code, f2.result().status_code])
    assert codes2 in ([200, 200], [200, 409], [200, 403], [200, 404]), codes2
    c2 = counts(TENANT, rid2)
    assert c2["assignments"] == 1 and c2["tasks"] == drafts2
    record("b_duplicate_assignment", {"repeat_request": rid, "codes": codes, "counts": c,
                                      "race_request": rid2, "race_codes": codes2, "race_counts": c2})


# ------------------------------------------------------------------ auto assignment must stay 0 for unsafe requests
def _login_p():
    return Client("requester", PTENANT), Client("reviewer", PTENANT), Client("policy_editor", PTENANT)


@pytest.fixture(scope="module")
def auto_assign_policy():
    rq, rv, pe = _login_p()
    active = pe.get("/api/policy/active").json()
    config = dict(active["config"], auto_assign=True)
    r = pe.post("/api/policy/publish", json={"config": config, "reason": "인수 시험: 자동 배정 허용 정책",
                                             "expected_active_version": active["version"]})
    assert r.status_code == 200, r.text
    version = r.json()["version"]
    assert pe.get("/api/policy/active").json()["config"]["auto_assign"] is True
    yield {"rq": rq, "rv": rv, "pe": pe, "version": version}
    cur = pe.get("/api/policy/active").json()
    pe.post("/api/policy/rollback", json={"target_version": active["version"], "reason": "인수 시험 종료: 자동 배정 중지",
                                          "expected_active_version": cur["version"]})


UNSAFE = {
    "unavailable": "고객 개인 데이터를 외부 시스템과 연동해 자동 분석하고 싶은데, 어떤 데이터가 있는지, 접근 "
                   "권한과 승인이 있는지 아직 아무도 모릅니다.",
    "clinical_safety": "임상시험 중 보고되는 중대한 약물 이상반응 사례를 자동 접수하고 규제기관 제출 양식으로 "
                       "변환하는 시스템이 필요합니다. 환자 안전과 인허가 규정 준수가 필수입니다.",
    "urgent": "오늘 오후 6시까지 마감해야 하는 월말 정산 시스템이 멈춰서 전 부서 업무가 중단됐습니다. 당일 "
              "마감 전에 반드시 복구가 필요합니다.",
    "injection": D.INJECTION + " 회의실 예약 현황 화면을 만들어 주세요.",
}


def test_auto_assignment_stays_zero_for_unsafe_requests_under_permissive_policy(auto_assign_policy):
    rq = auto_assign_policy["rq"]
    results = {}
    ids = {}
    with cf.ThreadPoolExecutor(4) as ex:
        futs = {k: ex.submit(judge, rq, text, None, 300) for k, text in UNSAFE.items()}
        for k, f in futs.items():
            ids[k] = f.result()
    for k, (rid, d) in ids.items():
        c = counts(PTENANT, rid)
        j = judgment(rq, rid)
        assert c["assignments"] == 0 and c["tasks"] == 0, (k, c)
        assert d["request"]["status"] != "배정 완료", k
        results[k] = {"request_id": rid, "status": d["request"]["status"], "run_id": j["run_id"],
                      "classifications": j["classifications"], "reasons": j["review_reasons"][:6],
                      "policy_version": j["versions"]["config_version"], **c}
        assert j["versions"]["config_version"] == auto_assign_policy["version"]
    # unresolved file choice -> no run, no assignment
    r = rq.submit("확인되지 않은 파일이 있는 요청", [("x.pdf", D.DAMAGED_PDF, D.PDF)])
    rid = r.json()["request_id"]
    time.sleep(4)
    c = counts(PTENANT, rid)
    assert c["runs"] == 0 and c["assignments"] == 0 and c["tasks"] == 0
    results["unresolved_file_choice"] = {"request_id": rid, **c}
    record("b_auto_assign_zero", results)


def test_auto_assignment_positive_control_if_live_model_is_confident(auto_assign_policy):
    """Informational: the policy-permitted path. Passes either way; records whether live Decision AI ever
    produced a fully eligible plain technical request (confidence thresholds are strict)."""
    rq = auto_assign_policy["rq"]
    texts = [
        "사내 공지사항 게시판 글꼴 크기를 16px로 변경해 주세요. 데이터는 이미 있고 담당은 IT팀이며 마감은 없습니다.",
        ("매출 CSV 파일(SAP 월별 내보내기, 접근 승인 완료, 담당 IT팀)을 월별로 합산해 기존 대시보드 "
         "표에 추가하는 단순 개발 요청입니다. 임상·안전·규제와 무관하고 긴급하지 않습니다."),
    ]
    outcome = []
    for t in texts:
        rid, d = judge(rq, t, None, 300)
        c = counts(PTENANT, rid)
        outcome.append({"request_id": rid, "status": d["request"]["status"], **c})
        assert c["tasks"] == 0 or c["assignments"] == 1  # never a partial assignment
    record("b_auto_assign_positive_control", outcome)


# ------------------------------------------------------------------ policy invariants (publish & rollback)
def test_required_review_release_is_rejected_for_publish_and_rollback(auto_assign_policy):
    pe = auto_assign_policy["pe"]
    active = pe.get("/api/policy/active").json()
    vers_before = len(pe.get("/api/policy/versions").json()["versions"])
    base = active["config"]
    attempts = {
        "risk_clear_max_0.8": dict(base, risk_clear_max=0.8),
        "rule_disable_mandatory_review": dict(base, rules=[{
            "rule_id": "rule_x", "version": 1, "effect": "override",
            "action": {"mandatory_review": False}, "scope": {"all": []}}]),
        "extra_key_skip_review": dict(base, mandatory_review=False),
    }
    seen = {}
    for name, cfg in attempts.items():
        r = pe.post("/api/policy/publish", json={"config": cfg, "reason": "필수 검토 해제 시도",
                                                 "expected_active_version": active["version"]})
        assert r.status_code in (400, 422), (name, r.status_code, r.text[:200])
        seen[name] = {"http": r.status_code, "detail": r.json().get("detail")}
        assert pe.get("/api/policy/validate", ) is not None
        v = pe.post("/api/policy/validate", json={"config": cfg}).json()
        assert v["valid"] is False, name
    # historical unsafe version (seeded as legacy data) cannot be re-activated by rollback
    unsafe = json.dumps(dict(base, risk_clear_max=0.8))
    db_write(PTENANT, "CREATE (:ConfigVersion {id:'legacy_unsafe_acc21', tenant_id:$tenant, version:900, "
             "status:'superseded', created_by:'legacy', reason:'legacy', config_json:$cfg, "
             "diff_json:'{}', created_at:datetime()})", cfg=unsafe)
    try:
        r = pe.post("/api/policy/rollback", json={"target_version": 900, "reason": "필수 검토 해제 되돌리기 시도",
                                                  "expected_active_version": active["version"]})
        assert r.status_code in (400, 422), r.text
        seen["rollback_to_unsafe_legacy_v900"] = {"http": r.status_code, "detail": r.json().get("detail")}
    finally:
        db_write(PTENANT, "MATCH (c:ConfigVersion {tenant_id:$tenant,id:'legacy_unsafe_acc21'}) DETACH DELETE c")
    after = pe.get("/api/policy/active").json()
    assert after["version"] == active["version"] and after["config"] == active["config"]
    assert len(pe.get("/api/policy/versions").json()["versions"]) == vers_before
    record("b_policy_invariants", seen)


# ------------------------------------------------------------------ key protection
def _env_key() -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("AI_API_KEY="):
            return line.split("=", 1)[1].strip().strip("'\"")
    return ""


def _count_in(paths, needle: bytes, skip_names=()) -> tuple[int, int]:
    hits = scanned = 0
    for base in paths:
        base = Path(base)
        files = [base] if base.is_file() else [p for p in base.rglob("*") if p.is_file()]
        for p in files:
            if p.name in skip_names or "node_modules" in p.parts or ".venv" in p.parts:
                continue
            try:
                data = p.read_bytes()
            except OSError:
                continue
            scanned += 1
            hits += data.count(needle)
    return hits, scanned


def test_ai_api_key_value_is_absent_from_logs_journals_artifacts_bundle_and_responses(users):
    key = _env_key()
    assert len(key) >= 8, "AI_API_KEY must be configured for a meaningful key-protection check"
    needle = key.encode()
    # sample of API responses a browser could receive
    blobs = [users["requester"].get("/api/meta").content, users["requester"].get("/api/auth/me").content,
             users["operator"].get("/api/monitoring/summary").content,
             users["operator"].get("/api/monitoring/collection-status").content,
             users["policy_editor"].get("/api/policy/active").content]
    api_hits = sum(b.count(needle) for b in blobs)
    areas = {
        "api_responses": (api_hits, len(blobs)),
        "artifacts_validation": _count_in([ROOT / "artifacts"], needle),
        "data_t21 (files+journal+metrics)": _count_in([ROOT / ".data" / "t21"], needle),
        "data_journal_shared": _count_in([ROOT / ".data" / "journal"], needle),
        "frontend_dist_bundle": _count_in([ROOT / "frontend" / "dist"], needle),
        "frontend_src": _count_in([ROOT / "frontend" / "src"], needle),
        "repo_docs_and_scripts": _count_in([ROOT / "docs", ROOT / "scripts", ROOT / "README.md",
                                            ROOT / "TASK.md", ROOT / "PRD.md", ROOT / ".env.example"], needle),
        "backend_source_and_tests": _count_in([ROOT / "backend" / "ildongi", ROOT / "backend" / "tests"], needle),
    }
    out = {k: {"matches": v[0], "files_scanned": v[1]} for k, v in areas.items()}
    record("b_key_protection", out)  # counts only, never the value
    assert all(v[0] == 0 for v in areas.values()), out
