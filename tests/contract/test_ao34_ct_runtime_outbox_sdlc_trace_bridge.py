from agentops.api.runtime import (
    get_runtime_evidence_summary,
    get_runtime_trace_timeline,
    ingest_runtime_events,
)
from agentops.core.runtime_contracts import get_contract
from agentops.storage.repository import InMemoryRepository
from tests.contract.test_ao31_ct_runtime_governance_foundation import (
    canonical_runtime_event,
    runtime_batch,
    runtime_event,
    runtime_run_payload,
)


def sdlc_trace_payload(**overrides):
    payload = {
        "sdlc_event_id": "sdlc_stage_refine",
        "run_id": "run_1",
        "trace_id": "trace_sdlc_1",
        "span_id": "stage_refine",
        "parent_span_id": "",
        "attempt_no": 1,
        "sdlc_event_type": "stage",
        "stage_name": "refine",
        "status": "passed",
        "started_at": "2026-05-09T05:00:00+00:00",
        "ended_at": "2026-05-09T05:00:01+00:00",
        "artifact_ref": "",
        "evidence_ref": "vault://sdlc/stage/refine",
        "violation_code": "",
    }
    payload.update(overrides)
    return payload


def canonical_sdlc_event(
    event_id,
    payload,
    *,
    sequence_no,
    idempotency_key,
    integration_mode="enterprise_managed",
):
    event = canonical_runtime_event(
        event_id,
        "sdlc_trace_event",
        payload,
        event_type_version="sdlc_trace_event.v1",
        sequence_no=sequence_no,
        idempotency_key=idempotency_key,
    )
    event["integration_mode"] = integration_mode
    event["enterprise_state"] = "managed"
    return event


def test_ao34_ct_001_contract_registry_has_outbox_and_sdlc_bridge_entries():
    outbox = get_contract("runtime_outbox_receipt.v1")
    sdlc = get_contract("sdlc_trace_event.v1")

    assert outbox.domain_owner == "AgentOps"
    assert {
        "batch_id",
        "outbox_id",
        "producer",
        "accepted_count",
        "deduplicated_count",
        "stale_count",
        "rejected_count",
        "dlq_count",
        "item_results",
        "audit_id",
    }.issubset(outbox.required_fields)
    assert "AO34-CT-001" in outbox.contract_tests

    assert sdlc.domain_owner == "Ai_AutoSDLC"
    assert sdlc.producer == "Ai_AutoSDLC"
    assert "AgentOps" in sdlc.consumers
    assert {"stage", "gate", "verification", "artifact", "violation"}.issubset(
        sdlc.enum_fields["sdlc_event_type"]
    )


def test_ao34_ct_002_outbox_replay_deduplicates_and_stale_sequence_is_ignored():
    repository = InMemoryRepository()
    newer = runtime_event(
        "evt_run_sequence_3",
        "runtime_run",
        runtime_run_payload(status="succeeded"),
        schema_version="runtime_run.v1",
        sequence_no=3,
        idempotency_key="runtime:run_1:sequence_3",
    )
    older = runtime_event(
        "evt_run_sequence_2",
        "runtime_run",
        runtime_run_payload(status="running"),
        schema_version="runtime_run.v1",
        sequence_no=2,
        idempotency_key="runtime:run_1:sequence_2",
    )

    first = ingest_runtime_events(
        runtime_batch(
            [newer],
            outbox_id="outbox_runtime_1",
            producer="Runtime",
            replay_reason="initial_delivery",
        ),
        repository,
    )
    stale = ingest_runtime_events(
        runtime_batch(
            [older],
            batch_id="batch_stale",
            outbox_id="outbox_runtime_1",
            producer="Runtime",
            replay_reason="network_replay",
        ),
        repository,
    )
    replay = ingest_runtime_events(
        runtime_batch(
            [older],
            batch_id="batch_stale_replay",
            outbox_id="outbox_runtime_1",
            producer="Runtime",
            replay_reason="network_replay",
        ),
        repository,
    )

    assert first["outbox_id"] == "outbox_runtime_1"
    assert first["accepted_count"] == 1
    assert stale["accepted_count"] == 0
    assert stale["stale_count"] == 1
    assert stale["item_results"] == [
        {
            "event_id": "evt_run_sequence_2",
            "status": "stale_ignored",
            "state": "out_of_order_ignored",
            "retryable": False,
        }
    ]
    assert replay["deduplicated_count"] == 1
    assert repository.get_runtime_run_fact("run_1")["status"] == "succeeded"


def test_ao34_ct_003_rejected_events_persist_summary_only_diagnostics():
    repository = InMemoryRepository()
    missing_signature = canonical_runtime_event(
        "evt_sdlc_signature_missing",
        "runtime_run",
        runtime_run_payload(),
        event_type_version="runtime_run.v1",
        sequence_no=1,
        idempotency_key="runtime:signature_missing",
    )
    missing_signature["signature"] = ""
    unsupported_schema = runtime_event(
        "evt_runtime_schema_bad",
        "runtime_run",
        runtime_run_payload(),
        schema_version="runtime_run.v99",
        sequence_no=2,
        idempotency_key="runtime:schema_bad",
    )

    outcome = ingest_runtime_events(
        runtime_batch([missing_signature, unsupported_schema]), repository
    )

    assert outcome["rejected_count"] == 2
    assert outcome["item_results"][0]["state"] == "signature_failed"
    assert outcome["item_results"][1]["state"] == "schema_rejected"
    assert repository.runtime_dlq_count() == 2
    diagnostics = list(repository.runtime_dlq.values())
    assert {diagnostic["event_id"] for diagnostic in diagnostics} == {
        "evt_sdlc_signature_missing",
        "evt_runtime_schema_bad",
    }
    for diagnostic in diagnostics:
        assert "event" not in diagnostic
        assert "payload" not in diagnostic
        assert diagnostic["payload_hash"].startswith("sha256:")


def test_ao34_ct_003_rejected_and_dlq_batch_keeps_retryable_outbox_state():
    repository = InMemoryRepository()
    missing_signature = canonical_runtime_event(
        "evt_signature_missing_mixed",
        "runtime_run",
        runtime_run_payload(),
        event_type_version="runtime_run.v1",
        sequence_no=1,
        idempotency_key="runtime:mixed_signature_missing",
    )
    missing_signature["signature"] = ""
    missing_parent_span = runtime_event(
        "evt_span_missing_parent_mixed",
        "trace_span",
        {
            "trace_id": "trace_1",
            "span_id": "span_child",
            "parent_span_id": "span_missing",
            "run_id": "run_1",
            "span_kind": "tool",
            "operation_name": "tool.call",
            "status_code": "waiting",
            "start_time": "2026-05-09T05:00:00+00:00",
            "end_time": "2026-05-09T05:00:01+00:00",
            "attempt_no": 1,
            "input_ref": "sha256:input",
            "output_ref": "sha256:output",
            "token_usage": {},
            "cost_estimate": {},
            "grant_id": "",
            "guardrail_result_refs": [],
            "error_code": "",
            "retryable": True,
        },
        schema_version="trace_span.v1",
        sequence_no=2,
        idempotency_key="runtime:mixed_missing_parent",
    )

    outcome = ingest_runtime_events(
        runtime_batch([missing_signature, missing_parent_span]), repository
    )

    assert outcome["accepted_count"] == 0
    assert outcome["rejected_count"] == 1
    assert outcome["dlq_count"] == 1
    assert outcome["outbox_state"] == "delivered_with_diagnostics"
    assert outcome["item_results"][1]["status"] == "dlq"
    assert outcome["item_results"][1]["retryable"] is True


def test_ao34_ct_004_sdlc_trace_event_maps_to_trace_spans_and_evidence_inputs():
    repository = InMemoryRepository()
    events = [
        runtime_event(
            "evt_run_sdlc",
            "runtime_run",
            runtime_run_payload(
                execution_environment="ci",
                trigger_source="ai_sdlc",
                status="succeeded",
            ),
            schema_version="runtime_run.v1",
            sequence_no=1,
            idempotency_key="runtime:sdlc:run",
        ),
        canonical_sdlc_event(
            "evt_sdlc_stage",
            sdlc_trace_payload(),
            sequence_no=2,
            idempotency_key="sdlc:stage",
        ),
        canonical_sdlc_event(
            "evt_sdlc_gate",
            sdlc_trace_payload(
                sdlc_event_id="sdlc_gate_constraints",
                span_id="gate_constraints",
                parent_span_id="stage_refine",
                sdlc_event_type="gate",
                stage_name="verify",
                status="passed",
                evidence_ref="vault://sdlc/gate/constraints",
            ),
            sequence_no=3,
            idempotency_key="sdlc:gate",
        ),
        canonical_sdlc_event(
            "evt_sdlc_verification",
            sdlc_trace_payload(
                sdlc_event_id="sdlc_pytest",
                span_id="verification_pytest",
                parent_span_id="gate_constraints",
                sdlc_event_type="verification",
                stage_name="verify",
                status="passed",
                evidence_ref="vault://sdlc/verification/pytest",
            ),
            sequence_no=4,
            idempotency_key="sdlc:verification",
        ),
        canonical_sdlc_event(
            "evt_sdlc_artifact",
            sdlc_trace_payload(
                sdlc_event_id="sdlc_artifact_report",
                span_id="artifact_report",
                parent_span_id="verification_pytest",
                sdlc_event_type="artifact",
                stage_name="close",
                status="emitted",
                artifact_ref="sha256:artifact-report",
                evidence_ref="vault://sdlc/artifact/report",
            ),
            sequence_no=5,
            idempotency_key="sdlc:artifact",
        ),
        canonical_sdlc_event(
            "evt_sdlc_violation",
            sdlc_trace_payload(
                sdlc_event_id="sdlc_violation_p1",
                span_id="violation_p1",
                parent_span_id="artifact_report",
                sdlc_event_type="violation",
                stage_name="review",
                status="blocked",
                evidence_ref="vault://sdlc/violation/p1",
                violation_code="AI_SDLC_P1_REVIEW_FINDING",
            ),
            sequence_no=6,
            idempotency_key="sdlc:violation",
        ),
    ]

    outcome = ingest_runtime_events(runtime_batch(events), repository)
    timeline = get_runtime_trace_timeline(repository, "run_1")
    evidence = get_runtime_evidence_summary(repository, "run_1")

    assert outcome["accepted_count"] == 6
    assert repository.trace_span_count() == 5
    spans_by_id = {span["span_id"]: span for span in timeline["spans"]}
    assert spans_by_id["stage_refine"]["span_kind"] == "workflow"
    assert spans_by_id["gate_constraints"]["span_kind"] == "guardrail"
    assert spans_by_id["verification_pytest"]["span_kind"] == "tool"
    assert spans_by_id["artifact_report"]["span_kind"] == "artifact"
    assert spans_by_id["violation_p1"]["span_kind"] == "guardrail"
    assert spans_by_id["artifact_report"]["output_ref"] == "sha256:artifact-report"
    assert spans_by_id["violation_p1"]["status_code"] == "blocked"
    assert "payload" not in spans_by_id["stage_refine"]
    assert "raw_payload" not in spans_by_id["stage_refine"]
    assert "evt_sdlc_artifact" in evidence["source_event_ids"]
    assert "trace_span" not in evidence["missing_dimensions"]
    assert "artifact_span" not in evidence["missing_dimensions"]


def test_ao34_ct_005_sdlc_trace_bridge_requires_enterprise_managed_envelope():
    repository = InMemoryRepository()
    event = canonical_sdlc_event(
        "evt_sdlc_standalone",
        sdlc_trace_payload(),
        sequence_no=1,
        idempotency_key="sdlc:standalone",
        integration_mode="standalone",
    )

    outcome = ingest_runtime_events(runtime_batch([event]), repository)

    assert outcome["rejected_count"] == 1
    assert outcome["item_results"][0]["error_code"] == "SDLC_TRACE_EVENT_INVALID"
    assert outcome["item_results"][0]["state"] == "schema_rejected"
    assert repository.trace_span_count() == 0
