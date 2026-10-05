"""Run unchanged QA-C-03/04/06 test functions with an in-process real-DB harness."""
import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="module")

ORIGINAL = Path(__file__).parents[2] / 'qa-full' / 'qa-c' / 'repro'
EVIDENCE = Path(__file__).parents[1] / 'original-evidence'

for name, functions in [
    ('test_api_robustness', ['test_oversized_integer_never_causes_500',
                             'test_nested_review_changes_are_validated_before_service']),
    ('test_review_queue_starvation', ['test_authorized_review_survives_newer_other_org_reviews']),
]:
    spec = importlib.util.spec_from_file_location(name, ORIGINAL / (name+'.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.EVIDENCE = EVIDENCE
    for function in functions:
        globals()[function] = getattr(module, function)
