"""Ingestion API contract implementation."""

from __future__ import annotations

from typing import Any

from agentops.core.envelope import SIGNATURE_TEST_EVENT_TYPE, evidence_mode_for, validate_event_envelope
from agentops.core.errors import AgentOpsError
from agentops.storage.repository import InMemoryRepository


def ingest_events_batch(events: list[dict[str, Any]], repository: InMemoryRepository) -> dict[str, list]:
    accepted: list[str] = []
    deduplicated: list[str] = []
    rejected: list[dict] = []

    for event in events:
        if not isinstance(event, dict):
            rejected.append(
                {
                    "event_id": "unknown",
                    "error_code": "EVENT_SCHEMA_INVALID",
                    "retryable": False,
                    "human_action_required": True,
                }
            )
            continue
        try:
            validate_event_envelope(event)
            signature_test_bootstrap_id = None
            if event["event_type"] == SIGNATURE_TEST_EVENT_TYPE:
                signature_test_bootstrap_id = repository.validate_signature_test_event(event)
            outcome = repository.write_event(event, evidence_mode=evidence_mode_for(event))
            if outcome == "deduplicated":
                deduplicated.append(event["event_id"])
            else:
                accepted.append(event["event_id"])
                if signature_test_bootstrap_id is not None:
                    repository.mark_signature_test_verified(signature_test_bootstrap_id, event["event_id"])
        except AgentOpsError as exc:
            rejected.append(
                {
                    "event_id": event.get("event_id", "unknown"),
                    "error_code": exc.error_code,
                    "retryable": exc.retryable,
                    "human_action_required": True,
                }
            )

    return {"accepted": accepted, "rejected": rejected, "deduplicated": deduplicated}
