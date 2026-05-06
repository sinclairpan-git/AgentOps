from __future__ import annotations

from datetime import UTC, datetime, timedelta

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


def test_ao6_ct_001b_agent_store_metadata_preserves_explicit_version_values():
    repository = InMemoryRepository()

    result = sync_agent_store_metadata(
        repository,
        {
            "agent_id": "agent.zero",
            "version": 0,
            "skills": [{"skill_id": "refine"}],
        },
    )

    assert result["version"] == "0"
    assert repository.get_agent_store_metadata("agent.zero", "0")["version"] == "0"
    assert repository.has_agent_store_skill("agent.zero", "0", "refine") is True


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


def test_ao6_ct_002a_discovery_ignores_events_without_agent_store_identity():
    repository = InMemoryRepository()
    event = base_event("stage_started", event_id="evt_custom_sink", idempotency_key="custom_sink:run_1")
    event.pop("agent_id", None)
    event.pop("agent_version", None)
    event["integration_mode"] = "custom_sink"
    event["payload"] = {"run_id": "run_1", "summary": "外部证据源"}
    repository.write_event(event)

    gaps = list_agent_store_discovery_gaps(repository)

    assert gaps == []


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


def test_ao6_ct_003b_metadata_refresh_accepts_null_skills():
    repository = InMemoryRepository()
    sync_agent_store_metadata(
        repository,
        {
            "agent_id": "agent.ai-sdlc",
            "version": "1.0.0",
            "skills": [{"skill_id": "refine"}],
        },
    )
    sync_agent_store_metadata(
        repository,
        {
            "agent_id": "agent.ai-sdlc",
            "version": "1.0.0",
            "skills": None,
        },
    )
    repository.write_event(base_event("stage_started"))

    gaps = list_agent_store_discovery_gaps(repository)

    assert repository.get_agent_store_metadata("agent.ai-sdlc", "1.0.0")["skills"] is None
    assert repository.has_agent_store_skill("agent.ai-sdlc", "1.0.0", "refine") is False
    assert len(gaps) == 1
    assert gaps[0]["gap_type"] == "skill_unregistered"
    assert gaps[0]["skill_id"] == "refine"


def test_ao6_ct_003c_agent_store_metadata_reads_are_isolated_from_repository_state():
    repository = InMemoryRepository()
    sync_agent_store_metadata(
        repository,
        {
            "agent_id": "agent.ai-sdlc",
            "version": "1.0.0",
            "skills": [{"skill_id": "refine"}],
        },
    )

    metadata = repository.get_agent_store_metadata("agent.ai-sdlc", "1.0.0")
    metadata["skills"][0]["skill_id"] = "polluted"
    fresh_metadata = repository.get_agent_store_metadata("agent.ai-sdlc", "1.0.0")

    assert fresh_metadata["skills"] == [{"skill_id": "refine"}]
    assert repository.has_agent_store_skill("agent.ai-sdlc", "1.0.0", "refine") is True


def test_ao6_ct_003d_agent_store_metadata_preserves_explicit_skill_ids():
    repository = InMemoryRepository()
    sync_agent_store_metadata(
        repository,
        {
            "agent_id": "agent.ai-sdlc",
            "version": "1.0.0",
            "skills": [{"skill_id": 0}],
        },
    )
    event = base_event("stage_started")
    event["payload"]["skill_id"] = 0
    event["payload"]["stage_id"] = 0
    event["payload"]["stage_name"] = 0
    repository.write_event(event)

    gaps = list_agent_store_discovery_gaps(repository)

    assert repository.has_agent_store_skill("agent.ai-sdlc", "1.0.0", "0") is True
    assert gaps == []


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


def test_ao6_ct_004a_run_audit_marks_mixed_agent_run_as_suspected():
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

    audit = get_run_audit(repository, "run_1")

    assert audit["registration_state"] == "suspected"
    assert audit["discovery_gap_ids"] == ["gap_agent_agent_ai_sdlc_2_0_0"]
    assert audit["related_agent_versions"] == ["agent.ai-sdlc@1.0.0", "agent.ai-sdlc@2.0.0"]
    assert "raw_payload" not in str(audit)


def test_ao6_ct_004b_run_audit_resolves_identity_from_agent_store_mapped_event():
    repository = InMemoryRepository()
    sync_agent_store_metadata(
        repository,
        {
            "agent_id": "agent.ai-sdlc",
            "version": "1.0.0",
            "skills": [{"skill_id": "refine"}],
        },
    )
    custom_event = base_event("stage_started", event_id="evt_custom_sink", idempotency_key="custom_sink:run_1")
    custom_event.pop("agent_id", None)
    custom_event.pop("agent_version", None)
    custom_event["integration_mode"] = "custom_sink"
    custom_event["payload"] = {"run_id": "run_1", "summary": "外部证据源"}
    repository.write_event(custom_event)
    repository.write_event(
        base_event(
            "stage_started",
            event_id="evt_stage_started_agent",
            idempotency_key="stage_started_agent:run_1",
            sequence_no=2,
        )
    )

    audit = get_run_audit(repository, "run_1")
    summary = get_agent_store_summary("agent.ai-sdlc", "1.0.0", evidence_summary("run_1"), repository=repository)

    assert audit["agent_id"] == "agent.ai-sdlc"
    assert audit["version"] == "1.0.0"
    assert audit["registration_state"] == "governed"
    assert audit["related_agent_versions"] == ["agent.ai-sdlc@1.0.0", "unknown_agent@unknown"]
    assert summary["run_audit"]["registration_state"] == "governed"


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


def test_ao6_ct_005a_agent_store_echo_summary_uses_only_current_run_gaps():
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
    run_2 = base_event(
        "stage_started",
        event_id="evt_stage_started_run_2",
        idempotency_key="stage_started:run_2",
        run_id="run_2",
        sequence_no=2,
    )
    run_2["payload"]["run_id"] = "run_2"
    run_2["payload"]["stage_id"] = "deploy"
    run_2["payload"]["stage_name"] = "deploy"
    repository.write_event(run_2)

    summary = get_agent_store_summary("agent.ai-sdlc", "1.0.0", evidence_summary("run_1"), repository=repository)
    risky_summary = get_agent_store_summary("agent.ai-sdlc", "1.0.0", evidence_summary("run_2"), repository=repository)

    assert summary["run_audit"]["registration_state"] == "governed"
    assert summary["risk_state"] == "normal"
    assert summary["discovery_gap_ids"] == []
    assert risky_summary["run_audit"]["registration_state"] == "suspected"
    assert risky_summary["risk_state"] == "warning"
    assert risky_summary["discovery_gap_ids"] == ["gap_skill_agent_ai_sdlc_1_0_0_deploy"]


def test_ao6_ct_005b_agent_store_echo_summary_includes_cross_version_run_gaps():
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

    summary = get_agent_store_summary("agent.ai-sdlc", "1.0.0", evidence_summary("run_1"), repository=repository)

    assert summary["run_audit"]["registration_state"] == "suspected"
    assert summary["risk_state"] == "warning"
    assert summary["discovery_gap_ids"] == ["gap_agent_agent_ai_sdlc_2_0_0"]


def test_ao6_ct_005c_agent_store_echo_summary_policy_requirement_is_isolated():
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
    summary["policy_requirement"]["affected_actions"].append("污染项")
    fresh_summary = get_agent_store_summary("agent.ai-sdlc", "1.0.0", evidence_summary(), repository=repository)

    assert fresh_summary["policy_requirement"]["affected_actions"] == ["运行审计", "高风险 Skill 调用"]


def test_ao6_ct_005d_agent_store_echo_summary_uses_runtime_validity_window():
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
    before = datetime.now(UTC) - timedelta(seconds=1)

    summary = get_agent_store_summary("agent.ai-sdlc", "1.0.0", evidence_summary(), repository=repository)

    after = datetime.now(UTC) + timedelta(seconds=1)
    calculated_at = datetime.fromisoformat(summary["calculated_at"].replace("Z", "+00:00"))
    valid_until = datetime.fromisoformat(summary["valid_until"].replace("Z", "+00:00"))
    assert before <= calculated_at <= after
    assert valid_until == calculated_at + timedelta(days=30)


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
