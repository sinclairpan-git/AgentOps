from agentops.core.policy_engine import evaluate_policy_check
from tests.contract.test_ao2_ct_001_policy_check import active_grant, policy_request


def test_low_risk_action_allows_without_grant():
    decision = evaluate_policy_check(
        policy_request(
            action="read",
            risk_level="low",
            resource_scope=None,
            skill_id="read.skill",
        )
    )

    assert decision["decision"] == "allow"
    assert decision["fallback_action"] == "allow"


def test_grant_requires_exact_scope_match():
    decision = evaluate_policy_check(
        policy_request(resource_scope={"repo": "AgentOps", "env": "prod", "path": "/secure"}),
        grant=active_grant(),
    )

    assert decision["decision"] == "approval_required"
    assert "grant_id" not in decision


def test_grant_requires_same_requester_and_policy_version():
    decision = evaluate_policy_check(
        policy_request(requester="user_2"),
        grant=active_grant(),
    )

    assert decision["decision"] == "approval_required"
    assert "grant_id" not in decision
