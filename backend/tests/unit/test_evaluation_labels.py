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
