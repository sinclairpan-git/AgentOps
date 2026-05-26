"""Runtime ingestion normalization for AO31."""

from __future__ import annotations

import math
from typing import Any

from agentops.core.errors import AgentOpsError
from agentops.core.runtime_contracts import get_contract, validate_contract_value
from agentops.storage.repository import InMemoryRepository


RUNTIME_BATCH_SCHEMA_VERSION = "runtime.ingestion.v1"

EVENT_TYPE_TO_CONTRACT = {
    "runtime_run": "runtime_run.v1",
    "trace_span": "trace_span.v1",
    "guardrail_result": "guardrail_result.v1",
    "sdlc_trace_event": "sdlc_trace_event.v1",
}

CANONICAL_EVENT_REQUIRED_FIELDS = get_contract("event_envelope.v1").required_fields | {
    "payload"
}

LEGACY_EVENT_REQUIRED_FIELDS = {
    "event_id",
    "schema_version",
    "event_type",
    "event_type_version",
    "timestamp",
    "sequence_no",
    "idempotency_key",
    "source_trust",
    "signature_state",
    "data_classification",
    "redaction_policy",
    "payload_hash",
    "payload_ref",
    "payload",
}


def ingest_runtime_batch(batch: Any, repository: InMemoryRepository) -> dict[str, Any]:
    _validate_batch(batch)
    incoming_span_ids = _incoming_valid_span_ids(batch["events"], repository)
    item_results: list[dict[str, Any]] = []
    accepted_count = 0
    deduplicated_count = 0
    stale_count = 0
    rejected_count = 0
    dlq_count = 0

    for event in sorted(batch["events"], key=_event_sort_key):
        result = _ingest_runtime_event(event, repository, incoming_span_ids)
        item_results.append(result)
        if result["status"] == "accepted":
            accepted_count += 1
        elif result["status"] == "deduplicated":
            deduplicated_count += 1
        elif result["status"] == "stale_ignored":
            stale_count += 1
        elif result["status"] == "dlq":
            dlq_count += 1
        else:
            rejected_count += 1

    receipt = {
        "schema_version": "runtime_outbox_receipt.v1",
        "batch_id": batch["batch_id"],
        "outbox_id": str(batch.get("outbox_id") or batch["batch_id"]),
        "producer": str(batch.get("producer") or "Runtime"),
        "replay_reason": str(batch.get("replay_reason") or "not_declared"),
        "outbox_state": _outbox_state(
            accepted_count=accepted_count,
            deduplicated_count=deduplicated_count,
            stale_count=stale_count,
            rejected_count=rejected_count,
            dlq_count=dlq_count,
        ),
        "accepted_count": accepted_count,
        "deduplicated_count": deduplicated_count,
        "stale_count": stale_count,
        "rejected_count": rejected_count,
        "dlq_count": dlq_count,
        "item_results": item_results,
        "audit_id": f"audit_runtime_ingestion_{batch['batch_id']}",
    }
    repository.write_runtime_outbox_receipt(receipt)
    return receipt


def _validate_batch(batch: Any) -> None:
    if not isinstance(batch, dict):
        raise AgentOpsError(
            "EVENT_SCHEMA_UNSUPPORTED",
            "Runtime ingestion batch must be object.",
        )
    if batch.get("schema_version") != RUNTIME_BATCH_SCHEMA_VERSION:
        raise AgentOpsError(
            "EVENT_SCHEMA_UNSUPPORTED",
            "Runtime ingestion batch schema is not supported.",
        )
    batch_id = batch.get("batch_id")
    if not isinstance(batch_id, str) or not batch_id.strip():
        raise AgentOpsError(
            "EVENT_SCHEMA_UNSUPPORTED",
            "Runtime batch requires batch_id.",
        )
    events = batch.get("events")
    if not isinstance(events, list):
        raise AgentOpsError(
            "EVENT_SCHEMA_UNSUPPORTED", "Runtime batch requires events."
        )


def _ingest_runtime_event(
    event: Any,
    repository: InMemoryRepository,
    incoming_span_ids: set[tuple[str, str, str, str]],
) -> dict[str, Any]:
    event_id = (
        event.get("event_id", "unknown") if isinstance(event, dict) else "unknown"
    )
    try:
        _validate_event_envelope(event)
        idempotency_outcome = repository.runtime_idempotency_outcome(
            event["idempotency_key"], event["payload_hash"]
        )
        if idempotency_outcome == "deduplicated":
            return _item_result(event_id, "deduplicated")
        if idempotency_outcome == "conflict":
            raise AgentOpsError(
                "EVENT_IDEMPOTENCY_CONFLICT",
                "Runtime event idempotency key maps to a different payload.",
            )

        event_type = event["event_type"]
        if event_type == "runtime_run":
            write_outcome = _write_runtime_run(event, repository)
        elif event_type == "trace_span":
            payload = _validated_trace_span_payload(event)
            parent_missing = _trace_parent_missing_for_payload(
                payload, repository, incoming_span_ids
            )
            if parent_missing:
                repository.write_runtime_dlq(
                    event,
                    error_code="TRACE_PARENT_MISSING",
                    message="Trace span parent was not found.",
                    state="trace_pending",
                    status="dlq",
                    retryable=True,
                )
                return _item_result(
                    event_id,
                    "dlq",
                    error_code="TRACE_PARENT_MISSING",
                    state="trace_pending",
                    retryable=True,
                )
            write_outcome = _write_trace_span(event, repository)
        elif event_type == "guardrail_result":
            write_outcome = _write_guardrail_result(event, repository)
        elif event_type == "sdlc_trace_event":
            payload = _sdlc_trace_span_payload(event)
            parent_missing = _trace_parent_missing_for_payload(
                payload, repository, incoming_span_ids
            )
            if parent_missing:
                repository.write_runtime_dlq(
                    event,
                    error_code="TRACE_PARENT_MISSING",
                    message="SDLC trace event parent was not found.",
                    state="trace_pending",
                    status="dlq",
                    retryable=True,
                )
                return _item_result(
                    event_id,
                    "dlq",
                    error_code="TRACE_PARENT_MISSING",
                    state="trace_pending",
                    retryable=True,
                )
            write_outcome = repository.write_trace_span_fact(event, payload)
        else:
            raise AgentOpsError(
                "EVENT_SCHEMA_UNSUPPORTED",
                "Runtime event type is not supported.",
            )

        repository.remember_runtime_idempotency(
            event["idempotency_key"], event_id, event["payload_hash"]
        )
        if write_outcome == "stale_ignored":
            return _item_result(
                event_id,
                "stale_ignored",
                state="out_of_order_ignored",
                retryable=False,
            )
        return _item_result(event_id, "accepted")
    except AgentOpsError as exc:
        if isinstance(event, dict):
            repository.write_runtime_dlq(
                event,
                error_code=exc.error_code,
                message=exc.message,
                state=_diagnostic_state(exc.error_code),
                status="rejected",
                retryable=exc.retryable,
            )
        return _item_result(
            event_id,
            "rejected",
            error_code=exc.error_code,
            state=_diagnostic_state(exc.error_code),
            retryable=exc.retryable,
        )


def _validate_event_envelope(event: dict[str, Any]) -> None:
    if not isinstance(event, dict):
        raise AgentOpsError(
            "EVENT_SCHEMA_UNSUPPORTED",
            "Runtime event envelope must be object.",
        )
    schema_version = event.get("schema_version")
    canonical_missing = CANONICAL_EVENT_REQUIRED_FIELDS - set(event)
    legacy_missing = LEGACY_EVENT_REQUIRED_FIELDS - set(event)
    if schema_version == "event_envelope.v1":
        if canonical_missing:
            raise AgentOpsError(
                "EVENT_SCHEMA_UNSUPPORTED",
                f"Runtime event is missing envelope fields: {sorted(canonical_missing)}",
            )
        _validate_canonical_event_envelope(event)
        return
    if schema_version in EVENT_TYPE_TO_CONTRACT.values():
        if legacy_missing:
            raise AgentOpsError(
                "EVENT_SCHEMA_UNSUPPORTED",
                f"Runtime event is missing envelope fields: {sorted(legacy_missing)}",
            )
        _validate_legacy_event_envelope(event)
        return
    raise AgentOpsError(
        "EVENT_SCHEMA_UNSUPPORTED",
        "Runtime event schema_version is not supported.",
    )


def _validate_canonical_event_envelope(event: dict[str, Any]) -> None:
    sequence_no = event.get("sequence_no")
    if not _sequence_no_is_numeric(sequence_no):
        raise AgentOpsError(
            "EVENT_SCHEMA_UNSUPPORTED",
            "Runtime event sequence_no must be numeric.",
        )
    _validate_envelope_enum_fields(event)
    if event.get("schema_version") != "event_envelope.v1":
        raise AgentOpsError(
            "EVENT_SCHEMA_UNSUPPORTED",
            "Runtime event envelope schema_version must be event_envelope.v1.",
        )
    if not str(event.get("signature") or "").strip():
        raise AgentOpsError(
            "EVENT_SIGNATURE_INVALID",
            "Runtime event signature is required.",
        )
    expected_contract = EVENT_TYPE_TO_CONTRACT.get(event["event_type"])
    if expected_contract is None or event["event_type_version"] != expected_contract:
        raise AgentOpsError(
            "EVENT_SCHEMA_UNSUPPORTED",
            "Runtime event event_type_version does not match event_type.",
        )


def _validate_legacy_event_envelope(event: dict[str, Any]) -> None:
    sequence_no = event.get("sequence_no")
    if not _sequence_no_is_numeric(sequence_no):
        raise AgentOpsError(
            "EVENT_SCHEMA_UNSUPPORTED",
            "Runtime event sequence_no must be numeric.",
        )
    validate_contract_value("event_envelope.v1", "source_trust", event["source_trust"])
    if event.get("signature_state") != "valid":
        raise AgentOpsError(
            "EVENT_SIGNATURE_INVALID",
            "Runtime event signature_state must be valid.",
        )
    expected_contract = EVENT_TYPE_TO_CONTRACT.get(event["event_type"])
    if expected_contract is None or event["schema_version"] != expected_contract:
        raise AgentOpsError(
            "EVENT_SCHEMA_UNSUPPORTED",
            "Runtime event schema_version does not match event_type.",
        )


def _validate_envelope_enum_fields(event: dict[str, Any]) -> None:
    entry = get_contract("event_envelope.v1")
    for field_name in entry.enum_fields:
        if field_name in event:
            validate_contract_value("event_envelope.v1", field_name, event[field_name])


def _write_runtime_run(event: dict[str, Any], repository: InMemoryRepository) -> str:
    payload = _validated_payload(event, "runtime_run.v1", "RUNTIME_RUN_INVALID")
    _validate_enum_fields("runtime_run.v1", payload)
    return repository.write_runtime_run_fact(event, payload)


def _write_trace_span(event: dict[str, Any], repository: InMemoryRepository) -> str:
    payload = _validated_trace_span_payload(event)
    return repository.write_trace_span_fact(event, payload)


def _write_guardrail_result(
    event: dict[str, Any], repository: InMemoryRepository
) -> str:
    payload = _validated_payload(
        event, "guardrail_result.v1", "GUARDRAIL_RESULT_INVALID"
    )
    _validate_enum_fields("guardrail_result.v1", payload)
    return repository.write_guardrail_result_fact(event, payload)


def _validated_trace_span_payload(event: dict[str, Any]) -> dict[str, Any]:
    payload = _validated_payload(event, "trace_span.v1", "TRACE_SPAN_INVALID")
    _validate_enum_fields("trace_span.v1", payload)
    return payload


def _sdlc_trace_span_payload(event: dict[str, Any]) -> dict[str, Any]:
    if (
        event.get("schema_version") != "event_envelope.v1"
        or event.get("integration_mode") != "enterprise_managed"
    ):
        raise AgentOpsError(
            "SDLC_TRACE_EVENT_INVALID",
            "SDLC trace bridge requires canonical enterprise_managed envelope.",
        )
    payload = _validated_payload(
        event, "sdlc_trace_event.v1", "SDLC_TRACE_EVENT_INVALID"
    )
    _validate_enum_fields("sdlc_trace_event.v1", payload)
    sdlc_event_type = str(payload["sdlc_event_type"])
    status = str(payload["status"])
    artifact_ref = str(payload.get("artifact_ref") or "")
    evidence_ref = str(payload.get("evidence_ref") or "")
    violation_code = str(payload.get("violation_code") or "")
    guard_result = str(
        payload.get("guard_result") or payload.get("task_guard_state") or ""
    )
    output_ref = artifact_ref or evidence_ref or str(event.get("payload_ref") or "")
    span = {
        "trace_id": str(payload["trace_id"]),
        "span_id": str(payload["span_id"]),
        "parent_span_id": str(payload.get("parent_span_id") or ""),
        "run_id": str(payload["run_id"]),
        "span_kind": _sdlc_span_kind(sdlc_event_type),
        "operation_name": _sdlc_operation_name(payload),
        "status_code": _sdlc_status_code(status),
        "start_time": str(payload["started_at"]),
        "end_time": str(payload["ended_at"]),
        "attempt_no": payload.get("attempt_no", 1),
        "input_ref": evidence_ref or str(event.get("payload_ref") or ""),
        "output_ref": output_ref,
        "token_usage": {},
        "cost_estimate": {},
        "grant_id": "",
        "guardrail_result_refs": [f"guard_result:{guard_result}"]
        if sdlc_event_type == "code_guard" and guard_result
        else [],
        "error_code": _sdlc_error_code(
            sdlc_event_type=sdlc_event_type,
            status=status,
            violation_code=violation_code,
            guard_result=guard_result,
        ),
        "retryable": status in {"started", "failed"},
    }
    span.update(_sdlc_summary_fields(payload, event))
    return span


def _validated_payload(
    event: dict[str, Any], contract_id: str, invalid_error_code: str
) -> dict[str, Any]:
    payload = event.get("payload")
    if not isinstance(payload, dict):
        raise AgentOpsError(invalid_error_code, "Runtime event payload must be object.")
    missing = get_contract(contract_id).required_fields - set(payload)
    if missing:
        raise AgentOpsError(
            invalid_error_code,
            f"{contract_id} payload missing fields: {sorted(missing)}.",
        )
    return payload


def _validate_enum_fields(contract_id: str, payload: dict[str, Any]) -> None:
    entry = get_contract(contract_id)
    for field_name in entry.enum_fields:
        if field_name not in payload:
            continue
        try:
            validate_contract_value(contract_id, field_name, payload[field_name])
        except AgentOpsError as exc:
            if contract_id == "trace_span.v1" and field_name == "span_kind":
                raise AgentOpsError(
                    "TRACE_SPAN_KIND_UNSUPPORTED",
                    "Trace span kind is not registered.",
                ) from exc
            raise


def _trace_parent_missing_for_payload(
    payload: dict[str, Any],
    repository: InMemoryRepository,
    incoming_span_ids: set[tuple[str, str, str, str]],
) -> bool:
    parent_span_id = str(payload.get("parent_span_id") or "").strip()
    if not parent_span_id:
        return False
    run_id = str(payload["run_id"])
    trace_id = str(payload["trace_id"])
    attempt_no = _attempt_identity(payload.get("attempt_no", 1))
    if repository.has_trace_span(
        run_id, trace_id, parent_span_id, attempt_no=attempt_no
    ):
        return False
    return (run_id, trace_id, attempt_no, parent_span_id) not in incoming_span_ids


def _incoming_valid_span_ids(
    events: list[dict[str, Any]], repository: InMemoryRepository
) -> set[tuple[str, str, str, str]]:
    candidates: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for event in events:
        if not isinstance(event, dict) or event.get("event_type") not in {
            "trace_span",
            "sdlc_trace_event",
        }:
            continue
        try:
            _validate_event_envelope(event)
            if event.get("event_type") == "trace_span":
                payload = _validated_trace_span_payload(event)
            else:
                payload = _sdlc_trace_span_payload(event)
        except AgentOpsError:
            continue
        run_id = payload.get("run_id")
        trace_id = payload.get("trace_id")
        span_id = payload.get("span_id")
        attempt_no = _attempt_identity(payload.get("attempt_no", 1))
        if run_id and trace_id and span_id:
            candidates[(str(run_id), str(trace_id), attempt_no, str(span_id))] = payload

    span_ids: set[tuple[str, str, str, str]] = set()
    changed = True
    while changed:
        changed = False
        for span_key, payload in candidates.items():
            if span_key in span_ids:
                continue
            run_id = str(payload["run_id"])
            trace_id = str(payload["trace_id"])
            attempt_no = _attempt_identity(payload.get("attempt_no", 1))
            parent_span_id = str(payload.get("parent_span_id") or "").strip()
            if (
                not parent_span_id
                or repository.has_trace_span(
                    run_id, trace_id, parent_span_id, attempt_no=attempt_no
                )
                or (run_id, trace_id, attempt_no, parent_span_id) in span_ids
            ):
                span_ids.add(span_key)
                changed = True
    return span_ids


def _event_sort_key(event: Any) -> tuple[int, float, str]:
    if not isinstance(event, dict):
        return (1, 0.0, "unknown")
    sequence_no = event.get("sequence_no")
    if _sequence_no_is_numeric(sequence_no):
        return (0, float(sequence_no), str(event.get("event_id", "")))
    return (1, 0.0, str(event.get("event_id", "")))


def _attempt_identity(value: Any) -> str:
    if isinstance(value, bool):
        return f"s:{value}"
    if isinstance(value, (int, float)):
        try:
            numeric_value = float(value)
        except OverflowError:
            return f"s:{value}"
        if math.isfinite(numeric_value):
            return f"n:{numeric_value:g}"
    if isinstance(value, str):
        try:
            numeric_value = float(value)
        except (OverflowError, ValueError):
            return f"s:{value}"
        if math.isfinite(numeric_value):
            return f"n:{numeric_value:g}"
    return f"s:{value}"


def _sequence_no_is_numeric(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(float(value))
    except OverflowError:
        return False


def _item_result(
    event_id: str,
    status: str,
    *,
    error_code: str | None = None,
    state: str | None = None,
    retryable: bool = False,
) -> dict[str, Any]:
    result: dict[str, Any] = {"event_id": event_id, "status": status}
    if state:
        result["state"] = state
    if error_code:
        result["error_code"] = error_code
        result["retryable"] = retryable
    elif state:
        result["retryable"] = retryable
    return result


def _outbox_state(
    *,
    accepted_count: int,
    deduplicated_count: int,
    stale_count: int,
    rejected_count: int,
    dlq_count: int,
) -> str:
    if rejected_count and not (
        accepted_count or deduplicated_count or stale_count or dlq_count
    ):
        return "rejected"
    if rejected_count or dlq_count or stale_count:
        return "delivered_with_diagnostics"
    if deduplicated_count and not accepted_count:
        return "replayed"
    return "delivered"


def _diagnostic_state(error_code: str) -> str:
    if error_code == "EVENT_SIGNATURE_INVALID":
        return "signature_failed"
    if error_code in {
        "EVENT_SCHEMA_UNSUPPORTED",
        "CONTRACT_ENUM_UNREGISTERED",
        "RUNTIME_RUN_INVALID",
        "TRACE_SPAN_INVALID",
        "TRACE_SPAN_KIND_UNSUPPORTED",
        "GUARDRAIL_RESULT_INVALID",
        "SDLC_TRACE_EVENT_INVALID",
    }:
        return "schema_rejected"
    if error_code == "TRACE_PARENT_MISSING":
        return "trace_pending"
    return "degraded"


def _sdlc_span_kind(sdlc_event_type: str) -> str:
    return {
        "stage": "workflow",
        "gate": "guardrail",
        "verification": "tool",
        "artifact": "artifact",
        "violation": "guardrail",
        "executable_task": "system",
        "code_guard": "guardrail",
    }[sdlc_event_type]


def _sdlc_status_code(status: str) -> str:
    return {
        "started": "waiting",
        "passed": "ok",
        "failed": "error",
        "blocked": "blocked",
        "skipped": "unset",
        "emitted": "ok",
    }[status]


def _sdlc_operation_name(payload: dict[str, Any]) -> str:
    event_type = str(payload.get("sdlc_event_type") or "event")
    stage_name = str(payload.get("stage_name") or "unknown")
    return f"ai_sdlc.{event_type}.{stage_name}"


def _sdlc_error_code(
    *,
    sdlc_event_type: str,
    status: str,
    violation_code: str,
    guard_result: str,
) -> str:
    if sdlc_event_type == "violation":
        return violation_code
    if sdlc_event_type == "code_guard" and (
        status == "blocked" or guard_result == "blocked"
    ):
        return violation_code or "TASK_GUARD_BLOCKED"
    return ""


def _sdlc_summary_fields(
    payload: dict[str, Any], event: dict[str, Any]
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "sdlc_event_id": str(payload.get("sdlc_event_id") or ""),
        "sdlc_event_type": str(payload.get("sdlc_event_type") or ""),
        "stage_name": str(payload.get("stage_name") or ""),
        "status": str(payload.get("status") or ""),
        "payload_ref": str(event.get("payload_ref") or ""),
        "source_trust": str(event.get("source_trust") or ""),
        "integration_mode": str(event.get("integration_mode") or ""),
        "enterprise_state": str(event.get("enterprise_state") or ""),
        "data_classification": str(event.get("data_classification") or "summary"),
        "redaction_policy": str(event.get("redaction_policy") or "summary_only"),
    }
    for field_name in (
        "workitem",
        "executable_task_id",
        "task_title",
        "task_guard_state",
        "guard_result",
        "blocking_reason",
        "adapter_diagnostic_state",
        "evidence_ref",
    ):
        if field_name in payload:
            summary[field_name] = payload[field_name]
    return summary
