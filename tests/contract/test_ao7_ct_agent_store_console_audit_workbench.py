from __future__ import annotations

import agentops.api.console_snapshot as console_snapshot_api
import agentops.core.agent_store as agent_store_core
from agentops.api.agent_store import sync_agent_store_metadata
from agentops.api.console_snapshot import build_console_snapshot
from agentops.storage.repository import InMemoryRepository
from tests.contract.conftest import base_event


def test_ao7_ct_001_console_snapshot_declares_agent_store_audit_route_and_domain():
    repository = InMemoryRepository()
    repository.write_event(
        base_event("stage_started", agent_id="agent.unknown", agent_version="0.1.0")
    )

    snapshot = build_console_snapshot(repository=repository)

    assert any(
        route["id"] == "agent-store-audit" and route["label"] == "Agent Store 审计"
        for route in snapshot["routes"]
    )
    assert set(snapshot["consoleData"]["agentStore"]) == {
        "discoveryGaps",
        "runAudits",
        "storeSummaries",
        "registryMap",
    }
    assert "raw_payload" not in str(snapshot)


def test_ao7_ct_002_discovery_gaps_are_visible_without_raw_payload():
    repository = InMemoryRepository()
    repository.write_event(
        base_event("stage_started", agent_id="agent.unknown", agent_version="0.1.0")
    )

    console_data = build_console_snapshot(repository=repository)["consoleData"]
    agent_store = console_data["agentStore"]

    assert agent_store["discoveryGaps"][0]["gap_id"] == "gap_agent_agent_unknown_0_1_0"
    assert agent_store["discoveryGaps"][0]["state"] == "suspected"
    assert agent_store["discoveryGaps"][0]["owner_hint"] == "Agent 负责人"
    assert agent_store["discoveryGaps"][0]["affected_runs"] == ["run_1"]
    agent_store_risk = next(
        risk for risk in console_data["risks"] if risk["source"] == "Agent Store"
    )
    assert agent_store_risk["deep_link"] == "agent-store-audit"
    assert "raw_payload" not in str(agent_store["discoveryGaps"])


def test_ao7_ct_003_run_audit_workbench_keeps_deep_links_and_related_versions():
    repository = InMemoryRepository()
    sync_agent_store_metadata(
        repository,
        {
            "agent_id": "agent.ai-sdlc",
            "version": "1.0.0",
            "skills": [{"skill_id": "refine"}],
        },
    )
    repository.write_event(base_event("stage_started"))
    repository.write_event(
        base_event(
            "stage_started",
            event_id="evt_stage_started_v2",
            idempotency_key="stage_started_v2:run_1",
            sequence_no=2,
            agent_version="2.0.0",
        )
    )

    audit = build_console_snapshot(repository=repository)["consoleData"]["agentStore"][
        "runAudits"
    ][0]

    assert audit["registration_state"] == "suspected"
    assert audit["discovery_gap_ids"] == ["gap_agent_agent_ai_sdlc_2_0_0"]
    assert audit["related_agent_versions"] == [
        "agent.ai-sdlc@1.0.0",
        "agent.ai-sdlc@2.0.0",
    ]
    assert (
        audit["deep_links"]["return_url"]
        == "/agent-store/agents/agent.ai-sdlc/runs/run_1"
    )
    assert audit["raw_access_state"] == "summary_only"


def test_ao7_ct_003a_run_audit_uses_agent_store_run_id_fallback():
    repository = InMemoryRepository()
    payload = base_event("stage_started")["payload"]
    payload.pop("run_id")
    repository.write_event(
        base_event(
            "stage_started",
            event_id="evt_without_run_id",
            idempotency_key="stage_started:without_run_id",
            run_id="",
            payload=payload,
        )
    )

    audit = build_console_snapshot(repository=repository)["consoleData"]["agentStore"][
        "runAudits"
    ][0]

    assert audit["run_id"] == "evt_without_run_id"
    assert (
        audit["deep_links"]["return_url"]
        == "/agent-store/agents/agent.ai-sdlc/runs/evt_without_run_id"
    )


def test_ao7_ct_004_store_summary_workbench_contains_policy_requirement_and_validity():
    repository = InMemoryRepository()
    sync_agent_store_metadata(
        repository,
        {
            "agent_id": "agent.ai-sdlc",
            "version": "1.0.0",
            "skills": [{"skill_id": "design"}],
        },
    )
    repository.write_event(base_event("stage_started"))

    summary = build_console_snapshot(repository=repository)["consoleData"][
        "agentStore"
    ]["storeSummaries"][0]

    assert summary["registry_fact_owner"] == "Agent Store"
    assert summary["risk_state"] == "warning"
    assert summary["policy_requirement"]["policy_owner"] == "安全/IAM"
    assert summary["policy_requirement"]["affected_actions"] == [
        "运行审计",
        "高风险 Skill 调用",
    ]
    assert summary["discovery_gap_ids"] == ["gap_skill_agent_ai_sdlc_1_0_0_refine"]
    assert summary["calculated_at"]
    assert summary["valid_until"]


def test_ao7_ct_004a_store_summary_reuses_l5_gate_event_contract():
    repository = InMemoryRepository()
    sync_agent_store_metadata(
        repository,
        {
            "agent_id": "agent.ai-sdlc",
            "version": "1.0.0",
            "skills": [{"skill_id": "refine"}],
        },
    )
    for index, event_type in enumerate(
        [
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
        ],
        start=1,
    ):
        repository.write_event(base_event(event_type, sequence_no=index))

    summary = build_console_snapshot(repository=repository)["consoleData"][
        "agentStore"
    ]["storeSummaries"][0]

    assert summary["evidence_level"] == "L5"
    assert summary["confidence"] == 1.0
    assert summary["missing_evidence"] == []
    assert summary["risk_state"] == "normal"


def test_ao7_ct_004b_store_summary_sorts_events_before_l5_evaluation():
    repository = InMemoryRepository()
    sync_agent_store_metadata(
        repository,
        {
            "agent_id": "agent.ai-sdlc",
            "version": "1.0.0",
            "skills": [{"skill_id": "refine"}],
        },
    )
    stale_payload = base_event("l5_eligibility_input")["payload"]
    stale_payload["policy_state_known"] = False
    repository.write_event(
        base_event(
            "l5_eligibility_input",
            event_id="evt_l5_eligibility_input_late",
            idempotency_key="l5_eligibility_input:run_1:late",
            sequence_no=11,
            payload=stale_payload,
        )
    )
    for index, event_type in enumerate(
        [
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
        ],
        start=1,
    ):
        repository.write_event(base_event(event_type, sequence_no=index))

    summary = build_console_snapshot(repository=repository)["consoleData"][
        "agentStore"
    ]["storeSummaries"][0]

    assert summary["evidence_level"] == "L4"
    assert summary["confidence"] == 0.8
    assert summary["risk_state"] == "warning"


def test_ao7_ct_004c_store_summary_reuses_precomputed_agent_store_audit_context(
    monkeypatch,
):
    repository = InMemoryRepository()
    sync_agent_store_metadata(
        repository,
        {
            "agent_id": "agent.ai-sdlc",
            "version": "1.0.0",
            "skills": [{"skill_id": "refine"}],
        },
    )
    repository.write_event(base_event("stage_started"))
    original_discover = console_snapshot_api.discover_agent_store_gaps
    discover_calls = 0

    def counted_discover(repository):
        nonlocal discover_calls
        discover_calls += 1
        return original_discover(repository)

    def unexpected_core_discover(repository):
        raise AssertionError("console snapshot must reuse precomputed Agent Store gaps")

    monkeypatch.setattr(
        console_snapshot_api, "discover_agent_store_gaps", counted_discover
    )
    monkeypatch.setattr(
        agent_store_core, "discover_agent_store_gaps", unexpected_core_discover
    )

    snapshot = console_snapshot_api.build_console_snapshot(repository=repository)

    assert snapshot["consoleData"]["agentStore"]["runAudits"][0]["run_id"] == "run_1"
    assert discover_calls <= 2


def test_ao7_ct_004d_audit_generation_failure_surfaces_degraded_record(monkeypatch):
    repository = InMemoryRepository()
    repository.write_event(base_event("stage_started"))

    def failing_audit(*args, **kwargs):
        raise RuntimeError("unexpected audit failure")

    monkeypatch.setattr(console_snapshot_api, "build_run_audit", failing_audit)

    agent_store = console_snapshot_api.build_console_snapshot(repository=repository)[
        "consoleData"
    ]["agentStore"]

    assert agent_store["runAudits"][0]["run_id"] == "run_1"
    assert agent_store["runAudits"][0]["registration_state"] == "degraded"
    assert agent_store["runAudits"][0]["processing_error"] == "Agent Store 审计生成失败"
    assert agent_store["storeSummaries"][0]["risk_state"] == "warning"
    assert agent_store["storeSummaries"][0]["missing_evidence"] == ["agent_store_audit"]


def test_ao7_ct_004e_summary_generation_failure_surfaces_degraded_summary(monkeypatch):
    repository = InMemoryRepository()
    sync_agent_store_metadata(
        repository,
        {
            "agent_id": "agent.ai-sdlc",
            "version": "1.0.0",
            "skills": [{"skill_id": "refine"}],
        },
    )
    repository.write_event(base_event("stage_started"))

    def failing_summary(*args, **kwargs):
        raise RuntimeError("unexpected summary failure")

    monkeypatch.setattr(
        console_snapshot_api, "build_agent_store_echo_summary", failing_summary
    )

    agent_store = console_snapshot_api.build_console_snapshot(repository=repository)[
        "consoleData"
    ]["agentStore"]

    assert agent_store["runAudits"][0]["registration_state"] == "governed"
    assert (
        agent_store["storeSummaries"][0]["run_audit"]["registration_state"]
        == "degraded"
    )
    assert (
        agent_store["storeSummaries"][0]["processing_error"]
        == "运行 run_1 的 Agent Store 回显摘要生成失败"
    )


def test_ao7_ct_005_registry_map_is_read_only_agent_store_metadata():
    repository = InMemoryRepository()
    sync_agent_store_metadata(
        repository,
        {
            "agent_id": "agent.ai-sdlc",
            "version": "1.0.0",
            "skills": [{"skill_id": "refine"}, {"skill_id": "design"}],
        },
    )

    registry_record = build_console_snapshot(repository=repository)["consoleData"][
        "agentStore"
    ]["registryMap"][0]

    assert registry_record["agent_id"] == "agent.ai-sdlc"
    assert registry_record["version"] == "1.0.0"
    assert registry_record["metadata_state"] == "consumed"
    assert registry_record["fact_owner"] == "Agent Store"
    assert registry_record["skill_count"] == 2
