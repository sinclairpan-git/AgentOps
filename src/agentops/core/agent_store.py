"""Agent Store metadata consumption, discovery, and audit helpers."""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any

from agentops.core.errors import AgentOpsError
from agentops.storage.repository import InMemoryRepository


DEFAULT_POLICY_REQUIREMENT = {
    "required_by": "AgentOps",
    "source": "runtime_policy",
    "issuer": "AgentOps Policy Service",
    "policy_owner": "安全/IAM",
    "policy_version": "runtime-v2",
    "can_ignore": False,
    "affected_actions": ["运行审计", "高风险 Skill 调用"],
}


def consume_agent_store_metadata(repository: InMemoryRepository, metadata: dict[str, Any]) -> dict[str, Any]:
    """Cache Agent Store metadata without becoming the registration source."""

    _require(metadata, {"agent_id"}, "AGENT_STORE_METADATA_INVALID")
    if metadata.get("version") in (None, "") and metadata.get("agent_version") in (None, ""):
        raise AgentOpsError("AGENT_STORE_METADATA_INVALID", "Missing required fields: version.")
    record = repository.upsert_agent_store_metadata(metadata)
    return {
        "agent_id": record["agent_id"],
        "version": record["version"],
        "metadata_state": "consumed",
        "fact_owner": "Agent Store",
        "synced_at": record["synced_at"],
    }


def discover_agent_store_gaps(repository: InMemoryRepository) -> list[dict[str, Any]]:
    """Find accepted run facts that cannot be mapped to Agent Store metadata."""

    raw_events = repository.raw_event_records()
    agent_runs: dict[str, set[str]] = defaultdict(set)
    skill_runs: dict[str, set[str]] = defaultdict(set)
    discovery: dict[str, dict[str, Any]] = {}

    for event in raw_events:
        agent_id_value = event.get("agent_id")
        version_value = event.get("agent_version")
        if version_value in (None, ""):
            version_value = event.get("version")
        if agent_id_value in (None, "") or version_value in (None, ""):
            continue
        agent_id = str(agent_id_value)
        version = str(version_value)
        run_id = _event_run_id(event)
        agent_key = f"{agent_id}@{version}"
        agent_runs[agent_key].add(run_id)

        if repository.get_agent_store_metadata(agent_id, version) is None:
            discovery[agent_key] = _gap(
                gap_id=f"gap_agent_{_slug(agent_key)}",
                gap_type="agent_unregistered",
                agent_id=agent_id,
                version=version,
                skill_id="",
                affected_runs=agent_runs[agent_key],
                severity="高",
                primary_action="通知 Owner 补齐 Agent Store 注册事实",
            )
            continue

        skill_id = _event_skill_id(event)
        if skill_id:
            skill_key = f"{agent_key}:{skill_id}"
            skill_runs[skill_key].add(run_id)
            if not repository.has_agent_store_skill(agent_id, version, skill_id):
                discovery[skill_key] = _gap(
                    gap_id=f"gap_skill_{_slug(skill_key)}",
                    gap_type="skill_unregistered",
                    agent_id=agent_id,
                    version=version,
                    skill_id=skill_id,
                    affected_runs=skill_runs[skill_key],
                    severity="中",
                    primary_action="补齐 Skill 注册事实或标记忽略",
                )

    return sorted(discovery.values(), key=lambda item: (item["gap_type"], item["agent_id"], item["skill_id"]))


def build_run_audit(repository: InMemoryRepository, run_id: str) -> dict[str, Any]:
    events = [event for event in repository.raw_event_records() if _event_run_id(event) == run_id]
    if not events:
        raise AgentOpsError("RUN_NOT_FOUND", "Run audit source events were not found.")

    events = sorted(events, key=_event_sequence_no)
    first = events[0]
    agent_id = str(first.get("agent_id") or "unknown_agent")
    version = str(first.get("agent_version") or first.get("version") or "unknown")
    metadata = repository.get_agent_store_metadata(agent_id, version)
    gaps = [
        gap
        for gap in discover_agent_store_gaps(repository)
        if run_id in gap["affected_runs"]
    ]
    registration_state = "governed" if metadata and not gaps else "suspected"

    return {
        "audit_id": f"audit_run_{_slug(run_id)}",
        "run_id": run_id,
        "agent_id": agent_id,
        "version": version,
        "registration_state": registration_state,
        "event_count": len(events),
        "event_ids": [str(event["event_id"]) for event in events],
        "raw_access_state": "summary_only",
        "discovery_gap_ids": [gap["gap_id"] for gap in gaps],
        "related_agent_versions": sorted(
            {
                f"{event.get('agent_id') or 'unknown_agent'}@{event.get('agent_version') or event.get('version') or 'unknown'}"
                for event in events
            }
        ),
        "deep_links": {
            "agent_id": agent_id,
            "version": version,
            "session_id": str(first.get("session_id") or f"sess_{run_id}"),
            "run_id": run_id,
            "installation_id": str(first.get("installation_id") or "unknown_installation"),
            "trace_id": str(first.get("trace_id") or f"trace_{run_id}"),
            "audit_id": f"audit_run_{_slug(run_id)}",
            "return_url": f"/agent-store/agents/{agent_id}/runs/{run_id}",
        },
    }


def build_agent_store_echo_summary(
    repository: InMemoryRepository,
    agent_id: str,
    version: str,
    evidence_summary: dict[str, Any],
    *,
    consumer_schema_version: str = "1.0",
) -> dict[str, Any]:
    if not consumer_schema_version.startswith("1."):
        raise AgentOpsError("SUMMARY_SCHEMA_UNSUPPORTED", "Unsupported Agent Store summary schema.")

    metadata = repository.get_agent_store_metadata(agent_id, version)
    run_id = str(evidence_summary["run_id"])
    run_audit = build_run_audit(repository, run_id)
    if run_audit["agent_id"] != agent_id or run_audit["version"] != version:
        raise AgentOpsError(
            "STORE_SUMMARY_RUN_MISMATCH",
            "Run audit does not match the requested Agent Store summary target.",
        )
    discovery_gaps = [gap for gap in discover_agent_store_gaps(repository) if run_id in gap["affected_runs"]]
    registered = metadata is not None and not discovery_gaps
    risk_state = "normal" if registered and evidence_summary.get("evidence_level") == "L5" else "warning"

    return {
        "schema_version": "agentops.agent_store.echo.v1",
        "agent_id": agent_id,
        "agent_version": version,
        "metadata_state": "registered" if metadata else "unregistered",
        "registry_fact_owner": "Agent Store",
        "score_template_id": "framework-capability-stage3",
        "evidence_level": evidence_summary["evidence_level"],
        "confidence": evidence_summary["confidence"],
        "missing_evidence": list(evidence_summary["missing_evidence"]),
        "risk_state": risk_state,
        "approval_state": "none",
        "policy_requirement": deepcopy(DEFAULT_POLICY_REQUIREMENT),
        "discovery_gap_ids": [gap["gap_id"] for gap in discovery_gaps],
        "run_audit": {
            "audit_id": run_audit["audit_id"],
            "registration_state": run_audit["registration_state"],
            "event_count": run_audit["event_count"],
        },
        "calculated_at": "2026-05-06T00:00:00Z",
        "valid_until": "2026-06-05T00:00:00Z",
        "deep_links": run_audit["deep_links"],
    }


def _gap(
    *,
    gap_id: str,
    gap_type: str,
    agent_id: str,
    version: str,
    skill_id: str,
    affected_runs: set[str],
    severity: str,
    primary_action: str,
) -> dict[str, Any]:
    return {
        "gap_id": gap_id,
        "gap_type": gap_type,
        "agent_id": agent_id,
        "version": version,
        "skill_id": skill_id,
        "state": "suspected",
        "severity": severity,
        "affected_runs": sorted(affected_runs),
        "owner_hint": "Agent Owner",
        "primary_action": primary_action,
        "audit_id": f"audit_{gap_id}",
    }


def _event_payload(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload")
    return dict(payload) if isinstance(payload, dict) else {}


def _event_run_id(event: dict[str, Any]) -> str:
    payload = _event_payload(event)
    for candidate in (event.get("run_id"), payload.get("run_id")):
        if candidate not in (None, ""):
            return str(candidate)
    return str(event.get("event_id") or "unknown_run")


def _event_skill_id(event: dict[str, Any]) -> str:
    payload = _event_payload(event)
    for candidate in (payload.get("skill_id"), payload.get("stage_id"), payload.get("stage_name")):
        if candidate not in (None, ""):
            return str(candidate)
    return ""


def _event_sequence_no(event: dict[str, Any]) -> int:
    try:
        return int(event.get("sequence_no", 0))
    except (TypeError, ValueError):
        return 0


def _require(data: dict[str, Any], fields: set[str], error_code: str) -> None:
    missing = sorted(field for field in fields if field not in data or data[field] in (None, ""))
    if missing:
        raise AgentOpsError(error_code, f"Missing required fields: {', '.join(missing)}.")


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_") or "unknown"
