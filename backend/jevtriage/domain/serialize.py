"""Convert Neo4j temporal values into stable JSON primitives."""
from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import Any


def to_native(value: Any) -> Any:
    """Convert Neo4j temporal values recursively; naive datetimes use UTC."""
    if isinstance(value, dict):
        return {key: to_native(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_native(item) for item in value]
    if hasattr(value, "to_native"):
        value = value.to_native()
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def dumps(value: Any, *, default_empty=None) -> str:
    """Canonical JSON used for payload hashing and storage."""
    return json.dumps(value if value is not None else default_empty, sort_keys=True,
                      ensure_ascii=False, default=json_value)


def loads_or(raw: str | None, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return default


def json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "iso_format"):
        return value.iso_format()
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    if hasattr(value, "to_native"):
        native = value.to_native()
        return native.isoformat() if hasattr(native, "isoformat") else str(native)
    return value
