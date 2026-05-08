import json
from datetime import datetime
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest

from agentops.api.credentials import (
    get_credential_status,
    issue_credentials,
    revoke_credentials,
)
from agentops.api.ingestion import ingest_events_batch
from agentops.api.server import create_http_handler
from agentops.core.errors import AgentOpsError
from agentops.storage.repository import InMemoryRepository
from tests.contract.conftest import base_event

FIXTURES_DIR = Path("contracts/cross-project/fixtures")
FIXTURE_NOW = datetime.fromisoformat("2026-05-07T12:02:00+00:00")
REVOKE_NOW = datetime.fromisoformat("2026-05-07T12:10:00+00:00")


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def bootstrap_session() -> dict:
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


def revocation_request(**overrides) -> dict:
    request = {
        "schema_version": "agentops_credential_revocation.v1",
        "bootstrap_id": "boot-inst-fixture",
        "revocation_id": "revoke-inst-fixture",
        "revoked_by": "security-operator",
        "reason": "设备遗失",
        "scope": "credential_and_device_key",
    }
    request.update(overrides)
    return request


def issue_fixture_credentials(repository: InMemoryRepository):
    repository.add_bootstrap_session(bootstrap_session())
    return issue_credentials(
        load_fixture("agentops_credential_handoff.v1.json"),
        repository,
        now=FIXTURE_NOW,
        headers={"Idempotency-Key": "idem-fixture"},
    )


def signature_test_event():
    event = base_event(
        "stage_started",
        event_id="evt_signature_test",
        idempotency_key="signature-test:boot-inst-fixture",
        user_id="user-1",
        agent_id="agent-1",
        agent_version="1.0.0",
        installation_id="inst-fixture",
        device_id="dev-fixture",
        session_id="sess-signature-test",
        run_id="run-signature-test",
        ingestion_token="token-fixture",
    )
    event["event_type"] = "signature_test_event"
    event["span_id"] = "span_signature_test"
    event["payload"] = {
        "bootstrap_id": "boot-inst-fixture",
        "credential_id": "cred-fixture",
        "token_id": "token-fixture",
        "device_key_id": "device-key-fixture",
        "installation_id": "inst-fixture",
        "device_id": "dev-fixture",
        "next_action": "send_signature_test_event",
    }
    return event


def enterprise_event_after_revocation():
    return base_event(
        "stage_started",
        event_id="evt_after_revoke",
        idempotency_key="stage-started:after-revoke",
        user_id="user-1",
        agent_id="agent-1",
        agent_version="1.0.0",
        installation_id="inst-fixture",
        device_id="dev-fixture",
        session_id="sess-after-revoke",
        run_id="run-after-revoke",
        ingestion_token="token-fixture",
    )


def json_post(
    server: ThreadingHTTPServer, path: str, payload: dict, *, origin: str | None = None
):
    connection = HTTPConnection(
        server.server_address[0], server.server_address[1], timeout=5
    )
    try:
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if origin:
            headers["Origin"] = origin
        connection.request("POST", path, body=body, headers=headers)
        response = connection.getresponse()
        payload_body = response.read().decode("utf-8")
        return response, json.loads(payload_body) if payload_body else {}
    finally:
        connection.close()


@pytest.fixture
def seeded_revocation_server(repository):
    issue_fixture_credentials(repository)
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_http_handler(repository))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_ao20_ct_001_revoke_credentials_updates_agentops_status(repository):
    issue_fixture_credentials(repository)

    response = revoke_credentials(revocation_request(), repository, now=REVOKE_NOW)
    status = get_credential_status(repository, "boot-inst-fixture")

    assert response["schema_version"] == "agentops_credential_revocation.v1"
    assert response["credential_status"] == "revoked"
    assert response["bootstrap_status"] == "revoked"
    assert response["next_action"] == "reissue_credential"
    assert status["credential_status"] == "revoked"
    assert status["bootstrap_status"] == "revoked"
    assert status["next_action"] == "reissue_credential"
    assert status["revocation_id"] == "revoke-inst-fixture"
    assert status["revoked_by"] == "security-operator"
    assert status["revocation_scope"] == "credential_and_device_key"
    assert status["verified_loaded"] == "not_asserted"
    assert status["l5_status"] == "not_asserted"


def test_ao20_ct_002_revoked_signature_test_event_is_rejected(repository):
    issue_fixture_credentials(repository)
    revoke_credentials(revocation_request(), repository, now=REVOKE_NOW)

    result = ingest_events_batch([signature_test_event()], repository)

    assert result["accepted"] == []
    assert result["rejected"][0]["error_code"] == "EVENT_CREDENTIAL_REVOKED"
    assert (
        repository.get_bootstrap_session("boot-inst-fixture")["bootstrap_status"]
        == "revoked"
    )


def test_ao20_ct_003_revoked_known_enterprise_event_is_rejected(repository):
    issue_fixture_credentials(repository)
    revoke_credentials(revocation_request(), repository, now=REVOKE_NOW)

    result = ingest_events_batch([enterprise_event_after_revocation()], repository)

    assert result["accepted"] == []
    assert result["rejected"][0]["error_code"] == "EVENT_CREDENTIAL_REVOKED"
    assert "evt_after_revoke" not in repository.raw_events


def test_ao20_ct_003b_revoked_duplicate_identity_is_rejected_after_active_match(
    repository,
):
    repository.add_bootstrap_session(
        {
            **bootstrap_session(),
            "bootstrap_id": "boot-active-shadow",
        }
    )
    repository.store_credentials(
        "boot-active-shadow",
        {
            "credential_id": "cred-active-shadow",
            "token_id": "token-fixture",
            "device_key_id": "device-key-shadow",
            "status": "active",
            "bootstrap_status": "credential_issued",
            "installation_id": "inst-fixture",
            "device_id": "dev-fixture",
            "expires_at": "2026-05-07T13:02:00+00:00",
            "next_action": "send_signature_test_event",
        },
    )
    issue_fixture_credentials(repository)
    revoke_credentials(revocation_request(), repository, now=REVOKE_NOW)

    result = ingest_events_batch([enterprise_event_after_revocation()], repository)

    assert result["accepted"] == []
    assert result["rejected"][0]["error_code"] == "EVENT_CREDENTIAL_REVOKED"
    assert "evt_after_revoke" not in repository.raw_events


def test_ao20_ct_004_unknown_revocation_schema_is_rejected(repository):
    issue_fixture_credentials(repository)

    with pytest.raises(AgentOpsError) as exc:
        revoke_credentials(
            revocation_request(schema_version="agentops_credential_revocation.v2"),
            repository,
        )

    assert exc.value.error_code == "CREDENTIAL_REVOCATION_SCHEMA_UNSUPPORTED"


def test_ao20_ct_005_http_revoke_route_returns_json_and_cors(seeded_revocation_server):
    response, payload = json_post(
        seeded_revocation_server,
        "/v1/bootstrap/credentials/boot-inst-fixture/revoke",
        {
            "schema_version": "agentops_credential_revocation.v1",
            "revocation_id": "revoke-inst-fixture",
            "revoked_by": "security-operator",
            "reason": "设备遗失",
            "scope": "credential_and_device_key",
        },
        origin="http://127.0.0.1:5174",
    )

    assert response.status == 200
    assert response.getheader("Access-Control-Allow-Origin") == "http://127.0.0.1:5174"
    assert payload["credential_status"] == "revoked"
    assert payload["bootstrap_status"] == "revoked"
    assert payload["next_action"] == "reissue_credential"


def test_ao20_ct_006_revocation_not_found_returns_stable_error(repository):
    with pytest.raises(AgentOpsError) as exc:
        revoke_credentials(revocation_request(), repository)

    assert exc.value.error_code == "CREDENTIAL_REVOCATION_NOT_FOUND"
