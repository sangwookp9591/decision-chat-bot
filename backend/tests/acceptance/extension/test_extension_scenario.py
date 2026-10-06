"""Gate check over a recorded T38 run (not collected by default; see conftest.py).

X38_RUN=1 X38_OUT=<artifacts/validation/<ts>/extension> .venv/bin/pytest tests/acceptance/extension -q
Fails when any X01–X09 check in the ledger is a final failure (a failure replaced by a recorded retest does not count)
or when a gate has no passing check. The scenario itself is driven by scenario.py (live Decision AI, real Neo4j, browser checks).
"""
import json
import os
from pathlib import Path

import pytest

from tests.acceptance.extension.report import RETESTED

OUT = Path(os.environ.get("X38_OUT", ""))
GATES = [f"X{n:02d}" for n in range(1, 10)]


@pytest.fixture(scope="module")
def ledger():
    path = OUT / "ledger.json"
    assert path.exists(), "run scenario.py stages first"
    return json.loads(path.read_text())


@pytest.mark.parametrize("gate", GATES)
def test_gate_has_passing_evidence_and_no_final_failure(gate, ledger):
    rows = [e for e in ledger if e["gate"] == gate]
    latest = {}
    for e in rows:
        latest[(e["gate"], e["step"])] = e
    final_failures = [k for k, e in latest.items() if e["status"] == "fail" and k not in RETESTED]
    assert not final_failures, final_failures
    assert any(e["status"] == "pass" for e in latest.values()), f"{gate}: no passing check recorded"
