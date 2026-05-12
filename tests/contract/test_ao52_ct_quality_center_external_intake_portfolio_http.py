from __future__ import annotations

import json
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from urllib.parse import urlencode

from agentops.api.app import create_app
from agentops.api.operations import ingest_quality_scorer_external_execution
from agentops.core.runtime_contracts import get_contract
from agentops.storage.audit import JsonlAuditLog
from agentops.storage.repository import InMemoryRepository
from tests.contract.test_ao47_ct_quality_scorer_external_intake_readback import (
    _assert_no_raw_leaks,
    _candidate_scorer,
    _seed_eval_case,
    _start_server,
)
from tests.contract.test_ao48_ct_quality_scorer_external_intake_index import (
    _seed_eval_case_for,
)


PORTFOLIO_ROUTE = "/v1/quality/center/external-intake/portfolio"


def test_ao52_ct_001_contract_registry_and_app_route_declared():
    contract = get_contract("quality_center_external_intake_portfolio_http.v1")
    routes = create_app()

    assert contract.domain_owner == "AgentOps"
    assert contract.enum_fields["method"] == frozenset({"GET"})
    assert "401" in contract.enum_fields["status_code"]
    assert {
        "route",
        "method",
        "window_limit",
        "requested_scope_count",
        "returned_scope_count",
        "portfolio",
        "summary",
        "audit_id",
    }.issubset(contract.required_fields)
    assert {
        "QUALITY_CENTER_INTAKE_PORTFOLIO_SCOPE_REQUIRED",
        "QUALITY_CENTER_INTAKE_PORTFOLIO_SCOPE_INVALID",
        "QUALITY_CENTER_INTAKE_PORTFOLIO_LIMIT_INVALID",
        "AGENTOPS_SCOPE_DENIED",
    }.issubset(contract.error_codes)
    assert "AO52-CT-001" in contract.contract_tests
    assert (
        routes["quality_center_external_intake_portfolio"]
        == "GET /v1/quality/center/external-intake/portfolio"
    )


def test_ao52_ct_002_http_portfolio_returns_multi_scope_summary_without_execution():
    repository = InMemoryRepository()
    eval_case_id = _seed_eval_case(repository)
    receipt = ingest_quality_scorer_external_execution(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        idempotency_key="quality-center-portfolio-http:accepted",
        signature="sig:quality-center-portfolio-http",
        scorer=_candidate_scorer(),
        external_result={
            "source_eval_cases": [eval_case_id],
            "case_results": [
                {
                    "eval_case_id": eval_case_id,
                    "outcome": "passed",
                    "score": 0.94,
                }
            ],
        },
    )
    before_count = len(
        repository.quality_scorer_execution_records("agent.ai-sdlc", "1.0.0")
    )
    server = _start_server(repository)
    try:
        response, payload = _json_get_multi(
            server,
            PORTFOLIO_ROUTE,
            {
                "scope": ["agent.ai-sdlc@1.0.0", "agent.store@1.0.0"],
                "required_scope": ["agent.store@1.0.0"],
                "limit": "5",
            },
        )
    finally:
        server.shutdown()

    after_count = len(
        repository.quality_scorer_execution_records("agent.ai-sdlc", "1.0.0")
    )
    portfolio = payload["portfolio"]
    assert response.status == 200
    assert payload["schema_version"] == (
        "quality_center_external_intake_portfolio_http.v1"
    )
    assert payload["route"] == PORTFOLIO_ROUTE
    assert payload["method"] == "GET"
    assert payload["window_limit"] == 5
    assert payload["requested_scope_count"] == 2
    assert payload["returned_scope_count"] == 2
    assert portfolio["schema_version"] == "quality_center_external_intake_portfolio.v1"
    assert portfolio["portfolio_state"] == "incomplete"
    assert portfolio["state_counts"] == {
        "receiving": 1,
        "no_receipts": 1,
        "needs_review": 0,
    }
    assert portfolio["receipt_count"] == 1
    assert portfolio["latest_receipts"][0]["latest_intake_id"] == receipt["intake_id"]
    assert portfolio["required_missing_scope_count"] == 1
    assert portfolio["required_missing_scopes"][0]["agent_id"] == "agent.store"
    assert portfolio["summary"]["automatic_scorer_invocation"] is False
    assert payload["summary"]["request_body_read"] is False
    assert payload["summary"]["store_write_performed"] is False
    assert after_count == before_count
    _assert_no_raw_leaks(payload)


def test_ao52_ct_003_http_portfolio_requires_scope():
    repository = InMemoryRepository()
    server = _start_server(repository)
    try:
        response, payload = _json_get_multi(
            server,
            PORTFOLIO_ROUTE,
            {"limit": "5"},
        )
    finally:
        server.shutdown()

    assert response.status == 400
    assert payload["error_code"] == "QUALITY_CENTER_INTAKE_PORTFOLIO_SCOPE_REQUIRED"
    assert payload["denied_scope"] == "quality_center_external_intake_portfolio.scope"


def test_ao52_ct_004_http_portfolio_rejects_invalid_scope_and_limit(tmp_path):
    repository = InMemoryRepository()
    audit_log = JsonlAuditLog(tmp_path / "audit.jsonl")
    server = _start_server(repository, audit_log=audit_log)
    try:
        invalid_scope_response, invalid_scope = _json_get_multi(
            server,
            PORTFOLIO_ROUTE,
            {"scope": ["agent.ai-sdlc"], "limit": "5"},
        )
        invalid_limit_response, invalid_limit = _json_get_multi(
            server,
            PORTFOLIO_ROUTE,
            {
                "scope": ["agent.ai-sdlc@1.0.0"],
                "limit": "token_secret:https://example.invalid/raw",
            },
        )
    finally:
        server.shutdown()

    records = [record.to_dict() for record in audit_log.records()]
    serialized_audit = json.dumps(records, ensure_ascii=False).lower()
    assert invalid_scope_response.status == 400
    assert (
        invalid_scope["error_code"] == "QUALITY_CENTER_INTAKE_PORTFOLIO_SCOPE_INVALID"
    )
    assert invalid_limit_response.status == 400
    assert (
        invalid_limit["error_code"] == "QUALITY_CENTER_INTAKE_PORTFOLIO_LIMIT_INVALID"
    )
    assert records[-1]["action"] == "quality.center.external_intake.portfolio"
    assert records[-1]["outcome"] == "rejected"
    assert "token_secret" not in serialized_audit
    assert "https://example.invalid" not in serialized_audit


def test_ao52_ct_005_http_portfolio_requires_production_read_scope(tmp_path):
    repository = InMemoryRepository()
    audit_log = JsonlAuditLog(tmp_path / "audit.jsonl")
    server = _start_server(repository, require_auth=True, audit_log=audit_log)
    try:
        response, payload = _json_get_multi(
            server,
            PORTFOLIO_ROUTE,
            {"scope": ["agent.ai-sdlc@1.0.0"]},
            headers={
                "X-AgentOps-Principal": "quality-operator",
                "X-AgentOps-Scopes": "quality.scorer.intake.write",
                "X-AgentOps-Request-Id": "req_ao52_scope",
                "X-AgentOps-Audit-Id": "audit_ao52_scope",
            },
        )
    finally:
        server.shutdown()

    records = [record.to_dict() for record in audit_log.records()]
    assert response.status == 403
    assert payload["error_code"] == "AGENTOPS_SCOPE_DENIED"
    assert payload["denied_scope"] == "quality.scorer.intake.read"
    assert records[-1]["action"] == "quality.center.external_intake.portfolio"
    assert records[-1]["outcome"] == "denied"
    assert records[-1]["denied_scope"] == "quality.scorer.intake.read"


def test_ao52_ct_006_http_portfolio_allows_uri_identity_without_raw_echo():
    repository = InMemoryRepository()
    eval_case_id = _seed_eval_case_for(
        repository,
        run_id="run_quality_center_portfolio_http_uri",
        agent_id="https://example.invalid/agent-quality-center-portfolio-http",
        version="1.0.0",
    )
    receipt = ingest_quality_scorer_external_execution(
        repository,
        "https://example.invalid/agent-quality-center-portfolio-http",
        "1.0.0",
        idempotency_key="quality-center-portfolio-http:uri-agent",
        signature="sig:quality-center-portfolio-http-uri",
        scorer=_candidate_scorer(),
        external_result={
            "source_eval_cases": [eval_case_id],
            "case_results": [
                {
                    "eval_case_id": eval_case_id,
                    "outcome": "passed",
                    "score": 0.94,
                }
            ],
        },
    )
    server = _start_server(repository)
    try:
        response, payload = _json_get_multi(
            server,
            PORTFOLIO_ROUTE,
            {
                "scope": [
                    "https://example.invalid/agent-quality-center-portfolio-http@1.0.0"
                ]
            },
        )
    finally:
        server.shutdown()

    portfolio = payload["portfolio"]
    assert response.status == 200
    assert portfolio["scope_count"] == 1
    assert portfolio["latest_receipts"][0]["agent_id"] == "[redacted]"
    assert portfolio["latest_receipts"][0]["latest_intake_id"] == receipt["intake_id"]
    assert portfolio["latest_receipts"][0]["agent_identity"][
        "agent_id_hash"
    ].startswith("sha256:")
    _assert_no_raw_leaks(payload)


def test_ao52_ct_007_http_portfolio_allows_production_read_scope(tmp_path):
    repository = InMemoryRepository()
    audit_log = JsonlAuditLog(tmp_path / "audit.jsonl")
    server = _start_server(repository, require_auth=True, audit_log=audit_log)
    try:
        response, payload = _json_get_multi(
            server,
            PORTFOLIO_ROUTE,
            {"scope": ["agent.ai-sdlc@1.0.0"]},
            headers={
                "X-AgentOps-Principal": "quality-operator",
                "X-AgentOps-Scopes": "quality.scorer.intake.read",
                "X-AgentOps-Request-Id": "req_ao52_read",
                "X-AgentOps-Audit-Id": "audit_ao52_read",
            },
        )
    finally:
        server.shutdown()

    records = [record.to_dict() for record in audit_log.records()]
    assert response.status == 200
    assert payload["portfolio"]["portfolio_state"] == "no_receipts"
    assert records[-1]["action"] == "quality.center.external_intake.portfolio"
    assert records[-1]["outcome"] == "accepted"


def _json_get_multi(
    server: ThreadingHTTPServer,
    path: str,
    query: dict[str, str | list[str]],
    *,
    headers: dict[str, str] | None = None,
):
    connection = HTTPConnection(
        server.server_address[0], server.server_address[1], timeout=5
    )
    try:
        request_headers = {
            "Origin": "http://127.0.0.1:5173",
            **(headers or {}),
        }
        connection.request(
            "GET",
            f"{path}?{urlencode(query, doseq=True)}",
            headers=request_headers,
        )
        response = connection.getresponse()
        body = response.read().decode("utf-8")
        return response, json.loads(body) if body else {}
    finally:
        connection.close()
