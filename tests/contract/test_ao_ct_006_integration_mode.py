from agentops.api.ingestion import ingest_events_batch
from tests.contract.conftest import base_event


def test_enterprise_managed_event_enters_managed_path(repository):
    event = base_event("stage_started")

    result = ingest_events_batch([event], repository)

    assert result["accepted"] == ["evt_stage_started"]
    assert repository.raw_events["evt_stage_started"]["evidence_mode"] == "managed"


def test_custom_sink_is_imported_evidence(repository):
    event = base_event(
        "stage_started",
        event_id="evt_custom",
        idempotency_key="custom:run_1",
        integration_mode="custom_sink",
        source_trust_level="imported",
        sink_id="sink_1",
        sink_capability_id="cap_1",
        external_subject="external_user",
    )
    event.pop("signature")

    result = ingest_events_batch([event], repository)

    assert result["accepted"] == ["evt_custom"]
    assert repository.raw_events["evt_custom"]["evidence_mode"] == "imported"


def test_standalone_remote_event_is_imported_not_l5(repository):
    event = base_event(
        "stage_started",
        event_id="evt_standalone",
        idempotency_key="standalone:run_1",
        integration_mode="standalone",
        enterprise_state="not_detected",
        source_trust_level="declared",
        local_subject="local-user",
        local_workspace_hash="sha256:workspace",
        local_report_uri="file://local/report.json",
    )
    event.pop("signature")

    result = ingest_events_batch([event], repository)

    assert result["accepted"] == ["evt_standalone"]
    assert repository.raw_events["evt_standalone"]["evidence_mode"] == "imported"


def test_unknown_integration_mode_is_rejected(repository):
    event = base_event("stage_started", integration_mode="unknown")

    result = ingest_events_batch([event], repository)

    assert result["rejected"][0]["error_code"] == "INTEGRATION_MODE_UNSUPPORTED"
