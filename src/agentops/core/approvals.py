"""Approval lifecycle state machine."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from agentops.core.errors import AgentOpsError
from agentops.models.approvals import (
    APPROVAL_ACTION_TO_STATUS,
    APPROVAL_TERMINAL_STATUSES,
)
from agentops.storage.repository import InMemoryRepository


def create_approval(
    policy_request: dict[str, Any],
    policy_decision: dict[str, Any],
    repository: InMemoryRepository,
    *,
    approver_scope: str,
    reason: str,
    supplemental_materials: list[str] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    if policy_decision["decision"] != "approval_required":
        raise AgentOpsError(
            "APPROVAL_NOT_REQUIRED",
            "Only approval_required decisions can create approvals.",
        )

    now = now or datetime.now(UTC)
    approval_id = (
        policy_decision.get("required_approval_id")
        or f"approval_{policy_request['run_id']}"
    )
    approval = {
        "approval_id": approval_id,
        "policy_check_id": policy_request.get(
            "policy_check_id", f"pcheck_{policy_request['run_id']}"
        ),
        "action": policy_request["action"],
        "requester": policy_request["requester"],
        "approver_scope": approver_scope,
        "reason": reason,
        "affected_actions": [policy_request["action"]],
        "agent_id": policy_request["agent_id"],
        "version": policy_request.get("version") or policy_request.get("agent_version"),
        "artifact_hash": policy_request.get("artifact_hash", ""),
        "installation_id": policy_request.get("installation_id", ""),
        "device_id": policy_request.get("device_id", ""),
        "user_id": policy_request.get("user_id") or policy_request["requester"],
        "session_id": policy_request.get("session_id", ""),
        "run_id": policy_request.get("run_id", ""),
        "skill_id": policy_request.get("skill_id"),
        "resource_scope": dict(policy_request["resource_scope"]),
        "policy_version": policy_request["policy_version"],
        "supplemental_materials": supplemental_materials or [],
        "status": "pending",
        "sla_due_at": (now + timedelta(minutes=60)).isoformat(),
        "created_at": now.isoformat(),
        "audit_id": f"audit_{approval_id}",
    }
    return repository.store_approval(approval)


def decide_approval(
    approval_id: str,
    *,
    action: str,
    actor: str,
    reason: str,
    repository: InMemoryRepository,
    now: datetime | None = None,
    break_glass: bool = False,
    break_glass_reason: str = "",
    required_materials: list[str] | None = None,
    supplemental_materials: list[str] | None = None,
    notification_intent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    approval = repository.get_approval(approval_id)
    if not approval:
        raise AgentOpsError("APPROVAL_NOT_FOUND", "Approval does not exist.")
    state_before = approval["status"]
    if approval["status"] in APPROVAL_TERMINAL_STATUSES:
        raise AgentOpsError(
            "APPROVAL_STATE_INVALID", "Terminal approval cannot transition."
        )
    if action not in APPROVAL_ACTION_TO_STATUS:
        raise AgentOpsError(
            "APPROVAL_ACTION_UNSUPPORTED", "Unsupported approval action."
        )
    if action == "approve" and actor == approval["requester"] and not break_glass:
        raise AgentOpsError(
            "APPROVAL_SELF_APPROVAL_DENIED",
            "Requester cannot approve their own high-risk action.",
            denied_scope="approval.self",
            audit_id=f"audit_{approval_id}",
        )
    if action == "approve" and break_glass and not break_glass_reason:
        raise AgentOpsError(
            "APPROVAL_BREAK_GLASS_REASON_REQUIRED",
            "Break-glass approval requires an audit reason.",
            denied_scope="approval.break_glass_reason",
            audit_id=f"audit_{approval_id}",
        )

    now = now or datetime.now(UTC)
    status = APPROVAL_ACTION_TO_STATUS[action]
    approval["status"] = status
    approval["decided_at"] = now.isoformat()
    if action == "request_input":
        approval["required_materials"] = list(required_materials or [])
        if supplemental_materials is not None:
            approval["supplemental_materials"] = list(supplemental_materials)
    if action == "escalate":
        approval["sla_state"] = "escalated"
    if action == "approve" and break_glass:
        approval["break_glass"] = True
        approval["break_glass_reason"] = break_glass_reason
    repository.store_approval(approval)

    operation = "break_glass_approve" if action == "approve" and break_glass else action
    decision = {
        "approval_decision_id": f"approval_decision_{approval_id}_{action}",
        "operation_id": f"approval_operation_{approval_id}_{operation}",
        "approval_id": approval_id,
        "actor": actor,
        "action": action,
        "operation": operation,
        "reason": reason,
        "state_before": state_before,
        "state_after": status,
        "summary": {
            "raw_payload_access": "forbidden",
            "break_glass": bool(action == "approve" and break_glass),
        },
        "created_at": now.isoformat(),
        "audit_id": f"audit_{approval_id}_{action}",
    }
    if required_materials is not None:
        decision["required_materials"] = list(required_materials)
    if supplemental_materials is not None:
        decision["supplemental_materials"] = list(supplemental_materials)
    if notification_intent is not None:
        decision["notification_intent"] = dict(notification_intent)
    if break_glass_reason:
        decision["break_glass_reason"] = break_glass_reason
    repository.store_approval_decision(decision)
    return approval
