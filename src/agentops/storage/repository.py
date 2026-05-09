"""In-memory repository for the stage-1 trusted loop."""

from __future__ import annotations

import math
from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import RLock
from typing import Any

from agentops.core.errors import AgentOpsError


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _runtime_number_sort_value(value: Any) -> float:
    if isinstance(value, bool):
        return -1.0
    if isinstance(value, (int, float)):
        try:
            numeric_value = float(value)
        except OverflowError:
            return -1.0
        return numeric_value if math.isfinite(numeric_value) else -1.0
    if isinstance(value, str):
        try:
            numeric_value = float(value)
        except (OverflowError, ValueError):
            return -1.0
        return numeric_value if math.isfinite(numeric_value) else -1.0
    return -1.0


def _runtime_attempt_sort_key(record: dict[str, Any]) -> tuple[float, float, str]:
    value = record.get("attempt_no", 0)
    attempt_no = _runtime_number_sort_value(value)
    sequence_no = _runtime_number_sort_value(record.get("sequence_no", 0))
    return (attempt_no, sequence_no, str(record.get("received_at", "")))


def _runtime_attempt_matches(actual: Any, expected: Any) -> bool:
    actual_sort_value = _runtime_number_sort_value(actual)
    expected_sort_value = _runtime_number_sort_value(expected)
    if actual_sort_value >= 0 and expected_sort_value >= 0:
        return actual_sort_value == expected_sort_value
    return str(actual) == str(expected)


def _runtime_time_sort_value(value: Any) -> tuple[int, float, str]:
    raw_value = str(value or "")
    try:
        parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    except ValueError:
        return (1, 0.0, raw_value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    timestamp = parsed.astimezone(UTC).timestamp()
    return (0, timestamp, raw_value)


@dataclass
class InMemoryRepository:
    _lock: RLock = field(default_factory=RLock, repr=False)
    raw_events: dict[str, dict[str, Any]] = field(default_factory=dict)
    idempotency_index: dict[str, str] = field(default_factory=dict)
    imported_events: dict[str, dict[str, Any]] = field(default_factory=dict)
    bootstrap_sessions: dict[str, dict[str, Any]] = field(default_factory=dict)
    credentials_by_bootstrap: dict[str, dict[str, Any]] = field(default_factory=dict)
    credential_identities_by_bootstrap: dict[str, dict[str, Any]] = field(
        default_factory=dict
    )
    credential_issue_idempotency: dict[str, dict[str, Any]] = field(
        default_factory=dict
    )
    used_bootstrap_nonces: set[str] = field(default_factory=set)
    approvals: dict[str, dict[str, Any]] = field(default_factory=dict)
    approval_decisions: dict[str, dict[str, Any]] = field(default_factory=dict)
    grants: dict[str, dict[str, Any]] = field(default_factory=dict)
    grant_consumptions: dict[str, dict[str, Any]] = field(default_factory=dict)
    raw_access_requests: dict[str, dict[str, Any]] = field(default_factory=dict)
    raw_access_grants: dict[str, dict[str, Any]] = field(default_factory=dict)
    agent_store_agents: dict[str, dict[str, Any]] = field(default_factory=dict)
    agent_store_skills: dict[str, dict[str, Any]] = field(default_factory=dict)
    runtime_runs: dict[str, dict[str, Any]] = field(default_factory=dict)
    trace_spans: dict[tuple[str, str, str], dict[str, Any]] = field(
        default_factory=dict
    )
    runtime_idempotency_index: dict[str, dict[str, str]] = field(default_factory=dict)
    runtime_dlq: dict[str, dict[str, Any]] = field(default_factory=dict)

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

    def runtime_run_count(self) -> int:
        with self._lock:
            return len(self.runtime_runs)

    def trace_span_count(self) -> int:
        with self._lock:
            return len(self.trace_spans)

    def runtime_dlq_count(self) -> int:
        with self._lock:
            return len(self.runtime_dlq)

    def get_runtime_run_fact(self, run_id: str) -> dict[str, Any] | None:
        with self._lock:
            candidates = [
                record
                for record in self.runtime_runs.values()
                if record.get("run_id") == run_id
            ]
            if not candidates:
                return None
            latest = sorted(candidates, key=_runtime_attempt_sort_key)[-1]
            return deepcopy(latest)

    def trace_span_records_for_run(
        self, run_id: str, *, attempt_no: Any | None = None
    ) -> tuple[dict[str, Any], ...]:
        with self._lock:
            spans = [
                deepcopy(record)
                for record in self.trace_spans.values()
                if record.get("run_id") == run_id
                and (
                    attempt_no is None
                    or _runtime_attempt_matches(record.get("attempt_no"), attempt_no)
                )
            ]
            return tuple(
                sorted(
                    spans,
                    key=lambda item: (
                        _runtime_time_sort_value(item.get("start_time")),
                        str(item.get("span_id", "")),
                    ),
                )
            )

    def runtime_idempotency_outcome(
        self, idempotency_key: str, payload_hash: str
    ) -> str:
        with self._lock:
            existing = self.runtime_idempotency_index.get(idempotency_key)
            if existing is None:
                return "new"
            if existing.get("payload_hash") != payload_hash:
                return "conflict"
            return "deduplicated"

    def remember_runtime_idempotency(
        self, idempotency_key: str, event_id: str, payload_hash: str
    ) -> None:
        with self._lock:
            self.runtime_idempotency_index[idempotency_key] = {
                "event_id": event_id,
                "payload_hash": payload_hash,
            }

    def write_runtime_run_fact(
        self, event: dict[str, Any], payload: dict[str, Any]
    ) -> None:
        record = {
            **deepcopy(payload),
            "event_id": event["event_id"],
            "sequence_no": event.get("sequence_no", 0),
            "received_at": utc_now(),
        }
        key = f"{payload['run_id']}:{payload.get('attempt_no', 1)}"
        with self._lock:
            existing = self.runtime_runs.get(key)
            if existing and _runtime_attempt_sort_key(
                record
            ) <= _runtime_attempt_sort_key(existing):
                return
            self.runtime_runs[key] = record

    def write_trace_span_fact(
        self, event: dict[str, Any], payload: dict[str, Any]
    ) -> None:
        record = {
            **deepcopy(payload),
            "event_id": event["event_id"],
            "sequence_no": event.get("sequence_no", 0),
            "received_at": utc_now(),
        }
        key = self._trace_span_key(
            payload["run_id"], payload["trace_id"], payload["span_id"]
        )
        with self._lock:
            existing = self.trace_spans.get(key)
            if existing and _runtime_number_sort_value(
                record.get("sequence_no", 0)
            ) <= _runtime_number_sort_value(existing.get("sequence_no", 0)):
                return
            self.trace_spans[key] = record

    def has_trace_span(self, run_id: str, trace_id: str, span_id: str) -> bool:
        with self._lock:
            return self._trace_span_key(run_id, trace_id, span_id) in self.trace_spans

    def write_runtime_dlq(
        self, event: dict[str, Any], *, error_code: str, message: str
    ) -> None:
        with self._lock:
            self.runtime_dlq[event.get("event_id", "unknown")] = {
                "event": deepcopy(event),
                "error_code": error_code,
                "message": message,
                "received_at": utc_now(),
            }

    @staticmethod
    def _trace_span_key(
        run_id: str, trace_id: str, span_id: str
    ) -> tuple[str, str, str]:
        return (str(run_id), str(trace_id), str(span_id))

    def add_bootstrap_session(self, session: dict[str, Any]) -> None:
        with self._lock:
            self.bootstrap_sessions[session["bootstrap_id"]] = dict(session)

    def remove_unissued_bootstrap_session(self, bootstrap_id: str) -> None:
        with self._lock:
            if bootstrap_id not in self.credentials_by_bootstrap:
                self.bootstrap_sessions.pop(bootstrap_id, None)

    def get_bootstrap_session(self, bootstrap_id: str) -> dict[str, Any] | None:
        with self._lock:
            session = self.bootstrap_sessions.get(bootstrap_id)
            return dict(session) if session else None

    def get_credentials(self, bootstrap_id: str) -> dict[str, Any] | None:
        with self._lock:
            credentials = self.credentials_by_bootstrap.get(bootstrap_id)
            return dict(credentials) if credentials else None

    @contextmanager
    def credential_reissue_transaction(self) -> Iterator[None]:
        with self._lock:
            yield

    def credential_bootstrap_records(self) -> tuple[dict[str, Any], ...]:
        with self._lock:
            return tuple(
                {
                    "bootstrap_session": dict(session),
                    "credentials": dict(self.credentials_by_bootstrap[bootstrap_id])
                    if bootstrap_id in self.credentials_by_bootstrap
                    else None,
                }
                for bootstrap_id, session in sorted(self.bootstrap_sessions.items())
            )

    def store_credentials(
        self,
        bootstrap_id: str,
        credentials: dict[str, Any],
        *,
        handoff_identity: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            if bootstrap_id not in self.credentials_by_bootstrap:
                self.credentials_by_bootstrap[bootstrap_id] = dict(credentials)
                if bootstrap_id in self.bootstrap_sessions:
                    session = dict(self.bootstrap_sessions[bootstrap_id])
                    session["status"] = "credential_issued"
                    session["bootstrap_status"] = "credential_issued"
                    session["credential_id"] = credentials["credential_id"]
                    session["token_id"] = credentials["token_id"]
                    session["device_key_id"] = credentials["device_key_id"]
                    self.bootstrap_sessions[bootstrap_id] = session
                if handoff_identity is not None:
                    self.credential_identities_by_bootstrap[bootstrap_id] = dict(
                        handoff_identity
                    )
                if idempotency_key is not None and handoff_identity is not None:
                    self.credential_issue_idempotency[idempotency_key] = dict(
                        handoff_identity
                    )
            return dict(self.credentials_by_bootstrap[bootstrap_id])

    def revoke_credentials(
        self, bootstrap_id: str, revocation: dict[str, Any]
    ) -> dict[str, Any]:
        with self._lock:
            credentials = self.credentials_by_bootstrap.get(bootstrap_id)
            session = self.bootstrap_sessions.get(bootstrap_id)
            if not credentials or not session:
                raise AgentOpsError(
                    "CREDENTIAL_REVOCATION_NOT_FOUND",
                    "Credential status does not exist for this bootstrap.",
                )

            revoked_credentials = {
                **credentials,
                "status": "revoked",
                "bootstrap_status": "revoked",
                "next_action": "reissue_credential",
                "revocation_id": revocation["revocation_id"],
                "revoked_at": revocation["revoked_at"],
                "revoked_by": revocation["revoked_by"],
                "revocation_reason": revocation["reason"],
                "revocation_scope": revocation["scope"],
            }
            revoked_session = {
                **session,
                "status": "revoked",
                "bootstrap_status": "revoked",
                "revocation_id": revocation["revocation_id"],
                "revoked_at": revocation["revoked_at"],
                "revoked_by": revocation["revoked_by"],
                "revocation_reason": revocation["reason"],
                "revocation_scope": revocation["scope"],
            }
            self.credentials_by_bootstrap[bootstrap_id] = revoked_credentials
            self.bootstrap_sessions[bootstrap_id] = revoked_session
            return dict(revoked_credentials)

    def mark_credentials_reissued(
        self, bootstrap_id: str, reissue: dict[str, Any]
    ) -> dict[str, Any]:
        with self._lock:
            credentials = self.credentials_by_bootstrap.get(bootstrap_id)
            session = self.bootstrap_sessions.get(bootstrap_id)
            if not credentials or not session:
                raise AgentOpsError(
                    "CREDENTIAL_REISSUE_NOT_FOUND",
                    "Source credential status does not exist for this bootstrap.",
                )
            reissue_fields = {
                "revocation_resolution": "reissued",
                "reissue_id": reissue["reissue_id"],
                "reissued_at": reissue["reissued_at"],
                "reissued_by": reissue["reissued_by"],
                "reissue_reason": reissue["reissue_reason"],
                "reissued_bootstrap_id": reissue["reissued_bootstrap_id"],
                "reissued_credential_id": reissue["reissued_credential_id"],
                "reissued_token_id": reissue["reissued_token_id"],
                "reissued_device_key_id": reissue["reissued_device_key_id"],
                "reissued_credential_snapshot": deepcopy(
                    reissue["reissued_credential_snapshot"]
                ),
            }
            self.credentials_by_bootstrap[bootstrap_id] = {
                **credentials,
                **reissue_fields,
            }
            self.bootstrap_sessions[bootstrap_id] = {**session, **reissue_fields}
            return dict(self.credentials_by_bootstrap[bootstrap_id])

    def validate_known_revocation_state(self, event: dict[str, Any]) -> None:
        if event.get("integration_mode") != "enterprise_managed":
            return
        ingestion_token = event.get("ingestion_token")
        installation_id = event.get("installation_id")
        device_id = event.get("device_id")
        with self._lock:
            matched_known_credential = False
            for credentials in self.credentials_by_bootstrap.values():
                token_matches = ingestion_token not in (
                    None,
                    "",
                ) and ingestion_token == credentials.get("token_id")
                identity_matches = (
                    installation_id not in (None, "")
                    and device_id not in (None, "")
                    and installation_id == credentials.get("installation_id")
                    and device_id == credentials.get("device_id")
                )
                if not token_matches and not identity_matches:
                    continue
                if credentials.get("status") == "revoked":
                    if (
                        identity_matches
                        and not token_matches
                        and self._replacement_chain_token_matches(
                            credentials, ingestion_token
                        )
                    ):
                        continue
                    raise AgentOpsError(
                        "EVENT_CREDENTIAL_REVOKED",
                        "enterprise_managed event uses a revoked credential.",
                    )
                matched_known_credential = True
            if matched_known_credential:
                return

    def _replacement_chain_token_matches(
        self, credentials: dict[str, Any], ingestion_token: str | None
    ) -> bool:
        if (
            ingestion_token in (None, "")
            or credentials.get("revocation_resolution") != "reissued"
        ):
            return False
        seen_bootstrap_ids: set[str] = set()
        next_bootstrap_id = str(credentials.get("reissued_bootstrap_id") or "")
        while next_bootstrap_id and next_bootstrap_id not in seen_bootstrap_ids:
            seen_bootstrap_ids.add(next_bootstrap_id)
            replacement = self.credentials_by_bootstrap.get(next_bootstrap_id)
            if not replacement:
                return False
            if replacement.get("status") != "revoked":
                return replacement.get(
                    "status"
                ) == "active" and ingestion_token == replacement.get("token_id")
            if replacement.get("revocation_resolution") != "reissued":
                return False
            next_bootstrap_id = str(replacement.get("reissued_bootstrap_id") or "")
        return False

    def record_credential_issue_idempotency(
        self, idempotency_key: str, handoff_identity: dict[str, Any]
    ) -> None:
        with self._lock:
            self.credential_issue_idempotency[idempotency_key] = dict(handoff_identity)

    def mark_bootstrap_nonces(self, *nonces: str) -> None:
        with self._lock:
            self.used_bootstrap_nonces.update(nonces)

    def validate_signature_test_event(self, event: dict[str, Any]) -> str:
        payload = event["payload"]
        bootstrap_id = payload["bootstrap_id"]
        with self._lock:
            credentials = self.credentials_by_bootstrap.get(bootstrap_id)
            if not credentials:
                raise AgentOpsError(
                    "SIGNATURE_TEST_CREDENTIAL_NOT_FOUND",
                    "No credential has been issued for this bootstrap.",
                )
            if credentials.get("status") == "revoked":
                raise AgentOpsError(
                    "EVENT_CREDENTIAL_REVOKED",
                    "signature_test_event uses a revoked credential.",
                )
            if (
                credentials.get("status") != "active"
                or event.get("credential_status") != "active"
            ):
                raise AgentOpsError(
                    "EVENT_CREDENTIAL_INACTIVE",
                    "signature_test_event requires an active credential.",
                )
            if event.get("device_key_status") != "active":
                raise AgentOpsError(
                    "EVENT_DEVICE_KEY_INACTIVE",
                    "signature_test_event requires an active device key.",
                )
            if event.get("ingestion_token") != credentials.get(
                "token_id"
            ) or payload.get("token_id") != credentials.get("token_id"):
                raise AgentOpsError(
                    "EVENT_INGESTION_TOKEN_MISMATCH",
                    "signature_test_event token does not match issued credential.",
                )
            if payload.get("credential_id") != credentials.get("credential_id"):
                raise AgentOpsError(
                    "EVENT_CREDENTIAL_MISMATCH",
                    "signature_test_event credential_id does not match issued credential.",
                )
            if payload.get("device_key_id") != credentials.get("device_key_id"):
                raise AgentOpsError(
                    "EVENT_DEVICE_KEY_MISMATCH",
                    "signature_test_event device_key_id does not match issued credential.",
                )
            if event.get("installation_id") != credentials.get(
                "installation_id"
            ) or payload.get("installation_id") != credentials.get("installation_id"):
                raise AgentOpsError(
                    "EVENT_IDENTITY_MISMATCH",
                    "signature_test_event installation_id does not match issued credential.",
                )
            if event.get("device_id") != credentials.get("device_id") or payload.get(
                "device_id"
            ) != credentials.get("device_id"):
                raise AgentOpsError(
                    "EVENT_IDENTITY_MISMATCH",
                    "signature_test_event device_id does not match issued credential.",
                )
            if payload.get("next_action") != "send_signature_test_event":
                raise AgentOpsError(
                    "EVENT_PAYLOAD_INVALID",
                    "signature_test_event next_action is invalid.",
                )
            return str(bootstrap_id)

    def mark_signature_test_verified(self, bootstrap_id: str, event_id: str) -> None:
        with self._lock:
            if bootstrap_id in self.bootstrap_sessions:
                session = dict(self.bootstrap_sessions[bootstrap_id])
                session["status"] = "verified"
                session["bootstrap_status"] = "signature_verified"
                session["signature_test_event_id"] = event_id
                session["verified_at"] = utc_now()
                self.bootstrap_sessions[bootstrap_id] = session
            if bootstrap_id in self.credentials_by_bootstrap:
                credentials = dict(self.credentials_by_bootstrap[bootstrap_id])
                credentials["bootstrap_status"] = "signature_verified"
                credentials["signature_test_event_id"] = event_id
                self.credentials_by_bootstrap[bootstrap_id] = credentials

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
        version_value = metadata.get("version")
        if version_value in (None, ""):
            version_value = metadata.get("agent_version")
        if version_value in (None, ""):
            version_value = "unknown"
        version = str(version_value)
        record = {
            **deepcopy(metadata),
            "agent_id": agent_id,
            "version": version,
            "synced_at": str(metadata.get("synced_at") or utc_now()),
        }
        skills = record.get("skills") or []
        if not isinstance(skills, list | tuple):
            skills = []
        with self._lock:
            agent_key = f"{agent_id}@{version}"
            self.agent_store_agents[f"{agent_id}@{version}"] = deepcopy(record)
            stale_skill_keys = [
                key
                for key in self.agent_store_skills
                if key.startswith(f"{agent_key}:")
            ]
            for key in stale_skill_keys:
                self.agent_store_skills.pop(key)
            for skill in skills:
                if isinstance(skill, dict):
                    skill_id_value = skill.get("skill_id")
                    if skill_id_value in (None, ""):
                        skill_id_value = skill.get("name")
                    if skill_id_value not in (None, ""):
                        skill_id = str(skill_id_value)
                        self.agent_store_skills[f"{agent_id}@{version}:{skill_id}"] = {
                            **deepcopy(skill),
                            "skill_id": skill_id,
                            "agent_id": agent_id,
                            "version": version,
                        }
            return deepcopy(record)

    def get_agent_store_metadata(
        self, agent_id: str, version: str
    ) -> dict[str, Any] | None:
        with self._lock:
            record = self.agent_store_agents.get(f"{agent_id}@{version}")
            return deepcopy(record) if record else None

    def has_agent_store_skill(self, agent_id: str, version: str, skill_id: str) -> bool:
        with self._lock:
            return f"{agent_id}@{version}:{skill_id}" in self.agent_store_skills

    def agent_store_metadata_records(self) -> tuple[dict[str, Any], ...]:
        with self._lock:
            return tuple(
                deepcopy(record) for record in self.agent_store_agents.values()
            )
