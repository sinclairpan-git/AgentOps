"""Approval lifecycle API contracts."""

from __future__ import annotations

from typing import Any

from agentops.core.approvals import create_approval, decide_approval
from agentops.storage.repository import InMemoryRepository


def create_approval_request(
    policy_request: dict[str, Any],
    policy_decision: dict[str, Any],
    repository: InMemoryRepository,
    **kwargs: Any,
) -> dict[str, Any]:
    return create_approval(policy_request, policy_decision, repository, **kwargs)


def decide_approval_request(
    approval_id: str,
    *,
    action: str,
    actor: str,
    reason: str,
    repository: InMemoryRepository,
    **kwargs: Any,
) -> dict[str, Any]:
    return decide_approval(
        approval_id,
        action=action,
        actor=actor,
        reason=reason,
        repository=repository,
        **kwargs,
    )
