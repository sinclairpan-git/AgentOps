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
    upstream: ThreadingHTTPServer, *, token: str = "gateway-token", **gateway_options
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
            **gateway_options,
        ),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _json_request(
    server: ThreadingHTTPServer,
    *,
    method: str = "POST",
    path: str = "/v1/runtime/events",
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
        connection.request(method, path, body=body, headers=request_headers)
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


def test_ao57_ct_011_reference_gateway_forwards_console_snapshot_for_compose_ui():
    repository = InMemoryRepository()
    upstream = _start_server(repository)
    gateway = _start_gateway(upstream)
    try:
        ingest_status, receipt = _json_request(
            gateway,
            headers={"Authorization": "Bearer gateway-token"},
            payload=_fixture_batch(),
        )
        snapshot_status, snapshot = _json_request(
            gateway,
            method="GET",
            path="/v1/console/snapshot",
        )
    finally:
        gateway.shutdown()
        gateway.server_close()
        upstream.shutdown()
        upstream.server_close()

    workbench = snapshot["consoleData"]["sdlcRunWorkbench"]
    assert ingest_status == 202
    assert receipt["accepted_count"] == 2
    assert snapshot_status == 200
    assert workbench["taskGuard"][0]["run_id"] == "run_sdlc_001"
    assert workbench["outboxReceipts"][0]["outbox_state"] == "delivered"
    assert workbench["evidenceReadiness"][0]["raw_payload_state"] == "summary_only"


def test_ao57_ct_012_reference_gateway_rejects_revoked_token_without_leaking_it():
    repository = InMemoryRepository()
    upstream = _start_server(repository)
    gateway = _start_gateway(upstream, revoked_tokens={"gateway-token"})
    try:
        status, payload = _json_request(
            gateway,
            headers={"Authorization": "Bearer gateway-token"},
            payload=_fixture_batch(),
        )
    finally:
        gateway.shutdown()
        gateway.server_close()
        upstream.shutdown()
        upstream.server_close()

    assert status == 401
    assert payload["error_code"] == "GATEWAY_TOKEN_REVOKED"
    assert "gateway-token" not in json.dumps(payload)
    assert repository.trace_span_count() == 0


def test_ao57_ct_013_reference_gateway_rejects_oversized_runtime_batch():
    repository = InMemoryRepository()
    upstream = _start_server(repository)
    gateway = _start_gateway(upstream, max_body_bytes=32)
    try:
        status, payload = _json_request(
            gateway,
            headers={"Authorization": "Bearer gateway-token"},
            payload=_fixture_batch(),
        )
    finally:
        gateway.shutdown()
        gateway.server_close()
        upstream.shutdown()
        upstream.server_close()

    assert status == 413
    assert payload["error_code"] == "GATEWAY_REQUEST_TOO_LARGE"
    assert payload["max_body_bytes"] == 32
    assert repository.trace_span_count() == 0


def test_ao57_ct_014_reference_gateway_rate_limits_producer_token():
    repository = InMemoryRepository()
    upstream = _start_server(repository)
    gateway = _start_gateway(upstream, rate_limit_per_minute=1)
    try:
        first_status, first_receipt = _json_request(
            gateway,
            headers={"Authorization": "Bearer gateway-token"},
            payload=_fixture_batch(),
        )
        second_status, second_payload = _json_request(
            gateway,
            headers={"Authorization": "Bearer gateway-token"},
            payload=_fixture_batch(),
        )
    finally:
        gateway.shutdown()
        gateway.server_close()
        upstream.shutdown()
        upstream.server_close()

    assert first_status == 202
    assert first_receipt["accepted_count"] == 2
    assert second_status == 429
    assert second_payload["error_code"] == "GATEWAY_RATE_LIMITED"
    assert second_payload["retry_after_seconds"] > 0
    assert repository.trace_span_count() == 2


def test_ao57_ct_015_reference_gateway_writes_redacted_gateway_audit(tmp_path):
    audit_log = tmp_path / "gateway-audit.jsonl"
    repository = InMemoryRepository()
    upstream = _start_server(repository)
    gateway = _start_gateway(upstream, audit_log_path=str(audit_log))
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
    records = [
        json.loads(line)
        for line in audit_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert records
    assert records[-1]["schema_version"] == "agentops_gateway_audit.v1"
    assert records[-1]["producer_principal"] == "producer.ai-sdlc.local"
    assert records[-1]["outcome"] == "accepted"
    assert records[-1]["inbound_identity_stripped"] is True
    serialized = json.dumps(records, ensure_ascii=False)
    assert "gateway-token" not in serialized
    assert "forged.client" not in serialized
    assert "evt_sdlc_task_prepared_001" not in serialized


def test_ao57_ct_016_reference_gateway_keeps_route_allowlist_closed():
    repository = InMemoryRepository()
    upstream = _start_server(repository)
    gateway = _start_gateway(upstream)
    try:
        status, payload = _json_request(
            gateway,
            path="/v1/events",
            headers={"Authorization": "Bearer gateway-token"},
            payload=_fixture_batch(),
        )
    finally:
        gateway.shutdown()
        gateway.server_close()
        upstream.shutdown()
        upstream.server_close()

    assert status == 404
    assert payload["error_code"] == "GATEWAY_ROUTE_NOT_FOUND"
    assert repository.trace_span_count() == 0


def test_ao57_ct_017_operator_role_can_read_trace_and_evidence_summary():
    repository = InMemoryRepository()
    server = _start_server(repository)
    try:
        ingest_status, receipt = _json_request(
            server,
            headers=_gateway_headers(scopes="event.ingest"),
            payload=_fixture_batch(),
        )
        read_headers = {
            "X-AgentOps-Principal": "ops.local",
            "X-AgentOps-Roles": "agentops-operator",
        }
        trace_status, trace = _json_request(
            server,
            method="GET",
            path="/v1/runtime/runs/run_sdlc_001/trace",
            headers=read_headers,
        )
        evidence_status, evidence = _json_request(
            server,
            method="GET",
            path="/v1/runtime/runs/run_sdlc_001/evidence-summary",
            headers=read_headers,
        )
    finally:
        server.shutdown()
        server.server_close()

    assert ingest_status == 202
    assert receipt["accepted_count"] == 2
    assert trace_status == 200
    assert trace["aggregate"]["span_count"] == 2
    assert evidence_status == 200
    assert evidence["raw_access_state"] == "summary_only"
