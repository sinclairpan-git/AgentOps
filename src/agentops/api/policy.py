"""PolicyDecision contract implementation."""

from __future__ import annotations

from typing import Any

from agentops.core.errors import AgentOpsError
from agentops.core.policy_engine import evaluate_policy_check as _evaluate_policy_check
from agentops.models.policy import HIGH_RISK_ACTIONS


def evaluate_policy_check(request: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    return _evaluate_policy_check(request, **kwargs)


def evaluate_policy_decision(
    *,
    action: str,
    resource_scope: dict[str, Any] | None = None,
    service_available: bool = True,
    policy_version: str = "policy.v1",
) -> dict[str, Any]:
    if action in HIGH_RISK_ACTIONS and not resource_scope:
        raise AgentOpsError("POLICY_SCOPE_REQUIRED", "High-risk actions require resource_scope.")

    if action in HIGH_RISK_ACTIONS and not service_available:
        decision = "block"
        fallback_action = "require_online"
        reason = "Policy service unavailable for high-risk action."
    elif action in HIGH_RISK_ACTIONS:
        decision = "approval_required"
        fallback_action = "require_online"
        reason = "High-risk action requires approval in stage 1."
    else:
        decision = "allow"
        fallback_action = "allow"
        reason = "Low-risk action allowed."

    return {
        "decision": decision,
        "fallback_action": fallback_action,
        "policy_version": policy_version,
        "decision_reason": reason,
        "audit_id": "audit_policy_decision",
    }
