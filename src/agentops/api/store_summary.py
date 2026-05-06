"""Agent Store summary contract implementation."""

from __future__ import annotations

from typing import Any

from agentops.core.agent_store import build_agent_store_echo_summary
from agentops.core.errors import AgentOpsError
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
        "agent_id": agent_id,
        "agent_version": version,
        "score_template_id": "framework-capability-stage1",
        "evidence_level": evidence_summary["evidence_level"],
        "confidence": evidence_summary["confidence"],
        "missing_evidence": list(evidence_summary["missing_evidence"]),
        "risk_state": "normal" if evidence_summary["evidence_level"] == "L5" else "warning",
        "approval_state": "none",
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
