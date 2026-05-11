from __future__ import annotations

import json

from agentops.api.app import create_app
from agentops.api.operations import ingest_quality_scorer_external_execution
from agentops.core.runtime_contracts import get_contract
from agentops.storage.audit import JsonlAuditLog
from agentops.storage.repository import InMemoryRepository
from tests.contract.test_ao47_ct_quality_scorer_external_intake_readback import (
    _assert_no_raw_leaks,
    _candidate_scorer,
    _json_get,
    _json_post,
    _seed_eval_case,
    _start_server,
    _valid_post_payload,
)
from tests.contract.test_ao48_ct_quality_scorer_external_intake_index import (
    _seed_eval_case_for,
)


def test_ao49_ct_001_contract_registry_and_app_route_declared():
    contract = get_contract("quality_scorer_external_intake_summary.v1")
    routes = create_app()

    assert contract.domain_owner == "AgentOps"
    assert contract.enum_fields["method"] == frozenset({"GET"})
    assert contract.enum_fields["health_state"] == frozenset(
        {"no_receipts", "receiving", "needs_review"}
    )
    assert "401" in contract.enum_fields["status_code"]
    assert {
        "route",
        "method",
        "agent_id",
        "version",
        "window_limit",
        "receipt_count",
        "health_state",
        "latest_receipt",
        "intake_state_counts",
        "source_trust_counts",
        "accepted_execution_count",
        "scorer_refs",
        "summary",
        "audit_id",
    }.issubset(contract.required_fields)
    assert {
        "QUALITY_SCORER_INTAKE_SUMMARY_QUERY_REQUIRED",
        "QUALITY_SCORER_INTAKE_SUMMARY_LIMIT_INVALID",
        "AGENTOPS_SCOPE_DENIED",
    }.issubset(contract.error_codes)
    assert "AO49-CT-001" in contract.contract_tests
    assert (
        routes["quality_scorer_external_intake_summary"]
        == "GET /v1/quality/scorers/external-intake/summary"
    )


def test_ao49_ct_002_http_summary_aggregates_scoped_receipts_without_new_execution():
    repository = InMemoryRepository()
    eval_case_id = _seed_eval_case(repository)
    server = _start_server(repository)
    try:
        first_response, _first = _json_post(
            server,
            "/v1/quality/scorers/external-intake",
            _valid_post_payload(eval_case_id, "scorer-external-summary:run-1"),
        )
        second_response, second = _json_post(
            server,
            "/v1/quality/scorers/external-intake",
            _valid_post_payload(eval_case_id, "scorer-external-summary:run-2"),
        )
        before_count = len(
            repository.quality_scorer_execution_records("agent.ai-sdlc", "1.0.0")
        )
        summary_response, payload = _json_get(
            server,
            "/v1/quality/scorers/external-intake/summary",
            {
                "agent_id": "agent.ai-sdlc",
                "version": "1.0.0",
                "limit": "5",
            },
        )
    finally:
        server.shutdown()

    after_count = len(
        repository.quality_scorer_execution_records("agent.ai-sdlc", "1.0.0")
    )
    assert first_response.status == 202
    assert second_response.status == 202
    assert summary_response.status == 200
    assert payload["schema_version"] == "quality_scorer_external_intake_summary.v1"
    assert payload["receipt_count"] == 2
    assert payload["window_limit"] == 5
    assert payload["health_state"] == "receiving"
    assert payload["latest_receipt"]["intake_id"] == second["intake_id"]
    assert payload["latest_sample_size"] == 1
    assert payload["latest_pass_rate"] == 1.0
    assert payload["intake_state_counts"] == {"accepted": 2}
    assert payload["source_trust_counts"] == {"signed": 2}
    assert payload["accepted_execution_count"] == 2
    assert payload["scorer_refs"] == [_candidate_scorer()]
    assert payload["summary"]["summary_only_intake_summary"] is True
    assert payload["summary"]["automatic_rollout_enabled"] is False
    assert before_count == 2
    assert after_count == before_count
    _assert_no_raw_leaks(payload)


def test_ao49_ct_003_http_summary_returns_empty_health_without_receipts():
    repository = InMemoryRepository()
    server = _start_server(repository)
    try:
        response, payload = _json_get(
            server,
            "/v1/quality/scorers/external-intake/summary",
            {
                "agent_id": "agent.ai-sdlc",
                "version": "1.0.0",
            },
        )
    finally:
        server.shutdown()

    assert response.status == 200
    assert payload["health_state"] == "no_receipts"
    assert payload["receipt_count"] == 0
    assert payload["latest_receipt"] == {}
    assert payload["latest_received_at"] == ""
    assert payload["latest_pass_rate"] == 0.0
    assert payload["latest_sample_size"] == 0
    assert payload["intake_state_counts"] == {}
    assert payload["source_trust_counts"] == {}
    assert payload["accepted_execution_count"] == 0
    assert payload["scorer_refs"] == []
    _assert_no_raw_leaks(payload)


def test_ao49_ct_004_http_summary_requires_full_agent_version_scope():
    repository = InMemoryRepository()
    server = _start_server(repository)
    try:
        response, payload = _json_get(
            server,
            "/v1/quality/scorers/external-intake/summary",
            {
                "agent_id": "agent.ai-sdlc",
                "limit": "5",
            },
        )
    finally:
        server.shutdown()

    assert response.status == 400
    assert payload["error_code"] == "QUALITY_SCORER_INTAKE_SUMMARY_QUERY_REQUIRED"
    assert payload["denied_scope"] == "quality_scorer_external_intake_summary.query"
    assert repository.quality_scorer_execution_records("agent.ai-sdlc", "1.0.0") == ()


def test_ao49_ct_005_http_summary_requires_production_read_scope(tmp_path):
    repository = InMemoryRepository()
    eval_case_id = _seed_eval_case(repository)
    ingest_quality_scorer_external_execution(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        idempotency_key="scorer-external-summary:scope",
        signature="sig:external-scorer-summary",
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
            "/v1/quality/scorers/external-intake/summary",
            {
                "agent_id": "agent.ai-sdlc",
                "version": "1.0.0",
            },
            headers={
                "X-AgentOps-Principal": "external-scorer",
                "X-AgentOps-Scopes": "quality.scorer.intake.write",
                "X-AgentOps-Request-Id": "req_ao49_scope",
                "X-AgentOps-Audit-Id": "audit_ao49_scope",
            },
        )
    finally:
        server.shutdown()

    records = [record.to_dict() for record in audit_log.records()]
    assert response.status == 403
    assert payload["error_code"] == "AGENTOPS_SCOPE_DENIED"
    assert payload["denied_scope"] == "quality.scorer.intake.read"
    assert records[-1]["action"] == "quality.scorer.external_intake.summary"
    assert records[-1]["outcome"] == "denied"
    assert records[-1]["denied_scope"] == "quality.scorer.intake.read"
    assert (
        len(repository.quality_scorer_execution_records("agent.ai-sdlc", "1.0.0")) == 1
    )


def test_ao49_ct_006_http_summary_invalid_limit_audits_without_query_payload(tmp_path):
    repository = InMemoryRepository()
    audit_log = JsonlAuditLog(tmp_path / "audit.jsonl")
    server = _start_server(repository, audit_log=audit_log)
    try:
        response, payload = _json_get(
            server,
            "/v1/quality/scorers/external-intake/summary",
            {
                "agent_id": "agent.ai-sdlc",
                "version": "1.0.0",
                "limit": "token_secret:https://example.invalid/raw",
            },
        )
    finally:
        server.shutdown()

    records = [record.to_dict() for record in audit_log.records()]
    serialized_audit = json.dumps(records, ensure_ascii=False).lower()
    assert response.status == 400
    assert payload["error_code"] == "QUALITY_SCORER_INTAKE_SUMMARY_LIMIT_INVALID"
    assert records[-1]["action"] == "quality.scorer.external_intake.summary"
    assert records[-1]["outcome"] == "rejected"
    assert records[-1]["error_code"] == "QUALITY_SCORER_INTAKE_SUMMARY_LIMIT_INVALID"
    assert "token_secret" not in serialized_audit
    assert "https://example.invalid" not in serialized_audit


def test_ao49_ct_007_http_summary_allows_uri_agent_id_without_raw_echo():
    repository = InMemoryRepository()
    eval_case_id = _seed_eval_case_for(
        repository,
        run_id="run_failed_summary_uri",
        agent_id="https://example.invalid/agent-summary-uri",
        version="1.0.0",
    )
    receipt = ingest_quality_scorer_external_execution(
        repository,
        "https://example.invalid/agent-summary-uri",
        "1.0.0",
        idempotency_key="scorer-external-summary:uri-agent",
        signature="sig:external-scorer-summary-uri",
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
        response, payload = _json_get(
            server,
            "/v1/quality/scorers/external-intake/summary",
            {
                "agent_id": "https://example.invalid/agent-summary-uri",
                "version": "1.0.0",
            },
        )
    finally:
        server.shutdown()

    assert response.status == 200
    assert payload["agent_id"] == "[redacted]"
    assert payload["receipt_count"] == 1
    assert payload["latest_receipt"]["intake_id"] == receipt["intake_id"]
    _assert_no_raw_leaks(payload)
