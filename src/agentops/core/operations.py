"""P1-B evidence, eval, budget, DLQ, exporter, SLO, and Store projections."""

from __future__ import annotations

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


def build_dlq_operations_projection(
    repository: InMemoryRepository,
) -> dict[str, Any]:
    records = repository.runtime_dlq_records()
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
) -> dict[str, Any]:
    health_summary = build_runtime_health_summary(repository, agent_id, version)
    budget_summary = build_runtime_budget_summary(repository, agent_id, version)
    dlq_summary = build_dlq_operations_projection(repository)
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


def _dlq_candidate(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": str(record.get("event_id") or ""),
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
    if budget_summary.get("budget_state") == "over_budget":
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
