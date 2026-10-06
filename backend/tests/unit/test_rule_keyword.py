"""Keyword grammar, deterministic matching and legacy rule compatibility."""
from copy import deepcopy

import pytest

from ildongi.domain.rules import (
    apply_rules,
    context_rules_for,
    normalize_for_match,
    text_matches,
    validate_rule,
)


def rule(scope=None, **extra):
    return {"schema": "rule-v1", "rule_id": "R-LEAD_ORG-03", "version": 1,
            "effect": "rule", "target": "lead_org", "action": {"set": "IT팀"},
            "scope": scope or {"all": [{"text": {"contains_any": ["VPN"]}}]}, **extra}


@pytest.mark.parametrize("predicate", [
    {"text": {"contains_any": []}}, {"text": {"contains_any": ["x"] * 21}},
    {"text": {"contains_any": ["x" * 51]}}, {"text": {"contains_any": [1]}},
    {"text": {"contains_any": [" \u200b"]}}, {"text": {"contains_all": ["VPN"]}},
    {"text": {"contains_any": ["VPN"], "extra": True}},
    {"text": {"contains_any": ["VPN"]}, "extra": True},
    {"text": {"contains_any": "VPN"}}, {"text": None},
])
def test_reject_invalid_predicate(predicate):
    with pytest.raises(ValueError, match="invalid text predicate"):
        validate_rule(rule({"all": [predicate]}))


def test_duplicate_and_original_spelling():
    with pytest.raises(ValueError, match="duplicate keyword"):
        validate_rule(rule({"all": [{"text": {"contains_any": ["VPN", " v p n"]}}]}))
    body = rule({"all": [{"text": {"contains_any": ["ＶＰＮ", "서버 점검"]}}]})
    assert validate_rule(body) == body


@pytest.mark.parametrize("text", ["ＶＰＮ 접속", "vpn접속", "V P N", "v\u200bp\u200bn"])
def test_normalization_and_original_offsets(text):
    matches = text_matches(rule()["scope"]["all"][0], [{"unit_id": "span", "text": text}])
    assert len(matches) == 1
    match = matches[0]
    assert normalize_for_match(text[match["char_start"]:match["char_end"]])[0] == "vpn"
    assert match["keyword"] == "VPN" and match["unit_id"] == "span"


def test_casefold_expansion_and_hangul_spaces():
    normalized, index = normalize_for_match("aß 서 버\u200b 점검")
    assert normalized == "ass서버점검" and index[1:3] == [1, 1]
    matches = text_matches({"text": {"contains_any": ["서버점검"]}}, [{"unit_id": "s", "text": "서 버 점검"}])
    assert matches[0]["char_start"] == 0 and matches[0]["char_end"] == 6


def test_application_and_fail_closed_and_and_scope():
    original = {"classifications": {"lead_org": "AI팀"}, "draft_tasks": [{"lead_org": "AI팀"}]}
    body = rule({"all": [{"text": {"contains_any": ["VPN"]}}, {"requester_org": "t-it"}]})
    features = {"requester_orgs": ["t-it"], "text_units": [{"unit_id": "s", "text": "VPN 접속"}]}
    result, applications = apply_rules(original, [body], features=features)
    effect = applications[0]
    assert result["classifications"]["lead_org"] == result["draft_tasks"][0]["lead_org"] == "IT팀"
    assert effect["source"] == "rule:R-LEAD_ORG-03@v1" and effect["target"] == "lead_org"
    assert effect["outcome"] == "used" and effect["matches"][0]["unit_id"] == "s"
    assert "text" not in effect["matches"][0]
    assert original["classifications"]["lead_org"] == "AI팀"
    for features in ({"requester_orgs": ["t-it"]}, {"text_units": [{"unit_id": "s", "text": "VPN"}]}):
        _, applications = apply_rules(original, [body], features=features)
        assert applications[0]["outcome"] == "out_of_scope" and applications[0]["matches"] == []


def test_order_limit_and_no_cross_unit_match():
    clause = {"text": {"contains_any": ["VPN", "서버"]}}
    units = [{"unit_id": "first", "text": "VPN VPN 서버"}, {"unit_id": "last", "text": "VPN VPN VPN"}]
    matches = text_matches(clause, units)
    assert [match["unit_id"] for match in matches] == ["first"] * 3 + ["last"] * 2
    assert [match["keyword"] for match in matches[:3]] == ["VPN", "VPN", "서버"]
    _, applications = apply_rules({}, [rule({"all": [clause, clause]})], features={"text_units": units})
    assert len(applications[0]["matches"]) == 5
    assert not text_matches(clause, [{"unit_id": "a", "text": "VP"}, {"unit_id": "b", "text": "N"}])


def test_context_scope_and_invalid_model_predicate():
    body = rule({"all": [{"requester_org": "it"}, {"text": {"contains_any": ["VPN"]}}]},
                effect="context", context_text="운영 가이드")
    features = {"requester_orgs": ["it"], "text_units": [{"unit_id": "s", "text": "VPN"}]}
    assert context_rules_for([body], features) == ["운영 가이드"]
    assert context_rules_for([body], {}) == []
    invalid = {**body, "scope": {"all": [{"field": "lead_org", "op": "eq", "value": "IT팀"}]}}
    with pytest.raises(ValueError, match="context scope must"):
        validate_rule(invalid)
    assert context_rules_for([invalid], features) == []


def test_legacy_snapshot_compatibility():
    original = {"classifications": {"lead_org": "AI팀"}}
    result, applications = apply_rules(original, [rule({"all": []})])
    expected = {"rule_version": "R-LEAD_ORG-03@1", "effect": "rule", "outcome": "used", "before": "AI팀", "after": "IT팀"}
    legacy = deepcopy(applications[0])
    for key in ("target", "source", "matches"):
        legacy.pop(key)
    assert legacy == expected and result["classifications"] == {"lead_org": "IT팀"}


def test_keyword_scope_survives_redaction_without_source_permission():
    from ildongi.auth.policy import redact_source
    from ildongi.auth.types import Principal
    principal = Principal("t", "u", (), frozenset({"rule_admin"}))
    body = rule()
    for payload in ({"proposed_body": body}, {"versions": [{"body": body}]}, {"config": {"rules": [body]}}):
        assert redact_source(principal, payload) == payload


def test_raw_text_and_lookalike_predicates_stay_redacted_in_same_response():
    from ildongi.auth.policy import redact_source
    from ildongi.auth.types import Principal
    principal = Principal("t", "u", (), frozenset({"rule_admin"}))
    payload = {"proposed_body": rule(), "request": {"text": "raw request"},
               "evidence": [{"text": "raw evidence", "source_text": "source"}],
               "summary": {"text": "raw summary"},
               "scope": {"all": [{"text": {"contains_any": ["raw source"]}}]},
               "body": {"scope": {"all": [{"text": {"contains_any": ["VPN"], "text": "raw"}},
                                            {"text": {"contains_any": [123]}}]}}}
    result = redact_source(principal, payload)
    assert result["proposed_body"] == rule()
    assert result["request"] == result["summary"] == {}
    assert result["evidence"] == [{}] and result["scope"]["all"] == [{}]
    assert result["body"]["scope"]["all"] == [{}, {}]
