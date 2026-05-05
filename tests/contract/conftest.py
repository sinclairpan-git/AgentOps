from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from agentops.storage.repository import InMemoryRepository


@pytest.fixture
def repository() -> InMemoryRepository:
    return InMemoryRepository()


def base_event(event_type: str = "stage_started", **overrides):
    event = {
        "event_id": f"evt_{event_type}",
        "schema_version": "event-envelope.v1",
        "event_type": event_type,
        "event_type_version": "1.0",
        "timestamp": "2026-05-05T00:00:00Z",
        "integration_mode": "enterprise_managed",
        "enterprise_state": "active",
        "user_id": "user_1",
        "identity_confidence": "verified",
        "agent_id": "agent.ai-sdlc",
        "agent_version": "1.0.0",
        "installation_id": "inst_1",
        "device_id": "dev_1",
        "session_id": "sess_1",
        "run_id": "run_1",
        "trace_id": "trace_1",
        "span_id": f"span_{event_type}",
        "sequence_no": 1,
        "idempotency_key": f"{event_type}:run_1",
        "source_trust_level": "verified",
        "signature": "sig_valid",
        "data_classification": "internal",
        "redaction_policy": "repo_default",
        "payload_hash": "sha256:payload",
        "payload": payload_for(event_type),
    }
    event.update(overrides)
    return event


def payload_for(event_type: str):
    payloads = {
        "stage_started": {
            "stage_id": "refine",
            "stage_name": "refine",
            "stage_order": 1,
            "session_id": "sess_1",
            "run_id": "run_1",
            "workitem": "WI-1",
            "repo": "AgentOps",
            "started_at": "2026-05-05T00:00:00Z",
            "adapter_state": "verified_loaded",
        },
        "stage_completed": {
            "stage_id": "refine",
            "status": "passed",
            "completed_at": "2026-05-05T00:01:00Z",
            "duration_ms": 60000,
            "artifacts": ["spec.md"],
            "verification_refs": ["gate_refine"],
            "violation_count": 0,
        },
        "gate_result": {
            "gate_id": "gate_refine",
            "gate_name": "refine",
            "result": "PASS",
            "evaluated_at": "2026-05-05T00:01:00Z",
            "blocking": False,
            "rule_results": [],
            "suggested_action": "continue",
        },
        "verification_result": {
            "verification_id": "ver_1",
            "verification_type": "pytest",
            "command_or_job": "pytest",
            "status": "passed",
            "commit": "local",
            "artifact_hash": "sha256:artifact",
            "freshness": "fresh",
            "logs_ref": "logs://local",
        },
        "violation_scan_completed": {
            "scan_id": "scan_1",
            "stage_id": "refine",
            "status": "passed",
            "violation_count": 0,
            "ruleset_version": "1.0",
            "completed_at": "2026-05-05T00:01:00Z",
        },
        "artifact_generated": {
            "artifact_id": "artifact_1",
            "artifact_type": "spec",
            "uri_or_hash": "sha256:artifact",
            "data_classification": "internal",
            "retention_policy": "default-90d",
            "linked_commit": "local",
        },
        "generation_snapshot": {
            "snapshot_id": "snap_1",
            "input_hash": "sha256:input",
            "output_hash": "sha256:output",
            "patch_hash": "sha256:patch",
            "redaction_policy": "repo_default",
            "model_ref": "codex",
            "prompt_template_version": "1.0",
        },
        "l5_eligibility_input": {
            "run_id": "run_1",
            "conditions": {},
            "outbox_status": "delivered",
            "policy_state_known": True,
            "enforcement_mode": "observe",
            "failed_conditions": [],
        },
    }
    return dict(payloads[event_type])


def future_time(minutes: int = 10) -> str:
    return (datetime.now(UTC) + timedelta(minutes=minutes)).isoformat()


def past_time(minutes: int = 10) -> str:
    return (datetime.now(UTC) - timedelta(minutes=minutes)).isoformat()
