from __future__ import annotations

import json

from agentops.api.acceptance import build_p0_acceptance_gate
from agentops.api.approvals import decide_approval_request
from agentops.api.grants import consume_grant, issue_grant
from agentops.api.policy import evaluate_policy_decision_v1
from agentops.api.runtime import ingest_runtime_events
from agentops.core.runtime_contracts import get_contract
from agentops.storage.repository import InMemoryRepository
from tests.contract.test_ao2_ct_001_policy_check import active_grant, policy_request
from tests.contract.test_ao2_ct_002_approval_lifecycle import (
    create_pending_approval,
    grant_request_from_approval,
)
from tests.contract.test_ao31_ct_runtime_governance_foundation import (
    runtime_batch,
    runtime_event,
)
from tests.contract.test_ao32_ct_evidence_health_summary_loop import (
    register_agent,
    write_full_trace,
    write_runtime_run,
)
from tests.contract.test_ao33_ct_policy_grant_guardrail_control import (
    guardrail_result_payload,
)
from tests.contract.test_ao34_ct_runtime_outbox_sdlc_trace_bridge import (
    canonical_sdlc_event,
    sdlc_trace_payload,
)


def test_ao35_ct_001_contract_registry_has_p0_acceptance_gate():
    contract = get_contract("p0_acceptance_gate.v1")

    assert contract.domain_owner == "AgentOps"
    assert contract.producer == "AgentOps"
    assert {"Ops", "Agent Store", "Ai_AutoSDLC"}.issubset(contract.consumers)
    assert {
        "gate_id",
        "run_id",
        "agent_id",
        "version",
        "gate_status",
        "required_checks",
        "summary",
        "audit_id",
    }.issubset(contract.required_fields)
    assert contract.enum_fields["gate_status"] == frozenset({"passed", "failed"})
    assert "AO35-CT-002" in contract.contract_tests


def test_ao35_ct_002_acceptance_gate_passes_complete_p0_loop():
    repository = InMemoryRepository()
    register_agent(repository)
    write_runtime_run(repository, status="succeeded")
    write_full_trace(repository)
    receipt = ingest_runtime_events(
        runtime_batch(
            [
                runtime_event(
                    "evt_guardrail_p0",
                    "guardrail_result",
                    guardrail_result_payload(status="passed", severity="info"),
                    schema_version="guardrail_result.v1",
                    sequence_no=50,
                    idempotency_key="runtime:p0:guardrail",
                ),
                canonical_sdlc_event(
                    "evt_sdlc_p0_gate",
                    sdlc_trace_payload(
                        sdlc_event_id="sdlc_gate_p0",
                        trace_id="trace_1",
                        span_id="sdlc_gate_p0",
                        parent_span_id="",
                        sdlc_event_type="gate",
                        stage_name="verify",
                        status="passed",
                        evidence_ref="vault://sdlc/p0/gate",
                    ),
                    sequence_no=51,
                    idempotency_key="sdlc:p0:gate",
                ),
            ],
            batch_id="batch_p0_acceptance",
            outbox_id="outbox_p0_acceptance",
            producer="Ai_AutoSDLC",
        ),
        repository,
    )
    grant = _issue_and_consume_bound_grant(repository)
    policy_decision = evaluate_policy_decision_v1(
        policy_request(),
        grant=active_grant(
            grant_id=grant["grant_id"],
            expires_at=grant["expires_at"],
            version=grant["version"],
            artifact_hash=grant["artifact_hash"],
            installation_id=grant["installation_id"],
            device_id=grant["device_id"],
            user_id=grant["user_id"],
            session_id=grant["session_id"],
            run_id=grant["run_id"],
        ),
    )

    gate = build_p0_acceptance_gate(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        "run_1",
        outbox_receipt=receipt,
        policy_decision=policy_decision,
    )

    assert gate["schema_version"] == "p0_acceptance_gate.v1"
    assert gate["gate_status"] == "passed"
    assert gate["summary"]["failed"] == 0
    assert {check["status"] for check in gate["required_checks"]} == {"passed"}
    assert gate["outbox_receipt"]["outbox_state"] == "delivered"
    assert gate["store_ops_detail_url"] == "/agentops/runtime/runs/run_1"

    serialized = json.dumps(gate, ensure_ascii=False)
    assert "raw_payload" not in serialized
    assert "credential_secret" not in serialized
    assert "token_secret" not in serialized
    assert "device_key" not in serialized
    assert "prompt" not in serialized


def test_ao35_ct_003_acceptance_gate_fails_when_store_summary_is_degraded():
    repository = InMemoryRepository()
    register_agent(repository)
    write_runtime_run(repository, status="succeeded")
    receipt = ingest_runtime_events(
        runtime_batch([], batch_id="batch_p0_empty", outbox_id="outbox_p0_empty"),
        repository,
    )

    gate = build_p0_acceptance_gate(
        repository,
        "agent.ai-sdlc",
        "1.0.0",
        "run_1",
        outbox_receipt=receipt,
        policy_decision=evaluate_policy_decision_v1(
            policy_request(action="read", risk_level="low")
        ),
    )

    failed_checks = {
        check["check_id"]: check["reason_code"]
        for check in gate["required_checks"]
        if check["status"] == "failed"
    }
    assert gate["gate_status"] == "failed"
    assert failed_checks["trace_timeline_complete"] == "trace_timeline_incomplete"
    assert failed_checks["evidence_summary_l5"] == "trace_pending"
    assert failed_checks["agent_store_echo_fresh"] == "agent_store_echo_not_fresh"


def _issue_and_consume_bound_grant(repository: InMemoryRepository) -> dict:
    approval = create_pending_approval(repository)
    approved = decide_approval_request(
        approval["approval_id"],
        action="approve",
        actor="security_1",
        reason="approved for P0 acceptance",
        repository=repository,
    )
    grant = issue_grant(
        approved["approval_id"],
        {
            **grant_request_from_approval(approved),
            "version": "1.0.0",
            "artifact_hash": "sha256:artifact",
            "installation_id": "install_1",
            "device_id": "device_1",
            "user_id": "user_1",
            "session_id": "sess_1",
            "run_id": "run_1",
            "remaining_uses": 1,
        },
        repository,
    )
    consume_grant(
        grant["grant_id"],
        policy_request(
            policy_check_id=grant["policy_check_id"],
            version=grant["version"],
            artifact_hash=grant["artifact_hash"],
            installation_id=grant["installation_id"],
            device_id=grant["device_id"],
            user_id=grant["user_id"],
            session_id=grant["session_id"],
            run_id=grant["run_id"],
        ),
        repository,
    )
    return grant
