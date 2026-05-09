import json
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from threading import Thread

import pytest

from agentops.api.app import create_app
from agentops.api.runtime import get_runtime_run_detail, get_runtime_trace_timeline
from agentops.core.errors import AgentOpsError
from agentops.api.runtime import ingest_runtime_events
from agentops.api.server import create_http_handler
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


def canonical_runtime_event(
    event_id,
    event_type,
    payload,
    *,
    event_type_version,
    sequence_no,
    idempotency_key,
    payload_hash=None,
):
    event = runtime_event(
        event_id,
        event_type,
        payload,
        schema_version=event_type_version,
        sequence_no=sequence_no,
        idempotency_key=idempotency_key,
        payload_hash=payload_hash,
    )
    event.update(
        {
            "schema_version": "event_envelope.v1",
            "event_type_version": event_type_version,
            "integration_mode": "standalone",
            "enterprise_state": "not_detected",
            "signature": f"sig_{event_id}",
        }
    )
    event.pop("signature_state", None)
    return event


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


def _json_get(server: ThreadingHTTPServer, path: str):
    connection = HTTPConnection(
        server.server_address[0], server.server_address[1], timeout=5
    )
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        body = response.read().decode("utf-8")
        return response, json.loads(body) if body else {}
    finally:
        connection.close()


def _serve_repository(repository: InMemoryRepository):
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), create_http_handler(repository=repository)
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


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


def test_ao31_ct_002_runtime_ingestion_accepts_registered_event_envelope():
    repository = InMemoryRepository()
    outcome = ingest_runtime_events(
        runtime_batch(
            [
                canonical_runtime_event(
                    "evt_run_canonical",
                    "runtime_run",
                    runtime_run_payload(),
                    event_type_version="runtime_run.v1",
                    sequence_no=1,
                    idempotency_key="runtime:run_canonical",
                ),
                canonical_runtime_event(
                    "evt_span_canonical",
                    "trace_span",
                    trace_span_payload(),
                    event_type_version="trace_span.v1",
                    sequence_no=2,
                    idempotency_key="runtime:span_canonical",
                ),
            ]
        ),
        repository,
    )

    assert outcome["accepted_count"] == 2
    assert outcome["rejected_count"] == 0
    assert repository.runtime_run_count() == 1
    assert repository.trace_span_count() == 1


def test_ao31_ct_002_runtime_ingestion_api_manifest_is_exposed():
    manifest = create_app()

    assert manifest["runtime_ingestion"] == "POST /v1/runtime/events"
    assert manifest["runtime_run_detail"] == "GET /v1/runtime/runs/{run_id}"
    assert manifest["runtime_trace_timeline"] == "GET /v1/runtime/runs/{run_id}/trace"


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


def test_ao31_ct_002_runtime_ingestion_rejects_missing_batch_id():
    repository = InMemoryRepository()
    batch = runtime_batch(
        [
            runtime_event(
                "evt_run_missing_batch",
                "runtime_run",
                runtime_run_payload(),
                schema_version="runtime_run.v1",
                sequence_no=1,
                idempotency_key="runtime:missing_batch",
            )
        ]
    )
    batch.pop("batch_id")

    with pytest.raises(AgentOpsError) as exc:
        ingest_runtime_events(batch, repository)

    assert exc.value.error_code == "EVENT_SCHEMA_UNSUPPORTED"
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


def test_ao31_ct_002_runtime_ingestion_rejects_non_numeric_sequence_without_crash():
    repository = InMemoryRepository()
    outcome = ingest_runtime_events(
        runtime_batch(
            [
                runtime_event(
                    "evt_bad_sequence",
                    "runtime_run",
                    runtime_run_payload(),
                    schema_version="runtime_run.v1",
                    sequence_no="1",
                    idempotency_key="runtime:bad_sequence",
                ),
                runtime_event(
                    "evt_span_valid",
                    "trace_span",
                    trace_span_payload(),
                    schema_version="trace_span.v1",
                    sequence_no=2,
                    idempotency_key="runtime:span_valid",
                ),
            ]
        ),
        repository,
    )

    assert outcome["accepted_count"] == 1
    assert outcome["rejected_count"] == 1
    assert any(
        item.get("error_code") == "EVENT_SCHEMA_UNSUPPORTED"
        for item in outcome["item_results"]
    )
    assert repository.trace_span_count() == 1
    assert repository.runtime_run_count() == 0


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


def test_ao31_ct_004_trace_span_invalid_kind_wins_over_missing_parent_dlq():
    repository = InMemoryRepository()
    outcome = ingest_runtime_events(
        runtime_batch(
            [
                runtime_event(
                    "evt_span_bad_kind_missing_parent",
                    "trace_span",
                    trace_span_payload(
                        span_id="span_child",
                        parent_span_id="span_missing",
                        span_kind="database",
                    ),
                    schema_version="trace_span.v1",
                    sequence_no=1,
                    idempotency_key="runtime:span_bad_kind_missing_parent",
                )
            ]
        ),
        repository,
    )

    assert outcome["rejected_count"] == 1
    assert outcome["dlq_count"] == 0
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


def test_ao31_ct_005_invalid_incoming_parent_does_not_accept_child_span():
    repository = InMemoryRepository()
    outcome = ingest_runtime_events(
        runtime_batch(
            [
                runtime_event(
                    "evt_parent_invalid",
                    "trace_span",
                    trace_span_payload(span_id="span_parent", span_kind="database"),
                    schema_version="trace_span.v1",
                    sequence_no=1,
                    idempotency_key="runtime:span_parent_invalid",
                ),
                runtime_event(
                    "evt_child_span",
                    "trace_span",
                    trace_span_payload(
                        span_id="span_child", parent_span_id="span_parent"
                    ),
                    schema_version="trace_span.v1",
                    sequence_no=2,
                    idempotency_key="runtime:span_child_parent_invalid",
                ),
            ]
        ),
        repository,
    )

    assert outcome["rejected_count"] == 1
    assert outcome["dlq_count"] == 1
    assert [item["error_code"] for item in outcome["item_results"]] == [
        "TRACE_SPAN_KIND_UNSUPPORTED",
        "TRACE_PARENT_MISSING",
    ]
    assert repository.trace_span_count() == 0


def test_ao31_ct_006_run_detail_projection_explains_blocked_and_trace_pending():
    repository = InMemoryRepository()
    ingest_runtime_events(
        runtime_batch(
            [
                runtime_event(
                    "evt_blocked_run",
                    "runtime_run",
                    runtime_run_payload(
                        status="blocked",
                        terminal_reason="policy_block: deploy requires approval",
                    ),
                    schema_version="runtime_run.v1",
                    sequence_no=1,
                    idempotency_key="runtime:blocked_run",
                )
            ]
        ),
        repository,
    )

    detail = get_runtime_run_detail(repository, "run_1")

    assert detail["run"]["status"] == "blocked"
    assert detail["display_state"]["display_name"] == "已阻断"
    assert detail["next_action"] == "查看原因"
    assert detail["trace_state"] == "pending"
    assert detail["audit_id"] == "audit_runtime_run_run_1"


def test_ao31_ct_006_run_detail_selects_latest_mixed_attempt_types():
    repository = InMemoryRepository()
    ingest_runtime_events(
        runtime_batch(
            [
                runtime_event(
                    "evt_run_attempt_1",
                    "runtime_run",
                    runtime_run_payload(attempt_no=1, status="running"),
                    schema_version="runtime_run.v1",
                    sequence_no=1,
                    idempotency_key="runtime:run_attempt_1",
                ),
                runtime_event(
                    "evt_run_attempt_2",
                    "runtime_run",
                    runtime_run_payload(attempt_no="2", status="blocked"),
                    schema_version="runtime_run.v1",
                    sequence_no=2,
                    idempotency_key="runtime:run_attempt_2",
                ),
            ]
        ),
        repository,
    )

    detail = get_runtime_run_detail(repository, "run_1")

    assert detail["run"]["attempt_no"] == "2"
    assert detail["run"]["status"] == "blocked"


def test_ao31_ct_006_run_detail_scope_denied_is_safe():
    repository = InMemoryRepository()

    with pytest.raises(AgentOpsError) as exc:
        get_runtime_run_detail(repository, "run_1", allowed=False)

    assert exc.value.error_code == "RUN_DETAIL_SCOPE_DENIED"
    assert exc.value.denied_scope == "runtime.run.read"


def test_ao31_ct_007_trace_timeline_projection_is_ordered_and_summarized():
    repository = InMemoryRepository()
    ingest_runtime_events(
        runtime_batch(
            [
                runtime_event(
                    "evt_run_timeline",
                    "runtime_run",
                    runtime_run_payload(),
                    schema_version="runtime_run.v1",
                    sequence_no=1,
                    idempotency_key="runtime:run_timeline",
                ),
                runtime_event(
                    "evt_span_root",
                    "trace_span",
                    trace_span_payload(
                        span_id="span_root",
                        parent_span_id="",
                        span_kind="model",
                        start_time="2026-05-09T05:00:00+00:00",
                        end_time="2026-05-09T05:00:01+00:00",
                    ),
                    schema_version="trace_span.v1",
                    sequence_no=2,
                    idempotency_key="runtime:span_root",
                ),
                runtime_event(
                    "evt_span_tool",
                    "trace_span",
                    trace_span_payload(
                        span_id="span_tool",
                        parent_span_id="span_root",
                        span_kind="tool",
                        operation_name="tool.call",
                        start_time="2026-05-09T05:00:01+00:00",
                        end_time="2026-05-09T05:00:02+00:00",
                    ),
                    schema_version="trace_span.v1",
                    sequence_no=3,
                    idempotency_key="runtime:span_tool",
                ),
            ]
        ),
        repository,
    )

    timeline = get_runtime_trace_timeline(repository, "run_1")

    assert timeline["trace_id"] == "trace_1"
    assert [span["span_id"] for span in timeline["spans"]] == [
        "span_root",
        "span_tool",
    ]
    assert timeline["redaction_state"] == "summary_only"
    assert timeline["aggregate"]["token_usage"]["input"] == 24
    assert timeline["aggregate"]["cost_estimate"]["amount"] == 0.02


def test_ao31_ct_007_trace_timeline_ignores_malformed_numeric_aggregate_values():
    repository = InMemoryRepository()
    ingest_runtime_events(
        runtime_batch(
            [
                runtime_event(
                    "evt_run_timeline",
                    "runtime_run",
                    runtime_run_payload(),
                    schema_version="runtime_run.v1",
                    sequence_no=1,
                    idempotency_key="runtime:run_timeline",
                ),
                runtime_event(
                    "evt_span_bad_numbers",
                    "trace_span",
                    trace_span_payload(
                        token_usage={"input": "abc", "output": "5"},
                        cost_estimate={"amount": "bad", "currency": "USD"},
                    ),
                    schema_version="trace_span.v1",
                    sequence_no=2,
                    idempotency_key="runtime:span_bad_numbers",
                ),
            ]
        ),
        repository,
    )

    timeline = get_runtime_trace_timeline(repository, "run_1")

    assert timeline["aggregate"]["token_usage"] == {"input": 0, "output": 5}
    assert timeline["aggregate"]["cost_estimate"] == {
        "amount": 0.0,
        "currency": "USD",
    }


def test_ao31_ct_007_runtime_detail_and_trace_http_routes_match_manifest():
    repository = InMemoryRepository()
    ingest_runtime_events(
        runtime_batch(
            [
                runtime_event(
                    "evt_run_http",
                    "runtime_run",
                    runtime_run_payload(),
                    schema_version="runtime_run.v1",
                    sequence_no=1,
                    idempotency_key="runtime:run_http",
                ),
                runtime_event(
                    "evt_span_http",
                    "trace_span",
                    trace_span_payload(),
                    schema_version="trace_span.v1",
                    sequence_no=2,
                    idempotency_key="runtime:span_http",
                ),
            ]
        ),
        repository,
    )
    server, thread = _serve_repository(repository)
    try:
        detail_response, detail = _json_get(server, "/v1/runtime/runs/run_1")
        trace_response, trace = _json_get(server, "/v1/runtime/runs/run_1/trace")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert detail_response.status == 200
    assert detail["run"]["run_id"] == "run_1"
    assert trace_response.status == 200
    assert trace["run_id"] == "run_1"
    assert trace["spans"][0]["span_id"] == "span_root"


def test_ao31_ct_007_trace_timeline_unknown_run_is_not_found():
    repository = InMemoryRepository()

    with pytest.raises(AgentOpsError) as exc:
        get_runtime_trace_timeline(repository, "missing_run")

    assert exc.value.error_code == "RUNTIME_RUN_NOT_FOUND"


def test_ao31_ct_007_trace_timeline_http_route_returns_not_found_for_unknown_run():
    server, thread = _serve_repository(InMemoryRepository())
    try:
        trace_response, trace = _json_get(server, "/v1/runtime/runs/missing_run/trace")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert trace_response.status == 404
    assert trace["error_code"] == "RUNTIME_RUN_NOT_FOUND"


def test_ao31_ct_007_trace_timeline_raw_access_requires_permission():
    repository = InMemoryRepository()

    with pytest.raises(AgentOpsError) as exc:
        get_runtime_trace_timeline(repository, "run_1", request_raw=True)

    assert exc.value.error_code == "RAW_ACCESS_REQUIRED"
    assert exc.value.denied_scope == "runtime.trace.raw"
