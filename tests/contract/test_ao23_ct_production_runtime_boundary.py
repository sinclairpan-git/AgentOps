from __future__ import annotations

import json
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest

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


def _json_request(
    server: ThreadingHTTPServer,
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    payload: dict | None = None,
):
    connection = HTTPConnection(
        server.server_address[0], server.server_address[1], timeout=5
    )
    try:
        request_headers = dict(headers or {})
        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        connection.request(method, path, body=body, headers=request_headers)
        response = connection.getresponse()
        response_body = response.read().decode("utf-8")
        response_payload = json.loads(response_body) if response_body else {}
        return response, response_payload
    finally:
        connection.close()


def _start_server(repository: InMemoryRepository) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), create_http_handler(repository, require_auth=True)
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _auth_headers(*, roles: str = "", scopes: str = "") -> dict[str, str]:
    headers = {
        "X-AgentOps-Principal": "user.ops@example.com",
        "X-AgentOps-Request-Id": "req_ao23",
        "X-AgentOps-Audit-Id": "audit_ao23",
    }
    if roles:
        headers["X-AgentOps-Roles"] = roles
    if scopes:
        headers["X-AgentOps-Scopes"] = scopes
    return headers


def _write_l5_run(repository: InMemoryRepository) -> None:
    sync_agent_store_metadata(
        repository,
        {
            "agent_id": "agent.ai-sdlc",
            "version": "1.0.0",
            "skills": [{"skill_id": "refine"}],
        },
    )
    for index, event_type in enumerate(L5_EVENT_TYPES, start=1):
        repository.write_event(
            base_event(
                event_type,
                event_id=f"evt_ao23_{event_type}",
                idempotency_key=f"ao23:{event_type}:run_1",
                sequence_no=index,
            )
        )


def test_ao23_ct_001_health_remains_anonymous_in_production_mode():
    repository = InMemoryRepository()
    server = _start_server(repository)
    try:
        response, payload = _json_request(server, "GET", "/v1/health")
    finally:
        server.shutdown()

    assert response.status == 200
    assert payload["status"] == "healthy"


def test_ao23_ct_002_event_ingest_requires_upstream_identity_in_production_mode():
    repository = InMemoryRepository()
    server = _start_server(repository)
    try:
        response, payload = _json_request(
            server, "POST", "/v1/events", payload={"events": [base_event()]}
        )
    finally:
        server.shutdown()

    assert response.status == 401
    assert payload == {
        "error_code": "UPSTREAM_IDENTITY_REQUIRED",
        "message": "生产模式需要上游 IAM/RBAC 身份证明。",
        "retryable": False,
        "audit_id": "audit_missing_identity",
        "request_id": "req_missing_identity",
        "denied_scope": "event.ingest",
    }
    assert repository.raw_event_count() == 0


def test_ao23_ct_003_viewer_cannot_ingest_events_in_production_mode():
    repository = InMemoryRepository()
    server = _start_server(repository)
    try:
        response, payload = _json_request(
            server,
            "POST",
            "/v1/events",
            headers=_auth_headers(roles="agentops-viewer"),
            payload={"events": [base_event()]},
        )
    finally:
        server.shutdown()

    assert response.status == 403
    assert payload["error_code"] == "AGENTOPS_SCOPE_DENIED"
    assert payload["request_id"] == "req_ao23"
    assert payload["audit_id"] == "audit_ao23"
    assert payload["denied_scope"] == "event.ingest"
    assert repository.raw_event_count() == 0


def test_ao23_ct_004_ingestor_role_can_ingest_events_in_production_mode():
    repository = InMemoryRepository()
    server = _start_server(repository)
    try:
        response, payload = _json_request(
            server,
            "POST",
            "/v1/events",
            headers=_auth_headers(roles="agentops-ingestor"),
            payload={"events": [base_event()]},
        )
    finally:
        server.shutdown()

    assert response.status == 202
    assert payload["accepted"] == ["evt_stage_started"]
    assert repository.raw_event_count() == 1


def test_ao23_ct_004a_auth_headers_are_case_insensitive():
    repository = InMemoryRepository()
    server = _start_server(repository)
    try:
        response, payload = _json_request(
            server,
            "POST",
            "/v1/events",
            headers={
                "x-agentops-principal": "user.ops@example.com",
                "x-agentops-roles": "agentops-ingestor",
                "x-agentops-request-id": "req_lowercase",
                "x-agentops-audit-id": "audit_lowercase",
            },
            payload={"events": [base_event()]},
        )
    finally:
        server.shutdown()

    assert response.status == 202
    assert payload["accepted"] == ["evt_stage_started"]
    assert repository.raw_event_count() == 1


def test_ao23_ct_005_store_summary_requires_consumer_or_viewer_boundary():
    repository = InMemoryRepository()
    _write_l5_run(repository)
    server = _start_server(repository)
    try:
        denied_response, denied = _json_request(
            server,
            "GET",
            "/v1/store-summary/agent.ai-sdlc?version=1.0.0&run_id=run_1",
            headers=_auth_headers(roles="agentops-ingestor"),
        )
        allowed_response, summary = _json_request(
            server,
            "GET",
            "/v1/store-summary/agent.ai-sdlc?version=1.0.0&run_id=run_1",
            headers=_auth_headers(roles="agent-store-consumer"),
        )
    finally:
        server.shutdown()

    assert denied_response.status == 403
    assert denied["denied_scope"] == "store.summary.read"
    assert allowed_response.status == 200
    assert summary["schema_version"] == "agentops.agent_store.echo.v1"
    assert summary["agentops_fact_owner"] == "AgentOps"


def test_ao23_ct_006_auth_errors_and_cors_do_not_expose_sensitive_values():
    repository = InMemoryRepository()
    server = _start_server(repository)
    try:
        options_response, _ = _json_request(
            server,
            "OPTIONS",
            "/v1/events",
            headers={"Origin": "http://127.0.0.1:5173"},
        )
        response, payload = _json_request(
            server, "POST", "/v1/events", payload={"events": [base_event()]}
        )
    finally:
        server.shutdown()

    serialized = json.dumps(payload, ensure_ascii=False).lower()
    assert options_response.getheader("Access-Control-Allow-Origin") == (
        "http://127.0.0.1:5173"
    )
    assert "X-AgentOps-Principal" in options_response.getheader(
        "Access-Control-Allow-Headers"
    )
    for forbidden in ("raw_payload", "token", "device_key", "credential_secret"):
        assert forbidden not in serialized
    assert response.status == 401


def test_ao23_ct_007_route_manifest_declares_production_auth_boundary():
    manifest = create_app()

    assert manifest["production_auth_boundary"].startswith("upstream headers:")


def test_ao23_ct_008_frontend_generation_artifacts_are_loader_compatible():
    module = pytest.importorskip(
        "ai_sdlc.generators.frontend_generation_constraint_artifacts"
    )
    root = Path(__file__).resolve().parents[2]

    constraints = module.load_frontend_generation_constraint_artifacts(root)

    assert constraints.work_item_id == "023"
    assert "DashboardPage" in constraints.recipe.allowed_recipe_ids
    assert any(
        rule.rule_id == "no-raw-material" for rule in constraints.hard_rules.rules
    )
