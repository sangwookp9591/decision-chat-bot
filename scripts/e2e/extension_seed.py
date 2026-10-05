"""Run existing extension fixture stages against the isolated E2E tenant."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from tests.acceptance.extension import scenario as S
from tests.acceptance.extension import scenario_r as R

for name in sys.argv[1:]:
    (R.STAGES.get(name) or S.STAGES[name])()
