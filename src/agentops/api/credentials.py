"""Bootstrap Credential API contract implementation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from agentops.core.errors import AgentOpsError
from agentops.storage.repository import InMemoryRepository


def issue_credentials(request: dict[str, Any], repository: InMemoryRepository, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    bootstrap_id = request["bootstrap_id"]
    session = repository.get_bootstrap_session(bootstrap_id)
    if not session:
        raise AgentOpsError("BOOTSTRAP_NOT_FOUND", "Bootstrap session does not exist.")
    session_expires_at = _parse_time(session["expires_at"])
    if session_expires_at <= now:
        raise AgentOpsError("BOOTSTRAP_EXPIRED", "Bootstrap session is expired.")
    if session.get("status") not in {"authenticated", "credential_issued", "verified"}:
        raise AgentOpsError("BOOTSTRAP_STATE_INVALID", "Bootstrap session is not eligible for credential issue.")
    existing = repository.credentials_by_bootstrap.get(bootstrap_id)
    if existing:
        return dict(existing)

    assertion = request["installation_assertion"]
    device_proof = request["device_proof"]

    expires_at = _parse_time(assertion["expires_at"])
    if expires_at <= now:
        raise AgentOpsError("BOOTSTRAP_EXPIRED", "Bootstrap assertion is expired.")
    _validate_timestamp_skew(assertion["issued_at"], now)

    if assertion["artifact_hash"] != session["artifact_hash"]:
        raise AgentOpsError("BOOTSTRAP_ARTIFACT_MISMATCH", "Artifact hash does not match bootstrap session.")

    if assertion["issuer"] != session["issuer"]:
        raise AgentOpsError("BOOTSTRAP_ISSUER_MISMATCH", "Issuer does not match bootstrap session.")

    if assertion["installation_id"] != session["installation_id"] or assertion["user_id"] != session["user_id"]:
        raise AgentOpsError("BOOTSTRAP_IDENTITY_MISMATCH", "Assertion identity does not match bootstrap session.")

    if assertion["device_id"] != device_proof["device_id"] or assertion["device_id"] != session["device_id"]:
        raise AgentOpsError("BOOTSTRAP_DEVICE_MISMATCH", "Device proof does not match bootstrap assertion.")

    proof_expires_at = _parse_time(device_proof["expires_at"])
    if proof_expires_at <= now:
        raise AgentOpsError("BOOTSTRAP_DEVICE_PROOF_EXPIRED", "Device proof is expired.")
    _validate_timestamp_skew(device_proof["issued_at"], now)

    if not assertion.get("signature") or not device_proof.get("signature"):
        raise AgentOpsError("BOOTSTRAP_SIGNATURE_REQUIRED", "Bootstrap assertion and device proof require signatures.")

    if assertion.get("canonicalization") != "json-canonical-form" or device_proof.get("canonicalization") != "json-canonical-form":
        raise AgentOpsError("BOOTSTRAP_CANONICALIZATION_UNSUPPORTED", "Unsupported canonicalization.")

    if assertion.get("algorithm") != device_proof.get("algorithm"):
        raise AgentOpsError("BOOTSTRAP_ALGORITHM_MISMATCH", "Assertion and device proof algorithms must match.")

    if not assertion.get("key_id") or not device_proof.get("key_id"):
        raise AgentOpsError("BOOTSTRAP_KEY_ID_REQUIRED", "Bootstrap assertion and device proof require key_id.")

    assertion_nonce = assertion["nonce"]
    device_nonce = device_proof["nonce"]
    if assertion_nonce in repository.used_bootstrap_nonces or device_nonce in repository.used_bootstrap_nonces:
        raise AgentOpsError("BOOTSTRAP_REPLAY_DETECTED", "Bootstrap nonce has already been used.")

    credentials = {
        "credential_id": f"cred_{bootstrap_id}",
        "token_id": f"tok_{bootstrap_id}",
        "device_key_id": f"devkey_{assertion['device_id']}",
        "status": "active",
        "installation_id": assertion["installation_id"],
        "device_id": assertion["device_id"],
        "expires_at": assertion["expires_at"],
    }
    repository.mark_bootstrap_nonces(assertion_nonce, device_nonce)
    return repository.store_credentials(bootstrap_id, credentials)


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _validate_timestamp_skew(value: str, now: datetime) -> None:
    issued_at = _parse_time(value)
    if abs(now - issued_at) > timedelta(minutes=5):
        raise AgentOpsError("BOOTSTRAP_TIMESTAMP_SKEW", "Bootstrap timestamp skew exceeds five minutes.")
