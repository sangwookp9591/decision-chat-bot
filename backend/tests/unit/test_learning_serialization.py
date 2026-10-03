from neo4j.time import DateTime, Duration

from jevtriage.domain.serialize import json_value


def test_neo4j_temporal_values_are_iso8601_strings_in_nested_payloads():
    payload = {"created_at": DateTime(2026, 10, 3, 12, 30, 0), "metrics": {"elapsed": Duration(seconds=7)}}
    encoded = json_value(payload)
    assert isinstance(encoded["created_at"], str)
    assert encoded["created_at"].startswith("2026-10-03T12:30:00")
    assert encoded["metrics"]["elapsed"] == "PT7S"
