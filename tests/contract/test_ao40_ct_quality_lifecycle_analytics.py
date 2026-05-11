from __future__ import annotations

import json

import pytest

from agentops.api.operations import (
    create_eval_case,
    get_adoption_roi_projection,
    get_lifecycle_recommendation,
    get_monthly_quality_report,
    get_quality_score_projection,
)
from agentops.core.errors import AgentOpsError
from agentops.core.runtime_contracts import get_contract
from agentops.storage.repository import InMemoryRepository
from tests.contract.test_ao32_ct_evidence_health_summary_loop import (
    write_full_trace,
    write_runtime_run,
)


def test_ao40_ct_001_contract_registry_has_quality_lifecycle_analytics():
    contract_ids = {
        "quality_score_projection.v1": {
            "agent_id",
            "version",
            "score_template_id",
            "score",
            "quality_state",
            "evidence_level",
            "confidence",
            "missing_evidence",
            "explanation",
            "summary",
            "audit_id",
        },
        "adoption_roi_projection.v1": {
            "agent_id",
            "version",
            "adoption_state",
            "retention_rate",
            "rework_risk",
            "adoption_metrics",
            "review_summary",
            "sampling_review_state",
            "summary",
            "audit_id",
        },
        "lifecycle_recommendation.v1": {
            "agent_id",
            "version",
            "lifecycle_state",
            "recommended_action",
            "owner_notification_state",
            "appeal_state",
            "quality_score",
            "risk_profile",
            "store_governance",
            "summary",
            "audit_id",
        },
        "monthly_quality_report.v1": {
            "report_period",
            "report_state",
            "agent_summaries",
            "trend_summary",
            "summary",
            "audit_id",
        },
    }

    for contract_id, required_fields in contract_ids.items():
        contract = get_contract(contract_id)
        assert contract.domain_owner == "AgentOps"
        assert required_fields.issubset(contract.required_fields)
        assert "AO40-CT-001" in contract.contract_tests


def test_ao40_ct_002_quality_score_keeps_missing_evidence_nonzero_and_manual():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_sparse", status="succeeded")

    score = get_quality_score_projection(repository, "agent.ai-sdlc", "1.0.0")

    assert score["schema_version"] == "quality_score_projection.v1"
    assert score["score"] > 0
    assert "trace_span" in score["missing_evidence"]
    assert "eval_case" in score["missing_evidence"]
    assert score["quality_state"] == "insufficient_evidence"
    assert score["summary"]["missing_evidence_scored_as_zero"] is False
    assert score["summary"]["automatic_lifecycle_action"] is False
    _assert_no_raw_leaks(score)


def test_ao40_ct_002_quality_score_uses_summary_health_and_eval_case():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_failed", status="failed")
    create_eval_case(
        repository,
        "run_failed",
        owner_team="Quality",
        expected_behavior="Failure should become a reviewed eval sample.",
    )
    write_runtime_run(repository, run_id="run_ok", status="succeeded")
    write_full_trace(repository, run_id="run_ok")

    score = get_quality_score_projection(repository, "agent.ai-sdlc", "1.0.0")

    assert score["score_template_id"] == "quality_summary_stage5"
    assert score["evidence_level"] in {"L4", "L5"}
    assert "eval_case" not in score["missing_evidence"]
    assert score["summary"]["raw_prompt_access"] == "forbidden"
    _assert_no_raw_leaks(score)


def test_ao40_ct_002_quality_explanation_uses_latest_evidence_completeness():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_complete", status="succeeded")
    write_full_trace(repository, run_id="run_complete")
    write_runtime_run(repository, run_id="run_latest_sparse", status="succeeded")

    score = get_quality_score_projection(repository, "agent.ai-sdlc", "1.0.0")

    assert score["explanation"]["evidence_completeness"] == 0.0
    assert score["explanation"]["health_window_evidence_completeness"] > 0.0
    assert "trace_span" in score["missing_evidence"]
    _assert_no_raw_leaks(score)


def test_ao40_ct_003_adoption_roi_is_summary_only_and_redacts_unsafe_labels():
    projection = get_adoption_roi_projection(
        agent_id="agent.ai-sdlc",
        version="1.0.0",
        owner_team="Platform",
        adoption_metrics={
            "generated_lines": 100,
            "retained_lines": 72,
            "modified_lines": 18,
            "deleted_lines": 10,
            "rework_rounds": 1,
            "pr_review_issue_count": 2,
            "ci_failure_types": ["unit", "HTTPS://example.invalid/raw-diff"],
            "merge_state": "merged",
            "rollback_count": 0,
            "sampling_review_state": "passed",
            "raw_diff": "must not appear",
            "prompt": "must not appear",
        },
    )

    assert projection["schema_version"] == "adoption_roi_projection.v1"
    assert projection["retention_rate"] == 0.72
    assert projection["rework_risk"] == "high"
    assert projection["adoption_state"] == "needs_review"
    assert "[redacted]" in projection["review_summary"]["ci_failure_types"]
    assert projection["summary"]["raw_diff_access"] == "forbidden"
    _assert_no_raw_leaks(projection)


def test_ao40_ct_003_adoption_waits_for_sampling_review_before_adopted():
    projection = get_adoption_roi_projection(
        agent_id="agent.ai-sdlc",
        version="1.0.0",
        adoption_metrics={
            "generated_lines": 100,
            "retained_lines": 80,
            "merge_state": "merged",
            "sampling_review_state": "pending",
        },
    )

    assert projection["adoption_state"] == "watching"
    assert projection["summary"]["requires_sampling_review"] is True
    _assert_no_raw_leaks(projection)


def test_ao40_ct_003_adoption_normalizes_merge_state_for_adopted_samples():
    projection = get_adoption_roi_projection(
        agent_id="agent.ai-sdlc",
        version="1.0.0",
        adoption_metrics={
            "generated_lines": 100,
            "retained_lines": 80,
            "merge_state": "MERGED",
            "sampling_review_state": "passed",
        },
    )

    assert projection["adoption_state"] == "adopted"
    assert projection["review_summary"]["merge_state"] == "merged"
    _assert_no_raw_leaks(projection)


def test_ao40_ct_003_adoption_redacts_owner_team_label():
    projection = get_adoption_roi_projection(
        agent_id="agent.ai-sdlc",
        version="1.0.0",
        owner_team="token_secret https://example.invalid/team",
        adoption_metrics={
            "generated_lines": 100,
            "retained_lines": 80,
            "merge_state": "merged",
            "sampling_review_state": "passed",
        },
    )

    assert projection["owner_team"] == "[redacted]"
    _assert_no_raw_leaks(projection)


def test_ao40_ct_004_lifecycle_recommendation_never_executes_store_action():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_blocked", status="blocked")

    recommendation = get_lifecycle_recommendation(repository, "agent.ai-sdlc", "1.0.0")

    assert recommendation["schema_version"] == "lifecycle_recommendation.v1"
    assert recommendation["recommended_action"] in {
        "collect_more_evidence",
        "open_disable_review",
    }
    assert recommendation["summary"]["automatic_lifecycle_action"] is False
    assert recommendation["summary"]["store_write_performed"] is False
    assert recommendation["summary"]["notification_sent"] is False
    _assert_no_raw_leaks(recommendation)


def test_ao40_ct_005_monthly_report_aggregates_quality_and_adoption():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_ok", status="succeeded")
    write_full_trace(repository, run_id="run_ok")

    report = get_monthly_quality_report(
        repository,
        report_period="2026-05",
        generated_by="ops_1",
        agent_refs=[
            {
                "agent_id": "agent.ai-sdlc",
                "version": "1.0.0",
                "owner_team": "Platform",
                "adoption_metrics": {
                    "generated_lines": 50,
                    "retained_lines": 40,
                    "merge_state": "merged",
                    "sampling_review_state": "passed",
                },
            }
        ],
    )

    assert report["schema_version"] == "monthly_quality_report.v1"
    assert report["report_state"] == "ready"
    assert report["trend_summary"]["agent_count"] == 1
    assert report["agent_summaries"][0]["adoption_state"] == "adopted"
    assert report["summary"]["automatic_publish_performed"] is False
    assert report["summary"]["store_write_performed"] is False
    _assert_no_raw_leaks(report)


def test_ao40_ct_005_monthly_report_rejects_malformed_agent_refs():
    repository = InMemoryRepository()

    with pytest.raises(AgentOpsError) as exc_info:
        get_monthly_quality_report(
            repository,
            report_period="2026-05",
            agent_refs=["bad"],
        )

    assert exc_info.value.error_code == "MONTHLY_REPORT_UNAVAILABLE"
    assert exc_info.value.denied_scope == "agent_refs[0]"


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
