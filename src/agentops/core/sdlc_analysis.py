"""Ai_AutoSDLC run analysis projections for AgentOps."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from agentops.core.errors import AgentOpsError
from agentops.core.runtime_summary import build_runtime_evidence_summary
from agentops.storage.repository import InMemoryRepository

HEALTH_SCHEMA_VERSION = "agentops_sdlc_run_health_summary.v1"
FINDING_SCHEMA_VERSION = "agentops_sdlc_finding.v1"
FINDINGS_RESPONSE_SCHEMA_VERSION = "agentops_sdlc_findings.v1"
TRENDS_SCHEMA_VERSION = "agentops_sdlc_trends.v1"

FINDING_ORDER = {
    "P0": 0,
    "P1": 1,
    "P2": 2,
    "P3": 3,
}

SUCCESS_STATUS_CODES = {"ok", "unset", ""}
FAILED_STATUS_CODES = {"error", "blocked"}
FAILED_STATUSES = {"failed", "blocked"}


def build_sdlc_run_health_summary(
    repository: InMemoryRepository, run_id: str
) -> dict[str, Any]:
    summaries = _sdlc_run_health_summaries(repository)
    for summary in summaries:
        if summary["run_id"] == run_id:
            return summary
    raise AgentOpsError(
        "RUNTIME_RUN_NOT_FOUND",
        "SDLC run health summary was not found.",
        audit_id=f"audit_sdlc_run_health_{_safe_ref(run_id)}",
        request_id=f"req_sdlc_run_health_{_safe_ref(run_id)}",
    )


def build_sdlc_findings(repository: InMemoryRepository) -> dict[str, Any]:
    summaries = _sdlc_run_health_summaries(repository)
    findings = _sdlc_findings_from_summaries(summaries)
    return {
        "schema_version": FINDINGS_RESPONSE_SCHEMA_VERSION,
        "finding_count": len(findings),
        "findings": findings,
        "summary": {
            "raw_access_state": "summary_only",
            "automatic_fix_performed": False,
            "outbox_replay_performed": False,
            "agentops_role": "observe_and_recommend",
        },
    }


def build_sdlc_trends(repository: InMemoryRepository) -> dict[str, Any]:
    summaries = _sdlc_run_health_summaries(repository)
    findings = _sdlc_findings_from_summaries(summaries)
    return _sdlc_trends_from_summaries(summaries, findings=findings)


def build_sdlc_analysis_snapshot(repository: InMemoryRepository) -> dict[str, Any]:
    summaries = _sdlc_run_health_summaries(repository)
    findings = _sdlc_findings_from_summaries(summaries)
    trends = _sdlc_trends_from_summaries(summaries, findings=findings)
    recommendations = _sdlc_recommendations(summaries, findings, trends)
    latest_real_report = next(
        (
            summary
            for summary in reversed(summaries)
            if summary["run_type"] == "real_run"
        ),
        None,
    )
    return {
        "health_summaries": summaries,
        "findings": findings,
        "trends": trends,
        "recommendations": recommendations,
        "latest_real_report": latest_real_report,
    }


def _sdlc_run_health_summaries(
    repository: InMemoryRepository,
) -> list[dict[str, Any]]:
    spans = [
        span for span in repository.trace_span_records() if span.get("sdlc_event_type")
    ]
    spans_by_run: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for span in spans:
        spans_by_run[str(span.get("run_id") or "unknown_sdlc_run")].append(span)

    receipt_stats = _receipt_stats_by_run(repository, spans_by_run)
    dlq_stats = _dlq_stats_by_run(repository)

    summaries = [
        _sdlc_run_health_summary_for_spans(
            repository,
            run_id,
            run_spans,
            receipt_stats.get(run_id, {}),
            dlq_stats.get(run_id, {}),
        )
        for run_id, run_spans in sorted(
            spans_by_run.items(), key=lambda item: _run_recency_key(item[1])
        )
    ]
    return summaries


def _sdlc_run_health_summary_for_spans(
    repository: InMemoryRepository,
    run_id: str,
    spans: list[dict[str, Any]],
    receipt_stats: dict[str, Any],
    dlq_stats: dict[str, Any],
) -> dict[str, Any]:
    sorted_spans = sorted(spans, key=_span_sort_key)
    failed_spans = [span for span in sorted_spans if _span_failed(span)]
    workitem = _first_non_empty(sorted_spans, "workitem") or "未声明"
    failed_span = failed_spans[0] if failed_spans else {}
    accepted = _safe_int(receipt_stats.get("accepted"))
    deduplicated = _safe_int(receipt_stats.get("deduplicated"))
    rejected = _safe_int(receipt_stats.get("rejected"))
    stale = _safe_int(receipt_stats.get("stale"))
    dlq = _safe_int(receipt_stats.get("dlq")) + _safe_int(dlq_stats.get("dlq"))
    delivered_state = str(receipt_stats.get("delivered_state") or "not_reported")
    evidence = _evidence_for_run(repository, run_id)
    failed_conditions = _failed_conditions(sorted_spans, failed_spans, rejected, dlq)
    retryable = any(bool(span.get("retryable")) for span in failed_spans) or bool(
        receipt_stats.get("retryable") or dlq_stats.get("retryable")
    )
    run_type = _run_type(run_id, workitem, receipt_stats)
    return {
        "schema_version": HEALTH_SCHEMA_VERSION,
        "run_id": run_id,
        "workitem": workitem,
        "run_type": run_type,
        "overall_status": _overall_status(
            failed_span_count=len(failed_spans),
            rejected=rejected,
            dlq=dlq,
            span_count=len(sorted_spans),
            delivered_state=delivered_state,
        ),
        "delivered_state": delivered_state,
        "accepted": accepted,
        "deduplicated": deduplicated,
        "rejected": rejected,
        "stale": stale,
        "dlq": dlq,
        "span_count": len(sorted_spans),
        "failed_span_count": len(failed_spans),
        "failed_stage": str(failed_span.get("stage_name") or ""),
        "failed_operation": str(failed_span.get("operation_name") or ""),
        "failed_conditions": failed_conditions,
        "blocking_reason": _blocking_reason(failed_span, rejected, dlq),
        "retryable": retryable,
        "next_action": _next_action(
            failed_spans=failed_spans,
            failed_conditions=failed_conditions,
            run_type=run_type,
            rejected=rejected,
            dlq=dlq,
        ),
        "evidence_level": str(evidence.get("evidence_level") or "L3"),
        "raw_access_state": "summary_only",
        "latest_event_at": _latest_event_at(sorted_spans),
        "run_classification_reason": _run_classification_reason(run_type),
    }


def _receipt_stats_by_run(
    repository: InMemoryRepository, spans_by_run: dict[str, list[dict[str, Any]]]
) -> dict[str, dict[str, Any]]:
    event_to_run: dict[str, str] = {}
    for run_id, spans in spans_by_run.items():
        for span in spans:
            event_id = str(span.get("event_id") or "")
            if event_id:
                event_to_run[event_id] = run_id

    stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "accepted": 0,
            "deduplicated": 0,
            "rejected": 0,
            "stale": 0,
            "dlq": 0,
            "retryable": False,
            "delivered_state": "not_reported",
            "batch_ids": set(),
            "replay_reasons": set(),
        }
    )
    for receipt in repository.runtime_outbox_receipt_records():
        if str(receipt.get("producer") or "") != "Ai_AutoSDLC":
            continue
        item_results = [
            item for item in receipt.get("item_results", []) if isinstance(item, dict)
        ]
        run_ids = {
            event_to_run[str(item.get("event_id") or "")]
            for item in item_results
            if str(item.get("event_id") or "") in event_to_run
        }
        if not run_ids:
            continue
        for run_id in sorted(run_ids):
            run_items = [
                item
                for item in item_results
                if event_to_run.get(str(item.get("event_id") or "")) == run_id
            ]
            stats[run_id]["accepted"] += sum(
                1 for item in run_items if item.get("status") == "accepted"
            )
            stats[run_id]["deduplicated"] += sum(
                1 for item in run_items if item.get("status") == "deduplicated"
            )
            stats[run_id]["rejected"] += sum(
                1 for item in run_items if item.get("status") == "rejected"
            )
            stats[run_id]["stale"] += sum(
                1 for item in run_items if item.get("status") == "stale_ignored"
            )
            stats[run_id]["dlq"] += sum(
                1 for item in run_items if item.get("status") == "dlq"
            )
            stats[run_id]["retryable"] = stats[run_id]["retryable"] or any(
                bool(item.get("retryable")) for item in run_items
            )
            stats[run_id]["delivered_state"] = _combine_delivered_state(
                str(stats[run_id]["delivered_state"]),
                str(receipt.get("outbox_state") or "not_reported"),
            )
            stats[run_id]["batch_ids"].add(str(receipt.get("batch_id") or ""))
            stats[run_id]["replay_reasons"].add(str(receipt.get("replay_reason") or ""))

    return {
        run_id: {
            **values,
            "batch_ids": sorted(item for item in values["batch_ids"] if item),
            "replay_reasons": sorted(item for item in values["replay_reasons"] if item),
        }
        for run_id, values in stats.items()
    }


def _dlq_stats_by_run(repository: InMemoryRepository) -> dict[str, dict[str, Any]]:
    stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"dlq": 0, "retryable": False}
    )
    for record in repository.runtime_dlq_records():
        run_id = str(record.get("run_id") or "")
        if not run_id:
            continue
        stats[run_id]["dlq"] += 1
        stats[run_id]["retryable"] = stats[run_id]["retryable"] or bool(
            record.get("retryable")
        )
    return stats


def _sdlc_findings_from_summaries(
    summaries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    workitem_counts: dict[str, int] = defaultdict(int)
    for summary in summaries:
        workitem_counts[str(summary.get("workitem") or "未声明")] += 1

    for summary in summaries:
        if summary["rejected"] or summary["dlq"]:
            findings.append(
                _finding(
                    summary,
                    severity="P1",
                    category="reporter_delivery_issue",
                    summary_text="Ai_AutoSDLC 上报存在拒绝或 DLQ 诊断。",
                    recommendation="优先修复 reporter envelope、trace parent 或签名诊断，重新发送摘要事件。",
                )
            )
        if "close_gate_failure" in summary["failed_conditions"]:
            category = (
                "missing_failure_reason"
                if "missing_failure_reason" in summary["failed_conditions"]
                else "close_gate_failure"
            )
            findings.append(
                _finding(
                    summary,
                    severity="P1",
                    category=category,
                    summary_text="close gate 失败需要输出可执行失败结论。",
                    recommendation="让 Ai_AutoSDLC 在 close gate failure 中稳定输出 blocking_reason、diagnostic code 和下一步修复建议。",
                )
            )
        elif "missing_failure_reason" in summary["failed_conditions"]:
            findings.append(
                _finding(
                    summary,
                    severity="P2",
                    category="missing_failure_reason",
                    summary_text="失败 span 缺少明确失败原因。",
                    recommendation="在失败事件中补齐 summary 级 blocking_reason 或 diagnostic code，避免 Ops 只能看到 failed。",
                )
            )
        if "task_guard_blocked" in summary["failed_conditions"]:
            findings.append(
                _finding(
                    summary,
                    severity="P1",
                    category="task_guard_blocked",
                    summary_text="任务守卫阻断了自迭代执行。",
                    recommendation="把阻断原因映射为可执行任务范围、变更路径类别和安全摘要级建议。",
                )
            )
        if "missing_executable_task" in summary["failed_conditions"]:
            findings.append(
                _finding(
                    summary,
                    severity="P2",
                    category="missing_executable_task",
                    summary_text="运行缺少 executable_task 摘要事件。",
                    recommendation="在每个真实 run 开始执行前先上报 executable_task，并绑定 workitem 与 task id。",
                )
            )
        if "stage_coverage_gap" in summary["failed_conditions"]:
            findings.append(
                _finding(
                    summary,
                    severity="P3",
                    category="stage_coverage_gap",
                    summary_text="运行缺少 close gate、verification 或 artifact 覆盖。",
                    recommendation="补齐 close gate、verification 和 artifact 摘要事件，便于 Ops 判断自迭代是否完整闭环。",
                )
            )
        if summary["evidence_level"] not in {"L5"}:
            findings.append(
                _finding(
                    summary,
                    severity="P3",
                    category="insufficient_evidence",
                    summary_text="当前运行证据等级不足以作为强健康样本。",
                    recommendation="补齐缺失 span 维度并保持 summary_only raw access 边界。",
                )
            )
        if (
            workitem_counts[str(summary.get("workitem") or "未声明")] > 1
            and summary["overall_status"] != "succeeded"
        ):
            findings.append(
                _finding(
                    summary,
                    severity="P2",
                    category="repeated_retry",
                    summary_text="同一 workitem 出现重复尝试且存在失败样本。",
                    recommendation="聚合失败诊断，避免 dry_run_retry 和 real_run 混为同一健康结论。",
                )
            )
    return sorted(
        _deduplicate_findings(findings),
        key=lambda item: (
            FINDING_ORDER.get(str(item.get("severity")), 9),
            str(item.get("created_at") or ""),
            str(item.get("finding_id") or ""),
        ),
    )


def _finding(
    summary: dict[str, Any],
    *,
    severity: str,
    category: str,
    summary_text: str,
    recommendation: str,
) -> dict[str, Any]:
    finding_id = _finding_id(summary["run_id"], category)
    return {
        "schema_version": FINDING_SCHEMA_VERSION,
        "finding_id": finding_id,
        "severity": severity,
        "category": category,
        "run_id": str(summary["run_id"]),
        "workitem": str(summary.get("workitem") or "未声明"),
        "summary": summary_text,
        "evidence_summary": _finding_evidence_summary(summary),
        "recommendation": recommendation,
        "created_at": str(
            summary.get("latest_event_at") or datetime.now(UTC).isoformat()
        ),
    }


def _deduplicate_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[tuple[str, str], dict[str, Any]] = {}
    for finding in findings:
        key = (str(finding["run_id"]), str(finding["category"]))
        if key not in deduped:
            deduped[key] = finding
    return list(deduped.values())


def _sdlc_trends_from_summaries(
    summaries: list[dict[str, Any]], *, findings: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "schema_version": TRENDS_SCHEMA_VERSION,
        "summary": _trend_entry("all", summaries, findings),
        "by_workitem": _trend_entries("workitem", summaries, findings),
        "by_stage": _trend_entries("failed_stage", summaries, findings, alias="stage"),
        "by_run_type": _trend_entries("run_type", summaries, findings),
        "raw_access_state": "summary_only",
        "automatic_fix_performed": False,
        "outbox_replay_performed": False,
    }


def _trend_entries(
    key_name: str,
    summaries: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    *,
    alias: str | None = None,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for summary in summaries:
        key = str(summary.get(key_name) or "none")
        grouped[key].append(summary)
    return [
        _trend_entry(key, grouped[key], findings, label_name=alias or key_name)
        for key in sorted(grouped)
    ]


def _trend_entry(
    key: str,
    summaries: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    *,
    label_name: str = "scope",
) -> dict[str, Any]:
    run_count = len(summaries)
    failed_count = sum(1 for item in summaries if item["overall_status"] != "succeeded")
    execute_failures = sum(
        1
        for item in summaries
        if item["failed_stage"] == "execute" and item["failed_span_count"]
    )
    close_failures = sum(
        1
        for item in summaries
        if item["failed_stage"] == "close" and item["failed_span_count"]
    )
    finding_counts = _finding_counts_for_summaries(summaries, findings)
    entry = {
        label_name: key,
        "run_count": run_count,
        "success_count": sum(
            1 for item in summaries if item["overall_status"] == "succeeded"
        ),
        "failed_count": failed_count,
        "close_failure_rate": _ratio(close_failures, run_count),
        "execute_failure_rate": _ratio(execute_failures, run_count),
        "task_guard_blocked_count": finding_counts.get("task_guard_blocked", 0),
        "missing_executable_task_count": finding_counts.get(
            "missing_executable_task", 0
        ),
        "rejected_count": sum(_safe_int(item.get("rejected")) for item in summaries),
        "dlq_count": sum(_safe_int(item.get("dlq")) for item in summaries),
        "average_span_count": _average(
            _safe_int(item.get("span_count")) for item in summaries
        ),
        "average_retry_count": _average_retry_count(summaries),
        "latest_failure_at": _latest_failure_at(summaries),
    }
    if label_name != "scope" and label_name not in entry:
        entry[label_name] = key
    return entry


def _finding_counts_for_summaries(
    summaries: list[dict[str, Any]], findings: list[dict[str, Any]]
) -> dict[str, int]:
    run_ids = {str(summary["run_id"]) for summary in summaries}
    counts: dict[str, int] = defaultdict(int)
    for finding in findings:
        if str(finding.get("run_id")) in run_ids:
            counts[str(finding.get("category"))] += 1
    return counts


def _sdlc_recommendations(
    summaries: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    trends: dict[str, Any],
) -> list[str]:
    recommendations = [
        "保持 AgentOps 只读观测边界：输出 finding、趋势和建议，不执行 outbox replay、不自动修复、不写回 SDLC。",
    ]
    categories = {str(finding.get("category")) for finding in findings}
    if "missing_failure_reason" in categories or "close_gate_failure" in categories:
        recommendations.append(
            "在 Ai_AutoSDLC 关闭门禁或验证失败事件中补齐摘要级 blocking_reason、diagnostic code 和 retryable，避免 Ops 只能看到 failed。"
        )
    if "missing_executable_task" in categories:
        recommendations.append(
            "把 executable_task 作为真实运行的前置上报，稳定包含 workitem、task id、任务标题和摘要证据引用。"
        )
    if "stage_coverage_gap" in categories:
        recommendations.append(
            "把关闭门禁、验证和 artifact 纳入每个真实自迭代运行的覆盖基线，并与 run_type 分开聚合。"
        )
    if "reporter_delivery_issue" in categories:
        recommendations.append(
            "对 rejected / DLQ 按 diagnostic code 建立 reporter 修复队列，先修 envelope、parent span 和签名摘要问题。"
        )
    real_run_count = sum(1 for item in summaries if item["run_type"] == "real_run")
    if real_run_count:
        recommendations.append(
            "趋势分析必须按 real_run、readiness_fixture、live_smoke、dry_run_retry 分桶，真实自迭代运行不与预演或探活样本混算。"
        )
    if trends.get("summary", {}).get("failed_count", 0) == 0 and summaries:
        recommendations.append(
            "保留最新真实运行的 delivered / accepted / failed_span_count=0 作为健康基线，后续失败与该基线对比。"
        )
    return recommendations


def _failed_conditions(
    spans: list[dict[str, Any]],
    failed_spans: list[dict[str, Any]],
    rejected: int,
    dlq: int,
) -> list[str]:
    conditions: list[str] = []
    event_types = {str(span.get("sdlc_event_type") or "") for span in spans}
    if "executable_task" not in event_types:
        conditions.append("missing_executable_task")
    if failed_spans:
        for span in failed_spans:
            event_type = str(span.get("sdlc_event_type") or "")
            stage = str(span.get("stage_name") or "")
            error_code = str(span.get("error_code") or "")
            blocking_reason = str(span.get("blocking_reason") or "")
            if event_type == "gate" and stage == "close":
                conditions.append("close_gate_failure")
            if event_type == "code_guard" and error_code == "TASK_GUARD_BLOCKED":
                conditions.append("task_guard_blocked")
            if not error_code and not blocking_reason:
                conditions.append("missing_failure_reason")
    required_event_types = {"gate", "verification", "artifact"}
    if spans and not required_event_types.issubset(event_types):
        conditions.append("stage_coverage_gap")
    if rejected:
        conditions.append("rejected_events")
    if dlq:
        conditions.append("dlq_events")
    return sorted(set(conditions))


def _overall_status(
    *,
    failed_span_count: int,
    rejected: int,
    dlq: int,
    span_count: int,
    delivered_state: str,
) -> str:
    if rejected or dlq:
        return "degraded"
    if failed_span_count:
        return "failed"
    if span_count and delivered_state in {"delivered", "replayed", "not_reported"}:
        return "succeeded"
    if span_count:
        return "degraded"
    return "unknown"


def _next_action(
    *,
    failed_spans: list[dict[str, Any]],
    failed_conditions: list[str],
    run_type: str,
    rejected: int,
    dlq: int,
) -> str:
    if rejected or dlq:
        return "先处理 reporter delivery 诊断，再重新采集 summary-only 上报。"
    if "missing_failure_reason" in failed_conditions:
        return "要求 SDLC 失败事件补齐 blocking_reason 或 diagnostic code。"
    if "close_gate_failure" in failed_conditions:
        return "复核 close gate 摘要结论，并让 SDLC 输出可执行修复建议。"
    if "task_guard_blocked" in failed_conditions:
        return "回到 SDLC 可执行任务范围，修复任务守卫阻断原因。"
    if "missing_executable_task" in failed_conditions:
        return "补齐 executable_task 摘要事件后再评估运行健康。"
    if failed_spans:
        return "复核失败 span 的 stage、operation 和 diagnostic code。"
    if run_type == "real_run":
        return "保持观测；将该真实自迭代 run 作为健康基线样本。"
    return "按上报类型标签单独聚合，不与真实自迭代 run 混算。"


def _blocking_reason(failed_span: dict[str, Any], rejected: int, dlq: int) -> str:
    if failed_span:
        return str(
            failed_span.get("blocking_reason")
            or failed_span.get("error_code")
            or "missing_failure_reason"
        )
    if rejected:
        return "reporter_event_rejected"
    if dlq:
        return "reporter_event_dlq"
    return ""


def _evidence_for_run(repository: InMemoryRepository, run_id: str) -> dict[str, Any]:
    try:
        return build_runtime_evidence_summary(repository, run_id)
    except AgentOpsError:
        return {"evidence_level": "L3", "raw_access_state": "summary_only"}


def _run_type(run_id: str, workitem: str, receipt_stats: dict[str, Any]) -> str:
    text = " ".join(
        [
            run_id,
            workitem,
            " ".join(receipt_stats.get("batch_ids", [])),
            " ".join(receipt_stats.get("replay_reasons", [])),
        ]
    ).lower()
    if "readiness" in text or "fixture" in text:
        return "readiness_fixture"
    if "live_smoke" in text or "smoke" in text:
        return "live_smoke"
    if "dry_run" in text or "dry-run" in text or "retry" in text:
        return "dry_run_retry"
    return "real_run"


def _run_classification_reason(run_type: str) -> str:
    return {
        "real_run": "未命中 readiness、smoke、dry-run 或 retry 标记，按真实自迭代运行聚合。",
        "dry_run_retry": "run_id、workitem、batch 或 replay_reason 含 dry-run/retry 标记。",
        "readiness_fixture": "run_id、workitem 或 batch 含 readiness/fixture 标记。",
        "live_smoke": "run_id、workitem 或 batch 含 smoke 标记。",
    }.get(run_type, "按 summary 标记分类。")


def _span_failed(span: dict[str, Any]) -> bool:
    return (
        str(span.get("status_code") or "") in FAILED_STATUS_CODES
        or str(span.get("status") or "") in FAILED_STATUSES
    )


def _combine_delivered_state(current: str, incoming: str) -> str:
    priority = {
        "rejected": 4,
        "delivered_with_diagnostics": 3,
        "replayed": 2,
        "delivered": 1,
        "not_reported": 0,
    }
    return incoming if priority.get(incoming, 2) > priority.get(current, 2) else current


def _finding_evidence_summary(summary: dict[str, Any]) -> str:
    failed_conditions = ",".join(summary.get("failed_conditions") or []) or "none"
    return (
        f"run={_safe_ref(summary.get('run_id'))}; "
        f"type={summary.get('run_type')}; "
        f"stage={summary.get('failed_stage') or 'none'}; "
        f"operation={summary.get('failed_operation') or 'none'}; "
        f"accepted={summary.get('accepted')}; rejected={summary.get('rejected')}; "
        f"dlq={summary.get('dlq')}; failed_spans={summary.get('failed_span_count')}; "
        f"conditions={failed_conditions}; raw_access=summary_only"
    )


def _finding_id(run_id: str, category: str) -> str:
    digest = hashlib.sha256(f"{run_id}\0{category}".encode("utf-8")).hexdigest()[:16]
    return f"sdlc_finding_{category}_{digest}"


def _first_non_empty(spans: list[dict[str, Any]], field_name: str) -> str:
    for span in spans:
        value = str(span.get(field_name) or "")
        if value:
            return value
    return ""


def _span_sort_key(span: dict[str, Any]) -> tuple[str, float, str]:
    return (
        str(span.get("start_time") or ""),
        _safe_float(span.get("sequence_no")),
        str(span.get("span_id") or ""),
    )


def _run_recency_key(spans: list[dict[str, Any]]) -> tuple[str, str]:
    return (_latest_event_at(spans), str(spans[0].get("run_id") if spans else ""))


def _latest_event_at(spans: list[dict[str, Any]]) -> str:
    values = [
        str(
            span.get("end_time")
            or span.get("start_time")
            or span.get("received_at")
            or ""
        )
        for span in spans
    ]
    return sorted(values)[-1] if values else ""


def _latest_failure_at(summaries: list[dict[str, Any]]) -> str:
    values = [
        str(item.get("latest_event_at") or "")
        for item in summaries
        if item.get("overall_status") != "succeeded"
    ]
    return sorted(values)[-1] if values else ""


def _average(values: Any) -> float:
    value_list = [float(value) for value in values]
    if not value_list:
        return 0.0
    return round(sum(value_list) / len(value_list), 4)


def _average_retry_count(summaries: list[dict[str, Any]]) -> float:
    workitems: dict[str, int] = defaultdict(int)
    for summary in summaries:
        workitems[str(summary.get("workitem") or "未声明")] += 1
    retry_counts = [
        max(0, workitems[str(summary.get("workitem") or "未声明")] - 1)
        for summary in summaries
    ]
    return _average(retry_counts)


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_ref(value: Any) -> str:
    return str(value or "").replace("://", "_").replace("/", "_").replace(" ", "_")
