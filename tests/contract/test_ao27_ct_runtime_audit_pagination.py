from __future__ import annotations

import base64
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
    audit_cursor_secret: str | bytes | None = "test-runtime-audit-cursor-secret",
) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        create_http_handler(
            repository,
            require_auth=True,
            audit_log=audit_log,
            audit_cursor_secret=audit_cursor_secret,
        ),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _auth_headers(*, roles: str = "agentops-operator") -> dict[str, str]:
    return {
        "X-AgentOps-Principal": "audit.reader@example.com",
        "X-AgentOps-Request-Id": "req_ao27",
        "X-AgentOps-Audit-Id": "audit_ao27",
        "X-AgentOps-Roles": roles,
    }


def _audit_log(path: Path) -> JsonlAuditLog:
    audit_log = JsonlAuditLog(path)
    for index in range(1, 6):
        audit_log.append(
            AuditRecord(
                audit_id=f"audit_runtime_{index}",
                request_id=f"req_runtime_{index}",
                action="credential.revoke",
                outcome="accepted" if index % 2 else "rejected",
                principal="operator@example.com",
                roles=("agentops-operator",),
                scopes=("runtime.audit.read",),
                resource=f"/v1/bootstrap/credentials/boot-{index}/revoke",
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


def test_ao27_ct_001_runtime_audit_query_returns_next_cursor(tmp_path: Path):
    audit_log = _audit_log(tmp_path / "audit.jsonl")
    server = _start_server(InMemoryRepository(), audit_log=audit_log)
    try:
        response, payload = _json_request(
            server,
            "GET",
            "/v1/audit/runtime?action=credential.revoke&limit=2",
            headers=_auth_headers(),
        )
    finally:
        server.shutdown()

    assert response.status == 200
    assert payload["returned"] == 2
    assert [record["audit_id"] for record in payload["records"]] == [
        "audit_runtime_1",
        "audit_runtime_2",
    ]
    assert payload["page_info"]["cursor"] == ""
    assert payload["page_info"]["has_more"] is True
    assert payload["page_info"]["next_cursor"]


def test_ao27_ct_002_cursor_reads_next_page_without_duplicates(tmp_path: Path):
    audit_log = _audit_log(tmp_path / "audit.jsonl")
    server = _start_server(InMemoryRepository(), audit_log=audit_log)
    try:
        first_response, first_payload = _json_request(
            server,
            "GET",
            "/v1/audit/runtime?action=credential.revoke&limit=2",
            headers=_auth_headers(),
        )
        cursor = first_payload["page_info"]["next_cursor"]
        second_response, second_payload = _json_request(
            server,
            "GET",
            f"/v1/audit/runtime?action=credential.revoke&limit=2&cursor={cursor}",
            headers=_auth_headers(),
        )
    finally:
        server.shutdown()

    assert first_response.status == 200
    assert second_response.status == 200
    assert [record["audit_id"] for record in second_payload["records"]] == [
        "audit_runtime_3",
        "audit_runtime_4",
    ]
    assert second_payload["page_info"]["cursor"] == cursor
    assert second_payload["page_info"]["has_more"] is True
    assert second_payload["page_info"]["next_cursor"] != cursor


def test_ao27_ct_003_final_page_has_no_next_cursor(tmp_path: Path):
    audit_log = _audit_log(tmp_path / "audit.jsonl")
    server = _start_server(InMemoryRepository(), audit_log=audit_log)
    try:
        _, first_payload = _json_request(
            server,
            "GET",
            "/v1/audit/runtime?action=credential.revoke&limit=3",
            headers=_auth_headers(),
        )
        cursor = first_payload["page_info"]["next_cursor"]
        response, payload = _json_request(
            server,
            "GET",
            f"/v1/audit/runtime?action=credential.revoke&limit=3&cursor={cursor}",
            headers=_auth_headers(),
        )
    finally:
        server.shutdown()

    assert response.status == 200
    assert [record["audit_id"] for record in payload["records"]] == [
        "audit_runtime_4",
        "audit_runtime_5",
    ]
    assert payload["page_info"]["has_more"] is False
    assert payload["page_info"]["next_cursor"] == ""


def test_ao27_ct_004_malformed_cursor_is_rejected_and_audited(tmp_path: Path):
    audit_path = tmp_path / "secret-audit-path.jsonl"
    audit_log = _audit_log(audit_path)
    server = _start_server(InMemoryRepository(), audit_log=audit_log)
    try:
        response, payload = _json_request(
            server,
            "GET",
            "/v1/audit/runtime?action=credential.revoke&cursor=not-a-valid-cursor",
            headers=_auth_headers(),
        )
    finally:
        server.shutdown()

    serialized = json.dumps(payload, ensure_ascii=False).lower()
    records = JsonlAuditLog(audit_path).records()
    assert response.status == 400
    assert payload["error_code"] == "AUDIT_CURSOR_INVALID"
    assert "secret-audit-path" not in serialized
    assert records[-1].action == "runtime.audit.read"
    assert records[-1].outcome == "rejected"
    assert records[-1].error_code == "AUDIT_CURSOR_INVALID"


def test_ao27_ct_005_cursor_cannot_cross_filter_sets(tmp_path: Path):
    audit_log = _audit_log(tmp_path / "audit.jsonl")
    server = _start_server(InMemoryRepository(), audit_log=audit_log)
    try:
        _, first_payload = _json_request(
            server,
            "GET",
            "/v1/audit/runtime?action=credential.revoke&limit=2",
            headers=_auth_headers(),
        )
        cursor = first_payload["page_info"]["next_cursor"]
        response, payload = _json_request(
            server,
            "GET",
            f"/v1/audit/runtime?action=store.summary.read&limit=2&cursor={cursor}",
            headers=_auth_headers(),
        )
    finally:
        server.shutdown()

    assert response.status == 400
    assert payload["error_code"] == "AUDIT_CURSOR_INVALID"


def test_ao27_ct_006_cursor_response_does_not_expose_sensitive_markers(
    tmp_path: Path,
):
    audit_log = _audit_log(tmp_path / "secret-audit-path.jsonl")
    server = _start_server(InMemoryRepository(), audit_log=audit_log)
    try:
        response, payload = _json_request(
            server,
            "GET",
            "/v1/audit/runtime?action=credential.revoke&limit=2",
            headers=_auth_headers(),
        )
    finally:
        server.shutdown()

    serialized = json.dumps(payload, ensure_ascii=False).lower()
    assert response.status == 200
    assert payload["page_info"]["next_cursor"]
    for forbidden in (
        "raw_payload",
        "credential_secret",
        "credential material",
        "device_key",
        "token",
        "secret-audit-path",
    ):
        assert forbidden not in serialized


def test_ao27_ct_007_unsigned_cursor_payload_is_rejected(tmp_path: Path):
    audit_path = tmp_path / "audit.jsonl"
    audit_log = _audit_log(audit_path)
    forged_payload = {
        "filters": {"action": "credential.revoke"},
        "offset": 4,
        "v": 1,
    }
    forged_cursor = (
        base64.urlsafe_b64encode(
            json.dumps(forged_payload, separators=(",", ":")).encode("utf-8")
        )
        .decode("ascii")
        .rstrip("=")
    )
    server = _start_server(InMemoryRepository(), audit_log=audit_log)
    try:
        response, payload = _json_request(
            server,
            "GET",
            f"/v1/audit/runtime?action=credential.revoke&cursor={forged_cursor}",
            headers=_auth_headers(),
        )
    finally:
        server.shutdown()

    records = JsonlAuditLog(audit_path).records()
    assert response.status == 400
    assert payload["error_code"] == "AUDIT_CURSOR_INVALID"
    assert records[-1].action == "runtime.audit.read"
    assert records[-1].outcome == "rejected"


def test_ao27_ct_008_cursor_base64_validation_is_strict(tmp_path: Path):
    audit_path = tmp_path / "audit.jsonl"
    audit_log = _audit_log(audit_path)
    server = _start_server(InMemoryRepository(), audit_log=audit_log)
    try:
        _, first_payload = _json_request(
            server,
            "GET",
            "/v1/audit/runtime?action=credential.revoke&limit=2",
            headers=_auth_headers(),
        )
        cursor = first_payload["page_info"]["next_cursor"]
        response, payload = _json_request(
            server,
            "GET",
            f"/v1/audit/runtime?action=credential.revoke&cursor=!!{cursor}",
            headers=_auth_headers(),
        )
    finally:
        server.shutdown()

    assert response.status == 400
    assert payload["error_code"] == "AUDIT_CURSOR_INVALID"


def test_ao27_ct_009_broad_filter_cursor_terminates_despite_read_audits(
    tmp_path: Path,
):
    audit_log = _audit_log(tmp_path / "audit.jsonl")
    server = _start_server(InMemoryRepository(), audit_log=audit_log)
    seen_audit_ids = []
    path = "/v1/audit/runtime?limit=1"
    try:
        for _ in range(8):
            response, payload = _json_request(
                server,
                "GET",
                path,
                headers=_auth_headers(),
            )
            assert response.status == 200
            seen_audit_ids.extend(record["audit_id"] for record in payload["records"])
            cursor = payload["page_info"]["next_cursor"]
            if not payload["page_info"]["has_more"]:
                break
            path = f"/v1/audit/runtime?limit=1&cursor={cursor}"
        else:
            raise AssertionError("cursor chain did not terminate")
    finally:
        server.shutdown()

    assert seen_audit_ids == [
        "audit_runtime_1",
        "audit_runtime_2",
        "audit_runtime_3",
        "audit_runtime_4",
        "audit_runtime_5",
        "audit_store_1",
    ]


def test_ao27_ct_010_cursor_survives_handler_recreation_with_stable_secret(
    tmp_path: Path,
):
    audit_log = _audit_log(tmp_path / "audit.jsonl")
    first_server = _start_server(
        InMemoryRepository(),
        audit_log=audit_log,
        audit_cursor_secret="stable-runtime-audit-cursor-secret",
    )
    try:
        first_response, first_payload = _json_request(
            first_server,
            "GET",
            "/v1/audit/runtime?action=credential.revoke&limit=2",
            headers=_auth_headers(),
        )
    finally:
        first_server.shutdown()

    cursor = first_payload["page_info"]["next_cursor"]
    second_server = _start_server(
        InMemoryRepository(),
        audit_log=audit_log,
        audit_cursor_secret="stable-runtime-audit-cursor-secret",
    )
    try:
        second_response, second_payload = _json_request(
            second_server,
            "GET",
            f"/v1/audit/runtime?action=credential.revoke&limit=2&cursor={cursor}",
            headers=_auth_headers(),
        )
    finally:
        second_server.shutdown()

    assert first_response.status == 200
    assert second_response.status == 200
    assert [record["audit_id"] for record in second_payload["records"]] == [
        "audit_runtime_3",
        "audit_runtime_4",
    ]


def test_ao27_ct_011_missing_cursor_secret_fails_closed(tmp_path: Path):
    audit_path = tmp_path / "audit.jsonl"
    audit_log = _audit_log(audit_path)
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        create_http_handler(
            InMemoryRepository(),
            require_auth=True,
            audit_log=audit_log,
        ),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        response, payload = _json_request(
            server,
            "GET",
            "/v1/audit/runtime?action=credential.revoke&limit=2",
            headers=_auth_headers(),
        )
    finally:
        server.shutdown()

    records = JsonlAuditLog(audit_path).records()
    assert response.status == 503
    assert payload["error_code"] == "AUDIT_CURSOR_SECRET_UNCONFIGURED"
    assert payload["retryable"] is True
    assert records[-1].action == "runtime.audit.read"
    assert records[-1].outcome == "rejected"
    assert records[-1].error_code == "AUDIT_CURSOR_SECRET_UNCONFIGURED"
