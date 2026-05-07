import json
from datetime import datetime
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest

from agentops.api.credentials import get_credential_status, issue_credentials
from agentops.api.ingestion import ingest_events_batch
from agentops.api.server import create_http_handler
from agentops.core.errors import AgentOpsError
from agentops.storage.repository import InMemoryRepository
from tests.contract.conftest import base_event

FIXTURES_DIR = Path("contracts/cross-project/fixtures")
FIXTURE_NOW = datetime.fromisoformat("2026-05-07T12:02:00+00:00")
HEADERS = {"Idempotency-Key": "idem-fixture"}


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


def issue_fixture_credentials(repository: InMemoryRepository):
    repository.add_bootstrap_session(bootstrap_session())
    return issue_credentials(load_fixture("agentops_credential_handoff.v1.json"), repository, now=FIXTURE_NOW, headers=HEADERS)


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


def contains_key(value, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(contains_key(child, key) for child in value.values())
    if isinstance(value, list):
        return any(contains_key(child, key) for child in value)
    return False


def json_get(server: ThreadingHTTPServer, path: str, *, origin: str | None = None):
    connection = HTTPConnection(server.server_address[0], server.server_address[1], timeout=5)
    try:
        headers = {"Origin": origin} if origin else {}
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        body = response.read().decode("utf-8")
        return response, json.loads(body) if body else {}
    finally:
        connection.close()


@pytest.fixture
def seeded_status_server(repository):
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


def test_ao18_cct_003_agent_store_reads_credential_issued_status(repository):
    issue_fixture_credentials(repository)

    status = get_credential_status(repository, "boot-inst-fixture")

    assert status["schema_version"] == "agentops_credential_status.v1"
    assert status["bootstrap_status"] == "credential_issued"
    assert status["credential_status"] == "active"
    assert status["credential_id"] == "cred-fixture"
    assert status["token_id"] == "token-fixture"
    assert status["device_key_id"] == "device-key-fixture"
    assert status["installation_id"] == "inst-fixture"
    assert status["device_id"] == "dev-fixture"
    assert status["next_action"] == "send_signature_test_event"
    assert status["agentops_fact_owner"] == "agentops"
    assert status["agent_store_consumer_boundary"] == "display_only_no_active_inference"
    assert "infer_active" in status["agent_store_forbidden_actions"]
    assert status["verified_loaded"] == "not_asserted"
    assert status["l5_status"] == "not_asserted"


def test_ao18_cct_003b_agent_store_reads_signature_verified_status(repository):
    issue_fixture_credentials(repository)
    ingest_events_batch([signature_test_event()], repository)

    status = get_credential_status(repository, "boot-inst-fixture")

    assert status["bootstrap_status"] == "signature_verified"
    assert status["next_action"] == "display_activation_result"
    assert status["signature_test_event_id"] == "evt_signature_test"
    assert status["agent_store_allowed_actions"] == ["display_status", "show_next_action"]


def test_ao18_cct_003n_unknown_bootstrap_status_is_not_found(repository):
    with pytest.raises(AgentOpsError) as exc:
        get_credential_status(repository, "boot-missing")

    assert exc.value.error_code == "CREDENTIAL_STATUS_NOT_FOUND"


def test_ao18_cct_003n_unknown_status_schema_is_rejected(repository):
    issue_fixture_credentials(repository)

    with pytest.raises(AgentOpsError) as exc:
        get_credential_status(repository, "boot-inst-fixture", consumer_schema_version="agentops_credential_status.v2")

    assert exc.value.error_code == "CREDENTIAL_STATUS_SCHEMA_UNSUPPORTED"


def test_ao18_cct_003s_status_response_does_not_expose_secret_or_raw_fields(repository):
    issue_fixture_credentials(repository)

    status = get_credential_status(repository, "boot-inst-fixture")

    for forbidden in ("token_value", "private_key", "raw_payload", "download_url", "raw_url", "signature"):
        assert not contains_key(status, forbidden)


def test_ao18_cct_http_status_route_returns_json_and_cors(seeded_status_server):
    response, payload = json_get(
        seeded_status_server,
        "/v1/bootstrap/credentials/boot-inst-fixture",
        origin="http://127.0.0.1:5174",
    )

    assert response.status == 200
    assert response.getheader("Access-Control-Allow-Origin") == "http://127.0.0.1:5174"
    assert payload["schema_version"] == "agentops_credential_status.v1"
    assert payload["bootstrap_status"] == "credential_issued"


def test_ao18_cct_http_status_route_returns_not_found(seeded_status_server):
    response, payload = json_get(seeded_status_server, "/v1/bootstrap/credentials/boot-missing")

    assert response.status == 404
    assert payload["error_code"] == "CREDENTIAL_STATUS_NOT_FOUND"
