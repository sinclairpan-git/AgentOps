"""PolicyDecision contract implementation."""

from __future__ import annotations

from typing import Any

from agentops.core.errors import AgentOpsError
from agentops.core.policy_engine import evaluate_policy_check as _evaluate_policy_check
from agentops.models.policy import HIGH_RISK_ACTIONS


def evaluate_policy_check(request: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    return _evaluate_policy_check(request, **kwargs)


def evaluate_policy_decision_v1(
    request: dict[str, Any], **kwargs: Any
) -> dict[str, Any]:
    decision = _evaluate_policy_check(request, **kwargs)
    policy_version = str(
        request.get("policy_set_version")
        or decision.get("policy_version")
        or request.get("policy_version")
        or "policy.v1"
    )
    request_id = str(
        request.get("policy_check_id") or f"pcheck_{request.get('run_id', 'unknown')}"
    )
    p0_decision = _p0_policy_decision(decision)
    ttl = _policy_decision_ttl(p0_decision)
    return {
        "schema_version": "policy_decision.v1",
        "decision_id": f"decision_{request_id}",
        "request_id": request_id,
        "subject": {
            "agent_id": request.get("agent_id"),
            "version": request.get("version") or request.get("agent_version"),
            "skill_id": request.get("skill_id"),
            "requester": request.get("requester"),
            "session_id": request.get("session_id"),
            "run_id": request.get("run_id"),
        },
        "resource": request.get("resource_scope") or {},
        "action": request["action"],
        "decision": p0_decision,
        "reason_code": _policy_reason_code(decision, p0_decision),
        "policy_set_version": policy_version,
        "obligations": _policy_obligations(p0_decision),
        "constraints": {
            "raw_payload_access": "forbidden",
            "agentops_executes_runtime": False,
        },
        "ttl": ttl,
        "fallback_action": str(decision["fallback_action"]),
        "audit_id": decision["audit_id"],
        "valid_until": decision.get("valid_until", ""),
        "denied_scope": decision.get("denied_scope", ""),
    }


def evaluate_policy_decision(
    *,
    action: str,
    resource_scope: dict[str, Any] | None = None,
    service_available: bool = True,
    policy_version: str = "policy.v1",
) -> dict[str, Any]:
    if action in HIGH_RISK_ACTIONS and not resource_scope:
        raise AgentOpsError(
            "POLICY_SCOPE_REQUIRED", "High-risk actions require resource_scope."
        )

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


def _p0_policy_decision(decision: dict[str, Any]) -> str:
    if decision["decision"] == "block" and decision.get("policy_state_known") is False:
        return "policy_unavailable"
    if decision["decision"] == "conditional_allow":
        return "allow"
    return str(decision["decision"])


def _policy_decision_ttl(decision: str) -> int:
    if decision in {"block", "policy_unavailable"}:
        return 0
    if decision == "approval_required":
        return 300
    if decision == "warn":
        return 600
    return 900


def _policy_reason_code(decision: dict[str, Any], p0_decision: str) -> str:
    denied_scope = str(decision.get("denied_scope") or "")
    if denied_scope == "policy.service_unavailable":
        return "policy_service_unavailable"
    if denied_scope:
        return denied_scope.replace(".", "_")
    if decision.get("grant_id"):
        return "grant_matched"
    return {
        "allow": "low_risk_allowed",
        "warn": "policy_check_degraded",
        "approval_required": "approval_required",
        "block": "policy_block",
        "policy_unavailable": "policy_service_unavailable",
    }[p0_decision]


def _policy_obligations(decision: str) -> list[str]:
    return {
        "allow": [],
        "warn": ["record_audit"],
        "approval_required": ["create_approval"],
        "block": ["stop_execution"],
        "policy_unavailable": ["retry_policy_check"],
    }[decision]
