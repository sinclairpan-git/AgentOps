"""Bootstrap Credential API contract implementation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from agentops.core.errors import AgentOpsError
from agentops.storage.repository import InMemoryRepository


def issue_credentials(request: dict[str, Any], repository: InMemoryRepository, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    bootstrap_id = request["bootstrap_id"]
    session = repository.get_bootstrap_session(bootstrap_id)
    if not session:
        raise AgentOpsError("BOOTSTRAP_NOT_FOUND", "Bootstrap session does not exist.")

    assertion = request["installation_assertion"]
    device_proof = request["device_proof"]

    expires_at = _parse_time(assertion["expires_at"])
    if expires_at <= now:
        raise AgentOpsError("BOOTSTRAP_EXPIRED", "Bootstrap assertion is expired.")

    if assertion["artifact_hash"] != session["artifact_hash"]:
        raise AgentOpsError("BOOTSTRAP_ARTIFACT_MISMATCH", "Artifact hash does not match bootstrap session.")

    if assertion["issuer"] != session["issuer"]:
        raise AgentOpsError("BOOTSTRAP_ISSUER_MISMATCH", "Issuer does not match bootstrap session.")

    if assertion["device_id"] != device_proof["device_id"] or assertion["device_id"] != session["device_id"]:
        raise AgentOpsError("BOOTSTRAP_DEVICE_MISMATCH", "Device proof does not match bootstrap assertion.")

    credentials = {
        "credential_id": f"cred_{bootstrap_id}",
        "token_id": f"tok_{bootstrap_id}",
        "device_key_id": f"devkey_{assertion['device_id']}",
        "status": "active",
        "installation_id": assertion["installation_id"],
        "device_id": assertion["device_id"],
        "expires_at": assertion["expires_at"],
    }
    return repository.store_credentials(bootstrap_id, credentials)


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
