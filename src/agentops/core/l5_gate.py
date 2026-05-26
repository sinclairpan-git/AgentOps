"""Run-level L5 Eligibility Gate."""

from __future__ import annotations

from typing import Any


L5_REQUIRED_EVENTS = {
    "stage_started",
    "stage_completed",
    "executable_task_prepared",
    "code_change_guard_result",
    "gate_result",
    "verification_result",
    "violation_scan_completed",
    "artifact_generated",
    "generation_snapshot",
    "l5_eligibility_input",
}


def evaluate_l5_gate(
    events: list[dict[str, Any]],
    *,
    reporter_enabled: bool = True,
    governance_state: str = "verified_loaded",
    identity_confidence: str = "verified",
    outbox_status: str = "delivered",
    policy_state_known: bool = True,
) -> dict[str, Any]:
    event_types = _semantic_event_types(events)
    missing_events = sorted(L5_REQUIRED_EVENTS - event_types)
    enterprise_events = [
        event
        for event in events
        if event.get("integration_mode") == "enterprise_managed"
    ]
    imported_events = [
        event
        for event in events
        if event.get("integration_mode") != "enterprise_managed"
    ]
    signed = all(event.get("signature") for event in enterprise_events)

    failed_conditions: list[str] = []
    missing_evidence: list[str] = []
    result = "L5"
    downgrade_reason = ""

    if not reporter_enabled or not signed:
        failed_conditions.append("source_signed")
        downgrade_reason = "Reporter is disabled or event source is unsigned."
        result = "L3"

    if not enterprise_events or imported_events:
        failed_conditions.append("enterprise_managed")
        downgrade_reason = (
            "Only enterprise_managed signed events can enter AgentOps L5."
        )
        result = "L3"

    if identity_confidence != "verified":
        failed_conditions.append("identity_confidence")
        downgrade_reason = "Identity confidence is not verified."
        result = _min_level(result, "L4")

    if missing_events:
        failed_conditions.append("stage_events_complete")
        missing_evidence.extend(missing_events)
        downgrade_reason = "L5 core event chain is incomplete."
        result = _min_level(result, "L4")

    if "verification_result" not in event_types:
        failed_conditions.append("verification_fresh")
        if "verification_result" not in missing_evidence:
            missing_evidence.append("verification_result")
        downgrade_reason = "Fresh verification is missing."
        result = _min_level(result, "L4")

    executable_task_linked = _executable_task_linked(events, event_types)
    task_guard_allowed = _task_guard_allowed(events, event_types)
    if not executable_task_linked:
        failed_conditions.append("executable_task_linked")
        if "executable_task_prepared" not in missing_evidence:
            missing_evidence.append("executable_task_prepared")
        downgrade_reason = "Executable task evidence is missing."
        result = _min_level(result, "L4")

    if not task_guard_allowed:
        failed_conditions.append("task_guard_allowed")
        if "code_change_guard_result" not in missing_evidence:
            missing_evidence.append("code_change_guard_result")
        downgrade_reason = "Code change task guard is missing or blocked."
        result = _min_level(result, "L4")

    if outbox_status != "delivered":
        failed_conditions.append("outbox_delivered")
        downgrade_reason = "Outbox delivery is pending."
        if "enterprise_managed" not in failed_conditions:
            result = "pending"

    if not policy_state_known:
        failed_conditions.append("policy_state_known")
        downgrade_reason = "High-risk policy state is unknown."
        result = _min_level(result, "L4")

    conditions = {
        "reporter_enabled": reporter_enabled,
        "governance_loaded": governance_state == "verified_loaded",
        "adapter_diagnostic_state": governance_state,
        "schema_valid": True,
        "source_signed": signed,
        "enterprise_managed": bool(enterprise_events) and not imported_events,
        "identity_confidence": identity_confidence == "verified",
        "session_mapping": True,
        "stage_events_complete": not missing_events,
        "verification_fresh": "verification_result" in event_types,
        "executable_task_linked": executable_task_linked,
        "task_guard_allowed": task_guard_allowed,
        "artifact_linked": "artifact_generated" in event_types
        or "generation_snapshot" in event_types,
        "outbox_delivered": outbox_status == "delivered",
        "policy_state_known": policy_state_known,
    }

    return {
        "result": result,
        "evidence_level": result,
        "conditions": conditions,
        "failed_conditions": failed_conditions,
        "missing_evidence": sorted(set(missing_evidence)),
        "downgrade_reason": downgrade_reason,
    }


def _min_level(current: str, candidate: str) -> str:
    order = {"L1": 1, "L2": 2, "L3": 3, "L4": 4, "L5": 5, "pending": 0}
    return candidate if order[candidate] < order[current] else current


def _semantic_event_types(events: list[dict[str, Any]]) -> set[str]:
    event_types: set[str] = set()
    for event in events:
        event_type = str(event.get("event_type") or "")
        if event_type:
            event_types.add(event_type)
        payload = _payload(event)
        sdlc_event_type = str(payload.get("sdlc_event_type") or "")
        status = str(payload.get("status") or "")
        if sdlc_event_type == "executable_task":
            event_types.add("executable_task_prepared")
        elif sdlc_event_type == "code_guard":
            event_types.add("code_change_guard_result")
        elif sdlc_event_type == "gate":
            event_types.add("gate_result")
        elif sdlc_event_type == "verification":
            event_types.add("verification_result")
        elif sdlc_event_type == "artifact":
            event_types.add("artifact_generated")
        elif sdlc_event_type == "violation":
            event_types.add("violation_scan_completed")
        elif sdlc_event_type == "stage":
            if status == "started":
                event_types.add("stage_started")
            else:
                event_types.add("stage_completed")
    return event_types


def _payload(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload")
    return payload if isinstance(payload, dict) else event


def _executable_task_linked(
    events: list[dict[str, Any]], event_types: set[str]
) -> bool:
    return "executable_task_prepared" in event_types


def _task_guard_allowed(events: list[dict[str, Any]], event_types: set[str]) -> bool:
    if "code_change_guard_result" not in event_types:
        return False
    saw_allowed_guard = False
    for event in events:
        payload = _payload(event)
        if (
            event.get("event_type") != "code_change_guard_result"
            and payload.get("sdlc_event_type") != "code_guard"
        ):
            continue
        guard_result = str(payload.get("guard_result") or "")
        task_guard_state = str(payload.get("task_guard_state") or "")
        status = str(payload.get("status") or "")
        if "blocked" in {guard_result, task_guard_state, status}:
            return False
        if (
            guard_result in {"allowed", "passed"}
            or task_guard_state in {"allowed", "passed"}
            or status == "passed"
        ):
            saw_allowed_guard = True
    return saw_allowed_guard
