"""Evidence Vault API contracts."""

from __future__ import annotations

from typing import Any

from agentops.core.evidence_vault import (
    approve_raw_access_request,
    build_evidence_vault_summary,
    create_raw_access_request,
)
from agentops.storage.repository import InMemoryRepository


def get_evidence_vault_summary(**kwargs: Any) -> dict[str, Any]:
    return build_evidence_vault_summary(**kwargs)


def request_raw_access(repository: InMemoryRepository, **kwargs: Any) -> dict[str, Any]:
    return create_raw_access_request(repository=repository, **kwargs)


def approve_raw_access(
    request_id: str, repository: InMemoryRepository, **kwargs: Any
) -> dict[str, Any]:
    return approve_raw_access_request(request_id, repository, **kwargs)
