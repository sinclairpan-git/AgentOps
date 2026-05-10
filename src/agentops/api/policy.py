"""PolicyDecision contract implementation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from agentops.core.errors import AgentOpsError
from agentops.core.policy_engine import evaluate_policy_check as _evaluate_policy_check
from agentops.models.policy import HIGH_RISK_ACTIONS
from agentops.storage.repository import InMemoryRepository


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
    ttl = _cap_ttl_by_valid_until(ttl, decision, _decision_now(kwargs))
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


def register_policy_set_version(
    repository: InMemoryRepository,
    *,
    policy_set_version: str,
    state: str,
    risk_templates: list[str],
    fallback_action: str,
    traffic_scope: dict[str, Any] | None = None,
    owner: str = "Security/IAM",
    rollback_from: str = "",
    rollback_reason: str = "",
    now: datetime | None = None,
) -> dict[str, Any]:
    if state not in {"draft", "canary", "active", "rolled_back", "retired"}:
        raise AgentOpsError(
            "POLICY_VERSION_INVALID", "Policy set version state is unsupported."
        )
    if fallback_action not in {"allow", "warn", "require_online", "block"}:
        raise AgentOpsError(
            "POLICY_VERSION_INVALID", "Policy fallback action is unsupported."
        )

    now = now or datetime.now(UTC)
    record = {
        "schema_version": "policy_set_version.v1",
        "policy_set_version": policy_set_version,
        "state": state,
        "risk_templates": list(risk_templates),
        "fallback_action": fallback_action,
        "traffic_scope": dict(traffic_scope or {}),
        "owner": owner,
        "rollback_from": rollback_from,
        "rollback_reason": rollback_reason,
        "deny_priority": {
            "deny_overrides_grant": True,
            "explanation": "deny/block policy signals have priority over active grants.",
        },
        "summary": {
            "raw_payload_access": "forbidden",
            "rollback_recorded": bool(rollback_from or rollback_reason),
        },
        "registered_at": now.isoformat(),
        "audit_id": f"audit_policy_set_{policy_set_version}",
    }
    return repository.store_policy_set_version(record)


def build_policy_operations_projection(
    repository: InMemoryRepository,
) -> dict[str, Any]:
    versions = sorted(
        repository.policy_set_version_records(),
        key=lambda item: str(item.get("registered_at", "")),
    )
    active_version = next(
        (
            str(item["policy_set_version"])
            for item in reversed(versions)
            if item.get("state") == "active"
        ),
        "",
    )
    return {
        "schema_version": "policy_set_version.v1",
        "active_version": active_version,
        "versions": versions,
        "summary": {
            "version_count": len(versions),
            "raw_payload_access": "forbidden",
            "deny_overrides_grant": True,
        },
        "audit_id": "audit_policy_operations_projection",
    }


def _policy_plain_language(decision: str) -> str:
    return {
        "block": "该动作被策略阻断，需要联系安全/IAM 负责人。",
        "approval_required": "该动作属于高风险操作，需要完成审批后才能继续。",
        "warn": "该动作存在风险提示，可以继续但会留下审计记录。",
        "conditional_allow": "该动作已通过限时授权，可以在授权范围内继续。",
        "allow": "该动作已通过策略检查。",
        "policy_unavailable": "策略服务暂不可用，当前动作需要等待策略检查恢复后重试。",
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


def _cap_ttl_by_valid_until(ttl: int, decision: dict[str, Any], now: datetime) -> int:
    if not decision.get("grant_id") or not decision.get("valid_until"):
        return ttl
    valid_until = _parse_policy_time(decision["valid_until"])
    if valid_until is None:
        return ttl
    remaining_seconds = int((valid_until - now).total_seconds())
    return max(0, min(ttl, remaining_seconds))


def _decision_now(kwargs: dict[str, Any]) -> datetime:
    now = kwargs.get("now")
    if isinstance(now, datetime):
        return now if now.tzinfo is not None else now.replace(tzinfo=UTC)
    return datetime.now(UTC)


def _parse_policy_time(value: Any) -> datetime | None:
    raw_value = str(value or "")
    try:
        parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


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
