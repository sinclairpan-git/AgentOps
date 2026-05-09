import pytest

from agentops.core.errors import AgentOpsError
from agentops.core.runtime_contracts import (
    CONTRACT_REGISTRY,
    STATE_REGISTRY,
    contract_registry_hash,
    get_contract,
    get_state,
    validate_contract_registry,
    validate_contract_value,
    validate_state_registry,
)


def test_runtime_contract_registry_covers_p0_contracts():
    validate_contract_registry(CONTRACT_REGISTRY)

    expected_contracts = {
        "runtime_run.v1",
        "trace_span.v1",
        "event_envelope.v1",
        "policy_decision.v1",
        "capability_grant.v1",
        "approval.v1",
        "evidence_summary.v1",
        "health_summary.v1",
    }

    assert expected_contracts.issubset(CONTRACT_REGISTRY)
    for contract_id in expected_contracts:
        entry = get_contract(contract_id)
        assert entry.domain_owner
        assert entry.producer
        assert entry.consumers
        assert entry.required_fields
        assert entry.error_codes
        assert entry.contract_tests


def test_contract_registry_rejects_missing_owner():
    broken = dict(CONTRACT_REGISTRY)
    broken["trace_span.v1"] = get_contract("trace_span.v1").with_changes(
        domain_owner=""
    )

    with pytest.raises(AgentOpsError) as exc:
        validate_contract_registry(broken)

    assert exc.value.error_code == "CONTRACT_OWNER_REQUIRED"


def test_contract_registry_rejects_unregistered_enum_value():
    with pytest.raises(AgentOpsError) as exc:
        validate_contract_value("policy_decision.v1", "decision", "maybe")

    assert exc.value.error_code == "CONTRACT_ENUM_UNREGISTERED"


def test_contract_registry_hash_is_stable():
    assert contract_registry_hash(CONTRACT_REGISTRY) == contract_registry_hash(
        CONTRACT_REGISTRY
    )


def test_state_registry_maps_runtime_states_to_actions():
    validate_state_registry(STATE_REGISTRY)

    approval = get_state("approval_paused")
    assert approval.display_name == "等待审批"
    assert approval.primary_action == "查看审批进度"

    trace_pending = get_state("trace_pending")
    assert trace_pending.severity == "warning"
    assert trace_pending.primary_action == "重试上报"


def test_state_registry_rejects_display_mismatch():
    broken = dict(STATE_REGISTRY)
    broken["trace_pending"] = get_state("trace_pending").with_changes(
        expected_display_name="执行链路已上报"
    )

    with pytest.raises(AgentOpsError) as exc:
        validate_state_registry(broken)

    assert exc.value.error_code == "STATE_DISPLAY_MISMATCH"
