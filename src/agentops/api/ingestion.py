"""Ingestion API contract implementation."""

from __future__ import annotations

from typing import Any

from agentops.core.envelope import evidence_mode_for, validate_event_envelope
from agentops.core.errors import AgentOpsError
from agentops.storage.repository import InMemoryRepository


def ingest_events_batch(events: list[dict[str, Any]], repository: InMemoryRepository) -> dict[str, list]:
    accepted: list[str] = []
    deduplicated: list[str] = []
    rejected: list[dict] = []

    for event in events:
        try:
            validate_event_envelope(event)
            outcome = repository.write_event(event, evidence_mode=evidence_mode_for(event))
            if outcome == "deduplicated":
                deduplicated.append(event["event_id"])
            else:
                accepted.append(event["event_id"])
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
