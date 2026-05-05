import pytest

from agentops.api.policy import evaluate_policy_check
from agentops.core.errors import AgentOpsError
from tests.contract.conftest import future_time


def policy_request(**overrides):
    request = {
        "action": "deploy",
        "risk_level": "high",
        "resource_scope": {"repo": "AgentOps", "env": "prod"},
        "requester": "user_1",
        "agent_id": "agent.ai-sdlc",
        "agent_version": "1.0.0",
        "skill_id": "deploy.skill",
        "session_id": "sess_1",
        "run_id": "run_1",
        "policy_version": "policy.v2",
        "enforcement_mode": "enforce",
    }
    request.update(overrides)
    return request


def active_grant(**overrides):
    grant = {
        "grant_id": "grant_1",
        "approval_id": "approval_1",
        "policy_check_id": "pcheck_1",
        "action": "deploy",
        "requester": "user_1",
        "agent_id": "agent.ai-sdlc",
        "skill_id": "deploy.skill",
        "resource_scope": {"repo": "AgentOps", "env": "prod"},
        "policy_version": "policy.v2",
        "issued_at": future_time(-1),
        "expires_at": future_time(),
        "status": "active",
        "audit_id": "audit_grant_1",
    }
    grant.update(overrides)
    return grant


def test_active_grant_returns_conditional_allow():
    decision = evaluate_policy_check(policy_request(), grant=active_grant())

    assert decision["decision"] == "conditional_allow"
    assert decision["fallback_action"] == "allow"
    assert decision["policy_state_known"] is True
    assert decision["grant_id"] == "grant_1"
    assert decision["valid_until"]
    assert decision["audit_id"]


def test_high_risk_action_requires_resource_scope():
    with pytest.raises(AgentOpsError) as exc:
        evaluate_policy_check(policy_request(resource_scope=None))

    assert exc.value.error_code == "POLICY_SCOPE_REQUIRED"
    assert exc.value.denied_scope == "policy.resource_scope"


def test_policy_unavailable_blocks_high_risk_action():
    decision = evaluate_policy_check(policy_request(), service_available=False)

    assert decision["decision"] == "block"
    assert decision["fallback_action"] == "require_online"
    assert decision["policy_state_known"] is False
    assert decision["denied_scope"] == "policy.service_unavailable"


@pytest.mark.parametrize(
    "deny_signal",
    [
        "global_deny",
        "iam_or_security_deny",
        "project_scope_deny",
        "agent_or_version_disabled",
        "policy_block",
    ],
)
def test_priority_deny_overrides_active_grant(deny_signal):
    decision = evaluate_policy_check(
        policy_request(),
        grant=active_grant(),
        governance_signals={deny_signal: True},
    )

    assert decision["decision"] == "block"
    assert decision["fallback_action"] == "block"
    assert decision["policy_state_known"] is True
    assert decision["denied_scope"] == deny_signal
    assert "grant_id" not in decision
