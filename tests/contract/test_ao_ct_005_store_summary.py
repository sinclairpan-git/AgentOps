import pytest

from agentops.api.store_summary import get_agent_store_summary
from agentops.core.errors import AgentOpsError


def evidence_summary():
    return {
        "run_id": "run_1",
        "evidence_level": "L5",
        "confidence": 1.0,
        "missing_evidence": [],
    }


def test_store_summary_contains_required_echo_fields():
    summary = get_agent_store_summary("agent.ai-sdlc", "1.0.0", evidence_summary())

    assert summary["score_template_id"] == "framework-capability-stage1"
    assert summary["evidence_level"] == "L5"
    assert summary["confidence"] == 1.0
    assert summary["missing_evidence"] == []
    assert summary["risk_state"] == "normal"
    assert summary["approval_state"] == "none"
    assert summary["calculated_at"]
    assert summary["valid_until"]
    assert summary["deep_links"]["agent_id"] == "agent.ai-sdlc"
    assert summary["deep_links"]["run_id"] == "run_1"
    assert "raw" not in summary


def test_unsupported_consumer_schema_returns_contract_error():
    with pytest.raises(AgentOpsError) as exc:
        get_agent_store_summary(
            "agent.ai-sdlc",
            "1.0.0",
            evidence_summary(),
            consumer_schema_version="2.0",
        )

    assert exc.value.error_code == "SUMMARY_SCHEMA_UNSUPPORTED"
