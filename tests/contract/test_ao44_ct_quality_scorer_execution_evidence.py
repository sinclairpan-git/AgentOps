from __future__ import annotations

import json

import pytest

from agentops.api.operations import (
    create_eval_case,
    create_quality_scorer_execution,
    get_quality_center_workbench,
)
from agentops.core.errors import AgentOpsError
from agentops.core.runtime_contracts import get_contract
from agentops.storage.repository import InMemoryRepository
from tests.contract.test_ao32_ct_evidence_health_summary_loop import (
    write_full_trace,
    write_runtime_run,
)


def test_ao44_ct_001_contract_registry_has_scorer_execution():
    contract = get_contract("quality_scorer_execution.v1")

    assert contract.domain_owner == "AgentOps"
    assert {
        "agent_id",
        "version",
        "scorer",
        "source_eval_cases",
        "sample_size",
        "execution_state",
        "outcome_counts",
        "pass_rate",
        "score_summary",
        "evidence_window",
        "recommendation",
        "summary",
        "audit_id",
    }.issubset(contract.required_fields)
    assert "AO44-CT-001" in contract.contract_tests


def test_ao44_ct_002_scorer_execution_records_summary_only_passed_result():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_failed", status="failed")
    write_full_trace(repository, run_id="run_failed")
    create_eval_case(
        repository,
        "run_failed",
        owner_team="Quality",
        expected_behavior="Classify the failure using summary evidence.",
    )

    execution = create_quality_scorer_execution(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        pass_threshold=0.7,
        scorer={
            "scorer_id": "quality_summary_stage5_candidate",
            "scorer_version": "1.1.0",
        },
    )

    assert execution["schema_version"] == "quality_scorer_execution.v1"
    assert execution["execution_id"] == "quality_scorer_execution_1"
    assert execution["execution_state"] == "passed"
    assert execution["sample_size"] == 1
    assert execution["pass_rate"] == 1.0
    assert execution["summary"]["summary_only_execution"] is True
    assert execution["summary"]["external_scorer_invoked"] is False
    assert execution["summary"]["automatic_rollout_enabled"] is False
    assert execution["summary"]["store_write_performed"] is False
    assert (
        repository.quality_scorer_execution_records(
            "agent.ai-sdlc",
            "1.0.0",
            scorer_id="quality_summary_stage5_candidate",
            scorer_version="1.1.0",
        )[0]["execution_id"]
        == "quality_scorer_execution_1"
    )
    _assert_no_raw_leaks(execution)


def test_ao44_ct_003_scorer_execution_requires_positive_evidence_threshold():
    repository = InMemoryRepository()

    with pytest.raises(AgentOpsError) as exc:
        create_quality_scorer_execution(
            repository,
            "agent.ai-sdlc",
            "1.0.0",
            min_eval_cases=0,
        )

    assert exc.value.error_code == "QUALITY_SCORER_EXECUTION_UNAVAILABLE"
    assert exc.value.denied_scope == "scorer_execution.min_eval_cases"


def test_ao44_ct_004_sparse_or_unsafe_execution_stays_manual_and_redacted():
    repository = InMemoryRepository()

    execution = create_quality_scorer_execution(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        min_eval_cases=2,
        scorer={
            "scorer_id": "https://example.invalid/token_secret",
            "scorer_version": "1.1.0",
        },
        executed_by="device_key HTTPS://example.invalid/operator",
    )

    assert execution["execution_state"] == "insufficient_evidence"
    assert execution["recommendation"] == "collect_more_samples"
    assert execution["scorer"]["scorer_id"] == "[redacted]"
    assert execution["executed_by"] == "[redacted]"
    assert execution["summary"]["manual_approval_required"] is True
    assert execution["summary"]["automatic_lifecycle_action"] is False
    assert execution["summary"]["notification_sent"] is False
    _assert_no_raw_leaks(execution)


def test_ao44_ct_005_quality_center_aggregates_latest_execution_evidence():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_failed", status="failed")
    write_full_trace(repository, run_id="run_failed")
    create_eval_case(
        repository,
        "run_failed",
        owner_team="Quality",
        expected_behavior="Classify failure from redacted summary.",
    )
    create_quality_scorer_execution(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        pass_threshold=0.7,
        scorer={
            "scorer_id": "quality_summary_stage5_candidate",
            "scorer_version": "1.1.0",
        },
    )

    workbench = get_quality_center_workbench(
        repository,
        report_period="2026-05",
        agent_refs=[
            {
                "agent_id": "agent.ai-sdlc",
                "version": "1.0.0",
                "owner_team": "Quality",
                "candidate_scorer": {
                    "scorer_id": "quality_summary_stage5_candidate",
                    "scorer_version": "1.1.0",
                },
            }
        ],
    )

    execution_summary = workbench["agent_summaries"][0]["scorer_execution"]
    assert execution_summary["execution_state"] == "passed"
    assert execution_summary["pass_rate"] == 1.0
    assert workbench["scorer_rollout_panel"]["execution_evidence_count"] == 1
    assert workbench["scorer_rollout_panel"]["execution_passed_count"] == 1
    assert workbench["scorer_rollout_panel"]["execution_manual_review_queue_size"] == 0
    assert workbench["summary"]["scorer_execution_evidence_count"] == 1
    assert workbench["summary"]["automatic_rollout_enabled"] is False
    assert workbench["summary"]["store_write_performed"] is False
    _assert_no_raw_leaks(workbench)


def test_ao44_ct_006_quality_center_filters_execution_by_scorer_version():
    repository = InMemoryRepository()
    write_runtime_run(repository, run_id="run_failed", status="failed")
    write_full_trace(repository, run_id="run_failed")
    create_eval_case(
        repository,
        "run_failed",
        owner_team="Quality",
        expected_behavior="Classify failure from redacted summary.",
    )
    create_quality_scorer_execution(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        pass_threshold=0.7,
        scorer={
            "scorer_id": "quality_summary_stage5_candidate",
            "scorer_version": "1.1.0",
        },
    )
    create_quality_scorer_execution(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        min_eval_cases=2,
        scorer={
            "scorer_id": "quality_summary_stage5_candidate",
            "scorer_version": "1.2.0",
        },
    )

    workbench = get_quality_center_workbench(
        repository,
        report_period="2026-05",
        agent_refs=[
            {
                "agent_id": "agent.ai-sdlc",
                "version": "1.0.0",
                "owner_team": "Quality",
                "candidate_scorer": {
                    "scorer_id": "quality_summary_stage5_candidate",
                    "scorer_version": "1.1.0",
                },
            }
        ],
    )

    execution_summary = workbench["agent_summaries"][0]["scorer_execution"]
    assert execution_summary["execution_id"] == "quality_scorer_execution_1"
    assert execution_summary["scorer_version"] == "1.1.0"
    assert execution_summary["execution_state"] == "passed"
    assert workbench["scorer_rollout_panel"]["execution_passed_count"] == 1
    assert (
        workbench["scorer_rollout_panel"]["execution_insufficient_evidence_count"] == 0
    )
    _assert_no_raw_leaks(workbench)


def test_ao44_ct_007_quality_center_matches_redacted_execution_identity_by_hash():
    repository = InMemoryRepository()
    agent_id = "agent." + ("very-long-agent-id-" * 8) + "token_secret"
    version = "version." + ("very-long-version-id-" * 8) + "https://example.invalid"
    write_runtime_run(
        repository,
        run_id="run_long_identity",
        agent_id=agent_id,
        version=version,
        status="failed",
    )
    write_full_trace(repository, run_id="run_long_identity")
    create_eval_case(
        repository,
        "run_long_identity",
        owner_team="Quality",
        expected_behavior="Classify failure from redacted summary.",
    )
    execution = create_quality_scorer_execution(
        repository,
        agent_id,
        version,
        pass_threshold=0.7,
        scorer={
            "scorer_id": "quality_summary_stage5_candidate",
            "scorer_version": "1.1.0",
        },
    )

    assert execution["agent_id"] == "[redacted]"
    assert execution["version"] == "[redacted]"
    assert (
        repository.quality_scorer_execution_records(
            agent_id,
            version,
            scorer_id="quality_summary_stage5_candidate",
            scorer_version="1.1.0",
        )[0]["execution_id"]
        == execution["execution_id"]
    )

    workbench = get_quality_center_workbench(
        repository,
        report_period="2026-05",
        agent_refs=[
            {
                "agent_id": agent_id,
                "version": version,
                "owner_team": "Quality",
                "candidate_scorer": {
                    "scorer_id": "quality_summary_stage5_candidate",
                    "scorer_version": "1.1.0",
                },
            }
        ],
    )

    execution_summary = workbench["agent_summaries"][0]["scorer_execution"]
    agent_identity = workbench["agent_summaries"][0]["agent_identity"]
    assert agent_identity["agent_id_hash"].startswith("sha256:")
    assert agent_identity["version_hash"].startswith("sha256:")
    assert execution_summary["execution_id"] == execution["execution_id"]
    assert execution_summary["execution_state"] == "passed"
    assert workbench["review_queue"]
    for review_item in workbench["review_queue"]:
        assert review_item["agent_id"] == "[redacted]"
        assert review_item["version"] == "[redacted]"
        assert review_item["agent_identity"] == agent_identity
    _assert_no_raw_leaks(workbench)


def test_ao44_ct_008_scorer_execution_redacts_source_run_identity():
    repository = InMemoryRepository()
    run_id = "run_https://example.invalid/token_secret"
    write_runtime_run(repository, run_id=run_id, status="failed")
    write_full_trace(repository, run_id=run_id)
    create_eval_case(
        repository,
        run_id,
        owner_team="Quality",
        expected_behavior="Classify failure from redacted summary.",
    )

    execution = create_quality_scorer_execution(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        pass_threshold=0.7,
        scorer={
            "scorer_id": "quality_summary_stage5_candidate",
            "scorer_version": "1.1.0",
        },
    )

    case_result = execution["case_results"][0]
    assert case_result["source_run_id"] == "[redacted]"
    assert case_result["source_run_identity"]["run_id_hash"].startswith("sha256:")
    _assert_no_raw_leaks(execution)


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
