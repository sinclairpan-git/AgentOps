"""Runtime ingestion API boundary."""

from __future__ import annotations

from typing import Any

from agentops.core.runtime_ingestion import ingest_runtime_batch
from agentops.storage.repository import InMemoryRepository


def ingest_runtime_events(
    batch: dict[str, Any], repository: InMemoryRepository
) -> dict[str, Any]:
    return ingest_runtime_batch(batch, repository)
