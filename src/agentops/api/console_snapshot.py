"""Console snapshot view model for the AgentOps frontend."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from agentops.core.l5_gate import evaluate_l5_gate
from agentops.storage.repository import InMemoryRepository

SCHEMA_VERSION = "agentops.console.snapshot.v1"

ROUTES = [
    {"id": "overview", "label": "总览", "icon": "⌂"},
    {"id": "runs", "label": "运行记录", "icon": "▶"},
    {"id": "evidence", "label": "证据检索", "icon": "◇"},
    {"id": "approvals", "label": "审批中心", "icon": "✓"},
    {"id": "policies", "label": "策略中心", "icon": "!"},
    {"id": "quality", "label": "质量中心", "icon": "质"},
    {"id": "risks", "label": "风险处置", "icon": "△"},
    {"id": "connectors", "label": "连接器状态", "icon": "∞"},
    {"id": "sdlc-runs", "label": "Ai_AutoSDLC 运行", "icon": "SD"},
]


def build_console_snapshot(*, generated_at: str | None = None, repository: InMemoryRepository | None = None) -> dict[str, Any]:
    """Build a safe snapshot matching the Vue2 Console information architecture."""

    console_data = _console_data_from_repository(repository) if repository is not None else _console_data()
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at or datetime.now(UTC).isoformat(),
        "source": "api_snapshot",
        "source_detail": {
            "mode": "repository_backed" if repository is not None else "sample_fixture",
            "fact_source": "InMemoryRepository" if repository is not None else "console_snapshot_fixture",
        },
        "routes": [dict(route) for route in ROUTES],
        "consoleData": console_data,
    }


def _console_data_from_repository(repository: InMemoryRepository) -> dict[str, Any]:
    events_by_run: dict[str, list[dict[str, Any]]] = defaultdict(list)
    raw_events = repository.raw_event_records()
    for event in raw_events:
        run_id = str(event.get("run_id") or _event_payload(event).get("run_id") or "unknown_run")
        events_by_run[run_id].append(event)

    run_models: list[dict[str, str]] = []
    evidence_models: list[dict[str, str]] = []
    risk_models: list[dict[str, str]] = []
    quality_models: list[dict[str, str]] = []
    l5_count = 0
    pending_count = 0
    degraded_count = 0

    for run_id in sorted(events_by_run):
        events = sorted(events_by_run[run_id], key=_event_sequence_no)
        l5_input = _last_payload(events, "l5_eligibility_input")
        governance_state = _governance_state(events)
        policy_state_known = _strict_bool(l5_input.get("policy_state_known"), default=True)
        outbox_status = str(l5_input.get("outbox_status", "delivered"))
        evaluation = evaluate_l5_gate(
            events,
            governance_state=governance_state,
            outbox_status=outbox_status,
            policy_state_known=policy_state_known,
        )
        l5_state = _l5_state(evaluation["result"])
        policy_state = "allow" if policy_state_known else "block"
        evidence_state = "summary_only" if evaluation["result"] == "L5" else "degraded"
        agent = str(events[0].get("agent_id") or "未知 Agent")
        skill = _run_skill(events)
        risk_level = "低" if evaluation["result"] == "L5" else "高"

        if evaluation["result"] == "L5":
            l5_count += 1
        elif evaluation["result"] == "pending":
            pending_count += 1
        else:
            degraded_count += 1

        run_models.append(_run(run_id, agent, skill, risk_level, l5_state, policy_state, evidence_state))
        evidence_models.append(
            _evidence(
                f"ev_{run_id}",
                run_id,
                _evidence_summary(evaluation, events),
                _payload_hash(events),
                evidence_state,
                f"audit_{run_id}",
            )
        )

        if evaluation["failed_conditions"]:
            risk_models.append(
                _risk(
                    f"risk_{run_id}",
                    "运行记录",
                    "高",
                    "degraded",
                    "AgentOps 管理员",
                    "查看降级原因",
                    "runs",
                )
            )

        quality_models.append(
            _quality(
                f"qs_{run_id}",
                "L5 证据完整性",
                l5_state,
                evaluation["evidence_level"],
                ",".join(sorted({event["event_type"] for event in events})),
                "AI-SDLC 负责人",
                "补齐缺失证据" if evaluation["missing_evidence"] or evaluation["failed_conditions"] else "保持基线",
            )
        )

    run_count = len(run_models)
    approvals = [_approval_from_record(approval) for approval in repository.approval_records()]
    approval_pending_count = sum(1 for approval in approvals if approval["status"] in {"pending", "escalated"})
    metrics = [
        {"label": "今日运行", "value": run_count, "status": "healthy" if run_count else "empty", "detail": f"{l5_count} 条 L5，{degraded_count} 条降级，{pending_count} 条待补偿"},
        {"label": "Policy SLO", "value": "本地内核", "status": "healthy", "detail": "当前由可执行内核生成策略摘要"},
        {"label": "审批待办", "value": approval_pending_count, "status": "pending" if approval_pending_count else "healthy", "detail": "来自 AgentOps 审批仓库事实"},
        {"label": "证据状态", "value": f"{len(evidence_models)} 条摘要", "status": "healthy" if evidence_models else "empty", "detail": "仅展示脱敏摘要和哈希，不暴露原文"},
    ]

    return {
        "summary": {
            "adapter": {
                "status": "materialized",
                "copy": "后端事实仓库已连接；adapter 仍需 verified_loaded 机器证明。",
                "proof_source": "InMemoryRepository 运行事实",
                "captured_at": datetime.now(UTC).isoformat(),
            },
            "metrics": metrics,
        },
        "runs": run_models,
        "evidence": evidence_models,
        "approvals": approvals,
        "policies": _policies_from_grants(repository.grant_records()),
        "risks": risk_models,
        "quality": quality_models,
        "connectors": _repository_connectors(repository, event_count=len(raw_events)),
        "sdlcRuns": _repository_sdlc_runs(repository, event_count=len(raw_events)),
    }


def _governance_state(events: list[dict[str, Any]]) -> str:
    for event in reversed(events):
        payload = _event_payload(event)
        if event.get("event_type") == "stage_started":
            return str(payload.get("adapter_state") or "materialized")
    return "materialized"


def _last_payload(events: list[dict[str, Any]], event_type: str) -> dict[str, Any]:
    for event in reversed(events):
        payload = _event_payload(event)
        if event.get("event_type") == event_type:
            return dict(payload)
    return {}


def _event_payload(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload")
    return dict(payload) if isinstance(payload, dict) else {}


def _event_sequence_no(event: dict[str, Any]) -> int:
    try:
        return int(event.get("sequence_no", 0))
    except (TypeError, ValueError):
        return 0


def _strict_bool(value: Any, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    return default


def _l5_state(result: str) -> str:
    if result == "L5":
        return "healthy"
    if result == "pending":
        return "pending"
    return "degraded"


def _run_skill(events: list[dict[str, Any]]) -> str:
    for event in events:
        payload = event.get("payload", {})
        if event.get("event_type") == "stage_started" and isinstance(payload, dict):
            return str(payload.get("stage_name") or "治理运行")
    return "治理运行"


def _evidence_summary(evaluation: dict[str, Any], events: list[dict[str, Any]]) -> str:
    if evaluation["result"] == "L5":
        return f"已接收 {len(events)} 条签名事件，核心证据链完整。"
    missing = "、".join(evaluation["missing_evidence"] or evaluation["failed_conditions"])
    return f"已接收 {len(events)} 条事件，但仍缺少：{missing}。"


def _payload_hash(events: list[dict[str, Any]]) -> str:
    for event in events:
        payload_hash = str(event.get("payload_hash") or "")
        if payload_hash:
            return payload_hash
    return "sha256:missing"


def _approval_from_record(approval: dict[str, Any]) -> dict[str, str]:
    approval_id = str(approval["approval_id"])
    return {
        "approval_id": approval_id,
        "id": approval_id,
        "requester": str(approval.get("requester") or approval.get("agent_id") or "未知申请方"),
        "reason": str(approval.get("reason") or approval.get("request_reason") or "需要审批后继续"),
        "affected_actions": str(approval.get("affected_actions") or approval.get("resource_scope") or "未声明动作"),
        "sla_due_at": str(approval.get("sla_due_at") or approval.get("expires_at") or "待确认"),
        "status": str(approval.get("status") or "pending"),
        "grant_status": str(approval.get("grant_status") or "pending"),
        "audit_id": str(approval.get("audit_id") or f"audit_{approval_id}"),
    }


def _policies_from_grants(grants: tuple[dict[str, Any], ...]) -> list[dict[str, str]]:
    if not grants:
        return [
            _policy("pol_repository_default", "warn", "本地事实接入", "require_online", "runtime-v2", "无", "audit_repository_default")
        ]
    return [
        _policy(
            str(grant.get("grant_id") or "grant_unknown"),
            "conditional_allow" if grant.get("status") == "active" else "block",
            str(grant.get("resource_scope") or "未声明动作"),
            "require_online",
            str(grant.get("policy_version") or "runtime-v2"),
            str(grant.get("expires_at") or "待确认"),
            str(grant.get("audit_id") or f"audit_{grant.get('grant_id') or 'grant_unknown'}"),
        )
        for grant in sorted(grants, key=lambda item: str(item.get("grant_id") or "grant_unknown"))
    ]


def _repository_connectors(repository: InMemoryRepository, *, event_count: int | None = None) -> list[dict[str, str]]:
    now = datetime.now(UTC).isoformat()
    event_count = repository.raw_event_count() if event_count is None else event_count
    return [
        _connector("conn_ingestion", "事件接入", "healthy", now, "无", "req_conn_ingestion"),
        _connector("conn_repository", "运行事实仓库", "healthy", now, f"{event_count} 条事件", "req_conn_repository"),
        _connector("conn_sdlc", "Ai_AutoSDLC", "materialized", now, "需要 verified_loaded 机器证明", "req_conn_sdlc"),
        _connector("conn_evidence", "证据存储", "healthy", now, "仅展示摘要", "req_conn_evidence"),
        _connector("conn_policy", "策略服务", "healthy", now, "本地内核策略摘要", "req_conn_policy"),
    ]


def _repository_sdlc_runs(repository: InMemoryRepository, *, event_count: int | None = None) -> list[dict[str, str]]:
    now = datetime.now(UTC).isoformat()
    event_count = repository.raw_event_count() if event_count is None else event_count
    return [
        _sdlc_run("sdlc_repository_snapshot", "console repository snapshot", "materialized", "dry_run_passed", "InMemoryRepository", now),
        _sdlc_run("sdlc_repository_events", "ingestion event count", "materialized", "dry_run_passed", f"{event_count} 条事件", now),
    ]


def _console_data() -> dict[str, Any]:
    return {
        "summary": {
            "adapter": {
                "status": "materialized",
                "copy": "后端快照已连接；adapter 仍需 verified_loaded 机器证明。",
                "proof_source": "AGENTS.md 规范路径",
                "captured_at": "2026-05-06T05:20:00Z",
            },
            "metrics": [
                {"label": "今日运行", "value": 42, "status": "healthy", "detail": "39 条可信，3 条需复核"},
                {
                    "label": "Policy SLO",
                    "value": "P95 860ms",
                    "status": "degraded",
                    "detail": "高风险动作需在线校验/阻断（require_online/block）",
                },
                {"label": "审批待办", "value": 7, "status": "pending", "detail": "2 条超过 SLA 并已升级"},
                {"label": "证据状态", "value": "1 条失败", "status": "redaction_failed", "detail": "原文访问已阻断"},
            ],
        },
        "runs": [
            _run("run_20260506_001", "发布 Agent", "生产部署", "高", "healthy", "approval_required", "summary_only"),
            _run("run_20260506_002", "质检 Agent", "测试执行", "中", "healthy", "conditional_allow", "approved_limited"),
            _run("run_20260506_003", "迁移 Agent", "结构变更", "高", "degraded", "block", "redaction_failed"),
            _run("run_20260506_004", "商店 Agent", "发布上架", "低", "unknown", "warn", "summary_only"),
        ],
        "evidence": [
            _evidence("ev_001", "run_20260506_001", "部署命令摘要已移除敏感值。", "sha256:7a21...", "summary_only", "audit_ev_001"),
            _evidence("ev_002", "run_20260506_002", "已获得短时复核窗口的限时授权。", "sha256:91be...", "approved_limited", "audit_ev_002"),
            _evidence(
                "ev_003",
                "run_20260506_003",
                "脱敏失败，仅保留哈希和告警。",
                "sha256:ff03...",
                "redaction_failed",
                "audit_ev_003",
                denied_scope="evidence.raw",
            ),
            _evidence(
                "ev_004",
                "run_20260506_004",
                "权限边界隐藏详情，可申请限定范围访问。",
                "sha256:a031...",
                "permission_denied",
                "audit_ev_004",
                denied_scope="证据检索.阶段2",
            ),
        ],
        "approvals": [
            _approval("ap_001", "发布 Agent", "生产部署需要短期 Grant", "deploy:prod", "2026-05-06 13:20", "pending", "pending"),
            _approval("ap_002", "质检 Agent", "复核失败的测试证据", "evidence.raw", "2026-05-06 12:40", "escalated", "expired"),
            _approval("ap_003", "迁移 Agent", "结构迁移被策略阻断", "db.migrate", "2026-05-06 14:00", "approved", "active"),
            _approval("ap_004", "商店 Agent", "已接受发布风险提示", "store.publish", "2026-05-06 13:10", "revoked", "revoked"),
        ],
        "policies": [
            _policy("pol_001", "approval_required", "deploy:prod", "require_online", "runtime-v2.3", "15 分钟", "audit_pol_001"),
            _policy("pol_002", "block", "db.migrate", "block", "runtime-v2.3", "无", "audit_pol_002"),
            _policy("pol_003", "conditional_allow", "test:run", "无", "runtime-v2.2", "10 分钟", "audit_pol_003"),
            _policy("pol_004", "unknown", "store.publish", "警告", "runtime-v2.1", "无", "req_policy_unknown"),
        ],
        "risks": [
            _risk("risk_001", "策略中心", "严重", "block", "安全/IAM", "复核拒绝优先级（deny）", "policies"),
            _risk("risk_002", "审批中心", "高", "escalated", "发布审批人", "升级审批", "approvals"),
            _risk("risk_003", "证据检索", "高", "redaction_failed", "证据负责人", "仅检查哈希", "evidence"),
            _risk("risk_004", "Ai_AutoSDLC 运行", "中", "unverified", "SDLC 负责人", "加载验证证明", "sdlc-runs"),
        ],
        "quality": [
            _quality("qs_001", "契约测试", "healthy", "88/88", "AO1/AO2/AO3 契约套件", "AgentOps 后端", "保持基线"),
            _quality("qs_002", "Browser Gate", "healthy", "已通过", "AO3 浏览器证据", "前端负责人", "持续采集"),
            _quality("qs_003", "证据完整性", "redaction_failed", "91%", "ev_003 已保留哈希", "证据负责人", "修复脱敏"),
            _quality("qs_004", "策略可解释性", "unknown", "需证明", "策略要求摘要", "安全/IAM", "刷新 SLO"),
        ],
        "connectors": [
            _connector("conn_agent_store", "Agent Store", "healthy", "2026-05-06 05:20", "无", "req_conn_agent_store"),
            _connector("conn_sdlc", "Ai_AutoSDLC", "materialized", "2026-05-06 05:20", "需要 verified_loaded 证明", "req_conn_sdlc"),
            _connector("conn_evidence", "证据存储", "degraded", "2026-05-06 05:18", "仅展示摘要", "req_conn_evidence"),
            _connector("conn_policy", "策略服务", "degraded", "2026-05-06 05:19", "高风险需在线校验/阻断（require_online/block）", "req_conn_policy"),
            _connector("conn_iam", "IAM/安全", "healthy", "2026-05-06 05:20", "无", "req_conn_iam"),
        ],
        "sdlcRuns": [
            _sdlc_run("sdlc_001", "ai-sdlc adapter status", "materialized", "dry_run_passed", "AGENTS.md", "2026-05-06 05:20"),
            _sdlc_run("sdlc_002", "ai-sdlc run --dry-run", "materialized", "dry_run_passed", "CLI 预演", "2026-05-06 05:21"),
            _sdlc_run("sdlc_003", "governance load probe", "materialized", "dry_run_passed", "待接入治理加载探针", "待采集"),
        ],
    }


def _run(run_id: str, agent: str, skill: str, risk_level: str, l5_state: str, policy_state: str, evidence_state: str) -> dict[str, str]:
    return {
        "run_id": run_id,
        "id": run_id,
        "agent": agent,
        "skill": skill,
        "risk_level": risk_level,
        "l5_state": l5_state,
        "policy_state": policy_state,
        "evidence_state": evidence_state,
    }


def _evidence(
    evidence_id: str,
    run_id: str,
    summary: str,
    payload_hash: str,
    raw_access_state: str,
    audit_id: str,
    *,
    denied_scope: str = "",
) -> dict[str, str]:
    return {
        "evidence_id": evidence_id,
        "id": evidence_id,
        "run_id": run_id,
        "summary": summary,
        "payload_hash": payload_hash,
        "raw_access_state": raw_access_state,
        "audit_id": audit_id,
        "denied_scope": denied_scope,
    }


def _approval(
    approval_id: str,
    requester: str,
    reason: str,
    affected_actions: str,
    sla_due_at: str,
    status: str,
    grant_status: str,
) -> dict[str, str]:
    return {
        "approval_id": approval_id,
        "id": approval_id,
        "requester": requester,
        "reason": reason,
        "affected_actions": affected_actions,
        "sla_due_at": sla_due_at,
        "status": status,
        "grant_status": grant_status,
        "audit_id": f"audit_{approval_id}",
    }


def _policy(
    policy_id: str,
    decision: str,
    action: str,
    fallback_action: str,
    policy_version: str,
    grant_ttl: str,
    audit_id: str,
) -> dict[str, str]:
    return {
        "id": policy_id,
        "decision": decision,
        "action": action,
        "fallback_action": fallback_action,
        "policy_version": policy_version,
        "grant_ttl": grant_ttl,
        "audit_id": audit_id,
    }


def _risk(risk_id: str, source: str, severity: str, state: str, owner_hint: str, primary_action: str, deep_link: str) -> dict[str, str]:
    return {
        "id": risk_id,
        "source": source,
        "severity": severity,
        "state": state,
        "owner_hint": owner_hint,
        "primary_action": primary_action,
        "deep_link": deep_link,
    }


def _quality(signal_id: str, category: str, status: str, score: str, evidence_ref: str, owner_hint: str, primary_action: str) -> dict[str, str]:
    return {
        "id": signal_id,
        "signal_id": signal_id,
        "category": category,
        "status": status,
        "score": score,
        "evidence_ref": evidence_ref,
        "owner_hint": owner_hint,
        "primary_action": primary_action,
    }


def _connector(connector_id: str, name: str, status: str, last_seen_at: str, degrade_action: str, request_id: str) -> dict[str, str]:
    return {
        "id": connector_id,
        "name": name,
        "status": status,
        "last_seen_at": last_seen_at,
        "degrade_action": degrade_action,
        "request_id": request_id,
    }


def _sdlc_run(
    run_id: str,
    command: str,
    adapter_status: str,
    dry_run_status: str,
    proof_source: str,
    captured_at: str,
) -> dict[str, str]:
    return {
        "id": run_id,
        "command": command,
        "adapter_status": adapter_status,
        "dry_run_status": dry_run_status,
        "proof_source": proof_source,
        "captured_at": captured_at,
        "verified_loaded": "unverified",
    }
