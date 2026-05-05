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


def build_policy_requirement_summary(
    policy_decision: dict[str, Any],
    *,
    affected_actions: list[str],
    consumer_schema_version: str = "policy-summary.v1",
    return_url: str = "/agent-store",
) -> dict[str, Any]:
    if not consumer_schema_version.startswith("policy-summary.v1"):
        raise AgentOpsError(
            "POLICY_SUMMARY_SCHEMA_UNSUPPORTED",
            "Policy requirement summary schema is unsupported.",
            request_id="req_policy_summary_schema",
        )

    decision = policy_decision["decision"]
    can_ignore = decision == "warn"
    return {
        "required_by": "AgentOps Policy Service",
        "source": "agentops.policy_check",
        "issuer": "AgentOps",
        "policy_owner": "Security/IAM",
        "policy_version": policy_decision["policy_version"],
        "can_ignore": can_ignore,
        "affected_actions": affected_actions,
        "deep_links": {
            "approval_url": f"/agentops/approvals/{policy_decision.get('required_approval_id', 'new')}",
            "policy_url": f"/agentops/policies/{policy_decision['policy_version']}",
            "evidence_url": "/agentops/evidence",
            "return_url": return_url,
        },
        "plain_language": _policy_plain_language(decision),
        "primary_action": "处理审批" if decision == "approval_required" else "查看策略",
        "secondary_action": "返回 Agent Store",
        "audit_id": policy_decision["audit_id"],
    }


def _policy_plain_language(decision: str) -> str:
    return {
        "block": "该动作被策略阻断，需要联系安全/IAM 负责人。",
        "approval_required": "该动作属于高风险操作，需要完成审批后才能继续。",
        "warn": "该动作存在风险提示，可以继续但会留下审计记录。",
        "conditional_allow": "该动作已通过限时授权，可以在授权范围内继续。",
        "allow": "该动作已通过策略检查。",
    }[decision]
