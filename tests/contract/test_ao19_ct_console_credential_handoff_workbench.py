import json
from datetime import datetime
from pathlib import Path

from agentops.api.console_snapshot import build_console_snapshot
from agentops.api.credentials import issue_credentials
from agentops.api.ingestion import ingest_events_batch
from agentops.storage.repository import InMemoryRepository
from tests.contract.conftest import base_event

FIXTURES_DIR = Path("contracts/cross-project/fixtures")
FIXTURE_NOW = datetime.fromisoformat("2026-05-07T12:02:00+00:00")


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


def issue_fixture_credentials(repository: InMemoryRepository):
    repository.add_bootstrap_session(bootstrap_session())
    return issue_credentials(
        load_fixture("agentops_credential_handoff.v1.json"),
        repository,
        now=FIXTURE_NOW,
        headers={"Idempotency-Key": "idem-fixture"},
    )


def signature_test_event():
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
    return event


def contains_key(value, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(contains_key(child, key) for child in value.values())
    if isinstance(value, list):
        return any(contains_key(child, key) for child in value)
    return False


def test_ao19_ct_001_console_declares_credential_handoff_route_and_shape():
    snapshot = build_console_snapshot()

    assert any(route["id"] == "credential-handoff" and route["label"] == "凭证联调" for route in snapshot["routes"])
    assert set(snapshot["consoleData"]["credentialHandoff"]) == {"summary", "sessions", "guardrails"}
    assert snapshot["consoleData"]["credentialHandoff"]["summary"]["schema_version"] == "agentops_credential_status.v1"


def test_ao19_ct_002_repository_snapshot_shows_agentops_status_without_store_inference(repository):
    issue_fixture_credentials(repository)

    workbench = build_console_snapshot(repository=repository)["consoleData"]["credentialHandoff"]
    row = workbench["sessions"][0]

    assert workbench["summary"]["bootstrap_count"] == 1
    assert workbench["summary"]["credential_issued"] == 1
    assert workbench["summary"]["signature_verified"] == 0
    assert workbench["summary"]["agentops_fact_owner"] == "agentops"
    assert workbench["summary"]["agent_store_boundary"] == "display_only_no_active_inference"
    assert row["bootstrap_status"] == "credential_issued"
    assert row["token_id"] == "已隐藏"
    assert row["next_action"] == "send_signature_test_event"
    assert row["agent_store_consumer_boundary"] == "display_only_no_active_inference"
    assert row["forbidden_actions"] == "infer_active,issue_credential,issue_ingestion_token,issue_device_key"
    assert row["verified_loaded"] == "not_asserted"
    assert row["l5_status"] == "not_asserted"


def test_ao19_ct_003_signature_verified_is_display_result_not_verified_loaded(repository):
    issue_fixture_credentials(repository)
    ingest_events_batch([signature_test_event()], repository)

    workbench = build_console_snapshot(repository=repository)["consoleData"]["credentialHandoff"]
    row = workbench["sessions"][0]

    assert workbench["summary"]["signature_verified"] == 1
    assert row["bootstrap_status"] == "signature_verified"
    assert row["next_action"] == "display_activation_result"
    assert row["signature_test_event_id"] == "evt_signature_test"
    assert row["verified_loaded"] == "not_asserted"
    assert row["l5_status"] == "not_asserted"


def test_ao19_ct_004_credential_workbench_has_no_secret_or_raw_material(repository):
    issue_fixture_credentials(repository)

    workbench = build_console_snapshot(repository=repository)["consoleData"]["credentialHandoff"]

    for forbidden in ("token_value", "private_key", "raw_payload", "download_url", "raw_url", "signature"):
        assert not contains_key(workbench, forbidden)
    assert "token-fixture" not in str(workbench)
    assert "不得本地推导 active" in " ".join(workbench["guardrails"])
