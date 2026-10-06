from uuid import uuid4

PREFIXES = {
    "request": "req_", "revision": "rev_", "run": "run_", "step": "step_",
    "job": "job_", "review": "rvw_", "task": "task_", "config": "cfg_",
    "correction": "cor_", "candidate": "cand_", "rule_decision": "rdec_",
    "rule": "rule_", "validation": "val_", "attempt": "att_", "event": "evt_",
    "assignment": "asn_", "audit": "aud_", "idempotency": "idem_",
}


def new_id(kind: str) -> str:
    return PREFIXES[kind] + uuid4().hex
