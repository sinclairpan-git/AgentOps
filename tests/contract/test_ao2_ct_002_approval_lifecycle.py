import pytest

from agentops.api.approvals import create_approval_request, decide_approval_request
from agentops.api.grants import issue_grant
from agentops.api.policy import evaluate_policy_check
from agentops.core.errors import AgentOpsError
from tests.contract.test_ao2_ct_001_policy_check import policy_request


def create_pending_approval(repository):
    request = policy_request()
    decision = evaluate_policy_check(request)
    return create_approval_request(
        request,
        decision,
        repository,
        approver_scope="iam.security",
        reason="Production deploy requires review.",
        supplemental_materials=["runbook://deploy"],
    )


def grant_request_from_approval(approval, **overrides):
    request = {
        "policy_check_id": approval["policy_check_id"],
        "action": approval["action"],
        "requester": approval["requester"],
        "agent_id": approval["agent_id"],
        "skill_id": approval["skill_id"],
        "resource_scope": dict(approval["resource_scope"]),
        "policy_version": approval["policy_version"],
    }
    request.update(overrides)
    return request


def test_approval_required_creates_approval(repository):
    approval = create_pending_approval(repository)

    assert approval["status"] == "pending"
    assert approval["requester"] == "user_1"
    assert approval["approver_scope"] == "iam.security"
    assert approval["reason"]
    assert approval["affected_actions"] == ["deploy"]
    assert approval["sla_due_at"]
    assert approval["audit_id"]


def test_requester_cannot_self_approve(repository):
    approval = create_pending_approval(repository)

    with pytest.raises(AgentOpsError) as exc:
        decide_approval_request(
            approval["approval_id"],
            action="approve",
            actor="user_1",
            reason="self approve",
            repository=repository,
        )

    assert exc.value.error_code == "APPROVAL_SELF_APPROVAL_DENIED"
    assert exc.value.denied_scope == "approval.self"


def test_approved_approval_can_issue_bound_grant(repository):
    approval = create_pending_approval(repository)
    approved = decide_approval_request(
        approval["approval_id"],
        action="approve",
        actor="security_1",
        reason="approved for deploy",
        repository=repository,
    )

    grant = issue_grant(
        approval["approval_id"], grant_request_from_approval(approved), repository
    )

    assert grant["status"] == "active"
    assert grant["approval_id"] == approval["approval_id"]
    assert grant["policy_check_id"] == approval["policy_check_id"]
    assert grant["resource_scope"] == approval["resource_scope"]
    assert grant["policy_version"] == approval["policy_version"]
    assert grant["requester"] == approval["requester"]


def test_expired_approval_cannot_issue_grant(repository):
    approval = create_pending_approval(repository)
    expired = decide_approval_request(
        approval["approval_id"],
        action="expire",
        actor="system",
        reason="sla elapsed",
        repository=repository,
    )

    with pytest.raises(AgentOpsError) as exc:
        issue_grant(
            expired["approval_id"], grant_request_from_approval(expired), repository
        )

    assert exc.value.error_code == "GRANT_APPROVAL_NOT_APPROVED"


def test_grant_cannot_expand_approval_scope(repository):
    approval = create_pending_approval(repository)
    approved = decide_approval_request(
        approval["approval_id"],
        action="approve",
        actor="security_1",
        reason="approved for deploy",
        repository=repository,
    )
    expanded_scope = {"repo": "AgentOps", "env": "prod", "namespace": "*"}

    with pytest.raises(AgentOpsError) as exc:
        issue_grant(
            approved["approval_id"],
            grant_request_from_approval(approved, resource_scope=expanded_scope),
            repository,
        )

    assert exc.value.error_code == "GRANT_SCOPE_ESCALATION_DENIED"
