"""Authenticated live load generator; writes only synthetic inputs and timings."""

from __future__ import annotations

import argparse
import asyncio
import csv
import io
import json
import os
import platform
import subprocess
import tempfile
import time
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
from docx import Document
from ildongi.config import get_settings
from ildongi.db.tx import read_tx
from ildongi.ingest.parsers import parse_file
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

KINDS = ("text",) * 10 + ("pdf",) * 5 + ("docx",) * 3 + ("md",) * 2
SENTENCE = "가상 업무 요청: 월별 매출 CSV 집계와 화면 표시를 검토하고 IT팀과 현업의 책임을 정해 주세요. "


class SSERecorder:
    def __init__(self, path: Path):
        self.stream = path.open("w", newline="")
        self.writer = csv.DictWriter(self.stream, fieldnames=["connection", "kind", "at", "status", "cursor", "recovery_ms"])
        self.writer.writeheader()
        self.count = 0

    def append(self, row: dict) -> None:
        self.writer.writerow(row)
        self.count += 1
        if self.count % 1000 == 0:
            self.stream.flush()

    def close(self) -> None:
        self.stream.close()


def utc() -> str:
    return datetime.now(UTC).isoformat()


def samples() -> dict[str, tuple[str, bytes | None, str | None]]:
    normal = (SENTENCE * 4)[:400]
    near = (SENTENCE * 350)[:19_950]
    pdf_buffer = io.BytesIO()
    pdf = canvas.Canvas(pdf_buffer, pagesize=letter, pageCompression=0)
    for line in range(25):
        pdf.drawString(30, 750 - line * 25, f"Synthetic monthly sales summary and dashboard request {line}.")
    pdf.save()
    near_pdf_buffer = io.BytesIO()
    near_pdf = canvas.Canvas(near_pdf_buffer, pagesize=letter, pageCompression=0)
    for page in range(15):
        for line in range(10):
            near_pdf.drawString(30, 750 - line * 25, f"Synthetic monthly sales summary dashboard requirement {page} {line}. " * 2)
        if page == 14:
            noise = Image.frombytes("RGB", (1200, 1200), os.urandom(1200 * 1200 * 3))
            near_pdf.drawImage(ImageReader(noise), 300, 20, width=200, height=200)
        near_pdf.showPage()
    near_pdf.save()
    doc = Document()
    for part in range(20):
        doc.add_paragraph(f"Synthetic sales dashboard requirements paragraph {part}. " * 12)
    doc_buffer = io.BytesIO()
    doc.save(doc_buffer)
    near_doc = Document()
    for part in range(100):
        near_doc.add_paragraph(f"Synthetic sales dashboard requirement {part}. " * 4)
    near_doc_buffer = io.BytesIO()
    near_doc.save(near_doc_buffer)
    return {
        "text": (normal, None, None),
        "text_near": (near, None, None),
        "pdf": (normal, pdf_buffer.getvalue(), "application/pdf"),
        "pdf_near": (normal, near_pdf_buffer.getvalue(), "application/pdf"),
        "docx": (normal, doc_buffer.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        "docx_near": (normal, near_doc_buffer.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        "md": (normal, b"# Synthetic sales dashboard\n" + b"- Monthly CSV summary\n" * 30, "text/markdown"),
        "md_near": (normal, b"# Synthetic sales dashboard\n" + b"- Monthly CSV summary\n" * 350, "text/markdown"),
    }


def validate_samples(inputs: dict) -> dict[str, int]:
    extracted = {}
    with tempfile.TemporaryDirectory(prefix="t25-inputs-") as directory:
        for name, (text, data, media) in inputs.items():
            if data is None:
                extracted[name] = 0
                assert len(text) <= 20_000, name
                continue
            suffix = name.split("_")[0]
            path = Path(directory) / f"synthetic-{name}.{suffix}"
            path.write_bytes(data)
            result = parse_file(path, path.name, media)
            if result.status != "ok" or len(text) + result.char_count > 20_000 or len(data) > 10 * 1024 * 1024:
                raise ValueError(f"unsupported generated input: {name}, status={result.status}, chars={result.char_count}")
            extracted[name] = result.char_count
    return extracted


def manifest(output: Path, args, inputs: dict, extracted: dict) -> None:
    def command(*argv):
        result = subprocess.run(argv, capture_output=True, text=True, check=False)
        return result.stdout.strip()

    sha = command("git", "rev-parse", "HEAD")
    dirty = bool(command("git", "status", "--porcelain"))
    details = {
        "started_at": utc(), "code_sha": sha, "uncommitted": dirty,
        "machine": platform.platform(), "cpu": platform.processor(),
        "logical_cpus": os.cpu_count(), "memory_bytes": command("sysctl", "-n", "hw.memsize"),
        "api_workers": 2, "worker_concurrency": 10, "sse_connections": 20,
        "client_slots": 10, "ai_mode": "live", "model": get_settings().ai_model,
        "duration_seconds": args.duration, "warmup_seconds": args.warmup,
        "target_requests": args.requests,
        "ai_call_cap": args.ai_call_cap,
        "input_bytes": {name: len(data or text.encode()) for name, (text, data, _) in inputs.items()},
        "input_characters": {name: len(text) for name, (text, _, _) in inputs.items()},
        "attachment_extracted_characters": extracted,
        "database": f"dedicated Neo4j 5.26.0, bolt {os.getenv('T25_NEO4J_BOLT_PORT', '7690')}",
    }
    (output / "manifest.json").write_text(json.dumps(details, ensure_ascii=False, indent=2))


async def login(client: httpx.AsyncClient):
    response = await client.post("/api/auth/login", json={"email": "requester@t-alpha.dev", "password": "dev-only-change-me"})
    response.raise_for_status()
    csrf = client.cookies.get("ildongi_csrf")
    if not csrf:
        raise RuntimeError("login did not return CSRF cookie")
    return csrf


async def sse_reader(index: int, base_url: str, cookies: httpx.Cookies, stop: asyncio.Event, rows, latest: dict,
                     reconnect_interval: int):
    cursor = None
    async with httpx.AsyncClient(base_url=base_url, cookies=cookies, timeout=None) as client:
        while not stop.is_set():
            connected = utc()
            reconnect_started = time.monotonic()
            try:
                headers = {"Last-Event-ID": cursor} if cursor else {}
                async with client.stream("GET", "/api/events/stream", headers=headers) as response:
                    rows.append({"connection": index, "kind": "connect", "at": connected, "status": response.status_code, "cursor": cursor})
                    response.raise_for_status()
                    if cursor and latest.get("request_id"):
                        snapshot = await client.get("/api/events/snapshot", params={"request_id": latest["request_id"]})
                        rows.append({"connection": index, "kind": "recovery", "at": utc(),
                                     "status": snapshot.status_code, "cursor": cursor,
                                     "recovery_ms": round((time.monotonic() - reconnect_started) * 1000, 2)})
                    event_id = None
                    async for line in response.aiter_lines():
                        if stop.is_set():
                            break
                        if line.startswith("id:"):
                            event_id = line[3:].strip()
                        elif not line and event_id:
                            cursor = event_id
                            rows.append({"connection": index, "kind": "event", "at": utc(), "status": 200, "cursor": cursor})
                            event_id = None
                        if time.monotonic() - reconnect_started >= reconnect_interval:
                            rows.append({"connection": index, "kind": "forced_reconnect", "at": utc(),
                                         "status": 200, "cursor": cursor})
                            break
            except (httpx.HTTPError, OSError) as exc:
                rows.append({"connection": index, "kind": "disconnect", "at": utc(), "status": type(exc).__name__, "cursor": cursor})
            if not stop.is_set():
                await asyncio.sleep(0.3)


async def run(args) -> None:
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    inputs = samples()
    extracted = validate_samples(inputs)
    manifest(output, args, inputs, extracted)
    client_rows: list[dict] = []
    sse_rows = SSERecorder(output / "sse.csv")
    stop = asyncio.Event()
    limits = httpx.Limits(max_connections=100, max_keepalive_connections=40)
    async with httpx.AsyncClient(base_url=args.base_url, timeout=90, limits=limits) as client:
        csrf = await login(client)
        latest: dict[str, str] = {}
        sse_tasks = [asyncio.create_task(sse_reader(i, args.base_url, client.cookies, stop, sse_rows, latest,
                                                    args.reconnect_interval)) for i in range(20)]
        begin = time.monotonic()
        measure_begin = begin + args.warmup
        end = measure_begin + args.duration
        timing = {"measurement_started_at": (datetime.now(UTC) + timedelta(seconds=args.warmup)).isoformat(),
                  "measurement_ended_at": (datetime.now(UTC) + timedelta(seconds=args.warmup + args.duration)).isoformat()}
        manifest_path = output / "manifest.json"
        manifest_data = json.loads(manifest_path.read_text()) | timing
        manifest_path.write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2))
        counts = Counter()
        number = 0
        stop_reason = None
        estimate = None

        async def usage_count():
            async def query(tx):
                result = await tx.run("MATCH (r:Run {tenant_id:'t-alpha'}) RETURN r.attempts_json AS attempts")
                rows = [row["attempts"] async for row in result]
                calls = errors = input_tokens = output_tokens = 0
                for value in rows:
                    for attempt in json.loads(value or "[]"):
                        usage = attempt.get("usage") or {}
                        calls += int(usage.get("attempts") or 0)
                        input_tokens += int(usage.get("input_tokens") or 0)
                        output_tokens += int(usage.get("output_tokens") or 0)
                        errors += attempt.get("error_class") == "AiRateLimited"
                return {"calls": calls, "rate_limited": errors, "input_tokens": input_tokens,
                        "output_tokens": output_tokens}
            return await read_tx("t-alpha", query)

        async def safety():
            nonlocal stop_reason, estimate
            while time.monotonic() < end and not stop.is_set():
                await asyncio.sleep(10)
                usage = await usage_count()
                (output / "usage_live.json").write_text(json.dumps({"at": utc(), **usage}))
                if estimate is None and time.monotonic() >= measure_begin:
                    estimate = {"warmup_seconds": args.warmup, "completed_requests": len(client_rows),
                                "observed_calls": usage["calls"],
                                "projected_30m_calls": round(usage["calls"] * 1800 / args.warmup),
                                "calls_per_request": usage["calls"] / len(client_rows) if client_rows else None}
                    (output / "warmup_estimate.json").write_text(json.dumps(estimate, indent=2))
                if usage["calls"] >= args.ai_call_cap:
                    stop_reason = f"Decision AI call safety cap ({args.ai_call_cap})"
                elif usage["calls"] and usage["rate_limited"] / usage["calls"] > .05:
                    stop_reason = "Decision AI 429 ratio exceeded 5%"
                if stop_reason:
                    stop.set()
                    break

        safety_task = asyncio.create_task(safety())

        async def producer(slot: int):
            nonlocal number
            while time.monotonic() < end and not stop.is_set():
                current = number
                number += 1
                kind = KINDS[current % len(KINDS)]
                variant = f"{kind}_near" if current % 100 in (0, 10, 15, 18) else kind
                text, file_bytes, media = inputs[variant]
                files = {"files": (f"synthetic-{current}.{kind}", file_bytes, media)} if file_bytes else None
                started = utc()
                clock = time.monotonic()
                row = {"number": current, "slot": slot, "kind": kind, "variant": variant,
                       "phase": "warmup" if clock < measure_begin else "measure",
                       "started_at": started, "input_chars": len(text), "file_bytes": len(file_bytes or b""),
                       "request_id": "", "run_id": "", "status": "", "elapsed_ms": "", "error": ""}
                try:
                    response = await client.post("/api/requests", data={"text": text}, files=files,
                                                 headers={"X-CSRF-Token": csrf, "Idempotency-Key": uuid4().hex})
                    row["status"] = response.status_code
                    if response.status_code == 202:
                        payload = response.json()
                        row["request_id"] = payload.get("request_id", "")
                        row["run_id"] = payload.get("run_id", "")
                        latest["request_id"] = row["request_id"]
                        counts[kind] += 1
                        lookup = await client.get(f"/api/requests/{row['request_id']}")
                        row["lookup_status"] = lookup.status_code
                        deadline = time.monotonic() + 120
                        while time.monotonic() < deadline and not stop.is_set():
                            if lookup.status_code == 200:
                                state = (lookup.json().get("request") or {}).get("status")
                                if state not in ("judgment_pending", "running"):
                                    row["terminal_status"] = state
                                    break
                            await asyncio.sleep(1)
                            lookup = await client.get(f"/api/requests/{row['request_id']}")
                            row["lookup_status"] = lookup.status_code
                        row["judgment_wait_ms"] = round((time.monotonic() - clock) * 1000, 2)
                    else:
                        row["error"] = response.text[:200]
                except Exception as exc:  # noqa: BLE001 - one failed virtual user is a measured sample
                    row["error"] = type(exc).__name__
                row["elapsed_ms"] = round((time.monotonic() - clock) * 1000, 2)
                row["ended_at"] = utc()
                client_rows.append(row)

        await asyncio.gather(*(producer(i) for i in range(10)))
        stop.set()
        await safety_task
        await asyncio.sleep(args.settle)  # Include terminal 120-second failure observations in the gate run.
        await asyncio.gather(*sse_tasks, return_exceptions=True)
    sse_rows.close()
    for name, rows in (("client.csv", client_rows),):
        if rows:
            with (output / name).open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=sorted({key for row in rows for key in row}))
                writer.writeheader()
                writer.writerows(rows)
    (output / "run.json").write_text(json.dumps({"ended_at": utc(), "accepted_by_kind": counts,
                                                   "attempted": len(client_rows), "sse_rows": sse_rows.count,
                                                   "stop_reason": stop_reason, "warmup_estimate": estimate}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--duration", type=int, default=1800)
    parser.add_argument("--warmup", type=int, default=300)
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--settle", type=int, default=120)
    parser.add_argument("--reconnect-interval", type=int, default=60)
    parser.add_argument("--ai-call-cap", type=int, default=25_000)
    asyncio.run(run(parser.parse_args()))
