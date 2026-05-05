import pytest

from agentops.api.evidence_vault import approve_raw_access, get_evidence_vault_summary, request_raw_access
from agentops.core.errors import AgentOpsError


def summary_kwargs(**overrides):
    kwargs = {
        "evidence_id": "ev_1",
        "run_id": "run_1",
        "payload_hash": "sha256:evidence",
        "redacted_summary": {"finding": "deployment evidence available"},
    }
    kwargs.update(overrides)
    return kwargs


def test_evidence_vault_summary_never_returns_raw_payload():
    summary = get_evidence_vault_summary(**summary_kwargs())

    assert summary["raw_access_state"] == "summary_only"
    assert summary["redacted_summary"]["finding"]
    assert summary["payload_hash"] == "sha256:evidence"
    assert summary["access_policy"] == "evidence-vault-approval"
    assert summary["audit_id"]
    assert "raw_payload" not in summary


def test_raw_access_denied_without_grant():
    with pytest.raises(AgentOpsError) as exc:
        get_evidence_vault_summary(**summary_kwargs(request_raw=True))

    assert exc.value.error_code == "RAW_ACCESS_DENIED"
    assert exc.value.denied_scope == "evidence.raw"


def test_approved_raw_access_returns_limited_access_state(repository):
    request = request_raw_access(
        repository,
        evidence_id="ev_1",
        requester="user_1",
        reason="incident review",
        approver_scope="iam.security",
        ttl_seconds=300,
    )
    grant = approve_raw_access(request["request_id"], repository)

    summary = get_evidence_vault_summary(**summary_kwargs(raw_access_grant=grant, requester="user_1", request_raw=True))

    assert summary["raw_access_state"] == "approved"
    assert summary["redaction_state"] == "ok"
    assert "raw_payload" not in summary


def test_expired_raw_access_grant_returns_contract_error(repository):
    request = request_raw_access(
        repository,
        evidence_id="ev_1",
        requester="user_1",
        reason="incident review",
        approver_scope="iam.security",
        ttl_seconds=-1,
    )
    grant = approve_raw_access(request["request_id"], repository)

    with pytest.raises(AgentOpsError) as exc:
        get_evidence_vault_summary(**summary_kwargs(raw_access_grant=grant, requester="user_1", request_raw=True))

    assert exc.value.error_code == "RAW_ACCESS_EXPIRED"


def test_raw_access_grant_must_match_evidence_and_requester(repository):
    request = request_raw_access(
        repository,
        evidence_id="ev_other",
        requester="user_other",
        reason="incident review",
        approver_scope="iam.security",
        ttl_seconds=300,
    )
    grant = approve_raw_access(request["request_id"], repository)

    with pytest.raises(AgentOpsError) as exc:
        get_evidence_vault_summary(**summary_kwargs(raw_access_grant=grant, requester="user_1", request_raw=True))

    assert exc.value.error_code == "RAW_ACCESS_DENIED"


def test_redaction_failed_returns_safe_empty_without_summary_or_raw():
    summary = get_evidence_vault_summary(**summary_kwargs(redaction_state="failed"))

    assert summary["raw_access_state"] == "redaction_failed"
    assert summary["redaction_state"] == "failed"
    assert summary["safe_empty"] is True
    assert summary["payload_hash"] == "sha256:evidence"
    assert "redacted_summary" not in summary
    assert "raw_payload" not in summary
