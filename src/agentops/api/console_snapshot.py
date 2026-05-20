"""Console snapshot view model for the AgentOps frontend."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from agentops.api.credentials import (
    CREDENTIAL_STATUS_SCHEMA_VERSION,
    get_credential_status,
)
from agentops.core.agent_store import (
    build_agent_store_echo_summary,
    build_run_audit,
    discover_agent_store_gaps,
)
from agentops.core.errors import AgentOpsError
from agentops.core.l5_gate import evaluate_l5_gate
from agentops.core.operations import (
    build_complex_risk_profile,
    build_exporter_ecosystem_projection,
    build_mcp_a2a_governance_projection,
    build_multi_agent_handoff_evaluation,
    build_quality_center_workbench as build_repository_quality_center_workbench,
)
from agentops.storage.repository import InMemoryRepository

SCHEMA_VERSION = "agentops.console.snapshot.v1"
CONSOLE_CREDENTIAL_STATUS_SCHEMA_VERSION = "agentops_credential_status.v1"

ROUTES = [
    {"id": "overview", "label": "总览", "icon": "⌂"},
    {"id": "runs", "label": "运行记录", "icon": "▶"},
    {"id": "evidence", "label": "证据检索", "icon": "◇"},
    {"id": "approvals", "label": "审批中心", "icon": "✓"},
    {"id": "policies", "label": "策略中心", "icon": "!"},
    {"id": "quality", "label": "质量中心", "icon": "质"},
    {"id": "risks", "label": "风险处置", "icon": "△"},
    {"id": "agent-store-audit", "label": "Agent Store 审计", "icon": "AS"},
    {"id": "credential-handoff", "label": "凭证联调", "icon": "凭"},
    {"id": "connectors", "label": "连接器状态", "icon": "∞"},
    {"id": "sdlc-runs", "label": "Ai_AutoSDLC 运行", "icon": "SD"},
]


def build_console_snapshot(
    *, generated_at: str | None = None, repository: InMemoryRepository | None = None
) -> dict[str, Any]:
    """Build a safe snapshot matching the Vue2 Console information architecture."""

    console_data = (
        _console_data_from_repository(repository)
        if repository is not None
        else _console_data()
    )
    console_data = _with_workbenches(console_data, repository=repository)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at or datetime.now(UTC).isoformat(),
        "source": "api_snapshot",
        "source_detail": {
            "mode": "repository_backed" if repository is not None else "sample_fixture",
            "fact_source": "InMemoryRepository"
            if repository is not None
            else "console_snapshot_fixture",
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
    quality_center_agent_refs: list[dict[str, str]] = []
    seen_quality_center_refs: set[tuple[str, str]] = set()
    l5_count = 0
    pending_count = 0
    degraded_count = 0

    for run_id in sorted(events_by_run):
        events = sorted(events_by_run[run_id], key=_event_sequence_no)
        l5_input = _last_payload(events, "l5_eligibility_input")
        governance_state = _governance_state(events)
        policy_state_known = _strict_bool(
            l5_input.get("policy_state_known"), default=False
        )
        outbox_status = str(l5_input.get("outbox_status", "delivered"))
        evaluation = evaluate_l5_gate(
            events,
            governance_state=governance_state,
            outbox_status=outbox_status,
            policy_state_known=policy_state_known,
        )
        l5_state = _l5_state(evaluation["result"])
        policy_state = _policy_state(
            policy_state_known=policy_state_known, has_l5_input=bool(l5_input)
        )
        evidence_state = "summary_only" if evaluation["result"] == "L5" else "degraded"
        agent = str(events[0].get("agent_id") or "未知 Agent")
        version = str(events[0].get("agent_version") or "unknown")
        skill = _run_skill(events)
        risk_level = "低" if evaluation["result"] == "L5" else "高"

        if evaluation["result"] == "L5":
            l5_count += 1
        elif evaluation["result"] == "pending":
            pending_count += 1
        else:
            degraded_count += 1

        run_models.append(
            _run(
                run_id, agent, skill, risk_level, l5_state, policy_state, evidence_state
            )
        )
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
                "补齐缺失证据"
                if evaluation["missing_evidence"] or evaluation["failed_conditions"]
                else "保持基线",
            )
        )
        quality_center_key = (agent, version)
        if quality_center_key not in seen_quality_center_refs:
            seen_quality_center_refs.add(quality_center_key)
            quality_center_agent_refs.append(
                {
                    "agent_id": agent,
                    "version": version,
                    "owner_team": "质量负责人",
                }
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
    approvals = [
        _approval_from_record(approval) for approval in repository.approval_records()
    ]
    approval_pending_count = sum(
        1 for approval in approvals if approval["status"] in {"pending", "escalated"}
    )
    metrics = [
        {
            "label": "今日运行",
            "value": run_count,
            "status": "healthy" if run_count else "empty",
            "detail": f"{l5_count} 条 L5，{degraded_count} 条降级，{pending_count} 条待补偿",
        },
        {
            "label": "Policy SLO",
            "value": "本地内核",
            "status": "healthy",
            "detail": "当前由可执行内核生成策略摘要",
        },
        {
            "label": "审批待办",
            "value": approval_pending_count,
            "status": "pending" if approval_pending_count else "healthy",
            "detail": "来自 AgentOps 审批仓库事实",
        },
        {
            "label": "证据状态",
            "value": f"{len(evidence_models)} 条摘要",
            "status": "healthy" if evidence_models else "empty",
            "detail": "仅展示脱敏摘要和哈希，不暴露原文",
        },
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
        "_qualityCenterAgentRefs": quality_center_agent_refs,
        "agentStore": _agent_store_workbench(repository, events_by_run),
        "credentialHandoff": _credential_handoff_workbench(repository),
        "connectors": _repository_connectors(repository, event_count=len(raw_events)),
        "sdlcRuns": _repository_sdlc_runs(repository, event_count=len(raw_events)),
    }


def _with_workbenches(
    console_data: dict[str, Any], *, repository: InMemoryRepository | None = None
) -> dict[str, Any]:
    adoption = _adoption_workbench(console_data)
    public_console_data = {
        key: value for key, value in console_data.items() if not key.startswith("_")
    }
    enriched = {
        **public_console_data,
        "adoption": adoption,
        "qualityCenterWorkbench": _quality_center_workbench(
            console_data, adoption, repository=repository
        ),
        "evidenceVault": _evidence_vault_workbench(console_data),
        "approvalWorkbench": _approval_workbench(console_data),
        "connectorWorkbench": _connector_workbench(console_data, repository=repository),
        "sdlcRunWorkbench": _sdlc_run_workbench(console_data),
        "actionWorkbench": _action_workbench(console_data),
    }
    return {
        **enriched,
        "operationCenter": _operation_center(console_data),
    }


def _quality_center_workbench(
    console_data: dict[str, Any],
    adoption: dict[str, Any],
    *,
    repository: InMemoryRepository | None = None,
) -> dict[str, Any]:
    if repository is not None:
        agent_refs = _quality_center_agent_refs(console_data)
        if agent_refs:
            return _console_quality_center_workbench(
                build_repository_quality_center_workbench(
                    repository,
                    agent_refs=agent_refs,
                    report_period="console_snapshot",
                    generated_by="agentops_console_snapshot",
                )
            )

    quality_items = list(console_data.get("quality", []))
    agent_summaries = [
        _quality_center_agent_summary(item, index)
        for index, item in enumerate(quality_items)
    ]
    review_queue = _quality_center_review_queue(agent_summaries, adoption)
    comparison_states = [
        str(
            summary.get("scorer_comparison", {}).get(
                "comparison_state", "insufficient_evidence"
            )
        )
        for summary in agent_summaries
    ]
    trend_summary = _quality_center_trend_summary(adoption, review_queue)
    return {
        "schema_version": "quality_center_workbench.v1",
        "report_period": "console_snapshot",
        "workbench_state": "ready" if agent_summaries else "empty",
        "generated_by": "agentops_console_snapshot",
        "agent_summaries": agent_summaries,
        "scorer_rollout_panel": {
            "candidate_count": len(agent_summaries),
            "ready_for_manual_approval_count": comparison_states.count(
                "ready_for_manual_approval"
            ),
            "needs_human_review_count": comparison_states.count("needs_human_review"),
            "insufficient_evidence_count": comparison_states.count(
                "insufficient_evidence"
            ),
            "automatic_rollout_enabled": False,
            "automatic_template_switch": False,
            "manual_approval_queue_size": sum(
                1
                for item in review_queue
                if item.get("review_type") == "scorer_rollout"
            ),
        },
        "external_intake_panel": _quality_center_external_intake_panel(
            agent_summaries, review_queue
        ),
        "external_intake_portfolio": _quality_center_external_intake_portfolio(
            agent_summaries, review_queue
        ),
        "review_queue": review_queue,
        "trend_summary": trend_summary,
        "summary": {
            "payload_access": "forbidden",
            "prompt_access": "forbidden",
            "change_access": "forbidden",
            "terminal_access": "forbidden",
            "automatic_rollout_enabled": False,
            "automatic_lifecycle_action": False,
            "store_write_performed": False,
            "automatic_publish_performed": False,
            "notification_sent": False,
            "external_intake_receipt_count": sum(
                _safe_int(item.get("external_intake_health", {}).get("receipt_count"))
                for item in agent_summaries
            ),
        },
        "audit_id": "audit_quality_center_console_snapshot",
    }


def _quality_center_agent_refs(console_data: dict[str, Any]) -> list[dict[str, Any]]:
    explicit_refs = console_data.get("_qualityCenterAgentRefs")
    if isinstance(explicit_refs, list):
        return [dict(ref) for ref in explicit_refs if isinstance(ref, dict)]

    refs: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for run in console_data.get("runs", []):
        agent_id = str(run.get("agent_id") or run.get("agent") or "")
        version = str(run.get("version") or run.get("agent_version") or "")
        if not agent_id or not version:
            continue
        key = (agent_id, version)
        if key in seen:
            continue
        seen.add(key)
        refs.append(
            {
                "agent_id": agent_id,
                "version": version,
                "owner_team": str(run.get("owner_team") or "质量负责人"),
            }
        )
    return refs


def _console_quality_center_workbench(workbench: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": str(workbench.get("schema_version") or ""),
        "report_period": str(workbench.get("report_period") or "console_snapshot"),
        "workbench_state": str(workbench.get("workbench_state") or "empty"),
        "generated_by": str(
            workbench.get("generated_by") or "agentops_console_snapshot"
        ),
        "agent_summaries": [
            _console_quality_center_agent_summary(summary)
            for summary in workbench.get("agent_summaries", [])
            if isinstance(summary, dict)
        ],
        "scorer_rollout_panel": _console_quality_center_rollout_panel(
            workbench.get("scorer_rollout_panel", {})
        ),
        "external_intake_panel": _console_quality_center_external_intake_panel(
            workbench.get("external_intake_panel", {})
        ),
        "external_intake_portfolio": _console_quality_center_external_intake_portfolio(
            workbench.get("external_intake_portfolio", {})
        ),
        "review_queue": [
            _console_quality_center_review_item(item)
            for item in workbench.get("review_queue", [])
            if isinstance(item, dict)
        ],
        "trend_summary": _console_quality_center_trend_summary(
            workbench.get("trend_summary", {})
        ),
        "summary": _console_quality_center_summary(workbench.get("summary", {})),
        "audit_id": str(workbench.get("audit_id") or "audit_quality_center_snapshot"),
    }


def _console_quality_center_agent_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "agent_id": _display_safe_text(str(summary.get("agent_id") or "")),
        "version": _display_safe_text(str(summary.get("version") or "")),
        "owner_team": _display_safe_text(str(summary.get("owner_team") or "")),
        "score": _safe_float(summary.get("score")),
        "quality_state": str(summary.get("quality_state") or "insufficient_evidence"),
        "confidence": _safe_float(summary.get("confidence")),
        "score_template_id": _display_safe_text(
            str(summary.get("score_template_id") or "")
        ),
        "evidence_level": _display_safe_text(str(summary.get("evidence_level") or "")),
        "missing_evidence": [
            _display_safe_text(str(item))
            for item in summary.get("missing_evidence", [])
        ],
        "explanation": _display_safe_text(str(summary.get("explanation") or "")),
        "lifecycle_state": str(summary.get("lifecycle_state") or "review_required"),
        "lifecycle_action": _display_safe_text(
            str(summary.get("lifecycle_action") or "open_ops_review")
        ),
        "scorer": _console_quality_center_scorer(summary.get("scorer", {})),
        "scorer_comparison": _console_quality_center_scorer_comparison(
            summary.get("scorer_comparison", {})
        ),
        "external_intake_health": _console_quality_center_external_intake_health(
            summary.get("external_intake_health", {})
        ),
    }


def _console_quality_center_scorer(scorer: Any) -> dict[str, Any]:
    scorer = scorer if isinstance(scorer, dict) else {}
    return {
        "scorer_id": _display_safe_text(str(scorer.get("scorer_id") or "")),
        "scorer_version": _display_safe_text(str(scorer.get("scorer_version") or "")),
        "rollout_state": str(scorer.get("rollout_state") or "candidate"),
    }


def _console_quality_center_scorer_comparison(comparison: Any) -> dict[str, Any]:
    comparison = comparison if isinstance(comparison, dict) else {}
    return {
        "comparison_state": str(
            comparison.get("comparison_state") or "insufficient_evidence"
        ),
        "safety_impact": str(comparison.get("safety_impact") or "neutral"),
        "alignment_delta": _safe_float(comparison.get("alignment_delta")),
        "recommendation": _display_safe_text(
            str(comparison.get("recommendation") or "collect_more_samples")
        ),
        "manual_approval_required": True,
    }


def _console_quality_center_review_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _display_safe_text(str(item.get("id") or "")),
        "agent_id": _display_safe_text(str(item.get("agent_id") or "")),
        "version": _display_safe_text(str(item.get("version") or "")),
        "review_type": _display_safe_text(str(item.get("review_type") or "")),
        "reason": _display_safe_text(str(item.get("reason") or "")),
        "recommended_action": _display_safe_text(
            str(item.get("recommended_action") or "")
        ),
        "owner_team": _display_safe_text(str(item.get("owner_team") or "")),
        "manual_review_required": True,
        "automatic_action_performed": False,
    }


def _console_quality_center_rollout_panel(panel: Any) -> dict[str, Any]:
    panel = panel if isinstance(panel, dict) else {}
    return {
        "candidate_count": _safe_int(panel.get("candidate_count")),
        "ready_for_manual_approval_count": _safe_int(
            panel.get("ready_for_manual_approval_count")
        ),
        "needs_human_review_count": _safe_int(panel.get("needs_human_review_count")),
        "insufficient_evidence_count": _safe_int(
            panel.get("insufficient_evidence_count")
        ),
        "automatic_rollout_enabled": False,
        "automatic_template_switch": False,
        "manual_approval_queue_size": _safe_int(
            panel.get("manual_approval_queue_size")
        ),
    }


def _console_quality_center_trend_summary(trend: Any) -> dict[str, Any]:
    trend = trend if isinstance(trend, dict) else {}
    return {
        "report_state": str(trend.get("report_state") or "insufficient_data"),
        "retention_rate": str(trend.get("retention_rate") or "0%"),
        "review_queue_size": _safe_int(trend.get("review_queue_size")),
        "rework_rounds": _safe_int(trend.get("rework_rounds")),
        "pr_review_findings": _safe_int(trend.get("pr_review_findings")),
        "recommendation": _display_safe_text(
            str(
                trend.get("recommendation")
                or "人工复核缺证据、低置信和评分器发布项；不执行自动生命周期动作。"
            )
        ),
    }


def _console_quality_center_summary(summary: Any) -> dict[str, Any]:
    summary = summary if isinstance(summary, dict) else {}
    return {
        "payload_access": str(
            summary.get("payload_access")
            or summary.get("raw_payload_access")
            or "forbidden"
        ),
        "prompt_access": str(
            summary.get("prompt_access")
            or summary.get("raw_prompt_access")
            or "forbidden"
        ),
        "change_access": str(
            summary.get("change_access")
            or summary.get("raw_diff_access")
            or "forbidden"
        ),
        "terminal_access": str(
            summary.get("terminal_access")
            or summary.get("terminal_output_access")
            or "forbidden"
        ),
        "automatic_rollout_enabled": False,
        "automatic_lifecycle_action": False,
        "store_write_performed": False,
        "automatic_publish_performed": False,
        "notification_sent": False,
        "external_intake_receipt_count": _safe_int(
            summary.get("external_intake_receipt_count")
        ),
    }


def _console_quality_center_external_intake_health(health: Any) -> dict[str, Any]:
    health = health if isinstance(health, dict) else {}
    summary = health.get("summary") if isinstance(health.get("summary"), dict) else {}
    return {
        "schema_version": "quality_center_external_intake_health.v1",
        "health_state": str(health.get("health_state") or "no_receipts"),
        "receipt_count": _safe_int(health.get("receipt_count")),
        "window_limit": _safe_int(health.get("window_limit") or 25),
        "latest_intake_id": _display_safe_text(
            str(health.get("latest_intake_id") or "")
        ),
        "latest_received_at": _display_safe_text(
            str(health.get("latest_received_at") or "")
        ),
        "latest_pass_rate": _safe_float(health.get("latest_pass_rate")),
        "latest_sample_size": _safe_int(health.get("latest_sample_size")),
        "intake_state_counts": _safe_count_map(health.get("intake_state_counts")),
        "source_trust_counts": _safe_count_map(health.get("source_trust_counts")),
        "accepted_execution_count": _safe_int(health.get("accepted_execution_count")),
        "scorer_refs": _safe_scorer_refs(health.get("scorer_refs")),
        "manual_review_required": bool(health.get("manual_review_required")),
        "recommendation": _display_safe_text(
            str(health.get("recommendation") or "optional")
        ),
        "summary": {
            "summary_only_intake_health": True,
            "latest_summary_keys": [
                _display_safe_text(str(key))
                for key in summary.get("latest_summary_keys", [])
            ],
            "automatic_rollout_enabled": False,
            "automatic_template_switch": False,
            "scorer_execution_performed": False,
            "store_write_performed": False,
            "notification_sent": False,
        },
    }


def _console_quality_center_external_intake_panel(panel: Any) -> dict[str, Any]:
    panel = panel if isinstance(panel, dict) else {}
    return {
        "monitored_agent_count": _safe_int(panel.get("monitored_agent_count")),
        "receiving_count": _safe_int(panel.get("receiving_count")),
        "no_receipts_count": _safe_int(panel.get("no_receipts_count")),
        "needs_review_count": _safe_int(panel.get("needs_review_count")),
        "receipt_count": _safe_int(panel.get("receipt_count")),
        "accepted_execution_count": _safe_int(panel.get("accepted_execution_count")),
        "manual_review_queue_size": _safe_int(panel.get("manual_review_queue_size")),
        "automatic_rollout_enabled": False,
        "automatic_scorer_invocation": False,
        "store_write_performed": False,
    }


def _console_quality_center_external_intake_portfolio(portfolio: Any) -> dict[str, Any]:
    portfolio = portfolio if isinstance(portfolio, dict) else {}
    coverage = (
        portfolio.get("scorer_coverage")
        if isinstance(portfolio.get("scorer_coverage"), dict)
        else {}
    )
    return {
        "schema_version": "quality_center_external_intake_portfolio.v1",
        "portfolio_state": str(portfolio.get("portfolio_state") or "empty"),
        "scope_count": _safe_int(portfolio.get("scope_count")),
        "version_scope_count": _safe_int(portfolio.get("version_scope_count")),
        "state_counts": _safe_count_map(portfolio.get("state_counts")),
        "receipt_count": _safe_int(portfolio.get("receipt_count")),
        "accepted_execution_count": _safe_int(
            portfolio.get("accepted_execution_count")
        ),
        "manual_review_queue_size": _safe_int(
            portfolio.get("manual_review_queue_size")
        ),
        "required_missing_scope_count": _safe_int(
            portfolio.get("required_missing_scope_count")
        ),
        "required_missing_scopes": [
            _console_quality_center_external_intake_scope(scope)
            for scope in portfolio.get("required_missing_scopes", [])
            if isinstance(scope, dict)
        ],
        "latest_receipts": [
            _console_quality_center_external_intake_receipt(receipt)
            for receipt in portfolio.get("latest_receipts", [])
            if isinstance(receipt, dict)
        ],
        "scorer_coverage": {
            "unique_scorer_count": _safe_int(coverage.get("unique_scorer_count")),
            "scopes_with_scorer_receipts": _safe_int(
                coverage.get("scopes_with_scorer_receipts")
            ),
            "scorer_refs": _safe_scorer_refs(coverage.get("scorer_refs")),
        },
        "summary": {
            "summary_only_intake_portfolio": True,
            "automatic_rollout_enabled": False,
            "automatic_template_switch": False,
            "automatic_scorer_invocation": False,
            "scorer_execution_performed": False,
            "store_write_performed": False,
            "notification_sent": False,
        },
    }


def _console_quality_center_external_intake_scope(
    scope: dict[str, Any],
) -> dict[str, Any]:
    return {
        "agent_id": _display_safe_text(str(scope.get("agent_id") or "")),
        "version": _display_safe_text(str(scope.get("version") or "")),
        "owner_team": _display_safe_text(str(scope.get("owner_team") or "")),
        "health_state": str(scope.get("health_state") or "no_receipts"),
        "recommendation": _display_safe_text(
            str(scope.get("recommendation") or "connect_external_scorer")
        ),
    }


def _console_quality_center_external_intake_receipt(
    receipt: dict[str, Any],
) -> dict[str, Any]:
    return {
        "agent_id": _display_safe_text(str(receipt.get("agent_id") or "")),
        "version": _display_safe_text(str(receipt.get("version") or "")),
        "health_state": str(receipt.get("health_state") or "no_receipts"),
        "latest_intake_id": _display_safe_text(
            str(receipt.get("latest_intake_id") or "")
        ),
        "latest_received_at": _display_safe_text(
            str(receipt.get("latest_received_at") or "")
        ),
        "latest_pass_rate": _safe_float(receipt.get("latest_pass_rate")),
        "latest_sample_size": _safe_int(receipt.get("latest_sample_size")),
    }


def _quality_center_external_intake_panel(
    agent_summaries: list[dict[str, Any]], review_queue: list[dict[str, Any]]
) -> dict[str, Any]:
    health_items = [
        item.get("external_intake_health", {})
        for item in agent_summaries
        if isinstance(item.get("external_intake_health"), dict)
    ]
    states = [str(item.get("health_state") or "") for item in health_items]
    return _console_quality_center_external_intake_panel(
        {
            "monitored_agent_count": len(health_items),
            "receiving_count": states.count("receiving"),
            "no_receipts_count": states.count("no_receipts"),
            "needs_review_count": states.count("needs_review"),
            "receipt_count": sum(
                _safe_int(item.get("receipt_count")) for item in health_items
            ),
            "accepted_execution_count": sum(
                _safe_int(item.get("accepted_execution_count")) for item in health_items
            ),
            "manual_review_queue_size": sum(
                1
                for item in review_queue
                if item.get("review_type") == "external_intake"
            ),
        }
    )


def _quality_center_external_intake_portfolio(
    agent_summaries: list[dict[str, Any]], review_queue: list[dict[str, Any]]
) -> dict[str, Any]:
    state_counts = {"receiving": 0, "no_receipts": 0, "needs_review": 0}
    latest_receipts: list[dict[str, Any]] = []
    required_missing_scopes: list[dict[str, Any]] = []
    scorer_refs: list[dict[str, str]] = []
    scopes_with_scorer_receipts = 0
    for summary in agent_summaries:
        health = (
            summary.get("external_intake_health")
            if isinstance(summary.get("external_intake_health"), dict)
            else {}
        )
        health_state = str(health.get("health_state") or "no_receipts")
        if health_state in state_counts:
            state_counts[health_state] += 1
        if _safe_int(health.get("receipt_count")) > 0:
            latest_receipts.append(
                {
                    "agent_id": summary.get("agent_id"),
                    "version": summary.get("version"),
                    "health_state": health_state,
                    "latest_intake_id": health.get("latest_intake_id"),
                    "latest_received_at": health.get("latest_received_at"),
                    "latest_pass_rate": health.get("latest_pass_rate"),
                    "latest_sample_size": health.get("latest_sample_size"),
                }
            )
        if health.get("manual_review_required") and health_state == "no_receipts":
            required_missing_scopes.append(
                {
                    "agent_id": summary.get("agent_id"),
                    "version": summary.get("version"),
                    "owner_team": summary.get("owner_team"),
                    "health_state": health_state,
                    "recommendation": health.get("recommendation"),
                }
            )
        refs = [ref for ref in health.get("scorer_refs", []) if isinstance(ref, dict)]
        if refs:
            scopes_with_scorer_receipts += 1
            scorer_refs.extend(_safe_scorer_refs(refs))
    if not agent_summaries:
        portfolio_state = "empty"
    elif state_counts["needs_review"]:
        portfolio_state = "needs_review"
    elif required_missing_scopes:
        portfolio_state = "incomplete"
    elif state_counts["receiving"]:
        portfolio_state = "receiving"
    else:
        portfolio_state = "no_receipts"
    return _console_quality_center_external_intake_portfolio(
        {
            "portfolio_state": portfolio_state,
            "scope_count": len(agent_summaries),
            "version_scope_count": len(
                {
                    (str(summary.get("agent_id")), str(summary.get("version")))
                    for summary in agent_summaries
                }
            ),
            "state_counts": state_counts,
            "receipt_count": sum(
                _safe_int(
                    summary.get("external_intake_health", {}).get("receipt_count")
                )
                for summary in agent_summaries
            ),
            "accepted_execution_count": sum(
                _safe_int(
                    summary.get("external_intake_health", {}).get(
                        "accepted_execution_count"
                    )
                )
                for summary in agent_summaries
            ),
            "manual_review_queue_size": sum(
                1
                for item in review_queue
                if item.get("review_type") == "external_intake"
            ),
            "required_missing_scope_count": len(required_missing_scopes),
            "required_missing_scopes": required_missing_scopes,
            "latest_receipts": latest_receipts,
            "scorer_coverage": {
                "unique_scorer_count": len(_safe_scorer_refs(scorer_refs)),
                "scopes_with_scorer_receipts": scopes_with_scorer_receipts,
                "scorer_refs": _safe_scorer_refs(scorer_refs),
            },
        }
    )


def _quality_center_agent_summary(item: dict[str, Any], index: int) -> dict[str, Any]:
    signal_id = str(item.get("signal_id") or item.get("id") or f"quality_{index}")
    status = str(item.get("status") or "unknown")
    quality_state = _quality_center_quality_state(status)
    comparison_state = _quality_center_comparison_state(status)
    return {
        "agent_id": _display_safe_text(str(item.get("category") or signal_id)),
        "version": "console_snapshot",
        "owner_team": _display_safe_text(str(item.get("owner_hint") or "质量负责人")),
        "score": _quality_center_score(item.get("score")),
        "quality_state": quality_state,
        "confidence": _quality_center_confidence(status),
        "score_template_id": "quality_summary_console_snapshot",
        "evidence_level": _display_safe_text(str(item.get("score") or "summary_only")),
        "missing_evidence": _quality_center_missing_evidence(item),
        "explanation": _display_safe_text(
            str(
                item.get("primary_action")
                or "仅展示 Console 摘要，必要时进入人工复核。"
            )
        ),
        "lifecycle_state": _quality_center_lifecycle_state(quality_state),
        "lifecycle_action": _quality_center_lifecycle_action(quality_state),
        "scorer": {
            "scorer_id": "quality_summary_console_snapshot",
            "scorer_version": "summary",
            "rollout_state": "candidate",
        },
        "scorer_comparison": {
            "comparison_state": comparison_state,
            "safety_impact": "neutral"
            if comparison_state == "ready_for_manual_approval"
            else "needs_review",
            "alignment_delta": 0.0,
            "recommendation": "submit_for_manual_rollout_approval"
            if comparison_state == "ready_for_manual_approval"
            else "collect_more_samples",
            "manual_approval_required": True,
        },
        "external_intake_health": _console_quality_center_external_intake_health({}),
    }


def _quality_center_review_queue(
    agent_summaries: list[dict[str, Any]], adoption: dict[str, Any]
) -> list[dict[str, Any]]:
    review_items: list[dict[str, Any]] = []
    for summary in agent_summaries:
        if summary["quality_state"] != "healthy":
            review_items.append(
                _quality_center_review_item(
                    summary,
                    review_type="quality_evidence",
                    reason="missing_or_low_confidence_evidence",
                    recommended_action="collect_more_evidence",
                )
            )
        comparison_state = str(
            summary.get("scorer_comparison", {}).get("comparison_state") or ""
        )
        if comparison_state in {
            "ready_for_manual_approval",
            "needs_human_review",
            "insufficient_evidence",
        }:
            review_items.append(
                _quality_center_review_item(
                    summary,
                    review_type="scorer_rollout",
                    reason=comparison_state,
                    recommended_action=str(
                        summary.get("scorer_comparison", {}).get("recommendation")
                        or "collect_more_samples"
                    ),
                )
            )
        if summary["lifecycle_state"] != "healthy":
            review_items.append(
                _quality_center_review_item(
                    summary,
                    review_type="lifecycle",
                    reason=str(summary["lifecycle_state"]),
                    recommended_action=str(summary["lifecycle_action"]),
                )
            )

    for signal in adoption.get("reviewSignals", []):
        review_items.append(
            {
                "id": f"quality_center_adoption_{_slug(str(signal.get('id') or 'review'))}",
                "agent_id": _display_safe_text(str(signal.get("title") or "adoption")),
                "version": "console_snapshot",
                "review_type": "quality_evidence",
                "reason": _display_safe_text(str(signal.get("reason") or "review")),
                "recommended_action": "open_ops_review",
                "owner_team": _display_safe_text(
                    str(signal.get("owner") or "质量负责人")
                ),
                "manual_review_required": True,
                "automatic_action_performed": False,
            }
        )
    return review_items


def _quality_center_review_item(
    summary: dict[str, Any], *, review_type: str, reason: str, recommended_action: str
) -> dict[str, Any]:
    agent_id = str(summary.get("agent_id") or "unknown_agent")
    version = str(summary.get("version") or "unknown")
    return {
        "id": f"quality_center_{_slug(review_type)}_{_slug(agent_id)}_{_slug(reason)}",
        "agent_id": agent_id,
        "version": version,
        "review_type": review_type,
        "reason": _display_safe_text(reason),
        "recommended_action": _display_safe_text(recommended_action),
        "owner_team": _display_safe_text(str(summary.get("owner_team") or "")),
        "manual_review_required": True,
        "automatic_action_performed": False,
    }


def _quality_center_trend_summary(
    adoption: dict[str, Any], review_queue: list[dict[str, Any]]
) -> dict[str, Any]:
    metrics = adoption.get("metrics", {})
    return {
        "report_state": "ready" if metrics else "insufficient_data",
        "retention_rate": str(metrics.get("retention_rate") or "0%"),
        "review_queue_size": len(review_queue),
        "rework_rounds": int(metrics.get("rework_rounds") or 0),
        "pr_review_findings": int(metrics.get("pr_review_findings") or 0),
        "recommendation": "人工复核缺证据、低置信和评分器发布项；不执行自动生命周期动作。",
    }


def _quality_center_quality_state(status: str) -> str:
    if status in {"healthy", "normal", "ok", "succeeded"}:
        return "healthy"
    if status in {"degraded", "warning", "warn", "pending"}:
        return "watching"
    if status in {"redaction_failed", "permission_denied", "failed", "blocked"}:
        return "needs_review"
    if status in {"block", "critical"}:
        return "critical"
    return "insufficient_evidence"


def _quality_center_lifecycle_state(quality_state: str) -> str:
    if quality_state == "healthy":
        return "healthy"
    if quality_state == "watching":
        return "watching"
    if quality_state == "critical":
        return "disable_review_recommended"
    return "review_required"


def _quality_center_lifecycle_action(quality_state: str) -> str:
    if quality_state == "healthy":
        return "none"
    if quality_state == "watching":
        return "watch"
    if quality_state == "critical":
        return "open_disable_review"
    return "open_ops_review"


def _quality_center_comparison_state(status: str) -> str:
    if status in {"healthy", "normal", "ok", "succeeded"}:
        return "ready_for_manual_approval"
    if status in {
        "redaction_failed",
        "permission_denied",
        "failed",
        "blocked",
        "block",
    }:
        return "needs_human_review"
    return "insufficient_evidence"


def _quality_center_confidence(status: str) -> float:
    if status in {"healthy", "normal", "ok", "succeeded"}:
        return 0.86
    if status in {"degraded", "warning", "warn", "pending"}:
        return 0.62
    return 0.38


def _quality_center_score(value: Any) -> float:
    text = str(value or "")
    digits = "".join(ch for ch in text if ch.isdigit() or ch == ".")
    if not digits:
        return 0.0
    try:
        return min(float(digits), 100.0)
    except ValueError:
        return 0.0


def _safe_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    if isinstance(value, bool):
        return float(value)
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _safe_count_map(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    return {
        _display_safe_text(str(key)): _safe_int(count) for key, count in value.items()
    }


def _safe_scorer_refs(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    refs: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        scorer_id = _display_safe_text(str(item.get("scorer_id") or ""))
        scorer_version = _display_safe_text(str(item.get("scorer_version") or ""))
        key = (scorer_id, scorer_version)
        if not scorer_id or key in seen:
            continue
        seen.add(key)
        refs.append({"scorer_id": scorer_id, "scorer_version": scorer_version})
    return refs


def _quality_center_missing_evidence(item: dict[str, Any]) -> list[str]:
    status = str(item.get("status") or "")
    if status in {"healthy", "normal", "ok", "succeeded"}:
        return []
    evidence_ref = _display_safe_text(str(item.get("evidence_ref") or "summary"))
    return [evidence_ref or "quality_summary"]


def _display_safe_text(value: str) -> str:
    lowered = value.lower()
    if any(
        marker in lowered
        for marker in ("http://", "https://", "://", "secret", "token")
    ):
        return "[redacted]"
    return value


def _evidence_vault_workbench(console_data: dict[str, Any]) -> dict[str, Any]:
    evidence_items = list(console_data.get("evidence", []))
    return {
        "requests": [_evidence_vault_request(item) for item in evidence_items],
        "grants": [_evidence_vault_grant(item) for item in evidence_items],
        "auditTrail": [_evidence_vault_audit(item) for item in evidence_items],
        "guardrails": [
            "默认不展示原文，只展示脱敏摘要、哈希和审计引用。",
            "原文访问申请必须绑定申请理由、审批范围、TTL 和 audit_id。",
            "脱敏失败时只保留哈希和告警，不生成下载链接。",
            "本阶段只读展示申请与授权状态，不自动批准、不自动写回。",
        ],
    }


def _sdlc_run_workbench(console_data: dict[str, Any]) -> dict[str, Any]:
    sdlc_runs = list(console_data.get("sdlcRuns", []))
    verified_count = sum(1 for item in sdlc_runs if _sdlc_proof_verified(item))
    pending_count = len(sdlc_runs) - verified_count
    status = (
        "verified_loaded"
        if sdlc_runs and verified_count == len(sdlc_runs)
        else "materialized"
    )
    return {
        "summary": {
            "id": "sdlc_run_summary",
            "adapter_status": str(
                console_data.get("summary", {})
                .get("adapter", {})
                .get("status", "materialized")
            ),
            "proof_state": "verified_loaded"
            if status == "verified_loaded"
            else "unverified",
            "dry_run_state": _sdlc_dry_run_state(sdlc_runs),
            "reporter_ready": verified_count,
            "pending_proofs": pending_count,
            "primary_action": "保持治理加载证明"
            if status == "verified_loaded"
            else "补齐 verified_loaded 机器证明",
            "safety_note": "CLI dry-run、AGENTS.md 或本地仓库事实不构成 verified_loaded 治理激活证明。",
        },
        "reporter": [_sdlc_reporter_item(item) for item in sdlc_runs],
        "outbox": [_sdlc_outbox_item(item) for item in sdlc_runs],
        "eligibility": [_sdlc_eligibility_item(item) for item in sdlc_runs],
        "guardrails": [
            "Reporter active 必须有 machine-verifiable proof，不得由 dry-run 或 AGENTS.md 推导。",
            "Outbox delivered 只表示投递状态，不在 Console 执行 Outbox Replay 或事件重放。",
            "materialized/unverified 只能说明配置已生成或 CLI 预演成功，不构成 verified_loaded 治理激活证明。",
            "L5 条件缺失必须展示 failed_conditions 和下一步动作，不得显示为 healthy。",
            "Ai_AutoSDLC 运行工作台不得展示原始载荷、下载链接、PR 原文、diff、patch 或外部 URL。",
        ],
    }


def _sdlc_dry_run_state(items: list[dict[str, Any]]) -> str:
    if not items:
        return "empty"
    return (
        "dry_run_passed"
        if all(item.get("dry_run_status") == "dry_run_passed" for item in items)
        else "pending"
    )


def _sdlc_proof_verified(item: dict[str, Any]) -> bool:
    proof_text = f"{item.get('proof_source', '')} {item.get('captured_at', '')}"
    pending = any(
        marker in proof_text for marker in ("待采集", "待接入", "CLI 预演", "AGENTS.md")
    )
    return (
        item.get("verified_loaded") == "verified_loaded"
        and bool(item.get("proof_source"))
        and bool(item.get("captured_at"))
        and not pending
    )


def _sdlc_run_ref(item: dict[str, Any]) -> str:
    return str(item.get("run_id") or item.get("id") or "unknown_sdlc_run")


def _sdlc_reporter_item(item: dict[str, Any]) -> dict[str, Any]:
    verified = _sdlc_proof_verified(item)
    run_ref = _sdlc_run_ref(item)
    adapter_status = str(item.get("adapter_status", "materialized"))
    return {
        "id": f"sdlc_reporter_{_slug(run_ref)}",
        "run_id": run_ref,
        "command": str(item.get("command", "Ai_AutoSDLC run")),
        "reporter_status": "active" if verified else "materialized",
        "integration_mode": "enterprise_managed",
        "credential_status": "active" if verified else "unverified",
        "source_signed": "active" if verified else "unverified",
        "identity_confidence": "verified_loaded" if verified else "unverified",
        "governance_state": adapter_status,
        "proof_source": str(item.get("proof_source", "")),
        "primary_action": "保持 Reporter 心跳" if verified else "补齐治理加载证明",
        "safety_note": "只读 Reporter 摘要，不签发凭证、不绑定设备、不执行企业激活。",
    }


def _sdlc_outbox_item(item: dict[str, Any]) -> dict[str, Any]:
    verified = _sdlc_proof_verified(item)
    run_ref = _sdlc_run_ref(item)
    return {
        "id": f"sdlc_outbox_{_slug(run_ref)}",
        "run_id": run_ref,
        "outbox_status": "healthy" if verified else "pending",
        "sequence_state": "healthy" if verified else "pending",
        "pending_events": "0" if verified else "待验证",
        "oldest_pending_age": "0 分钟" if verified else "待采集",
        "replay_boundary": "只读摘要，不在 Console 执行 Outbox Replay 或事件重放。",
        "evidence_impact": "可进入 L5 复核"
        if verified
        else "pending L5 verification，不提升证据等级。",
        "audit_id": f"audit_sdlc_{_slug(run_ref)}",
        "safety_note": "Outbox Replay 必须由后端审批流程执行，本页不提供重放按钮。",
    }


def _sdlc_eligibility_item(item: dict[str, Any]) -> dict[str, Any]:
    verified = _sdlc_proof_verified(item)
    run_ref = _sdlc_run_ref(item)
    failed_conditions = (
        "无" if verified else "governance_loaded,source_signed,outbox_delivered"
    )
    return {
        "id": f"sdlc_eligibility_{_slug(run_ref)}",
        "run_id": run_ref,
        "evidence_level": "L5" if verified else "pending",
        "l5_result": "healthy" if verified else "pending",
        "failed_conditions": failed_conditions,
        "policy_state_known": "allow" if verified else "unknown",
        "governance_loaded": "verified_loaded" if verified else "unverified",
        "verification_fresh": "healthy" if verified else "pending",
        "outbox_delivered": "healthy" if verified else "pending",
        "next_action": "保持证据链"
        if verified
        else "补齐 verified_loaded、签名来源和 Outbox delivered 证明",
        "safety_note": "Eligibility 仅解释 L5 条件，不覆盖 AgentOps 后端最终等级判定。",
    }


def _approval_workbench(console_data: dict[str, Any]) -> dict[str, Any]:
    approvals = list(console_data.get("approvals", []))
    return {
        "queues": [_approval_queue_item(item) for item in approvals],
        "grants": [_approval_grant_item(item) for item in approvals],
        "auditTrail": [_approval_audit_item(item) for item in approvals],
        "guardrails": [
            "审批队列只展示人工处置摘要，不在本页执行批准、拒绝或撤销。",
            "Grant 必须绑定原始审批编号、策略版本、资源范围、授权时限和审计编号。",
            "申请人不得作为唯一审批人批准自己的高风险动作，除非存在 break_glass 审计。",
            "补充材料只展示摘要和审计引用，不展示原文、PR 正文或下载链接。",
        ],
    }


def _approval_queue_item(approval: dict[str, Any]) -> dict[str, str]:
    status = str(approval["status"])
    return {
        "id": f"approval_queue_{approval['approval_id']}",
        "approval_id": str(approval["approval_id"]),
        "requester": str(approval["requester"]),
        "reason": str(approval["reason"]),
        "affected_actions": str(approval["affected_actions"]),
        "status": status,
        "sla_due_at": str(approval["sla_due_at"]),
        "sla_state": _approval_sla_state(status),
        "approver_scope": _approval_approver_scope(approval),
        "supplemental_materials": _approval_supplemental_materials(approval),
        "primary_action": _approval_primary_action(approval),
        "secondary_action": _approval_secondary_action(approval),
        "audit_id": str(approval["audit_id"]),
        "denied_scope": _approval_denied_scope(approval),
        "safety_note": "只读展示审批处置摘要，不执行批准、拒绝、撤销或生产写操作。",
    }


def _approval_grant_item(approval: dict[str, Any]) -> dict[str, str]:
    grant_status = _approval_grant_status(approval)
    return {
        "id": f"approval_grant_{approval['approval_id']}",
        "approval_id": str(approval["approval_id"]),
        "grant_status": grant_status,
        "policy_version": str(approval.get("policy_version") or "runtime-v2.3"),
        "resource_scope": str(
            approval.get("resource_scope")
            or approval.get("affected_actions")
            or "待确认范围"
        ),
        "ttl_summary": _approval_grant_ttl(grant_status),
        "expires_at": _approval_grant_expires_at(approval, grant_status),
        "revocation_state": _approval_revocation_state(grant_status),
        "audit_id": str(approval["audit_id"]),
        "consumption_policy": "Grant 仅可由绑定审批、策略版本和资源范围消费；本页不执行生产写操作。",
    }


def _approval_grant_status(approval: dict[str, Any]) -> str:
    status = str(approval["status"])
    grant_status = str(approval["grant_status"])
    if status == "approved":
        return grant_status if grant_status in {"active", "expired"} else "active"
    if status == "revoked":
        return "revoked"
    if status == "rejected":
        return "rejected"
    if status == "expired":
        return "expired"
    if status == "escalated":
        return "expired" if grant_status == "expired" else "pending"
    if status in {"pending", "needs_more_info"}:
        return "pending"
    return "pending" if grant_status == "active" else grant_status


def _approval_audit_item(approval: dict[str, Any]) -> dict[str, str]:
    status = str(approval["status"])
    return {
        "id": f"approval_audit_{approval['approval_id']}",
        "approval_id": str(approval["approval_id"]),
        "stage": _approval_audit_stage(status),
        "occurred_at": "快照生成时",
        "summary": _approval_audit_summary(approval),
        "owner": _approval_approver_scope(approval),
        "status": status,
        "audit_id": str(approval["audit_id"]),
    }


def _approval_sla_state(status: str) -> str:
    if status == "escalated":
        return "已升级"
    if status == "pending":
        return "待处理"
    if status == "approved":
        return "已完成"
    if status == "revoked":
        return "已撤销"
    if status == "rejected":
        return "已拒绝"
    if status == "expired":
        return "已过期"
    if status == "needs_more_info":
        return "待补充材料"
    return "需复核"


def _approval_approver_scope(approval: dict[str, Any]) -> str:
    return str(approval.get("approver_scope") or "安全/IAM 审批人")


def _approval_supplemental_materials(approval: dict[str, Any]) -> str:
    return str(
        approval.get("supplemental_materials") or "待补充：变更说明、影响范围、回滚预案"
    )


def _approval_denied_scope(approval: dict[str, Any]) -> str:
    status = str(approval["status"])
    if status in {"rejected", "revoked", "permission_denied"}:
        return str(
            approval.get("denied_scope")
            or approval.get("affected_actions")
            or "approval.scope"
        )
    return str(approval.get("denied_scope") or "")


def _approval_grant_ttl(grant_status: str) -> str:
    if grant_status == "active":
        return "15 分钟限时 Grant"
    if grant_status == "expired":
        return "Grant 已过期"
    if grant_status == "revoked":
        return "Grant 已撤销"
    if grant_status == "rejected":
        return "未签发 Grant"
    return "待审批后签发"


def _approval_grant_expires_at(approval: dict[str, Any], grant_status: str) -> str:
    if grant_status == "active":
        return str(approval.get("grant_expires_at") or "快照生成后 15 分钟")
    if grant_status == "expired":
        return "已过期"
    if grant_status == "revoked":
        return "已撤销"
    if grant_status == "rejected":
        return "未授权"
    return "待审批"


def _approval_revocation_state(grant_status: str) -> str:
    if grant_status == "revoked":
        return "已撤销，后续 Policy Check 不得 conditional_allow"
    if grant_status == "expired":
        return "已过期，需重新审批"
    if grant_status == "active":
        return "未撤销，仍需按资源范围和授权时限消费"
    return "未签发"


def _approval_audit_stage(status: str) -> str:
    if status == "approved":
        return "批准"
    if status == "rejected":
        return "拒绝"
    if status == "revoked":
        return "撤销"
    if status == "expired":
        return "过期"
    if status == "escalated":
        return "升级"
    if status == "needs_more_info":
        return "补充材料"
    return "申请"


def _approval_audit_summary(approval: dict[str, Any]) -> str:
    return f"{approval['requester']} 申请 {approval['affected_actions']}：{approval['reason']}。"


def _evidence_vault_request(evidence: dict[str, Any]) -> dict[str, Any]:
    state = str(evidence["raw_access_state"])
    return {
        "id": f"vault_req_{evidence['evidence_id']}",
        "evidence_id": str(evidence["evidence_id"]),
        "run_id": str(evidence["run_id"]),
        "requester": "证据负责人",
        "reason": _evidence_vault_reason(evidence),
        "status": _evidence_vault_request_status(state),
        "denied_scope": str(evidence.get("denied_scope") or ""),
        "audit_id": str(evidence["audit_id"]),
        "ttl_summary": _evidence_vault_ttl(state),
        "primary_action": _evidence_vault_primary_action(state),
        "safety_note": "仅记录原文访问申请摘要，不展示 Evidence Vault 原文。",
    }


def _evidence_vault_grant(evidence: dict[str, Any]) -> dict[str, Any]:
    state = str(evidence["raw_access_state"])
    return {
        "id": f"vault_grant_{evidence['evidence_id']}",
        "evidence_id": str(evidence["evidence_id"]),
        "requester": "证据负责人",
        "status": _evidence_vault_grant_status(state),
        "scope": _evidence_vault_scope(evidence),
        "expires_at": _evidence_vault_expires_at(state),
        "audit_id": str(evidence["audit_id"]),
        "consumption_policy": "只读复核窗口内可查看授权记录；不提供原文下载。",
    }


def _evidence_vault_audit(evidence: dict[str, Any]) -> dict[str, Any]:
    state = str(evidence["raw_access_state"])
    return {
        "id": f"vault_audit_{evidence['evidence_id']}",
        "evidence_id": str(evidence["evidence_id"]),
        "stage": _evidence_vault_stage(state),
        "occurred_at": "快照生成时",
        "summary": _evidence_vault_audit_summary(evidence),
        "owner": "证据负责人",
        "status": state,
        "audit_id": str(evidence["audit_id"]),
    }


def _evidence_vault_request_status(state: str) -> str:
    if state == "summary_only":
        return "pending"
    if state in {"approved_limited", "redaction_failed", "permission_denied"}:
        return state
    return "pending"


def _evidence_vault_grant_status(state: str) -> str:
    if state == "approved_limited":
        return "active"
    if state == "permission_denied":
        return "rejected"
    if state == "redaction_failed":
        return "redaction_failed"
    return "pending"


def _evidence_vault_reason(evidence: dict[str, Any]) -> str:
    state = str(evidence["raw_access_state"])
    if state == "approved_limited":
        return "复核窗口已获得限定范围授权，仅查看授权记录。"
    if state == "degraded":
        return "运行降级，需先补齐 L5/治理证据后再申请原文访问。"
    if state == "redaction_failed":
        return "脱敏失败，需要先修复脱敏或补充审批理由。"
    if state == "permission_denied":
        return "当前权限边界拒绝访问，需要补充限定范围申请。"
    return "默认仅查看安全摘要，必要时发起原文访问申请。"


def _evidence_vault_ttl(state: str) -> str:
    if state == "approved_limited":
        return "15 分钟限时窗口"
    if state == "degraded":
        return "待补偿"
    if state == "permission_denied":
        return "未授权"
    if state == "redaction_failed":
        return "脱敏失败，暂停授权"
    return "待审批"


def _evidence_vault_primary_action(state: str) -> str:
    if state == "approved_limited":
        return "查看授权记录"
    if state == "degraded":
        return "等待审批"
    if state == "permission_denied":
        return "补充申请理由"
    if state == "redaction_failed":
        return "仅查看哈希告警"
    return "申请原文访问"


def _evidence_vault_scope(evidence: dict[str, Any]) -> str:
    state = str(evidence["raw_access_state"])
    denied_scope = str(evidence.get("denied_scope") or "")
    if state == "approved_limited":
        return "限定复核字段"
    if state == "degraded":
        return denied_scope or "待补偿范围"
    if denied_scope:
        return denied_scope
    return "待审批范围"


def _evidence_vault_expires_at(state: str) -> str:
    if state == "approved_limited":
        return "快照生成后 15 分钟"
    if state == "degraded":
        return "待补偿"
    if state == "permission_denied":
        return "未授权"
    if state == "redaction_failed":
        return "暂停授权"
    return "待审批"


def _evidence_vault_stage(state: str) -> str:
    if state == "approved_limited":
        return "授权"
    if state == "degraded":
        return "降级"
    if state == "permission_denied":
        return "拒绝"
    if state == "redaction_failed":
        return "脱敏失败"
    return "申请"


def _evidence_vault_audit_summary(evidence: dict[str, Any]) -> str:
    state = str(evidence["raw_access_state"])
    if state == "redaction_failed":
        return "脱敏失败，审计仅保留哈希和告警。"
    if state == "degraded":
        return "运行降级，原文访问保持待审批，仅展示摘要和哈希。"
    if state == "permission_denied":
        return "访问被拒绝，需补充限定范围申请理由。"
    if state == "approved_limited":
        return "限定范围授权已记录，原文仍不在控制台展示。"
    return "原文访问尚未批准，继续展示安全摘要。"


def _operation_center(console_data: dict[str, Any]) -> dict[str, Any]:
    notifications: list[dict[str, str]] = []
    todos: list[dict[str, str]] = []
    protected_todos: list[dict[str, str]] = []
    search_index: list[dict[str, str]] = []
    protected_search_index: list[dict[str, str]] = []

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
                    _approval_action_id(approval),
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
                    _approval_action_id(approval),
                )
            )

    for evidence in console_data.get("evidence", []):
        if evidence.get("raw_access_state") in {
            "redaction_failed",
            "permission_denied",
        }:
            notifications.append(
                _notification(
                    f"notif_{evidence['evidence_id']}",
                    "证据需要关注",
                    str(evidence["summary"]),
                    str(evidence["raw_access_state"]),
                    "evidence",
                    str(evidence["audit_id"]),
                    _evidence_action_id(evidence),
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
                    _evidence_action_id(evidence),
                )
            )

    for risk in console_data.get("risks", []):
        is_agent_store_gap = str(risk["source"]) == "Agent Store" and str(
            risk["id"]
        ).startswith("gap_")
        notifications.append(
            _notification(
                f"notif_{risk['id']}",
                f"{risk['source']} 风险",
                _localized_action(str(risk["primary_action"])),
                str(risk["state"]),
                str(risk["deep_link"]),
                str(risk["id"]),
                _gap_action_id(risk) if is_agent_store_gap else _risk_action_id(risk),
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
                _risk_action_id(risk),
            )
        )

    for gap in console_data.get("agentStore", {}).get("discoveryGaps", []):
        protected_todos.append(
            _todo(
                f"todo_{gap['gap_id']}",
                "补齐 Agent Store 注册事实",
                f"{gap['agent_id']} / {gap['version']}",
                str(gap["owner_hint"]),
                str(gap["state"]),
                "agent-store-audit",
                "待排期",
                _gap_action_id(gap),
            )
        )

    for run in console_data.get("runs", []):
        search_index.append(
            _search_item(
                str(run["run_id"]),
                "运行记录",
                f"{run['agent']} / {run['skill']}",
                "runs",
                str(run["l5_state"]),
            )
        )
    for evidence in console_data.get("evidence", []):
        search_index.append(
            _search_item(
                str(evidence["evidence_id"]),
                "证据检索",
                str(evidence["summary"]),
                "evidence",
                str(evidence["raw_access_state"]),
                _evidence_action_id(evidence),
            )
        )
    for approval in console_data.get("approvals", []):
        search_index.append(
            _search_item(
                str(approval["approval_id"]),
                "审批中心",
                str(approval["reason"]),
                "approvals",
                str(approval["status"]),
                _approval_action_id(approval),
            )
        )
    for risk in console_data.get("risks", []):
        if str(risk["source"]) == "Agent Store" and str(risk["id"]).startswith("gap_"):
            continue
        search_index.append(
            _search_item(
                str(risk["id"]),
                str(risk["source"]),
                _localized_action(str(risk["primary_action"])),
                str(risk["deep_link"]),
                str(risk["state"]),
                _risk_action_id(risk),
            )
        )
    for gap in console_data.get("agentStore", {}).get("discoveryGaps", []):
        protected_search_index.append(
            _search_item(
                str(gap["gap_id"]),
                "Agent Store 审计",
                _localized_action(str(gap["primary_action"])),
                "agent-store-audit",
                str(gap["state"]),
                _gap_action_id(gap),
            )
        )

    return {
        "notifications": notifications[:8],
        "todos": _prioritized_unique(protected_todos, todos, limit=12),
        "searchIndex": _prioritized_unique(
            protected_search_index, search_index, limit=30
        ),
    }


def _adoption_workbench(console_data: dict[str, Any]) -> dict[str, Any]:
    runs = list(console_data.get("runs", []))
    quality = list(console_data.get("quality", []))
    risks = list(console_data.get("risks", []))
    evidence = list(console_data.get("evidence", []))
    run_count = len(runs)
    degraded_quality = sum(
        1 for item in quality if str(item.get("status")) not in {"healthy", "normal"}
    )
    blocked_risks = sum(
        1
        for item in risks
        if str(item.get("state"))
        in {"block", "redaction_failed", "unverified", "degraded"}
    )
    generated_lines = run_count * 180
    retained_lines = max(
        generated_lines - degraded_quality * 24 - blocked_risks * 16, 0
    )
    human_modified_lines = degraded_quality * 18 + blocked_risks * 9
    deleted_lines = degraded_quality * 7 + blocked_risks * 5
    ci_failure_types = _ci_failure_types(evidence=evidence, risks=risks)
    review_findings = degraded_quality + blocked_risks

    return {
        "metrics": {
            "generated_lines": generated_lines,
            "retained_lines": retained_lines,
            "human_modified_lines": human_modified_lines,
            "deleted_lines": deleted_lines,
            "rework_rounds": max(degraded_quality, blocked_risks),
            "pr_review_findings": review_findings,
            "ci_failure_types": ci_failure_types,
            "retention_rate": f"{round(retained_lines / generated_lines * 100)}%"
            if generated_lines
            else "0%",
        },
        "explanationChains": [_quality_explanation_chain(item) for item in quality],
        "segments": _adoption_segments(
            console_data, retained_lines=retained_lines, generated_lines=generated_lines
        ),
        "reviewSignals": _adoption_review_signals(quality, risks),
        "guardrails": [
            "低置信不自动下架，只进入人工复核和申诉路径。",
            "缺失证据不按 0 分处理，必须展示 missing_evidence。",
            "采纳指标只展示聚合摘要，不包含代码片段、差异内容或 PR 原文。",
            "本阶段不写 Agent Store，不自动降推荐。",
        ],
    }


def _ci_failure_types(
    *, evidence: list[dict[str, Any]], risks: list[dict[str, Any]]
) -> list[str]:
    failure_types: list[str] = []
    if any(
        str(item.get("raw_access_state")) == "redaction_failed" for item in evidence
    ):
        failure_types.append("证据脱敏失败")
    if any(str(item.get("state")) == "block" for item in risks):
        failure_types.append("策略阻断")
    if any(str(item.get("state")) == "unverified" for item in risks):
        failure_types.append("治理加载证明缺失")
    return failure_types or ["未发现阻断型 CI 失败"]


def _quality_explanation_chain(item: dict[str, Any]) -> dict[str, Any]:
    category = str(item.get("category") or "质量信号")
    status = str(item.get("status") or "unknown")
    score = str(item.get("score") or "待评估")
    evidence_ref = str(item.get("evidence_ref") or "待补充")
    owner = str(item.get("owner_hint") or "质量负责人")
    missing_evidence = _quality_missing_evidence(item)
    return {
        "id": f"chain_{_slug(str(item.get('signal_id') or item.get('id') or category))}",
        "signal_id": str(item.get("signal_id") or item.get("id") or "unknown_signal"),
        "category": category,
        "status": status,
        "score": score,
        "score_template_id": f"quality_summary_{_slug(category)}",
        "evidence_level": _quality_evidence_level(status),
        "confidence": _quality_confidence(status),
        "missing_evidence": missing_evidence,
        "explanation": f"{category} 当前评分为 {score}，依据 {evidence_ref} 形成摘要判断。",
        "appeal_path": f"联系{owner}补充证据或发起人工复核。",
        "lifecycle_guardrail": "低置信不自动下架。",
    }


def _quality_missing_evidence(item: dict[str, Any]) -> list[str]:
    status = str(item.get("status") or "unknown")
    evidence_ref = str(item.get("evidence_ref") or "")
    missing: list[str] = []
    if status in {"unknown", "degraded", "redaction_failed", "pending"}:
        missing.append("可验证质量证据")
    if "待" in evidence_ref or not evidence_ref:
        missing.append("证据引用")
    return missing or ["无阻断缺口"]


def _quality_evidence_level(status: str) -> str:
    if status == "healthy":
        return "L5"
    if status in {"degraded", "redaction_failed", "unknown"}:
        return "L3"
    return "pending"


def _quality_confidence(status: str) -> float:
    if status == "healthy":
        return 0.92
    if status in {"degraded", "redaction_failed"}:
        return 0.68
    if status == "unknown":
        return 0.45
    return 0.58


def _adoption_segments(
    console_data: dict[str, Any], *, retained_lines: int, generated_lines: int
) -> list[dict[str, str]]:
    agent_store_summary_count = len(
        console_data.get("agentStore", {}).get("storeSummaries", [])
    )
    retention_rate = (
        f"{round(retained_lines / generated_lines * 100)}%" if generated_lines else "0%"
    )
    sdlc_status = (
        "empty"
        if generated_lines == 0
        else "healthy"
        if retained_lines >= generated_lines * 0.75
        else "degraded"
    )
    return [
        {
            "id": "segment_sdlc_runs",
            "title": "Ai_AutoSDLC 标准路径",
            "status": sdlc_status,
            "retention_rate": retention_rate,
            "affected_agents": str(len(console_data.get("runs", []))),
            "owner": "SDLC 负责人",
            "next_review": "按周复核采纳摘要",
        },
        {
            "id": "segment_agent_store_echo",
            "title": "Agent Store 回显",
            "status": "pending" if agent_store_summary_count else "empty",
            "retention_rate": "待采集",
            "affected_agents": str(agent_store_summary_count),
            "owner": "Agent 负责人",
            "next_review": "等待注册事实同步后复核",
        },
    ]


def _adoption_review_signals(
    quality: list[dict[str, Any]], risks: list[dict[str, Any]]
) -> list[dict[str, str]]:
    signals: list[dict[str, str]] = []
    for item in quality:
        if str(item.get("status")) == "healthy":
            continue
        signals.append(
            {
                "id": f"review_{_slug(str(item.get('signal_id') or item.get('id') or item.get('category') or 'quality'))}",
                "title": f"{item.get('category', '质量信号')} 需要人工复核",
                "status": str(item.get("status") or "unknown"),
                "owner": str(item.get("owner_hint") or "质量负责人"),
                "evidence_ref": str(item.get("evidence_ref") or "待补充"),
                "reason": "低置信或缺失证据只进入复核队列，不自动下架。",
                "action": "发起人工复核",
            }
        )
    for risk in risks:
        if str(risk.get("state")) not in {"block", "redaction_failed", "unverified"}:
            continue
        signals.append(
            {
                "id": f"review_{_slug(str(risk.get('id') or 'risk'))}",
                "title": f"{risk.get('source', '风险')} 影响采纳判断",
                "status": str(risk.get("state") or "unknown"),
                "owner": str(risk.get("owner_hint") or "风险负责人"),
                "evidence_ref": str(risk.get("id") or "待补充"),
                "reason": "风险归因会降低采纳置信度，但不触发自动生命周期动作。",
                "action": "补充风险处置证明",
            }
        )
    return signals[:8]


def _notification(
    notification_id: str,
    title: str,
    body: str,
    status: str,
    route: str,
    ref: str,
    action_id: str = "",
) -> dict[str, str]:
    return {
        "id": notification_id,
        "title": title,
        "body": body,
        "status": status,
        "route": route,
        "ref": ref,
        "action_id": action_id,
    }


def _todo(
    todo_id: str,
    title: str,
    body: str,
    owner: str,
    status: str,
    route: str,
    due: str,
    action_id: str = "",
) -> dict[str, str]:
    return {
        "id": todo_id,
        "title": title,
        "body": body,
        "owner": owner,
        "status": status,
        "route": route,
        "due": due,
        "action_id": action_id,
    }


def _search_item(
    item_id: str, kind: str, title: str, route: str, status: str, action_id: str = ""
) -> dict[str, str]:
    return {
        "id": item_id,
        "kind": kind,
        "title": title,
        "route": route,
        "status": status,
        "action_id": action_id,
    }


def _prioritized_unique(
    protected_items: list[dict[str, str]], items: list[dict[str, str]], *, limit: int
) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in [*protected_items, *items]:
        item_id = item["id"]
        if item_id in seen:
            continue
        seen.add(item_id)
        selected.append(item)
        if len(selected) == limit:
            break
    return selected


def _action_workbench(console_data: dict[str, Any]) -> dict[str, Any]:
    details: list[dict[str, str]] = []
    protected_details: list[dict[str, str]] = []
    for approval in console_data.get("approvals", []):
        details.append(
            _action_detail(
                _approval_action_id(approval),
                "审批处置",
                str(approval["reason"]),
                str(approval["status"]),
                "approvals",
                "审批负责人",
                _approval_primary_action(approval),
                _approval_secondary_action(approval),
                f"SLA 重置或审批状态更新为完成态；Grant 状态同步为 {approval['grant_status']}。",
                str(approval["audit_id"]),
                "",
                str(approval["approval_id"]),
            )
        )
    for evidence in console_data.get("evidence", []):
        target = (
            protected_details
            if evidence.get("raw_access_state")
            in {"redaction_failed", "permission_denied", "degraded"}
            else details
        )
        target.append(
            _action_detail(
                _evidence_action_id(evidence),
                "证据处置",
                str(evidence["summary"]),
                str(evidence["raw_access_state"]),
                "evidence",
                "证据负责人",
                _evidence_primary_action(evidence),
                _evidence_secondary_action(evidence),
                _evidence_close_condition(evidence),
                str(evidence["audit_id"]),
                str(evidence["evidence_id"]),
                str(evidence["run_id"]),
            )
        )
    for risk in console_data.get("risks", []):
        if str(risk["source"]) == "Agent Store" and str(risk["id"]).startswith("gap_"):
            continue
        details.append(
            _action_detail(
                _risk_action_id(risk),
                f"{risk['source']} 风险处置",
                f"{risk['source']} / {risk['severity']} / {_localized_action(str(risk['primary_action']))}",
                str(risk["state"]),
                str(risk["deep_link"]),
                str(risk["owner_hint"]),
                _localized_action(str(risk["primary_action"])),
                "转交负责人",
                _close_condition_for_risk(risk),
                str(risk["id"]),
                "",
                str(risk["source"]),
            )
        )
    for gap in console_data.get("agentStore", {}).get("discoveryGaps", []):
        protected_details.append(
            _action_detail(
                _gap_action_id(gap),
                "Agent Store 注册事实处置",
                f"发现 {_localized_gap_type(str(gap['gap_type']))}，需要回到 Agent Store 补齐注册事实。",
                str(gap["state"]),
                "agent-store-audit",
                str(gap["owner_hint"]),
                _localized_action(str(gap["primary_action"])),
                "转交 Agent 负责人",
                "Agent Store 注册事实已同步为已治理、已忽略或已阻断，且影响运行已完成审计回显。",
                str(gap["audit_id"]),
                "",
                ",".join(str(run_id) for run_id in gap.get("affected_runs", [])),
            )
        )
    return {
        "details": _prioritized_unique(
            protected_details, details, limit=len(protected_details) + len(details)
        )
    }


def _action_detail(
    action_id: str,
    title: str,
    summary: str,
    status: str,
    route: str,
    owner: str,
    primary_action: str,
    secondary_action: str,
    close_condition: str,
    audit_ref: str,
    evidence_ref: str,
    related_ref: str,
) -> dict[str, Any]:
    safety_note = "当前为只读处置预案，不执行生产写操作。"
    return {
        "id": action_id,
        "title": title,
        "summary": summary,
        "status": status,
        "route": route,
        "owner": owner,
        "primary_action": primary_action,
        "secondary_action": secondary_action,
        "close_condition": close_condition,
        "audit_ref": audit_ref,
        "evidence_ref": evidence_ref,
        "related_ref": related_ref,
        "safety_note": safety_note,
        "timeline": _action_timeline(
            action_id,
            summary=summary,
            status=status,
            owner=owner,
            primary_action=primary_action,
            close_condition=close_condition,
        ),
        "audit_packet": _audit_packet(
            action_id,
            title=title,
            summary=summary,
            audit_ref=audit_ref,
            evidence_ref=evidence_ref,
            related_ref=related_ref,
        ),
    }


def _action_timeline(
    action_id: str,
    *,
    summary: str,
    status: str,
    owner: str,
    primary_action: str,
    close_condition: str,
) -> list[dict[str, str]]:
    timeline_id = _slug(action_id)
    return [
        _timeline_node(
            f"tl_{timeline_id}_detected",
            "发现",
            "快照生成时",
            "治理信号进入处置队列",
            summary,
            owner,
            status,
        ),
        _timeline_node(
            f"tl_{timeline_id}_triage",
            "研判",
            "快照生成时",
            "已生成建议动作",
            f"建议动作：{primary_action}。",
            owner,
            status,
        ),
        _timeline_node(
            f"tl_{timeline_id}_close",
            "关闭",
            "待完成",
            "等待关闭证明",
            close_condition,
            owner,
            "pending",
        ),
    ]


def _timeline_node(
    node_id: str,
    stage: str,
    occurred_at: str,
    title: str,
    body: str,
    owner: str,
    status: str,
) -> dict[str, str]:
    return {
        "id": node_id,
        "stage": stage,
        "occurred_at": occurred_at,
        "title": title,
        "body": body,
        "owner": owner,
        "status": status,
    }


def _audit_packet(
    action_id: str,
    *,
    title: str,
    summary: str,
    audit_ref: str,
    evidence_ref: str,
    related_ref: str,
) -> dict[str, Any]:
    refs = [item for item in (audit_ref, evidence_ref, related_ref) if item]
    return {
        "packet_id": f"packet_{_slug(action_id)}",
        "summary": f"只读复核包：{title}。{summary}",
        "export_state": "只读摘要已生成",
        "evidence_refs": refs,
        "echo_targets": _audit_echo_targets(action_id),
        "retention_policy": "仅保留摘要、哈希和审计引用；不包含 Evidence Vault 原文。",
        "safety_note": "只读复核包仅用于审计复核，不提供原文下载或生产写操作。",
    }


def _audit_echo_targets(action_id: str) -> list[str]:
    if action_id.startswith("action_gap_"):
        return ["Agent Store 审计", "风险处置", "通知中心"]
    if action_id.startswith("action_approval_"):
        return ["审批中心", "待办中心", "审计详情"]
    if action_id.startswith("action_evidence_"):
        return ["证据检索", "风险处置", "审计详情"]
    return ["风险处置", "通知中心", "审计详情"]


def _approval_action_id(approval: dict[str, Any]) -> str:
    return f"action_approval_{approval['approval_id']}"


def _approval_primary_action(approval: dict[str, Any]) -> str:
    status = str(approval["status"])
    if status in {"pending", "escalated"}:
        return "处理审批"
    if status == "approved":
        return "查看审批记录"
    if status == "revoked":
        return "查看撤销原因"
    if status == "expired":
        return "重新发起审批"
    if status == "rejected":
        return "查看拒绝原因"
    return "查看审批记录"


def _approval_secondary_action(approval: dict[str, Any]) -> str:
    status = str(approval["status"])
    if status in {"pending", "escalated"}:
        return "补充材料或转交审批"
    if status == "approved":
        return "查看 Grant 状态"
    if status == "revoked":
        return "通知申请方"
    if status == "expired":
        return "补充材料"
    if status == "rejected":
        return "通知申请方"
    return "转交审批负责人"


def _evidence_action_id(evidence: dict[str, Any]) -> str:
    return f"action_evidence_{evidence['evidence_id']}"


def _evidence_primary_action(evidence: dict[str, Any]) -> str:
    state = str(evidence["raw_access_state"])
    if state == "permission_denied":
        return "查看申请预案"
    if state == "approved_limited":
        return "查看授权记录"
    if state in {"summary_only", "redaction_failed"}:
        return "查看安全摘要"
    return "查看证据说明"


def _evidence_secondary_action(evidence: dict[str, Any]) -> str:
    state = str(evidence["raw_access_state"])
    if state == "summary_only":
        return "申请限定范围访问"
    if state == "approved_limited":
        return "查看到期时间"
    if state == "permission_denied":
        return "补充申请理由"
    return "转交证据负责人"


def _evidence_close_condition(evidence: dict[str, Any]) -> str:
    state = str(evidence["raw_access_state"])
    if state == "summary_only":
        return "安全摘要可解释、哈希可追溯，且无需查看原文。"
    if state == "approved_limited":
        return "限定范围授权仍在有效期内，审计引用可追溯。"
    return "脱敏摘要可解释、哈希可追溯，且原文访问已审批或明确拒绝。"


def _risk_action_id(risk: dict[str, Any]) -> str:
    return f"action_risk_{risk['id']}"


def _gap_action_id(item: dict[str, Any]) -> str:
    return f"action_gap_{item['gap_id'] if 'gap_id' in item else item['id']}"


def _close_condition_for_risk(risk: dict[str, Any]) -> str:
    source = str(risk["source"])
    if source == "审批中心":
        return "SLA 重置或审批完成，且 Grant 状态完成同步。"
    if source == "证据检索":
        return "证据摘要可解释，脱敏失败或拒绝范围已有审计说明。"
    if source == "Ai_AutoSDLC 运行":
        return "adapter 证明状态明确，不能将 materialized/unverified 误判为 verified_loaded。"
    return "处置动作完成，审计引用可追溯，风险状态不再阻塞当前队列。"


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
    missing = "、".join(
        _localized_evidence_gap(item)
        for item in evaluation["missing_evidence"] or evaluation["failed_conditions"]
    )
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
        "requester": str(
            approval.get("requester") or approval.get("agent_id") or "未知申请方"
        ),
        "reason": str(
            approval.get("reason") or approval.get("request_reason") or "需要审批后继续"
        ),
        "affected_actions": str(
            approval.get("affected_actions")
            or approval.get("resource_scope")
            or "未声明动作"
        ),
        "sla_due_at": str(
            approval.get("sla_due_at") or approval.get("expires_at") or "待确认"
        ),
        "status": str(approval.get("status") or "pending"),
        "grant_status": str(approval.get("grant_status") or "pending"),
        "audit_id": str(approval.get("audit_id") or f"audit_{approval_id}"),
    }


def _policies_from_grants(grants: tuple[dict[str, Any], ...]) -> list[dict[str, str]]:
    if not grants:
        return [
            _policy(
                "pol_repository_default",
                "warn",
                "本地事实接入",
                "require_online",
                "runtime-v2",
                "无",
                "audit_repository_default",
            )
        ]
    return [
        _policy(
            str(grant.get("grant_id") or "grant_unknown"),
            "conditional_allow" if grant.get("status") == "active" else "block",
            str(grant.get("resource_scope") or "未声明动作"),
            "require_online",
            str(grant.get("policy_version") or "runtime-v2"),
            str(grant.get("expires_at") or "待确认"),
            str(
                grant.get("audit_id")
                or f"audit_{grant.get('grant_id') or 'grant_unknown'}"
            ),
        )
        for grant in sorted(
            grants, key=lambda item: str(item.get("grant_id") or "grant_unknown")
        )
    ]


def _repository_connectors(
    repository: InMemoryRepository, *, event_count: int | None = None
) -> list[dict[str, str]]:
    now = datetime.now(UTC).isoformat()
    event_count = repository.raw_event_count() if event_count is None else event_count
    metadata_count = len(repository.agent_store_metadata_records())
    agent_store_status = "healthy" if metadata_count else "degraded"
    agent_store_action = (
        f"{metadata_count} 条元数据快照"
        if metadata_count
        else "等待 Agent Store 元数据同步"
    )
    return [
        _connector(
            "conn_agent_store",
            "Agent Store",
            agent_store_status,
            now,
            agent_store_action,
            "req_conn_agent_store",
        ),
        _connector(
            "conn_ingestion", "事件接入", "healthy", now, "无", "req_conn_ingestion"
        ),
        _connector(
            "conn_repository",
            "运行事实仓库",
            "healthy",
            now,
            f"{event_count} 条事件",
            "req_conn_repository",
        ),
        _connector("conn_git", "Git 仓库", "healthy", now, "无", "req_conn_git"),
        _connector("conn_pr", "PR 服务", "healthy", now, "无", "req_conn_pr"),
        _connector(
            "conn_ci", "CI 检查", "degraded", now, "降级为本地检查摘要", "req_conn_ci"
        ),
        _connector("conn_test", "测试执行", "healthy", now, "无", "req_conn_test"),
        _connector(
            "conn_sdlc",
            "Ai_AutoSDLC",
            "materialized",
            now,
            "需要 verified_loaded 机器证明",
            "req_conn_sdlc",
        ),
        _connector(
            "conn_evidence",
            "证据存储",
            "healthy",
            now,
            "仅展示摘要",
            "req_conn_evidence",
        ),
        _connector(
            "conn_policy",
            "策略服务",
            "healthy",
            now,
            "本地内核策略摘要",
            "req_conn_policy",
        ),
        _connector("conn_iam", "IAM/安全", "healthy", now, "无", "req_conn_iam"),
    ]


def _connector_workbench(
    console_data: dict[str, Any], *, repository: InMemoryRepository | None = None
) -> dict[str, Any]:
    connectors = list(console_data.get("connectors", []))
    return {
        "health": [_connector_health(item) for item in connectors],
        "dlq": [_connector_dlq(item) for item in connectors],
        "syncTrail": [_connector_sync_trail(item) for item in connectors],
        "ecosystemGovernance": _ecosystem_governance_workbench(
            console_data, repository=repository
        ),
        "guardrails": [
            "连接器新鲜度 SLO 为 15 分钟内，超过 20 分钟必须告警并降低证据等级。",
            "DLQ 与 Outbox Replay 只展示只读摘要，本页不执行回放、重试或生产写操作。",
            "Git、PR、CI、测试、IAM 等外部连接器必须展示限流状态、降级动作和负责人。",
            "MCP/A2A 必须经 Runtime Gateway 和 Policy Check；直连只能作为 suspected 外部线索。",
            "Exporter 生态只展示 dry-run 摘要和 configuration_hash，本页不执行网络写入。",
            "materialized/unverified 只能说明配置已生成或 CLI 预演成功，不构成 verified_loaded 治理激活证明。",
            "连接器工作台不得展示原始载荷、下载链接、PR 原文或外部 URL。",
        ],
    }


def _ecosystem_governance_workbench(
    console_data: dict[str, Any], *, repository: InMemoryRepository | None = None
) -> dict[str, Any]:
    agent_refs = _quality_center_agent_refs(console_data) or [
        {
            "agent_id": "agent.ai-sdlc",
            "version": "1.0.0",
            "owner_team": "生态治理负责人",
        }
    ]
    first_ref = agent_refs[0]
    subject_agent_id = _display_safe_text(str(first_ref.get("agent_id") or "agent"))
    projection_repo = repository if repository is not None else InMemoryRepository()
    mcp_a2a = [
        _console_mcp_a2a_projection(
            build_mcp_a2a_governance_projection(
                protocol="mcp",
                endpoint_ref="gateway_tools_summary_ref",
                subject_agent_id=subject_agent_id,
                resource_scope="tools.summary",
                requested_by="agentops_console",
                policy_check_state="required",
            )
        ),
        _console_mcp_a2a_projection(
            build_mcp_a2a_governance_projection(
                protocol="a2a",
                endpoint_ref="gateway_agent_handoff_summary_ref",
                subject_agent_id=subject_agent_id,
                resource_scope="agent.handoff",
                requested_by="agentops_console",
                policy_check_state="required",
            )
        ),
    ]
    exporter_projection = build_exporter_ecosystem_projection(
        requested_by="agentops_console",
        exporters=[
            {
                "exporter_id": "otel_summary",
                "exporter_type": "otlp",
                "endpoint_ref": "collector_otlp_summary_ref",
            },
            {
                "exporter_id": "openinference_summary",
                "exporter_type": "openinference",
                "endpoint_ref": "collector_openinference_summary_ref",
            },
        ],
    )
    handoffs = [
        _console_handoff_evaluation(
            build_multi_agent_handoff_evaluation(
                projection_repo,
                str(ref.get("agent_id") or ""),
                str(ref.get("version") or ""),
            )
        )
        for ref in agent_refs[:5]
    ]
    risk_profiles = [
        _console_complex_risk_profile(
            build_complex_risk_profile(
                projection_repo,
                str(ref.get("agent_id") or ""),
                str(ref.get("version") or ""),
            )
        )
        for ref in agent_refs[:5]
    ]
    return {
        "schema_version": "ecosystem_governance_workbench.v1",
        "workbench_state": "ready"
        if mcp_a2a or exporter_projection["exporters"]
        else "empty",
        "mcp_a2a": mcp_a2a,
        "exporters": [
            _console_exporter_item(item) for item in exporter_projection["exporters"]
        ],
        "handoffs": handoffs,
        "riskProfiles": risk_profiles,
        "summary": {
            "runtime_gateway_required": True,
            "direct_connection_allowed": False,
            "external_write_enabled": False,
            "network_dispatch_performed": False,
            "runtime_execution_performed": False,
            "automatic_store_action": False,
            "notification_sent": False,
            "monitored_agent_count": len(agent_refs),
            "ecosystem_state": str(
                exporter_projection.get("ecosystem_state") or "not_configured"
            ),
        },
        "guardrails": [
            "MCP/A2A 只展示 Runtime Gateway 和 Policy Check 摘要，不允许直连。",
            "Exporter 只展示 dry-run configuration_hash，不执行网络写入。",
            "多 Agent 移交只读取 TraceSpan 摘要字段，不重跑 handoff。",
            "复杂风险画像只进入人工复核，不自动 disable、不写 Store、不通知。",
        ],
        "audit_id": "audit_ecosystem_governance_console",
    }


def _console_mcp_a2a_projection(projection: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"ecosystem_{projection.get('protocol')}_{_slug(str(projection.get('subject_agent_id') or 'agent'))}",
        "protocol": str(projection.get("protocol") or ""),
        "endpoint_ref": _display_safe_text(str(projection.get("endpoint_ref") or "")),
        "subject_agent_id": _display_safe_text(
            str(projection.get("subject_agent_id") or "")
        ),
        "resource_scope": _display_safe_text(
            str(projection.get("resource_scope") or "")
        ),
        "gateway_state": str(projection.get("gateway_state") or "required"),
        "policy_check_state": str(projection.get("policy_check_state") or "required"),
        "evidence_state": str(projection.get("evidence_state") or "missing"),
        "runtime_gateway_required": True,
        "direct_connection_allowed": False,
        "runtime_execution_performed": False,
        "external_side_effects_enabled": False,
        "audit_id": _display_safe_text(str(projection.get("audit_id") or "")),
    }


def _console_exporter_item(exporter: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"ecosystem_exporter_{_slug(str(exporter.get('exporter_id') or 'exporter'))}",
        "exporter_id": _display_safe_text(str(exporter.get("exporter_id") or "")),
        "exporter_type": str(exporter.get("exporter_type") or ""),
        "endpoint_ref": _display_safe_text(str(exporter.get("endpoint_ref") or "")),
        "configuration_state": str(
            exporter.get("configuration_state") or "not_configured"
        ),
        "dispatch_state": str(exporter.get("dispatch_state") or "not_started"),
        "external_write_enabled": False,
        "configuration_hash": _display_safe_text(
            str(exporter.get("configuration_hash") or "")
        ),
    }


def _console_handoff_evaluation(evaluation: dict[str, Any]) -> dict[str, Any]:
    summary = (
        evaluation.get("summary") if isinstance(evaluation.get("summary"), dict) else {}
    )
    return {
        "id": f"ecosystem_handoff_{_slug(str(evaluation.get('agent_id') or 'agent'))}_{_slug(str(evaluation.get('version') or 'version'))}",
        "agent_id": _display_safe_text(str(evaluation.get("agent_id") or "")),
        "version": _display_safe_text(str(evaluation.get("version") or "")),
        "handoff_count": _safe_int(evaluation.get("handoff_count")),
        "failed_handoff_count": _safe_int(evaluation.get("failed_handoff_count")),
        "handoff_quality_state": str(
            evaluation.get("handoff_quality_state") or "insufficient_data"
        ),
        "automatic_handoff_action": False,
        "runtime_execution_performed": False,
        "derived_from": _display_safe_text(
            str(summary.get("derived_from") or "trace_span_summary_fields")
        ),
        "audit_id": _display_safe_text(str(evaluation.get("audit_id") or "")),
    }


def _console_complex_risk_profile(profile: dict[str, Any]) -> dict[str, Any]:
    handoff = (
        profile.get("handoff_evaluation")
        if isinstance(profile.get("handoff_evaluation"), dict)
        else {}
    )
    dlq = (
        profile.get("dlq_summary")
        if isinstance(profile.get("dlq_summary"), dict)
        else {}
    )
    return {
        "id": f"ecosystem_risk_{_slug(str(profile.get('agent_id') or 'agent'))}_{_slug(str(profile.get('version') or 'version'))}",
        "agent_id": _display_safe_text(str(profile.get("agent_id") or "")),
        "version": _display_safe_text(str(profile.get("version") or "")),
        "risk_profile_state": str(profile.get("risk_profile_state") or "low"),
        "risk_factor_count": len(profile.get("risk_factors", [])),
        "recommended_action": _display_safe_text(
            str(profile.get("recommended_action") or "none")
        ),
        "handoff_quality_state": str(
            handoff.get("handoff_quality_state") or "insufficient_data"
        ),
        "failed_handoff_count": _safe_int(handoff.get("failed_handoff_count")),
        "dlq_backlog_count": _safe_int(dlq.get("backlog_count")),
        "automatic_runtime_action": False,
        "automatic_store_action": False,
        "audit_id": _display_safe_text(str(profile.get("audit_id") or "")),
    }


def _connector_health(connector: dict[str, Any]) -> dict[str, str]:
    connector_id = str(connector["id"])
    status = str(connector["status"])
    return {
        "id": f"connector_health_{connector_id}",
        "connector_id": connector_id,
        "name": str(connector["name"]),
        "status": status,
        "last_seen_at": str(connector["last_seen_at"]),
        "freshness": _connector_freshness(status),
        "freshness_state": _connector_freshness_state(status),
        "rate_limit_state": _connector_rate_limit_state(connector_id, status),
        "rate_limit_detail": _connector_rate_limit_detail(connector_id, status),
        "degrade_action": str(connector["degrade_action"]),
        "evidence_impact": _connector_evidence_impact(connector),
        "owner": _connector_owner(connector_id),
        "request_id": str(connector["request_id"]),
        "primary_action": _connector_primary_action(connector),
        "secondary_action": _connector_secondary_action(connector),
        "safety_note": "只读健康摘要，不执行连接器重试、回放、写回或权限变更。",
    }


def _connector_dlq(connector: dict[str, Any]) -> dict[str, str]:
    connector_id = str(connector["id"])
    status = str(connector["status"])
    return {
        "id": f"connector_dlq_{connector_id}",
        "connector_id": connector_id,
        "dlq_depth": _connector_dlq_depth(status),
        "oldest_event_age": _connector_oldest_event_age(status),
        "replay_state": _connector_replay_state(status),
        "retry_window": _connector_retry_window(status),
        "degrade_policy": _connector_dlq_policy(connector),
        "request_id": str(connector["request_id"]),
        "audit_id": f"audit_{connector_id}",
        "safety_note": "Outbox Replay 需要人工审批后在后端执行，本页只展示队列摘要。",
    }


def _connector_sync_trail(connector: dict[str, Any]) -> dict[str, str]:
    connector_id = str(connector["id"])
    status = str(connector["status"])
    return {
        "id": f"connector_sync_{connector_id}",
        "connector_id": connector_id,
        "stage": _connector_sync_stage(status),
        "occurred_at": str(connector["last_seen_at"]),
        "summary": _connector_sync_summary(connector),
        "owner": _connector_owner(connector_id),
        "status": status,
        "request_id": str(connector["request_id"]),
    }


def _connector_owner(connector_id: str) -> str:
    owners = {
        "conn_agent_store": "Agent Store 负责人",
        "conn_ingestion": "事件接入负责人",
        "conn_repository": "运行事实仓库负责人",
        "conn_git": "Git 仓库负责人",
        "conn_pr": "PR 服务负责人",
        "conn_ci": "CI 负责人",
        "conn_test": "测试负责人",
        "conn_sdlc": "SDLC 负责人",
        "conn_evidence": "证据负责人",
        "conn_policy": "策略服务负责人",
        "conn_iam": "安全/IAM 负责人",
    }
    return owners.get(connector_id, "连接器负责人")


def _connector_freshness(status: str) -> str:
    if status == "healthy":
        return "15 分钟内"
    if status == "materialized":
        return "配置已生成，待 verified_loaded 证明"
    if status == "degraded":
        return "超过 20 分钟或降级"
    return "待采集"


def _connector_freshness_state(status: str) -> str:
    if status == "healthy":
        return "healthy"
    if status == "materialized":
        return "materialized"
    if status == "degraded":
        return "degraded"
    return "unknown"


def _connector_rate_limit_state(connector_id: str, status: str) -> str:
    if status == "degraded":
        return "degraded"
    if connector_id in {"conn_sdlc", "conn_policy", "conn_evidence"}:
        return "warning"
    return "healthy"


def _connector_rate_limit_detail(connector_id: str, status: str) -> str:
    if status == "degraded":
        return "限流或不可用已影响同步，降低证据等级并进入人工复核。"
    if connector_id == "conn_sdlc":
        return "治理证明未完成，仅低频探测，不提升为 verified_loaded。"
    if connector_id in {"conn_policy", "conn_evidence", "conn_ci"}:
        return "接近配额或依赖外部检查，按低频采集并保留摘要。"
    return "未触发限流，按连接器新鲜度 SLO 采集。"


def _connector_evidence_impact(connector: dict[str, Any]) -> str:
    status = str(connector["status"])
    if status == "healthy":
        return "证据等级不降低"
    if status == "materialized":
        return "仅证明配置已生成，不构成 verified_loaded 治理激活证明"
    return "降低证据等级，相关运行进入人工复核"


def _connector_primary_action(connector: dict[str, Any]) -> str:
    status = str(connector["status"])
    if status == "healthy":
        return "保持监控"
    if status == "degraded":
        return "查看降级影响"
    if status == "materialized":
        return "补齐治理加载证明"
    return "查看降级影响"


def _connector_secondary_action(connector: dict[str, Any]) -> str:
    status = str(connector["status"])
    if status == "healthy":
        return "按 SLO 继续采集心跳"
    if status == "materialized":
        return "等待 verified_loaded 机器证据"
    return "转交负责人并降低相关证据等级"


def _connector_dlq_depth(status: str) -> str:
    if status == "healthy":
        return "0"
    if status == "materialized":
        return "待验证"
    return "3"


def _connector_oldest_event_age(status: str) -> str:
    if status == "healthy":
        return "0 分钟"
    if status == "materialized":
        return "待采集"
    return "22 分钟"


def _connector_replay_state(status: str) -> str:
    if status == "healthy":
        return "healthy"
    if status == "materialized":
        return "materialized"
    return "pending"


def _connector_retry_window(status: str) -> str:
    if status == "healthy":
        return "无需回放"
    if status == "materialized":
        return "待 verified_loaded 后确认"
    return "人工审批后 15 分钟内回放"


def _connector_dlq_policy(connector: dict[str, Any]) -> str:
    status = str(connector["status"])
    if status == "healthy":
        return "无积压，继续按 15 分钟新鲜度 SLO 采集"
    if status == "materialized":
        return "未形成治理激活证明前，不提升证据等级"
    return f"执行降级：{connector['degrade_action']}；Outbox Replay 需人工审批"


def _connector_sync_stage(status: str) -> str:
    if status == "healthy":
        return "同步"
    if status == "materialized":
        return "待证明"
    return "降级"


def _connector_sync_summary(connector: dict[str, Any]) -> str:
    status = str(connector["status"])
    if status == "healthy":
        return f"{connector['name']} 心跳正常，继续按新鲜度 SLO 采集。"
    if status == "materialized":
        return f"{connector['name']} 已生成配置，但仍缺 verified_loaded 机器证明。"
    return f"{connector['name']} 进入降级路径：{connector['degrade_action']}。"


def _repository_sdlc_runs(
    repository: InMemoryRepository, *, event_count: int | None = None
) -> list[dict[str, str]]:
    now = datetime.now(UTC).isoformat()
    event_count = repository.raw_event_count() if event_count is None else event_count
    return [
        _sdlc_run(
            "sdlc_repository_snapshot",
            "console repository snapshot",
            "materialized",
            "dry_run_passed",
            "InMemoryRepository",
            now,
        ),
        _sdlc_run(
            "sdlc_repository_events",
            "ingestion event count",
            "materialized",
            "dry_run_passed",
            f"{event_count} 条事件",
            now,
        ),
    ]


def _credential_handoff_workbench(repository: InMemoryRepository) -> dict[str, Any]:
    rows = [
        _credential_handoff_row(repository, record)
        for record in repository.credential_bootstrap_records()
    ]
    issued_count = sum(
        1 for row in rows if row["bootstrap_status"] == "credential_issued"
    )
    verified_count = sum(
        1 for row in rows if row["bootstrap_status"] == "signature_verified"
    )
    revoked_count = sum(
        1
        for row in rows
        if row["bootstrap_status"] == "revoked" or row["credential_status"] == "revoked"
    )
    reissued_count = sum(
        1 for row in rows if row["revocation_resolution"] == "reissued"
    )
    return {
        "summary": {
            "id": "credential_handoff_summary",
            "schema_version": CONSOLE_CREDENTIAL_STATUS_SCHEMA_VERSION,
            "bootstrap_count": len(rows),
            "credential_issued": issued_count,
            "signature_verified": verified_count,
            "revoked": revoked_count,
            "reissued": reissued_count,
            "agentops_fact_owner": "agentops",
            "agent_store_boundary": "display_only_no_active_inference",
            "verified_loaded": "not_asserted",
            "l5_status": "not_asserted",
            "primary_action": "展示重新签发结果"
            if reissued_count
            else "处理撤销并重新签发"
            if revoked_count
            else "等待签名测试事件"
            if issued_count and not verified_count
            else "展示 AgentOps 回显结果",
            "safety_note": "凭证联调只展示 AgentOps 事实回显，不把 credential 或签名测试事件提升为 verified_loaded 或 L5。",
        },
        "sessions": rows,
        "guardrails": [
            "Agent Store 只能消费 bootstrap_status、next_action、installation_id 和 device_id 等回显字段。",
            "Agent Store 不得本地推导 active，不得签发 ReporterCredential、IngestionToken 或 DeviceKey。",
            "signature_verified 只表示签名测试事件通过，不构成 verified_loaded 或 L5。",
            "revoked 必须阻断后续签名测试和企业事件接入，只允许展示重新签发建议。",
            "reissued 只能表示 AgentOps 已签发替代 credential，旧 token 仍必须被拒绝。",
            "控制台不展示 token 值、私钥、原始载荷、下载链接、PR 原文或外部 URL。",
        ],
    }


def _credential_handoff_row(
    repository: InMemoryRepository, record: dict[str, Any]
) -> dict[str, Any]:
    session = dict(record["bootstrap_session"])
    bootstrap_id = str(session["bootstrap_id"])
    try:
        status = get_credential_status(repository, bootstrap_id)
    except AgentOpsError:
        status = {
            "schema_version": CREDENTIAL_STATUS_SCHEMA_VERSION,
            "bootstrap_id": bootstrap_id,
            "bootstrap_status": str(
                session.get("bootstrap_status") or session.get("status") or "pending"
            ),
            "credential_status": "pending",
            "credential_id": "待签发",
            "token_id": "待签发",
            "device_key_id": "待签发",
            "installation_id": str(session.get("installation_id") or "待确认"),
            "device_id": str(session.get("device_id") or "待确认"),
            "expires_at": str(session.get("expires_at") or "待确认"),
            "next_action": "issue_credential",
            "signature_test_event_id": None,
            "agentops_fact_owner": "agentops",
            "agent_store_consumer_boundary": "display_only_no_active_inference",
            "verified_loaded": "not_asserted",
            "l5_status": "not_asserted",
        }
    return {
        "id": f"credential_handoff_{_slug(bootstrap_id)}",
        "schema_version": str(status["schema_version"]),
        "bootstrap_id": bootstrap_id,
        "bootstrap_status": str(status["bootstrap_status"]),
        "credential_status": str(status["credential_status"]),
        "credential_id": str(status["credential_id"]),
        "token_id": "已隐藏",
        "device_key_id": str(status["device_key_id"]),
        "installation_id": str(status["installation_id"]),
        "device_id": str(status["device_id"]),
        "expires_at": str(status["expires_at"]),
        "next_action": str(status["next_action"]),
        "signature_test_event_id": str(
            status.get("signature_test_event_id") or "待接收"
        ),
        "revocation_id": str(status.get("revocation_id") or "未撤销"),
        "revoked_at": str(status.get("revoked_at") or "未撤销"),
        "revocation_reason": str(status.get("revocation_reason") or "未撤销"),
        "revocation_scope": str(status.get("revocation_scope") or "未撤销"),
        "revocation_resolution": str(
            status.get("revocation_resolution") or "未重新签发"
        ),
        "reissue_id": str(status.get("reissue_id") or "未重新签发"),
        "reissued_at": str(status.get("reissued_at") or "未重新签发"),
        "reissued_by": str(status.get("reissued_by") or "未重新签发"),
        "reissued_bootstrap_id": str(
            status.get("reissued_bootstrap_id") or "未重新签发"
        ),
        "reissued_credential_id": str(
            status.get("reissued_credential_id") or "未重新签发"
        ),
        "agentops_fact_owner": str(status["agentops_fact_owner"]),
        "agent_store_consumer_boundary": str(status["agent_store_consumer_boundary"]),
        "allowed_actions": "display_status,show_next_action",
        "forbidden_actions": "infer_active,issue_credential,issue_ingestion_token,issue_device_key",
        "verified_loaded": str(status["verified_loaded"]),
        "l5_status": str(status["l5_status"]),
        "display_scope": "只读回显，不包含 token 值、token_id 明文、私钥或原始载荷。",
    }


def _agent_store_workbench(
    repository: InMemoryRepository, events_by_run: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
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
            audit = build_run_audit(
                repository, run_id, events=events, discovery_gaps=raw_gaps
            )
        except Exception:
            audit = _agent_store_failed_audit(run_id, events)
            audits.append(_agent_store_audit(audit))
            summaries.append(
                _agent_store_summary(_agent_store_failed_summary(run_id, audit))
            )
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
        "registryMap": [
            _agent_store_registry_record(record)
            for record in repository.agent_store_metadata_records()
        ],
    }


def _agent_store_run_id(event: dict[str, Any]) -> str:
    payload = _event_payload(event)
    for candidate in (event.get("run_id"), payload.get("run_id")):
        if candidate not in (None, ""):
            return str(candidate)
    return str(event.get("event_id") or "unknown_run")


def _agent_store_evidence_summary(
    run_id: str, events: list[dict[str, Any]]
) -> dict[str, Any]:
    l5_input = _last_payload(events, "l5_eligibility_input")
    evaluation = evaluate_l5_gate(
        events,
        governance_state=_governance_state(events),
        outbox_status=str(l5_input.get("outbox_status", "delivered")),
        policy_state_known=_strict_bool(
            l5_input.get("policy_state_known"), default=False
        ),
    )
    return {
        "run_id": run_id,
        "evidence_level": str(evaluation["evidence_level"]),
        "confidence": _agent_store_confidence(str(evaluation["evidence_level"])),
        "missing_evidence": list(evaluation["missing_evidence"]),
    }


def _agent_store_failed_audit(
    run_id: str, events: list[dict[str, Any]]
) -> dict[str, Any]:
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
        "related_agent_versions": [_agent_version_label(event) for event in events]
        or [f"{agent_id}@{version}"],
        "deep_links": {
            "agent_id": agent_id,
            "version": version,
            "session_id": str(first.get("session_id") or f"sess_{run_id}"),
            "run_id": run_id,
            "installation_id": str(
                first.get("installation_id") or "unknown_installation"
            ),
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
        "related_agent_versions": [
            str(version) for version in audit["related_agent_versions"]
        ],
        "deep_links": {
            str(key): str(value) for key, value in audit["deep_links"].items()
        },
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
            "affected_actions": [
                str(action)
                for action in summary["policy_requirement"]["affected_actions"]
            ],
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


def _localized_gap_type(gap_type: str) -> str:
    labels = {
        "agent_unregistered": "Agent 未注册",
        "skill_unregistered": "Skill 未注册",
    }
    return labels.get(gap_type, "注册事实缺失")


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
                {
                    "label": "今日运行",
                    "value": 42,
                    "status": "healthy",
                    "detail": "39 条可信，3 条需复核",
                },
                {
                    "label": "Policy SLO",
                    "value": "P95 860ms",
                    "status": "degraded",
                    "detail": "高风险动作需在线校验/阻断（require_online/block）",
                },
                {
                    "label": "审批待办",
                    "value": 7,
                    "status": "pending",
                    "detail": "2 条超过 SLA 并已升级",
                },
                {
                    "label": "证据状态",
                    "value": "1 条失败",
                    "status": "redaction_failed",
                    "detail": "原文访问已阻断",
                },
            ],
        },
        "runs": [
            _run(
                "run_20260506_001",
                "发布 Agent",
                "生产部署",
                "高",
                "healthy",
                "approval_required",
                "summary_only",
            ),
            _run(
                "run_20260506_002",
                "质检 Agent",
                "测试执行",
                "中",
                "healthy",
                "conditional_allow",
                "approved_limited",
            ),
            _run(
                "run_20260506_003",
                "迁移 Agent",
                "结构变更",
                "高",
                "degraded",
                "block",
                "redaction_failed",
            ),
            _run(
                "run_20260506_004",
                "商店 Agent",
                "发布上架",
                "低",
                "unknown",
                "warn",
                "summary_only",
            ),
        ],
        "evidence": [
            _evidence(
                "ev_001",
                "run_20260506_001",
                "部署命令摘要已移除敏感值。",
                "sha256:7a21...",
                "summary_only",
                "audit_ev_001",
            ),
            _evidence(
                "ev_002",
                "run_20260506_002",
                "已获得短时复核窗口的限时授权。",
                "sha256:91be...",
                "approved_limited",
                "audit_ev_002",
            ),
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
            _approval(
                "ap_001",
                "发布 Agent",
                "生产部署需要短期 Grant",
                "deploy:prod",
                "2026-05-06 13:20",
                "pending",
                "pending",
            ),
            _approval(
                "ap_002",
                "质检 Agent",
                "复核失败的测试证据",
                "evidence.raw",
                "2026-05-06 12:40",
                "escalated",
                "expired",
            ),
            _approval(
                "ap_003",
                "迁移 Agent",
                "结构迁移被策略阻断",
                "db.migrate",
                "2026-05-06 14:00",
                "approved",
                "active",
            ),
            _approval(
                "ap_004",
                "商店 Agent",
                "已接受发布风险提示",
                "store.publish",
                "2026-05-06 13:10",
                "revoked",
                "revoked",
            ),
        ],
        "policies": [
            _policy(
                "pol_001",
                "approval_required",
                "deploy:prod",
                "require_online",
                "runtime-v2.3",
                "15 分钟",
                "audit_pol_001",
            ),
            _policy(
                "pol_002",
                "block",
                "db.migrate",
                "block",
                "runtime-v2.3",
                "无",
                "audit_pol_002",
            ),
            _policy(
                "pol_003",
                "conditional_allow",
                "test:run",
                "无",
                "runtime-v2.2",
                "10 分钟",
                "audit_pol_003",
            ),
            _policy(
                "pol_004",
                "unknown",
                "store.publish",
                "警告",
                "runtime-v2.1",
                "无",
                "req_policy_unknown",
            ),
        ],
        "risks": [
            _risk(
                "risk_001",
                "策略中心",
                "严重",
                "block",
                "安全/IAM",
                "复核拒绝优先级（deny）",
                "policies",
            ),
            _risk(
                "risk_002",
                "审批中心",
                "高",
                "escalated",
                "发布审批人",
                "升级审批",
                "approvals",
            ),
            _risk(
                "risk_003",
                "证据检索",
                "高",
                "redaction_failed",
                "证据负责人",
                "仅检查哈希",
                "evidence",
            ),
            _risk(
                "risk_004",
                "Ai_AutoSDLC 运行",
                "中",
                "unverified",
                "SDLC 负责人",
                "加载验证证明",
                "sdlc-runs",
            ),
        ],
        "quality": [
            _quality(
                "qs_001",
                "契约测试",
                "healthy",
                "88/88",
                "AO1/AO2/AO3 契约套件",
                "AgentOps 后端",
                "保持基线",
            ),
            _quality(
                "qs_002",
                "Browser Gate",
                "healthy",
                "已通过",
                "AO3 浏览器证据",
                "前端负责人",
                "持续采集",
            ),
            _quality(
                "qs_003",
                "证据完整性",
                "redaction_failed",
                "91%",
                "ev_003 已保留哈希",
                "证据负责人",
                "修复脱敏",
            ),
            _quality(
                "qs_004",
                "策略可解释性",
                "unknown",
                "需证明",
                "策略要求摘要",
                "安全/IAM",
                "刷新 SLO",
            ),
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
        "credentialHandoff": {
            "summary": {
                "id": "credential_handoff_summary",
                "schema_version": CREDENTIAL_STATUS_SCHEMA_VERSION,
                "bootstrap_count": 3,
                "credential_issued": 1,
                "signature_verified": 1,
                "revoked": 1,
                "agentops_fact_owner": "agentops",
                "agent_store_boundary": "display_only_no_active_inference",
                "verified_loaded": "not_asserted",
                "l5_status": "not_asserted",
                "primary_action": "处理撤销并重新签发",
                "safety_note": "凭证联调只展示 AgentOps 事实回显，不把 credential 或签名测试事件提升为 verified_loaded 或 L5。",
            },
            "sessions": [
                {
                    "id": "credential_handoff_boot_inst_fixture",
                    "schema_version": CREDENTIAL_STATUS_SCHEMA_VERSION,
                    "bootstrap_id": "boot-inst-fixture",
                    "bootstrap_status": "credential_issued",
                    "credential_status": "active",
                    "credential_id": "cred-inst-fixture",
                    "token_id": "已隐藏",
                    "device_key_id": "store-device-key-1",
                    "installation_id": "inst-fixture",
                    "device_id": "device-fixture",
                    "expires_at": "2026-05-07T15:00:00Z",
                    "next_action": "send_signature_test_event",
                    "signature_test_event_id": "待接收",
                    "revocation_id": "未撤销",
                    "revoked_at": "未撤销",
                    "revocation_reason": "未撤销",
                    "revocation_scope": "未撤销",
                    "agentops_fact_owner": "agentops",
                    "agent_store_consumer_boundary": "display_only_no_active_inference",
                    "allowed_actions": "display_status,show_next_action",
                    "forbidden_actions": "infer_active,issue_credential,issue_ingestion_token,issue_device_key",
                    "verified_loaded": "not_asserted",
                    "l5_status": "not_asserted",
                    "display_scope": "只读回显，不包含 token 值、token_id 明文、私钥或原始载荷。",
                },
                {
                    "id": "credential_handoff_boot_inst_verified",
                    "schema_version": CREDENTIAL_STATUS_SCHEMA_VERSION,
                    "bootstrap_id": "boot-inst-verified",
                    "bootstrap_status": "signature_verified",
                    "credential_status": "active",
                    "credential_id": "cred-inst-verified",
                    "token_id": "已隐藏",
                    "device_key_id": "store-device-key-2",
                    "installation_id": "inst-verified",
                    "device_id": "device-verified",
                    "expires_at": "2026-05-07T15:00:00Z",
                    "next_action": "display_activation_result",
                    "signature_test_event_id": "evt_signature_test_verified",
                    "revocation_id": "未撤销",
                    "revoked_at": "未撤销",
                    "revocation_reason": "未撤销",
                    "revocation_scope": "未撤销",
                    "agentops_fact_owner": "agentops",
                    "agent_store_consumer_boundary": "display_only_no_active_inference",
                    "allowed_actions": "display_status,show_next_action",
                    "forbidden_actions": "infer_active,issue_credential,issue_ingestion_token,issue_device_key",
                    "verified_loaded": "not_asserted",
                    "l5_status": "not_asserted",
                    "display_scope": "只读回显，不包含 token 值、token_id 明文、私钥或原始载荷。",
                },
                {
                    "id": "credential_handoff_boot_inst_revoked",
                    "schema_version": CREDENTIAL_STATUS_SCHEMA_VERSION,
                    "bootstrap_id": "boot-inst-revoked",
                    "bootstrap_status": "revoked",
                    "credential_status": "revoked",
                    "credential_id": "cred-inst-revoked",
                    "token_id": "已隐藏",
                    "device_key_id": "store-device-key-3",
                    "installation_id": "inst-revoked",
                    "device_id": "device-revoked",
                    "expires_at": "2026-05-07T15:00:00Z",
                    "next_action": "reissue_credential",
                    "signature_test_event_id": "evt_signature_test_revoked",
                    "revocation_id": "revoke-inst-revoked",
                    "revoked_at": "2026-05-07T15:10:00Z",
                    "revocation_reason": "设备遗失",
                    "revocation_scope": "credential_and_device_key",
                    "agentops_fact_owner": "agentops",
                    "agent_store_consumer_boundary": "display_only_no_active_inference",
                    "allowed_actions": "display_status,show_next_action",
                    "forbidden_actions": "infer_active,issue_credential,issue_ingestion_token,issue_device_key",
                    "verified_loaded": "not_asserted",
                    "l5_status": "not_asserted",
                    "display_scope": "只读回显，不包含 token 值、token_id 明文、私钥或原始载荷。",
                },
            ],
            "guardrails": [
                "Agent Store 只能消费 bootstrap_status、next_action、installation_id 和 device_id 等回显字段。",
                "Agent Store 不得本地推导 active，不得签发 ReporterCredential、IngestionToken 或 DeviceKey。",
                "signature_verified 只表示签名测试事件通过，不构成 verified_loaded 或 L5。",
                "revoked 必须阻断后续签名测试和企业事件接入，只允许展示重新签发建议。",
                "控制台不展示 token 值、私钥、原始载荷、下载链接、PR 原文或外部 URL。",
            ],
        },
        "connectors": [
            _connector(
                "conn_agent_store",
                "Agent Store",
                "healthy",
                "2026-05-06 05:20",
                "无",
                "req_conn_agent_store",
            ),
            _connector(
                "conn_git",
                "Git 仓库",
                "healthy",
                "2026-05-06 05:20",
                "无",
                "req_conn_git",
            ),
            _connector(
                "conn_pr", "PR 服务", "healthy", "2026-05-06 05:20", "无", "req_conn_pr"
            ),
            _connector(
                "conn_ci",
                "CI 检查",
                "degraded",
                "2026-05-06 05:17",
                "降级为本地检查摘要",
                "req_conn_ci",
            ),
            _connector(
                "conn_test",
                "测试执行",
                "healthy",
                "2026-05-06 05:20",
                "无",
                "req_conn_test",
            ),
            _connector(
                "conn_sdlc",
                "Ai_AutoSDLC",
                "materialized",
                "2026-05-06 05:20",
                "需要 verified_loaded 证明",
                "req_conn_sdlc",
            ),
            _connector(
                "conn_evidence",
                "证据存储",
                "degraded",
                "2026-05-06 05:18",
                "仅展示摘要",
                "req_conn_evidence",
            ),
            _connector(
                "conn_policy",
                "策略服务",
                "degraded",
                "2026-05-06 05:19",
                "高风险需在线校验/阻断（require_online/block）",
                "req_conn_policy",
            ),
            _connector(
                "conn_iam",
                "IAM/安全",
                "healthy",
                "2026-05-06 05:20",
                "无",
                "req_conn_iam",
            ),
        ],
        "sdlcRuns": [
            _sdlc_run(
                "sdlc_001",
                "ai-sdlc adapter status",
                "materialized",
                "dry_run_passed",
                "AGENTS.md",
                "2026-05-06 05:20",
            ),
            _sdlc_run(
                "sdlc_002",
                "ai-sdlc run --dry-run",
                "materialized",
                "dry_run_passed",
                "CLI 预演",
                "2026-05-06 05:21",
            ),
            _sdlc_run(
                "sdlc_003",
                "governance load probe",
                "materialized",
                "dry_run_passed",
                "待接入治理加载探针",
                "待采集",
            ),
        ],
    }


def _run(
    run_id: str,
    agent: str,
    skill: str,
    risk_level: str,
    l5_state: str,
    policy_state: str,
    evidence_state: str,
) -> dict[str, str]:
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


def _risk(
    risk_id: str,
    source: str,
    severity: str,
    state: str,
    owner_hint: str,
    primary_action: str,
    deep_link: str,
) -> dict[str, str]:
    return {
        "id": risk_id,
        "source": source,
        "severity": severity,
        "state": state,
        "owner_hint": owner_hint,
        "primary_action": primary_action,
        "deep_link": deep_link,
    }


def _quality(
    signal_id: str,
    category: str,
    status: str,
    score: str,
    evidence_ref: str,
    owner_hint: str,
    primary_action: str,
) -> dict[str, str]:
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


def _connector(
    connector_id: str,
    name: str,
    status: str,
    last_seen_at: str,
    degrade_action: str,
    request_id: str,
) -> dict[str, str]:
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
