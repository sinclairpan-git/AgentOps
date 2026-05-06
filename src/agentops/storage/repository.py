"""In-memory repository for the stage-1 trusted loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import RLock
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class InMemoryRepository:
    _lock: RLock = field(default_factory=RLock, repr=False)
    raw_events: dict[str, dict[str, Any]] = field(default_factory=dict)
    idempotency_index: dict[str, str] = field(default_factory=dict)
    imported_events: dict[str, dict[str, Any]] = field(default_factory=dict)
    bootstrap_sessions: dict[str, dict[str, Any]] = field(default_factory=dict)
    credentials_by_bootstrap: dict[str, dict[str, Any]] = field(default_factory=dict)
    used_bootstrap_nonces: set[str] = field(default_factory=set)
    approvals: dict[str, dict[str, Any]] = field(default_factory=dict)
    approval_decisions: dict[str, dict[str, Any]] = field(default_factory=dict)
    grants: dict[str, dict[str, Any]] = field(default_factory=dict)
    grant_consumptions: dict[str, dict[str, Any]] = field(default_factory=dict)
    raw_access_requests: dict[str, dict[str, Any]] = field(default_factory=dict)
    raw_access_grants: dict[str, dict[str, Any]] = field(default_factory=dict)
    agent_store_agents: dict[str, dict[str, Any]] = field(default_factory=dict)
    agent_store_skills: dict[str, dict[str, Any]] = field(default_factory=dict)

    def write_event(self, event: dict[str, Any], evidence_mode: str = "managed") -> str:
        event_id = event["event_id"]
        idempotency_key = event["idempotency_key"]
        with self._lock:
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

    def raw_event_records(self) -> tuple[dict[str, Any], ...]:
        with self._lock:
            return tuple(dict(event) for event in self.raw_events.values())

    def approval_records(self) -> tuple[dict[str, Any], ...]:
        with self._lock:
            return tuple(dict(approval) for approval in self.approvals.values())

    def grant_records(self) -> tuple[dict[str, Any], ...]:
        with self._lock:
            return tuple(dict(grant) for grant in self.grants.values())

    def raw_event_count(self) -> int:
        with self._lock:
            return len(self.raw_events)

    def add_bootstrap_session(self, session: dict[str, Any]) -> None:
        with self._lock:
            self.bootstrap_sessions[session["bootstrap_id"]] = dict(session)

    def get_bootstrap_session(self, bootstrap_id: str) -> dict[str, Any] | None:
        with self._lock:
            session = self.bootstrap_sessions.get(bootstrap_id)
            return dict(session) if session else None

    def store_credentials(self, bootstrap_id: str, credentials: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            if bootstrap_id not in self.credentials_by_bootstrap:
                self.credentials_by_bootstrap[bootstrap_id] = dict(credentials)
            return dict(self.credentials_by_bootstrap[bootstrap_id])

    def mark_bootstrap_nonces(self, *nonces: str) -> None:
        with self._lock:
            self.used_bootstrap_nonces.update(nonces)

    def store_approval(self, approval: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self.approvals[approval["approval_id"]] = dict(approval)
            return dict(approval)

    def get_approval(self, approval_id: str) -> dict[str, Any] | None:
        with self._lock:
            approval = self.approvals.get(approval_id)
            return dict(approval) if approval else None

    def store_approval_decision(self, decision: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self.approval_decisions[decision["approval_decision_id"]] = dict(decision)
            return dict(decision)

    def store_grant(self, grant: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self.grants[grant["grant_id"]] = dict(grant)
            return dict(grant)

    def get_grant(self, grant_id: str) -> dict[str, Any] | None:
        with self._lock:
            grant = self.grants.get(grant_id)
            return dict(grant) if grant else None

    def update_grant(self, grant: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self.grants[grant["grant_id"]] = dict(grant)
            return dict(grant)

    def store_grant_consumption(self, consumption: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self.grant_consumptions[consumption["consumption_id"]] = dict(consumption)
            return dict(consumption)

    def store_raw_access_request(self, request: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self.raw_access_requests[request["request_id"]] = dict(request)
            return dict(request)

    def get_raw_access_request(self, request_id: str) -> dict[str, Any] | None:
        with self._lock:
            request = self.raw_access_requests.get(request_id)
            return dict(request) if request else None

    def store_raw_access_grant(self, grant: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self.raw_access_grants[grant["raw_grant_id"]] = dict(grant)
            return dict(grant)

    def upsert_agent_store_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        agent_id = str(metadata["agent_id"])
        version = str(metadata.get("version") or metadata.get("agent_version") or "unknown")
        record = {
            **metadata,
            "agent_id": agent_id,
            "version": version,
            "synced_at": str(metadata.get("synced_at") or utc_now()),
        }
        with self._lock:
            self.agent_store_agents[f"{agent_id}@{version}"] = dict(record)
            for skill in record.get("skills", []):
                if isinstance(skill, dict):
                    skill_id = str(skill.get("skill_id") or skill.get("name") or "")
                    if skill_id:
                        self.agent_store_skills[f"{agent_id}@{version}:{skill_id}"] = {
                            **skill,
                            "skill_id": skill_id,
                            "agent_id": agent_id,
                            "version": version,
                        }
            return dict(record)

    def get_agent_store_metadata(self, agent_id: str, version: str) -> dict[str, Any] | None:
        with self._lock:
            record = self.agent_store_agents.get(f"{agent_id}@{version}")
            return dict(record) if record else None

    def has_agent_store_skill(self, agent_id: str, version: str, skill_id: str) -> bool:
        with self._lock:
            return f"{agent_id}@{version}:{skill_id}" in self.agent_store_skills

    def agent_store_metadata_records(self) -> tuple[dict[str, Any], ...]:
        with self._lock:
            return tuple(dict(record) for record in self.agent_store_agents.values())
