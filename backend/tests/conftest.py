"""Test-wide transaction safety settings."""

import os

os.environ["JEVTRIAGE_STRICT_TENANT"] = "1"
