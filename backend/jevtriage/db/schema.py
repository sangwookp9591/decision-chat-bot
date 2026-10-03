"""Idempotent Neo4j schema installation."""

import asyncio

from jevtriage.db.driver import close_driver, get_driver

LABELS = (
    "Request", "InputRevision", "Run", "RunStep", "Job", "Review", "ReviewDecision",
    "Assignment", "Task", "Team", "Policy", "ConfigVersion", "Event", "EventCounter",
    "Idempotency", "Audit", "Attachment", "EvidenceSpan", "ModelOutput", "Correction",
    "RuleCandidate", "RuleDecision", "RuleVersion", "ValidationRun", "RuleApplication",
)


async def apply_schema() -> None:
    driver = await get_driver()
    async with driver.session() as session:
        # Public learning IDs can repeat across tenants. Migrate earlier global
        # uniqueness constraints before installing tenant scoped replacements.
        for label in ("RuleCandidate", "RuleVersion"):
            await (await session.run(
                f"DROP CONSTRAINT {label.lower()}_id_unique IF EXISTS"
            )).consume()
            await (await session.run(
                f"CREATE CONSTRAINT {label.lower()}_tenant_id_unique IF NOT EXISTS "
                f"FOR (n:{label}) REQUIRE (n.tenant_id, n.id) IS UNIQUE"
            )).consume()
        for label in LABELS:
            if label in {"RuleCandidate", "RuleVersion"}:
                continue
            await (await session.run(
                f"CREATE CONSTRAINT {label.lower()}_id_unique IF NOT EXISTS "
                f"FOR (n:{label}) REQUIRE n.id IS UNIQUE"
            )).consume()
        for name, label, fields in (
            ("login_attempt_tenant_email_unique", "LoginAttempt", "tenant_id, email"),
            ("assignment_request_unique", "Assignment", "tenant_id, request_id"),
            ("task_draft_unique", "Task", "assignment_id, draft_task_id"),
            ("idempotency_key_unique", "Idempotency", "tenant_id, scope, key"),
            ("event_counter_tenant_unique", "EventCounter", "tenant_id"),
        ):
            properties = ", ".join(f"n.{field.strip()}" for field in fields.split(","))
            await (await session.run(
                f"CREATE CONSTRAINT {name} IF NOT EXISTS FOR (n:{label}) "
                f"REQUIRE ({properties}) IS UNIQUE"
            )).consume()
        for name, label, fields in (
            ("request_tenant_created", "Request", "tenant_id, created_at"),
            ("run_tenant_request", "Run", "tenant_id, request_id"),
            ("job_tenant_status", "Job", "tenant_id, status"),
            ("event_tenant_seq", "Event", "tenant_id, seq"),
            ("review_tenant_status", "Review", "tenant_id, status"),
            ("task_tenant_status", "Task", "tenant_id, status"),
        ):
            properties = ", ".join(f"n.{field.strip()}" for field in fields.split(","))
            await (await session.run(
                f"CREATE INDEX {name} IF NOT EXISTS FOR (n:{label}) ON ({properties})"
            )).consume()


async def main() -> None:
    try:
        await apply_schema()
    finally:
        await close_driver()


if __name__ == "__main__":
    asyncio.run(main())
