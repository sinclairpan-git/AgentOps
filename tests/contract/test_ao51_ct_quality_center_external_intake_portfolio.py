from __future__ import annotations

from agentops.api.operations import (
    get_quality_center_external_intake_portfolio,
    get_quality_center_workbench,
    ingest_quality_scorer_external_execution,
)
from agentops.core.runtime_contracts import get_contract
from agentops.storage.repository import (
    InMemoryRepository,
    _quality_scorer_lookup_hash,
)
from tests.contract.test_ao42_ct_quality_center_workbench import _assert_no_raw_leaks
from tests.contract.test_ao47_ct_quality_scorer_external_intake_readback import (
    _candidate_scorer,
    _seed_eval_case,
)
from tests.contract.test_ao48_ct_quality_scorer_external_intake_index import (
    _seed_eval_case_for,
)


def test_ao51_ct_001_contract_registry_exposes_external_intake_portfolio():
    workbench_contract = get_contract("quality_center_workbench.v1")
    portfolio_contract = get_contract("quality_center_external_intake_portfolio.v1")

    assert "external_intake_portfolio" in workbench_contract.required_fields
    assert "AO51-CT-001" in workbench_contract.contract_tests
    assert portfolio_contract.domain_owner == "AgentOps"
    assert portfolio_contract.enum_fields["portfolio_state"] == frozenset(
        {"empty", "no_receipts", "receiving", "incomplete", "needs_review"}
    )
    assert {
        "portfolio_state",
        "scope_count",
        "state_counts",
        "required_missing_scopes",
        "latest_receipts",
        "scorer_coverage",
        "summary",
    }.issubset(portfolio_contract.required_fields)
    assert "AO51-CT-002" in portfolio_contract.contract_tests


def test_ao51_ct_002_workbench_builds_multi_scope_external_intake_portfolio():
    repository = InMemoryRepository()
    eval_case_id = _seed_eval_case(repository)
    accepted = ingest_quality_scorer_external_execution(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        idempotency_key="quality-center-portfolio:accepted",
        signature="sig:quality-center-portfolio-accepted",
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
    rejected = _store_rejected_receipt(
        repository,
        agent_id="agent.runtime",
        version="2.0.0",
        idempotency_key="quality-center-portfolio:rejected",
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
            },
            {
                "agent_id": "agent.store",
                "version": "1.0.0",
                "owner_team": "Store",
                "external_intake_required": True,
            },
            {
                "agent_id": "agent.runtime",
                "version": "2.0.0",
                "owner_team": "Runtime",
            },
        ],
    )

    after_count = len(
        repository.quality_scorer_execution_records("agent.ai-sdlc", "1.0.0")
    )
    portfolio = workbench["external_intake_portfolio"]
    assert portfolio["schema_version"] == (
        "quality_center_external_intake_portfolio.v1"
    )
    assert portfolio["portfolio_state"] == "needs_review"
    assert portfolio["scope_count"] == 3
    assert portfolio["version_scope_count"] == 3
    assert portfolio["state_counts"] == {
        "receiving": 1,
        "no_receipts": 1,
        "needs_review": 1,
    }
    assert portfolio["receipt_count"] == 2
    assert portfolio["accepted_execution_count"] == 1
    assert portfolio["manual_review_queue_size"] == 2
    assert portfolio["required_missing_scope_count"] == 1
    assert portfolio["required_missing_scopes"][0]["agent_id"] == "agent.store"
    assert portfolio["required_missing_scopes"][0]["recommendation"] == (
        "connect_external_scorer"
    )
    latest_ids = {item["latest_intake_id"] for item in portfolio["latest_receipts"]}
    assert {accepted["intake_id"], rejected["intake_id"]} <= latest_ids
    assert portfolio["scorer_coverage"]["unique_scorer_count"] == 1
    assert portfolio["scorer_coverage"]["scopes_with_scorer_receipts"] == 2
    assert portfolio["summary"]["summary_only_intake_portfolio"] is True
    assert portfolio["summary"]["automatic_scorer_invocation"] is False
    assert portfolio["summary"]["store_write_performed"] is False
    assert after_count == before_count
    _assert_no_raw_leaks(workbench)


def test_ao51_ct_003_portfolio_api_matches_workbench_projection():
    repository = InMemoryRepository()
    eval_case_id = _seed_eval_case(repository)
    ingest_quality_scorer_external_execution(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        idempotency_key="quality-center-portfolio:api",
        signature="sig:quality-center-portfolio-api",
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
    kwargs = {
        "report_period": "2026-05",
        "agent_refs": [
            {
                "agent_id": "agent.ai-sdlc",
                "version": "1.0.0",
                "owner_team": "Quality",
            }
        ],
    }

    workbench = get_quality_center_workbench(repository, **kwargs)
    portfolio = get_quality_center_external_intake_portfolio(repository, **kwargs)

    assert portfolio == workbench["external_intake_portfolio"]
    assert portfolio["portfolio_state"] == "receiving"
    _assert_no_raw_leaks(portfolio)


def test_ao51_ct_004_portfolio_redacts_uri_identity_but_uses_hash_lookup():
    repository = InMemoryRepository()
    eval_case_id = _seed_eval_case_for(
        repository,
        run_id="run_quality_center_portfolio_uri",
        agent_id="https://example.invalid/agent-quality-center-portfolio",
        version="1.0.0",
    )
    receipt = ingest_quality_scorer_external_execution(
        repository,
        "https://example.invalid/agent-quality-center-portfolio",
        "1.0.0",
        idempotency_key="quality-center-portfolio:uri-agent",
        signature="sig:quality-center-portfolio-uri",
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
                "agent_id": "https://example.invalid/agent-quality-center-portfolio",
                "version": "1.0.0",
                "owner_team": "Quality",
            }
        ],
    )

    portfolio = workbench["external_intake_portfolio"]
    assert portfolio["scope_count"] == 1
    assert portfolio["state_counts"]["receiving"] == 1
    assert portfolio["latest_receipts"][0]["agent_id"] == "[redacted]"
    assert portfolio["latest_receipts"][0]["latest_intake_id"] == receipt["intake_id"]
    assert portfolio["latest_receipts"][0]["agent_identity"][
        "agent_id_hash"
    ].startswith("sha256:")
    _assert_no_raw_leaks(workbench)


def _store_rejected_receipt(
    repository: InMemoryRepository,
    *,
    agent_id: str,
    version: str,
    idempotency_key: str,
) -> dict:
    return repository.store_quality_scorer_external_receipt(
        {
            "schema_version": "quality_scorer_external_intake.v1",
            "intake_id": "",
            "idempotency_key": idempotency_key,
            "agent_id": agent_id,
            "version": version,
            "lookup_identity": {
                "agent_id_hash": _quality_scorer_lookup_hash("agent_id", agent_id),
                "version_hash": _quality_scorer_lookup_hash("version", version),
            },
            "scorer": _candidate_scorer(),
            "source_trust": "signed",
            "signature_state": "verified",
            "intake_state": "rejected",
            "payload_hash": "sha256:rejected",
            "producer": "external_scorer",
            "received_at": "2026-05-12T00:00:00+00:00",
            "sample_size": 1,
            "pass_rate": 0.0,
            "summary": {
                "raw_payload_access": "forbidden",
                "summary_only_intake": True,
                "agentops_scorer_invoked": False,
                "automatic_rollout_enabled": False,
                "automatic_template_switch": False,
                "store_write_performed": False,
                "notification_sent": False,
            },
            "audit_id": "audit_quality_center_portfolio_rejected",
        }
    )
