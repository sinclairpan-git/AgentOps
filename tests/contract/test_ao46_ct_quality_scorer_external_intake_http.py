from __future__ import annotations

import json
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from threading import Thread

from agentops.api.app import create_app
from agentops.api.operations import create_eval_case
from agentops.api.server import create_http_handler
from agentops.core.runtime_contracts import get_contract
from agentops.storage.audit import JsonlAuditLog
from agentops.storage.repository import InMemoryRepository
from tests.contract.test_ao32_ct_evidence_health_summary_loop import (
    write_full_trace,
    write_runtime_run,
)


def test_ao46_ct_001_contract_registry_and_app_route_declared():
    contract = get_contract("quality_scorer_external_intake_http.v1")
    routes = create_app()

    assert contract.domain_owner == "AgentOps"
    assert contract.enum_fields["method"] == frozenset({"POST"})
    assert {
        "route",
        "method",
        "agent_id",
        "version",
        "external_result",
        "idempotency_key",
        "signature",
        "source_trust",
        "receipt",
        "audit_id",
    }.issubset(contract.required_fields)
    assert {
        "QUALITY_SCORER_INTAKE_HTTP_REQUEST_INVALID",
        "QUALITY_SCORER_INTAKE_SIGNATURE_INVALID",
        "AGENTOPS_SCOPE_DENIED",
    }.issubset(contract.error_codes)
    assert "AO46-CT-001" in contract.contract_tests
    assert (
        routes["quality_scorer_external_intake"]
        == "POST /v1/quality/scorers/external-intake"
    )


def test_ao46_ct_002_http_external_intake_accepts_signed_summary_with_header_metadata():
    repository = InMemoryRepository()
    eval_case_id = _seed_eval_case(repository)
    server = _start_server(repository)
    try:
        response, receipt = _json_post(
            server,
            "/v1/quality/scorers/external-intake",
            {
                "agent_id": "agent.ai-sdlc",
                "version": "1.0.0",
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
                "pass_threshold": 0.8,
            },
            headers={
                "Idempotency-Key": "scorer-external-http:run-1",
                "X-AgentOps-Scorer-Signature": "sig:external-scorer-http",
                "X-AgentOps-Source-Trust": "verified",
            },
        )
    finally:
        server.shutdown()

    assert response.status == 202
    assert receipt["schema_version"] == "quality_scorer_external_intake.v1"
    assert receipt["intake_state"] == "accepted"
    assert receipt["idempotency_key"] == "scorer-external-http:run-1"
    assert receipt["source_trust"] == "verified"
    assert receipt["summary"]["agentops_scorer_invoked"] is False
    assert receipt["summary"]["automatic_rollout_enabled"] is False
    execution_records = repository.quality_scorer_execution_records(
        "agent.ai-sdlc",
        "1.0.0",
        scorer_id="quality_summary_stage5_candidate",
        scorer_version="1.1.0",
    )
    assert len(execution_records) == 1
    assert execution_records[0]["execution_source"] == "external_intake"


def test_ao46_ct_003_http_external_intake_rejects_missing_envelope_fields():
    repository = InMemoryRepository()
    server = _start_server(repository)
    try:
        response, payload = _json_post(
            server,
            "/v1/quality/scorers/external-intake",
            {
                "agent_id": "agent.ai-sdlc",
                "external_result": {},
            },
        )
    finally:
        server.shutdown()

    assert response.status == 400
    assert payload["error_code"] == "QUALITY_SCORER_INTAKE_HTTP_REQUEST_INVALID"
    assert repository.quality_scorer_execution_records("agent.ai-sdlc", "1.0.0") == ()


def test_ao46_ct_004_http_external_intake_rejects_raw_payload_and_audits_without_body(
    tmp_path,
):
    repository = InMemoryRepository()
    eval_case_id = _seed_eval_case(repository)
    audit_log = JsonlAuditLog(tmp_path / "audit.jsonl")
    server = _start_server(repository, audit_log=audit_log)
    try:
        response, payload = _json_post(
            server,
            "/v1/quality/scorers/external-intake",
            {
                "agent_id": "agent.ai-sdlc",
                "version": "1.0.0",
                "idempotency_key": "scorer-external-http:raw",
                "signature": "sig:external-scorer-http",
                "external_result": {
                    "source_eval_cases": [eval_case_id],
                    "case_results": [
                        {"eval_case_id": eval_case_id, "outcome": "passed"}
                    ],
                    "Raw_Payload": "token_secret https://example.invalid/raw",
                },
            },
        )
    finally:
        server.shutdown()

    records = [record.to_dict() for record in audit_log.records()]
    serialized_audit = json.dumps(records, ensure_ascii=False).lower()
    assert response.status == 400
    assert payload["error_code"] == "QUALITY_SCORER_INTAKE_RAW_INPUT"
    assert records[-1]["action"] == "quality.scorer.external_intake.ingest"
    assert records[-1]["outcome"] == "rejected"
    assert records[-1]["error_code"] == "QUALITY_SCORER_INTAKE_RAW_INPUT"
    assert "raw_payload" not in serialized_audit
    assert "token_secret" not in serialized_audit
    assert "https://example.invalid" not in serialized_audit
    assert repository.quality_scorer_execution_records("agent.ai-sdlc", "1.0.0") == ()


def test_ao46_ct_005_http_external_intake_requires_production_scope(tmp_path):
    repository = InMemoryRepository()
    eval_case_id = _seed_eval_case(repository)
    audit_log = JsonlAuditLog(tmp_path / "audit.jsonl")
    server = _start_server(repository, require_auth=True, audit_log=audit_log)
    try:
        response, payload = _json_post(
            server,
            "/v1/quality/scorers/external-intake",
            _valid_payload(eval_case_id),
            headers={
                "X-AgentOps-Principal": "external-scorer",
                "X-AgentOps-Scopes": "store.summary.read",
                "X-AgentOps-Request-Id": "req_ao46_scope",
                "X-AgentOps-Audit-Id": "audit_ao46_scope",
            },
        )
    finally:
        server.shutdown()

    records = [record.to_dict() for record in audit_log.records()]
    assert response.status == 403
    assert payload["error_code"] == "AGENTOPS_SCOPE_DENIED"
    assert payload["denied_scope"] == "quality.scorer.intake.write"
    assert records[-1]["outcome"] == "denied"
    assert records[-1]["denied_scope"] == "quality.scorer.intake.write"
    assert repository.quality_scorer_execution_records("agent.ai-sdlc", "1.0.0") == ()


def _json_post(
    server: ThreadingHTTPServer,
    path: str,
    payload: dict,
    *,
    headers: dict[str, str] | None = None,
):
    connection = HTTPConnection(
        server.server_address[0], server.server_address[1], timeout=5
    )
    try:
        request_headers = {
            "Content-Type": "application/json",
            "Origin": "http://127.0.0.1:5173",
            **(headers or {}),
        }
        connection.request(
            "POST",
            path,
            body=json.dumps(payload).encode("utf-8"),
            headers=request_headers,
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
    run_id: str = "run_failed",
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


def _valid_payload(eval_case_id: str) -> dict:
    return {
        "agent_id": "agent.ai-sdlc",
        "version": "1.0.0",
        "idempotency_key": "scorer-external-http:scope",
        "signature": "sig:external-scorer-http",
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
