from __future__ import annotations

import json

import pytest

from agentops.api.operations import (
    create_eval_case,
    get_quality_center_workbench,
)
from agentops.core.errors import AgentOpsError
from agentops.core.runtime_contracts import get_contract
from agentops.storage.repository import InMemoryRepository
from tests.contract.test_ao32_ct_evidence_health_summary_loop import (
    write_full_trace,
    write_runtime_run,
)


def test_ao42_ct_001_contract_registry_has_quality_center_workbench():
    contract = get_contract("quality_center_workbench.v1")

    assert contract.domain_owner == "AgentOps"
    assert {
        "workbench_state",
        "agent_summaries",
        "scorer_rollout_panel",
        "review_queue",
        "trend_summary",
        "summary",
        "audit_id",
    }.issubset(contract.required_fields)
    assert "AO42-CT-001" in contract.contract_tests


def test_ao42_ct_002_quality_center_aggregates_quality_lifecycle_and_scorer():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_failed", status="failed")
    write_full_trace(repository, run_id="run_failed")
    create_eval_case(
        repository,
        "run_failed",
        owner_team="Quality",
        expected_behavior="Failure should be classified without raw evidence.",
    )

    workbench = get_quality_center_workbench(
        repository,
        report_period="2026-05",
        generated_by="quality_lead",
        agent_refs=[
            {
                "agent_id": "agent.ai-sdlc",
                "version": "1.0.0",
                "owner_team": "Quality",
                "candidate_scorer": {
                    "scorer_id": "quality_summary_stage5_candidate",
                    "scorer_version": "1.1.0",
                    "scoring_policy": {
                        "evidence_weight": 24,
                        "failure_sensitivity": 36,
                    },
                },
                "adoption_metrics": {
                    "generated_lines": 100,
                    "retained_lines": 72,
                    "merge_state": "merged",
                    "sampling_review_state": "passed",
                },
            }
        ],
    )

    assert workbench["schema_version"] == "quality_center_workbench.v1"
    assert workbench["workbench_state"] == "ready"
    assert workbench["agent_summaries"][0]["score_template_id"] == (
        "quality_summary_stage5"
    )
    assert workbench["agent_summaries"][0]["scorer"]["scorer_id"] == (
        "quality_summary_stage5_candidate"
    )
    assert (
        workbench["agent_summaries"][0]["scorer_comparison"]["comparison_state"]
        == "ready_for_manual_approval"
    )
    assert workbench["scorer_rollout_panel"]["candidate_count"] == 1
    assert workbench["scorer_rollout_panel"]["ready_for_manual_approval_count"] == 1
    assert workbench["scorer_rollout_panel"]["automatic_rollout_enabled"] is False
    assert workbench["summary"]["store_write_performed"] is False
    assert workbench["summary"]["automatic_lifecycle_action"] is False
    _assert_no_raw_leaks(workbench)


def test_ao42_ct_003_quality_center_routes_manual_review_without_actions():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_sparse", status="failed")
    create_eval_case(
        repository,
        "run_sparse",
        owner_team="Quality",
        expected_behavior="Failure should remain evidence-bound.",
    )

    workbench = get_quality_center_workbench(
        repository,
        report_period="2026-05",
        agent_refs=[
            {
                "agent_id": "agent.ai-sdlc",
                "version": "1.0.0",
                "owner_team": "token_secret HTTPS://example.invalid/team",
                "candidate_scorer": {
                    "scorer_id": "HTTPS://example.invalid/raw-scorer",
                    "required_evidence": [],
                    "scoring_policy": {"evidence_weight": 0},
                },
            }
        ],
    )

    review_types = {item["review_type"] for item in workbench["review_queue"]}
    assert {"quality_evidence", "scorer_rollout", "lifecycle"} <= review_types
    assert all(
        item["manual_review_required"] is True for item in workbench["review_queue"]
    )
    assert all(
        item["automatic_action_performed"] is False
        for item in workbench["review_queue"]
    )
    assert workbench["agent_summaries"][0]["owner_team"] == "[redacted]"
    assert workbench["agent_summaries"][0]["scorer"]["scorer_id"] == "[redacted]"
    assert workbench["scorer_rollout_panel"]["needs_human_review_count"] == 1
    assert workbench["summary"]["automatic_rollout_enabled"] is False
    assert workbench["summary"]["automatic_publish_performed"] is False
    _assert_no_raw_leaks(workbench)


def test_ao42_ct_004_quality_center_empty_and_malformed_inputs():
    repository = InMemoryRepository()

    empty = get_quality_center_workbench(
        repository,
        report_period="2026-05",
        agent_refs=[],
    )
    assert empty["workbench_state"] == "empty"
    assert empty["agent_summaries"] == []
    assert empty["review_queue"] == []

    with pytest.raises(AgentOpsError) as exc:
        get_quality_center_workbench(
            repository,
            report_period="2026-05",
            agent_refs=["bad"],
        )

    assert exc.value.error_code == "QUALITY_CENTER_WORKBENCH_UNAVAILABLE"
    assert exc.value.denied_scope == "agent_refs[0]"


def test_ao42_ct_005_quality_center_queues_insufficient_scorer_evidence():
    repository = InMemoryRepository()

    workbench = get_quality_center_workbench(
        repository,
        report_period="2026-05",
        agent_refs=[
            {
                "agent_id": "agent.ai-sdlc",
                "version": "1.0.0",
                "owner_team": "Quality",
                "min_eval_cases": 2,
            }
        ],
    )

    scorer_items = [
        item
        for item in workbench["review_queue"]
        if item["review_type"] == "scorer_rollout"
    ]
    assert workbench["scorer_rollout_panel"]["insufficient_evidence_count"] == 1
    assert workbench["scorer_rollout_panel"]["manual_approval_queue_size"] == 1
    assert (
        workbench["agent_summaries"][0]["scorer_comparison"]["manual_approval_required"]
        is True
    )
    assert scorer_items[0]["reason"] == "insufficient_evidence"
    assert scorer_items[0]["recommended_action"] == "collect_more_samples"
    assert scorer_items[0]["manual_review_required"] is True
    assert scorer_items[0]["automatic_action_performed"] is False
    _assert_no_raw_leaks(workbench)


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
