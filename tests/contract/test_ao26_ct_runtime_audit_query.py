from __future__ import annotations

import json
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from agentops.api.app import create_app
from agentops.api.server import create_http_handler
from agentops.storage.audit import AuditRecord, JsonlAuditLog
from agentops.storage.repository import InMemoryRepository


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
):
    connection = HTTPConnection(
        server.server_address[0], server.server_address[1], timeout=5
    )
    try:
        connection.request(method, path, headers=dict(headers or {}))
        response = connection.getresponse()
        response_body = response.read().decode("utf-8")
        response_payload = json.loads(response_body) if response_body else {}
        return response, response_payload
    finally:
        connection.close()


def _start_server(
    repository: InMemoryRepository,
    *,
    audit_log: JsonlAuditLog | None,
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
        "X-AgentOps-Principal": "audit.reader@example.com",
        "X-AgentOps-Request-Id": "req_ao26",
        "X-AgentOps-Audit-Id": "audit_ao26",
    }
    if roles:
        headers["X-AgentOps-Roles"] = roles
    if scopes:
        headers["X-AgentOps-Scopes"] = scopes
    return headers


def _audit_log(path: Path) -> JsonlAuditLog:
    audit_log = JsonlAuditLog(path)
    audit_log.append(
        AuditRecord(
            audit_id="audit_runtime_1",
            request_id="req_runtime_1",
            action="credential.revoke",
            outcome="accepted",
            principal="operator@example.com",
            roles=("agentops-operator",),
            scopes=("runtime.audit.read",),
            resource="/v1/bootstrap/credentials/boot-1/revoke",
        )
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write("{malformed-jsonl\n")
    audit_log.append(
        AuditRecord(
            audit_id="audit_runtime_2",
            request_id="req_runtime_2",
            action="store.summary.read",
            outcome="rejected",
            principal="operator@example.com",
            roles=("agentops-operator",),
            scopes=("runtime.audit.read",),
            resource="/v1/store-summary/agent.ai-sdlc",
            error_code="STORE_SUMMARY_QUERY_REQUIRED",
        )
    )
    audit_log.append(
        AuditRecord(
            audit_id="audit_runtime_3",
            request_id="req_runtime_3",
            action="credential.revoke",
            outcome="rejected",
            principal="operator@example.com",
            roles=("agentops-operator",),
            scopes=("runtime.audit.read",),
            resource="/v1/bootstrap/credentials/boot-2/revoke",
            error_code="CREDENTIAL_REVOCATION_NOT_FOUND",
        )
    )
    return audit_log


def test_ao26_ct_001_operator_can_query_filtered_runtime_audit(tmp_path: Path):
    audit_log = _audit_log(tmp_path / "audit.jsonl")
    server = _start_server(InMemoryRepository(), audit_log=audit_log)
    try:
        response, payload = _json_request(
            server,
            "GET",
            "/v1/audit/runtime?action=credential.revoke&limit=1",
            headers=_auth_headers(roles="agentops-operator"),
        )
    finally:
        server.shutdown()

    assert response.status == 200
    assert payload["schema_version"] == "agentops.runtime_audit.query.v1"
    assert payload["returned"] == 1
    assert payload["limit"] == 1
    assert payload["filters"] == {"action": "credential.revoke"}
    assert payload["records"][0]["audit_id"] == "audit_runtime_1"
    assert set(payload["records"][0]) == ALLOWED_AUDIT_FIELDS


def test_ao26_ct_002_viewer_is_denied_runtime_audit_scope(tmp_path: Path):
    audit_path = tmp_path / "audit.jsonl"
    audit_log = _audit_log(audit_path)
    server = _start_server(InMemoryRepository(), audit_log=audit_log)
    try:
        response, payload = _json_request(
            server,
            "GET",
            "/v1/audit/runtime",
            headers=_auth_headers(roles="agentops-viewer"),
        )
    finally:
        server.shutdown()

    records = JsonlAuditLog(audit_path).records()
    assert response.status == 403
    assert payload["error_code"] == "AGENTOPS_SCOPE_DENIED"
    assert payload["denied_scope"] == "runtime.audit.read"
    assert records[-1].action == "runtime.audit.read"
    assert records[-1].outcome == "denied"
    assert records[-1].denied_scope == "runtime.audit.read"


def test_ao26_ct_003_request_and_outcome_filters_can_return_no_matches(
    tmp_path: Path,
):
    audit_log = _audit_log(tmp_path / "audit.jsonl")
    server = _start_server(InMemoryRepository(), audit_log=audit_log)
    try:
        response, payload = _json_request(
            server,
            "GET",
            "/v1/audit/runtime?request_id=req_missing&outcome=accepted",
            headers=_auth_headers(roles="agentops-admin"),
        )
    finally:
        server.shutdown()

    assert response.status == 200
    assert payload["records"] == []
    assert payload["returned"] == 0
    assert payload["filters"] == {
        "request_id": "req_missing",
        "outcome": "accepted",
    }


def test_ao26_ct_004_invalid_limit_is_rejected_without_path_leak(tmp_path: Path):
    audit_log = _audit_log(tmp_path / "secret-audit-path.jsonl")
    server = _start_server(InMemoryRepository(), audit_log=audit_log)
    try:
        response, payload = _json_request(
            server,
            "GET",
            "/v1/audit/runtime?limit=zero",
            headers=_auth_headers(roles="agentops-operator"),
        )
    finally:
        server.shutdown()

    serialized = json.dumps(payload, ensure_ascii=False)
    assert response.status == 400
    assert payload["error_code"] == "AUDIT_LIMIT_INVALID"
    assert "secret-audit-path" not in serialized


def test_ao26_ct_005_missing_audit_log_is_reported_without_path_leak():
    server = _start_server(InMemoryRepository(), audit_log=None)
    try:
        response, payload = _json_request(
            server,
            "GET",
            "/v1/audit/runtime",
            headers=_auth_headers(roles="agentops-operator"),
        )
    finally:
        server.shutdown()

    assert response.status == 503
    assert payload == {
        "error_code": "AUDIT_LOG_UNAVAILABLE",
        "message": "Runtime audit log is not configured.",
        "retryable": True,
    }


def test_ao26_ct_006_runtime_audit_query_never_exposes_sensitive_markers(
    tmp_path: Path,
):
    audit_log = _audit_log(tmp_path / "audit.jsonl")
    server = _start_server(InMemoryRepository(), audit_log=audit_log)
    try:
        response, payload = _json_request(
            server,
            "GET",
            "/v1/audit/runtime?limit=200",
            headers=_auth_headers(roles="agentops-operator"),
        )
    finally:
        server.shutdown()

    serialized = json.dumps(payload, ensure_ascii=False).lower()
    assert response.status == 200
    assert payload["returned"] == 3
    for forbidden in (
        "raw_payload",
        "credential_secret",
        "credential material",
        "device_key",
        "token",
        "audit.jsonl",
    ):
        assert forbidden not in serialized


def test_ao26_ct_007_route_manifest_declares_runtime_audit_query():
    manifest = create_app()

    assert manifest["runtime_audit_query"] == "GET /v1/audit/runtime"
