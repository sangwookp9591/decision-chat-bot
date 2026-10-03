"""T38 extension scenario tests are excluded from default collection (`make test`).

Run explicitly: X38_RUN=1 X38_API=http://127.0.0.1:<port> X38_TENANT=<tenant> pytest tests/acceptance/extension
"""
import os

collect_ignore_glob = [] if os.getenv("X38_RUN") == "1" else ["test_*.py"]
