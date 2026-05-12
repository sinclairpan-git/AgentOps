from __future__ import annotations

from agentops.api.operations import (
    get_quality_center_workbench,
    ingest_quality_scorer_external_execution,
)
from agentops.core.runtime_contracts import get_contract
from agentops.storage.repository import InMemoryRepository
from tests.contract.test_ao42_ct_quality_center_workbench import _assert_no_raw_leaks
from tests.contract.test_ao47_ct_quality_scorer_external_intake_readback import (
    _candidate_scorer,
    _seed_eval_case,
)
from tests.contract.test_ao48_ct_quality_scorer_external_intake_index import (
    _seed_eval_case_for,
)


def test_ao50_ct_001_contract_registry_exposes_external_intake_health():
    workbench_contract = get_contract("quality_center_workbench.v1")
    health_contract = get_contract("quality_center_external_intake_health.v1")

    assert "external_intake_panel" in workbench_contract.required_fields
    assert "AO50-CT-001" in workbench_contract.contract_tests
    assert health_contract.domain_owner == "AgentOps"
    assert health_contract.enum_fields["health_state"] == frozenset(
        {"no_receipts", "receiving", "needs_review"}
    )
    assert {
        "health_state",
        "receipt_count",
        "accepted_execution_count",
        "manual_review_required",
        "recommendation",
        "summary",
    }.issubset(health_contract.required_fields)
    assert "AO50-CT-002" in health_contract.contract_tests


def test_ao50_ct_002_workbench_aggregates_external_intake_receipts_without_actions():
    repository = InMemoryRepository()
    eval_case_id = _seed_eval_case(repository)
    first = ingest_quality_scorer_external_execution(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        idempotency_key="quality-center-intake:run-1",
        signature="sig:quality-center-intake-1",
        scorer=_candidate_scorer(),
        external_result={
            "source_eval_cases": [eval_case_id],
            "case_results": [
                {
                    "eval_case_id": eval_case_id,
                    "outcome": "passed",
                    "score": 0.94,
                }
            ],
        },
    )
    second = ingest_quality_scorer_external_execution(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        idempotency_key="quality-center-intake:run-2",
        signature="sig:quality-center-intake-2",
        scorer=_candidate_scorer(),
        external_result={
            "source_eval_cases": [eval_case_id],
            "case_results": [
                {
                    "eval_case_id": eval_case_id,
                    "outcome": "passed",
                    "score": 0.96,
                }
            ],
        },
    )
    before_count = len(
        repository.quality_scorer_execution_records("agent.ai-sdlc", "1.0.0")
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
            }
        ],
    )

    after_count = len(
        repository.quality_scorer_execution_records("agent.ai-sdlc", "1.0.0")
    )
    health = workbench["agent_summaries"][0]["external_intake_health"]
    assert first["intake_id"] != second["intake_id"]
    assert health["schema_version"] == "quality_center_external_intake_health.v1"
    assert health["health_state"] == "receiving"
    assert health["receipt_count"] == 2
    assert health["latest_intake_id"] == second["intake_id"]
    assert health["latest_sample_size"] == 1
    assert health["latest_pass_rate"] == 1.0
    assert health["intake_state_counts"] == {"accepted": 2}
    assert health["source_trust_counts"] == {"signed": 2}
    assert health["accepted_execution_count"] == 2
    assert health["scorer_refs"] == [_candidate_scorer()]
    assert health["manual_review_required"] is False
    assert health["recommendation"] == "monitor"
    assert health["summary"]["summary_only_intake_health"] is True
    assert health["summary"]["scorer_execution_performed"] is False
    assert workbench["external_intake_panel"]["receiving_count"] == 1
    assert workbench["external_intake_panel"]["receipt_count"] == 2
    assert workbench["external_intake_panel"]["automatic_scorer_invocation"] is False
    assert workbench["summary"]["external_intake_receipt_count"] == 2
    assert before_count == 2
    assert after_count == before_count
    _assert_no_raw_leaks(workbench)


def test_ao50_ct_003_required_external_intake_absence_routes_manual_review():
    repository = InMemoryRepository()

    workbench = get_quality_center_workbench(
        repository,
        report_period="2026-05",
        agent_refs=[
            {
                "agent_id": "agent.ai-sdlc",
                "version": "1.0.0",
                "owner_team": "Quality",
                "external_intake_required": True,
            }
        ],
    )

    health = workbench["agent_summaries"][0]["external_intake_health"]
    intake_items = [
        item
        for item in workbench["review_queue"]
        if item["review_type"] == "external_intake"
    ]
    assert health["health_state"] == "no_receipts"
    assert health["receipt_count"] == 0
    assert health["manual_review_required"] is True
    assert health["recommendation"] == "connect_external_scorer"
    assert workbench["external_intake_panel"]["no_receipts_count"] == 1
    assert workbench["external_intake_panel"]["manual_review_queue_size"] == 1
    assert intake_items[0]["reason"] == "no_receipts"
    assert intake_items[0]["recommended_action"] == "connect_external_scorer"
    assert intake_items[0]["automatic_action_performed"] is False
    _assert_no_raw_leaks(workbench)


def test_ao50_ct_004_workbench_redacts_uri_identity_but_uses_hash_lookup():
    repository = InMemoryRepository()
    eval_case_id = _seed_eval_case_for(
        repository,
        run_id="run_quality_center_uri_intake",
        agent_id="https://example.invalid/agent-quality-center-intake",
        version="1.0.0",
    )
    receipt = ingest_quality_scorer_external_execution(
        repository,
        "https://example.invalid/agent-quality-center-intake",
        "1.0.0",
        idempotency_key="quality-center-intake:uri-agent",
        signature="sig:quality-center-intake-uri",
        scorer=_candidate_scorer(),
        external_result={
            "source_eval_cases": [eval_case_id],
            "case_results": [
                {
                    "eval_case_id": eval_case_id,
                    "outcome": "passed",
                    "score": 0.94,
                }
            ],
        },
    )

    workbench = get_quality_center_workbench(
        repository,
        report_period="2026-05",
        agent_refs=[
            {
                "agent_id": "https://example.invalid/agent-quality-center-intake",
                "version": "1.0.0",
                "owner_team": "Quality",
            }
        ],
    )

    summary = workbench["agent_summaries"][0]
    health = summary["external_intake_health"]
    assert summary["agent_id"] == "[redacted]"
    assert health["receipt_count"] == 1
    assert health["latest_intake_id"] == receipt["intake_id"]
    assert workbench["external_intake_panel"]["receiving_count"] == 1
    _assert_no_raw_leaks(workbench)
