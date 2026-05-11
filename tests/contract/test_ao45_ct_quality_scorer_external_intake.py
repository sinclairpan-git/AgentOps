from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from agentops.api.operations import (
    create_eval_case,
    get_quality_center_workbench,
    ingest_quality_scorer_external_execution,
)
from agentops.core.errors import AgentOpsError
from agentops.core.runtime_contracts import get_contract
from agentops.storage.repository import InMemoryRepository
from tests.contract.test_ao32_ct_evidence_health_summary_loop import (
    write_full_trace,
    write_runtime_run,
)


def test_ao45_ct_001_contract_registry_has_external_intake():
    contract = get_contract("quality_scorer_external_intake.v1")

    assert contract.domain_owner == "AgentOps"
    assert {
        "intake_id",
        "idempotency_key",
        "agent_id",
        "version",
        "scorer",
        "source_trust",
        "signature_state",
        "intake_state",
        "payload_hash",
        "accepted_execution_id",
        "summary",
        "audit_id",
    }.issubset(contract.required_fields)
    assert contract.enum_fields["intake_state"] == frozenset(
        {"accepted", "deduplicated", "rejected"}
    )
    assert "AO45-CT-001" in contract.contract_tests


def test_ao45_ct_002_external_intake_accepts_signed_summary_result():
    repository = InMemoryRepository()
    eval_case_id = _seed_eval_case(repository)

    receipt = ingest_quality_scorer_external_execution(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        idempotency_key="scorer-external:run-1",
        source_trust="signed",
        signature="sig:external-scorer-1",
        scorer=_candidate_scorer(),
        external_result={
            "source_eval_cases": [eval_case_id],
            "case_results": [
                {
                    "eval_case_id": eval_case_id,
                    "outcome": "passed",
                    "score": 0.94,
                    "evidence_level": "L2",
                }
            ],
        },
        pass_threshold=0.8,
    )

    assert receipt["schema_version"] == "quality_scorer_external_intake.v1"
    assert receipt["intake_state"] == "accepted"
    assert receipt["signature_state"] == "verified"
    assert receipt["source_trust"] == "signed"
    assert receipt["summary"]["summary_only_intake"] is True
    assert receipt["summary"]["agentops_scorer_invoked"] is False
    assert receipt["summary"]["automatic_rollout_enabled"] is False
    assert receipt["summary"]["store_write_performed"] is False

    execution_records = repository.quality_scorer_execution_records(
        "agent.ai-sdlc",
        "1.0.0",
        scorer_id="quality_summary_stage5_candidate",
        scorer_version="1.1.0",
    )
    assert len(execution_records) == 1
    execution = execution_records[0]
    assert receipt["accepted_execution_id"] == execution["execution_id"]
    assert execution["execution_state"] == "passed"
    assert execution["pass_rate"] == 1.0
    assert execution["execution_source"] == "external_intake"
    assert execution["summary"]["external_scorer_result_received"] is True
    assert execution["summary"]["agentops_scorer_invoked"] is False
    _assert_no_raw_leaks(receipt)
    _assert_no_raw_leaks(execution)


def test_ao45_ct_003_external_intake_idempotency_does_not_duplicate_execution():
    repository = InMemoryRepository()
    eval_case_id = _seed_eval_case(repository)
    payload = {
        "source_eval_cases": [eval_case_id],
        "case_results": [
            {"eval_case_id": eval_case_id, "outcome": "passed", "score": 0.91}
        ],
    }

    first = ingest_quality_scorer_external_execution(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        idempotency_key="scorer-external:dedup",
        signature="sig:external-scorer-1",
        scorer=_candidate_scorer(),
        external_result=payload,
    )
    second = ingest_quality_scorer_external_execution(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        idempotency_key="scorer-external:dedup",
        signature="sig:external-scorer-1",
        scorer=_candidate_scorer(),
        external_result=payload,
    )

    assert first["intake_state"] == "accepted"
    assert second["intake_state"] == "deduplicated"
    assert second["intake_id"] == first["intake_id"]
    assert second["accepted_execution_id"] == first["accepted_execution_id"]
    assert (
        len(repository.quality_scorer_execution_records("agent.ai-sdlc", "1.0.0")) == 1
    )


def test_ao45_ct_004_external_intake_scopes_idempotency_by_agent_version():
    repository = InMemoryRepository()
    eval_case_a = _seed_eval_case(repository, run_id="run_failed_a")
    eval_case_b = _seed_eval_case(
        repository,
        run_id="run_failed_b",
        agent_id="agent.runtime",
        version="2.0.0",
    )

    first = ingest_quality_scorer_external_execution(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        idempotency_key="scorer-external:run-1",
        signature="sig:external-scorer-1",
        scorer=_candidate_scorer(),
        external_result={
            "source_eval_cases": [eval_case_a],
            "case_results": [
                {"eval_case_id": eval_case_a, "outcome": "passed", "score": 0.91}
            ],
        },
    )
    second = ingest_quality_scorer_external_execution(
        repository,
        "agent.runtime",
        "2.0.0",
        idempotency_key="scorer-external:run-1",
        signature="sig:external-scorer-1",
        scorer=_candidate_scorer(),
        external_result={
            "source_eval_cases": [eval_case_b],
            "case_results": [
                {"eval_case_id": eval_case_b, "outcome": "passed", "score": 0.92}
            ],
        },
    )

    assert first["intake_state"] == "accepted"
    assert second["intake_state"] == "accepted"
    assert second["intake_id"] != first["intake_id"]
    assert second["accepted_execution_id"] != first["accepted_execution_id"]
    assert (
        len(repository.quality_scorer_execution_records("agent.ai-sdlc", "1.0.0")) == 1
    )
    assert (
        len(repository.quality_scorer_execution_records("agent.runtime", "2.0.0")) == 1
    )


def test_ao45_ct_005_external_intake_check_and_write_is_atomic_for_duplicate_key():
    repository = InMemoryRepository()
    eval_case_id = _seed_eval_case(repository)
    payload = {
        "source_eval_cases": [eval_case_id],
        "case_results": [
            {"eval_case_id": eval_case_id, "outcome": "passed", "score": 0.91}
        ],
    }

    def ingest_once() -> dict:
        return ingest_quality_scorer_external_execution(
            repository,
            "agent.ai-sdlc",
            "1.0.0",
            idempotency_key="scorer-external:atomic",
            signature="sig:external-scorer-1",
            scorer=_candidate_scorer(),
            external_result=payload,
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        receipts = list(executor.map(lambda _: ingest_once(), range(8)))

    assert sum(1 for receipt in receipts if receipt["intake_state"] == "accepted") == 1
    assert (
        sum(1 for receipt in receipts if receipt["intake_state"] == "deduplicated") == 7
    )
    assert len({receipt["accepted_execution_id"] for receipt in receipts}) == 1
    assert (
        len(repository.quality_scorer_execution_records("agent.ai-sdlc", "1.0.0")) == 1
    )


def test_ao45_ct_006_external_intake_rejects_untrusted_or_unsigned_source():
    repository = InMemoryRepository()
    eval_case_id = _seed_eval_case(repository)

    with pytest.raises(AgentOpsError) as exc:
        ingest_quality_scorer_external_execution(
            repository,
            "agent.ai-sdlc",
            "1.0.0",
            idempotency_key="scorer-external:untrusted",
            source_trust="unsigned",
            signature="sig:external-scorer-1",
            scorer=_candidate_scorer(),
            external_result={"source_eval_cases": [eval_case_id]},
        )

    assert exc.value.error_code == "QUALITY_SCORER_INTAKE_UNTRUSTED"
    assert repository.quality_scorer_execution_records("agent.ai-sdlc", "1.0.0") == ()

    with pytest.raises(AgentOpsError) as signature_exc:
        ingest_quality_scorer_external_execution(
            repository,
            "agent.ai-sdlc",
            "1.0.0",
            idempotency_key="scorer-external:missing-signature",
            source_trust="signed",
            signature="",
            scorer=_candidate_scorer(),
            external_result={"source_eval_cases": [eval_case_id]},
        )

    assert signature_exc.value.error_code == "QUALITY_SCORER_INTAKE_SIGNATURE_INVALID"
    assert repository.quality_scorer_execution_records("agent.ai-sdlc", "1.0.0") == ()


def test_ao45_ct_007_external_intake_rejects_sample_boundary_and_raw_payload():
    repository = InMemoryRepository()
    eval_case_id = _seed_eval_case(repository)

    with pytest.raises(AgentOpsError) as sample_exc:
        ingest_quality_scorer_external_execution(
            repository,
            "agent.ai-sdlc",
            "1.0.0",
            idempotency_key="scorer-external:wrong-sample",
            signature="sig:external-scorer-1",
            scorer=_candidate_scorer(),
            external_result={"source_eval_cases": ["eval_case_missing"]},
        )

    assert sample_exc.value.error_code == "QUALITY_SCORER_INTAKE_SAMPLE_INVALID"

    with pytest.raises(AgentOpsError) as raw_exc:
        ingest_quality_scorer_external_execution(
            repository,
            "agent.ai-sdlc",
            "1.0.0",
            idempotency_key="scorer-external:raw",
            signature="sig:external-scorer-1",
            scorer=_candidate_scorer(),
            external_result={
                "source_eval_cases": [eval_case_id],
                "case_results": [{"eval_case_id": eval_case_id, "outcome": "passed"}],
                "raw_payload": "do not ingest",
            },
        )

    assert raw_exc.value.error_code == "QUALITY_SCORER_INTAKE_RAW_INPUT"
    assert repository.quality_scorer_execution_records("agent.ai-sdlc", "1.0.0") == ()


def test_ao45_ct_008_quality_center_aggregates_external_intake_execution():
    repository = InMemoryRepository()
    eval_case_id = _seed_eval_case(repository)
    ingest_quality_scorer_external_execution(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        idempotency_key="scorer-external:workbench",
        signature="sig:external-scorer-1",
        scorer=_candidate_scorer(),
        external_result={
            "source_eval_cases": [eval_case_id],
            "case_results": [
                {"eval_case_id": eval_case_id, "outcome": "passed", "score": 0.93}
            ],
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
                "candidate_scorer": _candidate_scorer(),
            }
        ],
    )

    execution_summary = workbench["agent_summaries"][0]["scorer_execution"]
    assert execution_summary["execution_state"] == "passed"
    assert execution_summary["pass_rate"] == 1.0
    assert workbench["scorer_rollout_panel"]["execution_evidence_count"] == 1
    assert workbench["scorer_rollout_panel"]["execution_passed_count"] == 1
    assert workbench["summary"]["automatic_rollout_enabled"] is False
    assert workbench["summary"]["store_write_performed"] is False
    _assert_no_raw_leaks(workbench)


def _seed_eval_case(
    repository: InMemoryRepository,
    run_id: str = "run_failed",
    *,
    agent_id: str = "agent.ai-sdlc",
    version: str = "1.0.0",
) -> str:
    write_runtime_run(
        repository,
        run_id=run_id,
        agent_id=agent_id,
        version=version,
        status="failed",
    )
    write_full_trace(repository, run_id=run_id)
    eval_case = create_eval_case(
        repository,
        run_id,
        owner_team="Quality",
        expected_behavior="Classify failure from redacted summary.",
    )
    return str(eval_case["eval_case_id"])


def _candidate_scorer() -> dict[str, str]:
    return {
        "scorer_id": "quality_summary_stage5_candidate",
        "scorer_version": "1.1.0",
        "score_template_id": "quality_summary_stage5_candidate",
    }


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
