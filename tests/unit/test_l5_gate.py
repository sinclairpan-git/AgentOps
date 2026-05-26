from agentops.core.l5_gate import evaluate_l5_gate
from tests.contract.conftest import base_event


L5_EVENTS = [
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
]


def complete_events():
    return [base_event(event_type) for event_type in L5_EVENTS]


def test_complete_run_is_l5():
    result = evaluate_l5_gate(complete_events())

    assert result["evidence_level"] == "L5"
    assert result["failed_conditions"] == []


def test_missing_fresh_verification_is_not_l5():
    events = [
        event
        for event in complete_events()
        if event["event_type"] != "verification_result"
    ]

    result = evaluate_l5_gate(events)

    assert result["evidence_level"] == "L4"
    assert "verification_result" in result["missing_evidence"]


def test_adapter_diagnostic_degraded_is_not_a_hard_l5_failure():
    result = evaluate_l5_gate(complete_events(), governance_state="degraded")

    assert result["evidence_level"] == "L5"
    assert "adapter_diagnostic_state" not in result["failed_conditions"]
    assert result["conditions"]["adapter_diagnostic_state"] == "degraded"


def test_missing_executable_task_is_not_l5():
    events = [
        event
        for event in complete_events()
        if event["event_type"] != "executable_task_prepared"
    ]

    result = evaluate_l5_gate(events)

    assert result["evidence_level"] == "L4"
    assert "executable_task_prepared" in result["missing_evidence"]
    assert "executable_task_linked" in result["failed_conditions"]


def test_blocked_task_guard_is_not_l5():
    events = [
        dict(event, payload={**event["payload"], "task_guard_state": "blocked"})
        if event["event_type"] == "code_change_guard_result"
        else event
        for event in complete_events()
    ]

    result = evaluate_l5_gate(events)

    assert result["evidence_level"] == "L4"
    assert "task_guard_allowed" in result["failed_conditions"]


def test_outbox_pending_is_pending_l5_verification():
    result = evaluate_l5_gate(complete_events(), outbox_status="pending")

    assert result["evidence_level"] == "pending"
    assert "outbox_delivered" in result["failed_conditions"]


def test_standalone_or_imported_events_cannot_be_l5():
    events = [
        dict(
            event,
            integration_mode="standalone",
            enterprise_state="not_detected",
            signature=None,
        )
        for event in complete_events()
    ]

    result = evaluate_l5_gate(events)

    assert result["evidence_level"] == "L3"
    assert "enterprise_managed" in result["failed_conditions"]


def test_standalone_or_imported_events_cannot_be_pending_l5():
    events = [
        dict(
            event,
            integration_mode="standalone",
            enterprise_state="not_detected",
            signature=None,
        )
        for event in complete_events()
    ]

    result = evaluate_l5_gate(events, outbox_status="pending")

    assert result["evidence_level"] == "L3"
    assert "enterprise_managed" in result["failed_conditions"]
    assert "outbox_delivered" in result["failed_conditions"]
