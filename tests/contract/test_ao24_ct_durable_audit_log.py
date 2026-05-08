from __future__ import annotations

import json
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from agentops.api.app import create_app
from agentops.api.server import create_http_handler
from agentops.storage.audit import JsonlAuditLog
from agentops.storage.repository import InMemoryRepository
from tests.contract.conftest import base_event


ALLOWED_AUDIT_FIELDS = {
    "audit_id",
    "request_id",
    "action",
    "outcome",
    "principal",
    "roles",
    "scopes",
    "resource",
    "denied_scope",
    "error_code",
    "recorded_at",
}


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


def _start_server(
    repository: InMemoryRepository, audit_log: JsonlAuditLog
) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        create_http_handler(repository, require_auth=True, audit_log=audit_log),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _auth_headers(*, roles: str = "", scopes: str = "") -> dict[str, str]:
    headers = {
        "X-AgentOps-Principal": "user.ops@example.com",
        "X-AgentOps-Request-Id": "req_ao24",
        "X-AgentOps-Audit-Id": "audit_ao24",
    }
    if roles:
        headers["X-AgentOps-Roles"] = roles
    if scopes:
        headers["X-AgentOps-Scopes"] = scopes
    return headers


def _sensitive_event() -> dict:
    event = base_event(
        event_id="evt_ao24_sensitive",
        idempotency_key="ao24:sensitive:run_1",
        ingestion_token="secret_ingestion_token_value",
    )
    event["payload"].update(
        {
            "raw_payload": "secret raw payload",
            "token": "secret token value",
            "device_key": "secret device key",
            "credential_secret": "secret credential",
        }
    )
    return event


def test_ao24_ct_001_auth_denial_is_persisted_across_audit_log_instances(
    tmp_path: Path,
):
    audit_path = tmp_path / "nested" / "runtime-audit.jsonl"
    audit_log = JsonlAuditLog(audit_path)
    repository = InMemoryRepository()
    server = _start_server(repository, audit_log)
    try:
        response, payload = _json_request(
            server, "POST", "/v1/events", payload={"events": [_sensitive_event()]}
        )
    finally:
        server.shutdown()

    records = JsonlAuditLog(audit_path).records()
    assert response.status == 401
    assert payload["error_code"] == "UPSTREAM_IDENTITY_REQUIRED"
    assert repository.raw_event_count() == 0
    assert len(records) == 1
    assert records[0].audit_id == "audit_missing_identity"
    assert records[0].request_id == "req_missing_identity"
    assert records[0].action == "event.ingest"
    assert records[0].outcome == "denied"
    assert records[0].principal == "anonymous"
    assert records[0].denied_scope == "event.ingest"
    assert records[0].error_code == "UPSTREAM_IDENTITY_REQUIRED"


def test_ao24_ct_002_authorized_event_ingest_writes_minimal_audit_record(
    tmp_path: Path,
):
    audit_path = tmp_path / "runtime-audit.jsonl"
    audit_log = JsonlAuditLog(audit_path)
    repository = InMemoryRepository()
    server = _start_server(repository, audit_log)
    try:
        response, payload = _json_request(
            server,
            "POST",
            "/v1/events",
            headers=_auth_headers(roles="agentops-ingestor"),
            payload={"events": [_sensitive_event()]},
        )
    finally:
        server.shutdown()

    records = JsonlAuditLog(audit_path).records()
    assert response.status == 202
    assert payload["accepted"] == ["evt_ao24_sensitive"]
    assert repository.raw_event_count() == 1
    assert len(records) == 1
    assert records[0].audit_id == "audit_ao24"
    assert records[0].request_id == "req_ao24"
    assert records[0].principal == "user.ops@example.com"
    assert records[0].roles == ("agentops-ingestor",)
    assert records[0].action == "event.ingest"
    assert records[0].outcome == "accepted"
    assert records[0].error_code == ""


def test_ao24_ct_003_audit_jsonl_uses_stable_allowlisted_schema(tmp_path: Path):
    audit_path = tmp_path / "runtime-audit.jsonl"
    audit_log = JsonlAuditLog(audit_path)
    repository = InMemoryRepository()
    server = _start_server(repository, audit_log)
    try:
        response, _ = _json_request(
            server,
            "POST",
            "/v1/events",
            headers=_auth_headers(scopes="event.ingest"),
            payload={"events": [_sensitive_event()]},
        )
    finally:
        server.shutdown()

    raw_lines = audit_path.read_text(encoding="utf-8").splitlines()
    serialized_record = json.loads(raw_lines[0])
    assert response.status == 202
    assert set(serialized_record) == ALLOWED_AUDIT_FIELDS


def test_ao24_ct_004_audit_jsonl_never_records_sensitive_request_material(
    tmp_path: Path,
):
    audit_path = tmp_path / "runtime-audit.jsonl"
    audit_log = JsonlAuditLog(audit_path)
    repository = InMemoryRepository()
    server = _start_server(repository, audit_log)
    try:
        _json_request(
            server,
            "POST",
            "/v1/events",
            headers=_auth_headers(roles="agentops-ingestor"),
            payload={"events": [_sensitive_event()]},
        )
        _json_request(
            server, "POST", "/v1/events", payload={"events": [_sensitive_event()]}
        )
    finally:
        server.shutdown()

    serialized = audit_path.read_text(encoding="utf-8").lower()
    for forbidden in (
        "raw_payload",
        "secret raw payload",
        "token",
        "secret_ingestion_token_value",
        "device_key",
        "credential_secret",
    ):
        assert forbidden not in serialized


def test_ao24_ct_005_route_manifest_declares_durable_audit_boundary():
    manifest = create_app()

    assert manifest["durable_audit_log"] == "append-only JSONL runtime audit boundary"
