from ildongi.judgment.eligibility import evaluate_auto_assign


def base():
    judgment = {
        "ai_need": "필요", "feasibility": "가능", "urgency": "일반", "lead_org": "IT팀",
        "choice_confidences": {k: .9 for k in ("ai_need", "feasibility", "urgency", "lead_org")},
        "risk_signals": {k: .1 for k in ("clinical_safety", "pharmacovigilance", "regulatory")},
        "risk_confirmed": True,
        "signals": {k: .9 for k in ("ai_team_involvement", "it_team_involvement", "business_involvement")},
        "draft_tasks": [{"lead_org": "IT팀", "deliverable": "화면", "status": "초안"}],
    }
    policy = {"auto_assign": True, "risk_clear_max": .2,
              "choice_confidence_thresholds": {k: .8 for k in judgment["choice_confidences"]}}
    context = {"input_confirmed": True, "latest_run": True, "evidence_complete": True}
    return judgment, policy, context


def test_each_choice_threshold_and_infeasible():
    for key in ("ai_need", "feasibility", "urgency", "lead_org"):
        j, p, c = base()
        assert evaluate_auto_assign(j, p, c)[0]
        j["choice_confidences"][key] = .79
        allowed, reasons = evaluate_auto_assign(j, p, c)
        assert not allowed and f"Choice confidence 미충족: {key}" in reasons
    j, p, c = base()
    j["feasibility"] = "현재 불가"
    assert not evaluate_auto_assign(j, p, c)[0]


def test_risk_and_noul_boundaries():
    j, p, c = base()
    j["risk_signals"]["regulatory"] = .2
    assert evaluate_auto_assign(j, p, c)[0]
    j["risk_signals"]["regulatory"] = .201
    assert "필수 검토: 위험 여부 미확정" in evaluate_auto_assign(j, p, c)[1]
    j, p, c = base()
    j["signals"]["it_team_involvement"] = .35
    assert "Noul 참여 불확실: it_team_involvement" in evaluate_auto_assign(j, p, c)[1]
    j["signals"]["it_team_involvement"] = .65
    assert not evaluate_auto_assign(j, p, c)[0]
    j["signals"]["it_team_involvement"] = .651
    assert evaluate_auto_assign(j, p, c)[0]


def test_missing_policy_disallows_auto_assignment():
    j, _, c = base()
    assert not evaluate_auto_assign(j, {}, c)[0]


def test_policy_band_validation_and_lead_org_default():
    from pydantic import ValidationError

    from ildongi.policy.service import PolicyConfig
    assert PolicyConfig().choice_confidence_thresholds["lead_org"] == .8
    for band in ([.5, .5], [-.01, .5], [.35, 1.01], [.5]):
        try:
            PolicyConfig(noul_uncertain_band=band)
        except ValidationError:
            pass
        else:
            raise AssertionError(f"invalid band accepted: {band}")
