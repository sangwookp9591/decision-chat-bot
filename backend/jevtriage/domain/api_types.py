"""Shared API integer limits compatible with Neo4j's signed 64-bit integers."""
from typing import Annotated

from pydantic import Field

Int64 = Annotated[int, Field(ge=-(2**63), le=2**63-1)]
