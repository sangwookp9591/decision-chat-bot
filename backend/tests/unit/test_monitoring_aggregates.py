from ildongi.monitoring.aggregates import _failure_group


def test_ai_rate_limited_is_an_external_model_failure():
    assert _failure_group("AiRateLimited") == "external_model"
