"""Bootstrap Credential API contract implementation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from agentops.core.errors import AgentOpsError
from agentops.storage.repository import InMemoryRepository

HANDOFF_SCHEMA_VERSION = "agentops_credential_handoff.v1"
ASSERTION_VERSION = "signed_installation_assertion.v1"
DEVICE_PROOF_VERSION = "device_proof.v1"
CANONICALIZATION = "json-c14n-v1"
AGENT_STORE_ISSUER = "agent-store"
AGENTOPS_AUDIENCE = "agentops"
NEXT_ACTION_SIGNATURE_TEST = "send_signature_test_event"
NEXT_ACTION_DISPLAY_RESULT = "display_activation_result"
CREDENTIAL_STATUS_SCHEMA_VERSION = "agentops_credential_status.v1"


def issue_credentials(
    request: dict[str, Any],
    repository: InMemoryRepository,
    now: datetime | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    _validate_schema_version(request)
    bootstrap_id = _required_string(request, "bootstrap_id", error_code="BOOTSTRAP_ID_REQUIRED")
    idempotency_key = _idempotency_key(headers)
    if not idempotency_key:
        raise AgentOpsError("BOOTSTRAP_IDEMPOTENCY_KEY_REQUIRED", "Credential issue requires Idempotency-Key header.")
    session = repository.get_bootstrap_session(bootstrap_id)
    if not session:
        raise AgentOpsError("BOOTSTRAP_NOT_FOUND", "Bootstrap session does not exist.")
    session_expires_at = _parse_time(session["expires_at"])
    if session_expires_at <= now:
        raise AgentOpsError("BOOTSTRAP_EXPIRED", "Bootstrap session is expired.")
    if session.get("status") not in {"authenticated", "credential_issued", "verified"}:
        raise AgentOpsError("BOOTSTRAP_STATE_INVALID", "Bootstrap session is not eligible for credential issue.")

    assertion = _required_dict(request, "installation_assertion", "BOOTSTRAP_ASSERTION_REQUIRED")
    device_proof = _required_dict(request, "device_proof", "BOOTSTRAP_DEVICE_PROOF_REQUIRED")
    _validate_assertion(assertion)
    _validate_device_proof(device_proof)

    expires_at = _parse_time(_required_string(assertion, "expires_at"))
    if expires_at <= now:
        raise AgentOpsError("BOOTSTRAP_EXPIRED", "Bootstrap assertion is expired.")
    _validate_timestamp_skew(_required_string(assertion, "issued_at"), now)

    if assertion["artifact_hash"] != session["artifact_hash"]:
        raise AgentOpsError("BOOTSTRAP_ARTIFACT_MISMATCH", "Artifact hash does not match bootstrap session.")

    if assertion["issuer"] != session["issuer"]:
        raise AgentOpsError("BOOTSTRAP_ISSUER_MISMATCH", "Issuer does not match bootstrap session.")

    if assertion["installation_id"] != session["installation_id"] or assertion["user_id"] != session["user_id"]:
        raise AgentOpsError("BOOTSTRAP_IDENTITY_MISMATCH", "Assertion identity does not match bootstrap session.")

    if assertion["device_id"] != device_proof["device_id"] or assertion["device_id"] != session["device_id"]:
        raise AgentOpsError("BOOTSTRAP_DEVICE_MISMATCH", "Device proof does not match bootstrap assertion.")

    if assertion["installation_id"] != device_proof["installation_id"]:
        raise AgentOpsError("BOOTSTRAP_DEVICE_MISMATCH", "Device proof installation does not match bootstrap assertion.")

    if assertion["assertion_hash"] != device_proof["assertion_hash"]:
        raise AgentOpsError("BOOTSTRAP_ASSERTION_HASH_MISMATCH", "Device proof is not bound to the assertion hash.")

    if assertion["device_public_key_thumbprint"] != device_proof["public_key_hash"]:
        raise AgentOpsError("BOOTSTRAP_DEVICE_KEY_MISMATCH", "Device proof public key does not match Agent Store binding.")

    proof_expires_at = _parse_time(_required_string(device_proof, "expires_at"))
    if proof_expires_at <= now:
        raise AgentOpsError("BOOTSTRAP_DEVICE_PROOF_EXPIRED", "Device proof is expired.")
    _validate_timestamp_skew(_required_string(device_proof, "issued_at"), now)

    if not assertion.get("signature") or not device_proof.get("signature"):
        raise AgentOpsError("BOOTSTRAP_SIGNATURE_REQUIRED", "Bootstrap assertion and device proof require signatures.")

    if not assertion.get("key_id") or not device_proof.get("key_id"):
        raise AgentOpsError("BOOTSTRAP_KEY_ID_REQUIRED", "Bootstrap assertion and device proof require key_id.")

    assertion_nonce = assertion.get("nonce")
    device_nonce = device_proof.get("nonce")
    if not assertion_nonce or not device_nonce:
        raise AgentOpsError("BOOTSTRAP_NONCE_REQUIRED", "Bootstrap assertion and device proof require nonces.")

    handoff_identity = _handoff_identity(bootstrap_id, assertion, device_proof)
    _validate_idempotency_identity(repository, idempotency_key, handoff_identity)
    existing = repository.credentials_by_bootstrap.get(bootstrap_id)
    if existing:
        existing_identity = repository.credential_identities_by_bootstrap.get(bootstrap_id)
        if existing_identity != handoff_identity:
            raise AgentOpsError("BOOTSTRAP_IDEMPOTENCY_CONFLICT", "Bootstrap retry identity does not match issued credential.")
        repository.record_credential_issue_idempotency(idempotency_key, handoff_identity)
        return dict(existing)

    if assertion_nonce in repository.used_bootstrap_nonces or device_nonce in repository.used_bootstrap_nonces:
        raise AgentOpsError("BOOTSTRAP_REPLAY_DETECTED", "Bootstrap nonce has already been used.")

    credential_suffix = _credential_suffix(assertion["installation_id"])
    credential_expires_at = (_parse_time(assertion["issued_at"]) + timedelta(hours=1)).isoformat()
    credentials = {
        "credential_id": f"cred-{credential_suffix}",
        "token_id": f"token-{credential_suffix}",
        "device_key_id": device_proof["key_id"],
        "status": "active",
        "bootstrap_status": "credential_issued",
        "installation_id": assertion["installation_id"],
        "device_id": assertion["device_id"],
        "expires_at": credential_expires_at,
        "next_action": NEXT_ACTION_SIGNATURE_TEST,
    }
    repository.mark_bootstrap_nonces(assertion_nonce, device_nonce)
    return repository.store_credentials(
        bootstrap_id,
        credentials,
        handoff_identity=handoff_identity,
        idempotency_key=idempotency_key,
    )


def get_credential_status(
    repository: InMemoryRepository,
    bootstrap_id: str,
    *,
    consumer_schema_version: str = CREDENTIAL_STATUS_SCHEMA_VERSION,
) -> dict[str, Any]:
    if consumer_schema_version != CREDENTIAL_STATUS_SCHEMA_VERSION:
        raise AgentOpsError("CREDENTIAL_STATUS_SCHEMA_UNSUPPORTED", "Unsupported credential status schema.")

    session = repository.get_bootstrap_session(bootstrap_id)
    credentials = repository.get_credentials(bootstrap_id)
    if not session or not credentials:
        raise AgentOpsError("CREDENTIAL_STATUS_NOT_FOUND", "Credential status does not exist for this bootstrap.")

    bootstrap_status = str(credentials.get("bootstrap_status") or session.get("bootstrap_status") or session.get("status"))
    next_action = NEXT_ACTION_DISPLAY_RESULT if bootstrap_status == "signature_verified" else NEXT_ACTION_SIGNATURE_TEST
    return {
        "schema_version": CREDENTIAL_STATUS_SCHEMA_VERSION,
        "bootstrap_id": bootstrap_id,
        "bootstrap_status": bootstrap_status,
        "credential_status": str(credentials.get("status") or "unknown"),
        "credential_id": str(credentials["credential_id"]),
        "token_id": str(credentials["token_id"]),
        "device_key_id": str(credentials["device_key_id"]),
        "installation_id": str(credentials["installation_id"]),
        "device_id": str(credentials["device_id"]),
        "expires_at": str(credentials["expires_at"]),
        "next_action": next_action,
        "signature_test_event_id": credentials.get("signature_test_event_id"),
        "agentops_fact_owner": "agentops",
        "agent_store_consumer_boundary": "display_only_no_active_inference",
        "agent_store_allowed_actions": ["display_status", "show_next_action"],
        "agent_store_forbidden_actions": ["infer_active", "issue_credential", "issue_ingestion_token", "issue_device_key"],
        "verified_loaded": "not_asserted",
        "l5_status": "not_asserted",
    }


def _validate_schema_version(request: dict[str, Any]) -> None:
    schema_version = _required_string(request, "schema_version", error_code="BOOTSTRAP_SCHEMA_REQUIRED")
    if schema_version == HANDOFF_SCHEMA_VERSION:
        return
    if schema_version.startswith("agentops_credential_handoff.v"):
        raise AgentOpsError("BOOTSTRAP_SCHEMA_UNSUPPORTED", f"Unsupported credential handoff schema: {schema_version}.")
    raise AgentOpsError("BOOTSTRAP_SCHEMA_INVALID", "Credential handoff schema_version is invalid.")


def _validate_assertion(assertion: dict[str, Any]) -> None:
    required = [
        "assertion_version",
        "issuer",
        "key_id",
        "algorithm",
        "canonicalization",
        "signature",
        "assertion_hash",
        "installation_id",
        "device_id",
        "device_public_key_thumbprint",
        "agent_id",
        "agent_version",
        "artifact_hash",
        "user_id",
        "audience",
        "nonce",
        "replay_window_seconds",
        "issued_at",
        "expires_at",
        "revocation_status",
    ]
    for field in required:
        _required_value(assertion, field, "BOOTSTRAP_ASSERTION_FIELD_MISSING")
    if "alg" in assertion or "subject_user_id" in assertion:
        raise AgentOpsError("BOOTSTRAP_ASSERTION_FIELD_UNSUPPORTED", "AgentOps handoff assertion must use external field names.")
    if assertion["assertion_version"] != ASSERTION_VERSION:
        raise AgentOpsError("BOOTSTRAP_ASSERTION_SCHEMA_UNSUPPORTED", "Unsupported installation assertion version.")
    if assertion["issuer"] != AGENT_STORE_ISSUER:
        raise AgentOpsError("BOOTSTRAP_ISSUER_MISMATCH", "Issuer does not match Agent Store handoff contract.")
    if assertion["audience"] != AGENTOPS_AUDIENCE:
        raise AgentOpsError("BOOTSTRAP_AUDIENCE_MISMATCH", "Installation assertion audience must be agentops.")
    if assertion["canonicalization"] != CANONICALIZATION:
        raise AgentOpsError("BOOTSTRAP_CANONICALIZATION_UNSUPPORTED", "Unsupported assertion canonicalization.")
    if assertion["revocation_status"] != "not_revoked":
        raise AgentOpsError("BOOTSTRAP_ASSERTION_REVOKED", "Installation assertion is revoked or unknown.")


def _validate_device_proof(device_proof: dict[str, Any]) -> None:
    required = [
        "proof_version",
        "installation_id",
        "device_id",
        "public_key_hash",
        "key_id",
        "algorithm",
        "canonicalization",
        "nonce",
        "assertion_hash",
        "signature",
        "issued_at",
        "expires_at",
    ]
    for field in required:
        _required_value(device_proof, field, "BOOTSTRAP_DEVICE_PROOF_FIELD_MISSING")
    if device_proof["proof_version"] != DEVICE_PROOF_VERSION:
        raise AgentOpsError("BOOTSTRAP_DEVICE_PROOF_SCHEMA_UNSUPPORTED", "Unsupported device proof version.")
    if device_proof["canonicalization"] != CANONICALIZATION:
        raise AgentOpsError("BOOTSTRAP_CANONICALIZATION_UNSUPPORTED", "Unsupported device proof canonicalization.")


def _validate_idempotency_identity(
    repository: InMemoryRepository,
    idempotency_key: str,
    handoff_identity: dict[str, Any],
) -> None:
    existing_identity = repository.credential_issue_idempotency.get(idempotency_key)
    if existing_identity is not None and existing_identity != handoff_identity:
        raise AgentOpsError("BOOTSTRAP_IDEMPOTENCY_CONFLICT", "Idempotency-Key was reused with different credential handoff identity.")


def _handoff_identity(bootstrap_id: str, assertion: dict[str, Any], device_proof: dict[str, Any]) -> dict[str, Any]:
    return {
        "bootstrap_id": bootstrap_id,
        "assertion_hash": assertion["assertion_hash"],
        "installation_id": assertion["installation_id"],
        "device_id": assertion["device_id"],
        "user_id": assertion["user_id"],
        "artifact_hash": assertion["artifact_hash"],
        "assertion_nonce": assertion["nonce"],
        "device_nonce": device_proof["nonce"],
        "device_public_key": device_proof["public_key_hash"],
    }


def _idempotency_key(headers: dict[str, str] | None) -> str | None:
    if not headers:
        return None
    for name, value in headers.items():
        if name.lower() == "idempotency-key" and value:
            return value.strip()
    return None


def _credential_suffix(installation_id: str) -> str:
    if installation_id.startswith("inst-") and len(installation_id) > len("inst-"):
        return installation_id.removeprefix("inst-")
    return installation_id


def _required_dict(payload: dict[str, Any], field: str, error_code: str) -> dict[str, Any]:
    value = payload.get(field)
    if not isinstance(value, dict):
        raise AgentOpsError(error_code, f"{field} is required.")
    return value


def _required_string(payload: dict[str, Any], field: str, error_code: str = "BOOTSTRAP_FIELD_MISSING") -> str:
    value = _required_value(payload, field, error_code)
    if not isinstance(value, str) or not value.strip():
        raise AgentOpsError(error_code, f"{field} must be a non-empty string.")
    return value.strip()


def _required_value(payload: dict[str, Any], field: str, error_code: str) -> Any:
    if field not in payload or payload[field] is None:
        raise AgentOpsError(error_code, f"{field} is required.")
    return payload[field]


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _validate_timestamp_skew(value: str, now: datetime) -> None:
    issued_at = _parse_time(value)
    if abs(now - issued_at) > timedelta(minutes=5):
        raise AgentOpsError("BOOTSTRAP_TIMESTAMP_SKEW", "Bootstrap timestamp skew exceeds five minutes.")
