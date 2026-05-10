from __future__ import annotations

from agentops.api.approvals import decide_approval_request
from agentops.api.policy import (
    build_policy_operations_projection,
    register_policy_set_version,
)
from agentops.core.runtime_contracts import get_contract
from tests.contract.test_ao2_ct_002_approval_lifecycle import create_pending_approval


def test_ao36_ct_001_contract_registry_has_approval_operation():
    contract = get_contract("approval_operation.v1")

    assert contract.domain_owner == "AgentOps"
    assert contract.producer == "AgentOps"
    assert {"Ops", "Policy Service"}.issubset(contract.consumers)
    assert {
        "operation_id",
        "approval_id",
        "operation",
        "actor",
        "state_before",
        "state_after",
        "summary",
        "audit_id",
    }.issubset(contract.required_fields)
    assert contract.enum_fields["operation"] == frozenset(
        {
            "request_input",
            "approve",
            "reject",
            "expire",
            "withdraw",
            "escalate",
            "break_glass_approve",
        }
    )
    assert "AO36-CT-002" in contract.contract_tests


def test_ao36_ct_001_contract_registry_has_policy_set_version():
    contract = get_contract("policy_set_version.v1")

    assert contract.domain_owner == "AgentOps"
    assert contract.producer == "Policy Service"
    assert {"Ops", "Runtime", "Agent Store"}.issubset(contract.consumers)
    assert {
        "policy_set_version",
        "state",
        "risk_templates",
        "fallback_action",
        "deny_priority",
        "summary",
        "audit_id",
    }.issubset(contract.required_fields)
    assert contract.enum_fields["state"] == frozenset(
        {"draft", "canary", "active", "rolled_back", "retired"}
    )
    assert "AO36-CT-003" in contract.contract_tests


def test_ao36_ct_001_contract_registry_has_grant_lifecycle():
    contract = get_contract("grant_lifecycle.v1")

    assert contract.domain_owner == "AgentOps"
    assert contract.producer == "Policy Service"
    assert {"Ops", "Runtime", "Agent Store"}.issubset(contract.consumers)
    assert {
        "grant_id",
        "status",
        "binding",
        "remaining_uses",
        "consumption_summary",
        "impact_summary",
        "audit_id",
    }.issubset(contract.required_fields)
    assert contract.enum_fields["status"] == frozenset(
        {"active", "revoked", "expired", "exhausted"}
    )
    assert "AO36-CT-004" in contract.contract_tests


def test_ao36_ct_002_approval_operation_can_request_input(repository):
    approval = create_pending_approval(repository)

    updated = decide_approval_request(
        approval["approval_id"],
        action="request_input",
        actor="security_1",
        reason="Need deployment impact assessment.",
        repository=repository,
        required_materials=["impact_assessment", "rollback_plan"],
        notification_intent={"target": approval["requester"], "channel": "todo"},
    )

    assert updated["status"] == "needs_input"
    assert updated["required_materials"] == ["impact_assessment", "rollback_plan"]
    operation = repository.approval_operation_records()[-1]
    assert operation["operation"] == "request_input"
    assert operation["state_before"] == "pending"
    assert operation["state_after"] == "needs_input"
    assert operation["summary"]["raw_payload_access"] == "forbidden"
    assert operation["notification_intent"]["target"] == approval["requester"]


def test_ao36_ct_002_approval_operation_can_escalate_and_withdraw(repository):
    approval = create_pending_approval(repository)

    escalated = decide_approval_request(
        approval["approval_id"],
        action="escalate",
        actor="system",
        reason="SLA elapsed.",
        repository=repository,
    )
    withdrawn = decide_approval_request(
        approval["approval_id"],
        action="withdraw",
        actor=approval["requester"],
        reason="Runtime run cancelled.",
        repository=repository,
    )

    assert escalated["status"] == "escalated"
    assert escalated["sla_state"] == "escalated"
    assert withdrawn["status"] == "withdrawn"
    operations = repository.approval_operation_records()
    assert [item["operation"] for item in operations[-2:]] == ["escalate", "withdraw"]
    assert operations[-1]["state_before"] == "escalated"
    assert operations[-1]["state_after"] == "withdrawn"


def test_ao36_ct_002_break_glass_approval_requires_audit_reason(repository):
    approval = create_pending_approval(repository)

    approved = decide_approval_request(
        approval["approval_id"],
        action="approve",
        actor=approval["requester"],
        reason="Incident command approved emergency continuation.",
        repository=repository,
        break_glass=True,
        break_glass_reason="incident_commander_override",
    )

    assert approved["status"] == "approved"
    operation = repository.approval_operation_records()[-1]
    assert operation["operation"] == "break_glass_approve"
    assert operation["actor"] == approval["requester"]
    assert operation["break_glass_reason"] == "incident_commander_override"
    assert operation["summary"]["break_glass"] is True


def test_ao36_ct_003_policy_operations_projection_explains_canary(repository):
    register_policy_set_version(
        repository,
        policy_set_version="policy.v3",
        state="canary",
        risk_templates=["deploy_prod", "raw_evidence_access"],
        fallback_action="require_online",
        traffic_scope={"percent": 10, "agents": ["agent_1"]},
        owner="Security/IAM",
    )

    projection = build_policy_operations_projection(repository)

    assert projection["schema_version"] == "policy_set_version.v1"
    assert projection["active_version"] == ""
    assert projection["versions"][0]["policy_set_version"] == "policy.v3"
    assert projection["versions"][0]["state"] == "canary"
    assert projection["versions"][0]["deny_priority"]["deny_overrides_grant"] is True
    assert projection["versions"][0]["fallback_action"] == "require_online"
    assert projection["versions"][0]["summary"]["raw_payload_access"] == "forbidden"


def test_ao36_ct_003_policy_operations_projection_explains_rollback(repository):
    register_policy_set_version(
        repository,
        policy_set_version="policy.v2",
        state="active",
        risk_templates=["deploy_prod"],
        fallback_action="require_online",
    )
    register_policy_set_version(
        repository,
        policy_set_version="policy.v3",
        state="rolled_back",
        risk_templates=["deploy_prod"],
        fallback_action="block",
        rollback_from="policy.v3",
        rollback_reason="elevated false positives",
    )

    projection = build_policy_operations_projection(repository)
    rolled_back = {
        item["policy_set_version"]: item for item in projection["versions"]
    }["policy.v3"]

    assert projection["active_version"] == "policy.v2"
    assert rolled_back["state"] == "rolled_back"
    assert rolled_back["rollback_from"] == "policy.v3"
    assert rolled_back["rollback_reason"] == "elevated false positives"
    assert rolled_back["summary"]["rollback_recorded"] is True
