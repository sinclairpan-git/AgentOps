"""P1-B operations API contracts."""

from __future__ import annotations

from typing import Any

from agentops.core.operations import (
    build_complex_risk_profile,
    build_adoption_roi_projection,
    build_dlq_operations_projection,
    build_exporter_ecosystem_projection,
    build_exporter_operation,
    build_lifecycle_recommendation,
    build_monthly_quality_report,
    build_mcp_a2a_governance_projection,
    build_multi_agent_handoff_evaluation,
    build_optimizer_recommendation,
    build_policy_simulation_projection,
    build_quality_center_workbench,
    build_quality_score_projection,
    build_quality_scorer_comparison,
    build_quality_scorer_version,
    build_runtime_budget_summary,
    build_runtime_slo_summary,
    create_quality_scorer_execution as _create_quality_scorer_execution,
    build_store_governance_projection,
    create_eval_case as _create_eval_case,
    create_evidence_access_operation as _create_evidence_access_operation,
    create_experiment_plan as _create_experiment_plan,
    create_safe_replay_plan as _create_safe_replay_plan,
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


def create_safe_replay_plan(
    repository: InMemoryRepository,
    run_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    return _create_safe_replay_plan(repository, run_id, **kwargs)


def create_experiment_plan(
    repository: InMemoryRepository,
    agent_id: str,
    version: str,
    **kwargs: Any,
) -> dict[str, Any]:
    return _create_experiment_plan(repository, agent_id, version, **kwargs)


def get_optimizer_recommendation(
    repository: InMemoryRepository,
    agent_id: str,
    version: str,
    **kwargs: Any,
) -> dict[str, Any]:
    return build_optimizer_recommendation(repository, agent_id, version, **kwargs)


def get_policy_simulation_projection(
    repository: InMemoryRepository,
    **kwargs: Any,
) -> dict[str, Any]:
    return build_policy_simulation_projection(repository, **kwargs)


def get_mcp_a2a_governance_projection(**kwargs: Any) -> dict[str, Any]:
    return build_mcp_a2a_governance_projection(**kwargs)


def get_exporter_ecosystem_projection(**kwargs: Any) -> dict[str, Any]:
    return build_exporter_ecosystem_projection(**kwargs)


def get_multi_agent_handoff_evaluation(
    repository: InMemoryRepository,
    agent_id: str,
    version: str,
) -> dict[str, Any]:
    return build_multi_agent_handoff_evaluation(repository, agent_id, version)


def get_complex_risk_profile(
    repository: InMemoryRepository,
    agent_id: str,
    version: str,
) -> dict[str, Any]:
    return build_complex_risk_profile(repository, agent_id, version)


def get_quality_score_projection(
    repository: InMemoryRepository,
    agent_id: str,
    version: str,
    **kwargs: Any,
) -> dict[str, Any]:
    return build_quality_score_projection(repository, agent_id, version, **kwargs)


def get_quality_scorer_version(**kwargs: Any) -> dict[str, Any]:
    return build_quality_scorer_version(**kwargs)


def get_quality_scorer_comparison(
    repository: InMemoryRepository,
    agent_id: str,
    version: str,
    **kwargs: Any,
) -> dict[str, Any]:
    return build_quality_scorer_comparison(repository, agent_id, version, **kwargs)


def create_quality_scorer_execution(
    repository: InMemoryRepository,
    agent_id: str,
    version: str,
    **kwargs: Any,
) -> dict[str, Any]:
    return _create_quality_scorer_execution(repository, agent_id, version, **kwargs)


def get_adoption_roi_projection(**kwargs: Any) -> dict[str, Any]:
    return build_adoption_roi_projection(**kwargs)


def get_lifecycle_recommendation(
    repository: InMemoryRepository,
    agent_id: str,
    version: str,
) -> dict[str, Any]:
    return build_lifecycle_recommendation(repository, agent_id, version)


def get_monthly_quality_report(
    repository: InMemoryRepository,
    **kwargs: Any,
) -> dict[str, Any]:
    return build_monthly_quality_report(repository, **kwargs)


def get_quality_center_workbench(
    repository: InMemoryRepository,
    **kwargs: Any,
) -> dict[str, Any]:
    return build_quality_center_workbench(repository, **kwargs)


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
