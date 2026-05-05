import pytest

from agentops.api.approvals import decide_approval_request
from agentops.core.errors import AgentOpsError
from tests.contract.test_ao2_ct_002_approval_lifecycle import create_pending_approval


def test_terminal_approval_cannot_transition(repository):
    approval = create_pending_approval(repository)
    decide_approval_request(
        approval["approval_id"],
        action="reject",
        actor="security_1",
        reason="not enough evidence",
        repository=repository,
    )

    with pytest.raises(AgentOpsError) as exc:
        decide_approval_request(
            approval["approval_id"],
            action="approve",
            actor="security_2",
            reason="late approve",
            repository=repository,
        )

    assert exc.value.error_code == "APPROVAL_STATE_INVALID"


def test_request_more_info_keeps_approval_non_terminal(repository):
    approval = create_pending_approval(repository)

    updated = decide_approval_request(
        approval["approval_id"],
        action="request_more_info",
        actor="security_1",
        reason="need rollout plan",
        repository=repository,
    )

    assert updated["status"] == "needs_more_info"
