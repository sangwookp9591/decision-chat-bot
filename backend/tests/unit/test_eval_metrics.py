import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from eval.metrics import evaluate


def test_classification_macro_f1_and_urgency_recall():
    rows = [
        {"label_status": "proposed", "proposed_labels": {"ai_need": "필요", "feasibility": "가능", "urgency": "긴급", "team_set": ["AI팀"]},
         "predictions": {"ai_need": "필요", "feasibility": "가능", "urgency": "긴급", "team_set": ["AI팀"], "confidence": 0.9, "requires_review": False, "auto_allowed": True}, "correct": True},
        {"label_status": "proposed", "proposed_labels": {"ai_need": "불필요", "feasibility": "가능", "urgency": "일반", "team_set": ["IT팀"]},
         "predictions": {"ai_need": "필요", "feasibility": "현재 불가", "urgency": "일반", "team_set": ["AI팀"], "confidence": 0.6, "requires_review": True, "auto_allowed": False}, "correct": False},
    ]
    result = evaluate(rows)
    assert result["classifications"]["ai_need"]["macro_f1"] == 1 / 3
    assert result["classifications"]["ai_need"]["class_counts"] == {"불필요": 1, "필요": 1}
    assert result["classifications"]["ai_need"]["confusion_matrix"]["불필요"]["필요"] == 1
    assert result["classifications"]["urgency"]["urgent_recall"] == 1
    assert result["status"] == "잠정(현업 미확정)"


def test_team_set_mean_f1_review_rates_and_confidence_accuracy():
    rows = [
        {"label_status": "confirmed", "proposed_labels": {"ai_need": "필요", "feasibility": "가능", "urgency": "긴급", "team_set": ["AI팀", "IT팀"]},
         "predictions": {"ai_need": "필요", "feasibility": "가능", "urgency": "긴급", "team_set": ["AI팀"], "confidence": 0.8, "requires_review": False, "auto_allowed": True}, "correct": True},
        {"label_status": "confirmed", "proposed_labels": {"ai_need": "불필요", "feasibility": "현재 불가", "urgency": "일반", "team_set": ["현업"]},
         "predictions": {"ai_need": "불필요", "feasibility": "현재 불가", "urgency": "일반", "team_set": ["IT팀"], "confidence": 0.4, "requires_review": True, "auto_allowed": False}, "correct": False},
    ]
    result = evaluate(rows)
    assert result["team_set"]["mean_f1"] == 1 / 3
    assert result["review_transition_rate"] == 0.5
    assert result["auto_processing_rate"] == 0.5
    assert result["confidence_buckets"][0]["accuracy"] == 0.0
    assert result["confidence_buckets"][2]["accuracy"] == 1.0
    assert result["status"] == "확정"
