from __future__ import annotations

import json
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from agentops.api.server import create_http_handler
from agentops.storage.audit import AuditRecord, JsonlAuditLog
from agentops.storage.repository import InMemoryRepository


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
        create_http_handler(
            repository,
            require_auth=True,
            audit_log=audit_log,
            audit_cursor_secret="test-runtime-audit-cursor-secret",
        ),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _auth_headers(*, roles: str = "agentops-operator") -> dict[str, str]:
    return {
        "X-AgentOps-Principal": "audit.exporter@example.com",
        "X-AgentOps-Request-Id": "req_ao28",
        "X-AgentOps-Audit-Id": "audit_ao28",
        "X-AgentOps-Roles": roles,
    }


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
    audit_log.append(
        AuditRecord(
            audit_id="audit_runtime_2",
            request_id="req_runtime_2",
            action="credential.revoke",
            outcome="rejected",
            principal="operator@example.com",
            roles=("agentops-operator",),
            scopes=("runtime.audit.read",),
            resource="/v1/bootstrap/credentials/boot-2/revoke?token=secret",
            error_code="CREDENTIAL_REVOCATION_NOT_FOUND",
        )
    )
    audit_log.append(
        AuditRecord(
            audit_id="audit_store_1",
            request_id="req_store_1",
            action="store.summary.read",
            outcome="accepted",
            principal="operator@example.com",
            roles=("agentops-operator",),
            scopes=("runtime.audit.read",),
            resource="/v1/store-summary/agent.ai-sdlc",
        )
    )
    return audit_log


def test_ao28_ct_001_operator_gets_stable_metadata_export_manifest(
    tmp_path: Path,
):
    audit_path = tmp_path / "audit.jsonl"
    audit_log = _audit_log(audit_path)
    server = _start_server(InMemoryRepository(), audit_log=audit_log)
    try:
        first_response, first_payload = _json_request(
            server,
            "GET",
            "/v1/audit/runtime/export-manifest?action=credential.revoke&limit=2",
            headers=_auth_headers(),
        )
        second_response, second_payload = _json_request(
            server,
            "GET",
            "/v1/audit/runtime/export-manifest?action=credential.revoke&limit=2",
            headers=_auth_headers(),
        )
    finally:
        server.shutdown()

    records = JsonlAuditLog(audit_path).records()
    assert first_response.status == 200
    assert second_response.status == 200
    assert first_payload["schema_version"] == "agentops.runtime_audit.export_manifest.v1"
    assert first_payload["filters"] == {"action": "credential.revoke"}
    assert first_payload["limit"] == 2
    assert first_payload["record_count"] == 2
    assert first_payload["record_audit_ids"] == [
        "audit_runtime_1",
        "audit_runtime_2",
    ]
    assert first_payload["digest_algorithm"] == "sha256"
    assert len(first_payload["content_digest"]) == 64
    assert first_payload["content_digest"] == second_payload["content_digest"]
    assert first_payload["manifest_id"] == second_payload["manifest_id"]
    assert first_payload["export_available"] is False
    assert first_payload["download_url"] == ""
    assert records[-2].action == "runtime.audit.export"
    assert records[-2].outcome == "accepted"
    assert records[-1].action == "runtime.audit.export"
    assert records[-1].outcome == "accepted"


def test_ao28_ct_002_export_manifest_does_not_expose_sensitive_markers(
    tmp_path: Path,
):
    audit_log = _audit_log(tmp_path / "secret-audit-path.jsonl")
    server = _start_server(InMemoryRepository(), audit_log=audit_log)
    try:
        response, payload = _json_request(
            server,
            "GET",
            "/v1/audit/runtime/export-manifest?action=credential.revoke&limit=2",
            headers=_auth_headers(),
        )
    finally:
        server.shutdown()

    serialized = json.dumps(payload, ensure_ascii=False).lower()
    assert response.status == 200
    assert payload["download_url"] == ""
    for forbidden in (
        "raw_payload",
        "credential_secret",
        "credential material",
        "device_key",
        "token=secret",
        "secret-audit-path",
    ):
        assert forbidden not in serialized


def test_ao28_ct_003_broad_export_manifest_excludes_export_audits(
    tmp_path: Path,
):
    audit_path = tmp_path / "audit.jsonl"
    audit_log = _audit_log(audit_path)
    server = _start_server(InMemoryRepository(), audit_log=audit_log)
    try:
        first_response, first_payload = _json_request(
            server,
            "GET",
            "/v1/audit/runtime/export-manifest?limit=10",
            headers=_auth_headers(),
        )
        second_response, second_payload = _json_request(
            server,
            "GET",
            "/v1/audit/runtime/export-manifest?limit=10",
            headers=_auth_headers(),
        )
    finally:
        server.shutdown()

    records = JsonlAuditLog(audit_path).records()
    assert first_response.status == 200
    assert second_response.status == 200
    assert first_payload["record_count"] == 3
    assert first_payload["record_audit_ids"] == [
        "audit_runtime_1",
        "audit_runtime_2",
        "audit_store_1",
    ]
    assert first_payload["content_digest"] == second_payload["content_digest"]
    assert first_payload["record_count"] == second_payload["record_count"]
    assert records[-2].action == "runtime.audit.export"
    assert records[-1].action == "runtime.audit.export"


def test_ao28_ct_004_explicit_export_action_filter_includes_export_audits(
    tmp_path: Path,
):
    audit_path = tmp_path / "audit.jsonl"
    audit_log = _audit_log(audit_path)
    server = _start_server(InMemoryRepository(), audit_log=audit_log)
    try:
        seed_response, _ = _json_request(
            server,
            "GET",
            "/v1/audit/runtime/export-manifest?action=credential.revoke&limit=2",
            headers=_auth_headers(),
        )
        response, payload = _json_request(
            server,
            "GET",
            "/v1/audit/runtime/export-manifest?action=runtime.audit.export&limit=10",
            headers=_auth_headers(),
        )
    finally:
        server.shutdown()

    records = JsonlAuditLog(audit_path).records()
    assert seed_response.status == 200
    assert response.status == 200
    assert payload["filters"] == {"action": "runtime.audit.export"}
    assert payload["record_count"] == 1
    assert payload["record_audit_ids"] == ["audit_ao28"]
    assert records[-2].action == "runtime.audit.export"
    assert records[-1].action == "runtime.audit.export"


def test_ao28_ct_005_viewer_is_denied_and_audited(tmp_path: Path):
    audit_path = tmp_path / "audit.jsonl"
    audit_log = _audit_log(audit_path)
    server = _start_server(InMemoryRepository(), audit_log=audit_log)
    try:
        response, payload = _json_request(
            server,
            "GET",
            "/v1/audit/runtime/export-manifest",
            headers=_auth_headers(roles="agentops-viewer"),
        )
    finally:
        server.shutdown()

    records = JsonlAuditLog(audit_path).records()
    assert response.status == 403
    assert payload["error_code"] == "AGENTOPS_SCOPE_DENIED"
    assert payload["denied_scope"] == "runtime.audit.read"
    assert records[-1].action == "runtime.audit.export"
    assert records[-1].outcome == "denied"
    assert records[-1].denied_scope == "runtime.audit.read"


def test_ao28_ct_006_invalid_limit_is_rejected_and_audited(tmp_path: Path):
    audit_path = tmp_path / "secret-audit-path.jsonl"
    audit_log = _audit_log(audit_path)
    server = _start_server(InMemoryRepository(), audit_log=audit_log)
    try:
        response, payload = _json_request(
            server,
            "GET",
            "/v1/audit/runtime/export-manifest?limit=zero",
            headers=_auth_headers(),
        )
    finally:
        server.shutdown()

    serialized = json.dumps(payload, ensure_ascii=False).lower()
    records = JsonlAuditLog(audit_path).records()
    assert response.status == 400
    assert payload["error_code"] == "AUDIT_LIMIT_INVALID"
    assert "secret-audit-path" not in serialized
    assert records[-1].action == "runtime.audit.export"
    assert records[-1].outcome == "rejected"
    assert records[-1].error_code == "AUDIT_LIMIT_INVALID"
