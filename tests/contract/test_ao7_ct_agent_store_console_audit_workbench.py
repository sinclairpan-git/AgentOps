from __future__ import annotations

from agentops.api.agent_store import sync_agent_store_metadata
from agentops.api.console_snapshot import build_console_snapshot
from agentops.storage.repository import InMemoryRepository
from tests.contract.conftest import base_event


def test_ao7_ct_001_console_snapshot_declares_agent_store_audit_route_and_domain():
    repository = InMemoryRepository()
    repository.write_event(base_event("stage_started", agent_id="agent.unknown", agent_version="0.1.0"))

    snapshot = build_console_snapshot(repository=repository)

    assert any(route["id"] == "agent-store-audit" and route["label"] == "Agent Store 审计" for route in snapshot["routes"])
    assert set(snapshot["consoleData"]["agentStore"]) == {
        "discoveryGaps",
        "runAudits",
        "storeSummaries",
        "registryMap",
    }
    assert "raw_payload" not in str(snapshot)


def test_ao7_ct_002_discovery_gaps_are_visible_without_raw_payload():
    repository = InMemoryRepository()
    repository.write_event(base_event("stage_started", agent_id="agent.unknown", agent_version="0.1.0"))

    agent_store = build_console_snapshot(repository=repository)["consoleData"]["agentStore"]

    assert agent_store["discoveryGaps"][0]["gap_id"] == "gap_agent_agent_unknown_0_1_0"
    assert agent_store["discoveryGaps"][0]["state"] == "suspected"
    assert agent_store["discoveryGaps"][0]["owner_hint"] == "Agent 负责人"
    assert agent_store["discoveryGaps"][0]["affected_runs"] == ["run_1"]
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

    audit = build_console_snapshot(repository=repository)["consoleData"]["agentStore"]["runAudits"][0]

    assert audit["registration_state"] == "suspected"
    assert audit["discovery_gap_ids"] == ["gap_agent_agent_ai_sdlc_2_0_0"]
    assert audit["related_agent_versions"] == ["agent.ai-sdlc@1.0.0", "agent.ai-sdlc@2.0.0"]
    assert audit["deep_links"]["return_url"] == "/agent-store/agents/agent.ai-sdlc/runs/run_1"
    assert audit["raw_access_state"] == "summary_only"


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

    summary = build_console_snapshot(repository=repository)["consoleData"]["agentStore"]["storeSummaries"][0]

    assert summary["registry_fact_owner"] == "Agent Store"
    assert summary["risk_state"] == "warning"
    assert summary["policy_requirement"]["policy_owner"] == "安全/IAM"
    assert summary["policy_requirement"]["affected_actions"] == ["运行审计", "高风险 Skill 调用"]
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

    summary = build_console_snapshot(repository=repository)["consoleData"]["agentStore"]["storeSummaries"][0]

    assert summary["evidence_level"] == "L5"
    assert summary["confidence"] == 1.0
    assert summary["missing_evidence"] == []
    assert summary["risk_state"] == "normal"


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

    registry_record = build_console_snapshot(repository=repository)["consoleData"]["agentStore"]["registryMap"][0]

    assert registry_record["agent_id"] == "agent.ai-sdlc"
    assert registry_record["version"] == "1.0.0"
    assert registry_record["metadata_state"] == "consumed"
    assert registry_record["fact_owner"] == "Agent Store"
    assert registry_record["skill_count"] == 2
