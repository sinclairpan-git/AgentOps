from __future__ import annotations

import json
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from threading import Thread

import pytest

from agentops.api.console_snapshot import build_console_snapshot
from agentops.api.server import create_http_handler


def _contains_key(value, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(child, key) for child in value.values())
    if isinstance(value, list):
        return any(_contains_key(child, key) for child in value)
    return False


def _json_response(server: ThreadingHTTPServer, path: str, *, origin: str | None = None):
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


@pytest.fixture
def http_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_http_handler())
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_ao4_ct_001_console_snapshot_schema():
    snapshot = build_console_snapshot(generated_at="2026-05-06T00:00:00Z")

    assert snapshot["schema_version"] == "agentops.console.snapshot.v1"
    assert snapshot["generated_at"] == "2026-05-06T00:00:00Z"
    assert snapshot["source"] == "api_snapshot"
    assert len(snapshot["routes"]) == 9
    assert set(snapshot["consoleData"]) >= {
        "summary",
        "runs",
        "evidence",
        "approvals",
        "policies",
        "quality",
        "risks",
        "connectors",
        "sdlcRuns",
    }


def test_ao4_ct_002_health_snapshot_and_not_found_are_json(http_server):
    health_response, health = _json_response(http_server, "/v1/health")
    snapshot_response, snapshot = _json_response(http_server, "/v1/console/snapshot")
    not_found_response, not_found = _json_response(http_server, "/missing")

    assert health_response.status == 200
    assert health == {"service": "agentops-api", "status": "healthy", "version": "0.1.0", "snapshot_provider": "ready"}
    assert snapshot_response.status == 200
    assert snapshot["schema_version"] == "agentops.console.snapshot.v1"
    assert not_found_response.status == 404
    assert not_found["error_code"] == "NOT_FOUND"


def test_ao4_ct_003_json_responses_include_cors_headers(http_server):
    response, _ = _json_response(http_server, "/v1/console/snapshot", origin="http://127.0.0.1:5174")

    assert response.getheader("Access-Control-Allow-Origin") == "http://127.0.0.1:5174"
    assert response.getheader("Access-Control-Allow-Methods") == "GET, OPTIONS"
    assert response.getheader("Access-Control-Allow-Headers") == "Content-Type"
    assert response.getheader("Access-Control-Allow-Origin") != "*"


def test_ao4_ct_003_disallowed_origin_is_forbidden(http_server):
    response, payload = _json_response(http_server, "/v1/console/snapshot", origin="https://example.com")

    assert response.status == 403
    assert payload["error_code"] == "ORIGIN_FORBIDDEN"


def test_ao4_ct_004_snapshot_never_contains_raw_payload():
    snapshot = build_console_snapshot()

    assert not _contains_key(snapshot, "raw_payload")


def test_ao4_ct_005_adapter_truth_keeps_pending_proof_unverified():
    snapshot = build_console_snapshot()

    for sdlc_run in snapshot["consoleData"]["sdlcRuns"]:
        proof_text = f"{sdlc_run.get('proof_source', '')} {sdlc_run.get('captured_at', '')}"
        pending_proof = any(marker in proof_text for marker in ("AGENTS.md", "CLI 预演", "待采集", "待接入"))
        if pending_proof:
            assert sdlc_run["verified_loaded"] == "unverified"
