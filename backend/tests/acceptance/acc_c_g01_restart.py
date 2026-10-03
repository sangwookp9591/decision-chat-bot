"""C) G01: README start + intake + lookup, and persistence across API/worker restarts.

Needs the runtime started by env.sh (ACC_ENV_OUT = its run directory) so processes can be restarted.
"""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import httpx
import pytest

from tests.acceptance.harness import (
    API,
    TENANT,
    counts,
    judge,
    judgment,
    pending_review,
    record,
    tasks_of,
)

ROOT = Path(__file__).resolve().parents[3]
ENV_OUT = os.environ.get("ACC_ENV_OUT")
ENV_SH = ROOT / "backend" / "tests" / "acceptance" / "env.sh"
needs_env = pytest.mark.skipif(not ENV_OUT, reason="ACC_ENV_OUT not set (runtime not started via env.sh)")


def _env(cmd: str) -> None:
    subprocess.run(["bash", str(ENV_SH), cmd, ENV_OUT], check=True, cwd=ROOT,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _wait_ready(timeout=60):
    end = time.time() + timeout
    while time.time() < end:
        try:
            if httpx.get(f"{API}/api/ready", timeout=3).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise TimeoutError("API not ready after restart")


def test_g01_readme_start_health_ready_meta_intake_and_lookup(users):
    assert httpx.get(f"{API}/api/health", timeout=5).status_code == 200
    ready = httpx.get(f"{API}/api/ready", timeout=5).json()
    assert ready["status"] == "ready"
    meta = httpx.get(f"{API}/api/meta", timeout=5).json()
    assert meta["mode"] == "live" and meta["limits"]["attachments"] == 5
    rq = users["requester"]
    rid, d = judge(rq, "README 절차 확인용: 월별 매출 요약 화면이 필요합니다.")
    assert rq.detail(rid)["request"]["id"] == rid
    assert any(x["id"] == rid for x in rq.get("/api/requests").json()["items"])
    record("g01_basic", {"health": 200, "ready": ready, "mode": meta["mode"], "request_id": rid,
                         "status": d["request"]["status"]})


def _snapshot(users, rid, review_id=None):
    rq, rv = users["requester"], users["reviewer"]
    d = rq.detail(rid)
    j = judgment(rq, rid)
    snap = {
        "status": d["request"]["status"], "revision": d["request"]["revision_number"],
        "judgment_id": j["id"], "run_id": j["run_id"], "classifications": j["classifications"],
        "versions": j["versions"], "outputs": sorted((o["id"], o["value"]) for o in j["outputs"]),
        "tasks": sorted((t["id"], t["title"], t["status"], t["lead_org"]) for t in tasks_of(rv, rid)),
        "flow": [(n["id"], n["status"]) for n in rq.get(
            f"/api/observe/runs/{j['run_id']}/flow").json()["nodes"]],
        "topology": sorted((e["from"], e["to"], e["kind"]) for e in rq.get(
            f"/api/observe/requests/{rid}/topology").json()["edges"]),
        "pending_reviews": sorted(r["id"] for r in rv.get("/api/reviews?status=pending").json()["reviews"]
                                  if r["request_id"] == rid),
        "counts": counts(TENANT, rid),
    }
    return snap


@needs_env
def test_g01_request_review_task_and_trace_survive_api_and_worker_restart(users):
    rq, rv = users["requester"], users["reviewer"]
    # one assigned request (tasks + topology) and one waiting for review
    a_rid, _ = judge(rq, "고객 문의 분류와 답변 초안을 만드는 AI 기능, 사내 시스템 연동, 현업 승인 기준이 필요합니다.")
    from tests.acceptance.harness import decide
    assert decide(rv, pending_review(rv, a_rid), "approve").status_code == 200
    p_rid, _ = judge(rq, "신규 입사자 온보딩 체크리스트 화면이 필요합니다.")
    pending_review(rv, p_rid)
    before = {a_rid: _snapshot(users, a_rid), p_rid: _snapshot(users, p_rid)}
    _env("restart-api")
    _env("restart-worker")
    _wait_ready()
    after = {a_rid: _snapshot(users, a_rid), p_rid: _snapshot(users, p_rid)}  # same sessions still valid
    assert after == before
    # the system keeps working: a decision after restart and a brand-new intake
    row = pending_review(rv, p_rid)
    assert decide(rv, row, "reject", reason="재시작 후 반려 확인").status_code == 200
    assert counts(TENANT, p_rid)["status"] == "반려"
    rid, d = judge(rq, "재시작 이후 접수: 월별 재고 조회 화면이 필요합니다.")
    assert d["request"]["status"] in ("검토 대기", "배정 완료", "auto_assign_eligible")
    record("g01_restart", {"assigned_request": a_rid, "pending_request": p_rid,
                           "identical_after_restart": True,
                           "compared": sorted(before[a_rid]), "new_request_after_restart": rid})


@needs_env
def test_g01_worker_restart_while_judging_completes_exactly_once(users):
    rq = users["requester"]
    r = rq.submit("처리 중 재시작 확인: 월별 설비 점검 화면과 알림이 필요합니다.")
    rid = r.json()["request_id"]
    _env("restart-worker")  # killed while the job is queued or running; lease takeover must finish it
    d = rq.wait(rid, timeout=300)
    assert d["request"]["status"] not in ("judgment_pending", "received")
    c = counts(TENANT, rid)
    assert c["judgments"] == 1 and c["assignments"] == 0
    record("g01_worker_restart_inflight", {"request_id": rid, **c})
