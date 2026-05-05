"""Evidence Vault summary and raw access state."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from agentops.core.errors import AgentOpsError
from agentops.storage.repository import InMemoryRepository


def build_evidence_vault_summary(
    *,
    evidence_id: str,
    run_id: str,
    payload_hash: str,
    redacted_summary: dict[str, Any] | None = None,
    raw_access_grant: dict[str, Any] | None = None,
    requester: str | None = None,
    redaction_state: str = "ok",
    request_raw: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    base = {
        "evidence_id": evidence_id,
        "run_id": run_id,
        "payload_hash": payload_hash,
        "access_policy": "evidence-vault-approval",
        "retention_policy": "default-90d",
        "audit_id": f"audit_evidence_vault_{evidence_id}",
    }

    if redaction_state == "failed":
        base.update(
            {
                "raw_access_state": "redaction_failed",
                "redaction_state": "failed",
                "safe_empty": True,
                "alert_action": "notify_evidence_owner",
            }
        )
        return base

    raw_state = _raw_access_state(raw_access_grant, evidence_id=evidence_id, requester=requester, now=now)
    if request_raw and raw_state != "approved":
        error_code = "RAW_ACCESS_EXPIRED" if raw_state == "expired" else "RAW_ACCESS_DENIED"
        raise AgentOpsError(
            error_code,
            "Raw evidence access requires active Evidence Vault approval.",
            denied_scope="evidence.raw",
            audit_id=base["audit_id"],
        )

    base.update(
        {
            "raw_access_state": raw_state,
            "redaction_state": "ok",
            "redacted_summary": redacted_summary or {"summary": "No sensitive evidence included."},
        }
    )
    return base


def create_raw_access_request(
    *,
    evidence_id: str,
    requester: str,
    reason: str,
    approver_scope: str,
    ttl_seconds: int,
    repository: InMemoryRepository,
) -> dict[str, Any]:
    request = {
        "request_id": f"rawreq_{evidence_id}_{requester}",
        "evidence_id": evidence_id,
        "requester": requester,
        "reason": reason,
        "approver_scope": approver_scope,
        "ttl_seconds": ttl_seconds,
        "status": "pending",
        "audit_id": f"audit_rawreq_{evidence_id}",
    }
    return repository.store_raw_access_request(request)


def approve_raw_access_request(
    request_id: str,
    repository: InMemoryRepository,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    request = repository.get_raw_access_request(request_id)
    if not request:
        raise AgentOpsError("RAW_ACCESS_REQUEST_NOT_FOUND", "Raw access request does not exist.")

    request["status"] = "approved"
    repository.store_raw_access_request(request)
    grant = {
        "raw_grant_id": f"rawgrant_{request_id}",
        "request_id": request_id,
        "evidence_id": request["evidence_id"],
        "requester": request["requester"],
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=request["ttl_seconds"])).isoformat(),
        "status": "active",
        "audit_id": f"audit_rawgrant_{request_id}",
    }
    return repository.store_raw_access_grant(grant)


def _raw_access_state(
    raw_access_grant: dict[str, Any] | None,
    *,
    evidence_id: str,
    requester: str | None,
    now: datetime,
) -> str:
    if not raw_access_grant:
        return "summary_only"
    if raw_access_grant.get("status") != "active":
        return "denied"
    if raw_access_grant.get("evidence_id") != evidence_id:
        return "denied"
    if not requester or raw_access_grant.get("requester") != requester:
        return "denied"
    if _parse_time(raw_access_grant["expires_at"]) <= now:
        return "expired"
    return "approved"


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
