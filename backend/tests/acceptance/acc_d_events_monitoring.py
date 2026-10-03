"""G08 (SSE interruption and recovery) and G09 (observation vs. a known request set, error -> Trace, alerts)."""
from __future__ import annotations

import json
import time

import httpx

from tests.acceptance.harness import (
    API,
    TENANT,
    TENANT_F,
    Client,
    db_read,
    judge,
    record,
)


def _read_sse(client: Client, after: int | None, until, max_seconds=90, max_events=500, abort_after=None):
    """Read SSE lines; stops when until(event)->True, after abort_after events (simulated cut), or time."""
    events = []
    params = {"after": after} if after is not None else {}
    cookies = client.http.cookies
    end = time.time() + max_seconds
    with (httpx.Client(base_url=API, cookies=cookies, timeout=httpx.Timeout(10, read=5)) as h,
          h.stream("GET", "/api/events/stream", params=params) as r):
        assert r.status_code == 200
        cur: dict = {}
        try:
            for line in r.iter_lines():
                if time.time() > end:
                    break
                if line == "":
                    if cur.get("event"):
                        events.append(cur)
                        if (until(cur) or (abort_after and len(events) >= abort_after)
                                or len(events) >= max_events):
                            break
                    cur = {}
                elif line.startswith("id: "):
                    cur["id"] = int(line[4:])
                elif line.startswith("event: "):
                    cur["event"] = line[7:]
                elif line.startswith("data: "):
                    cur["data"] = json.loads(line[6:])
        except httpx.ReadTimeout:
            pass
    return events


def _head(c: Client) -> int:
    rows = db_read(TENANT, "OPTIONAL MATCH (c:EventCounter {tenant_id:$tenant}) RETURN coalesce(c.seq,0) AS n")
    return rows[0]["n"]


def test_g08_sse_cut_and_resume_converges_to_persisted_state(users):
    rq = users["requester"]
    cursor = _head(rq)
    r = rq.submit("SSE 복구 확인: 월별 설비 점검 현황 화면이 필요합니다.")
    rid = r.json()["request_id"]
    # connection #1 is cut abruptly after three events
    first = _read_sse(rq, cursor, until=lambda e: False, abort_after=3)
    assert len(first) == 3 and all(e["id"] > cursor for e in first)
    rq.wait(rid)
    time.sleep(3)  # let trailing step events commit
    stored = {row["seq"] for row in db_read(
        TENANT, "MATCH (e:Event {tenant_id:$tenant,request_id:$rid}) RETURN e.seq AS seq", rid=rid)}
    # connection #2 resumes from the last seen id and receives the rest, in order
    resumed = _read_sse(rq, first[-1]["id"], until=lambda e: e["id"] >= max(stored))
    ids = [e["id"] for e in resumed]
    assert ids == sorted(ids) and all(i > first[-1]["id"] for i in ids)
    # replaying the same cursor again delivers identical events (client de-duplicates by id)
    again = _read_sse(rq, first[-1]["id"], until=lambda e: e["id"] >= max(stored))
    assert [e["id"] for e in again] == ids
    merged: dict[int, dict] = {}
    for e in first + resumed + again:
        merged[e["id"]] = e
    mine = [e for e in merged.values() if e["data"].get("request_id") == rid]
    last = [e for e in sorted(mine, key=lambda e: e["id"]) if e["event"] == "judgment_saved"][-1]
    final = rq.detail(rid)["request"]["status"]
    assert last["data"]["status"] == final, (last, final)
    got = {e["id"] for e in mine}
    assert stored == got, (sorted(stored), sorted(got))  # nothing missing, nothing extra
    # a cursor from the future cannot be trusted: server demands a snapshot
    future = _read_sse(rq, _head(rq) + 10_000, until=lambda e: True, max_seconds=15)
    assert future and future[0]["event"] == "snapshot-required"
    snap = rq.get("/api/events/snapshot", params={"request_id": rid}).json()
    assert snap["status"] == final and snap["latest_seq"] >= max(stored)
    record("g08_sse", {"request_id": rid, "first_ids": [e["id"] for e in first], "resumed_ids": ids,
                       "stored_seqs": sorted(stored), "final_status": final,
                       "snapshot": snap, "future_cursor_event": future[0]["event"]})


def test_g08_other_users_events_are_not_delivered(other_tenant_users, users):
    """Foreign tenant stream carries nothing about tenant-A requests."""
    rq_a = users["requester"]
    rid = rq_a.submit("테넌트 경계 확인 요청").json()["request_id"]
    b = other_tenant_users["requester"]
    events = _read_sse(b, 0, until=lambda e: False, max_seconds=8)
    assert all(e["data"].get("request_id") != rid for e in events)
    record("g08_tenant_boundary", {"foreign_request_in_other_tenant_stream": False,
                                   "other_events_seen": len(events)})


# ------------------------------------------------------------------ G09
def _summary(op: Client) -> dict:
    return op.get("/api/monitoring/summary").json()


def _stable_summary(op: Client, predicate, timeout=60):
    end = time.time() + timeout
    s = _summary(op)
    while time.time() < end:
        s = _summary(op)
        if predicate(s):
            return s
        time.sleep(2)
    return s


def test_g09_summary_matches_a_known_request_set(users):
    rq, op = users["requester"], users["operator"]
    base = _summary(op)
    rec0, elig0, within0 = (base["requests"]["received"], base["judgment"]["eligible_requests"],
                            base["judgment"]["within_120s"])
    pre_id0 = base["requests"]["failed_before_id"]
    ids = [judge(rq, f"관측 대조용 요청 {i}: 월별 재고 조회 화면이 필요합니다.")[0] for i in range(3)]
    bad = rq.submit("개수 초과", [(f"{i}.md", b"x", "text/markdown") for i in range(6)])
    assert bad.status_code == 400
    s = _stable_summary(op, lambda x: x["judgment"]["eligible_requests"] >= elig0 + 3
                        and x["requests"]["failed_before_id"] >= pre_id0 + 1)
    d_rec = s["requests"]["received"] - rec0
    d_elig = s["judgment"]["eligible_requests"] - elig0
    d_within = s["judgment"]["within_120s"] - within0
    d_pre = s["requests"]["failed_before_id"] - pre_id0
    assert d_elig == 3 and d_within == 3 and d_pre == 1, (d_elig, d_within, d_pre)
    assert d_rec >= 3
    assert s["judgment"]["failed_120s"] == base["judgment"]["failed_120s"]
    saved = db_read(TENANT, "MATCH (j:Judgment {tenant_id:$tenant}) RETURN count(j) AS n")[0]["n"]
    by_version = sum(v["saved"] for v in s["by_version"].values())
    assert by_version == saved or s["judgment"]["candidate_commits"] >= by_version
    assert s["collection"]["complete"] is True
    record("g09_known_set", {"known_valid_requests": ids, "known_pre_id_rejections": 1,
                             "delta": {"received": d_rec, "eligible": d_elig, "within_120s": d_within,
                                       "failed_before_id": d_pre},
                             "stored_judgments": saved, "summary_saved": by_version,
                             "collection_complete": s["collection"]["complete"]})


def test_g09_failures_lead_to_trace_and_raise_alerts(users):
    """Failed runs (invalid-key worker, tenant <base>f) appear in failures with a Trace link + alert."""
    rq = Client("requester", TENANT_F)
    op = Client("operator", TENANT_F)
    alerts0 = {a["id"] for a in op.get("/api/monitoring/alerts").json()["alerts"]}
    rids = [rq.submit(f"장애 대조 {i}: 월별 판매 화면이 필요합니다.").json()["request_id"] for i in range(3)]
    for rid in rids:
        d = rq.wait(rid, timeout=300, until=lambda x: x["request"]["status"] in ("failed", "실패"))
        assert d["request"]["status"] in ("failed", "실패")
    end = time.time() + 120
    found = []
    while time.time() < end and len(found) < 3:
        fails = op.get("/api/monitoring/failures").json()["causes"]
        found = [row for rows in fails.values() for row in rows if row.get("request_id") in rids]
        time.sleep(3)
    assert {row["request_id"] for row in found} == set(rids), found
    # from the aggregate row to the Trace of exactly that run
    row = found[0]
    run_id = row["run_id"] or op.get(f"/api/requests/{row['request_id']}/runs").json()["runs"][0]["id"]
    flow = op.get(f"/api/observe/runs/{run_id}/flow")
    assert flow.status_code == 200 and any(n["status"] == "failed" for n in flow.json()["nodes"])
    end = time.time() + 120
    new = []
    while time.time() < end and not new:
        new = [a for a in op.get("/api/monitoring/alerts").json()["alerts"] if a["id"] not in alerts0]
        time.sleep(3)
    record("g09_failures_alerts", {"failed_requests": rids, "failures_listed": len(found),
                                   "trace_run": run_id, "new_alerts": [(a["kind"], a["detail"]) for a in new]})
    assert new, "no alert was raised for repeated failures"
