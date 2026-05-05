import pytest

from agentops.api.policy import build_policy_requirement_summary, evaluate_policy_check
from agentops.core.errors import AgentOpsError
from tests.contract.test_ao2_ct_001_policy_check import policy_request


def test_policy_requirement_summary_has_actionable_store_cli_fields():
    decision = evaluate_policy_check(policy_request())

    summary = build_policy_requirement_summary(
        decision,
        affected_actions=["deploy"],
        return_url="/store/agents/agent.ai-sdlc",
    )

    assert summary["required_by"] == "AgentOps Policy Service"
    assert summary["source"] == "agentops.policy_check"
    assert summary["issuer"] == "AgentOps"
    assert summary["policy_owner"] == "Security/IAM"
    assert summary["policy_version"] == "policy.v2"
    assert summary["can_ignore"] is False
    assert summary["affected_actions"] == ["deploy"]
    assert summary["plain_language"]
    assert summary["primary_action"]
    assert summary["secondary_action"]
    assert set(summary["deep_links"]) == {"approval_url", "policy_url", "evidence_url", "return_url"}


def test_warn_policy_summary_can_be_ignored():
    summary = build_policy_requirement_summary(
        {
            "decision": "warn",
            "policy_version": "policy.v2",
            "audit_id": "audit_warn",
        },
        affected_actions=["read"],
    )

    assert summary["can_ignore"] is True


def test_policy_summary_schema_unsupported_returns_contract_error():
    with pytest.raises(AgentOpsError) as exc:
        build_policy_requirement_summary(
            {"decision": "approval_required", "policy_version": "policy.v2", "audit_id": "audit_1"},
            affected_actions=["deploy"],
            consumer_schema_version="policy-summary.v2",
        )

    assert exc.value.error_code == "POLICY_SUMMARY_SCHEMA_UNSUPPORTED"
    assert exc.value.request_id == "req_policy_summary_schema"
