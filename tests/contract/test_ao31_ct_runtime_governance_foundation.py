import pytest

from agentops.core.errors import AgentOpsError
from agentops.core.runtime_contracts import (
    CONTRACT_REGISTRY,
    STATE_REGISTRY,
    contract_registry_hash,
    get_contract,
    validate_contract_registry,
    validate_contract_value,
    validate_state_registry,
)


def test_ao31_ct_001_contract_registry_has_required_runtime_governance_entries():
    validate_contract_registry(CONTRACT_REGISTRY)

    runtime_run = get_contract("runtime_run.v1")
    trace_span = get_contract("trace_span.v1")

    assert runtime_run.domain_owner == "Agent Runtime"
    assert runtime_run.producer == "Runtime"
    assert "AgentOps" in runtime_run.consumers
    assert {"runtime_id", "run_id", "status"}.issubset(runtime_run.required_fields)
    assert "AO31-CT-003" in runtime_run.contract_tests

    assert trace_span.domain_owner == "Agent Runtime"
    assert {"trace_id", "span_id", "span_kind", "status_code"}.issubset(
        trace_span.required_fields
    )
    assert "AO31-CT-004" in trace_span.contract_tests


def test_ao31_ct_001_missing_owner_returns_contract_owner_required():
    broken = dict(CONTRACT_REGISTRY)
    broken["runtime_run.v1"] = get_contract("runtime_run.v1").with_changes(
        domain_owner=""
    )

    with pytest.raises(AgentOpsError) as exc:
        validate_contract_registry(broken)

    assert exc.value.error_code == "CONTRACT_OWNER_REQUIRED"


def test_ao31_ct_001_repeated_load_has_stable_hash():
    assert contract_registry_hash(CONTRACT_REGISTRY) == contract_registry_hash(
        CONTRACT_REGISTRY
    )


def test_ao31_ct_001_unknown_policy_decision_enum_is_rejected():
    with pytest.raises(AgentOpsError) as exc:
        validate_contract_value("policy_decision.v1", "decision", "defer")

    assert exc.value.error_code == "CONTRACT_ENUM_UNREGISTERED"


def test_ao31_ct_008_state_registry_has_plain_language_actions():
    validate_state_registry(STATE_REGISTRY)

    assert STATE_REGISTRY["running"].display_name == "运行中"
    assert STATE_REGISTRY["blocked"].primary_action == "查看原因"
    assert STATE_REGISTRY["trace_pending"].plain_language_explanation
    assert STATE_REGISTRY["degraded"].severity == "warning"


def test_ao31_ct_008_state_display_mismatch_is_rejected():
    broken = dict(STATE_REGISTRY)
    broken["blocked"] = STATE_REGISTRY["blocked"].with_changes(
        expected_display_name="已通过"
    )

    with pytest.raises(AgentOpsError) as exc:
        validate_state_registry(broken)

    assert exc.value.error_code == "STATE_DISPLAY_MISMATCH"
