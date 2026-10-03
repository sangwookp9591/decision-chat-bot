"""Persisted entity contracts; raw typed Jev answers remain unaltered JSON."""

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RequestStatus(StrEnum):
    RECEIVED = "received"
    NEEDS_INPUT = "needs_input"
    PROCESSING = "processing"
    AWAITING_REVIEW = "awaiting_review"
    ASSIGNED = "assigned"
    REJECTED = "rejected"
    FAILED = "failed"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    JUDGMENT_SAVED = "judgment_saved"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING_HUMAN = "waiting_human"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    APPROVED_WITH_CHANGES = "approved_with_changes"
    REJECTED = "rejected"
    NEEDS_INPUT = "needs_input"


class TaskStatus(StrEnum):
    PENDING = "pending"
    BLOCKED = "blocked"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class PolicyStatus(StrEnum):
    VALIDATED = "validated"
    ACTIVE = "active"
    SUPERSEDED = "superseded"


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RuleCandidateStatus(StrEnum):
    PROPOSED = "proposed"
    NEEDS_REVIEW = "needs_review"
    INSUFFICIENT_DATA = "insufficient_data"


class RuleDecisionStatus(StrEnum):
    APPROVED = "approved"
    SCOPE_AMENDED = "scope_amended"
    REJECTED = "rejected"


class RuleVersionStatus(StrEnum):
    VALIDATING = "validating"
    VALIDATED = "validated"
    PUBLISHED = "published"
    STOPPED = "stopped"
    ROLLED_BACK = "rolled_back"


class Entity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    tenant_id: str
    created_at: datetime
    created_by: str


class Request(Entity):
    status: RequestStatus
    active_run_id: str | None = None
    latest_revision_id: str | None = None


class InputRevision(Entity):
    request_id: str
    number: int = Field(ge=1)


class Run(Entity):
    request_id: str
    input_revision_id: str
    kind: Literal["normal", "shadow"] = "normal"
    status: RunStatus = RunStatus.PENDING
    config_version: int | None = None


class RunStep(Entity):
    run_id: str
    status: StepStatus = StepStatus.PENDING


class Review(Entity):
    request_id: str
    run_id: str
    input_revision_id: str
    draft_version: int
    review_version: int
    status: ReviewStatus = ReviewStatus.PENDING


class WorkTask(Entity):
    assignment_id: str
    draft_task_id: str
    status: TaskStatus = TaskStatus.PENDING


class Policy(Entity):
    version: int
    status: PolicyStatus


class Job(Entity):
    run_id: str
    input_revision_id: str
    status: JobStatus
    owner_id: str | None = None
    lease_generation: int = 0
    lease_expires_at: datetime | None = None


class RuleCandidate(Entity):
    status: RuleCandidateStatus
    source: Literal["ai", "human"]


class RuleDecision(Entity):
    candidate_id: str
    status: RuleDecisionStatus
    reason: str


class RuleVersion(Entity):
    rule_id: str
    version: int
    status: RuleVersionStatus
    config_version: int | None = None


class ValidationRun(Entity):
    baseline_config_version: int
    candidate_config_version: int
    sample_count: int = Field(ge=0)


class ModelOutput(Entity):
    run_id: str
    model: str
    answers: dict[str, Any]
    usage: dict[str, Any]
