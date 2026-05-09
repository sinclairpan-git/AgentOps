import pytest

from agentops.api.approvals import decide_approval_request
from agentops.api.grants import consume_grant, issue_grant
from agentops.api.policy import evaluate_policy_decision_v1
from agentops.api.runtime import (
    get_runtime_run_detail,
    get_runtime_trace_timeline,
    ingest_runtime_events,
)
from agentops.core.errors import AgentOpsError
from agentops.core.runtime_contracts import get_contract
from agentops.storage.repository import InMemoryRepository
from tests.contract.test_ao2_ct_001_policy_check import policy_request
from tests.contract.test_ao2_ct_002_approval_lifecycle import (
    create_pending_approval,
    grant_request_from_approval,
)
from tests.contract.test_ao31_ct_runtime_governance_foundation import (
    runtime_batch,
    runtime_event,
    runtime_run_payload,
    trace_span_payload,
)


def guardrail_result_payload(**overrides):
    payload = {
        "guardrail_result_id": "gr_1",
        "run_id": "run_1",
        "trace_id": "trace_1",
        "span_id": "span_guardrail",
        "attempt_no": 1,
        "guardrail_id": "pii_filter",
        "status": "passed",
        "severity": "info",
        "reason_code": "pii_clear",
        "policy_version": "policy.v2",
        "evidence_ref": "vault://guardrail/gr_1",
    }
    payload.update(overrides)
    return payload


def approved_grant(repository, **grant_overrides):
    approval = create_pending_approval(repository)
    approved = decide_approval_request(
        approval["approval_id"],
        action="approve",
        actor="security_1",
        reason="approved",
        repository=repository,
    )
    return issue_grant(
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
            **grant_overrides,
        },
        repository,
    )


def test_ao33_ct_001_policy_decision_v1_has_required_p0_fields():
    decision = evaluate_policy_decision_v1(
        policy_request(action="read", risk_level="low")
    )

    required_fields = get_contract("policy_decision.v1").required_fields

    assert required_fields.issubset(decision)
    assert decision["schema_version"] == "policy_decision.v1"
    assert decision["decision"] == "allow"
    assert decision["reason_code"] == "low_risk_allowed"
    assert decision["policy_set_version"] == "policy.v2"
    assert decision["ttl"] > 0
    assert decision["obligations"] == []
    assert decision["constraints"]["raw_payload_access"] == "forbidden"


def test_ao33_ct_002_policy_unavailable_is_not_allowed_for_high_risk_action():
    decision = evaluate_policy_decision_v1(policy_request(), service_available=False)

    assert decision["decision"] == "policy_unavailable"
    assert decision["fallback_action"] == "require_online"
    assert decision["ttl"] == 0
    assert decision["obligations"] == ["retry_policy_check"]


def test_ao33_ct_002_high_risk_policy_decision_requires_resource_scope():
    with pytest.raises(AgentOpsError) as exc:
        evaluate_policy_decision_v1(policy_request(resource_scope=None))

    assert exc.value.error_code == "POLICY_SCOPE_REQUIRED"
    assert exc.value.denied_scope == "policy.resource_scope"


def test_ao33_ct_003_capability_grant_binds_runtime_context(repository):
    grant = approved_grant(repository)

    required_fields = get_contract("capability_grant.v1").required_fields

    assert required_fields.issubset(grant)
    assert grant["version"] == "1.0.0"
    assert grant["artifact_hash"] == "sha256:artifact"
    assert grant["installation_id"] == "install_1"
    assert grant["device_id"] == "device_1"
    assert grant["user_id"] == "user_1"
    assert grant["session_id"] == "sess_1"
    assert grant["run_id"] == "run_1"
    assert grant["remaining_uses"] == 1
    assert grant["offline_allowed"] is False
    assert grant["signature"].startswith("sig_grant_")


def test_ao33_ct_004_grant_consumption_decrements_remaining_uses(repository):
    grant = approved_grant(repository)

    consumption = consume_grant(
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

    stored_grant = repository.get_grant(grant["grant_id"])
    assert consumption["remaining_uses_after"] == 0
    assert stored_grant is not None
    assert stored_grant["remaining_uses"] == 0

    with pytest.raises(AgentOpsError) as exc:
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

    assert exc.value.error_code == "GRANT_EXHAUSTED"


def test_ao33_ct_005_runtime_ingests_guardrail_result_fact():
    repository = InMemoryRepository()

    outcome = ingest_runtime_events(
        runtime_batch(
            [
                runtime_event(
                    "evt_run_1",
                    "runtime_run",
                    runtime_run_payload(status="running"),
                    schema_version="runtime_run.v1",
                    sequence_no=1,
                    idempotency_key="runtime:run_1",
                ),
                runtime_event(
                    "evt_guardrail_1",
                    "guardrail_result",
                    guardrail_result_payload(),
                    schema_version="guardrail_result.v1",
                    sequence_no=2,
                    idempotency_key="runtime:guardrail:gr_1",
                ),
            ]
        ),
        repository,
    )

    assert outcome["accepted_count"] == 2
    assert (
        repository.guardrail_result_records_for_run("run_1")[0]["guardrail_result_id"]
        == "gr_1"
    )


def test_ao33_ct_006_runtime_views_include_guardrail_summary_without_raw_payload():
    repository = InMemoryRepository()
    ingest_runtime_events(
        runtime_batch(
            [
                runtime_event(
                    "evt_run_1",
                    "runtime_run",
                    runtime_run_payload(status="running"),
                    schema_version="runtime_run.v1",
                    sequence_no=1,
                    idempotency_key="runtime:run_1",
                ),
                runtime_event(
                    "evt_span_guardrail",
                    "trace_span",
                    trace_span_payload(
                        span_id="span_guardrail",
                        span_kind="guardrail",
                        operation_name="guardrail.pii",
                        guardrail_result_refs=["gr_1"],
                    ),
                    schema_version="trace_span.v1",
                    sequence_no=2,
                    idempotency_key="runtime:span_guardrail",
                ),
                runtime_event(
                    "evt_guardrail_1",
                    "guardrail_result",
                    guardrail_result_payload(status="warn", severity="warning"),
                    schema_version="guardrail_result.v1",
                    sequence_no=3,
                    idempotency_key="runtime:guardrail:gr_1",
                ),
            ]
        ),
        repository,
    )

    detail = get_runtime_run_detail(repository, "run_1")
    timeline = get_runtime_trace_timeline(repository, "run_1")

    assert detail["guardrail_summary"] == [
        {
            "guardrail_result_id": "gr_1",
            "span_id": "span_guardrail",
            "guardrail_id": "pii_filter",
            "status": "warn",
            "severity": "warning",
            "reason_code": "pii_clear",
            "evidence_ref": "vault://guardrail/gr_1",
        }
    ]
    assert "payload" not in detail["guardrail_summary"][0]
    assert timeline["spans"][0]["guardrail_results"][0]["status"] == "warn"
    assert "payload" not in timeline["spans"][0]["guardrail_results"][0]
