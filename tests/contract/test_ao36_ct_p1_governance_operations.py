from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from agentops.api.approvals import decide_approval_request
from agentops.api.grants import (
    build_grant_lifecycle_view,
    consume_grant,
    issue_grant,
    revoke_grant,
)
from agentops.api.policy import (
    build_policy_operations_projection,
    register_policy_set_version,
)
from agentops.core.runtime_contracts import get_contract
from tests.contract.test_ao2_ct_001_policy_check import policy_request
from tests.contract.test_ao2_ct_002_approval_lifecycle import (
    create_pending_approval,
    grant_request_from_approval,
)


def test_ao36_ct_001_contract_registry_has_approval_operation():
    contract = get_contract("approval_operation.v1")

    assert contract.domain_owner == "AgentOps"
    assert contract.producer == "AgentOps"
    assert {"Ops", "Policy Service"}.issubset(contract.consumers)
    assert {
        "operation_id",
        "approval_id",
        "operation",
        "actor",
        "state_before",
        "state_after",
        "summary",
        "audit_id",
    }.issubset(contract.required_fields)
    assert contract.enum_fields["operation"] == frozenset(
        {
            "request_input",
            "request_more_info",
            "approve",
            "reject",
            "expire",
            "withdraw",
            "escalate",
            "revoke",
            "break_glass_approve",
        }
    )
    assert {"needs_more_info", "revoked"}.issubset(contract.enum_fields["state_after"])
    assert "AO36-CT-002" in contract.contract_tests


def test_ao36_ct_001_contract_registry_has_policy_set_version():
    contract = get_contract("policy_set_version.v1")

    assert contract.domain_owner == "AgentOps"
    assert contract.producer == "Policy Service"
    assert {"Ops", "Runtime", "Agent Store"}.issubset(contract.consumers)
    assert {
        "policy_set_version",
        "state",
        "risk_templates",
        "fallback_action",
        "deny_priority",
        "summary",
        "audit_id",
    }.issubset(contract.required_fields)
    assert contract.enum_fields["state"] == frozenset(
        {"draft", "canary", "active", "rolled_back", "retired"}
    )
    assert "AO36-CT-003" in contract.contract_tests


def test_ao36_ct_001_contract_registry_has_policy_operations_projection():
    contract = get_contract("policy_operations_projection.v1")

    assert contract.domain_owner == "AgentOps"
    assert contract.producer == "Policy Service"
    assert {"Ops", "Runtime", "Agent Store"}.issubset(contract.consumers)
    assert {"active_version", "versions", "summary", "audit_id"}.issubset(
        contract.required_fields
    )
    assert "AO36-CT-003" in contract.contract_tests


def test_ao36_ct_001_contract_registry_has_grant_lifecycle():
    contract = get_contract("grant_lifecycle.v1")

    assert contract.domain_owner == "AgentOps"
    assert contract.producer == "Policy Service"
    assert {"Ops", "Runtime", "Agent Store"}.issubset(contract.consumers)
    assert {
        "grant_id",
        "status",
        "binding",
        "remaining_uses",
        "consumption_summary",
        "impact_summary",
        "audit_id",
    }.issubset(contract.required_fields)
    assert contract.enum_fields["status"] == frozenset(
        {"active", "revoked", "expired", "exhausted"}
    )
    assert "AO36-CT-004" in contract.contract_tests


def test_ao36_ct_002_approval_operation_can_request_input(repository):
    approval = create_pending_approval(repository)

    updated = decide_approval_request(
        approval["approval_id"],
        action="request_input",
        actor="security_1",
        reason="Need deployment impact assessment.",
        repository=repository,
        required_materials=["impact_assessment", "rollback_plan"],
        notification_intent={"target": approval["requester"], "channel": "todo"},
    )

    assert updated["status"] == "needs_input"
    assert updated["required_materials"] == ["impact_assessment", "rollback_plan"]
    operation = repository.approval_operation_records()[-1]
    assert operation["operation"] == "request_input"
    assert operation["state_before"] == "pending"
    assert operation["state_after"] == "needs_input"
    assert operation["summary"]["raw_payload_access"] == "forbidden"
    assert operation["notification_intent"]["target"] == approval["requester"]


def test_ao36_ct_002_approval_operation_can_escalate_and_withdraw(repository):
    approval = create_pending_approval(repository)

    escalated = decide_approval_request(
        approval["approval_id"],
        action="escalate",
        actor="system",
        reason="SLA elapsed.",
        repository=repository,
    )
    withdrawn = decide_approval_request(
        approval["approval_id"],
        action="withdraw",
        actor=approval["requester"],
        reason="Runtime run cancelled.",
        repository=repository,
    )

    assert escalated["status"] == "escalated"
    assert escalated["sla_state"] == "escalated"
    assert withdrawn["status"] == "withdrawn"
    operations = repository.approval_operation_records()
    assert [item["operation"] for item in operations[-2:]] == ["escalate", "withdraw"]
    assert operations[-2]["sla_state"] == "escalated"
    assert operations[-1]["state_before"] == "escalated"
    assert operations[-1]["state_after"] == "withdrawn"


def test_ao36_ct_002_break_glass_approval_requires_audit_reason(repository):
    approval = create_pending_approval(repository)

    approved = decide_approval_request(
        approval["approval_id"],
        action="approve",
        actor=approval["requester"],
        reason="Incident command approved emergency continuation.",
        repository=repository,
        break_glass=True,
        break_glass_reason="incident_commander_override",
    )

    assert approved["status"] == "approved"
    operation = repository.approval_operation_records()[-1]
    assert operation["operation"] == "break_glass_approve"
    assert operation["actor"] == approval["requester"]
    assert operation["break_glass_reason"] == "incident_commander_override"
    assert operation["summary"]["break_glass"] is True


def test_ao36_ct_002_approval_operation_keeps_legacy_action_contract_safe(repository):
    approval = create_pending_approval(repository)

    updated = decide_approval_request(
        approval["approval_id"],
        action="request_more_info",
        actor="security_1",
        reason="Need the original reviewer notes.",
        repository=repository,
    )

    assert updated["status"] == "needs_more_info"
    operation = repository.approval_operation_records()[-1]
    contract = get_contract("approval_operation.v1")
    assert operation["operation"] in contract.enum_fields["operation"]
    assert operation["state_after"] in contract.enum_fields["state_after"]


def test_ao36_ct_002_repeated_approval_operations_keep_full_history(repository):
    approval = create_pending_approval(repository)

    for reason in ("Need the rollout plan.", "Need reviewer acknowledgement."):
        decide_approval_request(
            approval["approval_id"],
            action="request_more_info",
            actor="security_1",
            reason=reason,
            repository=repository,
        )

    operations = repository.approval_operation_records()
    matching = [
        item for item in operations if item["approval_id"] == approval["approval_id"]
    ]
    assert [item["reason"] for item in matching] == [
        "Need the rollout plan.",
        "Need reviewer acknowledgement.",
    ]
    assert len({item["approval_decision_id"] for item in matching}) == 2
    assert len({item["operation_id"] for item in matching}) == 2


def test_ao36_ct_002_concurrent_approval_operations_get_unique_ids(repository):
    approval = create_pending_approval(repository)

    def request_more_info(index: int) -> None:
        decide_approval_request(
            approval["approval_id"],
            action="request_more_info",
            actor=f"security_{index}",
            reason=f"Need follow-up evidence {index}.",
            repository=repository,
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(request_more_info, range(8)))

    matching = [
        item
        for item in repository.approval_operation_records()
        if item["approval_id"] == approval["approval_id"]
    ]

    assert len(matching) == 8
    assert len({item["approval_decision_id"] for item in matching}) == 8
    assert len({item["operation_id"] for item in matching}) == 8
    assert {item["operation_sequence"] for item in matching} == set(range(1, 9))


def test_ao36_ct_003_policy_operations_projection_explains_canary(repository):
    register_policy_set_version(
        repository,
        policy_set_version="policy.v3",
        state="canary",
        risk_templates=["deploy_prod", "raw_evidence_access"],
        fallback_action="require_online",
        traffic_scope={"percent": 10, "agents": ["agent_1"]},
        owner="Security/IAM",
    )

    projection = build_policy_operations_projection(repository)

    assert projection["schema_version"] == "policy_operations_projection.v1"
    assert projection["active_version"] == ""
    assert projection["versions"][0]["policy_set_version"] == "policy.v3"
    assert projection["versions"][0]["state"] == "canary"
    assert projection["versions"][0]["deny_priority"]["deny_overrides_grant"] is True
    assert projection["versions"][0]["fallback_action"] == "require_online"
    assert projection["versions"][0]["summary"]["raw_payload_access"] == "forbidden"


def test_ao36_ct_003_policy_operations_projection_explains_rollback(repository):
    register_policy_set_version(
        repository,
        policy_set_version="policy.v2",
        state="active",
        risk_templates=["deploy_prod"],
        fallback_action="require_online",
    )
    register_policy_set_version(
        repository,
        policy_set_version="policy.v3",
        state="rolled_back",
        risk_templates=["deploy_prod"],
        fallback_action="block",
        rollback_from="policy.v3",
        rollback_reason="elevated false positives",
    )

    projection = build_policy_operations_projection(repository)
    rolled_back = {item["policy_set_version"]: item for item in projection["versions"]}[
        "policy.v3"
    ]

    assert projection["active_version"] == "policy.v2"
    assert rolled_back["state"] == "rolled_back"
    assert rolled_back["rollback_from"] == "policy.v3"
    assert rolled_back["rollback_reason"] == "elevated false positives"
    assert rolled_back["summary"]["rollback_recorded"] is True


def test_ao36_ct_003_policy_operations_projection_preserves_transition_history(
    repository,
):
    for state in ("canary", "active", "rolled_back"):
        register_policy_set_version(
            repository,
            policy_set_version="policy.v4",
            state=state,
            risk_templates=["deploy_prod"],
            fallback_action="block",
            rollback_from="policy.v4" if state == "rolled_back" else "",
            rollback_reason="canary rollback" if state == "rolled_back" else "",
        )

    projection = build_policy_operations_projection(repository)
    transitions = [
        item
        for item in projection["versions"]
        if item["policy_set_version"] == "policy.v4"
    ]

    assert [item["state"] for item in transitions] == [
        "canary",
        "active",
        "rolled_back",
    ]
    assert [item["transition_sequence"] for item in transitions] == [1, 2, 3]
    assert len({item["policy_set_version_record_id"] for item in transitions}) == 3


def test_ao36_ct_004_grant_lifecycle_tracks_consumption_and_binding(repository):
    grant = _issue_active_grant(repository, remaining_uses=2)
    consume_grant(
        grant["grant_id"],
        _policy_request_for_grant(grant),
        repository,
    )

    lifecycle = build_grant_lifecycle_view(grant["grant_id"], repository)

    assert lifecycle["schema_version"] == "grant_lifecycle.v1"
    assert lifecycle["status"] == "active"
    assert lifecycle["binding"]["agent_id"] == grant["agent_id"]
    assert lifecycle["binding"]["resource_scope"] == grant["resource_scope"]
    assert lifecycle["remaining_uses"] == 1
    assert lifecycle["consumption_summary"]["consumption_count"] == 1
    assert lifecycle["impact_summary"]["affected_runs"] == [grant["run_id"]]
    assert lifecycle["summary"]["raw_payload_access"] == "forbidden"


def test_ao36_ct_004_active_offline_grant_does_not_queue_owner_notification(
    repository,
):
    grant = _issue_active_grant(repository, offline_allowed=True)

    lifecycle = build_grant_lifecycle_view(grant["grant_id"], repository)

    assert lifecycle["status"] == "active"
    assert lifecycle["impact_summary"]["offline_allowed"] is True
    assert lifecycle["impact_summary"]["owner_notification_state"] == "not_required"


def test_ao36_ct_004_grant_lifecycle_records_revocation_impact(repository):
    grant = _issue_active_grant(repository, offline_allowed=True)

    revoked = revoke_grant(
        grant["grant_id"],
        repository,
        actor="security_1",
        reason="risk containment",
    )
    lifecycle = build_grant_lifecycle_view(grant["grant_id"], repository)

    assert revoked["status"] == "revoked"
    assert lifecycle["status"] == "revoked"
    assert lifecycle["revoked_by"] == "security_1"
    assert lifecycle["revocation_reason"] == "risk containment"
    assert lifecycle["impact_summary"]["offline_allowed"] is True
    assert lifecycle["impact_summary"]["owner_notification_state"] == "pending"


def _issue_active_grant(repository, **grant_overrides):
    approval = create_pending_approval(repository)
    approved = decide_approval_request(
        approval["approval_id"],
        action="approve",
        actor="security_1",
        reason="approved for deploy",
        repository=repository,
    )
    grant_request = grant_request_from_approval(
        approved,
        version=approved["version"],
        artifact_hash=approved["artifact_hash"],
        installation_id=approved["installation_id"],
        device_id=approved["device_id"],
        user_id=approved["user_id"],
        session_id=approved["session_id"],
        run_id=approved["run_id"],
        **grant_overrides,
    )
    return issue_grant(approved["approval_id"], grant_request, repository)


def _policy_request_for_grant(grant):
    return policy_request(
        policy_check_id=grant["policy_check_id"],
        version=grant["version"],
        artifact_hash=grant["artifact_hash"],
        installation_id=grant["installation_id"],
        device_id=grant["device_id"],
        user_id=grant["user_id"],
        session_id=grant["session_id"],
        run_id=grant["run_id"],
    )
