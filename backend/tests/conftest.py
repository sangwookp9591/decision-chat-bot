"""Test-wide transaction safety settings."""

import os

os.environ["ILDONGI_STRICT_TENANT"] = "1"
