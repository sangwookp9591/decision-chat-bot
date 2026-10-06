"""Compatibility exports for rule application now owned by the domain layer."""

from ildongi.domain.rules import (
    CLASS_VALUES,
    ORGANIZATIONS,
    TARGETS,
    RuleInvariantError,
    apply_rules,
    context_rules_for,
    normalize_for_match,
    text_matches,
    validate_rule,
    validate_rule_or_raise,
)

__all__ = [
    "CLASS_VALUES", "ORGANIZATIONS", "TARGETS", "RuleInvariantError",
    "apply_rules", "context_rules_for", "normalize_for_match", "text_matches", "validate_rule", "validate_rule_or_raise",
]
