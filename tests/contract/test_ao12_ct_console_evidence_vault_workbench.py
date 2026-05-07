from __future__ import annotations

from agentops.api.console_snapshot import build_console_snapshot
from agentops.storage.repository import InMemoryRepository
from tests.contract.conftest import base_event


REQUIRED_REQUEST_KEYS = {
    "id",
    "evidence_id",
    "run_id",
    "requester",
    "reason",
    "status",
    "denied_scope",
    "audit_id",
    "ttl_summary",
    "primary_action",
    "safety_note",
}
REQUIRED_GRANT_KEYS = {
    "id",
    "evidence_id",
    "requester",
    "status",
    "scope",
    "expires_at",
    "audit_id",
    "consumption_policy",
}
REQUIRED_AUDIT_KEYS = {"id", "evidence_id", "stage", "occurred_at", "summary", "owner", "status", "audit_id"}


def _repository() -> InMemoryRepository:
    repository = InMemoryRepository()
    repository.write_event(base_event("stage_started", agent_id="agent.vault", agent_version="1.0.0"))
    repository.write_event(base_event("stage_completed", agent_id="agent.vault", agent_version="1.0.0", sequence_no=2))
    return repository


def _contains_unsafe_reference(value: object) -> bool:
    if isinstance(value, str):
        return "http://" in value or "https://" in value
    if isinstance(value, list | tuple):
        return any(_contains_unsafe_reference(item) for item in value)
    if isinstance(value, dict):
        forbidden = {"raw_payload", "download_url", "raw_url", "original_url", "raw_access_url", "pullRequestBody"}
        return bool(forbidden & set(value)) or any(_contains_unsafe_reference(item) for item in value.values())
    return False


def test_ao12_ct_001_snapshot_contains_evidence_vault_domain():
    evidence_vault = build_console_snapshot(repository=_repository())["consoleData"]["evidenceVault"]

    assert set(evidence_vault) == {"requests", "grants", "auditTrail", "guardrails"}
    assert evidence_vault["requests"]
    assert evidence_vault["grants"]
    assert evidence_vault["auditTrail"]
    assert "默认不展示原文" in " ".join(evidence_vault["guardrails"])


def test_ao12_ct_002_requests_grants_and_audits_have_contract_fields():
    evidence_vault = build_console_snapshot(repository=_repository())["consoleData"]["evidenceVault"]

    for request in evidence_vault["requests"]:
        assert REQUIRED_REQUEST_KEYS == set(request)
        assert request["evidence_id"]
        assert request["run_id"]
        assert request["audit_id"]
        assert request["primary_action"] in {"申请原文访问", "查看授权记录", "补充申请理由", "仅查看哈希告警", "等待审批"}
        assert "不展示 Evidence Vault 原文" in request["safety_note"]

    for grant in evidence_vault["grants"]:
        assert REQUIRED_GRANT_KEYS == set(grant)
        assert "不提供原文下载" in grant["consumption_policy"]

    for audit_node in evidence_vault["auditTrail"]:
        assert REQUIRED_AUDIT_KEYS == set(audit_node)
        assert audit_node["audit_id"]


def test_ao12_ct_003_vault_is_summary_only_and_has_no_raw_access_reference():
    evidence_vault = build_console_snapshot(repository=_repository())["consoleData"]["evidenceVault"]

    assert "raw_payload" not in str(evidence_vault)
    assert "download_url" not in str(evidence_vault)
    assert "raw_access_url" not in str(evidence_vault)
    assert not _contains_unsafe_reference(evidence_vault)


def test_ao12_ct_004_denied_and_redaction_failed_have_safe_next_steps():
    evidence_vault = build_console_snapshot()["consoleData"]["evidenceVault"]
    requests_by_state = {request["status"]: request for request in evidence_vault["requests"]}
    grants_by_status = {grant["status"]: grant for grant in evidence_vault["grants"]}

    assert requests_by_state["redaction_failed"]["primary_action"] == "仅查看哈希告警"
    assert requests_by_state["permission_denied"]["primary_action"] == "补充申请理由"
    assert grants_by_status["redaction_failed"]["expires_at"] == "暂停授权"
    assert grants_by_status["rejected"]["expires_at"] == "未授权"


def test_ao12_ct_005_empty_repository_reports_safe_empty_vault():
    evidence_vault = build_console_snapshot(repository=InMemoryRepository())["consoleData"]["evidenceVault"]

    assert evidence_vault["requests"] == []
    assert evidence_vault["grants"] == []
    assert evidence_vault["auditTrail"] == []
    assert "默认不展示原文" in " ".join(evidence_vault["guardrails"])


def test_ao12_ct_006_degraded_repository_evidence_keeps_raw_access_pending():
    evidence_vault = build_console_snapshot(repository=_repository())["consoleData"]["evidenceVault"]

    assert evidence_vault["requests"][0]["status"] == "pending"
    assert evidence_vault["requests"][0]["primary_action"] == "等待审批"
    assert evidence_vault["requests"][0]["ttl_summary"] == "待补偿"
    assert evidence_vault["grants"][0]["status"] == "pending"
    assert evidence_vault["grants"][0]["scope"] == "待补偿范围"
    assert evidence_vault["grants"][0]["expires_at"] == "待补偿"
    assert evidence_vault["auditTrail"][0]["stage"] == "降级"
    assert evidence_vault["auditTrail"][0]["status"] == "degraded"
