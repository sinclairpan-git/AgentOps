from __future__ import annotations

import json
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from threading import Thread

from agentops.api.agent_store import sync_agent_store_metadata
from agentops.api.app import create_app
from agentops.api.server import create_http_handler
from agentops.storage.repository import InMemoryRepository
from tests.contract.conftest import base_event

L5_EVENT_TYPES = [
    "stage_started",
    "stage_completed",
    "gate_result",
    "verification_result",
    "violation_scan_completed",
    "artifact_generated",
    "generation_snapshot",
    "l5_eligibility_input",
]


def json_get(server: ThreadingHTTPServer, path: str, *, origin: str | None = None):
    connection = HTTPConnection(server.server_address[0], server.server_address[1], timeout=5)
    try:
        headers = {"Origin": origin} if origin else {}
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        body = response.read().decode("utf-8")
        payload = json.loads(body) if body else {}
        return response, payload
    finally:
        connection.close()


def write_l5_run(repository: InMemoryRepository, *, include_adapter_state: bool = True) -> None:
    sync_agent_store_metadata(
        repository,
        {
            "agent_id": "agent.ai-sdlc",
            "version": "1.0.0",
            "skills": [{"skill_id": "refine"}],
        },
    )
    for index, event_type in enumerate(L5_EVENT_TYPES, start=1):
        event = base_event(
            event_type,
            event_id=f"evt_ao22_{event_type}",
            idempotency_key=f"ao22:{event_type}:run_1",
            sequence_no=index,
        )
        if event_type == "stage_started" and not include_adapter_state:
            event["payload"].pop("adapter_state", None)
        repository.write_event(
            event
        )


def start_server(repository: InMemoryRepository) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_http_handler(repository))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def test_ao22_ct_001_http_store_summary_returns_agentops_echo_contract():
    repository = InMemoryRepository()
    write_l5_run(repository)
    server = start_server(repository)
    try:
        response, summary = json_get(
            server,
            "/v1/store-summary/agent.ai-sdlc?version=1.0.0&run_id=run_1&schema_version=1.0",
            origin="http://127.0.0.1:5173",
        )
    finally:
        server.shutdown()

    assert response.status == 200
    assert response.getheader("Access-Control-Allow-Origin") == "http://127.0.0.1:5173"
    assert summary["schema_version"] == "agentops.agent_store.echo.v1"
    assert summary["agent_id"] == "agent.ai-sdlc"
    assert summary["agent_version"] == "1.0.0"
    assert summary["score_template_id"] == "framework-capability-stage3"
    assert summary["evidence_level"] == "L5"
    assert summary["confidence"] == 1.0
    assert summary["risk_state"] == "normal"
    assert summary["approval_state"] == "none"
    assert summary["deep_links"]["run_id"] == "run_1"
    assert summary["run_audit"] == {
        "audit_id": "audit_run_run_1",
        "registration_state": "governed",
        "event_count": len(L5_EVENT_TYPES),
    }


def test_ao22_ct_002_http_store_summary_does_not_claim_l5_for_incomplete_run():
    repository = InMemoryRepository()
    sync_agent_store_metadata(
        repository,
        {
            "agent_id": "agent.ai-sdlc",
            "version": "1.0.0",
            "skills": [{"skill_id": "refine"}],
        },
    )
    repository.write_event(base_event("stage_started"))
    server = start_server(repository)
    try:
        response, summary = json_get(server, "/v1/store-summary/agent.ai-sdlc?version=1.0.0&run_id=run_1")
    finally:
        server.shutdown()

    assert response.status == 200
    assert summary["evidence_level"] == "L4"
    assert summary["confidence"] < 1.0
    assert summary["risk_state"] == "warning"
    assert "verification_result" in summary["missing_evidence"]


def test_ao22_ct_002a_http_store_summary_does_not_infer_verified_loaded_when_adapter_state_missing():
    repository = InMemoryRepository()
    write_l5_run(repository, include_adapter_state=False)
    server = start_server(repository)
    try:
        response, summary = json_get(server, "/v1/store-summary/agent.ai-sdlc?version=1.0.0&run_id=run_1")
    finally:
        server.shutdown()

    assert response.status == 200
    assert summary["evidence_level"] == "L4"
    assert summary["confidence"] < 1.0
    assert summary["risk_state"] == "warning"
    assert summary["quality_state"]["source_trust"] == "declared"


def test_ao22_ct_003_http_store_summary_requires_version_and_run_id():
    repository = InMemoryRepository()
    write_l5_run(repository)
    server = start_server(repository)
    try:
        response, payload = json_get(server, "/v1/store-summary/agent.ai-sdlc?version=1.0.0")
    finally:
        server.shutdown()

    assert response.status == 400
    assert payload["error_code"] == "STORE_SUMMARY_QUERY_REQUIRED"


def test_ao22_ct_003a_http_store_summary_rejects_extra_path_segments():
    repository = InMemoryRepository()
    write_l5_run(repository)
    server = start_server(repository)
    try:
        response, payload = json_get(server, "/v1/store-summary/agent.ai-sdlc/extra?version=1.0.0&run_id=run_1")
    finally:
        server.shutdown()

    assert response.status == 404
    assert payload["error_code"] == "NOT_FOUND"


def test_ao22_ct_004_http_store_summary_rejects_unsupported_schema():
    repository = InMemoryRepository()
    write_l5_run(repository)
    server = start_server(repository)
    try:
        response, payload = json_get(
            server,
            "/v1/store-summary/agent.ai-sdlc?version=1.0.0&run_id=run_1&schema_version=2.0",
        )
    finally:
        server.shutdown()

    assert response.status == 409
    assert payload["error_code"] == "SUMMARY_SCHEMA_UNSUPPORTED"


def test_ao22_ct_005_http_store_summary_rejects_run_target_mismatch():
    repository = InMemoryRepository()
    write_l5_run(repository)
    server = start_server(repository)
    try:
        response, payload = json_get(server, "/v1/store-summary/agent.other?version=1.0.0&run_id=run_1")
    finally:
        server.shutdown()

    assert response.status == 409
    assert payload["error_code"] == "STORE_SUMMARY_RUN_MISMATCH"


def test_ao22_ct_006_http_store_summary_declares_display_only_consumer_boundary():
    repository = InMemoryRepository()
    write_l5_run(repository)
    server = start_server(repository)
    try:
        _, summary = json_get(server, "/v1/store-summary/agent.ai-sdlc?version=1.0.0&run_id=run_1")
    finally:
        server.shutdown()

    boundary = summary["agent_store_consumer_boundary"]
    assert summary["agentops_fact_owner"] == "AgentOps"
    assert summary["registry_fact_owner"] == "Agent Store"
    assert boundary["mode"] == "display_only"
    assert boundary["summary_fact_owner"] == "AgentOps"
    assert boundary["registry_fact_owner"] == "Agent Store"
    assert boundary["allowed_actions"] == [
        "display_summary",
        "open_agentops_deep_link",
        "request_agentops_review",
    ]
    assert "infer_active" in boundary["forbidden_actions"]
    assert "infer_verified_loaded" in boundary["forbidden_actions"]
    assert "read_raw_evidence" in boundary["forbidden_actions"]
    assert summary["raw_access_state"] == "summary_only"
    assert summary["redaction_policy"] == "repo_default"
    assert summary["data_classification"] == "internal"
    assert summary["quality_state"]["source"] == "AgentOps"


def test_ao22_ct_007_http_store_summary_excludes_raw_payload_and_secrets():
    repository = InMemoryRepository()
    sync_agent_store_metadata(
        repository,
        {
            "agent_id": "agent.ai-sdlc",
            "version": "1.0.0",
            "skills": [{"skill_id": "refine"}],
        },
    )
    event = base_event("stage_started")
    event["token_id"] = "tok_secret_leak"
    event["credential_secret"] = "cred_secret_leak"
    event["device_key_id"] = "devkey_secret_leak"
    event["payload"]["raw_payload"] = {"secret": "payload_secret_leak"}
    repository.write_event(event)
    server = start_server(repository)
    try:
        response, summary = json_get(server, "/v1/store-summary/agent.ai-sdlc?version=1.0.0&run_id=run_1")
    finally:
        server.shutdown()

    serialized = json.dumps(summary, ensure_ascii=False)
    assert response.status == 200
    assert "raw_payload" not in serialized
    assert "payload_secret_leak" not in serialized
    assert "tok_secret_leak" not in serialized
    assert "cred_secret_leak" not in serialized
    assert "devkey_secret_leak" not in serialized


def test_ao22_ct_008_app_declares_store_summary_route_manifest():
    app = create_app()

    assert app["store_summary"] == "/v1/store-summary/{agent_id}"
