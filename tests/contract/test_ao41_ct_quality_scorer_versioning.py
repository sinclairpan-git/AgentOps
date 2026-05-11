from __future__ import annotations

import json

import pytest

from agentops.api.operations import (
    create_eval_case,
    get_quality_scorer_comparison,
    get_quality_scorer_version,
)
from agentops.core.errors import AgentOpsError
from agentops.core.runtime_contracts import get_contract
from agentops.storage.repository import InMemoryRepository
from tests.contract.test_ao32_ct_evidence_health_summary_loop import (
    write_full_trace,
    write_runtime_run,
)


def test_ao41_ct_001_contract_registry_has_scorer_versioning():
    contract_ids = {
        "quality_scorer_version.v1": {
            "scorer_id",
            "scorer_version",
            "score_template_id",
            "rollout_state",
            "required_evidence",
            "input_boundary",
            "summary",
            "audit_id",
        },
        "quality_scorer_comparison.v1": {
            "agent_id",
            "version",
            "source_eval_cases",
            "sample_size",
            "baseline_scorer",
            "candidate_scorer",
            "comparison_state",
            "alignment_delta",
            "safety_impact",
            "recommendation",
            "summary",
            "audit_id",
        },
    }

    for contract_id, required_fields in contract_ids.items():
        contract = get_contract(contract_id)
        assert contract.domain_owner == "AgentOps"
        assert required_fields.issubset(contract.required_fields)
        assert "AO41-CT-001" in contract.contract_tests


def test_ao41_ct_002_scorer_version_declares_summary_only_boundary():
    scorer = get_quality_scorer_version(
        scorer_id="quality_summary_stage5_candidate",
        scorer_version="1.1.0",
        score_template_id="quality_summary_stage5_candidate",
        rollout_state="candidate",
        owner_team="Quality",
        required_evidence=["runtime_run", "runtime_evidence_summary", "eval_case"],
        scoring_policy={"evidence_weight": 24, "failure_sensitivity": 32},
    )

    assert scorer["schema_version"] == "quality_scorer_version.v1"
    assert scorer["rollout_state"] == "candidate"
    assert scorer["input_boundary"]["raw_payload_access"] == "forbidden"
    assert scorer["input_boundary"]["raw_prompt_access"] == "forbidden"
    assert scorer["summary"]["manual_approval_required"] is True
    assert scorer["summary"]["automatic_rollout_enabled"] is False
    assert scorer["summary"]["store_write_performed"] is False
    _assert_no_raw_leaks(scorer)


def test_ao41_ct_002_scorer_version_redacts_unsafe_labels():
    scorer = get_quality_scorer_version(
        scorer_id="HTTPS://example.invalid/raw-scorer",
        scorer_version="token_secret",
        owner_team="credential_secret",
    )

    assert scorer["scorer_id"] == "[redacted]"
    assert scorer["scorer_version"] == "[redacted]"
    assert scorer["owner_team"] == "[redacted]"
    _assert_no_raw_leaks(scorer)


def test_ao41_ct_002_scorer_version_preserves_explicit_zero_weights():
    scorer = get_quality_scorer_version(
        scoring_policy={"evidence_weight": 0, "failure_sensitivity": 0},
    )

    assert scorer["scoring_policy"]["evidence_weight"] == 0
    assert scorer["scoring_policy"]["failure_sensitivity"] == 0
    _assert_no_raw_leaks(scorer)


def test_ao41_ct_003_scorer_comparison_uses_eval_case_summaries_only():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_failed", status="failed")
    write_full_trace(repository, run_id="run_failed")
    create_eval_case(
        repository,
        "run_failed",
        owner_team="Quality",
        expected_behavior="Failure should be classified without raw evidence.",
    )
    write_runtime_run(
        repository,
        run_id="other_failed",
        status="failed",
        agent_id="agent.other",
    )
    create_eval_case(
        repository,
        "other_failed",
        owner_team="Quality",
        expected_behavior="Other agent sample must not leak into comparison.",
    )

    comparison = get_quality_scorer_comparison(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        candidate_scorer={
            "scorer_id": "quality_summary_stage5_candidate",
            "scorer_version": "1.1.0",
            "score_template_id": "quality_summary_stage5_candidate",
            "scoring_policy": {"evidence_weight": 24, "failure_sensitivity": 36},
        },
    )

    assert comparison["schema_version"] == "quality_scorer_comparison.v1"
    assert comparison["source_eval_cases"] == ["eval_case_1"]
    assert comparison["sample_size"] == 1
    assert comparison["comparison_state"] == "ready_for_manual_approval"
    assert comparison["safety_impact"] == "improved"
    assert comparison["recommendation"] == "submit_for_manual_rollout_approval"
    assert comparison["alignment_delta"] > 0
    assert comparison["summary"]["automatic_rollout_enabled"] is False
    assert comparison["summary"]["automatic_template_switch"] is False
    _assert_no_raw_leaks(comparison)


def test_ao41_ct_003_scorer_comparison_treats_empty_required_evidence_as_regression():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_failed", status="failed")
    write_full_trace(repository, run_id="run_failed")
    create_eval_case(
        repository,
        "run_failed",
        owner_team="Quality",
        expected_behavior="Failure should remain evidence-bound.",
    )

    comparison = get_quality_scorer_comparison(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        candidate_scorer={
            "scorer_id": "quality_summary_stage5_candidate",
            "scorer_version": "1.1.0",
            "required_evidence": [],
            "scoring_policy": {"evidence_weight": 0, "failure_sensitivity": 36},
        },
    )

    assert comparison["candidate_scorer"]["scorer_id"] == (
        "quality_summary_stage5_candidate"
    )
    assert comparison["comparison_state"] == "needs_human_review"
    assert comparison["safety_impact"] == "negative"
    assert comparison["recommendation"] == "keep_baseline"
    assert comparison["summary"]["automatic_rollout_enabled"] is False
    assert comparison["summary"]["manual_approval_required"] is True
    _assert_no_raw_leaks(comparison)


def test_ao41_ct_004_scorer_comparison_requires_minimum_eval_cases():
    repository = InMemoryRepository()

    comparison = get_quality_scorer_comparison(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        min_eval_cases=2,
    )

    assert comparison["comparison_state"] == "insufficient_evidence"
    assert comparison["recommendation"] == "collect_more_samples"
    assert comparison["source_eval_cases"] == []
    assert comparison["summary"]["automatic_rollout_enabled"] is False
    _assert_no_raw_leaks(comparison)


def test_ao41_ct_004_scorer_comparison_rejects_invalid_threshold():
    repository = InMemoryRepository()

    with pytest.raises(AgentOpsError) as exc:
        get_quality_scorer_comparison(
            repository,
            "agent.ai-sdlc",
            "1.0.0",
            min_eval_cases=0,
        )

    assert exc.value.error_code == "SCORER_COMPARISON_UNAVAILABLE"
    assert exc.value.denied_scope == "scorer_comparison.min_eval_cases"


def _assert_no_raw_leaks(payload: dict) -> None:
    forbidden_keys = {
        "raw_payload",
        "prompt",
        "raw_prompt",
        "diff",
        "raw_diff",
        "terminal",
        "terminal_output",
        "token_secret",
        "credential_secret",
        "device_key",
        "download_url",
        "raw_url",
        "pr_url",
    }
    forbidden_values = (
        "token_secret",
        "credential_secret",
        "device_key",
        "must not appear",
        "https://example.invalid",
    )
    _assert_no_forbidden_keys(payload, forbidden_keys)
    serialized = json.dumps(payload, ensure_ascii=False).lower()
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
