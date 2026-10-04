"""Executable boundaries for code paths that previously bypassed feature stores."""

import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[2] / "jevtriage"


def imports_in(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}


def test_api_modules_do_not_import_database_access():
    api_paths = [*PACKAGE.rglob("api.py"), *PACKAGE.rglob("*_api.py"),
                 PACKAGE / "judgment" / "progress.py"]
    for path in api_paths:
        assert not {"jevtriage.db.tx", "jevtriage.db.driver"} & imports_in(path), path
        assert "tx.run(" not in path.read_text(encoding="utf-8"), path
    for path in PACKAGE.rglob("router.py"):
        assert not {"jevtriage.db.tx", "jevtriage.db.driver"} & imports_in(path), path
        assert "tx.run(" not in path.read_text(encoding="utf-8"), path


def test_auth_router_uses_public_auth_boundary():
    source = (PACKAGE / "auth" / "router.py").read_text(encoding="utf-8")
    assert "_token_hash" not in source
    assert "session.run" not in source


def test_modules_do_not_import_other_modules_private_functions():
    for path in PACKAGE.rglob("*.py"):
        module = "jevtriage." + ".".join(path.relative_to(PACKAGE).with_suffix("").parts)
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            if node.module.startswith("jevtriage.") and node.module != module:
                assert not [name.name for name in node.names if name.name.startswith("_")], path


def test_rule_validation_is_shared_domain_logic():
    for name in ("judgment/service.py", "policy/service.py"):
        assert "jevtriage.learning.apply" not in (PACKAGE / name).read_text(encoding="utf-8")


def test_policy_mask_categories_are_shared_domain_data():
    assert "jevtriage.judgment.masking" not in (
        PACKAGE / "policy" / "service.py"
    ).read_text(encoding="utf-8")


def test_review_does_not_depend_on_judgment_package():
    for path in (PACKAGE / "review").glob("*.py"):
        assert not any(name.startswith("jevtriage.judgment") for name in imports_in(path)), path


def test_domain_run_compatibility_module_has_no_policy_logic():
    assert not any(
        name.startswith("jevtriage.policy")
        for name in imports_in(PACKAGE / "domain" / "runs.py")
    )


def test_database_layer_does_not_import_policy_package():
    for path in (PACKAGE / "db").glob("*.py"):
        assert not any(name.startswith("jevtriage.policy") for name in imports_in(path)), path


def test_ingest_does_not_import_worker_runtime():
    assert "jevtriage.jobs.worker" not in (
        PACKAGE / "ingest" / "service.py"
    ).read_text(encoding="utf-8")


def test_auth_policy_uses_shared_principal_type():
    assert "jevtriage.auth.core" not in imports_in(PACKAGE / "auth" / "policy.py")


def test_runtime_modules_have_no_local_jevtriage_imports():
    for name in ("auth/core.py", "judgment/service.py", "ingest/service.py", "db/events.py"):
        path = PACKAGE / name
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert not [
                    child.module for child in ast.walk(node)
                    if isinstance(child, ast.ImportFrom)
                    and (child.module or "").startswith("jevtriage.")
                ], path


def test_feature_modules_use_other_features_public_services():
    for path in PACKAGE.rglob("*.py"):
        owner = path.relative_to(PACKAGE).parts[0]
        for imported in imports_in(path):
            parts = imported.split(".")
            if len(parts) >= 3 and parts[0] == "jevtriage" and parts[2] in {"store", "trace_store"}:
                assert owner == parts[1], (path, imported)


def test_journal_batcher_does_not_import_writer():
    assert "jevtriage.journal.writer" not in imports_in(PACKAGE / "journal" / "group_commit.py")


def test_evaluation_router_service_store_boundary():
    assert (PACKAGE / "evaluation" / "api.py").exists()
    assert "jevtriage.db.tx" not in imports_in(PACKAGE / "evaluation" / "service.py")
