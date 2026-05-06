from __future__ import annotations

import pytest

from agentops.api.agent_store import get_run_audit, list_agent_store_discovery_gaps, sync_agent_store_metadata
from agentops.api.app import create_app
from agentops.api.console_snapshot import build_console_snapshot
from agentops.api.store_summary import get_agent_store_summary
from agentops.core.errors import AgentOpsError
from agentops.storage.repository import InMemoryRepository
from tests.contract.conftest import base_event


def evidence_summary(run_id: str = "run_1"):
    return {
        "run_id": run_id,
        "evidence_level": "L5",
        "confidence": 1.0,
        "missing_evidence": [],
    }


def test_ao6_ct_001_agent_store_metadata_is_consumed_not_owned():
    repository = InMemoryRepository()

    result = sync_agent_store_metadata(
        repository,
        {
            "agent_id": "agent.ai-sdlc",
            "version": "1.0.0",
            "owner": "AI-SDLC 团队",
            "skills": [{"skill_id": "refine", "display_name": "需求澄清"}],
        },
    )

    assert result["metadata_state"] == "consumed"
    assert result["fact_owner"] == "Agent Store"
    assert repository.get_agent_store_metadata("agent.ai-sdlc", "1.0.0")["owner"] == "AI-SDLC 团队"
    assert repository.has_agent_store_skill("agent.ai-sdlc", "1.0.0", "refine") is True


def test_ao6_ct_001a_agent_store_metadata_accepts_agent_version_alias():
    repository = InMemoryRepository()

    result = sync_agent_store_metadata(
        repository,
        {
            "agent_id": "agent.ai-sdlc",
            "agent_version": "1.0.0",
            "skills": [{"skill_id": "refine"}],
        },
    )

    assert result["version"] == "1.0.0"
    assert repository.get_agent_store_metadata("agent.ai-sdlc", "1.0.0")["agent_version"] == "1.0.0"
    assert repository.has_agent_store_skill("agent.ai-sdlc", "1.0.0", "refine") is True


def test_ao6_ct_002_unregistered_agent_is_discovered_without_raw_payload():
    repository = InMemoryRepository()
    repository.write_event(base_event("stage_started", agent_id="agent.unknown", agent_version="0.1.0"))

    gaps = list_agent_store_discovery_gaps(repository)

    assert gaps == [
        {
            "gap_id": "gap_agent_agent_unknown_0_1_0",
            "gap_type": "agent_unregistered",
            "agent_id": "agent.unknown",
            "version": "0.1.0",
            "skill_id": "",
            "state": "suspected",
            "severity": "高",
            "affected_runs": ["run_1"],
            "owner_hint": "Agent Owner",
            "primary_action": "通知 Owner 补齐 Agent Store 注册事实",
            "audit_id": "audit_gap_agent_agent_unknown_0_1_0",
        }
    ]
    assert "raw_payload" not in str(gaps)


def test_ao6_ct_003_registered_agent_with_unregistered_skill_is_discovered():
    repository = InMemoryRepository()
    sync_agent_store_metadata(
        repository,
        {
            "agent_id": "agent.ai-sdlc",
            "version": "1.0.0",
            "skills": [{"skill_id": "design", "display_name": "设计"}],
        },
    )
    repository.write_event(base_event("stage_started"))

    gaps = list_agent_store_discovery_gaps(repository)

    assert len(gaps) == 1
    assert gaps[0]["gap_type"] == "skill_unregistered"
    assert gaps[0]["skill_id"] == "refine"
    assert gaps[0]["affected_runs"] == ["run_1"]


def test_ao6_ct_003a_metadata_refresh_removes_stale_skills():
    repository = InMemoryRepository()
    sync_agent_store_metadata(
        repository,
        {
            "agent_id": "agent.ai-sdlc",
            "version": "1.0.0",
            "skills": [{"skill_id": "refine"}, {"skill_id": "design"}],
        },
    )
    sync_agent_store_metadata(
        repository,
        {
            "agent_id": "agent.ai-sdlc",
            "version": "1.0.0",
            "skills": [{"skill_id": "design"}],
        },
    )
    repository.write_event(base_event("stage_started"))

    gaps = list_agent_store_discovery_gaps(repository)

    assert repository.has_agent_store_skill("agent.ai-sdlc", "1.0.0", "refine") is False
    assert len(gaps) == 1
    assert gaps[0]["gap_type"] == "skill_unregistered"
    assert gaps[0]["skill_id"] == "refine"


def test_ao6_ct_004_run_audit_contains_deep_links_and_no_raw_payload():
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

    audit = get_run_audit(repository, "run_1")

    assert audit["registration_state"] == "governed"
    assert audit["event_ids"] == ["evt_stage_started"]
    assert audit["raw_access_state"] == "summary_only"
    assert audit["deep_links"] == {
        "agent_id": "agent.ai-sdlc",
        "version": "1.0.0",
        "session_id": "sess_1",
        "run_id": "run_1",
        "installation_id": "inst_1",
        "trace_id": "trace_1",
        "audit_id": "audit_run_run_1",
        "return_url": "/agent-store/agents/agent.ai-sdlc/runs/run_1",
    }
    assert "raw_payload" not in str(audit)


def test_ao6_ct_005_agent_store_echo_summary_includes_policy_requirement_and_audit():
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

    summary = get_agent_store_summary("agent.ai-sdlc", "1.0.0", evidence_summary(), repository=repository)

    assert summary["schema_version"] == "agentops.agent_store.echo.v1"
    assert summary["metadata_state"] == "registered"
    assert summary["registry_fact_owner"] == "Agent Store"
    assert summary["risk_state"] == "normal"
    assert summary["policy_requirement"] == {
        "required_by": "AgentOps",
        "source": "runtime_policy",
        "issuer": "AgentOps Policy Service",
        "policy_owner": "安全/IAM",
        "policy_version": "runtime-v2",
        "can_ignore": False,
        "affected_actions": ["运行审计", "高风险 Skill 调用"],
    }
    assert summary["run_audit"]["audit_id"] == "audit_run_run_1"
    assert summary["deep_links"]["return_url"] == "/agent-store/agents/agent.ai-sdlc/runs/run_1"
    assert "raw_payload" not in str(summary)


def test_ao6_ct_006_agent_store_echo_summary_rejects_unsupported_schema():
    repository = InMemoryRepository()
    repository.write_event(base_event("stage_started"))

    with pytest.raises(AgentOpsError) as exc:
        get_agent_store_summary("agent.ai-sdlc", "1.0.0", evidence_summary(), repository=repository, consumer_schema_version="2.0")

    assert exc.value.error_code == "SUMMARY_SCHEMA_UNSUPPORTED"


def test_ao6_ct_006a_agent_store_echo_summary_rejects_run_target_mismatch():
    repository = InMemoryRepository()
    repository.write_event(base_event("stage_started"))

    with pytest.raises(AgentOpsError) as exc:
        get_agent_store_summary("agent.other", "9.9.9", evidence_summary(), repository=repository)

    assert exc.value.error_code == "STORE_SUMMARY_RUN_MISMATCH"


def test_ao6_ct_007_console_snapshot_surfaces_agent_store_discovery_risks():
    repository = InMemoryRepository()
    repository.write_event(base_event("stage_started", agent_id="agent.unknown", agent_version="0.1.0"))

    snapshot = build_console_snapshot(repository=repository)

    assert any(risk["source"] == "Agent Store" for risk in snapshot["consoleData"]["risks"])
    assert any(connector["id"] == "conn_agent_store" and connector["status"] == "degraded" for connector in snapshot["consoleData"]["connectors"])


def test_ao6_ct_008_app_declares_agent_store_and_run_audit_routes():
    app = create_app()

    assert app["agent_store_metadata"] == "POST /v1/agent-store/metadata"
    assert app["agent_store_discovery"] == "/v1/agent-store/discovery"
    assert app["run_audit"] == "/v1/runs/{run_id}/audit"
