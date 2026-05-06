from __future__ import annotations

from agentops.api.console_snapshot import build_console_snapshot
from agentops.storage.repository import InMemoryRepository
from tests.contract.conftest import base_event

REQUIRED_TIMELINE_KEYS = {"id", "stage", "occurred_at", "title", "body", "owner", "status"}
REQUIRED_PACKET_KEYS = {
    "packet_id",
    "summary",
    "export_state",
    "evidence_refs",
    "echo_targets",
    "retention_policy",
    "safety_note",
}


def _contains_url_or_forbidden_key(value: object) -> bool:
    if isinstance(value, str):
        return "http://" in value or "https://" in value
    if isinstance(value, list | tuple):
        return any(_contains_url_or_forbidden_key(item) for item in value)
    if isinstance(value, dict):
        forbidden = {"raw_payload", "download_url", "raw_url", "original_url", "raw_access_url"}
        return bool(forbidden & set(value)) or any(_contains_url_or_forbidden_key(item) for item in value.values())
    return False


def _repository_with_core_items() -> InMemoryRepository:
    repository = InMemoryRepository()
    repository.write_event(base_event("stage_started", agent_id="agent.unknown", agent_version="0.1.0"))
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
    return repository


def test_ao10_ct_001_each_action_detail_has_readable_timeline():
    details = build_console_snapshot(repository=_repository_with_core_items())["consoleData"]["actionWorkbench"]["details"]

    assert details
    for detail in details:
        timeline = detail["timeline"]
        assert len(timeline) >= 3
        assert [node["stage"] for node in timeline[:3]] == ["发现", "研判", "关闭"]
        for node in timeline:
            assert REQUIRED_TIMELINE_KEYS <= set(node)
            assert node["owner"]
            assert node["body"]
            assert "raw_payload" not in str(node)
            assert not _contains_url_or_forbidden_key(node)


def test_ao10_ct_002_each_action_detail_has_summary_only_audit_packet():
    details = build_console_snapshot(repository=_repository_with_core_items())["consoleData"]["actionWorkbench"]["details"]

    for detail in details:
        packet = detail["audit_packet"]
        assert REQUIRED_PACKET_KEYS <= set(packet)
        assert packet["packet_id"].startswith("packet_action_")
        assert packet["export_state"] == "只读摘要已生成"
        assert packet["echo_targets"]
        assert packet["evidence_refs"]
        assert "Evidence Vault 原文" in packet["retention_policy"]
        assert "不提供原文下载或生产写操作" in packet["safety_note"]
        assert "raw_payload" not in str(packet)
        assert "download_url" not in packet
        assert "raw_url" not in packet
        assert not _contains_url_or_forbidden_key(packet)


def test_ao10_ct_003_approval_evidence_and_agent_store_gap_are_covered():
    details = build_console_snapshot(repository=_repository_with_core_items())["consoleData"]["actionWorkbench"]["details"]
    detail_ids = {detail["id"]: detail for detail in details}

    for prefix in ("action_approval_", "action_evidence_", "action_gap_"):
        matching = [detail for detail_id, detail in detail_ids.items() if detail_id.startswith(prefix)]
        assert matching, f"{prefix} detail must exist"
        for detail in matching:
            assert detail["timeline"]
            assert detail["audit_packet"]["echo_targets"]


def test_ao10_ct_004_audit_packet_targets_are_localized_and_safe():
    details = build_console_snapshot(repository=_repository_with_core_items())["consoleData"]["actionWorkbench"]["details"]

    for detail in details:
        targets = "、".join(detail["audit_packet"]["echo_targets"])
        assert targets
        assert "governed" not in targets
        assert "ignored" not in targets
        assert "blocked" not in targets
        assert "http://" not in str(detail["audit_packet"])
        assert "https://" not in str(detail["audit_packet"])
