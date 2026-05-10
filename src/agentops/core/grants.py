"""Capability Grant lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from agentops.core.errors import AgentOpsError
from agentops.models.grants import GRANT_BINDING_FIELDS, GRANT_CONTEXT_FIELDS
from agentops.storage.repository import InMemoryRepository


def issue_capability_grant(
    approval_id: str,
    grant_request: dict[str, Any],
    repository: InMemoryRepository,
    *,
    ttl_seconds: int = 900,
    now: datetime | None = None,
) -> dict[str, Any]:
    approval = repository.get_approval(approval_id)
    if not approval:
        raise AgentOpsError("APPROVAL_NOT_FOUND", "Approval does not exist.")
    if approval["status"] != "approved":
        raise AgentOpsError(
            "GRANT_APPROVAL_NOT_APPROVED", "Only approved approvals can issue grants."
        )

    _validate_approval_binding(approval, grant_request)

    now = now or datetime.now(UTC)
    grant = {
        "grant_id": grant_request.get("grant_id", f"grant_{approval_id}"),
        "decision_id": grant_request.get(
            "decision_id", f"decision_{approval['policy_check_id']}"
        ),
        "approval_id": approval_id,
        "policy_check_id": approval["policy_check_id"],
        "action": approval["action"],
        "requester": approval["requester"],
        "agent_id": approval["agent_id"],
        "version": _grant_context_value(approval, grant_request, "version"),
        "artifact_hash": _grant_context_value(
            approval, grant_request, "artifact_hash", default="sha256:unknown"
        ),
        "installation_id": _grant_context_value(
            approval, grant_request, "installation_id"
        ),
        "device_id": _grant_context_value(approval, grant_request, "device_id"),
        "user_id": _grant_context_value(
            approval,
            grant_request,
            "user_id",
            default=str(approval.get("requester") or ""),
        ),
        "session_id": _grant_context_value(approval, grant_request, "session_id"),
        "run_id": _grant_context_value(approval, grant_request, "run_id"),
        "skill_id": approval.get("skill_id"),
        "resource_scope": dict(approval["resource_scope"]),
        "policy_version": approval["policy_version"],
        "remaining_uses": _remaining_uses(grant_request.get("remaining_uses", 1)),
        "offline_allowed": bool(grant_request.get("offline_allowed", False)),
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat(),
        "status": "active",
        "signature": grant_request.get("signature", f"sig_grant_{approval_id}"),
        "key_id": grant_request.get("key_id", "agentops-local-key"),
        "audit_id": f"audit_grant_{approval_id}",
    }
    return repository.store_grant(grant)


def consume_capability_grant(
    grant_id: str,
    policy_request: dict[str, Any],
    repository: InMemoryRepository,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    grant = repository.consume_grant_atomically(
        grant_id,
        lambda stored_grant: _consume_grant_use(stored_grant, policy_request, now),
    )
    if not grant:
        raise AgentOpsError("GRANT_NOT_FOUND", "Capability Grant does not exist.")

    remaining_uses_after = _remaining_uses(grant.get("remaining_uses", 0))
    consumption = {
        "consumption_id": (
            f"consume_{grant_id}_{policy_request.get('run_id', 'run')}"
            f"_{remaining_uses_after}"
        ),
        "grant_id": grant_id,
        "policy_check_id": policy_request.get(
            "policy_check_id", f"pcheck_{policy_request['run_id']}"
        ),
        "consumed_at": now.isoformat(),
        "resource_scope": dict(policy_request["resource_scope"]),
        "remaining_uses_after": remaining_uses_after,
        "audit_id": f"audit_consume_{grant_id}",
    }
    return repository.store_grant_consumption(consumption)


def _consume_grant_use(
    grant: dict[str, Any], policy_request: dict[str, Any], now: datetime
) -> dict[str, Any]:
    if grant["status"] == "revoked":
        raise AgentOpsError(
            "GRANT_REVOKED",
            "Capability Grant is revoked.",
            denied_scope="grant.status",
            audit_id=grant["audit_id"],
        )
    if grant["status"] == "expired" or _parse_time(grant["expires_at"]) <= now:
        raise AgentOpsError(
            "GRANT_EXPIRED",
            "Capability Grant is expired.",
            denied_scope="grant.expires_at",
            audit_id=grant["audit_id"],
        )
    remaining_uses = _remaining_uses(grant.get("remaining_uses", 1))
    if remaining_uses <= 0:
        raise AgentOpsError(
            "GRANT_EXHAUSTED",
            "Capability Grant has no remaining uses.",
            denied_scope="grant.remaining_uses",
            audit_id=grant["audit_id"],
        )
    if not _request_matches_grant(grant, policy_request):
        raise AgentOpsError(
            "GRANT_SCOPE_MISMATCH",
            "Capability Grant does not match requested scope.",
            denied_scope="grant.resource_scope",
            audit_id=grant["audit_id"],
        )

    remaining_uses_after = remaining_uses - 1
    grant["remaining_uses"] = remaining_uses_after
    return grant


def revoke_capability_grant(
    grant_id: str,
    repository: InMemoryRepository,
    *,
    now: datetime | None = None,
    actor: str = "system",
    reason: str = "",
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    grant = repository.get_grant(grant_id)
    if not grant:
        raise AgentOpsError("GRANT_NOT_FOUND", "Capability Grant does not exist.")
    grant["status"] = "revoked"
    grant["revoked_at"] = now.isoformat()
    grant["revoked_by"] = actor
    grant["revocation_reason"] = reason
    return repository.update_grant(grant)


def build_grant_lifecycle(
    grant_id: str, repository: InMemoryRepository, *, now: datetime | None = None
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    grant = repository.get_grant(grant_id)
    if not grant:
        raise AgentOpsError("GRANT_NOT_FOUND", "Capability Grant does not exist.")
    consumptions = repository.grant_consumption_records(grant_id)
    status = _grant_lifecycle_status(grant, now)
    affected_runs = sorted({str(grant["run_id"])} if grant.get("run_id") else set())
    affected_sessions = sorted(
        {str(grant.get("session_id"))} if grant.get("session_id") else set()
    )
    offline_allowed = bool(grant.get("offline_allowed", False))
    owner_notification_state = (
        "pending" if status in {"revoked", "expired"} else "not_required"
    )
    return {
        "schema_version": "grant_lifecycle.v1",
        "grant_id": grant_id,
        "status": status,
        "binding": {
            field: grant.get(field)
            for field in (
                "approval_id",
                "policy_check_id",
                "action",
                "requester",
                "agent_id",
                "version",
                "artifact_hash",
                "installation_id",
                "device_id",
                "user_id",
                "session_id",
                "run_id",
                "skill_id",
                "resource_scope",
                "policy_version",
            )
        },
        "remaining_uses": _remaining_uses(grant.get("remaining_uses", 0)),
        "expires_at": grant.get("expires_at", ""),
        "revoked_at": grant.get("revoked_at", ""),
        "revoked_by": grant.get("revoked_by", ""),
        "revocation_reason": grant.get("revocation_reason", ""),
        "consumption_summary": {
            "consumption_count": len(consumptions),
            "last_consumed_at": consumptions[-1]["consumed_at"] if consumptions else "",
        },
        "impact_summary": {
            "affected_runs": affected_runs,
            "affected_sessions": affected_sessions,
            "offline_allowed": offline_allowed,
            "owner_notification_state": owner_notification_state,
        },
        "summary": {
            "raw_payload_access": "forbidden",
            "scope_expansion_allowed": False,
        },
        "audit_id": grant.get("audit_id", f"audit_grant_{grant_id}"),
    }


def _validate_approval_binding(
    approval: dict[str, Any], grant_request: dict[str, Any]
) -> None:
    for field in GRANT_BINDING_FIELDS:
        if grant_request.get(field, approval.get(field)) != approval.get(field):
            error_code = (
                "GRANT_SCOPE_ESCALATION_DENIED"
                if field == "resource_scope"
                else "GRANT_APPROVAL_BINDING_MISMATCH"
            )
            raise AgentOpsError(
                error_code,
                "Grant request must match approved policy request.",
                audit_id=approval["audit_id"],
            )
    for field in GRANT_CONTEXT_FIELDS:
        approved_value = _approval_context_value(approval, field)
        requested_value = grant_request.get(field)
        if approved_value not in (None, "") and requested_value not in (
            None,
            "",
            approved_value,
        ):
            raise AgentOpsError(
                "GRANT_APPROVAL_BINDING_MISMATCH",
                "Grant request must match approved runtime context.",
                audit_id=approval["audit_id"],
            )


def _grant_lifecycle_status(grant: dict[str, Any], now: datetime) -> str:
    if grant.get("status") == "revoked":
        return "revoked"
    if grant.get("status") == "expired" or _parse_time(grant["expires_at"]) <= now:
        return "expired"
    if _remaining_uses(grant.get("remaining_uses", 0)) <= 0:
        return "exhausted"
    return "active"


def _request_matches_grant(
    grant: dict[str, Any], policy_request: dict[str, Any]
) -> bool:
    for field in GRANT_BINDING_FIELDS:
        if grant.get(field) != policy_request.get(field):
            return False
    for field in GRANT_CONTEXT_FIELDS:
        grant_value = grant.get(field)
        request_value = policy_request.get(field)
        if field == "version":
            request_value = request_value or policy_request.get("agent_version")
        if field == "user_id":
            request_value = request_value or policy_request.get("requester")
        if not _context_value_matches(field, grant_value, request_value):
            return False
    return True


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _approval_context_value(approval: dict[str, Any], field: str) -> Any:
    if field == "version":
        return approval.get("version") or approval.get("agent_version")
    if field == "user_id":
        return approval.get("user_id") or approval.get("requester")
    return approval.get(field)


def _grant_context_value(
    approval: dict[str, Any],
    grant_request: dict[str, Any],
    field: str,
    *,
    default: Any = "",
) -> Any:
    value = _approval_context_value(approval, field)
    if value in (None, ""):
        value = grant_request.get(field)
    if value in (None, ""):
        return default
    return value


def _remaining_uses(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _context_value_matches(field: str, grant_value: Any, request_value: Any) -> bool:
    if grant_value in (None, ""):
        return True
    if request_value in (None, ""):
        return field == "artifact_hash" and grant_value == "sha256:unknown"
    return grant_value == request_value
