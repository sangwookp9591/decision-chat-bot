import pytest
from fastapi import HTTPException

from jevtriage.auth.core import Principal
from jevtriage.auth.policy import can
from jevtriage.evaluation.service import (
    LabelBody,
    _rows,
    _validate_labels,
    consensus_state,
    progress_summary,
    visible_candidate,
)


def test_eval_label_action_is_limited_to_labelers_and_reviewers():
    meta = {"tenant_id": "t"}
    assert can(Principal("t", "a", (), frozenset({"labeler"})), "eval_label", meta)
    assert can(Principal("t", "b", (), frozenset({"reviewer"})), "eval_label", meta)
    assert not can(Principal("t", "c", (), frozenset({"requester"})), "eval_label", meta)
    assert not can(Principal("other", "a", (), frozenset({"labeler"})), "eval_label", meta)


def test_disagreement_requires_consensus():
    assert consensus_state([{"ai_need": "필요"}, {"ai_need": "불필요"}]) == "consensus_required"
    assert consensus_state([{"ai_need": "필요"}, {"ai_need": "필요"}]) == "agreed"


@pytest.mark.parametrize("labels,field", [
    ({"ai_need": "INVALID", "feasibility": "가능", "urgency": "일반", "team_set": [], "risk_areas": []}, "ai_need"),
    ({"ai_need": "필요", "feasibility": "INVALID", "urgency": "일반", "team_set": [], "risk_areas": []}, "feasibility"),
    ({"ai_need": "필요", "feasibility": "가능", "urgency": "INVALID", "team_set": [], "risk_areas": []}, "urgency"),
    ({"ai_need": "필요", "feasibility": "가능", "urgency": "일반", "team_set": "AI팀", "risk_areas": []}, "team_set"),
    ({"ai_need": "필요", "feasibility": "가능", "urgency": "일반", "team_set": ["기타"], "risk_areas": []}, "team_set"),
    ({"ai_need": "필요", "feasibility": "가능", "urgency": "일반", "team_set": [], "risk_areas": "규제 검토"}, "risk_areas"),
    ({"ai_need": "필요", "feasibility": "가능", "urgency": "일반", "team_set": [], "risk_areas": [123]}, "risk_areas"),
    ({"ai_need": None, "feasibility": "가능", "urgency": "일반", "team_set": [], "risk_areas": []}, "ai_need"),
])
def test_invalid_label_values_rejected_with_field_reason(labels, field):
    sample_id = _rows("tuning")[0]["id"]
    body = LabelBody(labels=labels, confidence=.8)
    with pytest.raises(HTTPException) as error:
        _validate_labels("tuning", sample_id, body)
    assert error.value.status_code == 422
    assert field in str(error.value.detail)


def test_uncertain_answers_offered_by_the_labeling_ui_are_accepted():
    sample_id = _rows("tuning")[0]["id"]
    labels = {"ai_need": "정보 부족", "feasibility": "정보 부족", "urgency": "판단 보류",
              "team_set": [], "risk_areas": []}
    _validate_labels("tuning", sample_id, LabelBody(labels=labels, confidence=.5))


def test_consensus_confirmed_counts_as_completed_progress():
    summary = progress_summary(3, [
        {"id": "a", "status": "confirmed"},
        {"id": "b", "status": "consensus_confirmed"},
    ])
    assert summary["confirmed"] == 2
    assert summary["remaining"] == 1


def test_set_fields_are_order_independent_for_consensus():
    assert consensus_state([
        {"team_set": ["AI팀", "IT팀"], "risk_areas": []},
        {"team_set": ["IT팀", "AI팀"], "risk_areas": []},
    ]) == "agreed"


def test_set_fields_are_normalized_before_recording():
    sample_id = _rows("tuning")[0]["id"]
    labels = {"ai_need": "필요", "feasibility": "가능", "urgency": "일반",
              "team_set": ["IT팀", "AI팀", "AI팀"], "risk_areas": []}
    body = LabelBody(labels=labels, confidence=.8)
    _validate_labels("tuning", sample_id, body)
    assert body.labels["team_set"] == ["AI팀", "IT팀"]


def test_final_candidate_hides_proposed_prediction_until_confirmed():
    row = {"id": "x", "label_status": "proposed", "proposed_labels": {"ai_need": "필요"},
           "rationale": "memo", "predictions": {"ai_need": "불필요"}}
    assert "predictions" not in visible_candidate(row, "final")
    row["label_status"] = "confirmed"
    assert "predictions" not in visible_candidate(row, "final")


def test_final_candidate_hides_all_prediction_fields():
    row = {"id": "x", "prediction": "hidden", "model_output": {"label": 1}, "model_result": 1,
           "proposed_labels": {"ai_need": "필요"}, "rationale": "모델 설명", "scenario_tags": ["긴급"]}
    visible = visible_candidate(row, "final")
    assert not {"prediction", "predictions", "model_output", "model_result", "proposed_labels", "rationale", "scenario_tags"} & visible.keys()


def test_progress_counts_unique_confirmed_samples_and_deferred_separately():
    from jevtriage.evaluation.service import progress_summary
    summary = progress_summary(4, [
        {"id": "a", "status": "confirmed"}, {"id": "a", "status": "confirmed"},
        {"id": "b", "status": "deferred"},
    ])
    assert summary == {"total": 4, "confirmed": 1, "deferred": 1, "remaining": 2, "percent": 25}


def test_confirmed_export_row_includes_consensus_metadata():
    from jevtriage.evaluation.export import confirmed_row
    row = confirmed_row({"id": "x", "text": "sample"}, [
        {"labels": '{"ai_need":"필요"}', "user_id": "one", "confidence": .8, "created_at": "t1"},
        {"labels": '{"ai_need":"필요"}', "user_id": "two", "confidence": .9, "created_at": "t2"},
    ])
    assert row["agreement"] == "agreed" and row["label_count"] == 2
    assert row["proposed_labels"] == {"ai_need": "필요"}


def test_export_ignores_prior_confirmation_after_latest_defer():
    from jevtriage.evaluation.export import confirmed_row
    row = confirmed_row({"id": "x"}, [
        {"labels": '{"ai_need":"필요"}', "user_id": "one", "confidence": .8, "created_at": "t1", "status": "confirmed"},
        {"labels": '{"ai_need":"불필요"}', "user_id": "one", "confidence": .8, "created_at": "t2", "status": "deferred"},
    ])
    assert row == {}
