import pytest

from agentops.api.policy import evaluate_policy_decision
from agentops.core.errors import AgentOpsError


def test_high_risk_action_requires_approval_or_block():
    decision = evaluate_policy_decision(action="deploy", resource_scope={"repo": "AgentOps"})

    assert decision["decision"] in {"approval_required", "block"}
    assert decision["fallback_action"] == "require_online"
    assert decision["policy_version"] == "policy.v1"
    assert decision["audit_id"]


def test_missing_resource_scope_returns_contract_error():
    with pytest.raises(AgentOpsError) as exc:
        evaluate_policy_decision(action="deploy")

    assert exc.value.error_code == "POLICY_SCOPE_REQUIRED"


def test_policy_unknown_for_high_risk_blocks_or_requires_online():
    decision = evaluate_policy_decision(
        action="deploy",
        resource_scope={"repo": "AgentOps"},
        service_available=False,
    )

    assert decision["decision"] == "block"
    assert decision["fallback_action"] == "require_online"
