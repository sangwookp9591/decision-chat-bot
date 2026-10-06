"""Authentication principal shared by session handling and policy checks."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    tenant_id: str
    user_id: str
    org_ids: tuple[str, ...]
    roles: frozenset[str]
    can_read_source: bool = False
