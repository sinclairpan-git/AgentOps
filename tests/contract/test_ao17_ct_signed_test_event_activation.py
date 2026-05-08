import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import pytest

from agentops.api.credentials import issue_credentials
from agentops.api.ingestion import ingest_events_batch
from tests.contract.conftest import base_event

FIXTURES_DIR = Path("contracts/cross-project/fixtures")
FIXTURE_NOW = datetime.fromisoformat("2026-05-07T12:02:00+00:00")
HEADERS = {"Idempotency-Key": "idem-fixture"}


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def bootstrap_session() -> dict:
    return {
        "bootstrap_id": "boot-inst-fixture",
        "installation_id": "inst-fixture",
        "device_id": "dev-fixture",
        "user_id": "user-1",
        "artifact_hash": "sha256:first",
        "issuer": "agent-store",
        "status": "authenticated",
        "expires_at": "2026-05-07T12:30:00+00:00",
    }


def issue_fixture_credentials(repository):
    repository.add_bootstrap_session(bootstrap_session())
    return issue_credentials(
        load_fixture("agentops_credential_handoff.v1.json"),
        repository,
        now=FIXTURE_NOW,
        headers=HEADERS,
    )


def signature_test_event(**overrides):
    event = base_event(
        "stage_started",
        event_id="evt_signature_test",
        idempotency_key="signature-test:boot-inst-fixture",
        user_id="user-1",
        agent_id="agent-1",
        agent_version="1.0.0",
        installation_id="inst-fixture",
        device_id="dev-fixture",
        session_id="sess-signature-test",
        run_id="run-signature-test",
        ingestion_token="token-fixture",
    )
    event["event_type"] = "signature_test_event"
    event["span_id"] = "span_signature_test"
    event["payload"] = {
        "bootstrap_id": "boot-inst-fixture",
        "credential_id": "cred-fixture",
        "token_id": "token-fixture",
        "device_key_id": "device-key-fixture",
        "installation_id": "inst-fixture",
        "device_id": "dev-fixture",
        "next_action": "send_signature_test_event",
    }
    for key, value in overrides.items():
        if key == "payload":
            event["payload"] = {**event["payload"], **value}
        else:
            event[key] = value
    return event


def test_ao17_cct_004_signed_test_event_verifies_bootstrap(repository):
    credentials = issue_fixture_credentials(repository)

    result = ingest_events_batch([signature_test_event()], repository)

    assert credentials["bootstrap_status"] == "credential_issued"
    assert result["accepted"] == ["evt_signature_test"]
    assert result["rejected"] == []
    assert repository.raw_events["evt_signature_test"]["evidence_mode"] == "managed"
    assert repository.get_bootstrap_session("boot-inst-fixture")["status"] == "verified"
    assert (
        repository.get_bootstrap_session("boot-inst-fixture")["bootstrap_status"]
        == "signature_verified"
    )
    assert (
        repository.credentials_by_bootstrap["boot-inst-fixture"]["bootstrap_status"]
        == "signature_verified"
    )


def test_ao17_cct_004_missing_credential_is_rejected(repository):
    repository.add_bootstrap_session(bootstrap_session())

    result = ingest_events_batch([signature_test_event()], repository)

    assert result["accepted"] == []
    assert result["rejected"][0]["error_code"] == "SIGNATURE_TEST_CREDENTIAL_NOT_FOUND"
    assert (
        repository.get_bootstrap_session("boot-inst-fixture")["status"]
        == "authenticated"
    )


def test_ao17_cct_004_token_mismatch_is_rejected(repository):
    issue_fixture_credentials(repository)
    event = signature_test_event(
        ingestion_token="token-other", payload={"token_id": "token-other"}
    )

    result = ingest_events_batch([event], repository)

    assert result["rejected"][0]["error_code"] == "EVENT_INGESTION_TOKEN_MISMATCH"
    assert (
        repository.get_bootstrap_session("boot-inst-fixture")["status"]
        == "credential_issued"
    )


def test_ao17_cct_004_device_key_inactive_is_rejected(repository):
    issue_fixture_credentials(repository)
    event = signature_test_event(device_key_status="revoked")

    result = ingest_events_batch([event], repository)

    assert result["rejected"][0]["error_code"] == "EVENT_DEVICE_KEY_INACTIVE"
    assert (
        repository.get_bootstrap_session("boot-inst-fixture")["status"]
        == "credential_issued"
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("installation_id", "inst-other"),
        ("device_id", "dev-other"),
    ],
)
def test_ao17_cct_004_identity_mismatch_is_rejected(repository, field, value):
    issue_fixture_credentials(repository)
    event = signature_test_event(**{field: value, "payload": {field: value}})

    result = ingest_events_batch([event], repository)

    assert result["rejected"][0]["error_code"] == "EVENT_IDENTITY_MISMATCH"
    assert (
        repository.get_bootstrap_session("boot-inst-fixture")["status"]
        == "credential_issued"
    )


def test_ao17_cct_004_replayed_idempotency_key_does_not_duplicate(repository):
    issue_fixture_credentials(repository)
    first_event = signature_test_event()
    replay_event = deepcopy(first_event)
    replay_event["event_id"] = "evt_signature_test_replay"

    first = ingest_events_batch([first_event], repository)
    second = ingest_events_batch([replay_event], repository)

    assert first["accepted"] == ["evt_signature_test"]
    assert second["deduplicated"] == ["evt_signature_test_replay"]
    assert len(repository.raw_events) == 1
    assert (
        repository.get_bootstrap_session("boot-inst-fixture")["bootstrap_status"]
        == "signature_verified"
    )


def test_ao17_cct_004_missing_payload_field_is_invalid(repository):
    issue_fixture_credentials(repository)
    event = signature_test_event()
    event["payload"].pop("device_key_id")

    result = ingest_events_batch([event], repository)

    assert result["rejected"][0]["error_code"] == "EVENT_PAYLOAD_INVALID"
    assert (
        repository.get_bootstrap_session("boot-inst-fixture")["status"]
        == "credential_issued"
    )
