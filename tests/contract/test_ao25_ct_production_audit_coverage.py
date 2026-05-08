from __future__ import annotations

import json
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from agentops.api.agent_store import sync_agent_store_metadata
from agentops.api.server import create_http_handler
from agentops.storage.audit import JsonlAuditLog
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
        "X-AgentOps-Principal": "auditor.ops@example.com",
        "X-AgentOps-Request-Id": "req_ao25",
        "X-AgentOps-Audit-Id": "audit_ao25",
    }
    if roles:
        headers["X-AgentOps-Roles"] = roles
    if scopes:
        headers["X-AgentOps-Scopes"] = scopes
    return headers


def _credential_repository() -> InMemoryRepository:
    repository = InMemoryRepository()
    repository.add_bootstrap_session(
        {
            "bootstrap_id": "boot-ao25",
            "status": "credential_issued",
            "bootstrap_status": "credential_issued",
            "installation_id": "inst_ao25",
            "device_id": "dev_ao25",
            "expires_at": "2099-01-01T00:00:00+00:00",
        }
    )
    repository.store_credentials(
        "boot-ao25",
        {
            "credential_id": "cred-ao25-secret-should-not-log",
            "token_id": "token-ao25-secret-should-not-log",
            "device_key_id": "device-key-ao25-secret-should-not-log",
            "status": "active",
            "bootstrap_status": "credential_issued",
            "installation_id": "inst_ao25",
            "device_id": "dev_ao25",
            "expires_at": "2099-01-01T00:00:00+00:00",
            "next_action": "send_signature_test_event",
        },
    )
    return repository


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
                event_id=f"evt_ao25_{event_type}",
                idempotency_key=f"ao25:{event_type}:run_1",
                sequence_no=index,
            )
        )


def _reissue_payload() -> dict:
    return {
        "schema_version": "agentops_credential_reissue.v1",
        "new_bootstrap_id": "boot-ao25-r1",
        "reissue_id": "reissue_ao25",
        "requested_by": "security@example.com",
        "reason": "lost-device",
        "credential_handoff": {
            "bootstrap_id": "boot-ao25-r1",
            "credential_secret": "secret credential material",
            "installation_assertion": {
                "expires_at": "2099-01-01T00:00:00+00:00",
            },
        },
    }


def test_ao25_ct_001_console_snapshot_success_is_audited(tmp_path: Path):
    audit_path = tmp_path / "audit.jsonl"
    audit_log = JsonlAuditLog(audit_path)
    repository = InMemoryRepository()
    server = _start_server(repository, audit_log)
    try:
        response, payload = _json_request(
            server,
            "GET",
            "/v1/console/snapshot",
            headers=_auth_headers(roles="agentops-viewer"),
        )
    finally:
        server.shutdown()

    records = JsonlAuditLog(audit_path).records()
    assert response.status == 200
    assert payload["schema_version"] == "agentops.console.snapshot.v1"
    assert len(records) == 1
    assert records[0].action == "console.snapshot.read"
    assert records[0].outcome == "accepted"
    assert records[0].principal == "auditor.ops@example.com"


def test_ao25_ct_002_store_summary_success_and_query_failure_are_audited(
    tmp_path: Path,
):
    audit_path = tmp_path / "audit.jsonl"
    audit_log = JsonlAuditLog(audit_path)
    repository = InMemoryRepository()
    _write_l5_run(repository)
    server = _start_server(repository, audit_log)
    try:
        accepted_response, summary = _json_request(
            server,
            "GET",
            "/v1/store-summary/agent.ai-sdlc?version=1.0.0&run_id=run_1",
            headers=_auth_headers(roles="agent-store-consumer"),
        )
        rejected_response, rejected = _json_request(
            server,
            "GET",
            "/v1/store-summary/agent.ai-sdlc",
            headers=_auth_headers(roles="agent-store-consumer"),
        )
    finally:
        server.shutdown()

    records = JsonlAuditLog(audit_path).records()
    assert accepted_response.status == 200
    assert summary["schema_version"] == "agentops.agent_store.echo.v1"
    assert rejected_response.status == 400
    assert rejected["error_code"] == "STORE_SUMMARY_QUERY_REQUIRED"
    assert [(record.action, record.outcome, record.error_code) for record in records] == [
        ("store.summary.read", "accepted", ""),
        (
            "store.summary.read",
            "rejected",
            "STORE_SUMMARY_QUERY_REQUIRED",
        ),
    ]


def test_ao25_ct_003_credential_status_success_and_not_found_are_audited(
    tmp_path: Path,
):
    audit_path = tmp_path / "audit.jsonl"
    audit_log = JsonlAuditLog(audit_path)
    repository = _credential_repository()
    server = _start_server(repository, audit_log)
    try:
        accepted_response, accepted = _json_request(
            server,
            "GET",
            "/v1/bootstrap/credentials/boot-ao25",
            headers=_auth_headers(roles="agentops-viewer"),
        )
        rejected_response, rejected = _json_request(
            server,
            "GET",
            "/v1/bootstrap/credentials/boot-missing",
            headers=_auth_headers(roles="agentops-viewer"),
        )
    finally:
        server.shutdown()

    records = JsonlAuditLog(audit_path).records()
    assert accepted_response.status == 200
    assert accepted["bootstrap_id"] == "boot-ao25"
    assert rejected_response.status == 404
    assert rejected["error_code"] == "CREDENTIAL_STATUS_NOT_FOUND"
    assert [(record.action, record.outcome, record.error_code) for record in records] == [
        ("credential.read", "accepted", ""),
        ("credential.read", "rejected", "CREDENTIAL_STATUS_NOT_FOUND"),
    ]


def test_ao25_ct_004_credential_revoke_success_is_audited(tmp_path: Path):
    audit_path = tmp_path / "audit.jsonl"
    audit_log = JsonlAuditLog(audit_path)
    repository = _credential_repository()
    server = _start_server(repository, audit_log)
    try:
        response, payload = _json_request(
            server,
            "POST",
            "/v1/bootstrap/credentials/boot-ao25/revoke",
            headers=_auth_headers(roles="agentops-operator"),
            payload={
                "schema_version": "agentops_credential_revocation.v1",
                "revocation_id": "rev_ao25",
                "revoked_by": "security@example.com",
                "reason": "lost-device",
                "scope": "credential",
                "credential_secret": "secret credential material",
            },
        )
    finally:
        server.shutdown()

    records = JsonlAuditLog(audit_path).records()
    assert response.status == 200
    assert payload["credential_status"] == "revoked"
    assert records[0].action == "credential.revoke"
    assert records[0].outcome == "accepted"
    assert records[0].resource == "/v1/bootstrap/credentials/boot-ao25/revoke"


def test_ao25_ct_005_credential_reissue_not_found_is_audited(tmp_path: Path):
    audit_path = tmp_path / "audit.jsonl"
    audit_log = JsonlAuditLog(audit_path)
    repository = InMemoryRepository()
    server = _start_server(repository, audit_log)
    try:
        response, payload = _json_request(
            server,
            "POST",
            "/v1/bootstrap/credentials/boot-missing/reissue",
            headers=_auth_headers(roles="agentops-operator"),
            payload=_reissue_payload(),
        )
    finally:
        server.shutdown()

    records = JsonlAuditLog(audit_path).records()
    assert response.status == 404
    assert payload["error_code"] == "CREDENTIAL_REISSUE_NOT_FOUND"
    assert records[0].action == "credential.reissue"
    assert records[0].outcome == "rejected"
    assert records[0].error_code == "CREDENTIAL_REISSUE_NOT_FOUND"


def test_ao25_ct_006_extended_route_audit_never_records_sensitive_material(
    tmp_path: Path,
):
    audit_path = tmp_path / "audit.jsonl"
    audit_log = JsonlAuditLog(audit_path)
    repository = _credential_repository()
    server = _start_server(repository, audit_log)
    try:
        _json_request(
            server,
            "GET",
            "/v1/bootstrap/credentials/boot-ao25",
            headers=_auth_headers(roles="agentops-viewer"),
        )
        _json_request(
            server,
            "POST",
            "/v1/bootstrap/credentials/boot-ao25/revoke",
            headers=_auth_headers(roles="agentops-operator"),
            payload={
                "schema_version": "agentops_credential_revocation.v1",
                "revocation_id": "rev_ao25",
                "revoked_by": "security@example.com",
                "reason": "lost-device",
                "scope": "credential",
                "raw_payload": "secret raw payload",
                "token": "secret token value",
                "device_key": "secret device key",
                "credential_secret": "secret credential material",
            },
        )
    finally:
        server.shutdown()

    serialized = audit_path.read_text(encoding="utf-8").lower()
    for forbidden in (
        "raw_payload",
        "secret raw payload",
        "token-ao25-secret-should-not-log",
        "secret token value",
        "device-key-ao25-secret-should-not-log",
        "secret device key",
        "credential_secret",
        "secret credential material",
    ):
        assert forbidden not in serialized
