"""Evidence API contract implementation."""

from __future__ import annotations

from typing import Any

from agentops.core.evidence import build_evidence_summary


def get_evidence_summary(
    run_id: str,
    l5_evaluation: dict[str, Any],
    *,
    linked_event_ids: list[str] | None = None,
    raw_access_allowed: bool = False,
    request_raw: bool = False,
) -> dict[str, Any]:
    return build_evidence_summary(
        run_id,
        l5_evaluation,
        linked_event_ids=linked_event_ids,
        raw_access_allowed=raw_access_allowed,
        request_raw=request_raw,
    )
