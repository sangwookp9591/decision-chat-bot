"""Calculate the development gate from the same collector aggregate definitions."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

from jevtriage.db.tx import read_tx
from jevtriage.journal.collector import collect_once, connect
from jevtriage.monitoring.aggregates import (
    collection_status,
    percentile,
    summarize,
)


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


async def run(output: Path) -> None:
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    data_dir = output / "data"
    collect_once(data_dir)
    start = datetime.fromisoformat(manifest["measurement_started_at"]).astimezone(UTC)
    end = datetime.fromisoformat(manifest["measurement_ended_at"]).astimezone(UTC)
    with closing(connect(data_dir)) as db:
        rows = [json.loads(record[0]) for record in db.execute(
            "SELECT payload FROM events WHERE kind <> 'sse_deliver' AND ts>=? AND ts<=?",
            (start.isoformat(), (end + timedelta(seconds=125)).isoformat()))]
        sse_durations = [float(record[0]) for record in db.execute(
            "SELECT duration_ms FROM events WHERE kind='sse_deliver' AND ts>=? AND ts<=? AND duration_ms IS NOT NULL",
            (start.isoformat(), end.isoformat()))]
    client = [r for r in read_csv(output / "client.csv") if r["phase"] == "measure"]
    sse_path = output / "sse.csv"
    run_status = json.loads((output / "run.json").read_text())
    request_ids = {r["request_id"] for r in client if r["request_id"]}
    relevant = [r for r in rows if r.get("request_id") in request_ids or
                (r.get("kind") in {"request_received", "request_failed", "request_completed", "lookup_received", "lookup_failed", "lookup_completed"}
                 and start <= datetime.fromisoformat(r["ts"]).astimezone(UTC) <= end)]
    summary = summarize(relevant, now=end + timedelta(seconds=125))
    summary["latency_ms"]["sse_deliver_p95"] = percentile(sse_durations, .95)

    async def query(tx):
        result = await tx.run(
            "MATCH (r:Run {tenant_id:'t-alpha'}) WHERE r.request_id IN $ids "
            "OPTIONAL MATCH (s:RunStep {tenant_id:'t-alpha',run_id:r.id}) "
            "RETURN r.id AS run_id,r.request_id AS request_id,r.status AS status,"
            "r.versions_json AS versions,r.attempts_json AS attempts,"
            "collect({name:s.name,kind:s.kind,status:s.status,ended_at:s.ended_at,"
            "versions:s.versions_json,predecessors:s.predecessor_ids}) AS steps",
            ids=list(request_ids),
        )
        return [dict(row) async for row in result]

    runs = await read_tx("t-alpha", query)
    (output / "runs.json").write_text(json.dumps(runs, default=str, ensure_ascii=False))
    usage = Counter()
    trace_ok = trace_total = 0
    for run in runs:
        for attempt in json.loads(run.get("attempts") or "[]"):
            entry = attempt.get("usage") or {}
            for key in ("attempts", "input_tokens", "output_tokens"):
                usage[key] += int(entry.get(key) or 0)
            if attempt.get("error_class") == "JevRateLimited":
                usage["rate_limited_final_errors"] += 1
            if str(attempt.get("error_class") or "").startswith(("TypeSafe", "Jev")):
                usage["failed_external_attempts"] += 1
        if run["status"] in {"judgment_saved", "failed", "cancelled"}:
            trace_total += 1
            steps = [s for s in run["steps"] if s["name"]]
            versions = json.loads(run.get("versions") or "{}")
            expected = {"입력 정리", "Jev 판단", "근거 연결", "업무 분해", "규칙 적용", "자동 배정 조건 검사", "결과 저장"}
            has_terminal = (run["status"] != "judgment_saved" or expected.issubset({s["name"] for s in steps}))
            if (steps and has_terminal and versions.get("model") and
                    all(s["kind"] and s["status"] in {"succeeded", "failed", "skipped", "waiting_human"}
                        and s["ended_at"] and s["versions"] for s in steps)):
                trace_ok += 1
    availability = summary["availability"]
    judgment = summary["judgment"]
    latency = summary["latency_ms"]
    recovery = []
    sse_connected = set()
    with sse_path.open(newline="") as stream:
        for r in csv.DictReader(stream):
            if r["kind"] == "connect" and r["status"] == "200":
                sse_connected.add(int(r["connection"]))
            if (r["kind"] == "recovery" and r.get("recovery_ms") and r["status"] == "200"
                    and start <= datetime.fromisoformat(r["at"]).astimezone(UTC) <= end):
                recovery.append(float(r["recovery_ms"]))
    kind_counts = Counter(r["kind"] for r in client if r["status"] == "202")
    tests = {
        "duration_30m": (end - start).total_seconds() >= 1800 and not run_status.get("stop_reason")
        and datetime.fromisoformat(run_status["ended_at"]).astimezone(UTC) >= end,
        "accepted_200": sum(kind_counts.values()) >= 200,
        "virtual_users_10": {int(r["slot"]) for r in client} == set(range(10)),
        "mix_50_25_15_10": all(kind_counts.get(kind, 0) / max(sum(kind_counts.values()), 1) >= target - .02
                                  for kind, target in {"text": .5, "pdf": .25, "docx": .15, "md": .10}.items()),
        "sse_20": len(sse_connected) == 20,
        "availability_99_9": availability["ratio"] is not None and availability["ratio"] >= .999,
        "judgment_99": judgment["ratio"] is not None and judgment["ratio"] >= .99 and not judgment["pending_120s"],
        "intake_p95_2s": latency["intake_p95"] is not None and latency["intake_p95"] <= 2000,
        "text_p95_15s": latency["text_first_p95"] is not None and latency["text_first_p95"] <= 15000,
        "attachment_p95_45s": latency["attachment_first_p95"] is not None and latency["attachment_first_p95"] <= 45000,
        "sse_deliver_p95_2s": latency["sse_deliver_p95"] is not None and latency["sse_deliver_p95"] <= 2000,
        "sse_recovery_p95_5s": percentile(recovery, .95) is not None and percentile(recovery, .95) <= 5000,
        "trace_100": trace_total > 0 and trace_ok == trace_total,
    }
    result = {"tests": tests, "passed": sum(tests.values()), "total": len(tests),
              "accepted_by_kind": dict(kind_counts), "availability": availability,
              "judgment": judgment, "latency_ms": latency,
              "step_latency": summary["steps"], "failure_causes": summary["failures"],
              "journal_kinds": summary["kinds"],
              "sse_recovery": {"samples": len(recovery), "p95_ms": percentile(recovery, .95)},
              "trace": {"complete": trace_ok, "terminal": trace_total},
              "usage": dict(usage), "collector": collection_status(data_dir),
              "warmup_estimate": json.loads((output / "warmup_estimate.json").read_text()) if (output / "warmup_estimate.json").exists() else None,
              "stop_reason": run_status.get("stop_reason")}
    (output / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    manifest["measured_jev_calls_reported_by_successful_runs"] = usage["attempts"]
    manifest["failed_external_attempts"] = usage["failed_external_attempts"]
    manifest["jev_calls_inferred_from_run_attempts"] = usage["attempts"] + usage["failed_external_attempts"]
    manifest["input_tokens_recorded"] = usage["input_tokens"]
    manifest["output_tokens_recorded"] = usage["output_tokens"]
    manifest["run_versions"] = sorted({run["versions"] for run in runs if run.get("versions")})
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    lines = ["# T25 개발 부하 시험", "", f"기간: {start.isoformat()}–{end.isoformat()}",
             f"판정: {result['passed']}/{result['total']} 통과", "",
             "| 지표 | 결과 | 판정 |", "| --- | --- | --- |"]
    values = {"accepted_200": sum(kind_counts.values()), "availability_99_9": availability["ratio"],
              "judgment_99": judgment["ratio"], "intake_p95_2s": latency["intake_p95"],
              "text_p95_15s": latency["text_first_p95"], "attachment_p95_45s": latency["attachment_first_p95"],
              "sse_deliver_p95_2s": latency["sse_deliver_p95"],
              "sse_recovery_p95_5s": percentile(recovery, .95), "trace_100": f"{trace_ok}/{trace_total}"}
    for key, passed in tests.items():
        lines.append(f"| {key} | {values.get(key, '')} | {'통과' if passed else '미달/미검증'} |")
    lines.extend(["", "## 분모와 예산", "",
                  f"접수·조회 유효 호출 {availability['valid_calls']}건, 실패 {availability['failed_calls']}건, 미확정 {availability['unknown_validity']}건.",
                  f"최초 적격 요청 {judgment['eligible_requests']}건, 120초 내 저장 {judgment['within_120s']}건, 120초 실패 {judgment['failed_120s']}건.",
                  f"Jev 호출 추정 {usage['attempts'] + usage['failed_external_attempts']}회(성공 실행 기록 {usage['attempts']}회 + 외부 오류 종료 {usage['failed_external_attempts']}회), 입력 {usage['input_tokens']}토큰, 출력 {usage['output_tokens']}토큰. 실패 호출의 usage와 복구된 429의 개별 상태는 제품 기록에서 확인할 수 없다.",
                  f"중단 사유: {result['stop_reason'] or '없음'}."])
    (output / "REPORT.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    import asyncio
    asyncio.run(run(parser.parse_args().output))
