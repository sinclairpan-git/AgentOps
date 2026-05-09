"""Runtime ingestion normalization for AO31."""

from __future__ import annotations

from typing import Any

from agentops.core.errors import AgentOpsError
from agentops.core.runtime_contracts import get_contract, validate_contract_value
from agentops.storage.repository import InMemoryRepository


RUNTIME_BATCH_SCHEMA_VERSION = "runtime.ingestion.v1"

EVENT_TYPE_TO_CONTRACT = {
    "runtime_run": "runtime_run.v1",
    "trace_span": "trace_span.v1",
}

EVENT_REQUIRED_FIELDS = {
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


def ingest_runtime_batch(
    batch: dict[str, Any], repository: InMemoryRepository
) -> dict[str, Any]:
    _validate_batch(batch)
    incoming_span_ids = _incoming_span_ids(batch["events"])
    item_results: list[dict[str, Any]] = []
    accepted_count = 0
    deduplicated_count = 0
    rejected_count = 0
    dlq_count = 0

    for event in sorted(batch["events"], key=lambda item: item.get("sequence_no", 0)):
        result = _ingest_runtime_event(event, repository, incoming_span_ids)
        item_results.append(result)
        if result["status"] == "accepted":
            accepted_count += 1
        elif result["status"] == "deduplicated":
            deduplicated_count += 1
        elif result["status"] == "dlq":
            dlq_count += 1
        else:
            rejected_count += 1

    return {
        "batch_id": batch["batch_id"],
        "accepted_count": accepted_count,
        "deduplicated_count": deduplicated_count,
        "rejected_count": rejected_count,
        "dlq_count": dlq_count,
        "item_results": item_results,
        "audit_id": f"audit_runtime_ingestion_{batch['batch_id']}",
    }


def _validate_batch(batch: dict[str, Any]) -> None:
    if batch.get("schema_version") != RUNTIME_BATCH_SCHEMA_VERSION:
        raise AgentOpsError(
            "EVENT_SCHEMA_UNSUPPORTED",
            "Runtime ingestion batch schema is not supported.",
        )
    events = batch.get("events")
    if not isinstance(events, list):
        raise AgentOpsError(
            "EVENT_SCHEMA_UNSUPPORTED", "Runtime batch requires events."
        )


def _ingest_runtime_event(
    event: dict[str, Any],
    repository: InMemoryRepository,
    incoming_span_ids: set[tuple[str, str]],
) -> dict[str, Any]:
    event_id = event.get("event_id", "unknown")
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
            _write_runtime_run(event, repository)
        elif event_type == "trace_span":
            parent_missing = _trace_parent_missing(event, repository, incoming_span_ids)
            if parent_missing:
                repository.write_runtime_dlq(
                    event,
                    error_code="TRACE_PARENT_MISSING",
                    message="Trace span parent was not found.",
                )
                return _item_result(
                    event_id,
                    "dlq",
                    error_code="TRACE_PARENT_MISSING",
                    retryable=True,
                )
            _write_trace_span(event, repository)
        else:
            raise AgentOpsError(
                "EVENT_SCHEMA_UNSUPPORTED",
                "Runtime event type is not supported.",
            )

        repository.remember_runtime_idempotency(
            event["idempotency_key"], event_id, event["payload_hash"]
        )
        return _item_result(event_id, "accepted")
    except AgentOpsError as exc:
        return _item_result(
            event_id,
            "rejected",
            error_code=exc.error_code,
            retryable=exc.retryable,
        )


def _validate_event_envelope(event: dict[str, Any]) -> None:
    missing = EVENT_REQUIRED_FIELDS - set(event)
    if missing:
        raise AgentOpsError(
            "EVENT_SCHEMA_UNSUPPORTED",
            f"Runtime event is missing envelope fields: {sorted(missing)}",
        )
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


def _write_runtime_run(event: dict[str, Any], repository: InMemoryRepository) -> None:
    payload = _validated_payload(event, "runtime_run.v1", "RUNTIME_RUN_INVALID")
    _validate_enum_fields("runtime_run.v1", payload)
    repository.write_runtime_run_fact(event, payload)


def _write_trace_span(event: dict[str, Any], repository: InMemoryRepository) -> None:
    payload = _validated_payload(event, "trace_span.v1", "TRACE_SPAN_INVALID")
    _validate_enum_fields("trace_span.v1", payload)
    repository.write_trace_span_fact(event, payload)


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


def _trace_parent_missing(
    event: dict[str, Any],
    repository: InMemoryRepository,
    incoming_span_ids: set[tuple[str, str]],
) -> bool:
    payload = _validated_payload(event, "trace_span.v1", "TRACE_SPAN_INVALID")
    parent_span_id = str(payload.get("parent_span_id") or "").strip()
    if not parent_span_id:
        return False
    trace_id = payload["trace_id"]
    if repository.has_trace_span(trace_id, parent_span_id):
        return False
    return (trace_id, parent_span_id) not in incoming_span_ids


def _incoming_span_ids(events: list[dict[str, Any]]) -> set[tuple[str, str]]:
    span_ids: set[tuple[str, str]] = set()
    for event in events:
        if event.get("event_type") != "trace_span":
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        trace_id = payload.get("trace_id")
        span_id = payload.get("span_id")
        if trace_id and span_id:
            span_ids.add((str(trace_id), str(span_id)))
    return span_ids


def _item_result(
    event_id: str,
    status: str,
    *,
    error_code: str | None = None,
    retryable: bool = False,
) -> dict[str, Any]:
    result: dict[str, Any] = {"event_id": event_id, "status": status}
    if error_code:
        result["error_code"] = error_code
        result["retryable"] = retryable
    return result
