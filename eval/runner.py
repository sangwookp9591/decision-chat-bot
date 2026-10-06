"""Run Decision AI judgment on one frozen candidate split and save sanitized results."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from ildongi.config import get_settings
from ildongi.judgment.ai_client import AiClient
from ildongi.judgment.pipeline import run_judgment
from metrics import evaluate


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _predict(judgment: dict[str, Any]) -> dict[str, Any]:
    classifications = judgment["classifications"]
    raw_answers = judgment.get("raw_model_output", {}).get("answers", {})
    confidence_values = [raw_answers.get(key, {}).get("confidence", 0.0)
                         for key in ("ai_need", "feasibility", "urgency")]
    # The team set is the judgment's own involvement result plus the lead org,
    # not the static owners of catalog task templates.
    teams = {classifications.get("lead_org", "판단 보류")}
    teams.update(team for team in judgment.get("teams", []) if team in {"AI팀", "IT팀", "현업"})
    return {
        **classifications,
        "team_set": sorted(teams - {"판단 보류"}),
        "confidence": sum(confidence_values) / len(confidence_values),
        "requires_review": bool(judgment.get("review_reasons")),
        "auto_allowed": bool(judgment.get("eligibility", {}).get("allowed")),
    }


async def _run_one(row: dict[str, Any], client: AiClient, semaphore: asyncio.Semaphore,
                   retries: int, policy: dict[str, Any]) -> dict[str, Any]:
    async with semaphore:
        for attempt in range(retries + 1):
            try:
                result = await asyncio.to_thread(run_judgment, [], row["text"], policy, client)
                prediction = _predict(result)
                actual = row["proposed_labels"]
                correct = all(prediction[k] == actual[k] for k in ("ai_need", "feasibility", "urgency"))
                # Only model outputs needed for reproducibility are retained. Evidence excerpts and
                # the submitted request body are deliberately excluded from all files and logs.
                return {
                    "id": row["id"], "label_status": row["label_status"],
                    "proposed_labels": actual, "predictions": prediction, "correct": correct,
                    "usage": result.get("usage", {}), "versions": result.get("versions", {}),
                    "run_status": "success",
                }
            except Exception as exc:  # noqa: BLE001 - persist safe class only, never exception text
                error_type = type(exc).__name__
                if attempt >= retries:
                    return {"id": row["id"], "label_status": row["label_status"],
                            "proposed_labels": row["proposed_labels"], "run_status": "failed",
                            "error_type": error_type, "attempts": attempt + 1}
                await asyncio.sleep(min(2 ** attempt, 4))
    raise RuntimeError("unreachable")


async def run(split: str, max_samples: int, concurrency: int, retries: int) -> Path:
    settings = get_settings()
    if settings.ai_mode != "live":
        raise RuntimeError("AI_MODE must be live")
    if not settings.ai_api_key.get_secret_value():
        raise RuntimeError("AI_API_KEY is not configured")
    manifest_path = ROOT / "eval/candidates/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    split_info = manifest["splits"][split]
    split_path = ROOT / "eval/candidates" / split_info["path"]
    split_hash = hashlib.sha256(split_path.read_bytes()).hexdigest()
    if split_hash != split_info["sha256"]:
        raise RuntimeError("candidate split hash does not match manifest")
    rows = _read_jsonl(split_path)
    confirmed_path = ROOT / "eval/candidates/confirmed.jsonl"
    if confirmed_path.exists():
        confirmed = {r["id"]: r for r in _read_jsonl(confirmed_path)
                     if r.get("label_status") == "confirmed"}
        rows = [confirmed.get(r["id"], r) for r in rows]
    rows = rows[:max_samples]
    client = AiClient(settings.ai_api_key.get_secret_value(), mode="live", max_retries=2)
    policy = {"max_evidence_units": 1, "max_evidence_chars": 2000,
              "evidence_noul_threshold": 0.6, "catalog_noul_threshold": 0.5,
              "auto_assign_enabled": True, "input_confirmed": True}
    semaphore = asyncio.Semaphore(concurrency)
    results = await asyncio.gather(*(_run_one(row, client, semaphore, retries, policy) for row in rows))
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    outdir = ROOT / "artifacts/validation/eval" / timestamp
    outdir.mkdir(parents=True, exist_ok=False)
    (outdir / "raw.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    successful = [r for r in results if r["run_status"] == "success"]
    metrics = evaluate(successful)
    metrics["failed_count"] = len(results) - len(successful)
    metrics["run"] = {"split": split, "requested_count": len(rows), "split_sha256": split_hash,
                       "model_versions": sorted({r.get("versions", {}).get("model", "unknown") for r in successful}),
                       "mode": "live"}
    (outdir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return outdir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("tuning", "final"), default="tuning")
    parser.add_argument("--max-samples", type=int, default=60)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--retries", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.max_samples <= 72 or args.concurrency < 1 or args.retries < 0:
        parser.error("max-samples must be 1..72; concurrency >= 1; retries >= 0")
    try:
        path = asyncio.run(run(args.split, args.max_samples, args.concurrency, args.retries))
    except Exception as exc:  # noqa: BLE001 - safe, non-sensitive diagnostics only
        print(f"평가 실행 실패: {type(exc).__name__}")
        raise SystemExit(1) from None
    summary = json.loads((path / "metrics.json").read_text(encoding="utf-8"))
    print(json.dumps({"artifact": str(path.relative_to(ROOT)), "sample_count": summary["sample_count"],
                      "failed_count": summary["failed_count"], "status": summary["status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
