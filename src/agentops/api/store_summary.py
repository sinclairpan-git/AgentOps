"""Agent Store summary contract implementation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from agentops.core.agent_store import (
    AGENT_STORE_CONSUMER_BOUNDARY,
    DEFAULT_POLICY_REQUIREMENT,
    build_agent_store_echo_summary,
)
from agentops.core.evidence import build_evidence_summary
from agentops.core.errors import AgentOpsError
from agentops.core.l5_gate import evaluate_l5_gate
from agentops.storage.repository import InMemoryRepository


def get_agent_store_summary(
    agent_id: str,
    version: str,
    evidence_summary: dict[str, Any],
    *,
    consumer_schema_version: str = "1.0",
    repository: InMemoryRepository | None = None,
) -> dict[str, Any]:
    if repository is not None:
        return build_agent_store_echo_summary(
            repository,
            agent_id,
            version,
            evidence_summary,
            consumer_schema_version=consumer_schema_version,
        )

    if not consumer_schema_version.startswith("1."):
        raise AgentOpsError("SUMMARY_SCHEMA_UNSUPPORTED", "Unsupported Agent Store summary schema.")

    run_id = evidence_summary["run_id"]
    return {
        "schema_version": "agentops.agent_store.echo.v1",
        "agent_id": agent_id,
        "agent_version": version,
        "metadata_state": "unknown",
        "agentops_fact_owner": "AgentOps",
        "registry_fact_owner": "Agent Store",
        "agent_store_consumer_boundary": {
            key: list(value) if isinstance(value, list) else value
            for key, value in AGENT_STORE_CONSUMER_BOUNDARY.items()
        },
        "score_template_id": "framework-capability-stage1",
        "evidence_level": evidence_summary["evidence_level"],
        "confidence": evidence_summary["confidence"],
        "missing_evidence": list(evidence_summary["missing_evidence"]),
        "risk_state": "normal" if evidence_summary["evidence_level"] == "L5" else "warning",
        "approval_state": "none",
        "quality_state": {
            "source": "AgentOps",
            "source_trust": evidence_summary.get("source_trust", "verified"),
            "completeness": evidence_summary.get("completeness", 1.0),
            "freshness": evidence_summary.get("freshness", "fresh"),
        },
        "raw_access_state": evidence_summary.get("raw_access_state", "summary_only"),
        "redaction_policy": evidence_summary.get("redaction_policy", "repo_default"),
        "data_classification": evidence_summary.get("data_classification", "internal"),
        "policy_requirement": deepcopy(DEFAULT_POLICY_REQUIREMENT),
        "discovery_gap_ids": [],
        "run_audit": {
            "audit_id": "audit_store_summary",
            "registration_state": "suspected",
            "event_count": 0,
        },
        "calculated_at": "2026-05-05T00:00:00Z",
        "valid_until": "2026-06-04T00:00:00Z",
        "deep_links": {
            "agent_id": agent_id,
            "version": version,
            "session_id": f"sess_{run_id}",
            "run_id": run_id,
            "installation_id": "inst_stage1",
            "trace_id": "trace_stage1",
            "audit_id": "audit_store_summary",
            "return_url": "/agent-store/return",
        },
    }


def get_agent_store_summary_for_run(
    repository: InMemoryRepository,
    agent_id: str,
    version: str,
    run_id: str,
    *,
    consumer_schema_version: str = "1.0",
) -> dict[str, Any]:
    events = _events_for_run(repository, run_id)
    if not events:
        raise AgentOpsError("RUN_NOT_FOUND", "Run audit source events were not found.")
    evidence_summary = _agent_store_evidence_summary(run_id, events)
    return build_agent_store_echo_summary(
        repository,
        agent_id,
        version,
        evidence_summary,
        consumer_schema_version=consumer_schema_version,
    )


def _events_for_run(repository: InMemoryRepository, run_id: str) -> list[dict[str, Any]]:
    events = [
        event
        for event in repository.raw_event_records()
        if _event_run_id(event) == run_id
    ]
    return sorted(events, key=_event_sequence_no)


def _agent_store_evidence_summary(run_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    l5_input = _last_payload(events, "l5_eligibility_input")
    evaluation = evaluate_l5_gate(
        events,
        governance_state=_governance_state(events),
        outbox_status=str(l5_input.get("outbox_status", "delivered")),
        policy_state_known=_strict_bool(l5_input.get("policy_state_known"), default=False),
    )
    return build_evidence_summary(
        run_id,
        evaluation,
        linked_event_ids=[str(event["event_id"]) for event in events],
    )


def _last_payload(events: list[dict[str, Any]], event_type: str) -> dict[str, Any]:
    for event in reversed(events):
        if event.get("event_type") == event_type:
            payload = event.get("payload")
            return dict(payload) if isinstance(payload, dict) else {}
    return {}


def _governance_state(events: list[dict[str, Any]]) -> str:
    for event in reversed(events):
        payload = event.get("payload")
        if isinstance(payload, dict) and payload.get("adapter_state") not in (None, ""):
            return str(payload["adapter_state"])
    return "verified_loaded"


def _strict_bool(value: Any, *, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _event_payload(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload")
    return dict(payload) if isinstance(payload, dict) else {}


def _event_run_id(event: dict[str, Any]) -> str:
    payload = _event_payload(event)
    for candidate in (event.get("run_id"), payload.get("run_id")):
        if candidate not in (None, ""):
            return str(candidate)
    return str(event.get("event_id") or "unknown_run")


def _event_sequence_no(event: dict[str, Any]) -> int:
    try:
        return int(event.get("sequence_no", 0))
    except (TypeError, ValueError):
        return 0
