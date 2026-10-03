"""Convert Neo4j temporal values into stable JSON primitives."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any


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
