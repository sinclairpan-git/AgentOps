"""P1-B evidence, eval, budget, DLQ, exporter, SLO, and Store projections."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from math import ceil
from typing import Any

from agentops.core.errors import AgentOpsError
from agentops.core.runtime_summary import (
    build_runtime_evidence_summary,
    build_runtime_health_summary,
)
from agentops.storage.repository import InMemoryRepository

FAILURE_SAMPLE_STATES = {"failed", "timeout", "blocked", "cancelled", "degraded"}
TERMINAL_RUN_STATES = FAILURE_SAMPLE_STATES | {"succeeded"}
SUPPORTED_POLICY_SIMULATION_CHANGES = {
    "tighten_policy",
    "loosen_policy",
    "canary_policy",
    "rollback_policy",
}
SUPPORTED_ECOSYSTEM_PROTOCOLS = {"mcp", "a2a"}
SUPPORTED_ECOSYSTEM_EXPORTERS = {
    "otlp",
    "openinference",
    "apm",
    "data_lake",
}
FORBIDDEN_SUMMARY_KEYS = {
    "raw_payload",
    "prompt",
    "token_secret",
    "credential_secret",
    "device_key",
    "download_url",
    "raw_url",
}
FORBIDDEN_TEXT_MARKERS = (
    "token_secret",
    "credential_secret",
    "device_key",
)


def create_evidence_access_operation(
    repository: InMemoryRepository,
    evidence_summary: dict[str, Any],
    *,
    requester: str,
    reason: str,
    approver_scope: str,
    redaction_preview_state: str = "ready",
    now: datetime | None = None,
) -> dict[str, Any]:
    created_at = _normalize_time(now or datetime.now(UTC))
    evidence_id = str(
        evidence_summary.get("evidence_id")
        or f"evidence_{evidence_summary.get('run_id', 'unknown')}"
    )
    operation = {
        "schema_version": "evidence_access_operation.v1",
        "operation_id": "",
        "evidence_id": evidence_id,
        "run_id": str(evidence_summary.get("run_id") or ""),
        "trace_id": str(evidence_summary.get("trace_id") or ""),
        "payload_hash": str(evidence_summary.get("payload_hash") or ""),
        "payload_ref": str(evidence_summary.get("payload_ref") or ""),
        "requester": requester,
        "reason": reason,
        "approver_scope": approver_scope,
        "raw_access_state": "requested",
        "redaction_preview_state": _redaction_preview_state(redaction_preview_state),
        "owner_notification_state": (
            "pending" if redaction_preview_state == "failed" else "not_required"
        ),
        "created_at": created_at.isoformat(),
        "summary": {
            "raw_payload_access": "forbidden",
            "redacted_preview_only": True,
            "external_write_enabled": False,
        },
        "audit_id": f"audit_evidence_access_{evidence_id}",
    }
    return repository.store_evidence_access_operation(operation)


def create_eval_case(
    repository: InMemoryRepository,
    run_id: str,
    *,
    owner_team: str,
    expected_behavior: str,
    privacy_class: str = "internal",
    now: datetime | None = None,
) -> dict[str, Any]:
    run = repository.get_runtime_run_fact(run_id)
    if not run:
        raise AgentOpsError("RUNTIME_RUN_NOT_FOUND", "Runtime run fact was not found.")
    status = str(run.get("status") or "")
    if status not in FAILURE_SAMPLE_STATES:
        raise AgentOpsError(
            "EVAL_CASE_SOURCE_NOT_FAILED",
            "Only failed, blocked, cancelled, timeout, or degraded runs can seed EvalCase.",
            denied_scope="runtime.run.status",
            audit_id=f"audit_eval_case_{run_id}",
        )

    created_at = _normalize_time(now or datetime.now(UTC))
    evidence_summary = build_runtime_evidence_summary(repository, run_id)
    eval_case = {
        "schema_version": "eval_case.v1",
        "eval_case_id": "",
        "source_run": {
            "run_id": run_id,
            "agent_id": str(run.get("agent_id") or ""),
            "version": str(run.get("version") or ""),
            "status": status,
            "terminal_reason": str(run.get("terminal_reason") or ""),
        },
        "privacy_class": privacy_class,
        "owner_team": owner_team,
        "expected_behavior": expected_behavior,
        "status": "needs_review",
        "scorer_status": "not_started",
        "evidence_summary": evidence_summary,
        "created_at": created_at.isoformat(),
        "summary": {
            "raw_payload_access": "forbidden",
            "source": "runtime_failure_sample",
            "deterministic_scorer_ready": False,
        },
        "audit_id": f"audit_eval_case_{run_id}",
    }
    return repository.store_eval_case(eval_case)


def create_safe_replay_plan(
    repository: InMemoryRepository,
    run_id: str,
    *,
    created_by: str,
    reason: str,
    sandbox_profile: str = "read_only",
    replay_mode: str = "simulation_only",
    now: datetime | None = None,
) -> dict[str, Any]:
    run = repository.get_runtime_run_fact(run_id)
    if not run:
        raise AgentOpsError("RUNTIME_RUN_NOT_FOUND", "Runtime run fact was not found.")
    status = str(run.get("status") or "")
    if status not in TERMINAL_RUN_STATES:
        raise AgentOpsError(
            "REPLAY_SOURCE_NOT_TERMINAL",
            "Safe replay planning requires a terminal source run.",
            denied_scope="runtime.run.status",
            audit_id=f"audit_safe_replay_{run_id}",
        )

    created_at = _normalize_time(now or datetime.now(UTC))
    evidence_summary = build_runtime_evidence_summary(repository, run_id)
    replay_plan = {
        "schema_version": "safe_replay_plan.v1",
        "replay_plan_id": "",
        "source_run": {
            "run_id": run_id,
            "agent_id": str(run.get("agent_id") or ""),
            "version": str(run.get("version") or ""),
            "status": status,
            "attempt_no": run.get("attempt_no", 1),
            "terminal_reason": str(run.get("terminal_reason") or ""),
        },
        "sandbox_profile": sandbox_profile,
        "replay_mode": replay_mode
        if replay_mode in {"simulation_only", "shadow_plan"}
        else "simulation_only",
        "execution_state": "not_started",
        "evidence_summary": evidence_summary,
        "created_by": created_by,
        "reason": _redacted_text(reason),
        "created_at": created_at.isoformat(),
        "summary": {
            "raw_payload_access": "forbidden",
            "runtime_execution_performed": False,
            "external_side_effects_enabled": False,
            "simulation_only": True,
            "input_material": "hash_ref_summary_only",
        },
        "audit_id": f"audit_safe_replay_{run_id}",
    }
    return repository.store_safe_replay_plan(replay_plan)


def create_experiment_plan(
    repository: InMemoryRepository,
    agent_id: str,
    version: str,
    *,
    variants: list[dict[str, Any]],
    owner_team: str,
    hypothesis: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not variants:
        raise AgentOpsError(
            "EXPERIMENT_VARIANT_UNSAFE",
            "At least one safe experiment variant is required.",
        )
    created_at = _normalize_time(now or datetime.now(UTC))
    safe_variants = [
        _safe_experiment_variant(index, item)
        for index, item in enumerate(variants, start=1)
    ]
    experiment_plan = {
        "schema_version": "experiment_plan.v1",
        "experiment_plan_id": "",
        "agent_id": agent_id,
        "version": version,
        "variants": safe_variants,
        "owner_team": owner_team,
        "hypothesis": _redacted_text(hypothesis),
        "rollout_state": "planning",
        "created_at": created_at.isoformat(),
        "summary": {
            "raw_payload_access": "forbidden",
            "external_execution_enabled": False,
            "automatic_rollout_enabled": False,
            "variant_material": "hash_ref_summary_only",
        },
        "audit_id": f"audit_experiment_plan_{agent_id}_{version}",
    }
    return repository.store_experiment_plan(experiment_plan)


def build_runtime_budget_summary(
    repository: InMemoryRepository,
    agent_id: str,
    version: str,
    *,
    token_budget: int | None = None,
    cost_budget: float | None = None,
    latency_budget_ms: int | None = None,
) -> dict[str, Any]:
    runs = repository.runtime_run_records_for_agent_version(agent_id, version)
    spans = []
    for run in runs:
        spans.extend(
            repository.trace_span_records_for_run(
                str(run.get("run_id") or ""), attempt_no=run.get("attempt_no")
            )
        )

    input_tokens = 0
    output_tokens = 0
    total_cost = 0.0
    latencies = []
    for span in spans:
        usage = (
            span.get("token_usage") if isinstance(span.get("token_usage"), dict) else {}
        )
        input_tokens += _safe_int(usage.get("input") or usage.get("input_tokens"))
        output_tokens += _safe_int(usage.get("output") or usage.get("output_tokens"))
        cost = (
            span.get("cost_estimate")
            if isinstance(span.get("cost_estimate"), dict)
            else {}
        )
        total_cost += _safe_float(cost.get("amount"))
        latency_ms = _span_latency_ms(span)
        if latency_ms is not None:
            latencies.append(latency_ms)

    p95_latency = _percentile(latencies, 0.95)
    total_tokens = input_tokens + output_tokens
    budget_state = _budget_state(
        total_tokens=total_tokens,
        total_cost=total_cost,
        p95_latency=p95_latency,
        token_budget=token_budget,
        cost_budget=cost_budget,
        latency_budget_ms=latency_budget_ms,
    )
    return {
        "schema_version": "runtime_budget_summary.v1",
        "agent_id": agent_id,
        "version": version,
        "calculation_window": {
            "type": "recent_runs",
            "run_ids": [str(run.get("run_id")) for run in runs],
            "span_count": len(spans),
        },
        "token_usage": {
            "input": input_tokens,
            "output": output_tokens,
            "total": total_tokens,
        },
        "cost_estimate": {"amount": round(total_cost, 6), "currency": "USD"},
        "latency_ms": {
            "p95": p95_latency,
            "max": max(latencies) if latencies else 0,
            "sample_size": len(latencies),
        },
        "budget_state": budget_state,
        "recommended_action": (
            "review_budget" if budget_state in {"at_risk", "over_budget"} else "none"
        ),
        "summary": {
            "raw_payload_access": "forbidden",
            "derived_from": "trace_span_summary_fields",
        },
        "audit_id": f"audit_runtime_budget_{agent_id}_{version}",
    }


def build_optimizer_recommendation(
    repository: InMemoryRepository,
    agent_id: str,
    version: str,
    *,
    min_eval_cases: int = 1,
) -> dict[str, Any]:
    if min_eval_cases <= 0:
        raise AgentOpsError(
            "OPTIMIZER_EVIDENCE_REQUIRED",
            "Optimizer evidence threshold must be positive.",
            denied_scope="optimizer.min_eval_cases",
            audit_id=f"audit_optimizer_{agent_id}_{version}",
        )
    eval_cases = [
        record
        for record in repository.eval_case_records()
        if (record.get("source_run") or {}).get("agent_id") == agent_id
        and (record.get("source_run") or {}).get("version") == version
    ]
    eval_case_ids = [str(record.get("eval_case_id") or "") for record in eval_cases]
    if len(eval_cases) < min_eval_cases:
        recommendation_state = "insufficient_evidence"
        recommended_action = "collect_more_samples"
    else:
        recommendation_state = "ready"
        recommended_action = "prepare_experiment"

    status_summary: dict[str, int] = {}
    for record in eval_cases:
        source_run = (
            record.get("source_run")
            if isinstance(record.get("source_run"), dict)
            else {}
        )
        status = str(source_run.get("status") or "unknown")
        status_summary[status] = status_summary.get(status, 0) + 1

    return {
        "schema_version": "optimizer_recommendation.v1",
        "agent_id": agent_id,
        "version": version,
        "source_eval_cases": eval_case_ids,
        "recommendation_state": recommendation_state,
        "recommended_action": recommended_action,
        "evidence_window": {
            "type": "eval_case_summary",
            "sample_size": len(eval_cases),
            "minimum_required": min_eval_cases,
        },
        "summary": {
            "raw_payload_access": "forbidden",
            "automatic_config_rewrite": False,
            "automatic_model_switch": False,
            "runtime_execution_performed": False,
            "status_summary": status_summary,
        },
        "audit_id": f"audit_optimizer_{agent_id}_{version}",
    }


def build_policy_simulation_projection(
    repository: InMemoryRepository,
    *,
    policy_set_version: str,
    proposed_change: dict[str, Any],
    sample_run_ids: list[str],
    requested_by: str,
) -> dict[str, Any]:
    change_type = str(proposed_change.get("change_type") or "")
    if change_type not in SUPPORTED_POLICY_SIMULATION_CHANGES:
        raise AgentOpsError(
            "POLICY_SIMULATION_UNSUPPORTED_ACTION",
            "Policy simulation change_type is unsupported.",
            denied_scope="policy.change_type",
            audit_id=f"audit_policy_simulation_{policy_set_version}",
        )

    unique_sample_run_ids = _unique_strings(sample_run_ids)
    sampled_runs = [
        run
        for run_id in unique_sample_run_ids
        if (run := repository.get_runtime_run_fact(str(run_id))) is not None
    ]
    blocked_or_failed = sum(
        1
        for run in sampled_runs
        if str(run.get("status") or "") in FAILURE_SAMPLE_STATES
    )
    succeeded = sum(1 for run in sampled_runs if run.get("status") == "succeeded")
    simulation_state = "projected" if sampled_runs else "insufficient_sample"

    return {
        "schema_version": "policy_simulation_projection.v1",
        "policy_set_version": policy_set_version,
        "proposed_change": _safe_policy_change(proposed_change),
        "sample_run_ids": [str(run.get("run_id") or "") for run in sampled_runs],
        "requested_by": requested_by,
        "simulation_state": simulation_state,
        "decision_impact_summary": {
            "sample_size": len(sampled_runs),
            "succeeded": succeeded,
            "blocked_or_failed": blocked_or_failed,
            "projected_policy_publish": False,
            "deny_priority_preserved": True,
        },
        "summary": {
            "raw_payload_access": "forbidden",
            "dry_run_only": True,
            "policy_publish_performed": False,
            "runtime_execution_performed": False,
        },
        "audit_id": f"audit_policy_simulation_{policy_set_version}",
    }


def build_dlq_operations_projection(
    repository: InMemoryRepository,
    *,
    agent_id: str | None = None,
    version: str | None = None,
) -> dict[str, Any]:
    records = repository.runtime_dlq_records(agent_id=agent_id, version=version)
    error_summary: dict[str, int] = {}
    retry_candidates = []
    discard_candidates = []
    for record in records:
        error_code = str(record.get("error_code") or "UNKNOWN")
        error_summary[error_code] = error_summary.get(error_code, 0) + 1
        candidate = _dlq_candidate(record)
        if record.get("retryable", False):
            retry_candidates.append(candidate)
        else:
            discard_candidates.append(candidate)

    return {
        "schema_version": "dlq_operations_projection.v1",
        "agent_id": agent_id or "",
        "version": version or "",
        "backlog_count": len(records),
        "retry_candidates": retry_candidates,
        "discard_candidates": discard_candidates,
        "error_summary": error_summary,
        "summary": {
            "raw_payload_access": "forbidden",
            "operation_mode": "display_only",
            "replay_executes_here": False,
        },
        "audit_id": "audit_dlq_operations_projection",
    }


def build_mcp_a2a_governance_projection(
    *,
    protocol: str,
    endpoint_ref: str,
    subject_agent_id: str,
    resource_scope: str,
    requested_by: str = "system",
    policy_check_state: str = "required",
) -> dict[str, Any]:
    normalized_protocol = protocol.lower() if isinstance(protocol, str) else ""
    if normalized_protocol not in SUPPORTED_ECOSYSTEM_PROTOCOLS:
        raise AgentOpsError(
            "MCP_A2A_PROTOCOL_UNSUPPORTED",
            "MCP/A2A protocol is unsupported.",
            denied_scope="ecosystem.protocol",
            audit_id=f"audit_mcp_a2a_{subject_agent_id}",
        )
    safe_policy_state = (
        policy_check_state
        if policy_check_state in {"required", "passed", "blocked"}
        else "required"
    )
    return {
        "schema_version": "mcp_a2a_governance_projection.v1",
        "protocol": normalized_protocol,
        "endpoint_ref": str(endpoint_ref or ""),
        "subject_agent_id": subject_agent_id,
        "resource_scope": resource_scope,
        "requested_by": requested_by,
        "gateway_state": "configured" if endpoint_ref else "required",
        "policy_check_state": safe_policy_state,
        "evidence_state": "summary_only" if endpoint_ref else "missing",
        "summary": {
            "raw_payload_access": "forbidden",
            "direct_connection_allowed": False,
            "runtime_gateway_required": True,
            "runtime_execution_performed": False,
            "external_side_effects_enabled": False,
        },
        "audit_id": f"audit_mcp_a2a_{normalized_protocol}_{subject_agent_id}",
    }


def build_exporter_ecosystem_projection(
    *,
    exporters: list[dict[str, Any]],
    requested_by: str = "system",
) -> dict[str, Any]:
    safe_exporters = [
        _safe_exporter_config(index, exporter)
        for index, exporter in enumerate(exporters, start=1)
    ]
    ecosystem_state = "configured" if safe_exporters else "not_configured"
    return {
        "schema_version": "exporter_ecosystem_projection.v1",
        "exporters": safe_exporters,
        "requested_by": requested_by,
        "ecosystem_state": ecosystem_state,
        "external_write_enabled": False,
        "summary": {
            "raw_payload_access": "forbidden",
            "network_dispatch_performed": False,
            "dry_run_only": True,
            "exporter_material": "hash_ref_summary_only",
        },
        "audit_id": "audit_exporter_ecosystem",
    }


def build_multi_agent_handoff_evaluation(
    repository: InMemoryRepository,
    agent_id: str,
    version: str,
) -> dict[str, Any]:
    runs = repository.runtime_run_records_for_agent_version(agent_id, version)
    handoff_spans = []
    for run in runs:
        for span in repository.trace_span_records_for_run(
            str(run.get("run_id") or ""), attempt_no=run.get("attempt_no")
        ):
            if span.get("span_kind") == "handoff":
                handoff_spans.append(span)

    failed_handoffs = [
        span
        for span in handoff_spans
        if span.get("status_code") in {"error", "blocked"}
        or bool(span.get("error_code"))
    ]
    if not handoff_spans:
        quality_state = "insufficient_data"
    elif failed_handoffs:
        quality_state = "needs_review"
    else:
        quality_state = "healthy"

    return {
        "schema_version": "multi_agent_handoff_evaluation.v1",
        "agent_id": agent_id,
        "version": version,
        "source_run_ids": _unique_strings(
            [str(span.get("run_id") or "") for span in handoff_spans]
        ),
        "handoff_count": len(handoff_spans),
        "failed_handoff_count": len(failed_handoffs),
        "handoff_quality_state": quality_state,
        "handoff_candidates": [_handoff_candidate(span) for span in handoff_spans],
        "summary": {
            "raw_payload_access": "forbidden",
            "automatic_handoff_action": False,
            "runtime_execution_performed": False,
            "derived_from": "trace_span_summary_fields",
        },
        "audit_id": f"audit_handoff_evaluation_{agent_id}_{version}",
    }


def build_complex_risk_profile(
    repository: InMemoryRepository,
    agent_id: str,
    version: str,
) -> dict[str, Any]:
    health_summary = build_runtime_health_summary(repository, agent_id, version)
    dlq_summary = build_dlq_operations_projection(
        repository, agent_id=agent_id, version=version
    )
    handoff_evaluation = build_multi_agent_handoff_evaluation(
        repository, agent_id, version
    )
    risk_factors = _risk_factors(health_summary, dlq_summary, handoff_evaluation)
    risk_profile_state = _risk_profile_state(risk_factors)
    return {
        "schema_version": "complex_risk_profile.v1",
        "agent_id": agent_id,
        "version": version,
        "risk_profile_state": risk_profile_state,
        "risk_factors": risk_factors,
        "recommended_action": _risk_profile_action(risk_profile_state),
        "health_summary": health_summary,
        "handoff_evaluation": {
            "handoff_count": handoff_evaluation["handoff_count"],
            "failed_handoff_count": handoff_evaluation["failed_handoff_count"],
            "handoff_quality_state": handoff_evaluation["handoff_quality_state"],
        },
        "dlq_summary": {
            "backlog_count": dlq_summary["backlog_count"],
            "error_summary": dict(dlq_summary["error_summary"]),
        },
        "summary": {
            "raw_payload_access": "forbidden",
            "automatic_runtime_action": False,
            "automatic_store_action": False,
            "risk_model": "summary_projection_only",
        },
        "audit_id": f"audit_complex_risk_profile_{agent_id}_{version}",
    }


def build_exporter_operation(
    *,
    exporter_type: str,
    endpoint_ref: str = "",
    requested_by: str = "system",
) -> dict[str, Any]:
    if exporter_type not in {"otlp", "openinference"}:
        raise AgentOpsError("EXPORTER_UNSUPPORTED", "Exporter type is unsupported.")
    return {
        "schema_version": "exporter_operation.v1",
        "exporter_type": exporter_type,
        "endpoint_ref": endpoint_ref,
        "requested_by": requested_by,
        "configuration_state": "configured" if endpoint_ref else "not_configured",
        "external_write_enabled": False,
        "dispatch_state": "not_started",
        "summary": {
            "dry_run_only": True,
            "raw_payload_access": "forbidden",
            "network_dispatch_performed": False,
        },
        "audit_id": f"audit_exporter_{exporter_type}",
    }


def build_runtime_slo_summary(
    repository: InMemoryRepository,
    agent_id: str,
    version: str,
    *,
    token_budget: int | None = None,
    cost_budget: float | None = None,
    latency_budget_ms: int | None = None,
) -> dict[str, Any]:
    health_summary = build_runtime_health_summary(repository, agent_id, version)
    budget_summary = build_runtime_budget_summary(
        repository,
        agent_id,
        version,
        token_budget=token_budget,
        cost_budget=cost_budget,
        latency_budget_ms=latency_budget_ms,
    )
    dlq_summary = build_dlq_operations_projection(
        repository, agent_id=agent_id, version=version
    )
    slo_state = _slo_state(health_summary, budget_summary, dlq_summary)
    return {
        "schema_version": "runtime_slo_summary.v1",
        "agent_id": agent_id,
        "version": version,
        "slo_state": slo_state,
        "health_summary": health_summary,
        "budget_summary": budget_summary,
        "dlq_summary": {
            "backlog_count": dlq_summary["backlog_count"],
            "error_summary": dict(dlq_summary["error_summary"]),
        },
        "recommended_action": _slo_action(slo_state),
        "summary": {
            "raw_payload_access": "forbidden",
            "automatic_runtime_action": False,
        },
        "audit_id": f"audit_runtime_slo_{agent_id}_{version}",
    }


def build_store_governance_projection(
    repository: InMemoryRepository,
    agent_id: str,
    version: str,
) -> dict[str, Any]:
    health_summary = build_runtime_health_summary(repository, agent_id, version)
    recommended_action = str(health_summary.get("recommended_action") or "watching")
    risky = recommended_action in {
        "use_with_caution",
        "disable_recommended",
        "disabled",
        "expired",
    }
    return {
        "schema_version": "store_governance_projection.v1",
        "agent_id": agent_id,
        "version": version,
        "summary_state": "expired" if recommended_action == "expired" else "fresh",
        "recommended_action": recommended_action,
        "appeal_state": "available" if risky else "none",
        "owner_notification_state": "pending" if risky else "not_required",
        "replacement_suggestion_state": (
            "suggested"
            if recommended_action == "disable_recommended"
            else "not_required"
        ),
        "summary": {
            "raw_payload_access": "forbidden",
            "display_only": True,
            "automatic_lifecycle_action": False,
        },
        "audit_id": f"audit_store_governance_{agent_id}_{version}",
    }


def _redaction_preview_state(value: str) -> str:
    if value in {"ready", "failed", "not_available"}:
        return value
    return "not_available"


def _safe_experiment_variant(index: int, variant: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(variant, dict):
        raise AgentOpsError(
            "EXPERIMENT_VARIANT_UNSAFE",
            "Experiment variants must be objects.",
        )
    config_ref = str(variant.get("config_ref") or variant.get("artifact_ref") or "")
    safe_source = {
        key: value
        for key, value in variant.items()
        if key not in {"config", "payload", "raw", "raw_payload"}
    }
    return {
        "variant_id": str(variant.get("variant_id") or f"variant_{index}"),
        "variant_type": _variant_type(str(variant.get("variant_type") or "config")),
        "risk_level": _risk_level(str(variant.get("risk_level") or "medium")),
        "config_ref": config_ref,
        "config_hash": _stable_hash(safe_source),
        "execution_state": "not_started",
    }


def _safe_exporter_config(index: int, exporter: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(exporter, dict):
        raise AgentOpsError(
            "EXPORTER_ECOSYSTEM_UNSUPPORTED",
            "Exporter config must be an object.",
            denied_scope="exporter",
            audit_id="audit_exporter_ecosystem",
        )
    exporter_type = str(exporter.get("exporter_type") or exporter.get("type") or "")
    if exporter_type not in SUPPORTED_ECOSYSTEM_EXPORTERS:
        raise AgentOpsError(
            "EXPORTER_ECOSYSTEM_UNSUPPORTED",
            "Exporter type is unsupported.",
            denied_scope="exporter.type",
            audit_id="audit_exporter_ecosystem",
        )
    endpoint_ref = str(exporter.get("endpoint_ref") or "")
    safe_source = {
        key: value
        for key, value in exporter.items()
        if key not in {"config", "payload", "raw", "raw_payload"}
    }
    return {
        "exporter_id": str(exporter.get("exporter_id") or f"exporter_{index}"),
        "exporter_type": exporter_type,
        "endpoint_ref": endpoint_ref,
        "configuration_state": "configured" if endpoint_ref else "not_configured",
        "dispatch_state": "not_started",
        "external_write_enabled": False,
        "configuration_hash": _stable_hash(safe_source),
    }


def _handoff_candidate(span: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": str(span.get("run_id") or ""),
        "trace_id": str(span.get("trace_id") or ""),
        "span_id": str(span.get("span_id") or ""),
        "operation_name": str(span.get("operation_name") or ""),
        "status_code": str(span.get("status_code") or ""),
        "error_code": str(span.get("error_code") or ""),
        "retryable": bool(span.get("retryable", False)),
    }


def _risk_factors(
    health_summary: dict[str, Any],
    dlq_summary: dict[str, Any],
    handoff_evaluation: dict[str, Any],
) -> list[dict[str, Any]]:
    factors = []
    health_action = str(health_summary.get("recommended_action") or "watching")
    if health_action in {"disable_recommended", "disabled"}:
        factors.append(
            {
                "factor": "runtime_health",
                "severity": "critical",
                "state": health_action,
            }
        )
    elif health_action in {"use_with_caution", "expired", "watching"}:
        factors.append(
            {"factor": "runtime_health", "severity": "medium", "state": health_action}
        )
    if dlq_summary.get("backlog_count", 0) > 0:
        factors.append(
            {
                "factor": "runtime_dlq",
                "severity": "high",
                "state": "backlog_present",
            }
        )
    if handoff_evaluation.get("failed_handoff_count", 0) > 0:
        factors.append(
            {
                "factor": "multi_agent_handoff",
                "severity": "high",
                "state": "handoff_failures",
            }
        )
    if not factors:
        factors.append({"factor": "baseline", "severity": "low", "state": "clear"})
    return factors


def _risk_profile_state(factors: list[dict[str, Any]]) -> str:
    severities = {str(factor.get("severity") or "") for factor in factors}
    if "critical" in severities:
        return "critical"
    if "high" in severities:
        return "high"
    if "medium" in severities:
        return "medium"
    return "low"


def _risk_profile_action(risk_profile_state: str) -> str:
    return {
        "low": "none",
        "medium": "watch",
        "high": "open_ops_review",
        "critical": "disable_recommended",
    }[risk_profile_state]


def _safe_policy_change(change: dict[str, Any]) -> dict[str, Any]:
    return {
        "change_type": str(change.get("change_type") or ""),
        "policy_ref": str(change.get("policy_ref") or ""),
        "risk_level": _risk_level(str(change.get("risk_level") or "medium")),
        "change_hash": _stable_hash(change),
    }


def _variant_type(value: str) -> str:
    if value in {"model", "tool", "config", "policy"}:
        return value
    return "config"


def _risk_level(value: str) -> str:
    if value in {"low", "medium", "high", "critical"}:
        return value
    return "medium"


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique = []
    for value in values:
        normalized = str(value)
        if normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return unique


def _redacted_text(value: Any) -> str:
    text = str(value or "")
    if any(marker in text for marker in FORBIDDEN_TEXT_MARKERS):
        return "[redacted]"
    return text


def _stable_hash(value: Any) -> str:
    sanitized = _without_forbidden_keys(value)
    serialized = json.dumps(sanitized, ensure_ascii=False, sort_keys=True, default=str)
    return f"sha256:{hashlib.sha256(serialized.encode('utf-8')).hexdigest()}"


def _without_forbidden_keys(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _without_forbidden_keys(child)
            for key, child in value.items()
            if str(key) not in FORBIDDEN_SUMMARY_KEYS
        }
    if isinstance(value, list | tuple):
        return [_without_forbidden_keys(child) for child in value]
    return value


def _dlq_candidate(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": str(record.get("event_id") or ""),
        "run_id": str(record.get("run_id") or ""),
        "agent_id": str(record.get("agent_id") or ""),
        "version": str(record.get("version") or ""),
        "event_type": str(record.get("event_type") or ""),
        "error_code": str(record.get("error_code") or ""),
        "payload_hash": str(record.get("payload_hash") or ""),
        "payload_ref": str(record.get("payload_ref") or ""),
        "state": str(record.get("state") or ""),
        "retryable": bool(record.get("retryable", False)),
        "received_at": str(record.get("received_at") or ""),
        "recommended_action": "retry" if record.get("retryable", False) else "discard",
    }


def _budget_state(
    *,
    total_tokens: int,
    total_cost: float,
    p95_latency: int,
    token_budget: int | None,
    cost_budget: float | None,
    latency_budget_ms: int | None,
) -> str:
    budgets = [
        (float(total_tokens), float(token_budget or 0)),
        (total_cost, float(cost_budget or 0)),
        (float(p95_latency), float(latency_budget_ms or 0)),
    ]
    active = [(actual, budget) for actual, budget in budgets if budget > 0]
    if not active:
        return "unknown"
    if any(actual > budget for actual, budget in active):
        return "over_budget"
    if any(actual >= budget * 0.8 for actual, budget in active):
        return "at_risk"
    return "within_budget"


def _slo_state(
    health_summary: dict[str, Any],
    budget_summary: dict[str, Any],
    dlq_summary: dict[str, Any],
) -> str:
    health_action = health_summary.get("recommended_action")
    if health_action in {"disable_recommended", "disabled"}:
        return "breached"
    if dlq_summary.get("backlog_count", 0) > 0:
        return "breached"
    if budget_summary.get("budget_state") in {"at_risk", "over_budget"}:
        return "at_risk"
    if health_action in {"use_with_caution", "expired"}:
        return "at_risk"
    if health_action == "watching":
        return "watching"
    return "healthy"


def _slo_action(slo_state: str) -> str:
    return {
        "healthy": "none",
        "watching": "watch",
        "at_risk": "review_budget",
        "breached": "open_ops_review",
    }[slo_state]


def _span_latency_ms(span: dict[str, Any]) -> int | None:
    start = _parse_time(span.get("start_time"))
    end = _parse_time(span.get("end_time"))
    if start is None or end is None or end < start:
        return None
    return int((end - start).total_seconds() * 1000)


def _parse_time(value: Any) -> datetime | None:
    raw = str(value or "")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return _normalize_time(parsed)


def _normalize_time(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _percentile(values: list[int], percentile: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, ceil(len(ordered) * percentile) - 1)
    return ordered[index]


def _safe_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    if isinstance(value, bool):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
