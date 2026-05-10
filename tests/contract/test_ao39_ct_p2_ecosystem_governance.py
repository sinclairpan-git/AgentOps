from __future__ import annotations

import json

import pytest

from agentops.api.operations import (
    get_complex_risk_profile,
    get_exporter_ecosystem_projection,
    get_mcp_a2a_governance_projection,
    get_multi_agent_handoff_evaluation,
)
from agentops.api.runtime import ingest_runtime_events
from agentops.core.errors import AgentOpsError
from agentops.core.runtime_contracts import get_contract
from agentops.storage.repository import InMemoryRepository
from tests.contract.test_ao32_ct_evidence_health_summary_loop import (
    runtime_batch,
    runtime_event,
    trace_span_payload,
    write_runtime_run,
)


def test_ao39_ct_001_contract_registry_has_p2_b_operations():
    contract_ids = {
        "mcp_a2a_governance_projection.v1": {
            "protocol",
            "endpoint_ref",
            "subject_agent_id",
            "gateway_state",
            "policy_check_state",
            "evidence_state",
            "summary",
            "audit_id",
        },
        "exporter_ecosystem_projection.v1": {
            "exporters",
            "ecosystem_state",
            "external_write_enabled",
            "summary",
            "audit_id",
        },
        "multi_agent_handoff_evaluation.v1": {
            "agent_id",
            "version",
            "handoff_count",
            "failed_handoff_count",
            "handoff_quality_state",
            "summary",
            "audit_id",
        },
        "complex_risk_profile.v1": {
            "agent_id",
            "version",
            "risk_profile_state",
            "risk_factors",
            "recommended_action",
            "summary",
            "audit_id",
        },
    }

    for contract_id, required_fields in contract_ids.items():
        contract = get_contract(contract_id)
        assert contract.domain_owner == "AgentOps"
        assert required_fields.issubset(contract.required_fields)
        assert "AO39-CT-001" in contract.contract_tests


def test_ao39_ct_002_mcp_a2a_governance_requires_runtime_gateway():
    projection = get_mcp_a2a_governance_projection(
        protocol="mcp",
        endpoint_ref="mcp://tools/safe-search",
        subject_agent_id="agent.ai-sdlc",
        resource_scope="tools.safe_search",
        requested_by="ops_1",
        policy_check_state="passed",
    )

    assert projection["schema_version"] == "mcp_a2a_governance_projection.v1"
    assert projection["gateway_state"] == "configured"
    assert projection["policy_check_state"] == "passed"
    assert projection["evidence_state"] == "summary_only"
    assert projection["summary"]["runtime_gateway_required"] is True
    assert projection["summary"]["direct_connection_allowed"] is False
    assert projection["summary"]["runtime_execution_performed"] is False
    _assert_no_raw_leaks(projection)


def test_ao39_ct_002_unsupported_ecosystem_protocol_is_rejected():
    with pytest.raises(AgentOpsError) as exc:
        get_mcp_a2a_governance_projection(
            protocol="webhook",
            endpoint_ref="https://example.invalid/raw",
            subject_agent_id="agent.ai-sdlc",
            resource_scope="tools.external",
        )

    assert exc.value.error_code == "MCP_A2A_PROTOCOL_UNSUPPORTED"


def test_ao39_ct_002_non_string_protocol_is_rejected_as_domain_error():
    with pytest.raises(AgentOpsError) as exc:
        get_mcp_a2a_governance_projection(
            protocol=None,
            endpoint_ref="mcp://tools/safe-search",
            subject_agent_id="agent.ai-sdlc",
            resource_scope="tools.safe_search",
        )

    assert exc.value.error_code == "MCP_A2A_PROTOCOL_UNSUPPORTED"


def test_ao39_ct_003_exporter_ecosystem_is_dry_run_only():
    projection = get_exporter_ecosystem_projection(
        requested_by="ops_1",
        exporters=[
            {
                "exporter_id": "otel",
                "exporter_type": "otlp",
                "endpoint_ref": "otel://collector/internal",
                "config": {"token_secret": "must not appear"},
            },
            {
                "exporter_id": "lake",
                "exporter_type": "data_lake",
                "endpoint_ref": "lake://warehouse/runtime",
            },
        ],
    )

    assert projection["schema_version"] == "exporter_ecosystem_projection.v1"
    assert projection["ecosystem_state"] == "configured"
    assert projection["external_write_enabled"] is False
    assert projection["summary"]["network_dispatch_performed"] is False
    assert projection["exporters"][0]["configuration_hash"].startswith("sha256:")
    assert all(
        item["dispatch_state"] == "not_started" for item in projection["exporters"]
    )
    _assert_no_raw_leaks(projection)


def test_ao39_ct_003_unsupported_exporter_type_is_rejected():
    with pytest.raises(AgentOpsError) as exc:
        get_exporter_ecosystem_projection(
            exporters=[{"exporter_type": "raw_http", "endpoint_ref": "raw://sink"}],
        )

    assert exc.value.error_code == "EXPORTER_ECOSYSTEM_UNSUPPORTED"


def test_ao39_ct_003_non_object_exporter_is_rejected_as_domain_error():
    with pytest.raises(AgentOpsError) as exc:
        get_exporter_ecosystem_projection(exporters=[None])

    assert exc.value.error_code == "EXPORTER_ECOSYSTEM_UNSUPPORTED"


def test_ao39_ct_004_multi_agent_handoff_evaluation_reads_summary_spans():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_handoff", status="failed")
    _write_handoff_span(repository, span_id="handoff_ok", status_code="ok")
    _write_handoff_span(
        repository,
        span_id="handoff_failed",
        status_code="error",
        error_code="HANDOFF_POLICY_BLOCKED",
    )

    evaluation = get_multi_agent_handoff_evaluation(
        repository, "agent.ai-sdlc", "1.0.0"
    )

    assert evaluation["schema_version"] == "multi_agent_handoff_evaluation.v1"
    assert evaluation["handoff_count"] == 2
    assert evaluation["failed_handoff_count"] == 1
    assert evaluation["handoff_quality_state"] == "needs_review"
    assert evaluation["summary"]["automatic_handoff_action"] is False
    assert evaluation["summary"]["runtime_execution_performed"] is False
    _assert_no_raw_leaks(evaluation)


def test_ao39_ct_005_complex_risk_profile_combines_health_dlq_and_handoff():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_blocked", status="blocked")
    _write_handoff_span(
        repository,
        run_id="run_blocked",
        span_id="handoff_failed",
        status_code="blocked",
        error_code="HANDOFF_POLICY_BLOCKED",
    )
    repository.write_runtime_dlq(
        {
            "event_id": "evt_handoff_dlq",
            "agent_id": "agent.ai-sdlc",
            "version": "1.0.0",
            "payload_hash": "sha256:handoff-dlq",
        },
        error_code="TRACE_PARENT_MISSING",
        message="Parent span missing.",
    )

    profile = get_complex_risk_profile(repository, "agent.ai-sdlc", "1.0.0")

    assert profile["schema_version"] == "complex_risk_profile.v1"
    assert profile["risk_profile_state"] == "critical"
    assert profile["recommended_action"] == "disable_recommended"
    assert profile["handoff_evaluation"]["failed_handoff_count"] == 1
    assert profile["dlq_summary"]["backlog_count"] == 1
    assert profile["summary"]["automatic_runtime_action"] is False
    assert profile["summary"]["automatic_store_action"] is False
    _assert_no_raw_leaks(profile)


def _write_handoff_span(
    repository: InMemoryRepository,
    *,
    run_id: str = "run_handoff",
    span_id: str,
    status_code: str,
    error_code: str = "",
) -> None:
    span = trace_span_payload(
        run_id=run_id,
        span_id=span_id,
        span_kind="handoff",
        operation_name="agent.handoff",
        status_code=status_code,
        error_code=error_code,
    )
    ingest_runtime_events(
        runtime_batch(
            [
                runtime_event(
                    f"evt_{run_id}_{span_id}",
                    "trace_span",
                    span,
                    sequence_no=20,
                    idempotency_key=f"runtime:{run_id}:{span_id}",
                )
            ]
        ),
        repository,
    )


def _assert_no_raw_leaks(payload: dict) -> None:
    forbidden_keys = {
        "raw_payload",
        "prompt",
        "token_secret",
        "credential_secret",
        "device_key",
        "download_url",
        "raw_url",
        "config",
        "payload",
    }
    forbidden_values = (
        "token_secret",
        "credential_secret",
        "device_key",
        "must not appear",
    )
    _assert_no_forbidden_keys(payload, forbidden_keys)
    serialized = json.dumps(payload, ensure_ascii=False)
    for marker in forbidden_values:
        assert marker not in serialized


def _assert_no_forbidden_keys(value, forbidden_keys: set[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            assert key not in forbidden_keys
            _assert_no_forbidden_keys(child, forbidden_keys)
    elif isinstance(value, list):
        for child in value:
            _assert_no_forbidden_keys(child, forbidden_keys)
