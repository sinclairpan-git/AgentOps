import pytest

from agentops.api.credentials import issue_credentials
from agentops.core.errors import AgentOpsError
from tests.contract.conftest import future_time, past_time


def bootstrap_session():
    return {
        "bootstrap_id": "boot_1",
        "installation_id": "inst_1",
        "device_id": "dev_1",
        "user_id": "user_1",
        "artifact_hash": "sha256:artifact",
        "issuer": "agent-store",
        "status": "authenticated",
        "expires_at": future_time(),
    }


def credential_request(expires_at=None, artifact_hash="sha256:artifact"):
    expires_at = expires_at or future_time()
    return {
        "bootstrap_id": "boot_1",
        "installation_assertion": {
            "issuer": "agent-store",
            "key_id": "store-key-1",
            "algorithm": "ed25519",
            "canonicalization": "json-canonical-form",
            "signature": "sig_assertion",
            "installation_id": "inst_1",
            "agent_id": "agent.ai-sdlc",
            "agent_version": "1.0.0",
            "artifact_hash": artifact_hash,
            "user_id": "user_1",
            "device_id": "dev_1",
            "nonce": "nonce_1",
            "issued_at": past_time(1),
            "expires_at": expires_at,
        },
        "device_proof": {
            "device_id": "dev_1",
            "public_key_hash": "sha256:device",
            "key_id": "device-key-1",
            "algorithm": "ed25519",
            "canonicalization": "json-canonical-form",
            "nonce": "nonce_device",
            "signature": "sig_device",
            "issued_at": past_time(1),
            "expires_at": expires_at,
        },
    }


def test_active_bootstrap_issues_credential(repository):
    repository.add_bootstrap_session(bootstrap_session())

    response = issue_credentials(credential_request(), repository)

    assert response["credential_id"] == "cred_boot_1"
    assert response["token_id"] == "tok_boot_1"
    assert response["device_key_id"] == "devkey_dev_1"
    assert response["status"] == "active"


def test_expired_bootstrap_returns_contract_error(repository):
    repository.add_bootstrap_session(bootstrap_session())

    with pytest.raises(AgentOpsError) as exc:
        issue_credentials(credential_request(expires_at=past_time()), repository)

    assert exc.value.error_code == "BOOTSTRAP_EXPIRED"


def test_expired_bootstrap_session_returns_contract_error(repository):
    repository.add_bootstrap_session(dict(bootstrap_session(), expires_at=past_time()))

    with pytest.raises(AgentOpsError) as exc:
        issue_credentials(credential_request(), repository)

    assert exc.value.error_code == "BOOTSTRAP_EXPIRED"


def test_failed_bootstrap_session_cannot_issue_credentials(repository):
    repository.add_bootstrap_session(dict(bootstrap_session(), status="failed"))

    with pytest.raises(AgentOpsError) as exc:
        issue_credentials(credential_request(), repository)

    assert exc.value.error_code == "BOOTSTRAP_STATE_INVALID"


def test_same_bootstrap_retry_returns_same_credential_state(repository):
    repository.add_bootstrap_session(bootstrap_session())

    first = issue_credentials(credential_request(), repository)
    second = issue_credentials(credential_request(), repository)

    assert first == second


def test_artifact_mismatch_returns_contract_error(repository):
    repository.add_bootstrap_session(bootstrap_session())

    with pytest.raises(AgentOpsError) as exc:
        issue_credentials(credential_request(artifact_hash="sha256:other"), repository)

    assert exc.value.error_code == "BOOTSTRAP_ARTIFACT_MISMATCH"


def test_expired_device_proof_returns_contract_error(repository):
    repository.add_bootstrap_session(bootstrap_session())
    request = credential_request()
    request["device_proof"]["expires_at"] = past_time()

    with pytest.raises(AgentOpsError) as exc:
        issue_credentials(request, repository)

    assert exc.value.error_code == "BOOTSTRAP_DEVICE_PROOF_EXPIRED"


def test_device_proof_signature_and_canonicalization_are_required(repository):
    repository.add_bootstrap_session(bootstrap_session())
    request = credential_request()
    request["device_proof"]["signature"] = ""

    with pytest.raises(AgentOpsError) as exc:
        issue_credentials(request, repository)

    assert exc.value.error_code == "BOOTSTRAP_SIGNATURE_REQUIRED"


def test_stale_issued_at_returns_timestamp_skew_error(repository):
    repository.add_bootstrap_session(bootstrap_session())
    request = credential_request()
    request["installation_assertion"]["issued_at"] = past_time(10)

    with pytest.raises(AgentOpsError) as exc:
        issue_credentials(request, repository)

    assert exc.value.error_code == "BOOTSTRAP_TIMESTAMP_SKEW"


def test_nonce_replay_window_blocks_second_bootstrap(repository):
    repository.add_bootstrap_session(bootstrap_session())
    issue_credentials(credential_request(), repository)

    second_session = dict(bootstrap_session(), bootstrap_id="boot_2")
    repository.add_bootstrap_session(second_session)
    request = credential_request()
    request["bootstrap_id"] = "boot_2"

    with pytest.raises(AgentOpsError) as exc:
        issue_credentials(request, repository)

    assert exc.value.error_code == "BOOTSTRAP_REPLAY_DETECTED"
