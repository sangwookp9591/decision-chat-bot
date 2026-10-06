from datetime import UTC, datetime

from ildongi.learning.effects import _effect, _metrics


def test_effect_requires_human_labels_even_with_many_runs():
    row = {"started_at": datetime.now(UTC), "committed_at": None,
           "changed": False, "corrected": False, "reviewed": False, "failed": False,
           "labeled": False}
    metrics = _metrics([row] * 20)
    assert metrics["labeled_count"] == 0
    assert _effect(metrics, metrics, 20) == "insufficient_sample"
