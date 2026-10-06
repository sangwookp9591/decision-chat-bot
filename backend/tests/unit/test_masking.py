import pytest

from ildongi.judgment.masking import MaskingSession, mask_for_external
from ildongi.policy.service import DEFAULT_CONFIG, validate_config


@pytest.mark.parametrize("value", [
    "name@example.com", "010-1234-5678", "02-123-4567", "900101-1234567",
    "123-45-67890", "4111 1111 1111 1111", "123-456-789012", "192.168.1.1",
    "https://example.com/path?token=abc123secret&ok=1", "sk_test_abcdefghijklmnopqrstuvwxyz123456",
])
def test_sensitive_patterns_masked(value):
    assert value not in mask_for_external(f"앞 {value} 뒤", DEFAULT_CONFIG)


@pytest.mark.parametrize("value", ["2026-10-04", "1,234,567원", "v1.2.3", "127.0.0.999"])
def test_non_sensitive_values_preserved(value):
    assert value in mask_for_external(f"앞 {value} 뒤", DEFAULT_CONFIG)


def test_same_value_same_token_within_request_and_disabled_policy():
    session = MaskingSession()
    policy = {"masking": {"enabled": True, "categories": ["email"]}, "_masking_session": session}
    first = mask_for_external("name@example.com", policy)
    assert first == mask_for_external("name@example.com", policy)
    assert first != mask_for_external("other@example.com", policy)
    assert mask_for_external("name@example.com", {"masking": {"enabled": False}}) == "name@example.com"
    assert session.count == 3


def test_policy_defaults_masking_and_rejects_unknown_category():
    assert DEFAULT_CONFIG["masking"]["enabled"] is True
    _, errors = validate_config({**DEFAULT_CONFIG, "masking": {"enabled": True, "categories": ["unknown"]}})
    assert errors


def test_split_email_fragment_and_generic_long_token_are_masked():
    assert "name@example." not in mask_for_external("name@example.", DEFAULT_CONFIG)
    token = "AbC123xyZ9_abcdefghijklmNOPQRST456"
    assert token not in mask_for_external(token, DEFAULT_CONFIG)
