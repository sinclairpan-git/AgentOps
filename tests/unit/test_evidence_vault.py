from agentops.api.evidence_vault import get_evidence_vault_summary


def test_denied_raw_grant_does_not_approve_summary():
    summary = get_evidence_vault_summary(
        evidence_id="ev_1",
        run_id="run_1",
        payload_hash="sha256:evidence",
        raw_access_grant={"status": "revoked", "expires_at": "2026-05-05T00:00:00Z"},
    )

    assert summary["raw_access_state"] == "denied"
    assert "raw_payload" not in summary


def test_default_summary_has_safe_redacted_placeholder():
    summary = get_evidence_vault_summary(
        evidence_id="ev_1",
        run_id="run_1",
        payload_hash="sha256:evidence",
    )

    assert summary["redacted_summary"]["summary"] == "No sensitive evidence included."
