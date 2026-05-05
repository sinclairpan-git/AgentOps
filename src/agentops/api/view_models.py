"""Administrator page view models for stage-1 UX contracts."""

from __future__ import annotations

from datetime import UTC, datetime

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
STAGE2_STATES = ["healthy", "degraded", "unknown", "permission_denied"]


def build_admin_view_models() -> dict[str, list[dict]]:
    return {
        page: [_state_view_model(page, state) for state in STATES]
        for page in PAGES
    }


def _state_view_model(page: str, state: str) -> dict:
    permission_denied = state == "permission_denied"
    model = {
        "page": page,
        "state": state,
        "display_name": state.replace("_", " ").title(),
        "plain_language": _plain_language(state),
        "severity": "critical" if state == "failed" else "warning" if state == "degraded" else "info",
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
        "owner": "AgentOps Owner" if service != "policy_check" else "AgentOps + Security/IAM",
        "request_id": f"req_slo_{service}",
        "captured_at": captured_at or datetime.now(UTC).isoformat(),
    }


def build_stage2_admin_view_models(slo_snapshots: dict[str, dict] | None = None) -> dict[str, list[dict]]:
    slo_snapshots = slo_snapshots or {}
    return {
        page: [_stage2_state_view_model(page, state, slo_snapshots) for state in STAGE2_STATES]
        for page in STAGE2_PAGES
    }


def _stage2_state_view_model(page: str, state: str, slo_snapshots: dict[str, dict]) -> dict:
    service = _page_service(page)
    snapshot = slo_snapshots.get(service) or build_slo_snapshot(service)
    effective_state = snapshot["status"] if state == "healthy" else state
    permission_denied = effective_state == "permission_denied"
    model = {
        "page": page,
        "state": effective_state,
        "display_name": effective_state.replace("_", " ").title(),
        "plain_language": _stage2_plain_language(page, effective_state),
        "severity": "critical" if effective_state == "degraded" else "warning" if effective_state == "unknown" else "info",
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
    return f"{page} 当前状态健康。"


def _stage2_primary_action(page: str, state: str) -> str:
    if state == "degraded":
        return "处理降级"
    if state == "unknown":
        return "刷新状态"
    if state == "permission_denied":
        return "申请权限"
    return "查看详情"
