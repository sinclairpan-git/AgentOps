from __future__ import annotations

import json

import pytest

from agentops.api.operations import (
    create_eval_case,
    create_experiment_plan,
    create_safe_replay_plan,
    get_optimizer_recommendation,
    get_policy_simulation_projection,
)
from agentops.core.errors import AgentOpsError
from agentops.core.runtime_contracts import get_contract
from agentops.storage.repository import InMemoryRepository
from tests.contract.test_ao32_ct_evidence_health_summary_loop import (
    write_full_trace,
    write_runtime_run,
)


def test_ao38_ct_001_contract_registry_has_p2_a_operations():
    contract_ids = {
        "safe_replay_plan.v1": {
            "replay_plan_id",
            "source_run",
            "sandbox_profile",
            "replay_mode",
            "execution_state",
            "summary",
            "audit_id",
        },
        "experiment_plan.v1": {
            "experiment_plan_id",
            "agent_id",
            "version",
            "variants",
            "rollout_state",
            "summary",
            "audit_id",
        },
        "optimizer_recommendation.v1": {
            "agent_id",
            "version",
            "source_eval_cases",
            "recommendation_state",
            "recommended_action",
            "summary",
            "audit_id",
        },
        "policy_simulation_projection.v1": {
            "policy_set_version",
            "proposed_change",
            "sample_run_ids",
            "simulation_state",
            "decision_impact_summary",
            "summary",
            "audit_id",
        },
    }

    for contract_id, required_fields in contract_ids.items():
        contract = get_contract(contract_id)
        assert contract.domain_owner in {"AgentOps", "Policy Service"}
        assert required_fields.issubset(contract.required_fields)
        assert "AO38-CT-001" in contract.contract_tests


def test_ao38_ct_002_safe_replay_plan_is_simulation_only():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_failed", status="failed")
    write_full_trace(repository, run_id="run_failed")

    plan = create_safe_replay_plan(
        repository,
        "run_failed",
        created_by="ops_1",
        reason="Reproduce failure with isolated references only.",
    )

    assert plan["schema_version"] == "safe_replay_plan.v1"
    assert plan["source_run"]["run_id"] == "run_failed"
    assert plan["replay_mode"] == "simulation_only"
    assert plan["execution_state"] == "not_started"
    assert plan["summary"]["runtime_execution_performed"] is False
    assert plan["summary"]["external_side_effects_enabled"] is False
    assert plan["summary"]["raw_payload_access"] == "forbidden"
    _assert_no_raw_leaks(plan)


def test_ao38_ct_002_running_run_cannot_seed_safe_replay():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_active", status="running")

    with pytest.raises(AgentOpsError) as exc:
        create_safe_replay_plan(
            repository,
            "run_active",
            created_by="ops_1",
            reason="Cannot replay a live run.",
        )

    assert exc.value.error_code == "REPLAY_SOURCE_NOT_TERMINAL"


def test_ao38_ct_003_experiment_plan_keeps_variant_material_by_ref():
    repository = InMemoryRepository()

    plan = create_experiment_plan(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        owner_team="Quality",
        hypothesis="Compare safer model config against current baseline.",
        variants=[
            {
                "variant_id": "baseline",
                "variant_type": "model",
                "risk_level": "low",
                "config_ref": "store://agents/agent.ai-sdlc/1.0.0/baseline",
                "config": {
                    "raw_payload": "must not appear",
                    "token_secret": "must not appear",
                },
            },
            {
                "variant_id": "candidate",
                "variant_type": "tool",
                "risk_level": "medium",
                "artifact_ref": "store://agents/agent.ai-sdlc/1.0.0/candidate",
            },
        ],
    )

    assert plan["schema_version"] == "experiment_plan.v1"
    assert plan["rollout_state"] == "planning"
    assert plan["summary"]["external_execution_enabled"] is False
    assert plan["summary"]["automatic_rollout_enabled"] is False
    assert plan["variants"][0]["config_hash"].startswith("sha256:")
    assert "config" not in plan["variants"][0]
    _assert_no_raw_leaks(plan)


def test_ao38_ct_004_optimizer_uses_eval_case_summaries_only():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_failed", status="failed")
    create_eval_case(
        repository,
        "run_failed",
        owner_team="Quality",
        expected_behavior="Failure should be classified and handled.",
    )

    recommendation = get_optimizer_recommendation(repository, "agent.ai-sdlc", "1.0.0")

    assert recommendation["schema_version"] == "optimizer_recommendation.v1"
    assert recommendation["recommendation_state"] == "ready"
    assert recommendation["recommended_action"] == "prepare_experiment"
    assert recommendation["source_eval_cases"] == ["eval_case_1"]
    assert recommendation["summary"]["runtime_execution_performed"] is False
    assert recommendation["summary"]["automatic_config_rewrite"] is False
    _assert_no_raw_leaks(recommendation)


def test_ao38_ct_004_optimizer_requests_more_samples_when_evidence_is_missing():
    repository = InMemoryRepository()

    recommendation = get_optimizer_recommendation(repository, "agent.ai-sdlc", "1.0.0")

    assert recommendation["recommendation_state"] == "insufficient_evidence"
    assert recommendation["recommended_action"] == "collect_more_samples"
    assert recommendation["source_eval_cases"] == []


def test_ao38_ct_005_policy_simulation_is_dry_run_projection():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_success", status="succeeded")
    write_runtime_run(repository, run_id="run_blocked", status="blocked")

    projection = get_policy_simulation_projection(
        repository,
        policy_set_version="policy.v2",
        proposed_change={
            "change_type": "tighten_policy",
            "policy_ref": "policy://sets/policy.v2",
            "risk_level": "high",
            "token_secret": "must not appear",
        },
        sample_run_ids=["run_success", "run_blocked", "missing_run"],
        requested_by="policy_owner",
    )

    assert projection["schema_version"] == "policy_simulation_projection.v1"
    assert projection["simulation_state"] == "projected"
    assert projection["sample_run_ids"] == ["run_success", "run_blocked"]
    assert projection["decision_impact_summary"]["sample_size"] == 2
    assert projection["decision_impact_summary"]["blocked_or_failed"] == 1
    assert projection["decision_impact_summary"]["projected_policy_publish"] is False
    assert projection["summary"]["dry_run_only"] is True
    assert projection["summary"]["policy_publish_performed"] is False
    _assert_no_raw_leaks(projection)


def test_ao38_ct_005_policy_simulation_rejects_unsupported_change_type():
    repository = InMemoryRepository()

    with pytest.raises(AgentOpsError) as exc:
        get_policy_simulation_projection(
            repository,
            policy_set_version="policy.v2",
            proposed_change={"change_type": "publish_now"},
            sample_run_ids=[],
            requested_by="policy_owner",
        )

    assert exc.value.error_code == "POLICY_SIMULATION_UNSUPPORTED_ACTION"


def _assert_no_raw_leaks(payload: dict) -> None:
    forbidden_keys = {
        "raw_payload",
        "prompt",
        "token_secret",
        "credential_secret",
        "device_key",
        "download_url",
        "raw_url",
        "config",
        "payload",
    }
    forbidden_values = (
        "token_secret",
        "credential_secret",
        "device_key",
        "must not appear",
    )
    _assert_no_forbidden_keys(payload, forbidden_keys)
    serialized = json.dumps(payload, ensure_ascii=False)
    for marker in forbidden_values:
        assert marker not in serialized


def _assert_no_forbidden_keys(value, forbidden_keys: set[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            assert key not in forbidden_keys
            _assert_no_forbidden_keys(child, forbidden_keys)
    elif isinstance(value, list):
        for child in value:
            _assert_no_forbidden_keys(child, forbidden_keys)
