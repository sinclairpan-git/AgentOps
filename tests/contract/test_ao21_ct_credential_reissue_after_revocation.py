import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Event, Thread
from time import sleep

import pytest

import agentops.api.credentials as credentials_api
from agentops.api.credentials import (
    get_credential_status,
    issue_credentials,
    reissue_credentials,
    revoke_credentials,
)
from agentops.api.ingestion import ingest_events_batch
from agentops.api.server import create_http_handler
from agentops.core.errors import AgentOpsError
from tests.contract.conftest import base_event

FIXTURES_DIR = Path("contracts/cross-project/fixtures")
FIXTURE_NOW = datetime.fromisoformat("2026-05-07T12:02:00+00:00")
REVOKE_NOW = datetime.fromisoformat("2026-05-07T12:10:00+00:00")
REISSUE_NOW = datetime.fromisoformat("2026-05-07T12:12:00+00:00")


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
        headers={"Idempotency-Key": "idem-fixture"},
    )


def revocation_request(**overrides) -> dict:
    request = {
        "schema_version": "agentops_credential_revocation.v1",
        "bootstrap_id": "boot-inst-fixture",
        "revocation_id": "revoke-inst-fixture",
        "revoked_by": "security-operator",
        "reason": "设备遗失",
        "scope": "credential_and_device_key",
    }
    request.update(overrides)
    return request


def reissue_handoff(
    bootstrap_id: str = "boot-inst-fixture-r1",
    issued_at: str = "2026-05-07T12:12:00+00:00",
    expires_at: str = "2026-05-07T12:42:00+00:00",
) -> dict:
    request = deepcopy(load_fixture("agentops_credential_handoff.v1.json"))
    request["bootstrap_id"] = bootstrap_id
    assertion = request["installation_assertion"]
    assertion["assertion_hash"] = "sha256:assertion-fixture-r1"
    assertion["nonce"] = "nonce-install-fixture-r1"
    assertion["issued_at"] = issued_at
    assertion["expires_at"] = expires_at
    assertion["signature"] = "sig-install-fixture-r1"
    device_proof = request["device_proof"]
    device_proof["assertion_hash"] = assertion["assertion_hash"]
    device_proof["nonce"] = "nonce-device-fixture-r1"
    device_proof["key_id"] = "device-key-fixture-r1"
    device_proof["issued_at"] = issued_at
    device_proof["expires_at"] = expires_at
    device_proof["signature"] = "sig-device-fixture-r1"
    return request


def reissue_request(**overrides) -> dict:
    request = {
        "schema_version": "agentops_credential_reissue.v1",
        "source_bootstrap_id": "boot-inst-fixture",
        "new_bootstrap_id": "boot-inst-fixture-r1",
        "reissue_id": "reissue-inst-fixture",
        "requested_by": "security-operator",
        "reason": "撤销后重新签发设备凭证",
        "credential_handoff": reissue_handoff(),
    }
    request.update(overrides)
    return request


def signature_test_event_for_reissue(**overrides):
    event = base_event(
        "stage_started",
        event_id="evt_signature_test_reissue",
        idempotency_key="signature-test:boot-inst-fixture-r1",
        user_id="user-1",
        agent_id="agent-1",
        agent_version="1.0.0",
        installation_id="inst-fixture",
        device_id="dev-fixture",
        session_id="sess-signature-test-r1",
        run_id="run-signature-test-r1",
        ingestion_token="token-fixture-r1",
    )
    event["event_type"] = "signature_test_event"
    event["span_id"] = "span_signature_test_r1"
    event["payload"] = {
        "bootstrap_id": "boot-inst-fixture-r1",
        "credential_id": "cred-fixture-r1",
        "token_id": "token-fixture-r1",
        "device_key_id": "device-key-fixture-r1",
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


def enterprise_event_for_reissue(**overrides):
    return base_event(
        "stage_started",
        event_id=overrides.pop("event_id", "evt_after_reissue"),
        idempotency_key=overrides.pop("idempotency_key", "stage-started:after-reissue"),
        user_id="user-1",
        agent_id="agent-1",
        agent_version="1.0.0",
        installation_id="inst-fixture",
        device_id="dev-fixture",
        session_id="sess-after-reissue",
        run_id="run-after-reissue",
        ingestion_token=overrides.pop("ingestion_token", "token-fixture-r1"),
        **overrides,
    )


def json_post(
    server: ThreadingHTTPServer,
    path: str,
    payload: dict,
    headers: dict[str, str] | None = None,
):
    connection = HTTPConnection(
        server.server_address[0], server.server_address[1], timeout=5
    )
    try:
        body = json.dumps(payload).encode("utf-8")
        request_headers = {
            "Content-Type": "application/json",
            "Origin": "http://127.0.0.1:5174",
        }
        request_headers.update(headers or {})
        connection.request("POST", path, body=body, headers=request_headers)
        response = connection.getresponse()
        payload_body = response.read().decode("utf-8")
        return response, json.loads(payload_body) if payload_body else {}
    finally:
        connection.close()


@pytest.fixture
def revoked_repository(repository):
    issue_fixture_credentials(repository)
    revoke_credentials(revocation_request(), repository, now=REVOKE_NOW)
    return repository


def test_ao21_ct_001_reissue_revoked_credential_returns_new_agentops_credential(
    revoked_repository,
):
    response = reissue_credentials(
        reissue_request(),
        revoked_repository,
        now=REISSUE_NOW,
        headers={"Idempotency-Key": "idem-reissue-fixture"},
    )

    assert response["schema_version"] == "agentops_credential_reissue.v1"
    assert response["old_credential_status"] == "revoked"
    assert response["credential_status"] == "active"
    assert response["bootstrap_status"] == "credential_issued"
    assert response["credential_id"] == "cred-fixture-r1"
    assert response["token_id"] == "token-fixture-r1"
    assert response["next_action"] == "send_signature_test_event"
    assert response["verified_loaded"] == "not_asserted"
    assert (
        get_credential_status(revoked_repository, "boot-inst-fixture-r1")[
            "credential_id"
        ]
        == "cred-fixture-r1"
    )
    source_status = get_credential_status(revoked_repository, "boot-inst-fixture")
    assert source_status["credential_status"] == "revoked"
    assert source_status["revocation_resolution"] == "reissued"
    assert source_status["reissued_bootstrap_id"] == "boot-inst-fixture-r1"


def test_ao21_ct_001b_reissue_uses_new_bootstrap_for_replacement_ids(
    revoked_repository,
):
    response = reissue_credentials(
        reissue_request(
            new_bootstrap_id="boot-reissue-fixture-alt",
            reissue_id="reissue-inst-fixture-alt",
            credential_handoff=reissue_handoff(bootstrap_id="boot-reissue-fixture-alt"),
        ),
        revoked_repository,
        now=REISSUE_NOW,
        headers={"Idempotency-Key": "idem-reissue-alt"},
    )

    assert response["credential_id"] == "cred-reissue-fixture-alt"
    assert response["token_id"] == "token-reissue-fixture-alt"
    assert response["token_id"] != "token-fixture"


def test_ao21_ct_001c_reissue_source_allows_only_one_replacement(revoked_repository):
    first = reissue_credentials(
        reissue_request(),
        revoked_repository,
        now=REISSUE_NOW,
        headers={"Idempotency-Key": "idem-reissue-fixture"},
    )
    handoff = reissue_handoff(bootstrap_id="boot-inst-fixture-r2")
    handoff["installation_assertion"]["assertion_hash"] = "sha256:assertion-fixture-r2"
    handoff["installation_assertion"]["nonce"] = "nonce-install-fixture-r2"
    handoff["installation_assertion"]["signature"] = "sig-install-fixture-r2"
    handoff["device_proof"]["assertion_hash"] = "sha256:assertion-fixture-r2"
    handoff["device_proof"]["nonce"] = "nonce-device-fixture-r2"
    handoff["device_proof"]["key_id"] = "device-key-fixture-r2"
    handoff["device_proof"]["signature"] = "sig-device-fixture-r2"

    with pytest.raises(AgentOpsError) as exc:
        reissue_credentials(
            reissue_request(
                new_bootstrap_id="boot-inst-fixture-r2",
                reissue_id="reissue-inst-fixture-r2",
                credential_handoff=handoff,
            ),
            revoked_repository,
            now=REISSUE_NOW,
            headers={"Idempotency-Key": "idem-reissue-fixture-r2"},
        )

    source_status = get_credential_status(revoked_repository, "boot-inst-fixture")
    assert first["credential_id"] == "cred-fixture-r1"
    assert exc.value.error_code == "CREDENTIAL_REISSUE_SOURCE_ALREADY_REISSUED"
    assert source_status["reissued_bootstrap_id"] == "boot-inst-fixture-r1"
    assert revoked_repository.get_bootstrap_session("boot-inst-fixture-r2") is None


def test_ao21_ct_001d_reissue_source_guard_is_atomic_under_parallel_requests(
    revoked_repository, monkeypatch
):
    original_issue_credentials = credentials_api.issue_credentials
    first_issue_entered = Event()
    release_first_issue = Event()

    def blocking_issue_credentials(request, repository, now=None, headers=None):
        if request.get("bootstrap_id") == "boot-inst-fixture-r1":
            first_issue_entered.set()
            assert release_first_issue.wait(timeout=5)
        return original_issue_credentials(request, repository, now=now, headers=headers)

    handoff = reissue_handoff(bootstrap_id="boot-inst-fixture-r2")
    handoff["installation_assertion"]["assertion_hash"] = "sha256:assertion-fixture-r2"
    handoff["installation_assertion"]["nonce"] = "nonce-install-fixture-r2"
    handoff["installation_assertion"]["signature"] = "sig-install-fixture-r2"
    handoff["device_proof"]["assertion_hash"] = "sha256:assertion-fixture-r2"
    handoff["device_proof"]["nonce"] = "nonce-device-fixture-r2"
    handoff["device_proof"]["key_id"] = "device-key-fixture-r2"
    handoff["device_proof"]["signature"] = "sig-device-fixture-r2"
    monkeypatch.setattr(
        credentials_api, "issue_credentials", blocking_issue_credentials
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(
            reissue_credentials,
            reissue_request(),
            revoked_repository,
            now=REISSUE_NOW,
            headers={"Idempotency-Key": "idem-reissue-fixture"},
        )
        assert first_issue_entered.wait(timeout=5)
        second_future = executor.submit(
            reissue_credentials,
            reissue_request(
                new_bootstrap_id="boot-inst-fixture-r2",
                reissue_id="reissue-inst-fixture-r2",
                credential_handoff=handoff,
            ),
            revoked_repository,
            now=REISSUE_NOW,
            headers={"Idempotency-Key": "idem-reissue-fixture-r2"},
        )
        sleep(0.05)
        assert not second_future.done()
        release_first_issue.set()
        first = first_future.result(timeout=5)
        with pytest.raises(AgentOpsError) as exc:
            second_future.result(timeout=5)

    assert first["credential_id"] == "cred-fixture-r1"
    assert exc.value.error_code == "CREDENTIAL_REISSUE_SOURCE_ALREADY_REISSUED"
    assert revoked_repository.get_bootstrap_session("boot-inst-fixture-r2") is None


def test_ao21_ct_002_reissued_credential_passes_signature_test_but_old_token_stays_revoked(
    revoked_repository,
):
    reissue_credentials(
        reissue_request(),
        revoked_repository,
        now=REISSUE_NOW,
        headers={"Idempotency-Key": "idem-reissue-fixture"},
    )

    accepted = ingest_events_batch(
        [signature_test_event_for_reissue()], revoked_repository
    )
    old_token_event = signature_test_event_for_reissue(
        event_id="evt_signature_test_old_token",
        idempotency_key="signature-test:old-token",
        ingestion_token="token-fixture",
        payload={"token_id": "token-fixture"},
    )
    rejected = ingest_events_batch([old_token_event], revoked_repository)

    assert accepted["accepted"] == ["evt_signature_test_reissue"]
    assert (
        get_credential_status(revoked_repository, "boot-inst-fixture-r1")[
            "bootstrap_status"
        ]
        == "signature_verified"
    )
    assert rejected["accepted"] == []
    assert rejected["rejected"][0]["error_code"] == "EVENT_CREDENTIAL_REVOKED"


def test_ao21_ct_003_reissue_requires_new_nonce_and_new_bootstrap(revoked_repository):
    request = reissue_request(
        new_bootstrap_id="boot-inst-fixture",
        credential_handoff=load_fixture("agentops_credential_handoff.v1.json"),
    )

    with pytest.raises(AgentOpsError) as exc:
        reissue_credentials(
            request,
            revoked_repository,
            now=REISSUE_NOW,
            headers={"Idempotency-Key": "idem-reissue-fixture"},
        )

    assert exc.value.error_code == "CREDENTIAL_REISSUE_TARGET_INVALID"


def test_ao21_ct_003b_reissue_rejects_reused_nonce_without_orphan_session(
    revoked_repository,
):
    handoff = reissue_handoff()
    handoff["installation_assertion"]["nonce"] = "nonce-fixture"
    request = reissue_request(credential_handoff=handoff)

    with pytest.raises(AgentOpsError) as exc:
        reissue_credentials(
            request,
            revoked_repository,
            now=REISSUE_NOW,
            headers={"Idempotency-Key": "idem-reissue-fixture"},
        )

    assert exc.value.error_code == "BOOTSTRAP_REPLAY_DETECTED"
    assert revoked_repository.get_bootstrap_session("boot-inst-fixture-r1") is None


def test_ao21_ct_003c_reissue_bad_handoff_parse_error_rolls_back_session(
    revoked_repository,
):
    malformed_handoff = reissue_handoff(expires_at="not-a-timestamp")

    with pytest.raises(AgentOpsError) as exc:
        reissue_credentials(
            reissue_request(credential_handoff=malformed_handoff),
            revoked_repository,
            now=REISSUE_NOW,
            headers={"Idempotency-Key": "idem-reissue-fixture-bad-time"},
        )

    retry = reissue_credentials(
        reissue_request(),
        revoked_repository,
        now=REISSUE_NOW,
        headers={"Idempotency-Key": "idem-reissue-fixture"},
    )

    assert exc.value.error_code == "CREDENTIAL_REISSUE_HANDOFF_INVALID"
    assert retry["credential_id"] == "cred-fixture-r1"
    assert (
        revoked_repository.get_bootstrap_session("boot-inst-fixture-r1")[
            "bootstrap_status"
        ]
        == "credential_issued"
    )


def test_ao21_ct_003d_reissue_naive_handoff_time_rolls_back_session(revoked_repository):
    malformed_handoff = reissue_handoff(issued_at="2026-05-07T12:12:00")

    with pytest.raises(AgentOpsError) as exc:
        reissue_credentials(
            reissue_request(credential_handoff=malformed_handoff),
            revoked_repository,
            now=REISSUE_NOW,
            headers={"Idempotency-Key": "idem-reissue-fixture-naive-time"},
        )

    retry = reissue_credentials(
        reissue_request(),
        revoked_repository,
        now=REISSUE_NOW,
        headers={"Idempotency-Key": "idem-reissue-fixture"},
    )

    assert exc.value.error_code == "CREDENTIAL_REISSUE_HANDOFF_INVALID"
    assert retry["credential_id"] == "cred-fixture-r1"
    assert (
        revoked_repository.get_bootstrap_session("boot-inst-fixture-r1")[
            "bootstrap_status"
        ]
        == "credential_issued"
    )


def test_ao21_ct_004_reissue_rejects_non_revoked_source(repository):
    issue_fixture_credentials(repository)

    with pytest.raises(AgentOpsError) as exc:
        reissue_credentials(
            reissue_request(),
            repository,
            now=REISSUE_NOW,
            headers={"Idempotency-Key": "idem-reissue-fixture"},
        )

    assert exc.value.error_code == "CREDENTIAL_REISSUE_SOURCE_NOT_REVOKED"


def test_ao21_ct_005_reissue_retry_returns_same_result(revoked_repository):
    request = reissue_request()

    first = reissue_credentials(
        request,
        revoked_repository,
        now=REISSUE_NOW,
        headers={"Idempotency-Key": "idem-reissue-fixture"},
    )
    second = reissue_credentials(
        request,
        revoked_repository,
        now=REISSUE_NOW,
        headers={"Idempotency-Key": "idem-reissue-fixture"},
    )

    assert first == second


def test_ao21_ct_005b_reissue_retry_stays_stable_after_replacement_revoked(
    revoked_repository,
):
    request = reissue_request()
    first = reissue_credentials(
        request,
        revoked_repository,
        now=REISSUE_NOW,
        headers={"Idempotency-Key": "idem-reissue-fixture"},
    )
    revoke_credentials(
        revocation_request(
            bootstrap_id="boot-inst-fixture-r1",
            revocation_id="revoke-inst-fixture-r1",
        ),
        revoked_repository,
        now=REISSUE_NOW + timedelta(minutes=2),
    )

    retry = reissue_credentials(
        request,
        revoked_repository,
        now=REISSUE_NOW,
        headers={"Idempotency-Key": "idem-reissue-fixture"},
    )
    replacement_status = get_credential_status(
        revoked_repository, "boot-inst-fixture-r1"
    )

    assert retry == first
    assert retry["credential_status"] == "active"
    assert retry["bootstrap_status"] == "credential_issued"
    assert replacement_status["credential_status"] == "revoked"


def test_ao21_ct_006_http_reissue_route_returns_json_and_cors(revoked_repository):
    http_now = datetime.now(UTC)
    http_request = reissue_request(
        credential_handoff=reissue_handoff(
            issued_at=http_now.isoformat(),
            expires_at=(http_now + timedelta(minutes=30)).isoformat(),
        )
    )
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), create_http_handler(revoked_repository)
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        response, payload = json_post(
            server,
            "/v1/bootstrap/credentials/boot-inst-fixture/reissue",
            {
                key: value
                for key, value in http_request.items()
                if key != "source_bootstrap_id"
            },
            headers={"Idempotency-Key": "idem-reissue-fixture"},
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert response.status == 200
    assert response.getheader("Access-Control-Allow-Origin") == "http://127.0.0.1:5174"
    assert payload["schema_version"] == "agentops_credential_reissue.v1"
    assert payload["credential_id"] == "cred-fixture-r1"


def test_ao21_ct_007_reissued_identity_requires_replacement_token(revoked_repository):
    reissue_credentials(
        reissue_request(),
        revoked_repository,
        now=REISSUE_NOW,
        headers={"Idempotency-Key": "idem-reissue-fixture"},
    )

    accepted = ingest_events_batch([enterprise_event_for_reissue()], revoked_repository)
    rejected = ingest_events_batch(
        [
            enterprise_event_for_reissue(
                event_id="evt_after_reissue_random_token",
                idempotency_key="stage-started:after-reissue-random-token",
                ingestion_token="token-random",
            )
        ],
        revoked_repository,
    )

    assert accepted["accepted"] == ["evt_after_reissue"]
    assert rejected["accepted"] == []
    assert rejected["rejected"][0]["error_code"] == "EVENT_CREDENTIAL_REVOKED"


def test_ao21_ct_008_revocation_check_follows_replacement_chain(revoked_repository):
    reissue_credentials(
        reissue_request(),
        revoked_repository,
        now=REISSUE_NOW,
        headers={"Idempotency-Key": "idem-reissue-fixture"},
    )
    revoke_credentials(
        revocation_request(
            bootstrap_id="boot-inst-fixture-r1",
            revocation_id="revoke-inst-fixture-r1",
        ),
        revoked_repository,
        now=REISSUE_NOW + timedelta(minutes=2),
    )
    handoff = reissue_handoff(bootstrap_id="boot-inst-fixture-r2")
    handoff["installation_assertion"]["assertion_hash"] = "sha256:assertion-fixture-r2"
    handoff["installation_assertion"]["nonce"] = "nonce-install-fixture-r2"
    handoff["installation_assertion"]["issued_at"] = "2026-05-07T12:14:00+00:00"
    handoff["installation_assertion"]["expires_at"] = "2026-05-07T12:44:00+00:00"
    handoff["installation_assertion"]["signature"] = "sig-install-fixture-r2"
    handoff["device_proof"]["assertion_hash"] = "sha256:assertion-fixture-r2"
    handoff["device_proof"]["nonce"] = "nonce-device-fixture-r2"
    handoff["device_proof"]["key_id"] = "device-key-fixture-r2"
    handoff["device_proof"]["issued_at"] = "2026-05-07T12:14:00+00:00"
    handoff["device_proof"]["expires_at"] = "2026-05-07T12:44:00+00:00"
    handoff["device_proof"]["signature"] = "sig-device-fixture-r2"
    reissue_credentials(
        reissue_request(
            source_bootstrap_id="boot-inst-fixture-r1",
            new_bootstrap_id="boot-inst-fixture-r2",
            reissue_id="reissue-inst-fixture-r2",
            credential_handoff=handoff,
        ),
        revoked_repository,
        now=REISSUE_NOW + timedelta(minutes=2),
        headers={"Idempotency-Key": "idem-reissue-fixture-r2"},
    )

    accepted = ingest_events_batch(
        [
            enterprise_event_for_reissue(
                event_id="evt_after_second_reissue",
                idempotency_key="stage-started:after-second-reissue",
                ingestion_token="token-fixture-r2",
            )
        ],
        revoked_repository,
    )
    rejected = ingest_events_batch(
        [
            enterprise_event_for_reissue(
                event_id="evt_after_second_reissue_stale_token",
                idempotency_key="stage-started:after-second-reissue-stale-token",
                ingestion_token="token-fixture-r1",
            )
        ],
        revoked_repository,
    )

    assert accepted["accepted"] == ["evt_after_second_reissue"]
    assert rejected["accepted"] == []
    assert rejected["rejected"][0]["error_code"] == "EVENT_CREDENTIAL_REVOKED"
