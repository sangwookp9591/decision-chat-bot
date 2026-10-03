"""JSON encoding for Neo4j temporal values that reach the API inside raw record dicts.

Without this, FastAPI serializes ``neo4j.time.DateTime`` through its private attributes
(``{"_DateTime__date": ...}``), which clients cannot parse (observed in playback ``at``,
request ``created_at`` and task ``created_at``). Importing the module registers the encoders.
"""
from fastapi.encoders import ENCODERS_BY_TYPE
from neo4j.time import Date, DateTime, Duration, Time

ENCODERS_BY_TYPE[DateTime] = lambda value: value.iso_format()
ENCODERS_BY_TYPE[Date] = lambda value: value.iso_format()
ENCODERS_BY_TYPE[Time] = lambda value: value.iso_format()
ENCODERS_BY_TYPE[Duration] = lambda value: value.iso_format()
