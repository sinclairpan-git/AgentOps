from agentops.api.ingestion import ingest_events_batch
from tests.contract.conftest import base_event


def test_signed_enterprise_event_is_written(repository):
    result = ingest_events_batch([base_event("stage_started")], repository)

    assert result["accepted"] == ["evt_stage_started"]
    assert result["rejected"] == []
    assert "evt_stage_started" in repository.raw_events


def test_replayed_idempotency_key_does_not_duplicate(repository):
    event = base_event("stage_started")

    first = ingest_events_batch([event], repository)
    second = ingest_events_batch([dict(event, event_id="evt_replay")], repository)

    assert first["accepted"] == ["evt_stage_started"]
    assert second["deduplicated"] == ["evt_replay"]
    assert len(repository.raw_events) == 1


def test_missing_signature_returns_contract_error(repository):
    event = base_event("stage_started")
    event.pop("signature")

    result = ingest_events_batch([event], repository)

    assert result["accepted"] == []
    assert result["rejected"][0]["error_code"] == "EVENT_SIGNATURE_REQUIRED"


def test_l5_core_payload_missing_required_field_is_invalid(repository):
    event = base_event("stage_started")
    event["payload"].pop("adapter_state")

    result = ingest_events_batch([event], repository)

    assert result["rejected"][0]["error_code"] == "EVENT_PAYLOAD_INVALID"


def test_enterprise_event_requires_verified_source_and_active_credential(repository):
    event = base_event("stage_started", credential_status="revoked")

    result = ingest_events_batch([event], repository)

    assert result["rejected"][0]["error_code"] == "EVENT_CREDENTIAL_INACTIVE"
