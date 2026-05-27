from __future__ import annotations

import json
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from agentops.api.gateway import create_gateway_handler
from agentops.api.server import create_http_handler
from agentops.ops.access_readiness import (
    AccessReadinessConfig,
    run_access_readiness,
)
from agentops.storage.repository import InMemoryRepository


FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "contracts"
    / "cross-project"
    / "fixtures"
    / "ai_sdlc_executable_task_runtime_batch.v1.json"
)


def _start_server(repository: InMemoryRepository) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), create_http_handler(repository, require_auth=True)
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _start_gateway(
    upstream: ThreadingHTTPServer,
    *,
    token: str = "gateway-token",
) -> ThreadingHTTPServer:
    upstream_base = f"http://{upstream.server_address[0]}:{upstream.server_address[1]}"
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        create_gateway_handler(
            upstream_base=upstream_base,
            token=token,
            principal="producer.ai-sdlc.local",
            roles="agentops-ingestor",
            scopes="event.ingest",
        ),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def test_ao64_ct_001_access_readiness_passes_against_reference_stack():
    repository = InMemoryRepository()
    upstream = _start_server(repository)
    gateway = _start_gateway(upstream)
    try:
        result = run_access_readiness(
            AccessReadinessConfig(
                gateway_base=(
                    f"http://{gateway.server_address[0]}:{gateway.server_address[1]}"
                ),
                api_base=(
                    f"http://{upstream.server_address[0]}:{upstream.server_address[1]}"
                ),
                token="gateway-token",
                fixture_path=FIXTURE_PATH,
                bad_token="token_secret_bad",
            )
        )
    finally:
        gateway.shutdown()
        gateway.server_close()
        upstream.shutdown()
        upstream.server_close()

    assert result["schema_version"] == "agentops_access_readiness.v1"
    assert result["overall"] == "pass"
    assert repository.trace_span_count() == 2
    check_names = {check["name"] for check in result["checks"]}
    assert {
        "gateway.health",
        "api.health",
        "gateway.runtime_ingestion",
        "api.trace_readback",
        "api.evidence_readback",
        "gateway.bad_token_rejected",
        "api.raw_ingestion_rejected",
        "gateway.route_allowlist_closed",
    } <= check_names

    serialized = json.dumps(result, ensure_ascii=False)
    assert "gateway-token" not in serialized
    assert "token_secret_bad" not in serialized
    assert "evt_sdlc_task_prepared_001" not in serialized


def test_ao64_ct_002_access_readiness_fails_closed_when_token_missing():
    repository = InMemoryRepository()
    upstream = _start_server(repository)
    gateway = _start_gateway(upstream)
    try:
        result = run_access_readiness(
            AccessReadinessConfig(
                gateway_base=(
                    f"http://{gateway.server_address[0]}:{gateway.server_address[1]}"
                ),
                api_base=(
                    f"http://{upstream.server_address[0]}:{upstream.server_address[1]}"
                ),
                token="",
                fixture_path=FIXTURE_PATH,
            )
        )
    finally:
        gateway.shutdown()
        gateway.server_close()
        upstream.shutdown()
        upstream.server_close()

    assert result["overall"] == "fail"
    assert repository.trace_span_count() == 0
    assert result["checks"][-1]["name"] == "configuration.token"
    assert result["checks"][-1]["error_code"] == "AGENTOPS_INGESTION_TOKEN_REQUIRED"
