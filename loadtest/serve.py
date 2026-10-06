"""Run the dedicated load-test API without verbose Neo4j query notifications."""

from copy import deepcopy
import os

import uvicorn

if __name__ == "__main__":
    config = deepcopy(uvicorn.config.LOGGING_CONFIG)
    config.setdefault("loggers", {})["neo4j"] = {"level": "ERROR"}
    uvicorn.run("ildongi.main:app", host="127.0.0.1", port=int(os.getenv("T25_API_PORT", "8125")),
                workers=2, log_config=config)
