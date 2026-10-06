"""Compatibility import for the run creation boundary, now in db.runs."""

from ildongi.db.runs import start_run_in_tx

__all__ = ["start_run_in_tx"]
