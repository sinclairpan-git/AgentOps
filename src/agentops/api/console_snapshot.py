"""Console snapshot view model for the AgentOps frontend."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from agentops.core.agent_store import build_agent_store_echo_summary, build_run_audit, discover_agent_store_gaps
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
    {"id": "agent-store-audit", "label": "Agent Store 审计", "icon": "AS"},
    {"id": "connectors", "label": "连接器状态", "icon": "∞"},
    {"id": "sdlc-runs", "label": "Ai_AutoSDLC 运行", "icon": "SD"},
]


def build_console_snapshot(*, generated_at: str | None = None, repository: InMemoryRepository | None = None) -> dict[str, Any]:
    """Build a safe snapshot matching the Vue2 Console information architecture."""

    console_data = _console_data_from_repository(repository) if repository is not None else _console_data()
    console_data = _with_operation_center(console_data)
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
        run_id = _event_run_id(event)
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
        policy_state_known = _strict_bool(l5_input.get("policy_state_known"), default=False)
        outbox_status = str(l5_input.get("outbox_status", "delivered"))
        evaluation = evaluate_l5_gate(
            events,
            governance_state=governance_state,
            outbox_status=outbox_status,
            policy_state_known=policy_state_known,
        )
        l5_state = _l5_state(evaluation["result"])
        policy_state = _policy_state(policy_state_known=policy_state_known, has_l5_input=bool(l5_input))
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

    for gap in discover_agent_store_gaps(repository):
        risk_models.append(
            _risk(
                str(gap["gap_id"]),
                "Agent Store",
                str(gap["severity"]),
                "degraded",
                _localized_owner_hint(str(gap["owner_hint"])),
                _localized_action(str(gap["primary_action"])),
                "agent-store-audit",
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
        "agentStore": _agent_store_workbench(repository, events_by_run),
        "connectors": _repository_connectors(repository, event_count=len(raw_events)),
        "sdlcRuns": _repository_sdlc_runs(repository, event_count=len(raw_events)),
    }


def _with_operation_center(console_data: dict[str, Any]) -> dict[str, Any]:
    return {
        **console_data,
        "operationCenter": _operation_center(console_data),
    }


def _operation_center(console_data: dict[str, Any]) -> dict[str, Any]:
    notifications: list[dict[str, str]] = []
    todos: list[dict[str, str]] = []
    search_index: list[dict[str, str]] = []

    for approval in console_data.get("approvals", []):
        if approval.get("status") in {"pending", "escalated"}:
            notifications.append(
                _notification(
                    f"notif_{approval['approval_id']}",
                    "审批待处理",
                    f"{approval['requester']}：{approval['reason']}",
                    str(approval["status"]),
                    "approvals",
                    str(approval["audit_id"]),
                )
            )
            todos.append(
                _todo(
                    f"todo_{approval['approval_id']}",
                    "处理审批",
                    str(approval["reason"]),
                    "审批负责人",
                    str(approval["status"]),
                    "approvals",
                    str(approval["sla_due_at"]),
                )
            )

    for evidence in console_data.get("evidence", []):
        if evidence.get("raw_access_state") in {"redaction_failed", "permission_denied"}:
            notifications.append(
                _notification(
                    f"notif_{evidence['evidence_id']}",
                    "证据需要关注",
                    str(evidence["summary"]),
                    str(evidence["raw_access_state"]),
                    "evidence",
                    str(evidence["audit_id"]),
                )
            )
            todos.append(
                _todo(
                    f"todo_{evidence['evidence_id']}",
                    "处理证据访问",
                    str(evidence["summary"]),
                    "证据负责人",
                    str(evidence["raw_access_state"]),
                    "evidence",
                    "需复核",
                )
            )

    for risk in console_data.get("risks", []):
        is_agent_store_gap = str(risk["source"]) == "Agent Store" and str(risk["id"]).startswith("gap_")
        notifications.append(
            _notification(
                f"notif_{risk['id']}",
                f"{risk['source']} 风险",
                _localized_action(str(risk["primary_action"])),
                str(risk["state"]),
                str(risk["deep_link"]),
                str(risk["id"]),
            )
        )
        if is_agent_store_gap:
            continue
        todos.append(
            _todo(
                f"todo_{risk['id']}",
                _localized_action(str(risk["primary_action"])),
                f"{risk['source']} / {risk['severity']}",
                str(risk["owner_hint"]),
                str(risk["state"]),
                str(risk["deep_link"]),
                "持续跟进",
            )
        )

    for gap in console_data.get("agentStore", {}).get("discoveryGaps", []):
        todos.append(
            _todo(
                f"todo_{gap['gap_id']}",
                "补齐 Agent Store 注册事实",
                f"{gap['agent_id']} / {gap['version']}",
                str(gap["owner_hint"]),
                str(gap["state"]),
                "agent-store-audit",
                "待排期",
            )
        )

    for run in console_data.get("runs", []):
        search_index.append(_search_item(str(run["run_id"]), "运行记录", f"{run['agent']} / {run['skill']}", "runs", str(run["l5_state"])))
    for evidence in console_data.get("evidence", []):
        search_index.append(_search_item(str(evidence["evidence_id"]), "证据检索", str(evidence["summary"]), "evidence", str(evidence["raw_access_state"])))
    for approval in console_data.get("approvals", []):
        search_index.append(_search_item(str(approval["approval_id"]), "审批中心", str(approval["reason"]), "approvals", str(approval["status"])))
    for risk in console_data.get("risks", []):
        if str(risk["source"]) == "Agent Store" and str(risk["id"]).startswith("gap_"):
            continue
        search_index.append(_search_item(str(risk["id"]), str(risk["source"]), _localized_action(str(risk["primary_action"])), str(risk["deep_link"]), str(risk["state"])))
    for gap in console_data.get("agentStore", {}).get("discoveryGaps", []):
        search_index.append(_search_item(str(gap["gap_id"]), "Agent Store 审计", _localized_action(str(gap["primary_action"])), "agent-store-audit", str(gap["state"])))

    return {
        "notifications": notifications[:8],
        "todos": todos[:12],
        "searchIndex": search_index[:30],
    }


def _notification(notification_id: str, title: str, body: str, status: str, route: str, ref: str) -> dict[str, str]:
    return {
        "id": notification_id,
        "title": title,
        "body": body,
        "status": status,
        "route": route,
        "ref": ref,
    }


def _todo(todo_id: str, title: str, body: str, owner: str, status: str, route: str, due: str) -> dict[str, str]:
    return {
        "id": todo_id,
        "title": title,
        "body": body,
        "owner": owner,
        "status": status,
        "route": route,
        "due": due,
    }


def _search_item(item_id: str, kind: str, title: str, route: str, status: str) -> dict[str, str]:
    return {
        "id": item_id,
        "kind": kind,
        "title": title,
        "route": route,
        "status": status,
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


def _event_run_id(event: dict[str, Any]) -> str:
    payload = _event_payload(event)
    for candidate in (event.get("run_id"), payload.get("run_id")):
        if candidate not in (None, ""):
            return str(candidate)
    for fallback_key in ("event_id", "idempotency_key", "trace_id", "span_id"):
        fallback_value = event.get(fallback_key)
        if fallback_value not in (None, ""):
            return f"event_{fallback_value}"
    return f"event_sequence_{_event_sequence_no(event)}"


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


def _policy_state(*, policy_state_known: bool, has_l5_input: bool) -> str:
    if policy_state_known:
        return "allow"
    return "block" if has_l5_input else "unknown"


def _run_skill(events: list[dict[str, Any]]) -> str:
    for event in events:
        payload = event.get("payload", {})
        if event.get("event_type") == "stage_started" and isinstance(payload, dict):
            return str(payload.get("stage_name") or "治理运行")
    return "治理运行"


def _evidence_summary(evaluation: dict[str, Any], events: list[dict[str, Any]]) -> str:
    if evaluation["result"] == "L5":
        return f"已接收 {len(events)} 条签名事件，核心证据链完整。"
    missing = "、".join(_localized_evidence_gap(item) for item in evaluation["missing_evidence"] or evaluation["failed_conditions"])
    return f"已接收 {len(events)} 条事件，但仍缺少：{missing}。"


def _localized_evidence_gap(gap: str) -> str:
    labels = {
        "stage_started": "阶段开始事件",
        "stage_completed": "阶段完成事件",
        "gate_result": "门禁结果事件",
        "verification_result": "验证结果事件",
        "violation_scan_completed": "违规扫描事件",
        "artifact_generated": "产物生成事件",
        "generation_snapshot": "生成快照事件",
        "l5_eligibility_input": "L5 判定输入",
        "source_signed": "来源签名",
        "enterprise_managed": "企业托管来源",
        "governance_loaded": "治理加载证明",
        "identity_confidence": "身份可信证明",
        "stage_events_complete": "阶段事件完整性",
        "verification_fresh": "最新验证结果",
        "outbox_delivered": "事件投递结果",
        "policy_state_known": "策略状态证明",
    }
    return labels.get(gap, "可验证证据")


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
    metadata_count = len(repository.agent_store_metadata_records())
    agent_store_status = "healthy" if metadata_count else "degraded"
    agent_store_action = f"{metadata_count} 条元数据快照" if metadata_count else "等待 Agent Store 元数据同步"
    return [
        _connector("conn_agent_store", "Agent Store", agent_store_status, now, agent_store_action, "req_conn_agent_store"),
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


def _agent_store_workbench(repository: InMemoryRepository, events_by_run: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    raw_gaps = discover_agent_store_gaps(repository)
    gaps = [_agent_store_gap(gap) for gap in raw_gaps]
    agent_store_events_by_run: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for events in events_by_run.values():
        for event in events:
            agent_store_events_by_run[_agent_store_run_id(event)].append(event)

    audits = []
    summaries = []
    for run_id in sorted(agent_store_events_by_run):
        events = sorted(agent_store_events_by_run[run_id], key=_event_sequence_no)
        try:
            audit = build_run_audit(repository, run_id, events=events, discovery_gaps=raw_gaps)
        except Exception:
            audit = _agent_store_failed_audit(run_id, events)
            audits.append(_agent_store_audit(audit))
            summaries.append(_agent_store_summary(_agent_store_failed_summary(run_id, audit)))
            continue
        audits.append(_agent_store_audit(audit))
        try:
            summary = build_agent_store_echo_summary(
                repository,
                str(audit["agent_id"]),
                str(audit["version"]),
                _agent_store_evidence_summary(run_id, events),
                run_audit=audit,
                discovery_gaps=raw_gaps,
            )
        except Exception:
            summary = _agent_store_failed_summary(run_id, audit)
        summaries.append(_agent_store_summary(summary))

    return {
        "discoveryGaps": gaps,
        "runAudits": audits,
        "storeSummaries": summaries,
        "registryMap": [_agent_store_registry_record(record) for record in repository.agent_store_metadata_records()],
    }


def _agent_store_run_id(event: dict[str, Any]) -> str:
    payload = _event_payload(event)
    for candidate in (event.get("run_id"), payload.get("run_id")):
        if candidate not in (None, ""):
            return str(candidate)
    return str(event.get("event_id") or "unknown_run")


def _agent_store_evidence_summary(run_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    l5_input = _last_payload(events, "l5_eligibility_input")
    evaluation = evaluate_l5_gate(
        events,
        governance_state=_governance_state(events),
        outbox_status=str(l5_input.get("outbox_status", "delivered")),
        policy_state_known=_strict_bool(l5_input.get("policy_state_known"), default=False),
    )
    return {
        "run_id": run_id,
        "evidence_level": str(evaluation["evidence_level"]),
        "confidence": _agent_store_confidence(str(evaluation["evidence_level"])),
        "missing_evidence": list(evaluation["missing_evidence"]),
    }


def _agent_store_failed_audit(run_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    first = events[0] if events else {}
    agent_id = str(first.get("agent_id") or "unknown_agent")
    version = str(first.get("agent_version") or first.get("version") or "unknown")
    return {
        "audit_id": f"audit_run_{_slug(run_id)}",
        "run_id": run_id,
        "agent_id": agent_id,
        "version": version,
        "registration_state": "degraded",
        "event_count": len(events),
        "raw_access_state": "summary_only",
        "discovery_gap_ids": [],
        "related_agent_versions": [_agent_version_label(event) for event in events] or [f"{agent_id}@{version}"],
        "deep_links": {
            "agent_id": agent_id,
            "version": version,
            "session_id": str(first.get("session_id") or f"sess_{run_id}"),
            "run_id": run_id,
            "installation_id": str(first.get("installation_id") or "unknown_installation"),
            "trace_id": str(first.get("trace_id") or f"trace_{run_id}"),
            "audit_id": f"audit_run_{_slug(run_id)}",
            "return_url": f"/agent-store/agents/{agent_id}/runs/{run_id}",
        },
        "processing_error": "Agent Store 审计生成失败",
    }


def _agent_store_failed_summary(run_id: str, audit: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(UTC)
    return {
        "agent_id": str(audit["agent_id"]),
        "agent_version": str(audit["version"]),
        "metadata_state": "unknown",
        "registry_fact_owner": "Agent Store",
        "risk_state": "warning",
        "evidence_level": "pending",
        "confidence": 0.5,
        "missing_evidence": ["agent_store_audit"],
        "policy_requirement": {
            "required_by": "AgentOps",
            "source": "runtime_policy",
            "issuer": "AgentOps Policy Service",
            "policy_owner": "安全/IAM",
            "policy_version": "runtime-v2",
            "can_ignore": False,
            "affected_actions": ["运行审计", "高风险 Skill 调用"],
        },
        "discovery_gap_ids": [],
        "run_audit": {
            "audit_id": str(audit["audit_id"]),
            "registration_state": "degraded",
            "event_count": int(audit["event_count"]),
        },
        "calculated_at": now.isoformat(),
        "valid_until": now.isoformat(),
        "deep_links": dict(audit["deep_links"]),
        "processing_error": f"运行 {run_id} 的 Agent Store 回显摘要生成失败",
    }


def _agent_version_label(event: dict[str, Any]) -> str:
    agent_id = str(event.get("agent_id") or "unknown_agent")
    version = str(event.get("agent_version") or event.get("version") or "unknown")
    return f"{agent_id}@{version}"


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_") or "unknown"


def _agent_store_confidence(evidence_level: str) -> float:
    return {
        "L5": 1.0,
        "L4": 0.8,
        "L3": 0.6,
        "pending": 0.5,
    }.get(evidence_level, 0.4)


def _agent_store_gap(gap: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(gap["gap_id"]),
        "gap_id": str(gap["gap_id"]),
        "gap_type": str(gap["gap_type"]),
        "agent_id": str(gap["agent_id"]),
        "version": str(gap["version"]),
        "skill_id": str(gap["skill_id"]),
        "state": str(gap["state"]),
        "severity": str(gap["severity"]),
        "affected_runs": [str(run_id) for run_id in gap["affected_runs"]],
        "owner_hint": _localized_owner_hint(str(gap["owner_hint"])),
        "primary_action": _localized_action(str(gap["primary_action"])),
        "audit_id": str(gap["audit_id"]),
    }


def _agent_store_audit(audit: dict[str, Any]) -> dict[str, Any]:
    model = {
        "id": str(audit["audit_id"]),
        "audit_id": str(audit["audit_id"]),
        "run_id": str(audit["run_id"]),
        "agent_id": str(audit["agent_id"]),
        "version": str(audit["version"]),
        "registration_state": str(audit["registration_state"]),
        "event_count": int(audit["event_count"]),
        "raw_access_state": str(audit["raw_access_state"]),
        "discovery_gap_ids": [str(gap_id) for gap_id in audit["discovery_gap_ids"]],
        "related_agent_versions": [str(version) for version in audit["related_agent_versions"]],
        "deep_links": {str(key): str(value) for key, value in audit["deep_links"].items()},
    }
    if audit.get("processing_error"):
        model["processing_error"] = str(audit["processing_error"])
    return model


def _agent_store_summary(summary: dict[str, Any]) -> dict[str, Any]:
    model = {
        "id": f"{summary['agent_id']}@{summary['agent_version']}:{summary['run_audit']['audit_id']}",
        "agent_id": str(summary["agent_id"]),
        "agent_version": str(summary["agent_version"]),
        "metadata_state": str(summary["metadata_state"]),
        "registry_fact_owner": str(summary["registry_fact_owner"]),
        "risk_state": str(summary["risk_state"]),
        "evidence_level": str(summary["evidence_level"]),
        "confidence": float(summary["confidence"]),
        "missing_evidence": [str(item) for item in summary["missing_evidence"]],
        "policy_requirement": {
            "required_by": str(summary["policy_requirement"]["required_by"]),
            "source": str(summary["policy_requirement"]["source"]),
            "issuer": str(summary["policy_requirement"]["issuer"]),
            "policy_owner": str(summary["policy_requirement"]["policy_owner"]),
            "policy_version": str(summary["policy_requirement"]["policy_version"]),
            "can_ignore": bool(summary["policy_requirement"]["can_ignore"]),
            "affected_actions": [str(action) for action in summary["policy_requirement"]["affected_actions"]],
        },
        "discovery_gap_ids": [str(gap_id) for gap_id in summary["discovery_gap_ids"]],
        "run_audit": {
            "audit_id": str(summary["run_audit"]["audit_id"]),
            "registration_state": str(summary["run_audit"]["registration_state"]),
            "event_count": int(summary["run_audit"]["event_count"]),
        },
        "calculated_at": str(summary["calculated_at"]),
        "valid_until": str(summary["valid_until"]),
    }
    if summary.get("processing_error"):
        model["processing_error"] = str(summary["processing_error"])
    return model


def _agent_store_registry_record(record: dict[str, Any]) -> dict[str, Any]:
    skills = record.get("skills") or []
    skill_count = len(skills) if isinstance(skills, list | tuple) else 0
    return {
        "id": f"{record['agent_id']}@{record['version']}",
        "agent_id": str(record["agent_id"]),
        "version": str(record["version"]),
        "metadata_state": "consumed",
        "fact_owner": "Agent Store",
        "skill_count": skill_count,
        "synced_at": str(record.get("synced_at") or "待同步"),
    }


def _localized_owner_hint(owner_hint: str) -> str:
    return "Agent 负责人" if owner_hint == "Agent Owner" else owner_hint


def _localized_action(action: str) -> str:
    return (
        action.replace("通知 Owner 补齐", "通知负责人补齐")
        .replace("通知 Owner", "通知负责人")
        .replace("Owner", "负责人")
    )


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
        "agentStore": {
            "discoveryGaps": [
                {
                    "id": "gap_agent_agent_store_0_1_0",
                    "gap_id": "gap_agent_agent_store_0_1_0",
                    "gap_type": "agent_unregistered",
                    "agent_id": "agent.store",
                    "version": "0.1.0",
                    "skill_id": "",
                    "state": "suspected",
                    "severity": "高",
                    "affected_runs": ["run_20260506_004"],
                    "owner_hint": "Agent 负责人",
                    "primary_action": "通知负责人补齐 Agent Store 注册事实",
                    "audit_id": "audit_gap_agent_agent_store_0_1_0",
                }
            ],
            "runAudits": [
                {
                    "id": "audit_run_run_20260506_004",
                    "audit_id": "audit_run_run_20260506_004",
                    "run_id": "run_20260506_004",
                    "agent_id": "agent.store",
                    "version": "0.1.0",
                    "registration_state": "suspected",
                    "event_count": 3,
                    "raw_access_state": "summary_only",
                    "discovery_gap_ids": ["gap_agent_agent_store_0_1_0"],
                    "related_agent_versions": ["agent.store@0.1.0"],
                    "deep_links": {
                        "agent_id": "agent.store",
                        "version": "0.1.0",
                        "session_id": "sess_store_004",
                        "run_id": "run_20260506_004",
                        "installation_id": "inst_store",
                        "trace_id": "trace_store_004",
                        "audit_id": "audit_run_run_20260506_004",
                        "return_url": "/agent-store/agents/agent.store/runs/run_20260506_004",
                    },
                }
            ],
            "storeSummaries": [
                {
                    "id": "agent.store@0.1.0:audit_run_run_20260506_004",
                    "agent_id": "agent.store",
                    "agent_version": "0.1.0",
                    "metadata_state": "unregistered",
                    "registry_fact_owner": "Agent Store",
                    "risk_state": "warning",
                    "evidence_level": "L3",
                    "confidence": 0.6,
                    "missing_evidence": ["l5_eligibility_input"],
                    "policy_requirement": {
                        "required_by": "AgentOps",
                        "source": "runtime_policy",
                        "issuer": "AgentOps Policy Service",
                        "policy_owner": "安全/IAM",
                        "policy_version": "runtime-v2",
                        "can_ignore": False,
                        "affected_actions": ["运行审计", "高风险 Skill 调用"],
                    },
                    "discovery_gap_ids": ["gap_agent_agent_store_0_1_0"],
                    "run_audit": {
                        "audit_id": "audit_run_run_20260506_004",
                        "registration_state": "suspected",
                        "event_count": 3,
                    },
                    "calculated_at": "2026-05-06T05:20:00Z",
                    "valid_until": "2026-06-05T05:20:00Z",
                }
            ],
            "registryMap": [
                {
                    "id": "agent.publisher@1.0.0",
                    "agent_id": "agent.publisher",
                    "version": "1.0.0",
                    "metadata_state": "consumed",
                    "fact_owner": "Agent Store",
                    "skill_count": 2,
                    "synced_at": "2026-05-06T05:18:00Z",
                }
            ],
        },
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
