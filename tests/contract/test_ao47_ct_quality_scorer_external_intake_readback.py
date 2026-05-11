from __future__ import annotations

import json
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.parse import urlencode

from agentops.api.app import create_app
from agentops.api.operations import (
    create_eval_case,
    ingest_quality_scorer_external_execution,
)
from agentops.api.server import create_http_handler
from agentops.core.runtime_contracts import get_contract
from agentops.storage.audit import JsonlAuditLog
from agentops.storage.repository import InMemoryRepository
from tests.contract.test_ao32_ct_evidence_health_summary_loop import (
    write_full_trace,
    write_runtime_run,
)


def test_ao47_ct_001_contract_registry_and_app_route_declared():
    contract = get_contract("quality_scorer_external_intake_readback.v1")
    routes = create_app()

    assert contract.domain_owner == "AgentOps"
    assert contract.enum_fields["method"] == frozenset({"GET"})
    assert {
        "route",
        "method",
        "agent_id",
        "version",
        "idempotency_key",
        "receipt",
        "audit_id",
    }.issubset(contract.required_fields)
    assert {
        "QUALITY_SCORER_INTAKE_RECEIPT_QUERY_REQUIRED",
        "QUALITY_SCORER_INTAKE_RECEIPT_NOT_FOUND",
        "AGENTOPS_SCOPE_DENIED",
    }.issubset(contract.error_codes)
    assert "AO47-CT-001" in contract.contract_tests
    assert (
        routes["quality_scorer_external_intake_readback"]
        == "GET /v1/quality/scorers/external-intake"
    )


def test_ao47_ct_002_http_readback_returns_existing_receipt_without_new_execution():
    repository = InMemoryRepository()
    eval_case_id = _seed_eval_case(repository)
    server = _start_server(repository)
    try:
        post_response, posted = _json_post(
            server,
            "/v1/quality/scorers/external-intake",
            _valid_post_payload(eval_case_id, "scorer-external-readback:run-1"),
        )
        before_count = len(
            repository.quality_scorer_execution_records("agent.ai-sdlc", "1.0.0")
        )
        get_response, receipt = _json_get(
            server,
            "/v1/quality/scorers/external-intake",
            {
                "agent_id": "agent.ai-sdlc",
                "version": "1.0.0",
                "idempotency_key": "scorer-external-readback:run-1",
            },
        )
    finally:
        server.shutdown()

    after_count = len(
        repository.quality_scorer_execution_records("agent.ai-sdlc", "1.0.0")
    )
    assert post_response.status == 202
    assert get_response.status == 200
    assert receipt["schema_version"] == "quality_scorer_external_intake.v1"
    assert receipt["intake_id"] == posted["intake_id"]
    assert receipt["accepted_execution_id"] == posted["accepted_execution_id"]
    assert receipt["summary"]["summary_only_intake"] is True
    assert receipt["summary"]["automatic_rollout_enabled"] is False
    assert before_count == 1
    assert after_count == before_count
    _assert_no_raw_leaks(receipt)


def test_ao47_ct_003_http_readback_requires_full_query_scope():
    repository = InMemoryRepository()
    server = _start_server(repository)
    try:
        response, payload = _json_get(
            server,
            "/v1/quality/scorers/external-intake",
            {
                "agent_id": "agent.ai-sdlc",
                "idempotency_key": "scorer-external-readback:missing-version",
            },
        )
    finally:
        server.shutdown()

    assert response.status == 400
    assert payload["error_code"] == "QUALITY_SCORER_INTAKE_RECEIPT_QUERY_REQUIRED"
    assert payload["denied_scope"] == "quality_scorer_external_intake_readback.query"
    assert repository.quality_scorer_execution_records("agent.ai-sdlc", "1.0.0") == ()


def test_ao47_ct_004_http_readback_not_found_audits_without_query_payload(tmp_path):
    repository = InMemoryRepository()
    audit_log = JsonlAuditLog(tmp_path / "audit.jsonl")
    server = _start_server(repository, audit_log=audit_log)
    try:
        response, payload = _json_get(
            server,
            "/v1/quality/scorers/external-intake",
            {
                "agent_id": "agent.ai-sdlc",
                "version": "1.0.0",
                "idempotency_key": "token_secret:https://example.invalid/raw",
            },
        )
    finally:
        server.shutdown()

    records = [record.to_dict() for record in audit_log.records()]
    serialized_audit = json.dumps(records, ensure_ascii=False).lower()
    assert response.status == 404
    assert payload["error_code"] == "QUALITY_SCORER_INTAKE_RECEIPT_NOT_FOUND"
    assert records[-1]["action"] == "quality.scorer.external_intake.read"
    assert records[-1]["outcome"] == "rejected"
    assert records[-1]["error_code"] == "QUALITY_SCORER_INTAKE_RECEIPT_NOT_FOUND"
    assert "token_secret" not in serialized_audit
    assert "https://example.invalid" not in serialized_audit
    assert repository.quality_scorer_execution_records("agent.ai-sdlc", "1.0.0") == ()


def test_ao47_ct_005_http_readback_requires_production_scope(tmp_path):
    repository = InMemoryRepository()
    eval_case_id = _seed_eval_case(repository)
    receipt = ingest_quality_scorer_external_execution(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        idempotency_key="scorer-external-readback:scope",
        signature="sig:external-scorer-readback",
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
    audit_log = JsonlAuditLog(tmp_path / "audit.jsonl")
    server = _start_server(repository, require_auth=True, audit_log=audit_log)
    try:
        response, payload = _json_get(
            server,
            "/v1/quality/scorers/external-intake",
            {
                "agent_id": "agent.ai-sdlc",
                "version": "1.0.0",
                "idempotency_key": receipt["idempotency_key"],
            },
            headers={
                "X-AgentOps-Principal": "external-scorer",
                "X-AgentOps-Scopes": "quality.scorer.intake.write",
                "X-AgentOps-Request-Id": "req_ao47_scope",
                "X-AgentOps-Audit-Id": "audit_ao47_scope",
            },
        )
    finally:
        server.shutdown()

    records = [record.to_dict() for record in audit_log.records()]
    assert response.status == 403
    assert payload["error_code"] == "AGENTOPS_SCOPE_DENIED"
    assert payload["denied_scope"] == "quality.scorer.intake.read"
    assert records[-1]["outcome"] == "denied"
    assert records[-1]["denied_scope"] == "quality.scorer.intake.read"
    assert (
        len(repository.quality_scorer_execution_records("agent.ai-sdlc", "1.0.0")) == 1
    )


def _json_get(
    server: ThreadingHTTPServer,
    path: str,
    query: dict[str, str],
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
            f"{path}?{urlencode(query)}",
            headers=request_headers,
        )
        response = connection.getresponse()
        body = response.read().decode("utf-8")
        return response, json.loads(body) if body else {}
    finally:
        connection.close()


def _json_post(
    server: ThreadingHTTPServer,
    path: str,
    payload: dict,
):
    connection = HTTPConnection(
        server.server_address[0], server.server_address[1], timeout=5
    )
    try:
        connection.request(
            "POST",
            path,
            body=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Origin": "http://127.0.0.1:5173",
            },
        )
        response = connection.getresponse()
        body = response.read().decode("utf-8")
        return response, json.loads(body) if body else {}
    finally:
        connection.close()


def _start_server(
    repository: InMemoryRepository,
    *,
    require_auth: bool = False,
    audit_log: JsonlAuditLog | None = None,
) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        create_http_handler(
            repository,
            require_auth=require_auth,
            audit_log=audit_log,
        ),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _seed_eval_case(
    repository: InMemoryRepository,
    run_id: str = "run_failed_readback",
) -> str:
    write_runtime_run(
        repository,
        run_id=run_id,
        agent_id="agent.ai-sdlc",
        version="1.0.0",
        status="failed",
    )
    write_full_trace(repository, run_id=run_id)
    eval_case = create_eval_case(
        repository,
        run_id,
        owner_team="Quality",
        expected_behavior="Classify failure from redacted summary.",
    )
    return str(eval_case["eval_case_id"])


def _candidate_scorer() -> dict[str, str]:
    return {
        "scorer_id": "quality_summary_stage5_candidate",
        "scorer_version": "1.1.0",
        "score_template_id": "quality_summary_stage5_candidate",
    }


def _valid_post_payload(eval_case_id: str, idempotency_key: str) -> dict:
    return {
        "agent_id": "agent.ai-sdlc",
        "version": "1.0.0",
        "idempotency_key": idempotency_key,
        "signature": "sig:external-scorer-readback",
        "scorer": _candidate_scorer(),
        "external_result": {
            "source_eval_cases": [eval_case_id],
            "case_results": [
                {
                    "eval_case_id": eval_case_id,
                    "outcome": "passed",
                    "score": 0.94,
                }
            ],
        },
    }


def _assert_no_raw_leaks(payload: dict) -> None:
    forbidden_keys = {
        "raw_payload",
        "prompt",
        "raw_prompt",
        "diff",
        "raw_diff",
        "terminal",
        "terminal_output",
        "token_secret",
        "credential_secret",
        "device_key",
        "download_url",
        "raw_url",
        "pr_url",
    }
    _assert_no_forbidden_keys(payload, forbidden_keys)
    serialized = json.dumps(payload, ensure_ascii=False).lower()
    forbidden = (
        "token_secret",
        "credential_secret",
        "device_key",
        "https://example.invalid",
    )
    for marker in forbidden:
        assert marker not in serialized


def _assert_no_forbidden_keys(value, forbidden_keys: set[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            assert key not in forbidden_keys
            _assert_no_forbidden_keys(child, forbidden_keys)
    elif isinstance(value, list):
        for child in value:
            _assert_no_forbidden_keys(child, forbidden_keys)
