from jevtriage.auth.core import Principal
from jevtriage.auth.policy import can
from jevtriage.evaluation.service import consensus_state, visible_candidate


def test_eval_label_action_is_limited_to_labelers_and_reviewers():
    meta = {"tenant_id": "t"}
    assert can(Principal("t", "a", (), frozenset({"labeler"})), "eval_label", meta)
    assert can(Principal("t", "b", (), frozenset({"reviewer"})), "eval_label", meta)
    assert not can(Principal("t", "c", (), frozenset({"requester"})), "eval_label", meta)
    assert not can(Principal("other", "a", (), frozenset({"labeler"})), "eval_label", meta)


def test_disagreement_requires_consensus():
    assert consensus_state([{"ai_need": "필요"}, {"ai_need": "불필요"}]) == "consensus_required"
    assert consensus_state([{"ai_need": "필요"}, {"ai_need": "필요"}]) == "agreed"


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
