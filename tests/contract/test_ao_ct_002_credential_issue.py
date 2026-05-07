import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import pytest

from agentops.api.credentials import issue_credentials
from agentops.core.errors import AgentOpsError
from tests.contract.conftest import past_time

FIXTURES_DIR = Path("contracts/cross-project/fixtures")
FIXTURE_NOW = datetime.fromisoformat("2026-05-07T12:02:00+00:00")
HEADERS = {"Idempotency-Key": "idem-fixture"}


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def bootstrap_session():
    return {
        "bootstrap_id": "boot-inst-fixture",
        "installation_id": "inst-fixture",
        "device_id": "dev-fixture",
        "user_id": "user-1",
        "artifact_hash": "sha256:first",
        "issuer": "agent-store",
        "status": "authenticated",
        "expires_at": "2026-05-07T12:30:00+00:00",
    }


def credential_request() -> dict:
    return load_fixture("agentops_credential_handoff.v1.json")


def issue_fixture(repository, request: dict | None = None, headers: dict[str, str] | None = None):
    return issue_credentials(request or credential_request(), repository, now=FIXTURE_NOW, headers=headers or HEADERS)


def test_cct_001_agent_store_handoff_fixture_issues_credential(repository):
    repository.add_bootstrap_session(bootstrap_session())

    response = issue_fixture(repository)

    assert response == load_fixture("credential_issue_response.v1.json")


def test_cct_002_device_proof_binds_installation_device_and_assertion_hash(repository):
    repository.add_bootstrap_session(bootstrap_session())
    request = credential_request()
    request["device_proof"]["assertion_hash"] = "sha256:other"

    with pytest.raises(AgentOpsError) as exc:
        issue_fixture(repository, request)

    assert exc.value.error_code == "BOOTSTRAP_ASSERTION_HASH_MISMATCH"


def test_device_proof_installation_mismatch_returns_contract_error(repository):
    repository.add_bootstrap_session(bootstrap_session())
    request = credential_request()
    request["device_proof"]["installation_id"] = "inst-other"

    with pytest.raises(AgentOpsError) as exc:
        issue_fixture(repository, request)

    assert exc.value.error_code == "BOOTSTRAP_DEVICE_MISMATCH"


def test_device_proof_public_key_mismatch_returns_contract_error(repository):
    repository.add_bootstrap_session(bootstrap_session())
    request = credential_request()
    request["device_proof"]["public_key_hash"] = "thumb-other"

    with pytest.raises(AgentOpsError) as exc:
        issue_fixture(repository, request)

    assert exc.value.error_code == "BOOTSTRAP_DEVICE_KEY_MISMATCH"


def test_assertion_and_device_proof_algorithms_may_differ(repository):
    repository.add_bootstrap_session(bootstrap_session())
    request = credential_request()

    assert request["installation_assertion"]["algorithm"] == "HS256"
    assert request["device_proof"]["algorithm"] == "Ed25519"
    assert issue_fixture(repository, request)["status"] == "active"


def test_cct_003_response_echoes_agent_store_consumable_status(repository):
    repository.add_bootstrap_session(bootstrap_session())

    response = issue_fixture(repository)

    assert response["bootstrap_status"] == "credential_issued"
    assert response["next_action"] == "send_signature_test_event"
    assert response["installation_id"] == "inst-fixture"
    assert response["device_id"] == "dev-fixture"


def test_cct_006_unknown_major_schema_returns_unsupported_error(repository):
    repository.add_bootstrap_session(bootstrap_session())

    with pytest.raises(AgentOpsError) as exc:
        issue_fixture(repository, load_fixture("unsupported_schema.v2.json"))

    assert exc.value.error_code == "BOOTSTRAP_SCHEMA_UNSUPPORTED"


def test_legacy_assertion_field_names_are_rejected(repository):
    repository.add_bootstrap_session(bootstrap_session())
    request = credential_request()
    assertion = request["installation_assertion"]
    assertion["alg"] = assertion.pop("algorithm")
    assertion["subject_user_id"] = assertion.pop("user_id")

    with pytest.raises(AgentOpsError) as exc:
        issue_fixture(repository, request)

    assert exc.value.error_code == "BOOTSTRAP_ASSERTION_FIELD_MISSING"


def test_missing_idempotency_key_returns_contract_error(repository):
    repository.add_bootstrap_session(bootstrap_session())

    with pytest.raises(AgentOpsError) as exc:
        issue_credentials(credential_request(), repository, now=FIXTURE_NOW, headers={})

    assert exc.value.error_code == "BOOTSTRAP_IDEMPOTENCY_KEY_REQUIRED"


def test_lowercase_idempotency_key_is_accepted(repository):
    repository.add_bootstrap_session(bootstrap_session())

    response = issue_credentials(credential_request(), repository, now=FIXTURE_NOW, headers={"idempotency-key": "idem-fixture"})

    assert response["credential_id"] == "cred-fixture"


def test_same_bootstrap_retry_returns_same_credential_state(repository):
    repository.add_bootstrap_session(bootstrap_session())

    first = issue_fixture(repository)
    second = issue_fixture(repository)

    assert first == second


def test_reused_idempotency_key_with_different_identity_conflicts(repository):
    repository.add_bootstrap_session(bootstrap_session())
    issue_fixture(repository)
    second_session = dict(bootstrap_session(), bootstrap_id="boot-other")
    repository.add_bootstrap_session(second_session)
    request = credential_request()
    request["bootstrap_id"] = "boot-other"

    with pytest.raises(AgentOpsError) as exc:
        issue_fixture(repository, request)

    assert exc.value.error_code == "BOOTSTRAP_IDEMPOTENCY_CONFLICT"


def test_issued_bootstrap_retry_still_requires_signed_assertion(repository):
    repository.add_bootstrap_session(bootstrap_session())
    issue_fixture(repository)
    request = credential_request()
    request["installation_assertion"]["signature"] = ""

    with pytest.raises(AgentOpsError) as exc:
        issue_fixture(repository, request)

    assert exc.value.error_code == "BOOTSTRAP_SIGNATURE_REQUIRED"


def test_issued_bootstrap_retry_still_requires_device_proof(repository):
    repository.add_bootstrap_session(bootstrap_session())
    issue_fixture(repository)
    request = credential_request()
    request.pop("device_proof")

    with pytest.raises(AgentOpsError) as exc:
        issue_fixture(repository, request)

    assert exc.value.error_code == "BOOTSTRAP_DEVICE_PROOF_REQUIRED"


def test_expired_bootstrap_returns_contract_error(repository):
    repository.add_bootstrap_session(bootstrap_session())
    request = credential_request()
    request["installation_assertion"]["expires_at"] = past_time()

    with pytest.raises(AgentOpsError) as exc:
        issue_credentials(request, repository, headers=HEADERS)

    assert exc.value.error_code == "BOOTSTRAP_EXPIRED"


def test_expired_bootstrap_session_returns_contract_error(repository):
    repository.add_bootstrap_session(dict(bootstrap_session(), expires_at=past_time()))

    with pytest.raises(AgentOpsError) as exc:
        issue_credentials(credential_request(), repository, headers=HEADERS)

    assert exc.value.error_code == "BOOTSTRAP_EXPIRED"


def test_failed_bootstrap_session_cannot_issue_credentials(repository):
    repository.add_bootstrap_session(dict(bootstrap_session(), status="failed"))

    with pytest.raises(AgentOpsError) as exc:
        issue_fixture(repository)

    assert exc.value.error_code == "BOOTSTRAP_STATE_INVALID"


def test_artifact_mismatch_returns_contract_error(repository):
    repository.add_bootstrap_session(bootstrap_session())
    request = credential_request()
    request["installation_assertion"]["artifact_hash"] = "sha256:other"

    with pytest.raises(AgentOpsError) as exc:
        issue_fixture(repository, request)

    assert exc.value.error_code == "BOOTSTRAP_ARTIFACT_MISMATCH"


@pytest.mark.parametrize(("field", "value"), [("installation_id", "inst-other"), ("user_id", "user-other")])
def test_identity_mismatch_returns_contract_error(repository, field, value):
    repository.add_bootstrap_session(bootstrap_session())
    request = credential_request()
    request["installation_assertion"][field] = value

    with pytest.raises(AgentOpsError) as exc:
        issue_fixture(repository, request)

    assert exc.value.error_code == "BOOTSTRAP_IDENTITY_MISMATCH"


def test_expired_device_proof_returns_contract_error(repository):
    repository.add_bootstrap_session(bootstrap_session())
    request = credential_request()
    request["device_proof"]["expires_at"] = "2026-05-07T12:01:00+00:00"

    with pytest.raises(AgentOpsError) as exc:
        issue_credentials(request, repository, now=FIXTURE_NOW, headers=HEADERS)

    assert exc.value.error_code == "BOOTSTRAP_DEVICE_PROOF_EXPIRED"


def test_stale_issued_at_returns_timestamp_skew_error(repository):
    repository.add_bootstrap_session(bootstrap_session())
    request = credential_request()
    request["installation_assertion"]["issued_at"] = "2026-05-07T11:51:00+00:00"

    with pytest.raises(AgentOpsError) as exc:
        issue_credentials(request, repository, now=FIXTURE_NOW, headers=HEADERS)

    assert exc.value.error_code == "BOOTSTRAP_TIMESTAMP_SKEW"


def test_nonce_replay_window_blocks_second_bootstrap(repository):
    repository.add_bootstrap_session(bootstrap_session())
    issue_fixture(repository, headers={"Idempotency-Key": "idem-first"})

    second_session = dict(bootstrap_session(), bootstrap_id="boot-other")
    repository.add_bootstrap_session(second_session)
    request = deepcopy(credential_request())
    request["bootstrap_id"] = "boot-other"

    with pytest.raises(AgentOpsError) as exc:
        issue_credentials(request, repository, now=FIXTURE_NOW, headers={"Idempotency-Key": "idem-second"})

    assert exc.value.error_code == "BOOTSTRAP_REPLAY_DETECTED"
