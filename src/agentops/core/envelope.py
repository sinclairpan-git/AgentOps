"""EventEnvelope v1 validation and ingestion semantics."""

from __future__ import annotations

from typing import Any

from agentops.core.errors import AgentOpsError


L5_PAYLOAD_REQUIRED_FIELDS: dict[str, set[str]] = {
    "stage_started": {
        "stage_id",
        "stage_name",
        "stage_order",
        "session_id",
        "run_id",
        "workitem",
        "repo",
        "started_at",
        "adapter_state",
    },
    "stage_completed": {
        "stage_id",
        "status",
        "completed_at",
        "duration_ms",
        "artifacts",
        "verification_refs",
        "violation_count",
    },
    "gate_result": {
        "gate_id",
        "gate_name",
        "result",
        "evaluated_at",
        "blocking",
        "rule_results",
        "suggested_action",
    },
    "verification_result": {
        "verification_id",
        "verification_type",
        "command_or_job",
        "status",
        "commit",
        "artifact_hash",
        "freshness",
        "logs_ref",
    },
    "violation_scan_completed": {
        "scan_id",
        "stage_id",
        "status",
        "violation_count",
        "ruleset_version",
        "completed_at",
    },
    "artifact_generated": {
        "artifact_id",
        "artifact_type",
        "uri_or_hash",
        "data_classification",
        "retention_policy",
        "linked_commit",
    },
    "generation_snapshot": {
        "snapshot_id",
        "input_hash",
        "output_hash",
        "patch_hash",
        "redaction_policy",
        "model_ref",
        "prompt_template_version",
    },
    "l5_eligibility_input": {
        "run_id",
        "conditions",
        "outbox_status",
        "policy_state_known",
        "enforcement_mode",
        "failed_conditions",
    },
}

SIGNATURE_TEST_EVENT_TYPE = "signature_test_event"
SIGNATURE_TEST_PAYLOAD_REQUIRED_FIELDS = {
    "bootstrap_id",
    "credential_id",
    "token_id",
    "device_key_id",
    "installation_id",
    "device_id",
    "next_action",
}


BASE_REQUIRED_FIELDS = {
    "event_id",
    "schema_version",
    "event_type",
    "event_type_version",
    "timestamp",
    "integration_mode",
    "enterprise_state",
    "trace_id",
    "span_id",
    "sequence_no",
    "idempotency_key",
    "data_classification",
    "redaction_policy",
    "payload_hash",
    "payload",
}

ENTERPRISE_REQUIRED_FIELDS = {
    "user_id",
    "identity_confidence",
    "agent_id",
    "agent_version",
    "installation_id",
    "device_id",
    "session_id",
    "run_id",
    "signature",
    "source_trust_level",
    "ingestion_token",
    "credential_status",
    "device_key_status",
}

STANDALONE_REQUIRED_FIELDS = {
    "local_subject",
    "local_workspace_hash",
    "local_report_uri",
}
CUSTOM_SINK_REQUIRED_FIELDS = {"sink_id", "sink_capability_id", "external_subject"}


def validate_event_envelope(event: dict[str, Any]) -> None:
    _require_fields(event, BASE_REQUIRED_FIELDS, "EVENT_SCHEMA_INVALID")

    if event["schema_version"] != "event-envelope.v1":
        raise AgentOpsError(
            "EVENT_SCHEMA_UNSUPPORTED", "Unsupported event envelope schema."
        )

    integration_mode = event["integration_mode"]
    if integration_mode == "unknown":
        raise AgentOpsError(
            "INTEGRATION_MODE_UNSUPPORTED", "Unknown integration_mode is not accepted."
        )

    if integration_mode == "enterprise_managed":
        _validate_enterprise_event(event)
    elif integration_mode == "standalone":
        _require_fields(event, STANDALONE_REQUIRED_FIELDS, "EVENT_SCHEMA_INVALID")
        if event["enterprise_state"] != "not_detected":
            raise AgentOpsError(
                "EVENT_SCHEMA_INVALID",
                "standalone events must use enterprise_state=not_detected.",
            )
    elif integration_mode == "custom_sink":
        _require_fields(event, CUSTOM_SINK_REQUIRED_FIELDS, "EVENT_SCHEMA_INVALID")
    else:
        raise AgentOpsError(
            "INTEGRATION_MODE_UNSUPPORTED", "Unsupported integration_mode."
        )

    _validate_l5_payload(event)
    _validate_signature_test_payload(event)


def evidence_mode_for(event: dict[str, Any]) -> str:
    if event["integration_mode"] == "enterprise_managed":
        return "managed"
    return "imported"


def _validate_enterprise_event(event: dict[str, Any]) -> None:
    missing_signature = not event.get("signature")
    if missing_signature:
        raise AgentOpsError(
            "EVENT_SIGNATURE_REQUIRED", "enterprise_managed events require signature."
        )

    _require_fields(event, ENTERPRISE_REQUIRED_FIELDS, "EVENT_SCHEMA_INVALID")
    if event.get("identity_confidence") != "verified":
        raise AgentOpsError(
            "EVENT_IDENTITY_NOT_VERIFIED",
            "enterprise_managed events require verified identity.",
        )
    if event.get("source_trust_level") != "verified":
        raise AgentOpsError(
            "EVENT_SOURCE_NOT_VERIFIED",
            "enterprise_managed events require verified source trust.",
        )
    if event.get("credential_status") != "active":
        raise AgentOpsError(
            "EVENT_CREDENTIAL_INACTIVE",
            "enterprise_managed events require active credential.",
        )
    if event.get("device_key_status") != "active":
        raise AgentOpsError(
            "EVENT_DEVICE_KEY_INACTIVE",
            "enterprise_managed events require active device key.",
        )


def _validate_l5_payload(event: dict[str, Any]) -> None:
    required = L5_PAYLOAD_REQUIRED_FIELDS.get(event["event_type"])
    if not required:
        return

    payload = event.get("payload")
    if not isinstance(payload, dict):
        raise AgentOpsError(
            "EVENT_PAYLOAD_INVALID", "L5 core event payload must be an object."
        )
    _require_fields(payload, required, "EVENT_PAYLOAD_INVALID")


def _validate_signature_test_payload(event: dict[str, Any]) -> None:
    if event["event_type"] != SIGNATURE_TEST_EVENT_TYPE:
        return

    payload = event.get("payload")
    if not isinstance(payload, dict):
        raise AgentOpsError(
            "EVENT_PAYLOAD_INVALID", "signature_test_event payload must be an object."
        )
    _require_fields(
        payload, SIGNATURE_TEST_PAYLOAD_REQUIRED_FIELDS, "EVENT_PAYLOAD_INVALID"
    )


def _require_fields(data: dict[str, Any], fields: set[str], error_code: str) -> None:
    missing = sorted(
        field for field in fields if field not in data or data[field] in (None, "")
    )
    if missing:
        raise AgentOpsError(
            error_code, f"Missing required fields: {', '.join(missing)}."
        )
