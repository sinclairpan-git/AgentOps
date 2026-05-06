from __future__ import annotations

import json
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from threading import Thread

import pytest

from agentops import __version__
from agentops.api.app import create_app
from agentops.api.console_snapshot import build_console_snapshot
from agentops.api.server import create_http_handler
from agentops.storage.repository import InMemoryRepository
from tests.contract.conftest import base_event


def _contains_key(value, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(child, key) for child in value.values())
    if isinstance(value, list):
        return any(_contains_key(child, key) for child in value)
    return False


def _json_response(server: ThreadingHTTPServer, path: str, *, origin: str | None = None):
    return _json_request(server, "GET", path, origin=origin)


def _json_request(
    server: ThreadingHTTPServer,
    method: str,
    path: str,
    *,
    origin: str | None = None,
    payload: dict | None = None,
):
    connection = HTTPConnection(server.server_address[0], server.server_address[1], timeout=5)
    try:
        headers = {"Origin": origin} if origin else {}
        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        body = response.read().decode("utf-8")
        response_payload = json.loads(body) if body else {}
        return response, response_payload
    finally:
        connection.close()


def _raw_request(server: ThreadingHTTPServer, method: str, path: str, body: bytes):
    connection = HTTPConnection(server.server_address[0], server.server_address[1], timeout=5)
    try:
        connection.request(method, path, body=body, headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        response_body = response.read().decode("utf-8")
        payload = json.loads(response_body) if response_body else {}
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
    assert health == {"service": "agentops-api", "status": "healthy", "version": __version__, "snapshot_provider": "ready"}
    assert snapshot_response.status == 200
    assert snapshot["schema_version"] == "agentops.console.snapshot.v1"
    assert not_found_response.status == 404
    assert not_found["error_code"] == "NOT_FOUND"


def test_ao4_ct_003_json_responses_include_cors_headers(http_server):
    response, _ = _json_response(http_server, "/v1/console/snapshot", origin="http://127.0.0.1:5174")

    assert response.getheader("Access-Control-Allow-Origin") == "http://127.0.0.1:5174"
    assert response.getheader("Access-Control-Allow-Methods") == "GET, POST, OPTIONS"
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


def test_ao5_ct_001_repository_snapshot_reflects_ingested_l5_events():
    repository = InMemoryRepository()
    for index, event_type in enumerate(
        [
            "stage_started",
            "stage_completed",
            "gate_result",
            "verification_result",
            "violation_scan_completed",
            "artifact_generated",
            "generation_snapshot",
            "l5_eligibility_input",
        ],
        start=1,
    ):
        repository.write_event(base_event(event_type, sequence_no=index))

    snapshot = build_console_snapshot(generated_at="2026-05-06T01:00:00Z", repository=repository)

    assert snapshot["source_detail"]["mode"] == "repository_backed"
    assert snapshot["consoleData"]["summary"]["metrics"][0]["value"] == 1
    assert snapshot["consoleData"]["runs"] == [
        {
            "run_id": "run_1",
            "id": "run_1",
            "agent": "agent.ai-sdlc",
            "skill": "refine",
            "risk_level": "低",
            "l5_state": "healthy",
            "policy_state": "allow",
            "evidence_state": "summary_only",
        }
    ]
    assert snapshot["consoleData"]["evidence"][0]["summary"] == "已接收 8 条签名事件，核心证据链完整。"
    assert not _contains_key(snapshot, "raw_payload")


def test_ao5_ct_002_events_post_updates_http_snapshot():
    repository = InMemoryRepository()
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_http_handler(repository))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        response, payload = _json_request(
            server,
            "POST",
            "/v1/events",
            payload={"events": [base_event("stage_started")]},
        )
        snapshot_response, snapshot = _json_response(server, "/v1/console/snapshot")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert response.status == 202
    assert payload["accepted"] == ["evt_stage_started"]
    assert snapshot_response.status == 200
    assert snapshot["source_detail"]["mode"] == "repository_backed"
    assert snapshot["consoleData"]["summary"]["metrics"][0]["value"] == 1
    assert snapshot["consoleData"]["runs"][0]["run_id"] == "run_1"


def test_ao5_ct_003_event_post_rejects_invalid_envelope_and_keeps_snapshot_safe():
    repository = InMemoryRepository()
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_http_handler(repository))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    invalid_event = base_event("stage_started")
    invalid_event.pop("signature")
    try:
        response, payload = _json_request(server, "POST", "/v1/events", payload={"events": [invalid_event]})
        snapshot_response, snapshot = _json_response(server, "/v1/console/snapshot")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert response.status == 400
    assert payload["accepted"] == []
    assert payload["rejected"][0]["error_code"] == "EVENT_SIGNATURE_REQUIRED"
    assert payload["rejected"][0]["retryable"] is False
    assert payload["rejected"][0]["human_action_required"] is True
    assert snapshot_response.status == 200
    assert snapshot["consoleData"]["summary"]["metrics"][0]["status"] == "empty"
    assert snapshot["consoleData"]["runs"] == []
    assert not _contains_key(snapshot, "raw_payload")


def test_ao5_ct_004_event_post_deduplicates_idempotency_keys():
    repository = InMemoryRepository()
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_http_handler(repository))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    replay = base_event("stage_started", event_id="evt_stage_started_replay")
    try:
        first_response, first_payload = _json_request(server, "POST", "/v1/events", payload={"events": [base_event("stage_started")]})
        second_response, second_payload = _json_request(server, "POST", "/v1/events", payload={"events": [replay]})
        _, snapshot = _json_response(server, "/v1/console/snapshot")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert first_response.status == 202
    assert first_payload["accepted"] == ["evt_stage_started"]
    assert second_response.status == 202
    assert second_payload["deduplicated"] == ["evt_stage_started_replay"]
    assert snapshot["consoleData"]["summary"]["metrics"][0]["value"] == 1
    assert len(snapshot["consoleData"]["runs"]) == 1


def test_ao5_ct_005_event_post_mixed_batch_only_snapshots_accepted_events():
    repository = InMemoryRepository()
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_http_handler(repository))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    invalid_event = base_event("stage_completed")
    invalid_event["payload"].pop("duration_ms")
    try:
        response, payload = _json_request(
            server,
            "POST",
            "/v1/events",
            payload={"events": [base_event("stage_started"), invalid_event]},
        )
        _, snapshot = _json_response(server, "/v1/console/snapshot")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert response.status == 202
    assert payload["accepted"] == ["evt_stage_started"]
    assert payload["rejected"][0]["error_code"] == "EVENT_PAYLOAD_INVALID"
    assert snapshot["consoleData"]["summary"]["metrics"][0]["value"] == 1
    assert snapshot["consoleData"]["evidence"][0]["summary"] == "已接收 1 条事件，但仍缺少：artifact_generated、gate_result、generation_snapshot、l5_eligibility_input、stage_completed、verification_result、violation_scan_completed。"


def test_ao5_ct_006_event_post_request_errors_are_json_and_cors_is_enforced():
    repository = InMemoryRepository()
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_http_handler(repository))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        invalid_json_response, invalid_json = _raw_request(server, "POST", "/v1/events", b"{")
        missing_events_response, missing_events = _json_request(server, "POST", "/v1/events", payload={})
        allowed_response, _ = _json_request(
            server,
            "POST",
            "/v1/events",
            origin="http://127.0.0.1:5173",
            payload={"events": [base_event("stage_started")]},
        )
        forbidden_response, forbidden = _json_request(
            server,
            "POST",
            "/v1/events",
            origin="https://example.com",
            payload={"events": [base_event("stage_completed")]},
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert invalid_json_response.status == 400
    assert invalid_json["error_code"] == "REQUEST_JSON_INVALID"
    assert missing_events_response.status == 400
    assert missing_events["error_code"] == "EVENTS_REQUIRED"
    assert allowed_response.status == 202
    assert allowed_response.getheader("Access-Control-Allow-Origin") == "http://127.0.0.1:5173"
    assert forbidden_response.status == 403
    assert forbidden["error_code"] == "ORIGIN_FORBIDDEN"


def test_ao5_ct_007_repository_backed_adapter_truth_stays_unverified():
    repository = InMemoryRepository()
    repository.write_event(base_event("stage_started"))

    snapshot = build_console_snapshot(repository=repository)

    assert snapshot["consoleData"]["summary"]["adapter"]["status"] == "materialized"
    assert all(sdlc_run["verified_loaded"] == "unverified" for sdlc_run in snapshot["consoleData"]["sdlcRuns"])


def test_ao5_ct_008_api_assembly_truth_tracks_http_ingestion_route():
    app = create_app()

    assert app["ingestion"] == "POST /v1/events"
    assert app["console_snapshot"] == "/v1/console/snapshot"
