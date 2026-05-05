"""Administrator page view models for stage-1 UX contracts."""

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
