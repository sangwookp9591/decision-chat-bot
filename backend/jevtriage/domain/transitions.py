"""Explicit legal state changes; terminal states cannot be reopened."""

from enum import StrEnum

from jevtriage.domain.models import (
    JobStatus,
    PolicyStatus,
    RequestStatus,
    ReviewStatus,
    RuleCandidateStatus,
    RuleDecisionStatus,
    RuleVersionStatus,
    RunStatus,
    StepStatus,
    TaskStatus,
)

TRANSITIONS: dict[type[StrEnum], dict[StrEnum, set[StrEnum]]] = {
    RequestStatus: {
        RequestStatus.RECEIVED: {RequestStatus.NEEDS_INPUT, RequestStatus.PROCESSING, RequestStatus.FAILED},
        RequestStatus.NEEDS_INPUT: {RequestStatus.PROCESSING, RequestStatus.REJECTED, RequestStatus.FAILED},
        RequestStatus.PROCESSING: {RequestStatus.AWAITING_REVIEW, RequestStatus.ASSIGNED, RequestStatus.NEEDS_INPUT, RequestStatus.FAILED},
        RequestStatus.AWAITING_REVIEW: {RequestStatus.ASSIGNED, RequestStatus.REJECTED, RequestStatus.NEEDS_INPUT, RequestStatus.FAILED},
        RequestStatus.FAILED: {RequestStatus.PROCESSING},
    },
    RunStatus: {
        RunStatus.PENDING: {RunStatus.RUNNING, RunStatus.CANCELLED},
        RunStatus.RUNNING: {RunStatus.JUDGMENT_SAVED, RunStatus.FAILED, RunStatus.CANCELLED},
    },
    StepStatus: {
        StepStatus.PENDING: {StepStatus.RUNNING, StepStatus.SKIPPED, StepStatus.WAITING_HUMAN},
        StepStatus.RUNNING: {StepStatus.SUCCEEDED, StepStatus.FAILED, StepStatus.WAITING_HUMAN},
        StepStatus.WAITING_HUMAN: {StepStatus.RUNNING, StepStatus.SKIPPED},
    },
    ReviewStatus: {ReviewStatus.PENDING: {ReviewStatus.APPROVED, ReviewStatus.APPROVED_WITH_CHANGES, ReviewStatus.REJECTED, ReviewStatus.NEEDS_INPUT}},
    TaskStatus: {
        TaskStatus.PENDING: {TaskStatus.BLOCKED, TaskStatus.IN_PROGRESS},
        TaskStatus.BLOCKED: {TaskStatus.PENDING, TaskStatus.IN_PROGRESS},
        TaskStatus.IN_PROGRESS: {TaskStatus.BLOCKED, TaskStatus.COMPLETED},
    },
    PolicyStatus: {PolicyStatus.VALIDATED: {PolicyStatus.ACTIVE}, PolicyStatus.ACTIVE: {PolicyStatus.SUPERSEDED}},
    JobStatus: {JobStatus.PENDING: {JobStatus.RUNNING, JobStatus.CANCELLED}, JobStatus.RUNNING: {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}},
    RuleCandidateStatus: {RuleCandidateStatus.PROPOSED: {RuleCandidateStatus.NEEDS_REVIEW, RuleCandidateStatus.INSUFFICIENT_DATA}, RuleCandidateStatus.INSUFFICIENT_DATA: {RuleCandidateStatus.NEEDS_REVIEW}},
    RuleDecisionStatus: {},
    RuleVersionStatus: {RuleVersionStatus.VALIDATING: {RuleVersionStatus.VALIDATED}, RuleVersionStatus.VALIDATED: {RuleVersionStatus.PUBLISHED}, RuleVersionStatus.PUBLISHED: {RuleVersionStatus.STOPPED, RuleVersionStatus.ROLLED_BACK}},
}


class InvalidTransition(ValueError):
    pass


def assert_transition(current: StrEnum, target: StrEnum) -> None:
    if type(current) is not type(target) or target not in TRANSITIONS[type(current)].get(current, set()):
        raise InvalidTransition(f"{type(current).__name__}: {current} -> {target}")
