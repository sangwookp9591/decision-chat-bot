"""Export the latest confirmed evaluation decisions and refresh the manifest."""
from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any

from jevtriage.db.driver import close_driver, get_driver
from jevtriage.evaluation.service import consensus_state

ROOT = Path(__file__).resolve().parents[3]


def confirmed_row(row: dict[str, Any], labels: list[dict[str, Any]]) -> dict[str, Any]:
    parsed = [{**item, "labels": json.loads(item["labels"])} for item in labels]
    latest_by_user: dict[str, dict[str, Any]] = {}
    for item in parsed:
        latest_by_user[item["user_id"]] = item
    latest = list(latest_by_user.values())
    confirmed = [item for item in latest if item.get("status", "confirmed") in {"confirmed", "consensus_confirmed"}]
    resolution = next((item for item in reversed(latest) if item.get("status") == "consensus_confirmed"), None)
    if resolution and all(str(resolution["created_at"]) >= str(item["created_at"]) for item in confirmed):
        chosen = resolution
        agreement = "consensus_resolved"
    elif not confirmed:
        return {}
    else:
        chosen = confirmed[-1]
        agreement = consensus_state([item["labels"] for item in confirmed])
        if agreement == "consensus_required":
            return {}
    return {**row, "proposed_labels": chosen["labels"], "label_status": "confirmed",
            "confirmed_by": chosen["user_id"], "confirmed_at": str(chosen["created_at"]),
            "agreement": agreement, "label_count": len(confirmed), "confidence": chosen.get("confidence")}


async def export() -> Path:
    manifest_path = ROOT / "eval/candidates/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    driver = await get_driver()
    async with driver.session() as session:
        result = await session.run(
            "MATCH (l:EvalLabel) WHERE l.status IN ['confirmed','deferred','consensus_confirmed'] "
            "RETURN l.split AS split,l.sample_id AS id,l.labels AS labels,l.status AS status,"
            "l.user_id AS user_id,l.confidence AS confidence,l.created_at AS created_at ORDER BY created_at")
        by_sample: dict[tuple[str, str], list[dict[str, Any]]] = {}
        async for item in result:
            by_sample.setdefault((item["split"], item["id"]), []).append(dict(item))
    final = []
    for split in ("tuning", "final"):
        source = ROOT / "eval/candidates" / manifest["splits"][split]["path"]
        for line in source.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            exported = confirmed_row(row, by_sample.get((split, row["id"]), []))
            if exported:
                final.append(exported)
    output = ROOT / "eval/candidates/confirmed.jsonl"
    output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in final), encoding="utf-8")
    manifest["confirmed"] = {"path": "confirmed.jsonl", "count": len(final),
                              "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    try:
        print(asyncio.run(export()))
    finally:
        asyncio.run(close_driver())
