"""Production database access must pass through managed transaction helpers."""
import ast
from pathlib import Path

PACKAGE = Path(__file__).parents[2] / "ildongi"
ALLOWED = {PACKAGE / "db" / "driver.py", PACKAGE / "db" / "tx.py"}


def test_no_direct_driver_access_outside_database_boundary():
    violations = []
    for path in PACKAGE.rglob("*.py"):
        if path in ALLOWED:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (isinstance(node, ast.ImportFrom) and node.module == "ildongi.db.driver"
                    and any(alias.name == "get_driver" for alias in node.names)):
                violations.append(f"{path.relative_to(PACKAGE)}:{node.lineno}: imports get_driver")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "session":
                violations.append(f"{path.relative_to(PACKAGE)}:{node.lineno}: calls session()")
    assert not violations, "Direct driver access found:\n" + "\n".join(violations)
