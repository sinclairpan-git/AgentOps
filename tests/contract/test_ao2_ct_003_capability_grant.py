import pytest

from agentops.api.approvals import decide_approval_request
from agentops.api.grants import consume_grant, issue_grant, revoke_grant
from agentops.core.errors import AgentOpsError
from tests.contract.test_ao2_ct_001_policy_check import policy_request
from tests.contract.test_ao2_ct_002_approval_lifecycle import (
    create_pending_approval,
    grant_request_from_approval,
)


def issue_active_grant(repository, ttl_seconds=900):
    approval = create_pending_approval(repository)
    approved = decide_approval_request(
        approval["approval_id"],
        action="approve",
        actor="security_1",
        reason="approved",
        repository=repository,
    )
    return issue_grant(
        approved["approval_id"],
        grant_request_from_approval(approved),
        repository,
        ttl_seconds=ttl_seconds,
    )


def test_active_grant_can_be_consumed(repository):
    grant = issue_active_grant(repository)

    consumption = consume_grant(
        grant["grant_id"],
        policy_request(policy_check_id=grant["policy_check_id"]),
        repository,
    )

    assert consumption["grant_id"] == grant["grant_id"]
    assert consumption["policy_check_id"] == grant["policy_check_id"]
    assert consumption["consumed_at"]
    assert consumption["audit_id"]


def test_revoked_grant_cannot_be_consumed(repository):
    grant = issue_active_grant(repository)
    revoke_grant(grant["grant_id"], repository)

    with pytest.raises(AgentOpsError) as exc:
        consume_grant(
            grant["grant_id"],
            policy_request(policy_check_id=grant["policy_check_id"]),
            repository,
        )

    assert exc.value.error_code == "GRANT_REVOKED"
    assert exc.value.denied_scope == "grant.status"


def test_expired_grant_cannot_be_consumed(repository):
    grant = issue_active_grant(repository, ttl_seconds=-1)

    with pytest.raises(AgentOpsError) as exc:
        consume_grant(
            grant["grant_id"],
            policy_request(policy_check_id=grant["policy_check_id"]),
            repository,
        )

    assert exc.value.error_code == "GRANT_EXPIRED"
    assert exc.value.denied_scope == "grant.expires_at"


def test_scope_mismatch_grant_cannot_be_consumed(repository):
    grant = issue_active_grant(repository)

    with pytest.raises(AgentOpsError) as exc:
        consume_grant(
            grant["grant_id"],
            policy_request(
                policy_check_id=grant["policy_check_id"],
                resource_scope={"repo": "AgentOps", "env": "staging"},
            ),
            repository,
        )

    assert exc.value.error_code == "GRANT_SCOPE_MISMATCH"
    assert exc.value.denied_scope == "grant.resource_scope"
