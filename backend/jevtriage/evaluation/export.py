"""Export the latest labels per sample and refresh the candidate manifest."""
from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
from jevtriage.db.driver import close_driver, get_driver


async def export() -> Path:
    manifest_path = ROOT / "eval/candidates/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    driver = await get_driver()
    async with driver.session() as session:
        result = await session.run(
            "MATCH (l:EvalLabel {status:'confirmed'}) RETURN l.split AS split,l.sample_id AS id,"
            "l.labels AS labels,l.user_id AS user_id,l.confidence AS confidence,l.created_at AS confirmed_at "
            "ORDER BY l.created_at")
        latest = {}
        async for item in result:
            latest[(item["split"], item["id"])] = dict(item)
    final = []
    for split in ("tuning", "final"):
        info = manifest["splits"][split]
        source = ROOT / "eval/candidates" / info["path"]
        for line in source.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            label = latest.get((split, row["id"]))
            if label:
                row.update(proposed_labels=json.loads(label["labels"]), label_status="confirmed",
                           confirmed_by=label["user_id"], confirmed_at=str(label["confirmed_at"]),
                           agreement="multiple_labels" if False else "single_label",
                           confidence=label["confidence"])
                final.append(row)
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
