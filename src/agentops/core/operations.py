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
    "raw_prompt",
    "diff",
    "raw_diff",
    "terminal",
    "terminal_output",
    "pr_body",
    "pr_url",
    "token_secret",
    "credential_secret",
    "device_key",
    "download_url",
    "raw_url",
}
FORBIDDEN_TEXT_MARKERS = (
    "raw_payload",
    "raw_prompt",
    "raw_diff",
    "terminal_output",
    "token_secret",
    "credential_secret",
    "device_key",
    "download_url",
    "raw_url",
    "http://",
    "https://",
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
    resource_scope: str = "",
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
    if not isinstance(exporters, list | tuple):
        raise AgentOpsError(
            "EXPORTER_ECOSYSTEM_UNSUPPORTED",
            "Exporters must be a list.",
            denied_scope="exporters",
            audit_id="audit_exporter_ecosystem",
        )
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


def build_quality_score_projection(
    repository: InMemoryRepository,
    agent_id: str,
    version: str,
    *,
    score_template_id: str = "quality_summary_stage5",
) -> dict[str, Any]:
    health_summary = build_runtime_health_summary(repository, agent_id, version)
    runs = repository.runtime_run_records_for_agent_version(agent_id, version)
    latest_evidence = _latest_evidence_summary(repository, runs)
    eval_cases = [
        record
        for record in repository.eval_case_records()
        if (record.get("source_run") or {}).get("agent_id") == agent_id
        and (record.get("source_run") or {}).get("version") == version
    ]
    missing_evidence = _quality_missing_evidence(
        latest_evidence=latest_evidence,
        eval_case_count=len(eval_cases),
        run_count=len(runs),
    )
    score = _quality_score(health_summary, latest_evidence, len(eval_cases))
    confidence = _quality_confidence(health_summary, latest_evidence)
    quality_state = _quality_state(score, confidence)
    return {
        "schema_version": "quality_score_projection.v1",
        "agent_id": agent_id,
        "version": version,
        "score_template_id": score_template_id,
        "score": score,
        "quality_state": quality_state,
        "evidence_level": str(latest_evidence.get("evidence_level") or "L3"),
        "confidence": confidence,
        "missing_evidence": missing_evidence,
        "explanation": _quality_explanation(
            health_summary, latest_evidence, missing_evidence
        ),
        "source_run_ids": [str(run.get("run_id") or "") for run in runs],
        "health_summary": health_summary,
        "summary": {
            "raw_payload_access": "forbidden",
            "raw_prompt_access": "forbidden",
            "raw_diff_access": "forbidden",
            "score_model": "deterministic_summary_projection",
            "missing_evidence_scored_as_zero": False,
            "automatic_lifecycle_action": False,
            "low_confidence_auto_disable_blocked": confidence < 0.4,
        },
        "audit_id": f"audit_quality_score_{agent_id}_{version}",
    }


def build_quality_scorer_version(
    *,
    scorer_id: str = "quality_summary_stage5",
    scorer_version: str = "1.0.0",
    score_template_id: str = "quality_summary_stage5",
    rollout_state: str = "candidate",
    owner_team: str = "",
    required_evidence: list[str] | None = None,
    scoring_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    safe_rollout_state = (
        rollout_state
        if rollout_state in {"draft", "candidate", "approved", "retired"}
        else "draft"
    )
    policy = _safe_scorer_policy(scoring_policy)
    return {
        "schema_version": "quality_scorer_version.v1",
        "scorer_id": _safe_label(scorer_id) or "quality_summary_stage5",
        "scorer_version": _safe_label(scorer_version) or "1.0.0",
        "score_template_id": _safe_label(score_template_id) or "quality_summary_stage5",
        "rollout_state": safe_rollout_state,
        "owner_team": _safe_label(owner_team),
        "required_evidence": _safe_required_evidence(required_evidence),
        "input_boundary": {
            "accepted_inputs": [
                "runtime_health_summary",
                "runtime_evidence_summary",
                "eval_case_summary",
            ],
            "raw_payload_access": "forbidden",
            "raw_prompt_access": "forbidden",
            "raw_diff_access": "forbidden",
            "terminal_output_access": "forbidden",
        },
        "scoring_policy": policy,
        "summary": {
            "score_model": "deterministic_summary_projection",
            "manual_approval_required": safe_rollout_state != "approved",
            "automatic_rollout_enabled": False,
            "automatic_template_switch": False,
            "store_write_performed": False,
        },
        "audit_id": (
            f"audit_quality_scorer_{_safe_label(scorer_id) or 'quality_summary_stage5'}"
            f"_{_safe_label(scorer_version) or '1.0.0'}"
        ),
    }


def build_quality_scorer_comparison(
    repository: InMemoryRepository,
    agent_id: str,
    version: str,
    *,
    baseline_scorer: dict[str, Any] | None = None,
    candidate_scorer: dict[str, Any] | None = None,
    min_eval_cases: int = 1,
) -> dict[str, Any]:
    if min_eval_cases <= 0:
        raise AgentOpsError(
            "SCORER_COMPARISON_UNAVAILABLE",
            "Scorer comparison evidence threshold must be positive.",
            denied_scope="scorer_comparison.min_eval_cases",
            audit_id=f"audit_quality_scorer_comparison_{agent_id}_{version}",
        )

    baseline = _coerce_scorer_version(
        baseline_scorer,
        default_scorer_id="quality_summary_stage5",
        default_scorer_version="1.0.0",
        default_policy={"evidence_weight": 20, "failure_sensitivity": 25},
    )
    candidate = _coerce_scorer_version(
        candidate_scorer,
        default_scorer_id="quality_summary_stage5_candidate",
        default_scorer_version="1.1.0",
        default_policy={"evidence_weight": 24, "failure_sensitivity": 32},
    )
    eval_cases = [
        record
        for record in repository.eval_case_records()
        if (record.get("source_run") or {}).get("agent_id") == agent_id
        and (record.get("source_run") or {}).get("version") == version
    ]
    source_eval_cases = [str(record.get("eval_case_id") or "") for record in eval_cases]
    if len(eval_cases) < min_eval_cases:
        comparison_state = "insufficient_evidence"
        safety_impact = "needs_review"
        recommendation = "collect_more_samples"
        baseline_alignment = 0.0
        candidate_alignment = 0.0
    else:
        baseline_alignment = _scorer_alignment_score(baseline, eval_cases)
        candidate_alignment = _scorer_alignment_score(candidate, eval_cases)
        safety_impact = _scorer_safety_impact(
            baseline, candidate, baseline_alignment, candidate_alignment
        )
        comparison_state, recommendation = _scorer_comparison_decision(safety_impact)
    alignment_delta = round(candidate_alignment - baseline_alignment, 2)
    return {
        "schema_version": "quality_scorer_comparison.v1",
        "agent_id": agent_id,
        "version": version,
        "source_eval_cases": source_eval_cases,
        "sample_size": len(eval_cases),
        "baseline_scorer": _scorer_ref(baseline, baseline_alignment),
        "candidate_scorer": _scorer_ref(candidate, candidate_alignment),
        "comparison_state": comparison_state,
        "alignment_delta": alignment_delta,
        "safety_impact": safety_impact,
        "recommendation": recommendation,
        "evidence_window": {
            "type": "eval_case_summary",
            "minimum_required": min_eval_cases,
            "sample_size": len(eval_cases),
        },
        "summary": {
            "raw_payload_access": "forbidden",
            "raw_prompt_access": "forbidden",
            "raw_diff_access": "forbidden",
            "terminal_output_access": "forbidden",
            "automatic_rollout_enabled": False,
            "automatic_template_switch": False,
            "automatic_lifecycle_action": False,
            "store_write_performed": False,
            "manual_approval_required": comparison_state
            in {"ready_for_manual_approval", "needs_human_review"},
        },
        "audit_id": f"audit_quality_scorer_comparison_{agent_id}_{version}",
    }


def create_quality_scorer_execution(
    repository: InMemoryRepository,
    agent_id: str,
    version: str,
    *,
    scorer: dict[str, Any] | None = None,
    min_eval_cases: int = 1,
    pass_threshold: float = 0.8,
    executed_by: str = "quality_center",
    now: datetime | None = None,
) -> dict[str, Any]:
    if min_eval_cases <= 0:
        raise AgentOpsError(
            "QUALITY_SCORER_EXECUTION_UNAVAILABLE",
            "Scorer execution evidence threshold must be positive.",
            denied_scope="scorer_execution.min_eval_cases",
            audit_id=f"audit_quality_scorer_execution_{agent_id}_{version}",
        )
    safe_threshold = min(max(_safe_float(pass_threshold), 0.0), 1.0)
    scorer_version = _coerce_scorer_version(
        scorer,
        default_scorer_id="quality_summary_stage5_candidate",
        default_scorer_version="1.1.0",
        default_policy={"evidence_weight": 24, "failure_sensitivity": 32},
    )
    eval_cases = [
        record
        for record in repository.eval_case_records()
        if (record.get("source_run") or {}).get("agent_id") == agent_id
        and (record.get("source_run") or {}).get("version") == version
    ]
    case_results = [
        _scorer_execution_case_result(scorer_version, item) for item in eval_cases
    ]
    outcome_counts = {
        "passed": sum(1 for item in case_results if item["outcome"] == "passed"),
        "warning": sum(1 for item in case_results if item["outcome"] == "warning"),
        "failed": sum(1 for item in case_results if item["outcome"] == "failed"),
        "blocked": sum(1 for item in case_results if item["outcome"] == "blocked"),
    }
    sample_size = len(eval_cases)
    pass_rate = round(outcome_counts["passed"] / sample_size, 4) if sample_size else 0.0
    execution_state, recommendation = _scorer_execution_decision(
        sample_size=sample_size,
        min_eval_cases=min_eval_cases,
        pass_rate=pass_rate,
        pass_threshold=safe_threshold,
        outcome_counts=outcome_counts,
    )
    scores = [item["score"] for item in case_results]
    execution = {
        "schema_version": "quality_scorer_execution.v1",
        "execution_id": "",
        "agent_id": _safe_label(agent_id),
        "version": _safe_label(version),
        "lookup_identity": {
            "agent_id_hash": _quality_scorer_lookup_hash("agent_id", agent_id),
            "version_hash": _quality_scorer_lookup_hash("version", version),
        },
        "scorer": {
            "scorer_id": scorer_version["scorer_id"],
            "scorer_version": scorer_version["scorer_version"],
            "score_template_id": scorer_version["score_template_id"],
            "rollout_state": scorer_version["rollout_state"],
        },
        "source_eval_cases": [
            str(record.get("eval_case_id") or "") for record in eval_cases
        ],
        "sample_size": sample_size,
        "execution_state": execution_state,
        "outcome_counts": outcome_counts,
        "pass_rate": pass_rate,
        "score_summary": {
            "average": round(sum(scores) / len(scores), 4) if scores else 0.0,
            "minimum": min(scores) if scores else 0.0,
            "maximum": max(scores) if scores else 0.0,
            "threshold": safe_threshold,
        },
        "evidence_window": {
            "type": "eval_case_summary",
            "minimum_required": min_eval_cases,
            "sample_size": sample_size,
            "input_boundary": {
                "accepted_inputs": [
                    "eval_case_summary",
                    "runtime_evidence_summary",
                    "scorer_version_summary",
                ],
                "raw_payload_access": "forbidden",
                "raw_prompt_access": "forbidden",
                "raw_diff_access": "forbidden",
                "terminal_output_access": "forbidden",
            },
        },
        "recommendation": recommendation,
        "executed_by": _safe_label(executed_by),
        "executed_at": _normalize_time(now or datetime.now(UTC)).isoformat(),
        "summary": {
            "raw_payload_access": "forbidden",
            "raw_prompt_access": "forbidden",
            "raw_diff_access": "forbidden",
            "terminal_output_access": "forbidden",
            "summary_only_execution": True,
            "external_scorer_invoked": False,
            "automatic_rollout_enabled": False,
            "automatic_template_switch": False,
            "automatic_lifecycle_action": False,
            "store_write_performed": False,
            "notification_sent": False,
            "manual_approval_required": True,
        },
        "case_results": case_results,
        "audit_id": (
            "audit_quality_scorer_execution_"
            f"{_stable_hash([agent_id, version, scorer_version['scorer_id']])[-12:]}"
        ),
    }
    return repository.store_quality_scorer_execution(_without_forbidden_keys(execution))


def build_adoption_roi_projection(
    *,
    agent_id: str,
    version: str,
    adoption_metrics: dict[str, Any],
    owner_team: str = "",
) -> dict[str, Any]:
    safe_metrics = _safe_adoption_metrics(adoption_metrics)
    generated_lines = safe_metrics["generated_lines"]
    retained_lines = safe_metrics["retained_lines"]
    retention_rate = (
        round(retained_lines / generated_lines, 4) if generated_lines > 0 else 0.0
    )
    rework_risk = _rework_risk(safe_metrics)
    adoption_state = _adoption_state(safe_metrics, retention_rate, rework_risk)
    return {
        "schema_version": "adoption_roi_projection.v1",
        "agent_id": agent_id,
        "version": version,
        "owner_team": _safe_label(owner_team),
        "adoption_state": adoption_state,
        "retention_rate": retention_rate,
        "rework_risk": rework_risk,
        "adoption_metrics": safe_metrics,
        "review_summary": {
            "pr_review_issue_count": safe_metrics["pr_review_issue_count"],
            "ci_failure_types": safe_metrics["ci_failure_types"],
            "merge_state": safe_metrics["merge_state"],
            "rollback_count": safe_metrics["rollback_count"],
        },
        "sampling_review_state": safe_metrics["sampling_review_state"],
        "summary": {
            "raw_payload_access": "forbidden",
            "raw_diff_access": "forbidden",
            "raw_pr_access": "forbidden",
            "derived_from": "adoption_summary_metrics",
            "requires_sampling_review": safe_metrics["sampling_review_state"]
            in {"not_started", "pending", "failed"},
        },
        "audit_id": f"audit_adoption_roi_{agent_id}_{version}",
    }


def build_lifecycle_recommendation(
    repository: InMemoryRepository,
    agent_id: str,
    version: str,
) -> dict[str, Any]:
    quality_score = build_quality_score_projection(repository, agent_id, version)
    risk_profile = build_complex_risk_profile(repository, agent_id, version)
    store_governance = build_store_governance_projection(repository, agent_id, version)
    lifecycle_state, recommended_action = _lifecycle_decision(
        quality_score, risk_profile, store_governance
    )
    owner_notification_state = (
        "pending"
        if recommended_action in {"open_ops_review", "open_disable_review"}
        else "not_required"
    )
    appeal_state = (
        "available"
        if recommended_action in {"open_ops_review", "open_disable_review"}
        else "none"
    )
    return {
        "schema_version": "lifecycle_recommendation.v1",
        "agent_id": agent_id,
        "version": version,
        "lifecycle_state": lifecycle_state,
        "recommended_action": recommended_action,
        "owner_notification_state": owner_notification_state,
        "appeal_state": appeal_state,
        "quality_score": {
            "score": quality_score["score"],
            "quality_state": quality_score["quality_state"],
            "confidence": quality_score["confidence"],
            "missing_evidence": list(quality_score["missing_evidence"]),
        },
        "risk_profile": {
            "risk_profile_state": risk_profile["risk_profile_state"],
            "recommended_action": risk_profile["recommended_action"],
        },
        "store_governance": {
            "summary_state": store_governance["summary_state"],
            "recommended_action": store_governance["recommended_action"],
            "appeal_state": store_governance["appeal_state"],
        },
        "summary": {
            "raw_payload_access": "forbidden",
            "automatic_lifecycle_action": False,
            "store_write_performed": False,
            "notification_sent": False,
            "manual_review_required": recommended_action
            in {"collect_more_evidence", "open_ops_review", "open_disable_review"},
        },
        "audit_id": f"audit_lifecycle_recommendation_{agent_id}_{version}",
    }


def build_monthly_quality_report(
    repository: InMemoryRepository,
    *,
    report_period: str,
    agent_refs: list[dict[str, Any]],
    generated_by: str = "system",
) -> dict[str, Any]:
    agent_summaries = []
    for index, ref in enumerate(agent_refs):
        if not isinstance(ref, dict):
            raise AgentOpsError(
                "MONTHLY_REPORT_UNAVAILABLE",
                "Monthly quality report agent_refs entries must be objects.",
                denied_scope=f"agent_refs[{index}]",
                audit_id=f"audit_monthly_quality_{report_period}",
            )
        agent_id = str(ref.get("agent_id") or "")
        version = str(ref.get("version") or "")
        adoption_metrics = (
            ref.get("adoption_metrics")
            if isinstance(ref.get("adoption_metrics"), dict)
            else {}
        )
        quality_score = build_quality_score_projection(repository, agent_id, version)
        lifecycle = build_lifecycle_recommendation(repository, agent_id, version)
        adoption = build_adoption_roi_projection(
            agent_id=agent_id,
            version=version,
            adoption_metrics=adoption_metrics,
            owner_team=str(ref.get("owner_team") or ""),
        )
        agent_summaries.append(
            {
                "agent_id": agent_id,
                "version": version,
                "score": quality_score["score"],
                "quality_state": quality_score["quality_state"],
                "confidence": quality_score["confidence"],
                "risk_action": lifecycle["risk_profile"]["recommended_action"],
                "lifecycle_action": lifecycle["recommended_action"],
                "adoption_state": adoption["adoption_state"],
                "retention_rate": adoption["retention_rate"],
            }
        )
    trend_summary = _monthly_trend_summary(agent_summaries)
    return {
        "schema_version": "monthly_quality_report.v1",
        "report_period": report_period,
        "report_state": "ready" if agent_summaries else "insufficient_data",
        "generated_by": _safe_label(generated_by),
        "agent_summaries": agent_summaries,
        "trend_summary": trend_summary,
        "summary": {
            "raw_payload_access": "forbidden",
            "raw_diff_access": "forbidden",
            "automatic_publish_performed": False,
            "store_write_performed": False,
            "notification_sent": False,
        },
        "audit_id": f"audit_monthly_quality_report_{report_period}",
    }


def build_quality_center_workbench(
    repository: InMemoryRepository,
    *,
    agent_refs: list[dict[str, Any]],
    report_period: str,
    generated_by: str = "quality_center",
) -> dict[str, Any]:
    agent_summaries: list[dict[str, Any]] = []
    review_queue: list[dict[str, Any]] = []
    comparison_counts = {
        "candidate_count": 0,
        "ready_for_manual_approval_count": 0,
        "needs_human_review_count": 0,
        "insufficient_evidence_count": 0,
    }
    for index, ref in enumerate(agent_refs):
        if not isinstance(ref, dict):
            raise AgentOpsError(
                "QUALITY_CENTER_WORKBENCH_UNAVAILABLE",
                "Quality Center agent_refs entries must be objects.",
                denied_scope=f"agent_refs[{index}]",
                audit_id=f"audit_quality_center_{report_period}",
            )
        agent_id = str(ref.get("agent_id") or "")
        version = str(ref.get("version") or "")
        owner_team = _safe_label(ref.get("owner_team") or "")
        candidate_scorer = (
            ref.get("candidate_scorer")
            if isinstance(ref.get("candidate_scorer"), dict)
            else None
        )
        baseline_scorer = (
            ref.get("baseline_scorer")
            if isinstance(ref.get("baseline_scorer"), dict)
            else None
        )
        min_eval_cases = max(1, _safe_int(ref.get("min_eval_cases") or 1))
        quality_score = build_quality_score_projection(repository, agent_id, version)
        lifecycle = build_lifecycle_recommendation(repository, agent_id, version)
        comparison = build_quality_scorer_comparison(
            repository,
            agent_id,
            version,
            baseline_scorer=baseline_scorer,
            candidate_scorer=candidate_scorer,
            min_eval_cases=min_eval_cases,
        )
        scorer_version = build_quality_scorer_version(
            **_quality_center_scorer_kwargs(candidate_scorer)
        )
        execution_records = repository.quality_scorer_execution_records(
            agent_id,
            version,
            scorer_id=str(scorer_version["scorer_id"]),
            scorer_version=str(scorer_version["scorer_version"]),
            limit=1,
        )
        execution_summary = _quality_center_execution_summary(
            execution_records[-1] if execution_records else None
        )
        comparison_state = str(comparison.get("comparison_state") or "")
        comparison_counts["candidate_count"] += 1
        comparison_count_key = f"{comparison_state}_count"
        if comparison_count_key in comparison_counts:
            comparison_counts[comparison_count_key] += 1
        agent_identity = _quality_center_agent_identity(agent_id, version)
        summary = {
            "agent_id": _safe_label(agent_id),
            "version": _safe_label(version),
            "agent_identity": agent_identity,
            "owner_team": owner_team,
            "score": quality_score["score"],
            "quality_state": quality_score["quality_state"],
            "confidence": quality_score["confidence"],
            "score_template_id": quality_score["score_template_id"],
            "evidence_level": quality_score["evidence_level"],
            "missing_evidence": list(quality_score["missing_evidence"]),
            "explanation": quality_score["explanation"],
            "lifecycle_state": lifecycle["lifecycle_state"],
            "lifecycle_action": lifecycle["recommended_action"],
            "scorer": {
                "scorer_id": scorer_version["scorer_id"],
                "scorer_version": scorer_version["scorer_version"],
                "rollout_state": scorer_version["rollout_state"],
            },
            "scorer_comparison": {
                "comparison_state": comparison_state,
                "safety_impact": comparison["safety_impact"],
                "alignment_delta": comparison["alignment_delta"],
                "recommendation": comparison["recommendation"],
                "manual_approval_required": comparison_state
                in {
                    "ready_for_manual_approval",
                    "needs_human_review",
                    "insufficient_evidence",
                },
            },
            "scorer_execution": execution_summary,
        }
        agent_summaries.append(summary)
        review_queue.extend(
            _quality_center_review_items(
                summary,
                quality_score=quality_score,
                lifecycle=lifecycle,
                comparison=comparison,
            )
        )

    monthly_report = build_monthly_quality_report(
        repository,
        report_period=report_period,
        generated_by=generated_by,
        agent_refs=agent_refs,
    )
    return {
        "schema_version": "quality_center_workbench.v1",
        "report_period": report_period,
        "workbench_state": "ready" if agent_summaries else "empty",
        "generated_by": _safe_label(generated_by),
        "agent_summaries": agent_summaries,
        "scorer_rollout_panel": {
            **comparison_counts,
            **_quality_center_execution_counts(agent_summaries, review_queue),
            "automatic_rollout_enabled": False,
            "automatic_template_switch": False,
            "manual_approval_queue_size": sum(
                1
                for item in review_queue
                if item.get("review_type") == "scorer_rollout"
            ),
        },
        "review_queue": review_queue,
        "trend_summary": monthly_report["trend_summary"],
        "summary": {
            "raw_payload_access": "forbidden",
            "raw_prompt_access": "forbidden",
            "raw_diff_access": "forbidden",
            "terminal_output_access": "forbidden",
            "automatic_rollout_enabled": False,
            "automatic_lifecycle_action": False,
            "store_write_performed": False,
            "automatic_publish_performed": False,
            "notification_sent": False,
            "scorer_execution_evidence_count": sum(
                1
                for item in agent_summaries
                if item.get("scorer_execution", {}).get("execution_state")
                != "not_recorded"
            ),
        },
        "audit_id": f"audit_quality_center_workbench_{report_period}",
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


def _latest_evidence_summary(
    repository: InMemoryRepository, runs: tuple[dict[str, Any], ...]
) -> dict[str, Any]:
    if not runs:
        return {
            "evidence_level": "L3",
            "confidence": 0.0,
            "completeness": 0.0,
            "missing_evidence": ["runtime_run"],
        }
    latest_run = runs[-1]
    try:
        return build_runtime_evidence_summary(
            repository, str(latest_run.get("run_id") or "")
        )
    except AgentOpsError:
        return {
            "evidence_level": "L3",
            "confidence": 0.0,
            "completeness": 0.0,
            "missing_evidence": ["runtime_evidence"],
        }


def _quality_missing_evidence(
    *,
    latest_evidence: dict[str, Any],
    eval_case_count: int,
    run_count: int,
) -> list[str]:
    missing = {
        str(item) for item in latest_evidence.get("missing_evidence", []) if str(item)
    }
    if run_count == 0:
        missing.add("runtime_run")
    if eval_case_count == 0:
        missing.add("eval_case")
    return sorted(missing)


def _quality_score(
    health_summary: dict[str, Any],
    latest_evidence: dict[str, Any],
    eval_case_count: int,
) -> float:
    success_rate = _safe_float(health_summary.get("success_rate"))
    failure_rate = _safe_float(health_summary.get("failure_rate"))
    evidence_completeness = _safe_float(latest_evidence.get("completeness"))
    policy_block_count = _safe_int(health_summary.get("policy_block_count"))
    eval_bonus = 5.0 if eval_case_count > 0 else 0.0
    score = (
        35.0
        + (35.0 * success_rate)
        + (20.0 * evidence_completeness)
        + eval_bonus
        - (25.0 * failure_rate)
        - (10.0 * min(policy_block_count, 3))
    )
    return round(max(0.0, min(100.0, score)), 2)


def _quality_confidence(
    health_summary: dict[str, Any], latest_evidence: dict[str, Any]
) -> float:
    health_confidence = _safe_float(health_summary.get("confidence"))
    evidence_confidence = _safe_float(latest_evidence.get("confidence"))
    return round(max(0.0, min(1.0, min(health_confidence, evidence_confidence))), 4)


def _quality_state(score: float, confidence: float) -> str:
    if confidence < 0.4:
        return "insufficient_evidence"
    if score >= 85:
        return "healthy"
    if score >= 70:
        return "watching"
    if score >= 50:
        return "needs_review"
    return "critical"


def _quality_explanation(
    health_summary: dict[str, Any],
    latest_evidence: dict[str, Any],
    missing_evidence: list[str],
) -> dict[str, Any]:
    return {
        "success_rate": _safe_float(health_summary.get("success_rate")),
        "failure_rate": _safe_float(health_summary.get("failure_rate")),
        "evidence_completeness": _safe_float(latest_evidence.get("completeness")),
        "health_window_evidence_completeness": _safe_float(
            health_summary.get("evidence_completeness")
        ),
        "policy_block_count": _safe_int(health_summary.get("policy_block_count")),
        "missing_evidence": list(missing_evidence),
        "guardrail": "low_confidence_requires_manual_review",
    }


def _safe_required_evidence(values: list[str] | None) -> list[str]:
    source = (
        ["runtime_run", "runtime_evidence_summary", "eval_case"]
        if values is None
        else values
    )
    safe_values = [_safe_label(value) for value in source]
    return [value for value in _unique_strings(safe_values) if value]


def _safe_scorer_policy(policy: dict[str, Any] | None) -> dict[str, int]:
    source = policy if isinstance(policy, dict) else {}
    return {
        "evidence_weight": _bounded_policy_weight(source, "evidence_weight", 20),
        "failure_sensitivity": _bounded_policy_weight(
            source, "failure_sensitivity", 25
        ),
    }


def _bounded_policy_weight(
    source: dict[str, Any], field_name: str, default: int
) -> int:
    value = _safe_int(source[field_name]) if field_name in source else default
    return min(max(value, 0), 50)


def _coerce_scorer_version(
    scorer: dict[str, Any] | None,
    *,
    default_scorer_id: str,
    default_scorer_version: str,
    default_policy: dict[str, Any],
) -> dict[str, Any]:
    source = scorer if isinstance(scorer, dict) else {}
    source_policy = (
        source.get("scoring_policy")
        if isinstance(source.get("scoring_policy"), dict)
        else {}
    )
    scoring_policy = {**default_policy, **source_policy}
    return build_quality_scorer_version(
        scorer_id=str(source.get("scorer_id") or default_scorer_id),
        scorer_version=str(source.get("scorer_version") or default_scorer_version),
        score_template_id=str(source.get("score_template_id") or default_scorer_id),
        rollout_state=str(source.get("rollout_state") or "candidate"),
        owner_team=str(source.get("owner_team") or ""),
        required_evidence=source.get("required_evidence")
        if isinstance(source.get("required_evidence"), list)
        else None,
        scoring_policy=scoring_policy,
    )


def _scorer_alignment_score(
    scorer: dict[str, Any], eval_cases: list[dict[str, Any]]
) -> float:
    if not eval_cases:
        return 0.0
    policy = (
        scorer.get("scoring_policy")
        if isinstance(scorer.get("scoring_policy"), dict)
        else {}
    )
    evidence_weight = _safe_int(policy.get("evidence_weight"))
    failure_sensitivity = _safe_int(policy.get("failure_sensitivity"))
    scores = []
    for record in eval_cases:
        source_run = (
            record.get("source_run")
            if isinstance(record.get("source_run"), dict)
            else {}
        )
        evidence_summary = (
            record.get("evidence_summary")
            if isinstance(record.get("evidence_summary"), dict)
            else {}
        )
        status_signal = (
            1.0 if str(source_run.get("status") or "") in FAILURE_SAMPLE_STATES else 0.0
        )
        expected_signal = 1.0 if str(record.get("expected_behavior") or "") else 0.0
        evidence_signal = _safe_float(evidence_summary.get("completeness"))
        scores.append(
            min(
                100.0,
                35.0
                + (evidence_weight * evidence_signal)
                + (failure_sensitivity * status_signal)
                + (10.0 * expected_signal),
            )
        )
    return round(sum(scores) / len(scores), 2)


def _scorer_safety_impact(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    baseline_alignment: float,
    candidate_alignment: float,
) -> str:
    baseline_evidence = set(baseline.get("required_evidence") or [])
    candidate_evidence = set(candidate.get("required_evidence") or [])
    alignment_delta = candidate_alignment - baseline_alignment
    if not candidate_evidence or not candidate_evidence.issuperset(baseline_evidence):
        return "negative"
    if alignment_delta >= 5.0:
        return "improved"
    if alignment_delta < -5.0:
        return "negative"
    if abs(alignment_delta) < 1.0:
        return "neutral"
    return "needs_review"


def _scorer_comparison_decision(safety_impact: str) -> tuple[str, str]:
    if safety_impact == "improved":
        return ("ready_for_manual_approval", "submit_for_manual_rollout_approval")
    if safety_impact == "negative":
        return ("needs_human_review", "keep_baseline")
    return ("needs_human_review", "needs_human_review")


def _scorer_ref(scorer: dict[str, Any], alignment_score: float) -> dict[str, Any]:
    return {
        "scorer_id": scorer["scorer_id"],
        "scorer_version": scorer["scorer_version"],
        "score_template_id": scorer["score_template_id"],
        "rollout_state": scorer["rollout_state"],
        "alignment_score": alignment_score,
    }


def _scorer_execution_case_result(
    scorer: dict[str, Any], eval_case: dict[str, Any]
) -> dict[str, Any]:
    source_run = (
        eval_case.get("source_run")
        if isinstance(eval_case.get("source_run"), dict)
        else {}
    )
    evidence_summary = (
        eval_case.get("evidence_summary")
        if isinstance(eval_case.get("evidence_summary"), dict)
        else {}
    )
    policy = (
        scorer.get("scoring_policy")
        if isinstance(scorer.get("scoring_policy"), dict)
        else {}
    )
    evidence_weight = _safe_float(policy.get("evidence_weight")) / 50.0
    failure_sensitivity = _safe_float(policy.get("failure_sensitivity")) / 50.0
    completeness = min(max(_safe_float(evidence_summary.get("completeness")), 0.0), 1.0)
    status = str(source_run.get("status") or "")
    expected_signal = 1.0 if str(eval_case.get("expected_behavior") or "") else 0.0
    status_signal = 1.0 if status in FAILURE_SAMPLE_STATES else 0.0
    score = round(
        min(
            1.0,
            (0.55 * completeness)
            + (0.25 * status_signal * failure_sensitivity)
            + (0.2 * expected_signal)
            + (0.1 * evidence_weight),
        ),
        4,
    )
    if status in {"blocked", "timeout", "cancelled"}:
        outcome = "blocked"
    elif score >= 0.8:
        outcome = "passed"
    elif score >= 0.55:
        outcome = "warning"
    else:
        outcome = "failed"
    missing_evidence = evidence_summary.get("missing_evidence")
    if not isinstance(missing_evidence, list):
        missing_evidence = []
    source_run_id = str(source_run.get("run_id") or "")
    return {
        "eval_case_id": str(eval_case.get("eval_case_id") or ""),
        "source_run_id": _safe_label(source_run_id),
        "source_run_identity": {
            "run_id_hash": _quality_scorer_lookup_hash("run_id", source_run_id),
        },
        "outcome": outcome,
        "score": score,
        "evidence_level": _safe_label(evidence_summary.get("evidence_level") or ""),
        "missing_evidence_count": len(missing_evidence),
    }


def _scorer_execution_decision(
    *,
    sample_size: int,
    min_eval_cases: int,
    pass_rate: float,
    pass_threshold: float,
    outcome_counts: dict[str, int],
) -> tuple[str, str]:
    if sample_size < min_eval_cases:
        return ("insufficient_evidence", "collect_more_samples")
    if outcome_counts["blocked"] > 0:
        return ("blocked", "open_manual_scorer_review")
    if outcome_counts["failed"] == sample_size:
        return ("failed", "keep_baseline")
    if outcome_counts["failed"] > 0 or pass_rate < pass_threshold:
        return ("needs_review", "open_manual_scorer_review")
    return ("passed", "submit_for_manual_rollout_approval")


def _quality_scorer_lookup_hash(field_name: str, value: Any) -> str:
    material = f"{field_name}\0{str(value or '')}"
    return f"sha256:{hashlib.sha256(material.encode('utf-8')).hexdigest()}"


def _safe_adoption_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    source = metrics if isinstance(metrics, dict) else {}
    ci_failure_types = source.get("ci_failure_types")
    if not isinstance(ci_failure_types, list | tuple):
        ci_failure_types = []
    sampling_review_state = str(
        source.get("sampling_review_state") or "not_started"
    ).lower()
    if sampling_review_state not in {"not_started", "pending", "passed", "failed"}:
        sampling_review_state = "not_started"
    merge_state = _safe_label(source.get("merge_state") or "unknown").lower()
    return {
        "generated_lines": max(0, _safe_int(source.get("generated_lines"))),
        "retained_lines": max(0, _safe_int(source.get("retained_lines"))),
        "modified_lines": max(0, _safe_int(source.get("modified_lines"))),
        "deleted_lines": max(0, _safe_int(source.get("deleted_lines"))),
        "rework_rounds": max(0, _safe_int(source.get("rework_rounds"))),
        "pr_review_issue_count": max(0, _safe_int(source.get("pr_review_issue_count"))),
        "ci_failure_types": [_safe_label(item) for item in ci_failure_types[:10]],
        "merge_state": merge_state,
        "rollback_count": max(0, _safe_int(source.get("rollback_count"))),
        "sampling_review_state": sampling_review_state,
    }


def _safe_label(value: Any) -> str:
    text = str(value or "")
    normalized = text.lower()
    if any(marker.lower() in normalized for marker in FORBIDDEN_TEXT_MARKERS):
        return "[redacted]"
    return text[:80]


def _rework_risk(metrics: dict[str, Any]) -> str:
    if (
        metrics["rollback_count"] > 0
        or metrics["rework_rounds"] >= 3
        or len(metrics["ci_failure_types"]) >= 2
    ):
        return "high"
    if metrics["rework_rounds"] > 0 or metrics["pr_review_issue_count"] > 0:
        return "medium"
    return "low"


def _adoption_state(
    metrics: dict[str, Any], retention_rate: float, rework_risk: str
) -> str:
    if metrics["generated_lines"] == 0:
        return "insufficient_data"
    if rework_risk == "high" or metrics["sampling_review_state"] == "failed":
        return "needs_review"
    if metrics["sampling_review_state"] != "passed":
        return "watching"
    if retention_rate >= 0.6 and metrics["merge_state"] == "merged":
        return "adopted"
    return "watching"


def _lifecycle_decision(
    quality_score: dict[str, Any],
    risk_profile: dict[str, Any],
    store_governance: dict[str, Any],
) -> tuple[str, str]:
    quality_state = str(quality_score.get("quality_state") or "")
    risk_state = str(risk_profile.get("risk_profile_state") or "")
    store_action = str(store_governance.get("recommended_action") or "")
    confidence = _safe_float(quality_score.get("confidence"))
    if confidence < 0.4 or quality_state == "insufficient_evidence":
        return ("review_required", "collect_more_evidence")
    if risk_state == "critical" or store_action in {"disable_recommended", "disabled"}:
        return ("disable_review_recommended", "open_disable_review")
    if risk_state == "high" or quality_state in {"critical", "needs_review"}:
        return ("review_required", "open_ops_review")
    if risk_state == "medium" or quality_state == "watching":
        return ("watching", "watch")
    return ("healthy", "none")


def _monthly_trend_summary(agent_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    if not agent_summaries:
        return {
            "agent_count": 0,
            "average_score": 0.0,
            "review_required_count": 0,
            "adoption_needs_review_count": 0,
        }
    review_required_count = sum(
        1
        for item in agent_summaries
        if item.get("lifecycle_action")
        in {"collect_more_evidence", "open_ops_review", "open_disable_review"}
    )
    adoption_needs_review_count = sum(
        1 for item in agent_summaries if item.get("adoption_state") == "needs_review"
    )
    average_score = round(
        sum(_safe_float(item.get("score")) for item in agent_summaries)
        / len(agent_summaries),
        2,
    )
    return {
        "agent_count": len(agent_summaries),
        "average_score": average_score,
        "review_required_count": review_required_count,
        "adoption_needs_review_count": adoption_needs_review_count,
    }


def _quality_center_scorer_kwargs(
    candidate_scorer: dict[str, Any] | None,
) -> dict[str, Any]:
    source = candidate_scorer if isinstance(candidate_scorer, dict) else {}
    return {
        "scorer_id": str(source.get("scorer_id") or "quality_summary_stage5_candidate"),
        "scorer_version": str(source.get("scorer_version") or "1.1.0"),
        "score_template_id": str(
            source.get("score_template_id") or "quality_summary_stage5_candidate"
        ),
        "rollout_state": str(source.get("rollout_state") or "candidate"),
        "owner_team": str(source.get("owner_team") or ""),
        "required_evidence": source.get("required_evidence")
        if isinstance(source.get("required_evidence"), list)
        else None,
        "scoring_policy": source.get("scoring_policy")
        if isinstance(source.get("scoring_policy"), dict)
        else None,
    }


def _quality_center_execution_summary(
    execution: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(execution, dict):
        return {
            "execution_state": "not_recorded",
            "sample_size": 0,
            "pass_rate": 0.0,
            "manual_review_required": True,
            "recommendation": "collect_more_samples",
            "audit_id": "",
        }
    scorer = (
        execution.get("scorer") if isinstance(execution.get("scorer"), dict) else {}
    )
    return {
        "execution_id": str(execution.get("execution_id") or ""),
        "scorer_id": _safe_label(scorer.get("scorer_id") or ""),
        "scorer_version": _safe_label(scorer.get("scorer_version") or ""),
        "execution_state": _safe_label(execution.get("execution_state") or ""),
        "sample_size": _safe_int(execution.get("sample_size")),
        "pass_rate": round(_safe_float(execution.get("pass_rate")), 4),
        "recommendation": _safe_label(execution.get("recommendation") or ""),
        "manual_review_required": bool(
            execution.get("summary", {}).get("manual_approval_required", True)
        ),
        "automatic_action_performed": False,
        "audit_id": str(execution.get("audit_id") or ""),
    }


def _quality_center_execution_counts(
    agent_summaries: list[dict[str, Any]], review_queue: list[dict[str, Any]]
) -> dict[str, int]:
    execution_summaries = [
        item.get("scorer_execution", {})
        for item in agent_summaries
        if item.get("scorer_execution", {}).get("execution_state") != "not_recorded"
    ]
    states = [str(item.get("execution_state") or "") for item in execution_summaries]
    return {
        "execution_evidence_count": len(execution_summaries),
        "execution_passed_count": states.count("passed"),
        "execution_needs_review_count": sum(
            1 for state in states if state in {"needs_review", "failed", "blocked"}
        ),
        "execution_insufficient_evidence_count": states.count("insufficient_evidence"),
        "execution_manual_review_queue_size": sum(
            1 for item in review_queue if item.get("review_type") == "scorer_execution"
        ),
    }


def _quality_center_agent_identity(agent_id: str, version: str) -> dict[str, str]:
    return {
        "agent_id_hash": _quality_scorer_lookup_hash("agent_id", agent_id),
        "version_hash": _quality_scorer_lookup_hash("version", version),
    }


def _safe_agent_identity(identity: dict[str, Any] | None) -> dict[str, str]:
    source = identity if isinstance(identity, dict) else {}
    agent_id_hash = str(source.get("agent_id_hash") or "")
    version_hash = str(source.get("version_hash") or "")
    return {
        "agent_id_hash": agent_id_hash if agent_id_hash.startswith("sha256:") else "",
        "version_hash": version_hash if version_hash.startswith("sha256:") else "",
    }


def _quality_center_review_items(
    summary: dict[str, Any],
    *,
    quality_score: dict[str, Any],
    lifecycle: dict[str, Any],
    comparison: dict[str, Any],
) -> list[dict[str, Any]]:
    agent_id = str(summary.get("agent_id") or "")
    version = str(summary.get("version") or "")
    owner_team = str(summary.get("owner_team") or "")
    agent_identity = _safe_agent_identity(
        summary.get("agent_identity")
        if isinstance(summary.get("agent_identity"), dict)
        else None
    )
    items: list[dict[str, Any]] = []
    if (
        quality_score.get("missing_evidence")
        or quality_score.get("quality_state") == "insufficient_evidence"
    ):
        items.append(
            _quality_center_review_item(
                agent_id,
                version,
                review_type="quality_evidence",
                reason="missing_or_low_confidence_evidence",
                recommended_action="collect_more_evidence",
                owner_team=owner_team,
                agent_identity=agent_identity,
            )
        )
    comparison_state = str(comparison.get("comparison_state") or "")
    if comparison_state in {
        "ready_for_manual_approval",
        "needs_human_review",
        "insufficient_evidence",
    }:
        items.append(
            _quality_center_review_item(
                agent_id,
                version,
                review_type="scorer_rollout",
                reason=comparison_state,
                recommended_action=str(comparison.get("recommendation") or ""),
                owner_team=owner_team,
                agent_identity=agent_identity,
            )
        )
    scorer_execution = (
        summary.get("scorer_execution")
        if isinstance(summary.get("scorer_execution"), dict)
        else {}
    )
    execution_state = str(scorer_execution.get("execution_state") or "")
    if execution_state in {
        "insufficient_evidence",
        "needs_review",
        "failed",
        "blocked",
    }:
        items.append(
            _quality_center_review_item(
                agent_id,
                version,
                review_type="scorer_execution",
                reason=execution_state,
                recommended_action=str(
                    scorer_execution.get("recommendation")
                    or "open_manual_scorer_review"
                ),
                owner_team=owner_team,
                agent_identity=agent_identity,
            )
        )
    if lifecycle.get("summary", {}).get("manual_review_required"):
        items.append(
            _quality_center_review_item(
                agent_id,
                version,
                review_type="lifecycle",
                reason=str(lifecycle.get("lifecycle_state") or ""),
                recommended_action=str(lifecycle.get("recommended_action") or ""),
                owner_team=owner_team,
                agent_identity=agent_identity,
            )
        )
    return items


def _quality_center_review_item(
    agent_id: str,
    version: str,
    *,
    review_type: str,
    reason: str,
    recommended_action: str,
    owner_team: str,
    agent_identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    safe_review_type = _safe_label(review_type)
    safe_reason = _safe_label(reason)
    safe_identity = _safe_agent_identity(agent_identity)
    return {
        "id": (
            f"quality_center_{safe_review_type}_"
            f"{_stable_hash([safe_identity, safe_reason])[-12:]}"
        ),
        "agent_id": _safe_label(agent_id),
        "version": _safe_label(version),
        "agent_identity": safe_identity,
        "review_type": safe_review_type,
        "reason": safe_reason,
        "recommended_action": _safe_label(recommended_action),
        "owner_team": _safe_label(owner_team),
        "manual_review_required": True,
        "automatic_action_performed": False,
    }


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
    normalized = text.lower()
    if any(marker.lower() in normalized for marker in FORBIDDEN_TEXT_MARKERS):
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
