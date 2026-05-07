from __future__ import annotations

from agentops.api.console_snapshot import build_console_snapshot
from agentops.storage.repository import InMemoryRepository


REQUIRED_HEALTH_KEYS = {
    "id",
    "connector_id",
    "name",
    "status",
    "last_seen_at",
    "freshness",
    "freshness_state",
    "rate_limit_state",
    "rate_limit_detail",
    "degrade_action",
    "evidence_impact",
    "owner",
    "request_id",
    "primary_action",
    "secondary_action",
    "safety_note",
}
REQUIRED_DLQ_KEYS = {
    "id",
    "connector_id",
    "dlq_depth",
    "oldest_event_age",
    "replay_state",
    "retry_window",
    "degrade_policy",
    "request_id",
    "audit_id",
    "safety_note",
}
REQUIRED_SYNC_KEYS = {"id", "connector_id", "stage", "occurred_at", "summary", "owner", "status", "request_id"}


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


def test_ao14_ct_001_snapshot_contains_connector_workbench_domain():
    console_data = build_console_snapshot()["consoleData"]
    workbench = console_data["connectorWorkbench"]

    assert set(workbench) == {"health", "dlq", "syncTrail", "guardrails"}
    assert workbench["health"]
    assert workbench["dlq"]
    assert workbench["syncTrail"]
    assert len(workbench["health"]) == len(console_data["connectors"])
    assert len(workbench["dlq"]) == len(console_data["connectors"])
    assert len(workbench["syncTrail"]) == len(console_data["connectors"])
    assert {item["connector_id"] for item in workbench["health"]} == {item["id"] for item in console_data["connectors"]}
    assert {item["connector_id"] for item in workbench["dlq"]} == {item["id"] for item in console_data["connectors"]}
    assert {item["connector_id"] for item in workbench["syncTrail"]} == {item["id"] for item in console_data["connectors"]}
    guardrails = " ".join(workbench["guardrails"])
    assert "15 分钟" in guardrails
    assert "超过 20 分钟" in guardrails
    assert "Outbox Replay" in guardrails


def test_ao14_ct_002_health_dlq_and_sync_rows_have_contract_fields():
    workbench = build_console_snapshot()["consoleData"]["connectorWorkbench"]

    for health in workbench["health"]:
        assert REQUIRED_HEALTH_KEYS == set(health)
        assert health["connector_id"]
        assert health["name"]
        assert health["freshness"]
        assert health["rate_limit_detail"]
        assert health["owner"]
        assert health["request_id"]
        assert health["primary_action"] in {"保持监控", "补齐治理加载证明", "查看降级影响"}
        assert "只读健康摘要" in health["safety_note"]

    for dlq in workbench["dlq"]:
        assert REQUIRED_DLQ_KEYS == set(dlq)
        assert dlq["connector_id"]
        assert dlq["dlq_depth"]
        assert dlq["oldest_event_age"]
        assert dlq["retry_window"]
        assert dlq["audit_id"]
        assert "队列摘要" in dlq["safety_note"]

    for sync_node in workbench["syncTrail"]:
        assert REQUIRED_SYNC_KEYS == set(sync_node)
        assert sync_node["connector_id"]
        assert sync_node["summary"]
        assert sync_node["owner"]
        assert sync_node["request_id"]


def test_ao14_ct_003_workbench_has_no_raw_access_or_download_reference():
    workbench = build_console_snapshot()["consoleData"]["connectorWorkbench"]

    assert "raw_payload" not in str({key: value for key, value in workbench.items() if key != "guardrails"})
    assert "download_url" not in str(workbench)
    assert "raw_access_url" not in str(workbench)
    assert not _contains_unsafe_reference(workbench)


def test_ao14_ct_004_materialized_sdlc_connector_cannot_claim_governance_activation():
    workbench = build_console_snapshot()["consoleData"]["connectorWorkbench"]
    health = {item["connector_id"]: item for item in workbench["health"]}
    dlq = {item["connector_id"]: item for item in workbench["dlq"]}
    sync = {item["connector_id"]: item for item in workbench["syncTrail"]}

    assert health["conn_sdlc"]["status"] == "materialized"
    assert health["conn_sdlc"]["freshness_state"] == "materialized"
    assert health["conn_sdlc"]["primary_action"] == "补齐治理加载证明"
    assert "不构成 verified_loaded" in health["conn_sdlc"]["evidence_impact"]
    assert dlq["conn_sdlc"]["dlq_depth"] == "待验证"
    assert dlq["conn_sdlc"]["replay_state"] == "materialized"
    assert "verified_loaded" in dlq["conn_sdlc"]["retry_window"]
    assert sync["conn_sdlc"]["stage"] == "待证明"


def test_ao14_ct_005_degraded_connectors_lower_evidence_and_enter_manual_replay_boundary():
    workbench = build_console_snapshot()["consoleData"]["connectorWorkbench"]
    degraded_health = [item for item in workbench["health"] if item["status"] == "degraded"]
    degraded_dlq = {item["connector_id"]: item for item in workbench["dlq"] if item["replay_state"] == "pending"}

    assert degraded_health
    for item in degraded_health:
        assert item["freshness_state"] == "degraded"
        assert item["rate_limit_state"] == "degraded"
        assert item["primary_action"] == "查看降级影响"
        assert "降低证据等级" in item["evidence_impact"]
        assert item["connector_id"] in degraded_dlq
        assert degraded_dlq[item["connector_id"]]["dlq_depth"] != "0"
        assert "人工审批" in degraded_dlq[item["connector_id"]]["retry_window"]
        assert "Outbox Replay" in degraded_dlq[item["connector_id"]]["degrade_policy"]


def test_ao14_ct_006_repository_snapshot_includes_git_pr_ci_test_iam_boundaries():
    workbench = build_console_snapshot(repository=InMemoryRepository())["consoleData"]["connectorWorkbench"]
    guardrails = " ".join(workbench["guardrails"])
    connector_ids = {item["connector_id"] for item in workbench["health"]}

    assert workbench["health"]
    assert {"conn_git", "conn_pr", "conn_ci", "conn_test", "conn_iam"} <= connector_ids
    assert "Git、PR、CI、测试、IAM" in guardrails
    assert "连接器工作台不得展示原始载荷" in guardrails
    assert "materialized/unverified" in guardrails
