from __future__ import annotations

from agentops.api.agent_store import sync_agent_store_metadata
from agentops.api.console_snapshot import ROUTES, build_console_snapshot
from agentops.storage.repository import InMemoryRepository
from tests.contract.conftest import base_event

ROUTE_IDS = {route["id"] for route in ROUTES}
REQUIRED_DETAIL_KEYS = {
    "id",
    "title",
    "summary",
    "status",
    "route",
    "owner",
    "primary_action",
    "secondary_action",
    "close_condition",
    "audit_ref",
    "evidence_ref",
    "related_ref",
    "safety_note",
}


def test_ao9_ct_001_snapshot_contains_action_workbench_without_raw_payload():
    repository = InMemoryRepository()
    repository.write_event(
        base_event("stage_started", agent_id="agent.unknown", agent_version="0.1.0")
    )

    console_data = build_console_snapshot(repository=repository)["consoleData"]
    action_workbench = console_data["actionWorkbench"]

    assert set(action_workbench) == {"details"}
    assert action_workbench["details"]
    assert "raw_payload" not in str(action_workbench)


def test_ao9_ct_002_operation_center_action_ids_resolve_to_details():
    repository = InMemoryRepository()
    repository.store_approval(
        {
            "approval_id": "ap_pending",
            "requester": "发布 Agent",
            "reason": "生产部署需要短期 Grant",
            "affected_actions": "deploy:prod",
            "sla_due_at": "2026-05-06 13:20",
            "status": "pending",
            "grant_status": "pending",
            "audit_id": "audit_ap_pending",
        }
    )
    repository.write_event(
        base_event("stage_started", agent_id="agent.unknown", agent_version="0.1.0")
    )

    console_data = build_console_snapshot(repository=repository)["consoleData"]
    details_by_id = {
        item["id"]: item for item in console_data["actionWorkbench"]["details"]
    }

    for collection_name in ("notifications", "todos", "searchIndex"):
        for item in console_data["operationCenter"][collection_name]:
            action_id = item.get("action_id")
            if action_id:
                assert action_id in details_by_id
                assert details_by_id[action_id]["route"] in ROUTE_IDS


def test_ao9_ct_003_agent_store_gap_detail_survives_caps():
    repository = InMemoryRepository()
    repository.write_event(
        base_event("stage_started", agent_id="agent.unknown", agent_version="0.1.0")
    )
    for index in range(35):
        repository.store_approval(
            {
                "approval_id": f"ap_bulk_{index:02d}",
                "requester": "发布 Agent",
                "reason": f"批量审批 {index:02d}",
                "affected_actions": "deploy:prod",
                "sla_due_at": "2026-05-06 13:20",
                "status": "pending",
                "grant_status": "pending",
                "audit_id": f"audit_ap_bulk_{index:02d}",
            }
        )

    console_data = build_console_snapshot(repository=repository)["consoleData"]
    detail_ids = {item["id"] for item in console_data["actionWorkbench"]["details"]}

    assert "action_gap_gap_agent_agent_unknown_0_1_0" in detail_ids
    assert any(
        item["action_id"] == "action_gap_gap_agent_agent_unknown_0_1_0"
        for item in console_data["operationCenter"]["todos"]
    )
    assert any(
        item["action_id"] == "action_gap_gap_agent_agent_unknown_0_1_0"
        for item in console_data["operationCenter"]["searchIndex"]
    )


def test_ao9_ct_003b_gap_detail_survives_action_workbench_cap():
    repository = InMemoryRepository()
    repository.write_event(
        base_event("stage_started", agent_id="agent.unknown", agent_version="0.1.0")
    )
    for index in range(45):
        repository.store_approval(
            {
                "approval_id": f"ap_bulk_{index:02d}",
                "requester": "发布 Agent",
                "reason": f"批量审批 {index:02d}",
                "affected_actions": "deploy:prod",
                "sla_due_at": "2026-05-06 13:20",
                "status": "pending",
                "grant_status": "pending",
                "audit_id": f"audit_ap_bulk_{index:02d}",
            }
        )

    console_data = build_console_snapshot(repository=repository)["consoleData"]
    detail_ids = {item["id"] for item in console_data["actionWorkbench"]["details"]}

    assert len(console_data["actionWorkbench"]["details"]) >= 45
    for collection_name in ("todos", "searchIndex"):
        for item in console_data["operationCenter"][collection_name]:
            action_id = item.get("action_id")
            if action_id:
                assert action_id in detail_ids


def test_ao9_ct_004_action_detail_shape_and_read_only_safety_note():
    repository = InMemoryRepository()
    repository.write_event(
        base_event("stage_started", agent_id="agent.unknown", agent_version="0.1.0")
    )

    details = build_console_snapshot(repository=repository)["consoleData"][
        "actionWorkbench"
    ]["details"]

    for detail in details:
        assert REQUIRED_DETAIL_KEYS <= set(detail)
        assert detail["route"] in ROUTE_IDS
        assert detail["owner"]
        assert detail["primary_action"]
        assert detail["secondary_action"]
        assert detail["close_condition"]
        assert detail["audit_ref"]
        assert detail["safety_note"] == "当前为只读处置预案，不执行生产写操作。"
        assert "governed" not in detail["close_condition"]
        assert "ignored" not in detail["close_condition"]
        assert "blocked" not in detail["close_condition"]


def test_ao9_ct_005_all_search_action_ids_resolve_to_details():
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

    console_data = build_console_snapshot(repository=repository)["consoleData"]
    detail_ids = {item["id"] for item in console_data["actionWorkbench"]["details"]}

    for item in console_data["operationCenter"]["searchIndex"]:
        action_id = item.get("action_id")
        if action_id:
            assert action_id in detail_ids


def test_ao9_ct_006_clean_registered_run_does_not_create_gap_detail():
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

    details = build_console_snapshot(repository=repository)["consoleData"][
        "actionWorkbench"
    ]["details"]

    assert not any(item["id"].startswith("action_gap_") for item in details)
