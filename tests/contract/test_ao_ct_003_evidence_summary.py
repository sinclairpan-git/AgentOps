import pytest

from agentops.api.evidence import get_evidence_summary
from agentops.core.errors import AgentOpsError


def l5_evaluation():
    return {
        "evidence_level": "L5",
        "missing_evidence": [],
        "downgrade_reason": "",
    }


def test_evidence_summary_outputs_redacted_governance_fields():
    summary = get_evidence_summary("run_1", l5_evaluation(), linked_event_ids=["evt_1"])

    assert summary["run_id"] == "run_1"
    assert summary["evidence_level"] == "L5"
    assert summary["raw_access_state"] == "summary_only"
    assert summary["data_classification"] == "internal"
    assert summary["redaction_policy"] == "repo_default"
    assert summary["access_policy"] == "evidence-vault-approval"
    assert summary["retention_policy"] == "default-90d"
    assert summary["source_trust"] == "verified"
    assert summary["completeness"] == 1.0
    assert summary["freshness"] == "fresh"
    assert summary["linked_event_ids"] == ["evt_1"]


def test_raw_access_denied_uses_contract_error():
    with pytest.raises(AgentOpsError) as exc:
        get_evidence_summary("run_1", l5_evaluation(), request_raw=True)

    assert exc.value.error_code == "RAW_ACCESS_DENIED"
    assert exc.value.denied_scope == "evidence.raw"
