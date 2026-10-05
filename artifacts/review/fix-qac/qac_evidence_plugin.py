"""Redirect original QA probes' output without replacing pre-fix evidence."""
from pathlib import Path


def pytest_collection_modifyitems(items):
    folder = Path(__file__).parent / 'original-evidence'
    folder.mkdir(exist_ok=True)
    for item in items:
        if hasattr(item.module, 'EVIDENCE'):
            item.module.EVIDENCE = folder
