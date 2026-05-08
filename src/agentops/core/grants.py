"""Capability Grant lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from agentops.core.errors import AgentOpsError
from agentops.models.grants import GRANT_BINDING_FIELDS
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
        "approval_id": approval_id,
        "policy_check_id": approval["policy_check_id"],
        "action": approval["action"],
        "requester": approval["requester"],
        "agent_id": approval["agent_id"],
        "skill_id": approval.get("skill_id"),
        "resource_scope": dict(approval["resource_scope"]),
        "policy_version": approval["policy_version"],
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat(),
        "status": "active",
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
    grant = repository.get_grant(grant_id)
    if not grant:
        raise AgentOpsError("GRANT_NOT_FOUND", "Capability Grant does not exist.")
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
    if not _request_matches_grant(grant, policy_request):
        raise AgentOpsError(
            "GRANT_SCOPE_MISMATCH",
            "Capability Grant does not match requested scope.",
            denied_scope="grant.resource_scope",
            audit_id=grant["audit_id"],
        )

    consumption = {
        "consumption_id": f"consume_{grant_id}_{policy_request.get('run_id', 'run')}",
        "grant_id": grant_id,
        "policy_check_id": policy_request.get(
            "policy_check_id", f"pcheck_{policy_request['run_id']}"
        ),
        "consumed_at": now.isoformat(),
        "resource_scope": dict(policy_request["resource_scope"]),
        "audit_id": f"audit_consume_{grant_id}",
    }
    return repository.store_grant_consumption(consumption)


def revoke_capability_grant(
    grant_id: str,
    repository: InMemoryRepository,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    grant = repository.get_grant(grant_id)
    if not grant:
        raise AgentOpsError("GRANT_NOT_FOUND", "Capability Grant does not exist.")
    grant["status"] = "revoked"
    grant["revoked_at"] = now.isoformat()
    return repository.update_grant(grant)


def _validate_approval_binding(
    approval: dict[str, Any], grant_request: dict[str, Any]
) -> None:
    for field in GRANT_BINDING_FIELDS:
        if grant_request.get(field) != approval.get(field):
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


def _request_matches_grant(
    grant: dict[str, Any], policy_request: dict[str, Any]
) -> bool:
    for field in GRANT_BINDING_FIELDS:
        if grant.get(field) != policy_request.get(field):
            return False
    return True


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
