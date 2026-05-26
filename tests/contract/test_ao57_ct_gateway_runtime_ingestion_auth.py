from __future__ import annotations

import json
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from agentops.api.gateway import create_gateway_handler
from agentops.api.server import create_http_handler
from agentops.storage.repository import InMemoryRepository

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "contracts"
    / "cross-project"
    / "fixtures"
    / "ai_sdlc_executable_task_runtime_batch.v1.json"
)


def _fixture_batch() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _start_server(repository: InMemoryRepository) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), create_http_handler(repository, require_auth=True)
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _start_gateway(
    upstream: ThreadingHTTPServer, *, token: str = "gateway-token"
) -> ThreadingHTTPServer:
    upstream_base = f"http://{upstream.server_address[0]}:{upstream.server_address[1]}"
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        create_gateway_handler(
            upstream_base=upstream_base,
            token=token,
            principal="producer.ai-sdlc.local",
            roles="",
            scopes="event.ingest",
        ),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _json_request(
    server: ThreadingHTTPServer,
    *,
    headers: dict[str, str] | None = None,
    payload: dict | None = None,
) -> tuple[int, dict]:
    connection = HTTPConnection(
        server.server_address[0], server.server_address[1], timeout=5
    )
    try:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request_headers = {"Content-Type": "application/json"}
        request_headers.update(headers or {})
        connection.request(
            "POST", "/v1/runtime/events", body=body, headers=request_headers
        )
        response = connection.getresponse()
        raw_body = response.read().decode("utf-8")
        return response.status, json.loads(raw_body) if raw_body else {}
    finally:
        connection.close()


def _gateway_headers(*, roles: str = "", scopes: str = "") -> dict[str, str]:
    headers = {
        "X-AgentOps-Principal": "producer.ai-sdlc.local",
        "X-AgentOps-Request-Id": "req_gateway_sdlc",
        "X-AgentOps-Audit-Id": "audit_gateway_sdlc",
    }
    if roles:
        headers["X-AgentOps-Roles"] = roles
    if scopes:
        headers["X-AgentOps-Scopes"] = scopes
    return headers


def test_ao57_ct_005_runtime_ingestion_rejects_bearer_without_gateway_identity():
    repository = InMemoryRepository()
    server = _start_server(repository)
    try:
        status, payload = _json_request(
            server,
            headers={"Authorization": "Bearer token_secret_123"},
            payload=_fixture_batch(),
        )
    finally:
        server.shutdown()
        server.server_close()

    assert status == 401
    assert payload["error_code"] == "UPSTREAM_IDENTITY_REQUIRED"
    assert payload["denied_scope"] == "event.ingest"
    assert "token_secret_123" not in json.dumps(payload)
    assert repository.trace_span_count() == 0


def test_ao57_ct_006_gateway_ingestor_scope_can_post_sdlc_runtime_batch():
    repository = InMemoryRepository()
    server = _start_server(repository)
    try:
        status, receipt = _json_request(
            server,
            headers=_gateway_headers(scopes="event.ingest"),
            payload=_fixture_batch(),
        )
    finally:
        server.shutdown()
        server.server_close()

    assert status == 202
    assert receipt["schema_version"] == "runtime_outbox_receipt.v1"
    assert receipt["accepted_count"] == 2
    assert receipt["rejected_count"] == 0
    assert repository.trace_span_count() == 2


def test_ao57_ct_007_gateway_ingestor_role_can_post_sdlc_runtime_batch():
    repository = InMemoryRepository()
    server = _start_server(repository)
    try:
        status, receipt = _json_request(
            server,
            headers=_gateway_headers(roles="agentops-ingestor"),
            payload=_fixture_batch(),
        )
    finally:
        server.shutdown()
        server.server_close()

    assert status == 202
    assert receipt["producer"] == "Ai_AutoSDLC"
    assert repository.runtime_outbox_receipt_records()[0]["outbox_state"] == "delivered"


def test_ao57_ct_008_gateway_viewer_scope_cannot_post_runtime_batch():
    repository = InMemoryRepository()
    server = _start_server(repository)
    try:
        status, payload = _json_request(
            server,
            headers=_gateway_headers(roles="agentops-viewer"),
            payload=_fixture_batch(),
        )
    finally:
        server.shutdown()
        server.server_close()

    assert status == 403
    assert payload["error_code"] == "AGENTOPS_SCOPE_DENIED"
    assert payload["denied_scope"] == "event.ingest"
    assert repository.trace_span_count() == 0


def test_ao57_ct_009_reference_gateway_cleans_client_identity_headers():
    repository = InMemoryRepository()
    upstream = _start_server(repository)
    gateway = _start_gateway(upstream)
    try:
        status, receipt = _json_request(
            gateway,
            headers={
                "Authorization": "Bearer gateway-token",
                "X-AgentOps-Principal": "forged.client",
                "X-AgentOps-Roles": "agentops-viewer",
                "X-AgentOps-Scopes": "console.snapshot.read",
            },
            payload=_fixture_batch(),
        )
    finally:
        gateway.shutdown()
        gateway.server_close()
        upstream.shutdown()
        upstream.server_close()

    assert status == 202
    assert receipt["accepted_count"] == 2
    assert repository.trace_span_count() == 2


def test_ao57_ct_010_reference_gateway_rejects_bad_token_without_leaking_it():
    repository = InMemoryRepository()
    upstream = _start_server(repository)
    gateway = _start_gateway(upstream)
    try:
        status, payload = _json_request(
            gateway,
            headers={"Authorization": "Bearer token_secret_bad"},
            payload=_fixture_batch(),
        )
    finally:
        gateway.shutdown()
        gateway.server_close()
        upstream.shutdown()
        upstream.server_close()

    assert status == 401
    assert payload["error_code"] == "GATEWAY_TOKEN_INVALID"
    assert "token_secret_bad" not in json.dumps(payload)
    assert repository.trace_span_count() == 0
