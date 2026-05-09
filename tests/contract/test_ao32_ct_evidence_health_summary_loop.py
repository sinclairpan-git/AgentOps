from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from agentops.api.agent_store import sync_agent_store_metadata
from agentops.api.runtime import (
    get_runtime_evidence_summary,
    get_runtime_run_detail,
    get_runtime_trace_timeline,
    ingest_runtime_events,
)
from agentops.api.store_summary import get_agent_store_summary_for_run
from agentops.core.errors import AgentOpsError
from agentops.core.runtime_summary import build_runtime_health_summary
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
        "status": "succeeded",
        "terminal_reason": "",
    }
    payload.update(overrides)
    return payload


def trace_span_payload(**overrides):
    payload = {
        "trace_id": "trace_1",
        "span_id": "span_model",
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


def runtime_event(event_id, event_type, payload, *, sequence_no, idempotency_key):
    return {
        "event_id": event_id,
        "schema_version": "event_envelope.v1",
        "event_type": event_type,
        "event_type_version": f"{event_type}.v1",
        "timestamp": "2026-05-09T05:00:00+00:00",
        "integration_mode": "standalone",
        "enterprise_state": "not_detected",
        "sequence_no": sequence_no,
        "idempotency_key": idempotency_key,
        "source_trust": "verified",
        "signature": f"sig_{event_id}",
        "data_classification": "internal",
        "redaction_policy": "summary_only",
        "payload_hash": f"sha256:{event_id}",
        "payload_ref": f"vault://{event_id}",
        "payload": payload,
    }


def runtime_batch(events):
    return {
        "batch_id": "batch_ao32",
        "runtime_id": "runtime_local_1",
        "runtime_version": "1.0.0",
        "schema_version": "runtime.ingestion.v1",
        "sent_at": "2026-05-09T05:00:02+00:00",
        "events": events,
        "signature": "sig_batch",
    }


def write_runtime_run(repository: InMemoryRepository, **overrides) -> None:
    run_id = str(overrides.get("run_id", "run_1"))
    attempt_no = int(overrides.get("attempt_no", 1))
    sequence_no = int(overrides.pop("sequence_no", 1))
    event_id = f"evt_{run_id}" if attempt_no == 1 else f"evt_{run_id}_a{attempt_no}"
    ingest_runtime_events(
        runtime_batch(
            [
                runtime_event(
                    event_id,
                    "runtime_run",
                    runtime_run_payload(**overrides),
                    sequence_no=sequence_no,
                    idempotency_key=f"runtime:{run_id}:attempt:{attempt_no}",
                )
            ]
        ),
        repository,
    )


def write_full_trace(
    repository: InMemoryRepository, *, run_id: str = "run_1", attempt_no: int = 1
) -> None:
    spans = [
        trace_span_payload(
            run_id=run_id,
            attempt_no=attempt_no,
            span_id="span_model",
            span_kind="model",
            operation_name="model.call",
        ),
        trace_span_payload(
            run_id=run_id,
            attempt_no=attempt_no,
            span_id="span_tool",
            parent_span_id="span_model",
            span_kind="tool",
            operation_name="tool.invoke",
        ),
        trace_span_payload(
            run_id=run_id,
            attempt_no=attempt_no,
            span_id="span_guardrail",
            parent_span_id="span_tool",
            span_kind="guardrail",
            operation_name="guardrail.check",
        ),
        trace_span_payload(
            run_id=run_id,
            attempt_no=attempt_no,
            span_id="span_artifact",
            parent_span_id="span_guardrail",
            span_kind="artifact",
            operation_name="artifact.write",
            output_ref="vault://artifact/ref",
        ),
    ]
    ingest_runtime_events(
        runtime_batch(
            [
                runtime_event(
                    f"evt_{run_id}_{span['span_id']}",
                    "trace_span",
                    span,
                    sequence_no=index,
                    idempotency_key=(
                        f"runtime:{run_id}:attempt:{attempt_no}:{span['span_id']}"
                    ),
                )
                for index, span in enumerate(spans, start=10)
            ]
        ),
        repository,
    )


def register_agent(repository: InMemoryRepository) -> None:
    sync_agent_store_metadata(
        repository,
        {
            "agent_id": "agent.ai-sdlc",
            "version": "1.0.0",
            "skills": [{"skill_id": "refine"}],
        },
    )


def set_runtime_run_received_at(
    repository: InMemoryRepository, run_id: str, attempt_no: int, received_at: str
) -> None:
    for record in repository.runtime_runs.values():
        if record.get("run_id") == run_id and record.get("attempt_no") == attempt_no:
            record["received_at"] = received_at


def test_ao32_ct_001_evidence_summary_outputs_l5_for_complete_runtime_trace():
    repository = InMemoryRepository()
    write_runtime_run(repository)
    write_full_trace(repository)

    summary = get_runtime_evidence_summary(repository, "run_1")

    assert summary["schema_version"] == "evidence_summary.v1"
    assert summary["run_id"] == "run_1"
    assert summary["trace_id"] == "trace_1"
    assert summary["evidence_level"] == "L5"
    assert summary["confidence"] == 1.0
    assert summary["completeness"] == 1.0
    assert summary["missing_dimensions"] == []
    assert summary["redaction_state"] == "summary_only"
    assert summary["raw_access_state"] == "summary_only"
    assert summary["source_event_ids"] == [
        "evt_run_1",
        "evt_run_1_span_model",
        "evt_run_1_span_tool",
        "evt_run_1_span_guardrail",
        "evt_run_1_span_artifact",
    ]


def test_ao32_ct_001_evidence_summary_degrades_when_trace_is_pending():
    repository = InMemoryRepository()
    write_runtime_run(repository)

    summary = get_runtime_evidence_summary(repository, "run_1")

    assert summary["evidence_level"] == "L3"
    assert summary["confidence"] < 1.0
    assert "trace_span" in summary["missing_dimensions"]
    assert summary["degraded_reason"] == "trace_pending"


def test_ao32_ct_002_raw_access_requires_evidence_vault_approval():
    repository = InMemoryRepository()
    write_runtime_run(repository)
    write_full_trace(repository)

    with pytest.raises(AgentOpsError) as exc:
        get_runtime_evidence_summary(repository, "run_1", request_raw=True)

    assert exc.value.error_code == "RAW_ACCESS_REQUIRED"
    assert exc.value.audit_id == "audit_runtime_evidence_run_1"
    assert exc.value.denied_scope == "runtime.evidence.raw"
    assert exc.value.request_access_url == "/v1/evidence/raw-access-requests"


def test_ao32_ct_003_health_summary_aggregates_recent_runtime_runs():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_success", status="succeeded")
    write_runtime_run(
        repository,
        run_id="run_failed",
        status="failed",
        terminal_reason="tool_error",
        sequence_no=2,
    )
    write_runtime_run(
        repository,
        run_id="run_blocked",
        status="blocked",
        terminal_reason="policy_block",
        sequence_no=3,
    )
    write_full_trace(repository, run_id="run_success")

    summary = build_runtime_health_summary(repository, "agent.ai-sdlc", "1.0.0")

    assert summary["schema_version"] == "health_summary.v1"
    assert summary["sample_size"] == 3
    assert summary["success_rate"] == pytest.approx(1 / 3)
    assert summary["failure_rate"] == pytest.approx(1 / 3)
    assert summary["policy_block_count"] == 1
    assert summary["recommended_action"] == "disable_recommended"


def test_ao32_ct_003_health_summary_handles_empty_sample_without_dividing_by_zero():
    repository = InMemoryRepository()

    summary = build_runtime_health_summary(repository, "agent.ai-sdlc", "1.0.0")

    assert summary["sample_size"] == 0
    assert summary["success_rate"] == 0.0
    assert summary["failure_rate"] == 0.0
    assert summary["evidence_completeness"] == 0.0
    assert summary["recommended_action"] == "watching"


def test_ao32_ct_003_health_summary_zero_window_is_empty():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_success", status="succeeded")

    summary = build_runtime_health_summary(
        repository, "agent.ai-sdlc", "1.0.0", window_limit=0
    )

    assert summary["sample_size"] == 0
    assert summary["calculation_window"]["run_ids"] == []
    assert summary["recommended_action"] == "watching"


def test_ao32_ct_003_health_summary_scores_each_run_attempt_independently():
    repository = InMemoryRepository()
    write_runtime_run(
        repository,
        run_id="run_retry",
        attempt_no=1,
        status="failed",
        terminal_reason="tool_error",
    )
    write_runtime_run(
        repository,
        run_id="run_retry",
        attempt_no=2,
        status="succeeded",
        sequence_no=2,
    )
    write_full_trace(repository, run_id="run_retry", attempt_no=2)

    summary = build_runtime_health_summary(repository, "agent.ai-sdlc", "1.0.0")

    assert summary["sample_size"] == 2
    assert summary["evidence_completeness"] == pytest.approx(0.5)
    assert summary["recommended_action"] == "disable_recommended"


def test_ao32_ct_003_health_summary_window_uses_received_recency_not_attempt_number():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_old_retry", attempt_no=9, status="failed")
    write_runtime_run(
        repository,
        run_id="run_new",
        attempt_no=1,
        status="succeeded",
        sequence_no=2,
    )
    set_runtime_run_received_at(
        repository, "run_old_retry", 9, "2026-05-09T05:00:00+00:00"
    )
    set_runtime_run_received_at(repository, "run_new", 1, "2026-05-09T06:00:00+00:00")

    summary = build_runtime_health_summary(
        repository, "agent.ai-sdlc", "1.0.0", window_limit=1
    )

    assert summary["calculation_window"]["run_ids"] == ["run_new"]
    assert summary["success_rate"] == 1.0


def test_ao32_ct_004_store_summary_returns_runtime_evidence_health_and_ops_link():
    repository = InMemoryRepository()
    register_agent(repository)
    write_runtime_run(repository)
    write_full_trace(repository)

    summary = get_agent_store_summary_for_run(
        repository, "agent.ai-sdlc", "1.0.0", "run_1"
    )

    assert summary["schema_version"] == "agentops.agent_store.echo.v1"
    assert summary["agent_id"] == "agent.ai-sdlc"
    assert summary["agentops_fact_owner"] == "AgentOps"
    assert summary["agent_store_consumer_boundary"]["mode"] == "display_only"
    assert summary["evidence_summary"]["schema_version"] == "evidence_summary.v1"
    assert summary["health_summary"]["schema_version"] == "health_summary.v1"
    assert summary["recommended_action"] == "usable"
    assert summary["ops_detail_url"] == "/agentops/runtime/runs/run_1"


def test_ao32_ct_004_store_summary_marks_unregistered_runtime_run_as_suspected():
    repository = InMemoryRepository()
    write_runtime_run(repository)
    write_full_trace(repository)

    summary = get_agent_store_summary_for_run(
        repository, "agent.ai-sdlc", "1.0.0", "run_1"
    )

    assert summary["metadata_state"] == "unregistered"
    assert summary["run_audit"]["registration_state"] == "suspected"


def test_ao32_ct_004_store_summary_rejects_runtime_run_target_mismatch():
    repository = InMemoryRepository()
    register_agent(repository)
    write_runtime_run(repository)

    with pytest.raises(AgentOpsError) as exc:
        get_agent_store_summary_for_run(repository, "agent.other", "1.0.0", "run_1")

    assert exc.value.error_code == "STORE_SUMMARY_RUN_MISMATCH"


def test_ao32_ct_005_store_summary_marks_expired_summary_as_expired():
    repository = InMemoryRepository()
    register_agent(repository)
    write_runtime_run(repository)
    write_full_trace(repository)
    now = datetime(2026, 5, 9, 12, 0, tzinfo=UTC)
    expired_at = now - timedelta(minutes=1)

    summary = get_agent_store_summary_for_run(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        "run_1",
        now=now,
        summary_valid_until=expired_at,
    )

    assert summary["summary_state"] == "expired"
    assert summary["recommended_action"] == "expired"
    assert summary["health_summary"]["recommended_action"] == "expired"


def test_ao32_ct_006_runtime_to_store_summary_end_to_end_without_raw_leaks():
    repository = InMemoryRepository()
    register_agent(repository)
    write_runtime_run(repository)
    write_full_trace(repository)

    run_detail = get_runtime_run_detail(repository, "run_1")
    timeline = get_runtime_trace_timeline(repository, "run_1")
    evidence = get_runtime_evidence_summary(repository, "run_1")
    store_summary = get_agent_store_summary_for_run(
        repository, "agent.ai-sdlc", "1.0.0", "run_1"
    )

    assert run_detail["run"]["run_id"] == "run_1"
    assert timeline["run_id"] == "run_1"
    assert evidence["run_id"] == "run_1"
    assert store_summary["deep_links"]["run_id"] == "run_1"
    assert store_summary["evidence_summary"]["run_id"] == "run_1"
    assert store_summary["health_summary"]["calculation_window"]["run_ids"] == ["run_1"]

    serialized = json.dumps(store_summary, ensure_ascii=False)
    assert "raw_payload" not in serialized
    assert "prompt" not in serialized
    assert "token_secret" not in serialized
    assert "credential_secret" not in serialized
    assert "device_key" not in serialized
