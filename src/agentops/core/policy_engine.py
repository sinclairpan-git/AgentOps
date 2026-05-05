"""Stage-2 policy check evaluator."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from agentops.core.errors import AgentOpsError
from agentops.models.policy import HIGH_RISK_ACTIONS, POLICY_PRIORITY_DENIES


def evaluate_policy_check(
    request: dict[str, Any],
    *,
    grant: dict[str, Any] | None = None,
    governance_signals: dict[str, Any] | None = None,
    service_available: bool = True,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    action = request["action"]
    resource_scope = request.get("resource_scope")
    policy_version = request.get("policy_version", "policy.v2")

    if _is_high_risk(action, request) and not resource_scope:
        raise AgentOpsError(
            "POLICY_SCOPE_REQUIRED",
            "High-risk actions require resource_scope.",
            denied_scope="policy.resource_scope",
            audit_id="audit_policy_scope_required",
        )

    deny_signal = _first_priority_deny(governance_signals or {})
    if deny_signal:
        return _decision(
            decision="block",
            fallback_action="block",
            policy_state_known=True,
            reason=f"{deny_signal} has higher priority than grant or allow.",
            policy_version=policy_version,
            denied_scope=deny_signal,
        )

    if _is_high_risk(action, request) and not service_available:
        return _decision(
            decision="block",
            fallback_action="require_online",
            policy_state_known=False,
            reason="Policy service unavailable for high-risk action.",
            policy_version=policy_version,
            denied_scope="policy.service_unavailable",
        )

    if not service_available:
        return _decision(
            decision="warn",
            fallback_action="warn",
            policy_state_known=False,
            reason="Policy service unavailable; low-risk action is not fully verified.",
            policy_version=policy_version,
            denied_scope="policy.service_unavailable",
        )

    if grant and _grant_matches_request(grant, request, now):
        return _decision(
            decision="conditional_allow",
            fallback_action="allow",
            policy_state_known=True,
            reason="Active capability grant matches the policy check request.",
            policy_version=policy_version,
            grant_id=grant["grant_id"],
            valid_until=grant["expires_at"],
        )

    if _is_high_risk(action, request):
        return _decision(
            decision="approval_required",
            fallback_action="require_online",
            policy_state_known=True,
            reason="High-risk action requires Approval Center review.",
            policy_version=policy_version,
            required_approval_id=f"approval_pending_{request.get('run_id', 'unknown')}",
        )

    return _decision(
        decision="allow",
        fallback_action="allow",
        policy_state_known=True,
        reason="Low-risk action allowed.",
        policy_version=policy_version,
    )


def _decision(
    *,
    decision: str,
    fallback_action: str,
    policy_state_known: bool,
    reason: str,
    policy_version: str,
    grant_id: str | None = None,
    required_approval_id: str | None = None,
    valid_until: str | None = None,
    denied_scope: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "decision": decision,
        "fallback_action": fallback_action,
        "policy_state_known": policy_state_known,
        "decision_reason": reason,
        "policy_version": policy_version,
        "audit_id": f"audit_policy_{decision}",
    }
    if grant_id:
        result["grant_id"] = grant_id
    if required_approval_id:
        result["required_approval_id"] = required_approval_id
    if valid_until:
        result["valid_until"] = valid_until
    if denied_scope:
        result["denied_scope"] = denied_scope
    return result


def _first_priority_deny(governance_signals: dict[str, Any]) -> str | None:
    for signal in POLICY_PRIORITY_DENIES:
        if governance_signals.get(signal):
            return signal
    return None


def _grant_matches_request(grant: dict[str, Any], request: dict[str, Any], now: datetime) -> bool:
    if grant.get("status") != "active":
        return False
    if _parse_time(grant["expires_at"]) <= now:
        return False

    comparable_fields = ("action", "requester", "agent_id", "skill_id", "policy_version")
    for field in comparable_fields:
        if grant.get(field) != request.get(field):
            return False

    return grant.get("resource_scope") == request.get("resource_scope")


def _is_high_risk(action: str, request: dict[str, Any]) -> bool:
    return action in HIGH_RISK_ACTIONS or request.get("risk_level") in {"high", "critical"}


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
