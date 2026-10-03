"""Lease-backed async Job worker. Run with ``python -m jevtriage.jobs.worker``."""

import argparse
import asyncio
import json
import os
import signal
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime
from uuid import uuid4

from jevtriage.config import get_settings
from jevtriage.db.events import append_event_in_tx
from jevtriage.db.jobs import OwnershipLost, claim_or_takeover, heartbeat, verify_owner_in_tx
from jevtriage.db.locks import lock_node_in_tx
from jevtriage.db.requests import StaleRun, assert_active_run_in_tx
from jevtriage.db.tx import read_tx, write_tx
from jevtriage.domain.ids import new_id
from jevtriage.journal.reader import producer_heartbeat
from jevtriage.journal.writer import JournalWriter, failure_count
from jevtriage.observe.trace_store import finish_step_in_tx, start_step_in_tx

Handler = Callable[["JobContext"], Awaitable[None]]
HANDLERS: dict[str, Handler] = {}
STEP_KINDS = {"ai", "code", "rule", "external", "human"}


def register(kind: str, handler: Handler) -> None:
    if not kind or kind in HANDLERS:
        raise ValueError("handler kind absent or already registered")
    HANDLERS[kind] = handler


def _utc_now():
    return datetime.now(UTC).isoformat()


class JobContext:
    def __init__(self, *, tenant_id, job_id, run_id, request_id, revision_id,
                 owner_id, generation, attempt_id, versions, journal, lost):
        self.tenant_id = tenant_id
        self.job_id = job_id
        self.run_id = run_id
        self.request_id = request_id
        self.revision_id = revision_id
        self.owner_id = owner_id
        self.generation = generation
        self.attempt_id = attempt_id
        self.versions = versions
        self.run_kind = "normal"
        self.org_ids: tuple[str, ...] = ()
        self.journal = journal
        self.lost = lost
        self.usage: dict = {}

    def record_usage(self, **usage):
        self.usage.update(usage)

    def _journal(self, kind, *, status, duration_ms=None, error_class=None, step_name=None,
                 ts_override=None, complete_judgment=False):
        try:
            self.journal.append({
                "event_id": new_id("event"), "attempt_id": self.attempt_id,
                "request_id": self.request_id, "run_id": self.run_id,
                "kind": kind, "ts": ts_override or _utc_now(), "status_code": status,
                "duration_ms": duration_ms, "error_class": error_class,
                "tenant_id": self.tenant_id, "revision_id": self.revision_id,
                "org_ids": list(self.org_ids),
                "run_kind": self.run_kind,
                "config_version": self.versions.get("config"),
                "model_version": self.versions.get("model"),
                "qset_version": self.versions.get("qset"),
                "complete_judgment": complete_judgment,
                "step_name": step_name,
            })
        finally:
            producer_heartbeat(get_settings().data_dir, "worker", failure_count())

    async def commit(self, fn, *, affects_request=False):
        """Execute a formal write only while this generation still owns the Job."""
        if self.lost.is_set():
            raise OwnershipLost("heartbeat failed or ownership lost")

        async def op(tx):
            # Request precedes Job in the global lock order.
            if affects_request:
                await assert_active_run_in_tx(
                    tx, self.tenant_id, self.request_id, self.run_id, self.revision_id,
                )
            await lock_node_in_tx(tx, self.tenant_id, "Run", self.run_id)
            await verify_owner_in_tx(tx, self.tenant_id, self.job_id,
                                     self.owner_id, self.generation)
            return await fn(tx)

        try:
            return await write_tx(self.tenant_id, op)
        except OwnershipLost:
            self.lost.set()
            raise

    @asynccontextmanager
    async def step(self, name: str, *, kind: str = "code", actor: str | None = None,
                   parent_step_id: str | None = None, predecessor_ids=(),
                   input_summary=None, output_summary=None,
                   completion_status="succeeded"):
        if kind not in STEP_KINDS:
            raise ValueError("invalid step kind")
        if completion_status not in {"succeeded", "skipped", "waiting_human"}:
            raise ValueError("invalid completion status")
        async def start(tx):
            created_id = await start_step_in_tx(
                tx, tenant_id=self.tenant_id, run_id=self.run_id, name=name, kind=kind,
                actor=actor or self.owner_id, versions=self.versions,
                attempt_id=self.attempt_id, parent_step_id=parent_step_id,
                predecessor_ids=predecessor_ids, input_summary=input_summary,
            )
            await append_event_in_tx(
                tx, self.tenant_id, "run.step",
                {"status": "running", "step_name": name, "kind": kind},
                request_id=self.request_id, run_id=self.run_id,
            )
            return created_id

        step_id = await self.commit(start)
        started = asyncio.get_running_loop().time()
        try:
            yield step_id
        except BaseException as exc:
            error_class = type(exc).__name__
            elapsed_ms = round((asyncio.get_running_loop().time() - started) * 1000)
            if isinstance(exc, OwnershipLost) or self.lost.is_set():
                self._journal("ownership_lost", status="lost", duration_ms=elapsed_ms,
                              error_class=error_class)
            else:
                self._journal("worker_step", status="failed", duration_ms=elapsed_ms,
                              error_class=error_class, step_name=name)
                async def finish_failed(tx):
                    result = await finish_step_in_tx(
                        tx, tenant_id=self.tenant_id, step_id=step_id,
                        status="failed", error_class=error_class,
                        output_summary=output_summary,
                    )
                    await append_event_in_tx(
                        tx, self.tenant_id, "run.step",
                        {"status": "failed", "step_name": name, "kind": kind},
                        request_id=self.request_id, run_id=self.run_id,
                    )
                    return result

                await self.commit(finish_failed)
            raise
        else:
            try:
                async def finish(tx):
                    result = await finish_step_in_tx(
                        tx, tenant_id=self.tenant_id, step_id=step_id,
                        status=completion_status, output_summary=output_summary,
                    )
                    await append_event_in_tx(
                        tx, self.tenant_id, "run.step",
                        {"status": completion_status, "step_name": name, "kind": kind},
                        request_id=self.request_id, run_id=self.run_id,
                    )
                    return result

                duration = await self.commit(finish)
            except OwnershipLost:
                self._journal("ownership_lost", status="lost",
                              duration_ms=round((asyncio.get_running_loop().time() - started) * 1000),
                              error_class="OwnershipLost")
                raise
            self._journal("worker_step", status=completion_status, duration_ms=duration,
                          step_name=name)


class Worker:
    def __init__(self, *, concurrency=2, lease_seconds=15.0, poll_seconds=0.5,
                 deadline_seconds=120.0, max_attempts=3, owner_id=None, journal=None,
                 handlers=None, tenants=None):
        if min(concurrency, lease_seconds, poll_seconds, deadline_seconds, max_attempts) <= 0:
            raise ValueError("worker settings must be positive")
        self.owner_id = owner_id or f"worker_{uuid4().hex}"
        self.concurrency = concurrency
        self.lease_seconds = lease_seconds
        self.poll_seconds = poll_seconds
        self.deadline_seconds = deadline_seconds
        self.max_attempts = max_attempts
        self.journal = journal or JournalWriter()
        self.handlers = handlers if handlers is not None else HANDLERS
        self.tenants = frozenset(tenants or ())
        self.stopping = asyncio.Event()
        self.tasks: set[asyncio.Task] = set()
        self.active_jobs: set[str] = set()
        self._last_producer_heartbeat = 0.0

    async def candidates(self):
        # Discovery is intentionally cross-tenant; each mutation below is tenant scoped.
        async def op(tx):
            rows = await tx.run(
                "MATCH (j:Job) WHERE (size($tenants)=0 OR j.tenant_id IN $tenants) AND "
                "(j.status = 'pending' OR (j.status = 'running' AND j.lease_expires_at <= datetime())) "
                "RETURN j.id AS job_id, j.tenant_id AS tenant_id "
                "ORDER BY j.created_at LIMIT $limit",
                limit=max(10, self.concurrency * 4), tenants=list(self.tenants),
            )
            return [dict(row) async for row in rows]
        return await read_tx("worker-discovery", op)

    async def _load(self, tenant_id, job_id):
        async def op(tx):
            result = await tx.run(
                "MATCH (j:Job {tenant_id: $tenant_id, id: $job_id}) "
                "MATCH (r:Run {tenant_id: $tenant_id, id: j.run_id}) "
                "OPTIONAL MATCH (q:Request {tenant_id:$tenant_id,id:r.request_id}) "
                "RETURN j, r, q.org_ids AS org_ids",
                tenant_id=tenant_id, job_id=job_id,
            )
            row = await result.single()
            return (dict(row["j"]), dict(row["r"]), tuple(row["org_ids"] or ())) if row else None
        return await read_tx(tenant_id, op)

    async def _begin_attempt(self, job, run, generation):
        tenant_id, job_id, run_id = job["tenant_id"], job["id"], run["id"]
        attempt_id = new_id("attempt")

        async def op(tx):
            await lock_node_in_tx(tx, tenant_id, "Run", run_id)
            await verify_owner_in_tx(tx, tenant_id, job_id, self.owner_id, generation)
            result = await tx.run(
                "MATCH (r:Run {tenant_id: $tenant_id, id: $run_id}) RETURN r",
                tenant_id=tenant_id, run_id=run_id,
            )
            row = await result.single(strict=True)
            current = dict(row["r"])
            attempts = json.loads(current.get("attempts_json") or "[]")
            now = _utc_now()
            for item in attempts:
                if item["status"] == "running":
                    item.update(status="interrupted", ended_at=now, error_class="LeaseExpired")
            count = len(attempts) + 1
            started = current.get("started_at") or current.get("created_at")
            elapsed = 0.0
            if started:
                started = started.to_native() if hasattr(started, "to_native") else started
                elapsed = (datetime.now(UTC) - started.astimezone(UTC)).total_seconds()
            deadline = current.get("deadline_seconds") or self.deadline_seconds
            expired = elapsed >= deadline or count > self.max_attempts
            if current.get("status") in {"failed", "cancelled", "judgment_saved"}:
                raise ValueError("run already terminal")
            versions = json.loads(current.get("versions_json") or "{}")
            if not versions:
                versions = {"policy": current.get("policy_version"),
                            "config": current.get("config_version"),
                            "model": current.get("model_version"),
                            "qset": current.get("qset_version"),
                            "schema": current.get("schema_version"),
                            "catalog": current.get("catalog_version")}
            attempts.append({"attempt_id": attempt_id, "generation": generation,
                             "started_at": now, "status": "running", "usage": {}})
            await (await tx.run(
                "MATCH (s:RunStep {tenant_id: $tenant_id, run_id: $run_id, status: 'running'}) "
                "WHERE s.attempt_id <> $attempt_id "
                "WITH s, datetime() AS ended "
                "SET s.status = 'failed', s.error_class = 'LeaseExpired', "
                "s.ended_at = ended, "
                "s.duration_ms = ended.epochMillis - s.started_at.epochMillis",
                tenant_id=tenant_id, run_id=run_id, attempt_id=attempt_id,
            )).consume()
            await (await tx.run(
                "MATCH (r:Run {tenant_id: $tenant_id, id: $run_id}) "
                "SET r.status = 'running', r.started_at = coalesce(r.started_at, datetime()), "
                "r.deadline_seconds = coalesce(r.deadline_seconds, $deadline), "
                "r.versions_json = coalesce(r.versions_json, $versions), "
                "r.attempts_json = $attempts, r.attempt_count = $count",
                tenant_id=tenant_id, run_id=run_id, deadline=deadline,
                versions=json.dumps(versions), attempts=json.dumps(attempts), count=count,
            )).consume()
            return attempt_id, versions, expired, max(0.0, deadline - elapsed), count

        return await write_tx(tenant_id, op)

    async def _finish(self, ctx, status, error_class=None):
        deadline_failure = status == "failed" and error_class in {
            "DeadlineExceeded", "MaxAttemptsExceeded"
        }

        async def op(tx):
            result = await tx.run(
                "MATCH (r:Run {tenant_id: $tenant_id, id: $run_id}) RETURN r",
                tenant_id=ctx.tenant_id, run_id=ctx.run_id,
            )
            run = dict((await result.single(strict=True))["r"])
            if run["status"] in {"failed", "cancelled", "judgment_saved"}:
                raise ValueError("run already terminal")
            attempts = json.loads(run["attempts_json"])
            attempt = next(item for item in attempts if item["attempt_id"] == ctx.attempt_id)
            ended = _utc_now()
            attempt.update(status=status, ended_at=ended, error_class=error_class,
                           usage=ctx.usage)
            result = await tx.run(
                "MATCH (r:Run {tenant_id: $tenant_id, id: $run_id}) "
                "MATCH (j:Job {tenant_id: $tenant_id, id: $job_id}) "
                "WITH r, j, datetime() AS ended "
                "SET r.status = $status, r.ended_at = ended, "
                "r.duration_ms = ended.epochMillis - r.started_at.epochMillis, "
                "r.error_class = $error_class, r.attempts_json = $attempts, "
                "j.status = CASE WHEN $status = 'judgment_saved' THEN 'completed' ELSE 'failed' END "
                "RETURN r.duration_ms AS duration_ms",
                tenant_id=ctx.tenant_id, run_id=ctx.run_id, job_id=ctx.job_id,
                status=status, error_class=error_class, attempts=json.dumps(attempts),
            )
            duration_ms = (await result.single(strict=True))["duration_ms"]
            if deadline_failure and update_request:
                await (await tx.run(
                    "MATCH (q:Request {tenant_id:$tenant_id,id:$request_id,active_run_id:$run_id}) "
                    "SET q.status='실패'",
                    tenant_id=ctx.tenant_id, request_id=ctx.request_id, run_id=ctx.run_id,
                )).consume()
                await append_event_in_tx(
                    tx, ctx.tenant_id, "judgment_failed",
                    {"error_class": error_class},
                    request_id=ctx.request_id, run_id=ctx.run_id,
                )
            return duration_ms, str(run["first_judgment_committed_at"]) if run.get("first_judgment_committed_at") else None

        update_request = deadline_failure
        if deadline_failure:
            try:
                duration, committed_at = await ctx.commit(op, affects_request=True)
            except StaleRun:
                update_request = False
                duration, committed_at = await ctx.commit(op)
        else:
            duration, committed_at = await ctx.commit(op)
        ctx._journal("worker_run", status=status, duration_ms=duration,
                     error_class=error_class)
        if committed_at:
            ctx._journal("judgment_committed", status="committed", ts_override=committed_at,
                         complete_judgment=True)

    async def _heartbeat(self, ctx, handler_task):
        try:
            while not ctx.lost.is_set():
                await asyncio.sleep(self.lease_seconds / 3)
                await heartbeat(ctx.tenant_id, ctx.job_id, ctx.owner_id,
                                ctx.generation, self.lease_seconds)
                producer_heartbeat(get_settings().data_dir, "worker", failure_count())
        except Exception as exc:  # noqa: BLE001 - every heartbeat failure invalidates ownership
            ctx.lost.set()
            ctx._journal("ownership_lost", status="lost", error_class=type(exc).__name__)
            handler_task.cancel()

    async def process_job(self, tenant_id, job_id):
        generation = await claim_or_takeover(tenant_id, job_id, self.owner_id,
                                             self.lease_seconds)
        pair = await self._load(tenant_id, job_id)
        if pair is None:
            raise LookupError("claimed job has no run")
        job, run, org_ids = pair
        attempt_id, versions, expired, remaining, _ = await self._begin_attempt(job, run, generation)
        ctx = JobContext(
            tenant_id=tenant_id, job_id=job_id, run_id=run["id"],
            request_id=run["request_id"], revision_id=run["input_revision_id"],
            owner_id=self.owner_id, generation=generation, attempt_id=attempt_id,
            versions=versions, journal=self.journal, lost=asyncio.Event(),
        )
        ctx.run_kind = run.get("kind") or "normal"
        ctx.org_ids = org_ids
        ctx._journal("worker_attempt_start", status="running")
        beat = asyncio.create_task(self._heartbeat(ctx, asyncio.current_task()))
        try:
            if expired:
                await self._finish(ctx, "failed", "DeadlineExceeded" if remaining <= 0 else "MaxAttemptsExceeded")
                return
            kind = job.get("kind") or run.get("job_kind") or (
                "judgment" if run.get("kind") == "normal" else None
            )
            handler = self.handlers.get(kind)
            if handler is None:
                raise LookupError(f"no handler for job kind {kind!r}")
            await asyncio.wait_for(handler(ctx), timeout=remaining)
            await self._finish(ctx, "judgment_saved")
        except OwnershipLost:
            ctx._journal("ownership_lost", status="lost", error_class="OwnershipLost")
        except BaseException as exc:
            if isinstance(exc, asyncio.CancelledError) and not ctx.lost.is_set():
                raise
            if ctx.lost.is_set():
                ctx._journal("ownership_lost", status="lost", error_class=type(exc).__name__)
                return
            ctx._journal("worker_attempt_failure", status="failed",
                         error_class=type(exc).__name__)
            try:
                await self._finish(ctx, "failed", type(exc).__name__)
            except OwnershipLost:
                ctx._journal("ownership_lost", status="lost", error_class="OwnershipLost")
        finally:
            beat.cancel()
            with suppress(asyncio.CancelledError):
                await beat

    async def run(self):
        while not self.stopping.is_set():
            if time.monotonic() - self._last_producer_heartbeat >= 5:
                try:
                    producer_heartbeat(get_settings().data_dir, "worker", failure_count())
                except OSError:
                    pass  # The independent watchdog detects low disk space.
                self._last_producer_heartbeat = time.monotonic()
            for row in await self.candidates():
                if len(self.tasks) >= self.concurrency or self.stopping.is_set():
                    break
                job_id = row["job_id"]
                if job_id in self.active_jobs:
                    continue
                self.active_jobs.add(job_id)
                task = asyncio.create_task(self.process_job(row["tenant_id"], job_id))
                self.tasks.add(task)
                def done(future, job_id=job_id):
                    self.active_jobs.discard(job_id)
                    self.tasks.discard(future)
                    with suppress(OwnershipLost, asyncio.CancelledError):
                        future.result()
                task.add_done_callback(done)
            try:
                await asyncio.wait_for(self.stopping.wait(), timeout=self.poll_seconds)
            except TimeoutError:
                pass
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)

    def stop(self):
        self.stopping.set()


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--lease-seconds", type=float, default=15)
    parser.add_argument("--poll-seconds", type=float, default=0.5)
    parser.add_argument("--deadline-seconds", type=float, default=120)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--tenant", action="append", default=[], help="Process jobs for this tenant only (repeatable)")
    args = parser.parse_args()
    tenants = args.tenant or [item.strip() for item in os.environ.get("WORKER_TENANTS", "").split(",") if item.strip()]
    args.tenants = tenants
    del args.tenant
    worker = Worker(**vars(args))
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, worker.stop)
    await worker.run()


from jevtriage.judgment.handler import handle_judgment

register("judgment", handle_judgment)


if __name__ == "__main__":
    asyncio.run(main())
