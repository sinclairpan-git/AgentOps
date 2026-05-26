import json
from pathlib import Path

from agentops.api.console_snapshot import build_console_snapshot
from agentops.api.runtime import ingest_runtime_events
from agentops.core.l5_gate import evaluate_l5_gate
from agentops.core.runtime_contracts import get_contract
from agentops.storage.repository import InMemoryRepository
from tests.contract.conftest import base_event


FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "contracts"
    / "cross-project"
    / "fixtures"
    / "ai_sdlc_executable_task_runtime_batch.v1.json"
)


def _fixture_batch() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_ao56_ct_001_contract_registry_accepts_executable_task_runtime_events():
    sdlc = get_contract("sdlc_trace_event.v1")
    envelope = get_contract("event_envelope.v1")

    assert {"executable_task", "code_guard"}.issubset(
        sdlc.enum_fields["sdlc_event_type"]
    )
    assert {
        "workitem",
        "executable_task_id",
        "task_guard_state",
        "adapter_diagnostic_state",
    }.issubset(sdlc.optional_fields)
    assert {"signed_producer", "verified_runtime"}.issubset(
        envelope.enum_fields["source_trust"]
    )


def test_ao56_ct_002_fixture_ingests_task_and_guard_as_summary_only_trace_spans():
    repository = InMemoryRepository()

    receipt = ingest_runtime_events(_fixture_batch(), repository)

    assert receipt["schema_version"] == "runtime_outbox_receipt.v1"
    assert receipt["producer"] == "Ai_AutoSDLC"
    assert receipt["accepted_count"] == 2
    assert receipt["rejected_count"] == 0
    assert receipt["dlq_count"] == 0
    spans = repository.trace_span_records_for_run("run_sdlc_001")
    assert [span["operation_name"] for span in spans] == [
        "ai_sdlc.executable_task.execute",
        "ai_sdlc.code_guard.execute",
    ]
    assert spans[0]["span_kind"] == "system"
    assert spans[1]["span_kind"] == "guardrail"
    assert spans[1]["guardrail_result_refs"] == ["guard_result:allowed"]
    assert "payload" not in spans[0]
    assert "allowed_paths" not in spans[0]


def test_ao56_ct_003_l5_uses_task_guard_not_verified_loaded_as_main_path():
    complete_events = [
        base_event(event_type)
        for event_type in [
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
    ]

    l5 = evaluate_l5_gate(complete_events, governance_state="materialized")
    assert l5["evidence_level"] == "L5"
    assert "governance_loaded" not in l5["failed_conditions"]

    without_task = [
        event
        for event in complete_events
        if event["event_type"] != "executable_task_prepared"
    ]
    blocked_guard = [
        dict(event, payload={**event["payload"], "guard_result": "blocked"})
        if event["event_type"] == "code_change_guard_result"
        else event
        for event in complete_events
    ]

    assert evaluate_l5_gate(without_task)["evidence_level"] == "L4"
    blocked = evaluate_l5_gate(blocked_guard)
    assert blocked["evidence_level"] == "L4"
    assert "task_guard_allowed" in blocked["failed_conditions"]


def test_ao56_ct_004_console_workbench_exposes_task_guard_receipt_and_diagnostics():
    repository = InMemoryRepository()
    receipt = ingest_runtime_events(_fixture_batch(), repository)

    snapshot = build_console_snapshot(repository=repository)
    workbench = snapshot["consoleData"]["sdlcRunWorkbench"]

    assert workbench["summary"]["verified_loaded_semantics"] == "diagnostic_only"
    assert workbench["taskGuard"][0]["run_id"] == "run_sdlc_001"
    assert workbench["taskGuard"][0]["task_guard_state"] == "allowed"
    assert workbench["taskGuard"][0]["executable_task_id"] == "T56-2.2"
    assert workbench["outboxReceipts"][0]["outbox_id"] == receipt["outbox_id"]
    assert workbench["outboxReceipts"][0]["accepted_count"] == "2"
    assert workbench["evidenceReadiness"][0]["raw_payload_state"] == "summary_only"
    assert workbench["adapterDiagnostics"][0]["hard_gate"] == "false"
