"""Metrics for proposed human-reviewed evaluation labels."""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Any


def _f1(tp: int, fp: int, fn: int) -> float:
    denom = 2 * tp + fp + fn
    return 2 * tp / denom if denom else 0.0


def classification_metrics(rows: Iterable[dict[str, Any]], label: str) -> dict[str, Any]:
    pairs = [(r["proposed_labels"][label], r["predictions"][label]) for r in rows]
    classes = sorted({x for pair in pairs for x in pair})
    counts: Counter[str] = Counter(y for y, _ in pairs)
    confusion = {actual: {predicted: 0 for predicted in classes} for actual in classes}
    for actual, predicted in pairs:
        confusion[actual][predicted] += 1
    scores = []
    for cls in classes:
        tp = sum(a == cls and p == cls for a, p in pairs)
        fp = sum(a != cls and p == cls for a, p in pairs)
        fn = sum(a == cls and p != cls for a, p in pairs)
        scores.append(_f1(tp, fp, fn))
    result: dict[str, Any] = {
        "sample_count": len(pairs),
        "class_counts": dict(sorted(counts.items())),
        "macro_f1": sum(scores) / len(scores) if scores else 0.0,
        "confusion_matrix": confusion,
    }
    if label == "urgency":
        urgent_total = counts.get("긴급", 0)
        urgent_correct = confusion.get("긴급", {}).get("긴급", 0)
        result["urgent_recall"] = urgent_correct / urgent_total if urgent_total else 0.0
    return result


def team_set_metrics(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(rows)
    per_row = []
    for row in rows:
        actual = set(row["proposed_labels"]["team_set"])
        predicted = set(row["predictions"].get("team_set", []))
        denom = len(actual) + len(predicted)
        per_row.append(2 * len(actual & predicted) / denom if denom else 1.0)
    return {"sample_count": len(rows), "mean_f1": sum(per_row) / len(per_row) if per_row else 0.0}


def confidence_metrics(rows: Iterable[dict[str, Any]], bins: list[float] | None = None) -> list[dict[str, Any]]:
    """Accuracy by max-confidence interval; bins are increasing upper bounds."""
    bins = bins or [0.5, 0.7, 0.85, 1.0]
    buckets = [{"lower": 0.0 if i == 0 else bins[i - 1], "upper": upper, "count": 0, "correct": 0}
               for i, upper in enumerate(bins)]
    for row in rows:
        confidence = row.get("predictions", {}).get("confidence")
        if confidence is None:
            continue
        confidence = max(0.0, min(1.0, float(confidence)))
        index = next((i for i, upper in enumerate(bins) if confidence <= upper), len(bins) - 1)
        bucket = buckets[index]
        bucket["count"] += 1
        bucket["correct"] += int(bool(row.get("correct")))
    for bucket in buckets:
        bucket["accuracy"] = bucket["correct"] / bucket["count"] if bucket["count"] else None
    return buckets


def evaluate(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(rows)
    rows = [r for r in rows if r.get("label_status") == "confirmed"] or rows
    labels = {key: classification_metrics(rows, key) for key in ("ai_need", "feasibility", "urgency")}
    review = sum(bool(r.get("predictions", {}).get("requires_review")) for r in rows)
    auto = sum(bool(r.get("predictions", {}).get("auto_allowed")) for r in rows)
    is_confirmed = bool(rows) and all(r.get("label_status") == "confirmed" for r in rows)
    return {
        "status": "확정" if is_confirmed else "잠정(현업 미확정)",
        "sample_count": len(rows),
        "classifications": labels,
        "team_set": team_set_metrics(rows),
        "confidence_buckets": confidence_metrics(rows),
        "review_transition_rate": review / len(rows) if rows else 0.0,
        "auto_processing_rate": auto / len(rows) if rows else 0.0,
    }
