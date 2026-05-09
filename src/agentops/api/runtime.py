"""Runtime ingestion API boundary."""

from __future__ import annotations

from typing import Any

from agentops.core.runtime_summary import (
    build_runtime_evidence_summary,
    build_runtime_health_summary,
)
from agentops.core.runtime_ingestion import ingest_runtime_batch
from agentops.api.view_models import (
    build_runtime_run_detail_projection,
    build_trace_timeline_projection,
)
from agentops.storage.repository import InMemoryRepository


def ingest_runtime_events(batch: Any, repository: InMemoryRepository) -> dict[str, Any]:
    return ingest_runtime_batch(batch, repository)


def get_runtime_run_detail(
    repository: InMemoryRepository,
    run_id: str,
    *,
    allowed: bool = True,
) -> dict[str, Any]:
    return build_runtime_run_detail_projection(repository, run_id, allowed=allowed)


def get_runtime_trace_timeline(
    repository: InMemoryRepository,
    run_id: str,
    *,
    request_raw: bool = False,
    raw_access_allowed: bool = False,
) -> dict[str, Any]:
    return build_trace_timeline_projection(
        repository,
        run_id,
        request_raw=request_raw,
        raw_access_allowed=raw_access_allowed,
    )


def get_runtime_evidence_summary(
    repository: InMemoryRepository,
    run_id: str,
    *,
    request_raw: bool = False,
    raw_access_allowed: bool = False,
) -> dict[str, Any]:
    return build_runtime_evidence_summary(
        repository,
        run_id,
        request_raw=request_raw,
        raw_access_allowed=raw_access_allowed,
    )


def get_runtime_health_summary(
    repository: InMemoryRepository,
    agent_id: str,
    version: str,
) -> dict[str, Any]:
    return build_runtime_health_summary(repository, agent_id, version)
