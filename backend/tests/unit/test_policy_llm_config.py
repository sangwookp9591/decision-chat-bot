from copy import deepcopy

from ildongi.policy.service import DEFAULT_CONFIG, validate_config


def test_llm_defaults_and_old_policy():
    old = deepcopy(DEFAULT_CONFIG)
    old.pop('llm', None)
    config, issues = validate_config(old)
    assert not issues
    assert config['llm']['provider'] is None
    assert not any(config['llm']['features'].values())


def test_model_required_and_masking_required():
    raw = deepcopy(DEFAULT_CONFIG)
    raw['llm'] = {'provider': 'anthropic'}
    assert validate_config(raw)[1]
    raw['llm']['model'] = 'claude-opus-5-5'
    raw['masking']['enabled'] = False
    assert any(i['code'] == 'LLM_REQUIRES_MASKING' for i in validate_config(raw)[1])
