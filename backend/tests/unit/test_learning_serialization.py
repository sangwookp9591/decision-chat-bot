from datetime import UTC, datetime

from neo4j.time import DateTime, Duration

from ildongi.db.idempotency import payload_hash
from ildongi.domain.serialize import dumps, json_value, loads_or, to_native


def test_neo4j_temporal_values_are_iso8601_strings_in_nested_payloads():
    payload = {"created_at": DateTime(2026, 10, 3, 12, 30, 0), "metrics": {"elapsed": Duration(seconds=7)}}
    encoded = json_value(payload)
    assert isinstance(encoded["created_at"], str)
    assert encoded["created_at"].startswith("2026-10-03T12:30:00")
    assert encoded["metrics"]["elapsed"] == "PT7S"


def test_shared_native_and_json_helpers_preserve_native_values_and_handle_bad_json():
    value = datetime(2026, 10, 3)  # noqa: DTZ001 - deliberately exercise naive UTC handling
    assert to_native(value) == value.replace(tzinfo=UTC)
    assert to_native({"items": [1, 2]}) == {"items": [1, 2]}
    assert dumps({"한글": 1}) == '{"한글": 1}'
    assert loads_or('{"ok":true}', {}) == {"ok": True}
    assert loads_or("{bad", {}) == {}
    assert loads_or("", []) == []


def test_payload_hash_uses_sorted_json_keys():
    assert payload_hash({"b": 2, "a": 1}) == payload_hash({"a": 1, "b": 2})
