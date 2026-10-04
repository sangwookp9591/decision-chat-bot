"""Idempotent Neo4j schema installation."""

import asyncio

from jevtriage.db.driver import close_driver
from jevtriage.db.tx import cross_tenant_tx

LABELS = (
    "Request", "InputRevision", "Run", "RunStep", "Job", "Review", "ReviewDecision",
    "Assignment", "Task", "Team", "Policy", "ConfigVersion", "Event", "EventCounter",
    "Idempotency", "Audit", "Attachment", "EvidenceSpan", "ModelOutput", "Correction",
    "RuleCandidate", "RuleDecision", "RuleVersion", "ValidationRun", "RuleApplication",
    "Session", "User", "Org", "Tenant", "Judgment", "Draft", "DraftTask", "RuleSeries",
    "LoginAttempt",
)
TENANT_SCOPED_IDS = frozenset({
    "RuleCandidate", "RuleVersion", "Org", "Judgment", "Draft", "DraftTask",
    "RuleSeries", "LoginAttempt",
})


async def apply_schema() -> None:
    async def migrate(tx):
        # Public learning IDs can repeat across tenants. Migrate earlier global
        # uniqueness constraints before installing tenant scoped replacements.
        for label in TENANT_SCOPED_IDS:
            await (await tx.run(
                f"DROP CONSTRAINT {label.lower()}_id_unique IF EXISTS"
            )).consume()
            await (await tx.run(
                f"CREATE CONSTRAINT {label.lower()}_tenant_id_unique IF NOT EXISTS "
                f"FOR (n:{label}) REQUIRE (n.tenant_id, n.id) IS UNIQUE"
            )).consume()
        # A uniqueness constraint owns its backing range index; migrate older
        # nonunique indexes on the same properties before installing it.
        for name in ("event_tenant_seq", "judgment_tenant_run"):
            await (await tx.run(f"DROP INDEX {name} IF EXISTS")).consume()
        for label in LABELS:
            if label in TENANT_SCOPED_IDS:
                continue
            await (await tx.run(
                f"CREATE CONSTRAINT {label.lower()}_id_unique IF NOT EXISTS "
                f"FOR (n:{label}) REQUIRE n.id IS UNIQUE"
            )).consume()
        for name, label, fields in (
            ("login_attempt_tenant_email_unique", "LoginAttempt", "tenant_id, email"),
            ("assignment_request_unique", "Assignment", "tenant_id, request_id"),
            ("task_draft_unique", "Task", "assignment_id, draft_task_id"),
            ("idempotency_key_unique", "Idempotency", "tenant_id, scope, key"),
            ("event_counter_tenant_unique", "EventCounter", "tenant_id"),
            ("session_token_hash_unique", "Session", "token_hash"),
            ("user_email_unique", "User", "email"),
            ("configversion_tenant_version_unique", "ConfigVersion", "tenant_id, version"),
            ("event_tenant_seq_unique", "Event", "tenant_id, seq"),
            ("judgment_tenant_run_unique", "Judgment", "tenant_id, run_id"),
        ):
            properties = ", ".join(f"n.{field.strip()}" for field in fields.split(","))
            await (await tx.run(
                f"CREATE CONSTRAINT {name} IF NOT EXISTS FOR (n:{label}) "
                f"REQUIRE ({properties}) IS UNIQUE"
            )).consume()
        for name, label, fields in (
            ("request_tenant_created", "Request", "tenant_id, created_at"),
            ("run_tenant_request", "Run", "tenant_id, request_id"),
            ("job_tenant_status", "Job", "tenant_id, status"),
            ("review_tenant_status", "Review", "tenant_id, status"),
            ("task_tenant_status", "Task", "tenant_id, status"),
            ("judgment_tenant_request", "Judgment", "tenant_id, request_id"),
            ("modeloutput_tenant_run", "ModelOutput", "tenant_id, run_id"),
            ("draft_tenant_run_version", "Draft", "tenant_id, run_id, draft_version"),
            ("drafttask_tenant_run", "DraftTask", "tenant_id, run_id"),
            ("evidencespan_tenant_revision", "EvidenceSpan", "tenant_id, revision_id"),
            ("runstep_tenant_run", "RunStep", "tenant_id, run_id"),
            ("event_tenant_request", "Event", "tenant_id, request_id"),
            ("job_status", "Job", "status"),
            ("job_status_lease", "Job", "status, lease_expires_at"),
            ("job_tenant_status_lease", "Job", "tenant_id, status, lease_expires_at"),
            ("review_tenant_request_status", "Review", "tenant_id, request_id, status"),
            ("task_tenant_request", "Task", "tenant_id, request_id"),
        ):
            properties = ", ".join(f"n.{field.strip()}" for field in fields.split(","))
            await (await tx.run(
                f"CREATE INDEX {name} IF NOT EXISTS FOR (n:{label}) ON ({properties})"
            )).consume()
    await cross_tenant_tx("schema.migration", migrate, write=True)


async def main() -> None:
    try:
        await apply_schema()
    finally:
        await close_driver()


if __name__ == "__main__":
    asyncio.run(main())
