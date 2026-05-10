"""P1-B operations API contracts."""

from __future__ import annotations

from typing import Any

from agentops.core.operations import (
    build_dlq_operations_projection,
    build_exporter_operation,
    build_runtime_budget_summary,
    build_runtime_slo_summary,
    build_store_governance_projection,
    create_eval_case as _create_eval_case,
    create_evidence_access_operation as _create_evidence_access_operation,
)
from agentops.storage.repository import InMemoryRepository


def create_evidence_access_operation(
    repository: InMemoryRepository,
    evidence_summary: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    return _create_evidence_access_operation(repository, evidence_summary, **kwargs)


def create_eval_case(
    repository: InMemoryRepository,
    run_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    return _create_eval_case(repository, run_id, **kwargs)


def get_runtime_budget_summary(
    repository: InMemoryRepository,
    agent_id: str,
    version: str,
    **kwargs: Any,
) -> dict[str, Any]:
    return build_runtime_budget_summary(repository, agent_id, version, **kwargs)


def get_dlq_operations_projection(repository: InMemoryRepository) -> dict[str, Any]:
    return build_dlq_operations_projection(repository)


def get_exporter_operation(**kwargs: Any) -> dict[str, Any]:
    return build_exporter_operation(**kwargs)


def get_runtime_slo_summary(
    repository: InMemoryRepository,
    agent_id: str,
    version: str,
    **kwargs: Any,
) -> dict[str, Any]:
    return build_runtime_slo_summary(repository, agent_id, version, **kwargs)


def get_store_governance_projection(
    repository: InMemoryRepository,
    agent_id: str,
    version: str,
) -> dict[str, Any]:
    return build_store_governance_projection(repository, agent_id, version)
