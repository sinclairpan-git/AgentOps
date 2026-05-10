from __future__ import annotations

from agentops.core.runtime_contracts import get_contract


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
