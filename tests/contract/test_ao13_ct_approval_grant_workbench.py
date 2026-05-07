from __future__ import annotations

from agentops.api.console_snapshot import _approval_grant_item, build_console_snapshot
from agentops.storage.repository import InMemoryRepository


REQUIRED_QUEUE_KEYS = {
    "id",
    "approval_id",
    "requester",
    "reason",
    "affected_actions",
    "status",
    "sla_due_at",
    "sla_state",
    "approver_scope",
    "supplemental_materials",
    "primary_action",
    "secondary_action",
    "audit_id",
    "denied_scope",
    "safety_note",
}
REQUIRED_GRANT_KEYS = {
    "id",
    "approval_id",
    "grant_status",
    "policy_version",
    "resource_scope",
    "ttl_summary",
    "expires_at",
    "revocation_state",
    "audit_id",
    "consumption_policy",
}
REQUIRED_AUDIT_KEYS = {"id", "approval_id", "stage", "occurred_at", "summary", "owner", "status", "audit_id"}


def _contains_unsafe_reference(value: object) -> bool:
    if isinstance(value, str):
        return "http://" in value or "https://" in value
    if isinstance(value, list | tuple):
        return any(_contains_unsafe_reference(item) for item in value)
    if isinstance(value, dict):
        forbidden = {
            "raw_payload",
            "download_url",
            "raw_url",
            "original_url",
            "raw_access_url",
            "pullRequestBody",
            "pull_request_body",
        }
        return bool(forbidden & set(value)) or any(_contains_unsafe_reference(item) for item in value.values())
    return False


def test_ao13_ct_001_snapshot_contains_approval_workbench_domain():
    console_data = build_console_snapshot()["consoleData"]
    workbench = console_data["approvalWorkbench"]

    assert set(workbench) == {"queues", "grants", "auditTrail", "guardrails"}
    assert workbench["queues"]
    assert workbench["grants"]
    assert workbench["auditTrail"]
    assert len(workbench["queues"]) == len(console_data["approvals"])
    assert len(workbench["grants"]) == len(console_data["approvals"])
    assert len(workbench["auditTrail"]) == len(console_data["approvals"])
    assert {item["approval_id"] for item in workbench["queues"]} == {
        item["approval_id"] for item in console_data["approvals"]
    }
    assert {item["approval_id"] for item in workbench["grants"]} == {
        item["approval_id"] for item in console_data["approvals"]
    }
    assert {item["approval_id"] for item in workbench["auditTrail"]} == {
        item["approval_id"] for item in console_data["approvals"]
    }
    assert "审批队列只展示人工处置摘要" in " ".join(workbench["guardrails"])


def test_ao13_ct_002_queue_grant_and_audit_rows_have_contract_fields():
    workbench = build_console_snapshot()["consoleData"]["approvalWorkbench"]

    for queue in workbench["queues"]:
        assert REQUIRED_QUEUE_KEYS == set(queue)
        assert queue["approval_id"]
        assert queue["requester"]
        assert queue["reason"]
        assert queue["affected_actions"]
        assert queue["audit_id"]
        assert queue["primary_action"] in {
            "处理审批",
            "查看审批记录",
            "查看撤销原因",
            "升级审批",
            "查看拒绝原因",
            "补充材料",
        }
        assert "只读展示审批处置摘要" in queue["safety_note"]

    for grant in workbench["grants"]:
        assert REQUIRED_GRANT_KEYS == set(grant)
        assert grant["approval_id"]
        assert grant["policy_version"]
        assert grant["resource_scope"]
        assert grant["ttl_summary"]
        assert grant["audit_id"]
        assert "策略版本和资源范围" in grant["consumption_policy"]

    for audit_node in workbench["auditTrail"]:
        assert REQUIRED_AUDIT_KEYS == set(audit_node)
        assert audit_node["approval_id"]
        assert audit_node["audit_id"]


def test_ao13_ct_003_workbench_has_no_raw_access_or_download_reference():
    workbench = build_console_snapshot()["consoleData"]["approvalWorkbench"]

    assert "raw_payload" not in str(workbench)
    assert "download_url" not in str(workbench)
    assert "raw_access_url" not in str(workbench)
    assert not _contains_unsafe_reference(workbench)


def test_ao13_ct_004_approval_states_bind_to_safe_grant_outcomes():
    workbench = build_console_snapshot()["consoleData"]["approvalWorkbench"]
    queues = {item["approval_id"]: item for item in workbench["queues"]}
    grants = {item["approval_id"]: item for item in workbench["grants"]}
    audit_trail = {item["approval_id"]: item for item in workbench["auditTrail"]}

    assert queues["ap_001"]["status"] == "pending"
    assert queues["ap_001"]["primary_action"] == "处理审批"
    assert grants["ap_001"]["grant_status"] == "pending"
    assert grants["ap_001"]["ttl_summary"] == "待审批后签发"

    assert queues["ap_002"]["status"] == "escalated"
    assert queues["ap_002"]["sla_state"] == "已升级"
    assert grants["ap_002"]["grant_status"] == "expired"
    assert grants["ap_002"]["revocation_state"] == "已过期，需重新审批"

    assert queues["ap_003"]["status"] == "approved"
    assert queues["ap_003"]["primary_action"] == "查看审批记录"
    assert grants["ap_003"]["grant_status"] == "active"
    assert grants["ap_003"]["ttl_summary"] == "15 分钟限时 Grant"

    assert queues["ap_004"]["status"] == "revoked"
    assert queues["ap_004"]["denied_scope"] == "store.publish"
    assert grants["ap_004"]["grant_status"] == "revoked"
    assert audit_trail["ap_004"]["stage"] == "撤销"


def test_ao13_ct_005_empty_repository_reports_safe_empty_workbench():
    workbench = build_console_snapshot(repository=InMemoryRepository())["consoleData"]["approvalWorkbench"]

    assert workbench["queues"] == []
    assert workbench["grants"] == []
    assert workbench["auditTrail"] == []
    guardrails = " ".join(workbench["guardrails"])
    assert "审批队列只展示人工处置摘要" in guardrails
    assert "不得作为唯一审批人" in guardrails


def test_ao13_ct_006_pending_approval_cannot_materialize_active_grant():
    grant = _approval_grant_item(
        {
            "approval_id": "ap_tampered",
            "requester": "发布 Agent",
            "reason": "生产部署需要短期 Grant",
            "affected_actions": "deploy:prod",
            "sla_due_at": "2026-05-06 13:20",
            "status": "pending",
            "grant_status": "active",
            "audit_id": "audit_ap_tampered",
        }
    )

    assert grant["grant_status"] == "pending"
    assert grant["ttl_summary"] == "待审批后签发"
    assert grant["expires_at"] == "待审批"
    assert grant["revocation_state"] == "未签发"
