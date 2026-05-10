"""P0 end-to-end acceptance gate projection."""

from __future__ import annotations

from typing import Any

from agentops.api.runtime import (
    get_runtime_evidence_summary,
    get_runtime_run_detail,
    get_runtime_trace_timeline,
)
from agentops.api.store_summary import get_agent_store_summary_for_run
from agentops.core.runtime_summary import build_runtime_health_summary
from agentops.storage.repository import InMemoryRepository

REQUIRED_P0_SPAN_KINDS = frozenset({"model", "tool", "guardrail", "artifact"})
SENSITIVE_RAW_KEYS = frozenset(
    {
        "raw_payload",
        "credential_secret",
        "token_secret",
        "device_key",
        "prompt",
    }
)
RAW_LEAK_MARKERS = (
    "raw_payload",
    "credential_secret",
    "token_secret",
    "device_key",
    "prompt",
)


def build_p0_acceptance_gate(
    repository: InMemoryRepository,
    agent_id: str,
    version: str,
    run_id: str,
    *,
    outbox_receipt: dict[str, Any] | None = None,
    policy_decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a read-only P0 governance acceptance result for one runtime run."""

    run_detail = get_runtime_run_detail(repository, run_id)
    timeline = get_runtime_trace_timeline(repository, run_id)
    evidence_summary = get_runtime_evidence_summary(repository, run_id)
    health_summary = build_runtime_health_summary(repository, agent_id, version)
    store_summary = get_agent_store_summary_for_run(
        repository, agent_id, version, run_id
    )

    context = {
        "run_detail": run_detail,
        "timeline": timeline,
        "evidence_summary": evidence_summary,
        "health_summary": health_summary,
        "store_summary": store_summary,
        "outbox_receipt": _outbox_receipt_summary(outbox_receipt),
        "policy_decision": _policy_decision_summary(policy_decision),
        "grant_summary": _grant_summary(repository, agent_id, version, run_id),
    }
    checks = [
        _outbox_check(context["outbox_receipt"]),
        _runtime_run_check(run_detail, agent_id, version),
        _trace_timeline_check(timeline),
        _evidence_summary_check(evidence_summary),
        _health_summary_check(health_summary),
        _policy_decision_check(context["policy_decision"]),
        _grant_check(context["grant_summary"]),
        _guardrail_check(run_detail),
        _sdlc_bridge_check(timeline),
        _store_echo_check(store_summary, run_id),
        _no_raw_leak_check(context),
    ]
    failed = [check for check in checks if check["status"] != "passed"]
    return {
        "schema_version": "p0_acceptance_gate.v1",
        "gate_id": f"p0_acceptance_{run_id}",
        "run_id": run_id,
        "agent_id": agent_id,
        "version": version,
        "gate_status": "passed" if not failed else "failed",
        "required_checks": checks,
        "summary": {
            "passed": len(checks) - len(failed),
            "failed": len(failed),
            "failed_check_ids": [check["check_id"] for check in failed],
        },
        "outbox_receipt": context["outbox_receipt"],
        "run_detail_url": f"/agentops/runtime/runs/{run_id}",
        "store_ops_detail_url": store_summary.get("ops_detail_url", ""),
        "audit_id": f"audit_p0_acceptance_{run_id}",
    }


def _outbox_receipt_summary(receipt: dict[str, Any] | None) -> dict[str, Any]:
    if not receipt:
        return {"state": "missing"}
    return {
        "schema_version": str(receipt.get("schema_version") or ""),
        "batch_id": str(receipt.get("batch_id") or ""),
        "outbox_id": str(receipt.get("outbox_id") or ""),
        "producer": str(receipt.get("producer") or ""),
        "outbox_state": str(receipt.get("outbox_state") or ""),
        "accepted_count": _safe_int(receipt.get("accepted_count")),
        "deduplicated_count": _safe_int(receipt.get("deduplicated_count")),
        "stale_count": _safe_int(receipt.get("stale_count")),
        "rejected_count": _safe_int(receipt.get("rejected_count")),
        "dlq_count": _safe_int(receipt.get("dlq_count")),
        "audit_id": str(receipt.get("audit_id") or ""),
    }


def _policy_decision_summary(decision: dict[str, Any] | None) -> dict[str, Any]:
    if not decision:
        return {"state": "missing"}
    constraints = decision.get("constraints")
    constraints = constraints if isinstance(constraints, dict) else {}
    boundary_declared = "agentops_executes_runtime" in constraints
    return {
        "schema_version": str(decision.get("schema_version") or ""),
        "decision_id": str(decision.get("decision_id") or ""),
        "decision": str(decision.get("decision") or ""),
        "reason_code": str(decision.get("reason_code") or ""),
        "policy_set_version": str(decision.get("policy_set_version") or ""),
        "ttl": _safe_int(decision.get("ttl")),
        "fallback_action": str(decision.get("fallback_action") or ""),
        "audit_id": str(decision.get("audit_id") or ""),
        "agentops_runtime_boundary_declared": boundary_declared,
        "agentops_executes_runtime": constraints.get("agentops_executes_runtime")
        if boundary_declared
        else None,
    }


def _grant_summary(
    repository: InMemoryRepository, agent_id: str, version: str, run_id: str
) -> dict[str, Any]:
    grants = [
        grant
        for grant in repository.grant_records()
        if grant.get("agent_id") == agent_id
        and grant.get("version") == version
        and grant.get("run_id") == run_id
    ]
    if not grants:
        return {"state": "missing"}
    grant = grants[-1]
    consumptions = [
        consumption
        for consumption in repository.grant_consumptions.values()
        if consumption.get("grant_id") == grant.get("grant_id")
    ]
    return {
        "state": "bound",
        "grant_id": str(grant.get("grant_id") or ""),
        "status": str(grant.get("status") or ""),
        "remaining_uses": _safe_int(grant.get("remaining_uses")),
        "consumption_count": len(consumptions),
        "audit_id": str(grant.get("audit_id") or ""),
        "signature_present": bool(str(grant.get("signature") or "").strip()),
    }


def _outbox_check(receipt: dict[str, Any]) -> dict[str, Any]:
    passed = (
        receipt.get("schema_version") == "runtime_outbox_receipt.v1"
        and receipt.get("outbox_state") == "delivered"
        and receipt.get("accepted_count", 0) > 0
        and receipt.get("rejected_count") == 0
        and receipt.get("dlq_count") == 0
        and receipt.get("stale_count") == 0
    )
    return _check(
        "outbox_delivered_without_diagnostics",
        passed,
        "outbox_not_cleanly_delivered",
        receipt.get("audit_id", ""),
    )


def _runtime_run_check(
    run_detail: dict[str, Any], agent_id: str, version: str
) -> dict[str, Any]:
    run = run_detail.get("run") or {}
    passed = (
        run.get("agent_id") == agent_id
        and run.get("version") == version
        and run.get("status") == "succeeded"
    )
    return _check(
        "runtime_run_succeeded",
        passed,
        "runtime_run_not_succeeded",
        run_detail.get("audit_id", ""),
    )


def _trace_timeline_check(timeline: dict[str, Any]) -> dict[str, Any]:
    spans = timeline.get("spans") or []
    span_kinds = {span.get("span_kind") for span in spans}
    passed = (
        bool(spans)
        and not timeline.get("degraded")
        and REQUIRED_P0_SPAN_KINDS.issubset(span_kinds)
    )
    return _check(
        "trace_timeline_complete",
        passed,
        "trace_timeline_incomplete",
        f"audit_runtime_trace_{timeline.get('run_id', 'unknown')}",
    )


def _evidence_summary_check(summary: dict[str, Any]) -> dict[str, Any]:
    passed = (
        summary.get("schema_version") == "evidence_summary.v1"
        and summary.get("evidence_level") == "L5"
        and summary.get("freshness") == "fresh"
        and not summary.get("missing_dimensions")
    )
    return _check(
        "evidence_summary_l5",
        passed,
        str(summary.get("degraded_reason") or "evidence_not_l5"),
        f"audit_runtime_evidence_{summary.get('run_id', 'unknown')}",
    )


def _health_summary_check(summary: dict[str, Any]) -> dict[str, Any]:
    passed = (
        summary.get("schema_version") == "health_summary.v1"
        and summary.get("sample_size", 0) > 0
        and summary.get("recommended_action") == "usable"
    )
    return _check(
        "health_summary_usable",
        passed,
        "health_summary_not_usable",
        f"audit_runtime_health_{summary.get('agent_id', 'unknown')}",
    )


def _policy_decision_check(decision: dict[str, Any]) -> dict[str, Any]:
    passed = (
        decision.get("schema_version") == "policy_decision.v1"
        and decision.get("decision") in {"allow", "warn"}
        and decision.get("ttl", 0) > 0
        and decision.get("agentops_runtime_boundary_declared") is True
        and decision.get("agentops_executes_runtime") is False
    )
    return _check(
        "policy_decision_allows_under_constraints",
        passed,
        "policy_decision_not_acceptable",
        decision.get("audit_id", ""),
    )


def _grant_check(grant: dict[str, Any]) -> dict[str, Any]:
    passed = (
        grant.get("state") == "bound"
        and grant.get("status") == "active"
        and grant.get("signature_present") is True
        and grant.get("consumption_count", 0) > 0
    )
    return _check(
        "capability_grant_bound_and_audited",
        passed,
        "grant_not_bound_or_consumed",
        grant.get("audit_id", ""),
    )


def _guardrail_check(run_detail: dict[str, Any]) -> dict[str, Any]:
    guardrails = run_detail.get("guardrail_summary") or []
    passed = any(
        item.get("status") in {"passed", "warn"}
        or item.get("status_code") in {"ok", "blocked"}
        for item in guardrails
    )
    return _check(
        "guardrail_result_projected",
        passed,
        "guardrail_result_missing",
        run_detail.get("audit_id", ""),
    )


def _sdlc_bridge_check(timeline: dict[str, Any]) -> dict[str, Any]:
    passed = any(
        str(span.get("operation_name") or "").startswith("ai_sdlc.")
        for span in timeline.get("spans") or []
    )
    return _check(
        "ai_sdlc_trace_bridge_present",
        passed,
        "sdlc_trace_bridge_missing",
        f"audit_runtime_trace_{timeline.get('run_id', 'unknown')}",
    )


def _store_echo_check(summary: dict[str, Any], run_id: str) -> dict[str, Any]:
    passed = (
        summary.get("schema_version") == "agentops.agent_store.echo.v1"
        and summary.get("summary_state") == "fresh"
        and summary.get("recommended_action") == "usable"
        and summary.get("deep_links", {}).get("run_id") == run_id
        and summary.get("agentops_fact_owner") == "AgentOps"
    )
    return _check(
        "agent_store_echo_fresh",
        passed,
        "agent_store_echo_not_fresh",
        summary.get("run_audit", {}).get("audit_id", ""),
    )


def _no_raw_leak_check(context: dict[str, Any]) -> dict[str, Any]:
    marker = _find_sensitive_raw_key(context)
    return _check(
        "summary_only_no_raw_leaks",
        not marker,
        f"raw_marker_present:{marker}" if marker else "raw_marker_present",
        "audit_p0_acceptance_raw_leak_scan",
    )


def _check(
    check_id: str, passed: bool, reason_code: str, evidence_ref: str
) -> dict[str, str]:
    return {
        "check_id": check_id,
        "status": "passed" if passed else "failed",
        "reason_code": "ok" if passed else reason_code,
        "evidence_ref": evidence_ref,
    }


def _find_sensitive_raw_key(value: Any) -> str:
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            if key_text in SENSITIVE_RAW_KEYS:
                return key_text
            nested = _find_sensitive_raw_key(item)
            if nested:
                return nested
    if isinstance(value, list | tuple):
        for item in value:
            nested = _find_sensitive_raw_key(item)
            if nested:
                return nested
    return ""


def _safe_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
