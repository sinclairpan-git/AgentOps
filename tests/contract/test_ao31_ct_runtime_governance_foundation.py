import pytest

from agentops.api.app import create_app
from agentops.core.errors import AgentOpsError
from agentops.api.runtime import ingest_runtime_events
from agentops.core.runtime_contracts import (
    CONTRACT_REGISTRY,
    STATE_REGISTRY,
    contract_registry_hash,
    get_contract,
    validate_contract_registry,
    validate_contract_value,
    validate_state_registry,
)
from agentops.storage.repository import InMemoryRepository


def runtime_run_payload(**overrides):
    payload = {
        "runtime_id": "runtime_local_1",
        "runtime_version": "1.0.0",
        "execution_environment": "local",
        "session_id": "session_1",
        "run_id": "run_1",
        "attempt_no": 1,
        "agent_id": "agent.ai-sdlc",
        "version": "1.0.0",
        "trigger_source": "user",
        "isolation_profile": "basic_local",
        "policy_bundle_version": "policy.v1",
        "status": "running",
        "terminal_reason": "",
    }
    payload.update(overrides)
    return payload


def trace_span_payload(**overrides):
    payload = {
        "trace_id": "trace_1",
        "span_id": "span_root",
        "parent_span_id": "",
        "run_id": "run_1",
        "span_kind": "model",
        "operation_name": "model.call",
        "status_code": "ok",
        "start_time": "2026-05-09T05:00:00+00:00",
        "end_time": "2026-05-09T05:00:01+00:00",
        "attempt_no": 1,
        "input_ref": "sha256:input",
        "output_ref": "sha256:output",
        "token_usage": {"input": 12, "output": 8},
        "cost_estimate": {"amount": 0.01, "currency": "USD"},
        "grant_id": "",
        "guardrail_result_refs": [],
        "error_code": "",
        "retryable": False,
    }
    payload.update(overrides)
    return payload


def runtime_event(
    event_id,
    event_type,
    payload,
    *,
    schema_version,
    sequence_no,
    idempotency_key,
    payload_hash=None,
):
    return {
        "event_id": event_id,
        "schema_version": schema_version,
        "event_type": event_type,
        "event_type_version": "1.0",
        "timestamp": "2026-05-09T05:00:00+00:00",
        "sequence_no": sequence_no,
        "idempotency_key": idempotency_key,
        "source_trust": "verified",
        "signature_state": "valid",
        "data_classification": "internal",
        "redaction_policy": "summary_only",
        "payload_hash": payload_hash or f"sha256:{event_id}",
        "payload_ref": f"vault://{event_id}",
        "payload": payload,
    }


def runtime_batch(events, **overrides):
    batch = {
        "batch_id": "batch_1",
        "runtime_id": "runtime_local_1",
        "runtime_version": "1.0.0",
        "schema_version": "runtime.ingestion.v1",
        "sent_at": "2026-05-09T05:00:02+00:00",
        "events": events,
        "signature": "sig_batch",
    }
    batch.update(overrides)
    return batch


def test_ao31_ct_001_contract_registry_has_required_runtime_governance_entries():
    validate_contract_registry(CONTRACT_REGISTRY)

    runtime_run = get_contract("runtime_run.v1")
    trace_span = get_contract("trace_span.v1")

    assert runtime_run.domain_owner == "Agent Runtime"
    assert runtime_run.producer == "Runtime"
    assert "AgentOps" in runtime_run.consumers
    assert {"runtime_id", "run_id", "status"}.issubset(runtime_run.required_fields)
    assert "AO31-CT-003" in runtime_run.contract_tests

    assert trace_span.domain_owner == "Agent Runtime"
    assert {"trace_id", "span_id", "span_kind", "status_code"}.issubset(
        trace_span.required_fields
    )
    assert "AO31-CT-004" in trace_span.contract_tests


def test_ao31_ct_001_missing_owner_returns_contract_owner_required():
    broken = dict(CONTRACT_REGISTRY)
    broken["runtime_run.v1"] = get_contract("runtime_run.v1").with_changes(
        domain_owner=""
    )

    with pytest.raises(AgentOpsError) as exc:
        validate_contract_registry(broken)

    assert exc.value.error_code == "CONTRACT_OWNER_REQUIRED"


def test_ao31_ct_001_repeated_load_has_stable_hash():
    assert contract_registry_hash(CONTRACT_REGISTRY) == contract_registry_hash(
        CONTRACT_REGISTRY
    )


def test_ao31_ct_001_unknown_policy_decision_enum_is_rejected():
    with pytest.raises(AgentOpsError) as exc:
        validate_contract_value("policy_decision.v1", "decision", "defer")

    assert exc.value.error_code == "CONTRACT_ENUM_UNREGISTERED"


def test_ao31_ct_008_state_registry_has_plain_language_actions():
    validate_state_registry(STATE_REGISTRY)

    assert STATE_REGISTRY["running"].display_name == "运行中"
    assert STATE_REGISTRY["blocked"].primary_action == "查看原因"
    assert STATE_REGISTRY["trace_pending"].plain_language_explanation
    assert STATE_REGISTRY["degraded"].severity == "warning"


def test_ao31_ct_008_state_display_mismatch_is_rejected():
    broken = dict(STATE_REGISTRY)
    broken["blocked"] = STATE_REGISTRY["blocked"].with_changes(
        expected_display_name="已通过"
    )

    with pytest.raises(AgentOpsError) as exc:
        validate_state_registry(broken)

    assert exc.value.error_code == "STATE_DISPLAY_MISMATCH"


def test_ao31_ct_002_runtime_ingestion_batch_accepts_run_and_span():
    repository = InMemoryRepository()
    outcome = ingest_runtime_events(
        runtime_batch(
            [
                runtime_event(
                    "evt_run_1",
                    "runtime_run",
                    runtime_run_payload(),
                    schema_version="runtime_run.v1",
                    sequence_no=1,
                    idempotency_key="runtime:run_1",
                ),
                runtime_event(
                    "evt_span_1",
                    "trace_span",
                    trace_span_payload(),
                    schema_version="trace_span.v1",
                    sequence_no=2,
                    idempotency_key="runtime:span_1",
                ),
            ]
        ),
        repository,
    )

    assert outcome["accepted_count"] == 2
    assert outcome["deduplicated_count"] == 0
    assert outcome["rejected_count"] == 0
    assert repository.runtime_run_count() == 1
    assert repository.trace_span_count() == 1


def test_ao31_ct_002_runtime_ingestion_api_manifest_is_exposed():
    manifest = create_app()

    assert manifest["runtime_ingestion"] == "POST /v1/runtime/events"


def test_ao31_ct_002_runtime_ingestion_rejects_unsupported_schema():
    repository = InMemoryRepository()
    outcome = ingest_runtime_events(
        runtime_batch(
            [
                runtime_event(
                    "evt_schema_bad",
                    "runtime_run",
                    runtime_run_payload(),
                    schema_version="runtime_run.v99",
                    sequence_no=1,
                    idempotency_key="runtime:schema_bad",
                )
            ]
        ),
        repository,
    )

    assert outcome["rejected_count"] == 1
    assert outcome["item_results"][0]["error_code"] == "EVENT_SCHEMA_UNSUPPORTED"
    assert repository.runtime_run_count() == 0


def test_ao31_ct_002_runtime_ingestion_deduplicates_replay():
    repository = InMemoryRepository()
    batch = runtime_batch(
        [
            runtime_event(
                "evt_run_1",
                "runtime_run",
                runtime_run_payload(),
                schema_version="runtime_run.v1",
                sequence_no=1,
                idempotency_key="runtime:run_1",
            )
        ]
    )

    first = ingest_runtime_events(batch, repository)
    replay = ingest_runtime_events(batch, repository)

    assert first["accepted_count"] == 1
    assert replay["deduplicated_count"] == 1
    assert repository.runtime_run_count() == 1


def test_ao31_ct_003_runtime_run_fact_rejects_missing_required_field():
    repository = InMemoryRepository()
    payload = runtime_run_payload()
    payload.pop("run_id")

    outcome = ingest_runtime_events(
        runtime_batch(
            [
                runtime_event(
                    "evt_run_bad",
                    "runtime_run",
                    payload,
                    schema_version="runtime_run.v1",
                    sequence_no=1,
                    idempotency_key="runtime:run_bad",
                )
            ]
        ),
        repository,
    )

    assert outcome["rejected_count"] == 1
    assert outcome["item_results"][0]["error_code"] == "RUNTIME_RUN_INVALID"


def test_ao31_ct_004_trace_span_fact_rejects_unsupported_span_kind():
    repository = InMemoryRepository()
    outcome = ingest_runtime_events(
        runtime_batch(
            [
                runtime_event(
                    "evt_span_bad_kind",
                    "trace_span",
                    trace_span_payload(span_kind="database"),
                    schema_version="trace_span.v1",
                    sequence_no=1,
                    idempotency_key="runtime:span_bad_kind",
                )
            ]
        ),
        repository,
    )

    assert outcome["rejected_count"] == 1
    assert outcome["item_results"][0]["error_code"] == "TRACE_SPAN_KIND_UNSUPPORTED"


def test_ao31_ct_005_trace_parent_missing_enters_dlq():
    repository = InMemoryRepository()
    outcome = ingest_runtime_events(
        runtime_batch(
            [
                runtime_event(
                    "evt_child_span",
                    "trace_span",
                    trace_span_payload(
                        span_id="span_child", parent_span_id="span_missing"
                    ),
                    schema_version="trace_span.v1",
                    sequence_no=1,
                    idempotency_key="runtime:span_child",
                )
            ]
        ),
        repository,
    )

    assert outcome["dlq_count"] == 1
    assert outcome["item_results"][0]["error_code"] == "TRACE_PARENT_MISSING"
    assert repository.trace_span_count() == 0
