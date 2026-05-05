import pytest

from agentops.api.grants import issue_grant
from agentops.core.errors import AgentOpsError
from tests.contract.test_ao2_ct_002_approval_lifecycle import create_pending_approval, grant_request_from_approval
from agentops.api.approvals import decide_approval_request


def approved_approval(repository):
    approval = create_pending_approval(repository)
    return decide_approval_request(
        approval["approval_id"],
        action="approve",
        actor="security_1",
        reason="approved",
        repository=repository,
    )


def test_grant_binding_rejects_action_replacement(repository):
    approval = approved_approval(repository)

    with pytest.raises(AgentOpsError) as exc:
        issue_grant(approval["approval_id"], grant_request_from_approval(approval, action="network"), repository)

    assert exc.value.error_code == "GRANT_APPROVAL_BINDING_MISMATCH"


def test_grant_binding_rejects_requester_replacement(repository):
    approval = approved_approval(repository)

    with pytest.raises(AgentOpsError) as exc:
        issue_grant(approval["approval_id"], grant_request_from_approval(approval, requester="user_2"), repository)

    assert exc.value.error_code == "GRANT_APPROVAL_BINDING_MISMATCH"
