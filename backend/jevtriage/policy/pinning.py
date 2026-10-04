"""Compatibility import for policy version pinning now owned by db.pinning."""

from jevtriage.db.pinning import pin_config_for_run_in_tx

__all__ = ["pin_config_for_run_in_tx"]
