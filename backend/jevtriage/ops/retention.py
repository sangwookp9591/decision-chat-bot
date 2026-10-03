"""Bounded, policy-driven cleanup for operational records and telemetry."""
from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import uuid
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from jevtriage.config import get_settings
from jevtriage.db.driver import get_driver
from jevtriage.db.tx import read_tx, write_tx
from jevtriage.journal.collector import metrics_path
from jevtriage.journal.writer import JournalWriter
from jevtriage.policy.service import get_active_snapshot


@dataclass(frozen=True)
class RetentionConfig:
    event_days: int = 90
    idempotency_days: int = 30
    session_grace_days: int = 7
    login_attempt_window_seconds: int = 900
    journal_days: int = 90
    metrics_days: int = 90
    batch_size: int = 500

    def __post_init__(self):
        for key, value in asdict(self).items():
            lower = 1 if key != "session_grace_days" else 0
            upper = 10000 if key == "batch_size" else (2592000 if key == "login_attempt_window_seconds" else 3650)
            if not lower <= value <= upper:
                raise ValueError(f"invalid retention setting: {key}")


def _cutoff(days: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).isoformat()


async def _count(tx, query: str, *, tenant_id: str, **params) -> int:
    return int((await (await tx.run(query, tenant=tenant_id, **params)).single(strict=True))["n"])


async def _count_expired(tenant_id: str, label: str, predicate: str, cutoff: str) -> int:
    async def op(tx):
        return await _count(tx, f"MATCH (n:{label} {{tenant_id:$tenant}}) WHERE {predicate} RETURN count(n) AS n",
                            tenant_id=tenant_id, cutoff=cutoff)
    return await read_tx(tenant_id, op)


async def _purge_node(tenant_id: str, label: str, predicate: str, params: dict, batch_size: int,
                      *, on_batch=None) -> int:
    total = 0
    while True:
        async def op(tx):
            result = await tx.run(
                f"MATCH (n:{label} {{tenant_id:$tenant}}) WHERE {predicate} "
                "WITH n ORDER BY n.created_at LIMIT $batch "
                "WITH collect(n) AS nodes, collect(n.seq) AS seqs "
                "FOREACH (n IN nodes | DETACH DELETE n) "
                "RETURN size(nodes) AS count, max(seqs) AS max_seq",
                tenant=tenant_id, batch=batch_size, **params)
            return await result.single(strict=True)
        row = await write_tx(tenant_id, op)
        n = int(row["count"])
        if not n:
            break
        total += n
        if on_batch:
            await on_batch(row)
        if n < batch_size:
            break
    return total


async def _retained_events(tenant_id: str, config: RetentionConfig, cutoff: str, dry_run: bool) -> int:
    async def count(tx):
        return await _count(tx,
            "MATCH (e:Event {tenant_id:$tenant}) WHERE e.created_at < datetime($cutoff) RETURN count(e) AS n",
            tenant_id=tenant_id, cutoff=cutoff)
    count_due = await read_tx(tenant_id, count)
    if dry_run or not count_due:
        return count_due
    async def purge_batch(tx):
        row = await (await tx.run(
            "MATCH (e:Event {tenant_id:$tenant}) WHERE e.created_at < datetime($cutoff) "
            "WITH e ORDER BY e.seq LIMIT $batch WITH collect(e) AS events "
            "FOREACH (e IN events | DETACH DELETE e) "
            "WITH events MATCH (c:EventCounter {tenant_id:$tenant}) "
            "OPTIONAL MATCH (remaining:Event {tenant_id:$tenant}) "
            "WITH events,c,min(remaining.seq) AS first_remaining "
            "SET c.retained_from_seq=coalesce(first_remaining,c.seq+1) RETURN size(events) AS n",
            tenant=tenant_id, cutoff=cutoff, batch=config.batch_size)).single(strict=True)
        return int(row["n"])
    while await write_tx(tenant_id, purge_batch):
        pass
    return count_due


def _sqlite_cleanup(data_dir: Path, config: RetentionConfig, dry_run: bool) -> tuple[int, int]:
    path = metrics_path(data_dir)
    if not path.exists():
        return 0, 0
    cutoff = _cutoff(config.metrics_days)
    with closing(sqlite3.connect(path)) as db:
        due = int(db.execute("SELECT count(*) FROM events WHERE ts < ?", (cutoff,)).fetchone()[0])
        if not dry_run:
            while True:
                db.execute("DELETE FROM events WHERE event_id IN (SELECT event_id FROM events WHERE ts < ? LIMIT ?)",
                           (cutoff, config.batch_size))
                if db.execute("SELECT changes()").fetchone()[0] == 0:
                    break
            db.commit()
    journal_cutoff = datetime.now(UTC) - timedelta(days=config.journal_days)
    removed = 0
    folder = data_dir / "journal"
    if folder.exists():
        with closing(sqlite3.connect(path)) as db:
            for archive in folder.glob("archive-*.jsonl"):
                if datetime.fromtimestamp(archive.stat().st_mtime, UTC) >= journal_cutoff:
                    continue
                try:
                    offset = db.execute("SELECT byte_offset FROM offsets WHERE path=?", (str(archive),)).fetchone()
                except sqlite3.Error:
                    continue
                if offset and offset[0] >= archive.stat().st_size:
                    removed += 1
                    if not dry_run:
                        archive.unlink()
    return due, removed


async def cleanup(*, data_dir: Path | None = None, tenant_id: str | None = None,
                  config: RetentionConfig | None = None, dry_run: bool = False) -> dict:
    data_dir = Path(data_dir or get_settings().data_dir)
    if config is None:
        if tenant_id:
            _, snapshot = await get_active_snapshot(tenant_id)
            config = RetentionConfig(**snapshot.get("retention", {}))
        else:
            config = RetentionConfig()
    if tenant_id is None:
        driver = await get_driver()
        async with driver.session() as session:
            tenant_rows = await (await session.run("MATCH (t:Tenant) RETURN t.id AS id")).data()
        tenant_ids = [r["id"] for r in tenant_rows]
    else:
        tenant_ids = [tenant_id]
    deleted = {"events": 0, "idempotency": 0, "sessions": 0, "login_attempts": 0,
               "journal_files": 0, "metrics_events": 0}
    now = datetime.now(UTC)
    for tenant in tenant_ids:
        cfg = config
        if tenant_id is None:
            _, snapshot = await get_active_snapshot(tenant)
            cfg = RetentionConfig(**snapshot.get("retention", {}))
        deleted["events"] += await _retained_events(tenant, cfg, _cutoff(cfg.event_days), dry_run)
        id_cutoff = _cutoff(cfg.idempotency_days)
        id_due = await _count_expired(tenant, "Idempotency", "n.created_at < datetime($cutoff)", id_cutoff)
        if dry_run:
            deleted["idempotency"] += id_due
        else:
            deleted["idempotency"] += await _purge_node(tenant, "Idempotency", "n.created_at < datetime($cutoff)", {"cutoff": id_cutoff}, cfg.batch_size)
        session_cutoff = (now - timedelta(days=cfg.session_grace_days)).isoformat()
        session_due = await _count_expired(tenant, "Session", "n.expires_at < datetime($cutoff)", session_cutoff)
        deleted["sessions"] += session_due if dry_run else await _purge_node(tenant, "Session", "n.expires_at < datetime($cutoff)", {"cutoff": session_cutoff}, cfg.batch_size)
        attempt_cutoff = (now - timedelta(seconds=cfg.login_attempt_window_seconds)).isoformat()
        attempt_due = await _count_expired(tenant, "LoginAttempt", "n.window_start < datetime($cutoff)", attempt_cutoff)
        deleted["login_attempts"] += attempt_due if dry_run else await _purge_node(tenant, "LoginAttempt", "n.window_start < datetime($cutoff)", {"cutoff": attempt_cutoff}, cfg.batch_size)
    deleted["metrics_events"], deleted["journal_files"] = _sqlite_cleanup(data_dir, config, dry_run)
    result = {"dry_run": dry_run, "tenants": len(tenant_ids), "deleted": deleted}
    if not dry_run:
        JournalWriter(data_dir).append({"event_id": f"retention_{uuid.uuid4().hex}", "attempt_id": "retention",
            "kind": "retention_cleanup", "ts": datetime.now(UTC).isoformat(), "status_code": 200,
            "validity": "dry_run=false", "step_name": json.dumps(deleted, sort_keys=True)})
    return result


async def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--tenant")
    args = parser.parse_args()
    result = await cleanup(tenant_id=args.tenant, dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
