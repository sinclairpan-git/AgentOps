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


def _auth_headers(
    *, roles: str = "agentops-operator", scopes: str = ""
) -> dict[str, str]:
    headers = {
        "X-AgentOps-Principal": "audit.exporter@example.com",
        "X-AgentOps-Request-Id": "req_ao29",
        "X-AgentOps-Audit-Id": "audit_ao29",
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
            scopes=("runtime.audit.read", "runtime.audit.export"),
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
            scopes=("runtime.audit.read", "runtime.audit.export"),
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


class _DriftingReadAuditLog(JsonlAuditLog):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.records_calls = 0

    def records(self) -> list[AuditRecord]:
        self.records_calls += 1
        records = super().records()
        if self.records_calls <= 1:
            return records
        return [
            *records,
            AuditRecord(
                audit_id="audit_runtime_3",
                request_id="req_runtime_3",
                action="credential.revoke",
                outcome="accepted",
                principal="operator@example.com",
                roles=("agentops-operator",),
                scopes=("runtime.audit.read", "runtime.audit.export"),
                resource="/v1/bootstrap/credentials/boot-3/revoke",
            ),
        ]


def _manifest_request(
    server: ThreadingHTTPServer,
    *,
    path: str = "/v1/audit/runtime/export-manifest?action=credential.revoke&limit=2",
):
    response, payload = _json_request(
        server,
        "GET",
        path,
        headers=_auth_headers(),
    )
    assert response.status == 200
    return payload


def test_ao29_ct_001_operator_materializes_manifest_gated_bundle(tmp_path: Path):
    audit_path = tmp_path / "audit.jsonl"
    audit_log = _audit_log(audit_path)
    server = _start_server(InMemoryRepository(), audit_log=audit_log)
    try:
        manifest = _manifest_request(server)
        response, payload = _json_request(
            server,
            "POST",
            "/v1/audit/runtime/export-bundle",
            headers=_auth_headers(),
            payload={
                "manifest_id": manifest["manifest_id"],
                "content_digest": manifest["content_digest"],
                "filters": {"action": "credential.revoke"},
                "limit": 2,
            },
        )
    finally:
        server.shutdown()

    records = JsonlAuditLog(audit_path).records()
    assert response.status == 200
    assert payload["schema_version"] == "agentops.runtime_audit.export_bundle.v1"
    assert (
        payload["bundle_format"]
        == "application/vnd.agentops.runtime-audit.metadata+json"
    )
    assert payload["digest_algorithm"] == "sha256"
    assert len(payload["bundle_digest"]) == 64
    assert payload["manifest_id"] == manifest["manifest_id"]
    assert payload["manifest_digest"] == manifest["content_digest"]
    assert payload["filters"] == {"action": "credential.revoke"}
    assert payload["limit"] == 2
    assert payload["record_count"] == 2
    assert [record["audit_id"] for record in payload["records"]] == [
        "audit_runtime_1",
        "audit_runtime_2",
    ]
    assert all(set(record) == ALLOWED_AUDIT_FIELDS for record in payload["records"])
    assert (
        payload["records"][1]["resource"] == "/v1/bootstrap/credentials/boot-2/revoke"
    )
    assert payload["download_url"] == ""
    assert records[-1].action == "runtime.audit.export.bundle"
    assert records[-1].outcome == "accepted"


def test_ao29_ct_002_export_bundle_does_not_expose_sensitive_markers(tmp_path: Path):
    audit_log = _audit_log(tmp_path / "secret-audit-path.jsonl")
    server = _start_server(InMemoryRepository(), audit_log=audit_log)
    try:
        manifest = _manifest_request(server)
        response, payload = _json_request(
            server,
            "POST",
            "/v1/audit/runtime/export-bundle",
            headers=_auth_headers(),
            payload={
                "manifest_id": manifest["manifest_id"],
                "content_digest": manifest["content_digest"],
                "filters": {"action": "credential.revoke"},
                "limit": 2,
                "raw_payload": "credential_secret token=secret device_key",
            },
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


def test_ao29_ct_003_viewer_is_denied_export_scope_and_audited(tmp_path: Path):
    audit_path = tmp_path / "audit.jsonl"
    audit_log = _audit_log(audit_path)
    server = _start_server(InMemoryRepository(), audit_log=audit_log)
    try:
        manifest = _manifest_request(server)
        response, payload = _json_request(
            server,
            "POST",
            "/v1/audit/runtime/export-bundle",
            headers=_auth_headers(roles="agentops-viewer"),
            payload={
                "manifest_id": manifest["manifest_id"],
                "content_digest": manifest["content_digest"],
                "filters": {"action": "credential.revoke"},
                "limit": 2,
            },
        )
    finally:
        server.shutdown()

    records = JsonlAuditLog(audit_path).records()
    assert response.status == 403
    assert payload["error_code"] == "AGENTOPS_SCOPE_DENIED"
    assert payload["denied_scope"] == "runtime.audit.export"
    assert records[-1].action == "runtime.audit.export.bundle"
    assert records[-1].outcome == "denied"
    assert records[-1].denied_scope == "runtime.audit.export"


def test_ao29_ct_004_manifest_mismatch_is_rejected_without_records(tmp_path: Path):
    audit_path = tmp_path / "audit.jsonl"
    audit_log = _audit_log(audit_path)
    server = _start_server(InMemoryRepository(), audit_log=audit_log)
    try:
        manifest = _manifest_request(server)
        response, payload = _json_request(
            server,
            "POST",
            "/v1/audit/runtime/export-bundle",
            headers=_auth_headers(),
            payload={
                "manifest_id": manifest["manifest_id"],
                "content_digest": "0" * 64,
                "filters": {"action": "credential.revoke"},
                "limit": 2,
            },
        )
    finally:
        server.shutdown()

    serialized = json.dumps(payload, ensure_ascii=False).lower()
    records = JsonlAuditLog(audit_path).records()
    assert response.status == 409
    assert payload["error_code"] == "AUDIT_EXPORT_MANIFEST_MISMATCH"
    assert "records" not in payload
    assert "token=secret" not in serialized
    assert records[-1].action == "runtime.audit.export.bundle"
    assert records[-1].outcome == "rejected"
    assert records[-1].error_code == "AUDIT_EXPORT_MANIFEST_MISMATCH"


def test_ao29_ct_005_manifest_query_mismatch_is_rejected_without_records(
    tmp_path: Path,
):
    audit_path = tmp_path / "audit.jsonl"
    audit_log = _audit_log(audit_path)
    server = _start_server(InMemoryRepository(), audit_log=audit_log)
    try:
        manifest = _manifest_request(server)
        response, payload = _json_request(
            server,
            "POST",
            "/v1/audit/runtime/export-bundle",
            headers=_auth_headers(),
            payload={
                "manifest_id": manifest["manifest_id"],
                "content_digest": manifest["content_digest"],
                "filters": {"action": "credential.revoke"},
            },
        )
    finally:
        server.shutdown()

    records = JsonlAuditLog(audit_path).records()
    assert response.status == 409
    assert payload["error_code"] == "AUDIT_EXPORT_MANIFEST_MISMATCH"
    assert "records" not in payload
    assert records[-1].action == "runtime.audit.export.bundle"
    assert records[-1].outcome == "rejected"
    assert records[-1].error_code == "AUDIT_EXPORT_MANIFEST_MISMATCH"


def test_ao29_ct_006_invalid_filters_are_rejected_and_audited(tmp_path: Path):
    audit_path = tmp_path / "secret-audit-path.jsonl"
    audit_log = _audit_log(audit_path)
    server = _start_server(InMemoryRepository(), audit_log=audit_log)
    try:
        response, payload = _json_request(
            server,
            "POST",
            "/v1/audit/runtime/export-bundle",
            headers=_auth_headers(),
            payload={
                "manifest_id": "audit_export_fake",
                "content_digest": "0" * 64,
                "filters": {
                    "resource": "/v1/bootstrap/credentials/boot-2?token=secret"
                },
                "limit": 2,
            },
        )
    finally:
        server.shutdown()

    serialized = json.dumps(payload, ensure_ascii=False).lower()
    records = JsonlAuditLog(audit_path).records()
    assert response.status == 400
    assert payload["error_code"] == "AUDIT_EXPORT_FILTERS_INVALID"
    assert "secret-audit-path" not in serialized
    assert "token=secret" not in serialized
    assert records[-1].action == "runtime.audit.export.bundle"
    assert records[-1].outcome == "rejected"
    assert records[-1].error_code == "AUDIT_EXPORT_FILTERS_INVALID"


def test_ao29_ct_007_falsey_non_object_filters_are_rejected(tmp_path: Path):
    audit_path = tmp_path / "audit.jsonl"
    audit_log = _audit_log(audit_path)
    server = _start_server(InMemoryRepository(), audit_log=audit_log)
    try:
        response, payload = _json_request(
            server,
            "POST",
            "/v1/audit/runtime/export-bundle",
            headers=_auth_headers(),
            payload={
                "manifest_id": "audit_export_fake",
                "content_digest": "0" * 64,
                "filters": "",
                "limit": 2,
            },
        )
    finally:
        server.shutdown()

    records = JsonlAuditLog(audit_path).records()
    assert response.status == 400
    assert payload["error_code"] == "AUDIT_EXPORT_FILTERS_INVALID"
    assert records[-1].action == "runtime.audit.export.bundle"
    assert records[-1].outcome == "rejected"
    assert records[-1].error_code == "AUDIT_EXPORT_FILTERS_INVALID"


def test_ao29_ct_008_bundle_uses_one_audit_snapshot_for_manifest_gate(
    tmp_path: Path,
):
    audit_path = tmp_path / "audit.jsonl"
    audit_log = _audit_log(audit_path)
    manifest_server = _start_server(InMemoryRepository(), audit_log=audit_log)
    try:
        manifest = _manifest_request(manifest_server)
    finally:
        manifest_server.shutdown()

    drifting_audit_log = _DriftingReadAuditLog(audit_path)
    bundle_server = _start_server(InMemoryRepository(), audit_log=drifting_audit_log)
    try:
        response, payload = _json_request(
            bundle_server,
            "POST",
            "/v1/audit/runtime/export-bundle",
            headers=_auth_headers(),
            payload={
                "manifest_id": manifest["manifest_id"],
                "content_digest": manifest["content_digest"],
                "filters": {"action": "credential.revoke"},
                "limit": 2,
            },
        )
    finally:
        bundle_server.shutdown()

    assert response.status == 200
    assert payload["manifest_digest"] == manifest["content_digest"]
    assert payload["record_count"] == 2
    assert [record["audit_id"] for record in payload["records"]] == [
        "audit_runtime_1",
        "audit_runtime_2",
    ]
    assert drifting_audit_log.records_calls == 1


def test_ao29_ct_009_route_manifest_declares_runtime_audit_export_bundle():
    manifest = create_app()

    assert manifest["runtime_audit_export_bundle"] == (
        "POST /v1/audit/runtime/export-bundle"
    )
