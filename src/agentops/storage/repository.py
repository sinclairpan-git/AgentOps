"""In-memory repository for the stage-1 trusted loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class InMemoryRepository:
    raw_events: dict[str, dict[str, Any]] = field(default_factory=dict)
    idempotency_index: dict[str, str] = field(default_factory=dict)
    imported_events: dict[str, dict[str, Any]] = field(default_factory=dict)
    bootstrap_sessions: dict[str, dict[str, Any]] = field(default_factory=dict)
    credentials_by_bootstrap: dict[str, dict[str, Any]] = field(default_factory=dict)
    used_bootstrap_nonces: set[str] = field(default_factory=set)

    def write_event(self, event: dict[str, Any], evidence_mode: str = "managed") -> str:
        event_id = event["event_id"]
        idempotency_key = event["idempotency_key"]
        if idempotency_key in self.idempotency_index:
            return "deduplicated"

        record = dict(event)
        record["received_at"] = utc_now()
        record["evidence_mode"] = evidence_mode
        self.raw_events[event_id] = record
        self.idempotency_index[idempotency_key] = event_id
        if evidence_mode == "imported":
            self.imported_events[event_id] = record
        return "accepted"

    def add_bootstrap_session(self, session: dict[str, Any]) -> None:
        self.bootstrap_sessions[session["bootstrap_id"]] = dict(session)

    def get_bootstrap_session(self, bootstrap_id: str) -> dict[str, Any] | None:
        return self.bootstrap_sessions.get(bootstrap_id)

    def store_credentials(self, bootstrap_id: str, credentials: dict[str, Any]) -> dict[str, Any]:
        if bootstrap_id not in self.credentials_by_bootstrap:
            self.credentials_by_bootstrap[bootstrap_id] = dict(credentials)
        return dict(self.credentials_by_bootstrap[bootstrap_id])

    def mark_bootstrap_nonces(self, *nonces: str) -> None:
        self.used_bootstrap_nonces.update(nonces)
