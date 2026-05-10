from __future__ import annotations

import json

import pytest

from agentops.api.operations import (
    create_eval_case,
    create_evidence_access_operation,
    get_dlq_operations_projection,
    get_exporter_operation,
    get_runtime_budget_summary,
    get_runtime_slo_summary,
    get_store_governance_projection,
)
from agentops.core.errors import AgentOpsError
from agentops.core.runtime_contracts import get_contract
from agentops.storage.repository import InMemoryRepository
from tests.contract.test_ao32_ct_evidence_health_summary_loop import (
    write_full_trace,
    write_runtime_run,
)


def test_ao37_ct_001_contract_registry_has_p1_b_operations():
    contract_ids = {
        "evidence_access_operation.v1": {
            "operation_id",
            "evidence_id",
            "requester",
            "reason",
            "raw_access_state",
            "summary",
            "audit_id",
        },
        "eval_case.v1": {
            "eval_case_id",
            "source_run",
            "privacy_class",
            "owner_team",
            "expected_behavior",
            "scorer_status",
            "audit_id",
        },
        "runtime_budget_summary.v1": {
            "agent_id",
            "version",
            "token_usage",
            "cost_estimate",
            "latency_ms",
            "budget_state",
            "audit_id",
        },
        "dlq_operations_projection.v1": {
            "backlog_count",
            "retry_candidates",
            "discard_candidates",
            "error_summary",
            "audit_id",
        },
        "exporter_operation.v1": {
            "exporter_type",
            "configuration_state",
            "external_write_enabled",
            "dispatch_state",
            "audit_id",
        },
        "runtime_slo_summary.v1": {
            "agent_id",
            "version",
            "slo_state",
            "health_summary",
            "budget_summary",
            "recommended_action",
            "audit_id",
        },
        "store_governance_projection.v1": {
            "agent_id",
            "version",
            "summary_state",
            "appeal_state",
            "owner_notification_state",
            "replacement_suggestion_state",
            "audit_id",
        },
    }

    for contract_id, required_fields in contract_ids.items():
        contract = get_contract(contract_id)
        assert contract.domain_owner == "AgentOps"
        assert required_fields.issubset(contract.required_fields)
        assert "AO37-CT-001" in contract.contract_tests


def test_ao37_ct_002_evidence_access_operation_is_summary_only():
    repository = InMemoryRepository()
    evidence_summary = {
        "schema_version": "evidence_summary.v1",
        "run_id": "run_1",
        "trace_id": "trace_1",
        "evidence_id": "evidence_1",
        "payload_hash": "sha256:evidence",
        "payload_ref": "vault://evidence/1",
        "raw_access_state": "summary_only",
    }

    operation = create_evidence_access_operation(
        repository,
        evidence_summary,
        requester="ops_1",
        reason="Investigate failed deployment.",
        approver_scope="evidence.owner",
        redaction_preview_state="ready",
    )

    assert operation["schema_version"] == "evidence_access_operation.v1"
    assert operation["evidence_id"] == "evidence_1"
    assert operation["raw_access_state"] == "requested"
    assert operation["summary"]["raw_payload_access"] == "forbidden"
    assert operation["owner_notification_state"] == "not_required"
    _assert_no_raw_leaks(operation)


def test_ao37_ct_002_redaction_failed_queues_owner_notification():
    repository = InMemoryRepository()

    operation = create_evidence_access_operation(
        repository,
        {"run_id": "run_1", "evidence_id": "evidence_1"},
        requester="ops_1",
        reason="Need source proof.",
        approver_scope="evidence.owner",
        redaction_preview_state="failed",
    )

    assert operation["redaction_preview_state"] == "failed"
    assert operation["owner_notification_state"] == "pending"
    assert operation["summary"]["raw_payload_access"] == "forbidden"


def test_ao37_ct_003_failed_run_can_become_eval_case():
    repository = InMemoryRepository()
    write_runtime_run(
        repository,
        run_id="run_failed",
        status="failed",
        terminal_reason="tool_error",
    )

    eval_case = create_eval_case(
        repository,
        "run_failed",
        owner_team="Quality",
        expected_behavior="Tool failure should be surfaced with a safe fallback.",
    )

    assert eval_case["schema_version"] == "eval_case.v1"
    assert eval_case["source_run"]["run_id"] == "run_failed"
    assert eval_case["status"] == "needs_review"
    assert eval_case["privacy_class"] == "internal"
    assert eval_case["scorer_status"] == "not_started"
    assert eval_case["summary"]["raw_payload_access"] == "forbidden"


def test_ao37_ct_003_succeeded_run_is_not_failure_sample():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_success", status="succeeded")

    with pytest.raises(AgentOpsError) as exc:
        create_eval_case(
            repository,
            "run_success",
            owner_team="Quality",
            expected_behavior="No failure expected.",
        )

    assert exc.value.error_code == "EVAL_CASE_SOURCE_NOT_FAILED"


def test_ao37_ct_004_runtime_budget_summary_aggregates_tokens_cost_and_latency():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_1", status="succeeded")
    write_full_trace(repository, run_id="run_1")

    budget = get_runtime_budget_summary(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        token_budget=100,
        cost_budget=0.02,
        latency_budget_ms=500,
    )

    assert budget["schema_version"] == "runtime_budget_summary.v1"
    assert budget["token_usage"]["input"] == 48
    assert budget["token_usage"]["output"] == 32
    assert budget["cost_estimate"]["amount"] == pytest.approx(0.04)
    assert budget["latency_ms"]["p95"] == 1000
    assert budget["budget_state"] == "over_budget"
    assert budget["recommended_action"] == "review_budget"
    _assert_no_raw_leaks(budget)


def test_ao37_ct_005_dlq_projection_is_summary_only():
    repository = InMemoryRepository()
    repository.write_runtime_dlq(
        {
            "event_id": "evt_retry",
            "event_type": "trace_span",
            "event_type_version": "trace_span.v1",
            "schema_version": "event_envelope.v1",
            "sequence_no": 3,
            "idempotency_key": "runtime:retry",
            "payload_hash": "sha256:retry",
            "payload_ref": "vault://retry",
            "source_trust": "verified",
            "integration_mode": "enterprise_managed",
        },
        error_code="TRACE_PARENT_MISSING",
        message="Parent span missing.",
        retryable=True,
    )
    repository.write_runtime_dlq(
        {
            "event_id": "evt_discard",
            "event_type": "runtime_run",
            "event_type_version": "runtime_run.v1",
            "schema_version": "event_envelope.v1",
            "sequence_no": 4,
            "idempotency_key": "runtime:discard",
            "payload_hash": "sha256:discard",
            "payload_ref": "vault://discard",
        },
        error_code="EVENT_SIGNATURE_INVALID",
        message="Invalid signature.",
        retryable=False,
        status="rejected",
    )

    projection = get_dlq_operations_projection(repository)

    assert projection["schema_version"] == "dlq_operations_projection.v1"
    assert projection["backlog_count"] == 2
    assert projection["retry_candidates"][0]["event_id"] == "evt_retry"
    assert projection["discard_candidates"][0]["event_id"] == "evt_discard"
    assert projection["error_summary"]["TRACE_PARENT_MISSING"] == 1
    assert projection["summary"]["raw_payload_access"] == "forbidden"
    _assert_no_raw_leaks(projection)


def test_ao37_ct_006_exporter_operation_is_dry_run_only():
    operation = get_exporter_operation(
        exporter_type="otlp",
        endpoint_ref="otel://collector/internal",
        requested_by="ops_1",
    )

    assert operation["schema_version"] == "exporter_operation.v1"
    assert operation["configuration_state"] == "configured"
    assert operation["external_write_enabled"] is False
    assert operation["dispatch_state"] == "not_started"
    assert operation["summary"]["dry_run_only"] is True


def test_ao37_ct_007_runtime_slo_combines_health_budget_and_dlq():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_1", status="failed")
    repository.write_runtime_dlq(
        {
            "event_id": "evt_retry",
            "agent_id": "agent.ai-sdlc",
            "version": "1.0.0",
            "payload_hash": "sha256:retry",
        },
        error_code="TRACE_PARENT_MISSING",
        message="Parent span missing.",
    )

    slo = get_runtime_slo_summary(repository, "agent.ai-sdlc", "1.0.0")

    assert slo["schema_version"] == "runtime_slo_summary.v1"
    assert slo["slo_state"] == "breached"
    assert slo["health_summary"]["recommended_action"] == "disable_recommended"
    assert slo["dlq_summary"]["backlog_count"] == 1
    assert slo["recommended_action"] == "open_ops_review"


def test_ao37_ct_007_runtime_slo_passes_budget_thresholds():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_1", status="succeeded")
    write_full_trace(repository, run_id="run_1")

    slo = get_runtime_slo_summary(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        token_budget=50,
        cost_budget=0.02,
        latency_budget_ms=500,
    )

    assert slo["budget_summary"]["budget_state"] == "over_budget"
    assert slo["slo_state"] == "at_risk"
    assert slo["recommended_action"] == "review_budget"


def test_ao37_ct_007_runtime_slo_warns_on_at_risk_budget():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_1", status="succeeded")
    write_full_trace(repository, run_id="run_1")

    slo = get_runtime_slo_summary(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        token_budget=100,
        cost_budget=0.05,
        latency_budget_ms=2000,
    )

    assert slo["budget_summary"]["budget_state"] == "at_risk"
    assert slo["slo_state"] == "at_risk"
    assert slo["recommended_action"] == "review_budget"


def test_ao37_ct_007_runtime_slo_ignores_unrelated_dlq_backlog():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_1", status="succeeded")
    write_full_trace(repository, run_id="run_1")
    repository.write_runtime_dlq(
        {
            "event_id": "evt_other_agent",
            "agent_id": "agent.other",
            "version": "9.9.9",
            "payload_hash": "sha256:other",
        },
        error_code="TRACE_PARENT_MISSING",
        message="Parent span missing.",
    )

    slo = get_runtime_slo_summary(repository, "agent.ai-sdlc", "1.0.0")

    assert slo["dlq_summary"]["backlog_count"] == 0
    assert slo["slo_state"] == "healthy"
    assert slo["recommended_action"] == "none"


def test_ao37_ct_007_runtime_slo_backfills_dlq_identity_from_run():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_1", status="succeeded")
    write_full_trace(repository, run_id="run_1")
    repository.write_runtime_dlq(
        {
            "event_id": "evt_missing_parent",
            "event_type": "trace_span",
            "payload": {"run_id": "run_1", "trace_id": "trace_1"},
            "payload_hash": "sha256:missing-parent",
        },
        error_code="TRACE_PARENT_MISSING",
        message="Parent span missing.",
    )

    slo = get_runtime_slo_summary(repository, "agent.ai-sdlc", "1.0.0")

    assert slo["dlq_summary"]["backlog_count"] == 1
    assert slo["slo_state"] == "breached"
    assert slo["recommended_action"] == "open_ops_review"


def test_ao37_ct_007_runtime_slo_reconciles_out_of_order_dlq_identity():
    repository = InMemoryRepository()
    repository.write_runtime_dlq(
        {
            "event_id": "evt_out_of_order",
            "event_type": "trace_span",
            "payload": {"run_id": "run_1", "trace_id": "trace_1"},
            "payload_hash": "sha256:out-of-order",
        },
        error_code="TRACE_PARENT_MISSING",
        message="Parent span missing.",
    )
    write_runtime_run(repository, run_id="run_1", status="succeeded")
    write_full_trace(repository, run_id="run_1")

    records = repository.runtime_dlq_records(agent_id="agent.ai-sdlc", version="1.0.0")
    slo = get_runtime_slo_summary(repository, "agent.ai-sdlc", "1.0.0")

    assert records[0]["agent_id"] == "agent.ai-sdlc"
    assert records[0]["version"] == "1.0.0"
    assert slo["dlq_summary"]["backlog_count"] == 1
    assert slo["slo_state"] == "breached"
    assert slo["recommended_action"] == "open_ops_review"


def test_ao37_ct_008_store_governance_projection_is_display_only():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_1", status="blocked")

    projection = get_store_governance_projection(repository, "agent.ai-sdlc", "1.0.0")

    assert projection["schema_version"] == "store_governance_projection.v1"
    assert projection["summary_state"] == "fresh"
    assert projection["appeal_state"] == "available"
    assert projection["owner_notification_state"] == "pending"
    assert projection["replacement_suggestion_state"] == "suggested"
    assert projection["summary"]["automatic_lifecycle_action"] is False


def _assert_no_raw_leaks(payload: dict) -> None:
    forbidden_keys = {
        "raw_payload",
        "prompt",
        "token_secret",
        "credential_secret",
        "device_key",
        "download_url",
        "raw_url",
    }
    forbidden_values = ("token_secret", "credential_secret", "device_key")
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
