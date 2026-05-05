"""Evidence summary construction."""

from __future__ import annotations

from typing import Any

from agentops.core.errors import AgentOpsError


def build_evidence_summary(
    run_id: str,
    l5_evaluation: dict[str, Any],
    *,
    linked_event_ids: list[str] | None = None,
    raw_access_allowed: bool = False,
    request_raw: bool = False,
) -> dict[str, Any]:
    if request_raw and not raw_access_allowed:
        raise AgentOpsError(
            "RAW_ACCESS_DENIED",
            "Raw evidence access requires Evidence Vault approval.",
            audit_id="audit_evidence_denied",
            request_id=f"raw:{run_id}",
            denied_scope="evidence.raw",
        )

    return {
        "run_id": run_id,
        "evidence_level": l5_evaluation["evidence_level"],
        "confidence": 1.0 if l5_evaluation["evidence_level"] == "L5" else 0.62,
        "missing_evidence": list(l5_evaluation.get("missing_evidence", [])),
        "raw_access_state": "approved" if raw_access_allowed else "summary_only",
        "linked_event_ids": linked_event_ids or [],
        "data_classification": "internal",
        "redaction_policy": "repo_default",
        "access_policy": "evidence-vault-approval",
        "retention_policy": "default-90d",
        "redacted_summary": {
            "run_id": run_id,
            "downgrade_reason": l5_evaluation.get("downgrade_reason", ""),
        },
        "payload_hash": f"sha256:{run_id}",
        "source_trust": "verified" if l5_evaluation["evidence_level"] == "L5" else "declared",
        "completeness": 1.0 if not l5_evaluation.get("missing_evidence") else 0.5,
        "freshness": "fresh" if "verification_result" not in l5_evaluation.get("missing_evidence", []) else "unknown",
        "downgrade_reason": l5_evaluation.get("downgrade_reason", ""),
    }
