"""Tenant-scoped, immutable dynamic policy versions."""

from .service import get_active_snapshot, get_version

__all__ = ["get_active_snapshot", "get_version"]
