from __future__ import annotations

import json

from agentops.api.app import create_app
from agentops.api.operations import (
    create_eval_case,
    ingest_quality_scorer_external_execution,
)
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
from tests.contract.test_ao32_ct_evidence_health_summary_loop import (
    write_full_trace,
    write_runtime_run,
)


def test_ao48_ct_001_contract_registry_and_app_route_declared():
    contract = get_contract("quality_scorer_external_intake_index.v1")
    routes = create_app()

    assert contract.domain_owner == "AgentOps"
    assert contract.enum_fields["method"] == frozenset({"GET"})
    assert "401" in contract.enum_fields["status_code"]
    assert {
        "route",
        "method",
        "agent_id",
        "version",
        "limit",
        "returned",
        "receipts",
        "summary",
        "audit_id",
    }.issubset(contract.required_fields)
    assert {
        "QUALITY_SCORER_INTAKE_INDEX_QUERY_REQUIRED",
        "QUALITY_SCORER_INTAKE_INDEX_LIMIT_INVALID",
        "AGENTOPS_SCOPE_DENIED",
    }.issubset(contract.error_codes)
    assert "AO48-CT-001" in contract.contract_tests
    assert (
        routes["quality_scorer_external_intake_index"]
        == "GET /v1/quality/scorers/external-intake/index"
    )


def test_ao48_ct_002_http_index_returns_recent_scoped_receipts_without_new_execution():
    repository = InMemoryRepository()
    eval_case_id = _seed_eval_case(repository)
    server = _start_server(repository)
    try:
        first_response, _first = _json_post(
            server,
            "/v1/quality/scorers/external-intake",
            _valid_post_payload(eval_case_id, "scorer-external-index:run-1"),
        )
        second_response, second = _json_post(
            server,
            "/v1/quality/scorers/external-intake",
            _valid_post_payload(eval_case_id, "scorer-external-index:run-2"),
        )
        before_count = len(
            repository.quality_scorer_execution_records("agent.ai-sdlc", "1.0.0")
        )
        index_response, payload = _json_get(
            server,
            "/v1/quality/scorers/external-intake/index",
            {
                "agent_id": "agent.ai-sdlc",
                "version": "1.0.0",
                "limit": "1",
            },
        )
    finally:
        server.shutdown()

    after_count = len(
        repository.quality_scorer_execution_records("agent.ai-sdlc", "1.0.0")
    )
    assert first_response.status == 202
    assert second_response.status == 202
    assert index_response.status == 200
    assert payload["schema_version"] == "quality_scorer_external_intake_index.v1"
    assert payload["returned"] == 1
    assert payload["limit"] == 1
    assert payload["receipts"][0]["intake_id"] == second["intake_id"]
    assert payload["receipts"][0]["idempotency_key"] == "scorer-external-index:run-2"
    assert payload["summary"]["summary_only_index"] is True
    assert payload["summary"]["key_only_lookup_allowed"] is False
    assert before_count == 2
    assert after_count == before_count
    _assert_no_raw_leaks(payload)


def test_ao48_ct_003_http_index_requires_full_agent_version_scope():
    repository = InMemoryRepository()
    server = _start_server(repository)
    try:
        response, payload = _json_get(
            server,
            "/v1/quality/scorers/external-intake/index",
            {
                "agent_id": "agent.ai-sdlc",
                "limit": "5",
            },
        )
    finally:
        server.shutdown()

    assert response.status == 400
    assert payload["error_code"] == "QUALITY_SCORER_INTAKE_INDEX_QUERY_REQUIRED"
    assert payload["denied_scope"] == "quality_scorer_external_intake_index.query"
    assert repository.quality_scorer_execution_records("agent.ai-sdlc", "1.0.0") == ()


def test_ao48_ct_004_http_index_requires_production_read_scope(tmp_path):
    repository = InMemoryRepository()
    eval_case_id = _seed_eval_case(repository)
    ingest_quality_scorer_external_execution(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        idempotency_key="scorer-external-index:scope",
        signature="sig:external-scorer-index",
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
            "/v1/quality/scorers/external-intake/index",
            {
                "agent_id": "agent.ai-sdlc",
                "version": "1.0.0",
            },
            headers={
                "X-AgentOps-Principal": "external-scorer",
                "X-AgentOps-Scopes": "quality.scorer.intake.write",
                "X-AgentOps-Request-Id": "req_ao48_scope",
                "X-AgentOps-Audit-Id": "audit_ao48_scope",
            },
        )
    finally:
        server.shutdown()

    records = [record.to_dict() for record in audit_log.records()]
    assert response.status == 403
    assert payload["error_code"] == "AGENTOPS_SCOPE_DENIED"
    assert payload["denied_scope"] == "quality.scorer.intake.read"
    assert records[-1]["action"] == "quality.scorer.external_intake.index"
    assert records[-1]["outcome"] == "denied"
    assert records[-1]["denied_scope"] == "quality.scorer.intake.read"
    assert (
        len(repository.quality_scorer_execution_records("agent.ai-sdlc", "1.0.0")) == 1
    )


def test_ao48_ct_005_http_index_invalid_limit_audits_without_query_payload(tmp_path):
    repository = InMemoryRepository()
    audit_log = JsonlAuditLog(tmp_path / "audit.jsonl")
    server = _start_server(repository, audit_log=audit_log)
    try:
        response, payload = _json_get(
            server,
            "/v1/quality/scorers/external-intake/index",
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
    assert payload["error_code"] == "QUALITY_SCORER_INTAKE_INDEX_LIMIT_INVALID"
    assert records[-1]["action"] == "quality.scorer.external_intake.index"
    assert records[-1]["outcome"] == "rejected"
    assert records[-1]["error_code"] == "QUALITY_SCORER_INTAKE_INDEX_LIMIT_INVALID"
    assert "token_secret" not in serialized_audit
    assert "https://example.invalid" not in serialized_audit


def test_ao48_ct_006_repository_index_is_scoped_by_agent_version():
    repository = InMemoryRepository()
    first_eval_case_id = _seed_eval_case(repository, run_id="run_failed_index_a")
    ingest_quality_scorer_external_execution(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        idempotency_key="scorer-external-index:agent-a",
        signature="sig:external-scorer-index-a",
        scorer=_candidate_scorer(),
        external_result={
            "source_eval_cases": [first_eval_case_id],
            "case_results": [
                {
                    "eval_case_id": first_eval_case_id,
                    "outcome": "passed",
                    "score": 0.94,
                }
            ],
        },
    )
    second_eval_case_id = _seed_eval_case_for(
        repository,
        run_id="run_failed_index_b",
        agent_id="agent.other",
        version="2.0.0",
    )
    ingest_quality_scorer_external_execution(
        repository,
        "agent.other",
        "2.0.0",
        idempotency_key="scorer-external-index:agent-b",
        signature="sig:external-scorer-index-b",
        scorer=_candidate_scorer(),
        external_result={
            "source_eval_cases": [second_eval_case_id],
            "case_results": [
                {
                    "eval_case_id": second_eval_case_id,
                    "outcome": "passed",
                    "score": 0.91,
                }
            ],
        },
    )

    receipts = repository.quality_scorer_external_receipt_records(
        agent_id="agent.ai-sdlc",
        version="1.0.0",
    )

    assert len(receipts) == 1
    assert receipts[0]["idempotency_key"] == "scorer-external-index:agent-a"
    _assert_no_raw_leaks({"receipts": list(receipts)})


def test_ao48_ct_007_http_index_allows_uri_agent_id_without_raw_echo():
    repository = InMemoryRepository()
    eval_case_id = _seed_eval_case_for(
        repository,
        run_id="run_failed_index_uri",
        agent_id="https://example.invalid/agent-uri",
        version="1.0.0",
    )
    receipt = ingest_quality_scorer_external_execution(
        repository,
        "https://example.invalid/agent-uri",
        "1.0.0",
        idempotency_key="scorer-external-index:uri-agent",
        signature="sig:external-scorer-index-uri",
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
            "/v1/quality/scorers/external-intake/index",
            {
                "agent_id": "https://example.invalid/agent-uri",
                "version": "1.0.0",
            },
        )
    finally:
        server.shutdown()

    assert response.status == 200
    assert payload["agent_id"] == "[redacted]"
    assert payload["returned"] == 1
    assert payload["receipts"][0]["intake_id"] == receipt["intake_id"]
    _assert_no_raw_leaks(payload)


def test_ao48_ct_008_repository_index_does_not_match_redacted_plain_identity():
    repository = InMemoryRepository()
    first_eval_case_id = _seed_eval_case_for(
        repository,
        run_id="run_failed_index_redacted_a",
        agent_id="https://example.invalid/agent-a",
        version="1.0.0",
    )
    second_eval_case_id = _seed_eval_case_for(
        repository,
        run_id="run_failed_index_redacted_b",
        agent_id="https://example.invalid/agent-b",
        version="1.0.0",
    )
    ingest_quality_scorer_external_execution(
        repository,
        "https://example.invalid/agent-a",
        "1.0.0",
        idempotency_key="scorer-external-index:redacted-a",
        signature="sig:external-scorer-index-a",
        scorer=_candidate_scorer(),
        external_result={
            "source_eval_cases": [first_eval_case_id],
            "case_results": [
                {
                    "eval_case_id": first_eval_case_id,
                    "outcome": "passed",
                    "score": 0.94,
                }
            ],
        },
    )
    ingest_quality_scorer_external_execution(
        repository,
        "https://example.invalid/agent-b",
        "1.0.0",
        idempotency_key="scorer-external-index:redacted-b",
        signature="sig:external-scorer-index-b",
        scorer=_candidate_scorer(),
        external_result={
            "source_eval_cases": [second_eval_case_id],
            "case_results": [
                {
                    "eval_case_id": second_eval_case_id,
                    "outcome": "passed",
                    "score": 0.91,
                }
            ],
        },
    )

    receipts = repository.quality_scorer_external_receipt_records(
        agent_id="[redacted]",
        version="1.0.0",
    )

    assert receipts == ()


def _seed_eval_case_for(
    repository: InMemoryRepository,
    *,
    run_id: str,
    agent_id: str,
    version: str,
) -> str:
    write_runtime_run(
        repository,
        run_id=run_id,
        agent_id=agent_id,
        version=version,
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
