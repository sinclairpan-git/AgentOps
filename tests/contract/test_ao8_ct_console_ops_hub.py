from __future__ import annotations

from agentops.api.agent_store import sync_agent_store_metadata
from agentops.api.console_snapshot import ROUTES, build_console_snapshot
from agentops.storage.repository import InMemoryRepository
from tests.contract.conftest import base_event


ROUTE_IDS = {route["id"] for route in ROUTES}
FORBIDDEN_OPERATION_TEXT = {
    "artifact_generated",
    "generation_snapshot",
    "l5_eligibility_input",
    "stage_started",
    "stage_completed",
    "gate_result",
    "verification_result",
    "violation_scan_completed",
    "Agent Owner",
    "Owner",
}


def _assert_unique_ids(items: list[dict[str, str]]) -> None:
    ids = [item["id"] for item in items]
    assert len(ids) == len(set(ids))


def _assert_operation_center_contract(operation_center: dict[str, list[dict[str, str]]]) -> None:
    for key in ("notifications", "todos", "searchIndex"):
        _assert_unique_ids(operation_center[key])

    for item in [*operation_center["notifications"], *operation_center["todos"], *operation_center["searchIndex"]]:
        assert item["route"] in ROUTE_IDS

    visible_text = " ".join(
        str(item.get(field, ""))
        for item in [*operation_center["notifications"], *operation_center["todos"], *operation_center["searchIndex"]]
        for field in ("title", "body", "kind", "owner", "due")
    )
    for forbidden in FORBIDDEN_OPERATION_TEXT:
        assert forbidden not in visible_text


def test_ao8_ct_001_console_snapshot_contains_operation_center():
    repository = InMemoryRepository()
    repository.write_event(base_event("stage_started", agent_id="agent.unknown", agent_version="0.1.0"))

    operation_center = build_console_snapshot(repository=repository)["consoleData"]["operationCenter"]

    assert set(operation_center) == {"notifications", "todos", "searchIndex"}
    assert operation_center["notifications"]
    assert operation_center["todos"]
    assert operation_center["searchIndex"]
    assert "raw_payload" not in str(operation_center)
    _assert_operation_center_contract(operation_center)


def test_ao8_ct_002_agent_store_gap_becomes_todo_and_search_result():
    repository = InMemoryRepository()
    repository.write_event(base_event("stage_started", agent_id="agent.unknown", agent_version="0.1.0"))

    operation_center = build_console_snapshot(repository=repository)["consoleData"]["operationCenter"]

    assert any(
        item["route"] == "agent-store-audit" and item["owner"] == "Agent 负责人"
        for item in operation_center["todos"]
    )
    assert any(
        item["route"] == "agent-store-audit" and item["due"] == "待排期"
        for item in operation_center["todos"]
    )
    assert sum(1 for item in operation_center["todos"] if item["id"] == "todo_gap_agent_agent_unknown_0_1_0") == 1
    assert any(
        item["kind"] == "Agent Store 审计" and item["route"] == "agent-store-audit"
        for item in operation_center["searchIndex"]
    )
    assert sum(1 for item in operation_center["searchIndex"] if item["id"] == "gap_agent_agent_unknown_0_1_0") == 1
    _assert_operation_center_contract(operation_center)


def test_ao8_ct_003_approval_and_evidence_items_are_actionable():
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
    event = base_event("stage_started")
    event["signature"] = ""
    repository.write_event(event)

    operation_center = build_console_snapshot(repository=repository)["consoleData"]["operationCenter"]

    assert any(item["title"] == "审批待处理" and item["route"] == "approvals" for item in operation_center["notifications"])
    assert any(
        item["title"] == "处理审批" and item["status"] == "pending" and item["due"] == "2026-05-06 13:20"
        for item in operation_center["todos"]
    )
    assert any(item["kind"] == "审批中心" and item["id"] == "ap_pending" for item in operation_center["searchIndex"])
    _assert_operation_center_contract(operation_center)


def test_ao8_ct_004_registered_clean_run_keeps_search_without_false_todo():
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

    operation_center = build_console_snapshot(repository=repository)["consoleData"]["operationCenter"]

    assert any(item["id"] == "run_1" and item["route"] == "runs" for item in operation_center["searchIndex"])
    assert not any(item["route"] == "agent-store-audit" for item in operation_center["todos"])
    _assert_operation_center_contract(operation_center)


def test_ao8_ct_005_agent_store_gap_survives_operation_center_caps():
    repository = InMemoryRepository()
    repository.write_event(base_event("stage_started", agent_id="agent.unknown", agent_version="0.1.0"))
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

    operation_center = build_console_snapshot(repository=repository)["consoleData"]["operationCenter"]

    assert len(operation_center["todos"]) == 12
    assert len(operation_center["searchIndex"]) == 30
    assert any(item["id"] == "todo_gap_agent_agent_unknown_0_1_0" for item in operation_center["todos"])
    assert any(item["id"] == "gap_agent_agent_unknown_0_1_0" for item in operation_center["searchIndex"])
    _assert_operation_center_contract(operation_center)
