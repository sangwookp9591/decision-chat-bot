"""Executable boundaries for code paths that previously bypassed feature stores."""

import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[2] / "ildongi"


def imports_in(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}


def test_api_modules_do_not_import_database_access():
    api_paths = [*PACKAGE.rglob("api.py"), *PACKAGE.rglob("*_api.py"),
                 PACKAGE / "judgment" / "progress.py"]
    for path in api_paths:
        assert not {"ildongi.db.tx", "ildongi.db.driver"} & imports_in(path), path
        assert "tx.run(" not in path.read_text(encoding="utf-8"), path
    for path in PACKAGE.rglob("router.py"):
        assert not {"ildongi.db.tx", "ildongi.db.driver"} & imports_in(path), path
        assert "tx.run(" not in path.read_text(encoding="utf-8"), path


def test_auth_router_uses_public_auth_boundary():
    source = (PACKAGE / "auth" / "router.py").read_text(encoding="utf-8")
    assert "_token_hash" not in source
    assert "session.run" not in source


def test_modules_do_not_import_other_modules_private_functions():
    for path in PACKAGE.rglob("*.py"):
        module = "ildongi." + ".".join(path.relative_to(PACKAGE).with_suffix("").parts)
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            if node.module.startswith("ildongi.") and node.module != module:
                assert not [name.name for name in node.names if name.name.startswith("_")], path


def test_rule_validation_is_shared_domain_logic():
    for name in ("judgment/service.py", "policy/service.py"):
        assert "ildongi.learning.apply" not in (PACKAGE / name).read_text(encoding="utf-8")


def test_policy_mask_categories_are_shared_domain_data():
    assert "ildongi.judgment.masking" not in (
        PACKAGE / "policy" / "service.py"
    ).read_text(encoding="utf-8")


def test_review_does_not_depend_on_judgment_package():
    for path in (PACKAGE / "review").glob("*.py"):
        assert not any(name.startswith("ildongi.judgment") for name in imports_in(path)), path


def test_domain_run_compatibility_module_has_no_policy_logic():
    assert not any(
        name.startswith("ildongi.policy")
        for name in imports_in(PACKAGE / "domain" / "runs.py")
    )


def test_database_layer_does_not_import_policy_package():
    for path in (PACKAGE / "db").glob("*.py"):
        assert not any(name.startswith("ildongi.policy") for name in imports_in(path)), path


def test_ingest_does_not_import_worker_runtime():
    assert "ildongi.jobs.worker" not in (
        PACKAGE / "ingest" / "service.py"
    ).read_text(encoding="utf-8")


def test_auth_policy_uses_shared_principal_type():
    assert "ildongi.auth.core" not in imports_in(PACKAGE / "auth" / "policy.py")


def test_runtime_modules_have_no_local_ildongi_imports():
    for name in ("auth/core.py", "judgment/service.py", "ingest/service.py", "db/events.py"):
        path = PACKAGE / name
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert not [
                    child.module for child in ast.walk(node)
                    if isinstance(child, ast.ImportFrom)
                    and (child.module or "").startswith("ildongi.")
                ], path


def test_feature_modules_use_other_features_public_services():
    for path in PACKAGE.rglob("*.py"):
        owner = path.relative_to(PACKAGE).parts[0]
        for imported in imports_in(path):
            parts = imported.split(".")
            if len(parts) >= 3 and parts[0] == "ildongi" and parts[2] in {"store", "trace_store"}:
                assert owner == parts[1], (path, imported)


def test_journal_batcher_does_not_import_writer():
    assert "ildongi.journal.writer" not in imports_in(PACKAGE / "journal" / "group_commit.py")


def test_evaluation_router_service_store_boundary():
    assert (PACKAGE / "evaluation" / "api.py").exists()
    assert "ildongi.db.tx" not in imports_in(PACKAGE / "evaluation" / "service.py")
