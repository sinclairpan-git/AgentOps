"""Agent Store integration API boundary."""

from __future__ import annotations

from typing import Any

from agentops.core.agent_store import build_run_audit, consume_agent_store_metadata, discover_agent_store_gaps
from agentops.storage.repository import InMemoryRepository


def sync_agent_store_metadata(repository: InMemoryRepository, metadata: dict[str, Any]) -> dict[str, Any]:
    return consume_agent_store_metadata(repository, metadata)


def list_agent_store_discovery_gaps(repository: InMemoryRepository) -> list[dict[str, Any]]:
    return discover_agent_store_gaps(repository)


def get_run_audit(repository: InMemoryRepository, run_id: str) -> dict[str, Any]:
    return build_run_audit(repository, run_id)
