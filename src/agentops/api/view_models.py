"""Administrator page view models for stage-1 UX contracts."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

from agentops.core.errors import AgentOpsError
from agentops.core.runtime_contracts import get_state
from agentops.storage.repository import InMemoryRepository

PAGES = [
    "Overview",
    "Runs",
    "Evidence Explorer",
    "Risk Triage",
    "Approval Center",
    "Policy Center",
    "Quality Center",
    "Connector Status",
]

STATES = ["pending", "degraded", "failed", "empty", "permission_denied"]

STAGE2_PAGES = ["Approval Center", "Policy Center", "Evidence Explorer", "Risk Triage"]
STAGE2_PAGE_STATES = {
    "Approval Center": [
        "healthy",
        "pending",
        "needs_more_info",
        "approved",
        "rejected",
        "expired",
        "revoked",
        "escalated",
        "degraded",
        "unknown",
        "permission_denied",
    ],
    "Policy Center": [
        "healthy",
        "block",
        "approval_required",
        "warn",
        "conditional_allow",
        "allow",
        "degraded",
        "unknown",
        "permission_denied",
    ],
    "Evidence Explorer": [
        "healthy",
        "summary_only",
        "pending_approval",
        "approved_limited",
        "expired",
        "redaction_failed",
        "degraded",
        "unknown",
        "permission_denied",
    ],
    "Risk Triage": [
        "healthy",
        "policy_block",
        "approval_overdue",
        "evidence_failed",
        "quality_drop",
        "degraded",
        "unknown",
        "permission_denied",
    ],
}
STAGE2_STATES = sorted(
    {state for states in STAGE2_PAGE_STATES.values() for state in states}
)


def build_admin_view_models() -> dict[str, list[dict]]:
    return {
        page: [_state_view_model(page, state) for state in STATES] for page in PAGES
    }


def _state_view_model(page: str, state: str) -> dict:
    permission_denied = state == "permission_denied"
    model = {
        "page": page,
        "state": state,
        "display_name": state.replace("_", " ").title(),
        "plain_language": _plain_language(state),
        "severity": "critical"
        if state == "failed"
        else "warning"
        if state == "degraded"
        else "info",
        "primary_action": "申请权限" if permission_denied else "查看详情",
        "secondary_action": "返回摘要" if permission_denied else "通知 Owner",
        "owner_hint": "AgentOps Owner",
        "audit_id": "audit_ui_state",
        "request_id": f"req_{page.lower().replace(' ', '_')}_{state}",
        "contains_raw_evidence": False,
        "allowed_transitions": ["pending", "degraded", "failed", "empty"],
    }
    if permission_denied:
        model["denied_scope"] = f"{page}.raw"
    return model


def _plain_language(state: str) -> str:
    return {
        "pending": "数据正在处理，结果尚未完成。",
        "degraded": "部分证据或外部系统不可用，当前结果已降级。",
        "failed": "处理失败，需要人工查看原因并重试或关闭。",
        "empty": "当前没有需要处理的项目。",
        "permission_denied": "你只能查看脱敏摘要，可申请更高权限。",
    }[state]


def build_slo_snapshot(
    service: str,
    *,
    p95_ms: int | None = None,
    error_rate: float | None = None,
    captured_at: str | None = None,
) -> dict:
    status = _slo_status(service, p95_ms, error_rate)
    return {
        "snapshot_id": f"slo_{service}",
        "service": service,
        "p95_ms": p95_ms,
        "error_rate": error_rate,
        "status": status,
        "degrade_action": _slo_degrade_action(service, status),
        "review_required": status == "degraded",
        "owner": "AgentOps Owner"
        if service != "policy_check"
        else "AgentOps + Security/IAM",
        "request_id": f"req_slo_{service}",
        "captured_at": captured_at or datetime.now(UTC).isoformat(),
    }


def build_stage2_admin_view_models(
    slo_snapshots: dict[str, dict] | None = None,
) -> dict[str, list[dict]]:
    slo_snapshots = slo_snapshots or {}
    return {
        page: [
            _stage2_state_view_model(page, state, slo_snapshots)
            for state in STAGE2_PAGE_STATES[page]
        ]
        for page in STAGE2_PAGES
    }


def _stage2_state_view_model(
    page: str, state: str, slo_snapshots: dict[str, dict]
) -> dict:
    service = _page_service(page)
    snapshot = slo_snapshots.get(service) or build_slo_snapshot(service)
    effective_state = snapshot["status"] if state == "healthy" else state
    permission_denied = effective_state == "permission_denied"
    model = {
        "page": page,
        "state": effective_state,
        "display_name": effective_state.replace("_", " ").title(),
        "plain_language": _stage2_plain_language(page, effective_state),
        "severity": "critical"
        if effective_state == "degraded"
        else "warning"
        if effective_state == "unknown"
        else "info",
        "primary_action": _stage2_primary_action(page, effective_state),
        "secondary_action": "返回摘要",
        "owner_hint": snapshot["owner"],
        "request_id": snapshot["request_id"],
        "audit_id": f"audit_stage2_{page.lower().replace(' ', '_')}_{effective_state}",
        "degrade_action": snapshot["degrade_action"],
        "review_required": snapshot["review_required"],
        "contains_raw_evidence": False,
    }
    if permission_denied:
        model["denied_scope"] = f"{page}.stage2"
    return model


def _slo_status(service: str, p95_ms: int | None, error_rate: float | None) -> str:
    if p95_ms is None or error_rate is None:
        return "unknown"
    if service == "policy_check" and (p95_ms > 800 or error_rate > 0.01):
        return "degraded"
    if service == "evidence_query" and p95_ms > 3000:
        return "degraded"
    if service == "approval_service" and p95_ms > 60000:
        return "degraded"
    return "healthy"


def _slo_degrade_action(service: str, status: str) -> str:
    if status == "healthy":
        return "none"
    return {
        "policy_check": "高风险动作 require_online/block，并触发事件复盘。",
        "approval_service": "提醒审批人并升级 IAM。",
        "evidence_query": "回退脱敏摘要，暂停原文查询。",
    }[service]


def _page_service(page: str) -> str:
    return {
        "Approval Center": "approval_service",
        "Policy Center": "policy_check",
        "Evidence Explorer": "evidence_query",
        "Risk Triage": "policy_check",
    }[page]


def _stage2_plain_language(page: str, state: str) -> str:
    if state == "degraded":
        return f"{page} 的关键链路已降级，需要按降级动作处理。"
    if state == "unknown":
        return f"{page} 暂无新鲜 SLO 数据，不能显示为健康。"
    if state == "permission_denied":
        return "你没有查看该治理状态详情的权限，只能查看安全摘要。"
    business_copy = {
        "pending": "审批正在等待处理，请按 SLA 跟进。",
        "needs_more_info": "审批人需要补充材料后才能继续。",
        "approved": "审批已通过，可在授权范围内签发或使用 Grant。",
        "rejected": "审批已拒绝，动作不得继续执行。",
        "expired": "审批或授权已过期，需要重新申请。",
        "revoked": "授权已撤销，后续动作不得继续。",
        "escalated": "审批已升级，需要更高权限处理。",
        "summary_only": "当前仅展示脱敏摘要。",
        "pending_approval": "原文访问申请正在审批中。",
        "approved_limited": "原文访问已限时批准。",
        "redaction_failed": "脱敏失败，只能展示 hash 和告警动作。",
        "block": "策略阻断当前动作。",
        "approval_required": "该动作需要审批后才能继续。",
        "warn": "该动作有风险提示，继续会留下审计记录。",
        "conditional_allow": "该动作已获得限时 Grant。",
        "allow": "该动作已通过策略检查。",
        "policy_block": "存在需要立即处理的策略阻断风险。",
        "approval_overdue": "存在超过 SLA 的审批待办。",
        "evidence_failed": "存在证据失败或 DLQ 风险。",
        "quality_drop": "存在质量下降风险，需要复核。",
    }
    if state in business_copy:
        return business_copy[state]
    return f"{page} 当前状态健康。"


def _stage2_primary_action(page: str, state: str) -> str:
    if state == "degraded":
        return "处理降级"
    if state == "unknown":
        return "刷新状态"
    if state == "permission_denied":
        return "申请权限"
    business_actions = {
        "pending": "处理审批",
        "needs_more_info": "补充材料",
        "approved": "查看 Grant",
        "rejected": "查看拒绝原因",
        "expired": "重新申请",
        "revoked": "查看撤销审计",
        "escalated": "升级处理",
        "summary_only": "申请原文",
        "pending_approval": "查看申请",
        "approved_limited": "查看限时访问",
        "redaction_failed": "通知证据 Owner",
        "block": "查看阻断原因",
        "approval_required": "创建审批",
        "warn": "查看风险提示",
        "conditional_allow": "查看 Grant",
        "allow": "查看裁决",
        "policy_block": "立即阻断",
        "approval_overdue": "催办审批",
        "evidence_failed": "重试证据",
        "quality_drop": "发起复核",
    }
    if state in business_actions:
        return business_actions[state]
    return "查看详情"


def build_runtime_run_detail_projection(
    repository: InMemoryRepository,
    run_id: str,
    *,
    allowed: bool = True,
) -> dict[str, Any]:
    if not allowed:
        raise AgentOpsError(
            "RUN_DETAIL_SCOPE_DENIED",
            "Runtime run detail requires runtime.run.read permission.",
            audit_id=f"audit_runtime_run_{run_id}",
            request_id=f"req_runtime_run_{run_id}",
            denied_scope="runtime.run.read",
        )

    run = repository.get_runtime_run_fact(run_id)
    if run is None:
        raise AgentOpsError(
            "RUNTIME_RUN_NOT_FOUND",
            "Runtime run fact was not found.",
            audit_id=f"audit_runtime_run_{run_id}",
            request_id=f"req_runtime_run_{run_id}",
        )

    state = get_state(_run_display_state(run))
    spans = repository.trace_span_records_for_run(
        run_id, attempt_no=run.get("attempt_no")
    )
    guardrail_results = repository.guardrail_result_records_for_run(
        run_id, attempt_no=run.get("attempt_no")
    )
    trace_state = "complete" if spans else "pending"
    return {
        "run": run,
        "display_state": state.to_stable_dict(),
        "next_action": state.primary_action,
        "policy_summary": _runtime_policy_summary(run),
        "approval_summary": _runtime_approval_summary(run),
        "guardrail_summary": _runtime_guardrail_summary(spans, guardrail_results),
        "artifact_refs": _runtime_artifact_refs(spans),
        "outbox_state": "delivered" if spans else "pending",
        "trace_state": trace_state,
        "audit_id": f"audit_runtime_run_{run_id}",
    }


def build_trace_timeline_projection(
    repository: InMemoryRepository,
    run_id: str,
    *,
    request_raw: bool = False,
    raw_access_allowed: bool = False,
) -> dict[str, Any]:
    if request_raw and not raw_access_allowed:
        raise AgentOpsError(
            "RAW_ACCESS_REQUIRED",
            "Raw trace input/output requires Evidence Vault approval.",
            audit_id=f"audit_runtime_trace_{run_id}",
            request_id=f"req_runtime_trace_{run_id}",
            denied_scope="runtime.trace.raw",
        )

    run = repository.get_runtime_run_fact(run_id)
    if run is None:
        raise AgentOpsError(
            "RUNTIME_RUN_NOT_FOUND",
            "Runtime run fact was not found.",
            audit_id=f"audit_runtime_trace_{run_id}",
            request_id=f"req_runtime_trace_{run_id}",
        )

    spans = list(
        repository.trace_span_records_for_run(run_id, attempt_no=run.get("attempt_no"))
    )
    guardrail_results = list(
        repository.guardrail_result_records_for_run(
            run_id, attempt_no=run.get("attempt_no")
        )
    )
    trace_id = str(spans[0].get("trace_id")) if spans else ""
    degraded_reason = _timeline_degraded_reason(spans)
    return {
        "trace_id": trace_id,
        "run_id": run_id,
        "spans": [_trace_span_projection(span, guardrail_results) for span in spans],
        "degraded": bool(degraded_reason),
        "degraded_reason": degraded_reason,
        "redaction_state": "raw" if raw_access_allowed else "summary_only",
        "aggregate": _trace_aggregate(spans),
    }


def _run_display_state(run: dict[str, Any]) -> str:
    status = str(run.get("status") or "degraded")
    if status in {
        "created",
        "running",
        "approval_paused",
        "succeeded",
        "failed",
        "cancelled",
        "timeout",
        "blocked",
    }:
        return status
    return "degraded"


def _runtime_policy_summary(run: dict[str, Any]) -> dict[str, str] | None:
    terminal_reason = str(run.get("terminal_reason") or "")
    if "policy" not in terminal_reason and run.get("status") != "blocked":
        return None
    return {
        "decision": "block",
        "reason_code": terminal_reason or "policy_block",
        "fallback_action": "require_online",
        "policy_set_version": str(run.get("policy_bundle_version") or "unknown"),
    }


def _runtime_approval_summary(run: dict[str, Any]) -> dict[str, str] | None:
    if run.get("status") != "approval_paused":
        return None
    return {
        "approval_id": f"approval_{run['run_id']}",
        "status": "pending",
        "primary_action": "查看审批进度",
    }


def _runtime_guardrail_summary(
    spans: tuple[dict[str, Any], ...],
    guardrail_results: tuple[dict[str, Any], ...],
) -> list[dict[str, str]]:
    summaries = [_guardrail_result_summary(result) for result in guardrail_results]
    resolved_span_ids = {
        str(result.get("span_id"))
        for result in guardrail_results
        if result.get("span_id") not in (None, "")
    }
    summaries.extend(
        _guardrail_span_summary(span)
        for span in spans
        if span.get("span_kind") == "guardrail"
        and str(span.get("span_id")) not in resolved_span_ids
    )
    return summaries


def _runtime_artifact_refs(spans: tuple[dict[str, Any], ...]) -> list[dict[str, str]]:
    return [
        {
            "span_id": str(span.get("span_id")),
            "output_ref": str(span.get("output_ref") or ""),
        }
        for span in spans
        if span.get("span_kind") == "artifact"
    ]


def _trace_span_projection(
    span: dict[str, Any],
    guardrail_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    guardrail_results = guardrail_results or []
    return {
        "trace_id": span.get("trace_id"),
        "span_id": span.get("span_id"),
        "parent_span_id": span.get("parent_span_id"),
        "span_kind": span.get("span_kind"),
        "operation_name": span.get("operation_name"),
        "status_code": span.get("status_code"),
        "start_time": span.get("start_time"),
        "end_time": span.get("end_time"),
        "duration_ms": _trace_duration_ms(span),
        "input_ref": span.get("input_ref"),
        "output_ref": span.get("output_ref"),
        "error_code": span.get("error_code"),
        "retryable": span.get("retryable"),
        "guardrail_result_refs": list(span.get("guardrail_result_refs") or []),
        "guardrail_results": _span_guardrail_results(span, guardrail_results),
    }


def _span_guardrail_results(
    span: dict[str, Any], guardrail_results: list[dict[str, Any]]
) -> list[dict[str, str]]:
    refs = {str(ref) for ref in span.get("guardrail_result_refs") or []}
    if not refs:
        return []
    return [
        _guardrail_result_summary(result)
        for result in guardrail_results
        if str(result.get("guardrail_result_id")) in refs
    ]


def _guardrail_result_summary(result: dict[str, Any]) -> dict[str, str]:
    return {
        "guardrail_result_id": str(result.get("guardrail_result_id")),
        "span_id": str(result.get("span_id")),
        "guardrail_id": str(result.get("guardrail_id")),
        "status": str(result.get("status")),
        "severity": str(result.get("severity")),
        "reason_code": str(result.get("reason_code")),
        "evidence_ref": str(result.get("evidence_ref") or ""),
    }


def _guardrail_span_summary(span: dict[str, Any]) -> dict[str, str]:
    return {
        "span_id": str(span.get("span_id")),
        "operation_name": str(span.get("operation_name")),
        "status_code": str(span.get("status_code")),
    }


def _trace_duration_ms(span: dict[str, Any]) -> int:
    start_time = _parse_runtime_timestamp(span.get("start_time"))
    end_time = _parse_runtime_timestamp(span.get("end_time"))
    if start_time is None or end_time is None:
        return 0
    duration = (end_time - start_time).total_seconds() * 1000
    return max(0, int(round(duration)))


def _parse_runtime_timestamp(value: Any) -> datetime | None:
    raw_value = str(value or "")
    try:
        parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _timeline_degraded_reason(spans: list[dict[str, Any]]) -> str | None:
    if not spans:
        return "trace_pending"
    span_ids = {
        (str(span.get("trace_id") or ""), str(span.get("span_id") or ""))
        for span in spans
    }
    for span in spans:
        trace_id = str(span.get("trace_id") or "")
        parent_span_id = str(span.get("parent_span_id") or "")
        if parent_span_id and (trace_id, parent_span_id) not in span_ids:
            return "TRACE_PARENT_MISSING"
    return None


def _trace_aggregate(spans: list[dict[str, Any]]) -> dict[str, Any]:
    input_tokens = 0
    output_tokens = 0
    cost_amount = 0.0
    currency = "unknown"
    for span in spans:
        token_usage = span.get("token_usage") or {}
        input_tokens += _safe_int(token_usage.get("input"))
        output_tokens += _safe_int(token_usage.get("output"))
        cost_estimate = span.get("cost_estimate") or {}
        cost_amount += _safe_float(cost_estimate.get("amount"))
        if cost_estimate.get("currency"):
            currency = str(cost_estimate["currency"])
    return {
        "span_count": len(spans),
        "token_usage": {"input": input_tokens, "output": output_tokens},
        "cost_estimate": {"amount": round(cost_amount, 6), "currency": currency},
    }


def _safe_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        try:
            numeric_value = float(value)
        except OverflowError:
            return 0
        return int(numeric_value) if math.isfinite(numeric_value) else 0
    if isinstance(value, str):
        try:
            numeric_value = float(value)
        except (OverflowError, ValueError):
            return 0
        return int(numeric_value) if math.isfinite(numeric_value) else 0
    return 0


def _safe_float(value: Any) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        try:
            numeric_value = float(value)
        except OverflowError:
            return 0.0
        return numeric_value if math.isfinite(numeric_value) else 0.0
    if isinstance(value, str):
        try:
            numeric_value = float(value)
        except (OverflowError, ValueError):
            return 0.0
        return numeric_value if math.isfinite(numeric_value) else 0.0
    return 0.0
