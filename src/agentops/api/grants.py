"""Capability Grant API contracts."""

from __future__ import annotations

from typing import Any

from agentops.core.grants import (
    consume_capability_grant,
    issue_capability_grant,
    revoke_capability_grant,
)
from agentops.storage.repository import InMemoryRepository


def issue_grant(
    approval_id: str,
    grant_request: dict[str, Any],
    repository: InMemoryRepository,
    **kwargs: Any,
) -> dict[str, Any]:
    return issue_capability_grant(approval_id, grant_request, repository, **kwargs)


def consume_grant(
    grant_id: str,
    policy_request: dict[str, Any],
    repository: InMemoryRepository,
    **kwargs: Any,
) -> dict[str, Any]:
    return consume_capability_grant(grant_id, policy_request, repository, **kwargs)


def revoke_grant(
    grant_id: str, repository: InMemoryRepository, **kwargs: Any
) -> dict[str, Any]:
    return revoke_capability_grant(grant_id, repository, **kwargs)
