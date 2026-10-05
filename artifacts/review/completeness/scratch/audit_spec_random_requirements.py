"""Sample exactly 10 completed requirement IDs, then execute their relevant tests."""
import json
import random
import re
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[4]
scratch = Path(__file__).resolve().parent
complete = []
for line in (scratch.parent / 'SPEC_TRACE.md').read_text().splitlines():
    cells = [value.strip() for value in line.split('|')]
    if len(cells) == 11 and re.fullmatch('R[0-9]{2}', cells[1]) and cells[8] == '완료':
        complete.append(cells[1])
selected = random.Random(20261005).sample(complete, 10)
tests = {
    'R15': 'tests/integration/test_authz_matrix.py::test_request_detail_redacts_revision_text',
    'R26': 'tests/integration/test_judgment_graph.py::test_path_both_directions_with_depth_and_limits',
    'R08': 'tests/integration/test_policy_versions.py::test_publish_diff_audit_snapshot_and_rollback',
    'R10': 'tests/integration/test_sse_events.py::test_stream_order_resume_scope_and_snapshot',
    'R04': 'tests/integration/test_judgment_service.py::test_fixed_policy_survives_new_active_version',
    'R03': 'tests/integration/test_judgment_service.py::test_reanalysis_preserves_previous_judgment',
    'R25': 'tests/integration/test_judgment_graph.py::test_rule_graph_matches_stored_nodes_and_edges_exactly',
    'R16': 'src/lib/motion.test.tsx',
    'R02': 'tests/unit/test_parsers.py::test_corruption_spoof_and_size_rejection',
    'R12': 'tests/integration/test_observe_api.py::test_observe_reads_saved_steps_reviews_and_real_topology',
    'R20': 'tests/integration/test_candidates.py::test_three_support_cases_generate_idempotent_candidate_without_config_write',
    'R21': 'tests/integration/test_rules_integration.py::test_role_matrix_and_state_transitions',
    'R19': 'tests/integration/test_review_assignment.py::test_correction_preserves_original_and_relationships',
    'R05': 'tests/integration/test_judgment_service.py::test_real_span_citation_is_persisted_with_probability',
    'R09': 'tests/integration/test_observe_api.py::test_observe_reads_saved_steps_reviews_and_real_topology',
    'R22': 'tests/integration/test_rules_integration.py::test_publication_application_stop_revert_and_restart',
    'R23': 'tests/integration/test_shadow_api.py::test_shadow_stores_validation_without_business_mutation',
}
commands = [
    ('backend', ['.venv/bin/pytest', '-vv', *[tests[key] for key in selected if key != 'R16']]),
    ('frontend', ['npx', 'vitest', 'run', tests['R16'], '--reporter=verbose']),
]
(scratch / 'audit-spec-random-requirements.json').write_text(json.dumps({'seed': 20261005, 'population': complete, 'selected': selected, 'tests': {key: tests[key] for key in selected}, 'commands': commands}, ensure_ascii=False, indent=2) + '\n')
codes = []
for directory, command in commands:
    log = scratch / f'audit-spec-random-requirements-{directory}.log'
    with log.open('w') as output:
        result = subprocess.run(command, cwd=root / directory, stdout=output, stderr=subprocess.STDOUT)
    codes.append(result.returncode)
    print(log.read_text())
raise SystemExit(max(codes))
