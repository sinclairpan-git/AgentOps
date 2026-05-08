from agentops.api.console_snapshot import build_console_snapshot


def _contains_forbidden(value):
    forbidden = {
        "raw_payload",
        "download_url",
        "raw_url",
        "raw_access_url",
        "original_url",
        "pullRequestBody",
        "pull_request_body",
        "diff",
        "patch",
    }
    if isinstance(value, dict):
        return any(
            key in forbidden or _contains_forbidden(item) for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_forbidden(item) for item in value)
    if isinstance(value, str):
        return "http://" in value or "https://" in value
    return False


def test_ao15_ct_001_snapshot_includes_sdlc_run_workbench_sections():
    workbench = build_console_snapshot()["consoleData"]["sdlcRunWorkbench"]

    assert set(workbench) == {
        "summary",
        "reporter",
        "outbox",
        "eligibility",
        "guardrails",
    }
    assert workbench["summary"]["proof_state"] == "unverified"
    assert workbench["summary"]["dry_run_state"] == "dry_run_passed"
    assert "不构成 verified_loaded" in workbench["summary"]["safety_note"]
    assert workbench["reporter"]
    assert workbench["outbox"]
    assert workbench["eligibility"]


def test_ao15_ct_002_reporter_rows_bind_sdlc_runs_and_stay_unverified_without_machine_proof():
    data = build_console_snapshot()["consoleData"]
    runs = {item["id"] for item in data["sdlcRuns"]}
    reporter = data["sdlcRunWorkbench"]["reporter"]

    assert {item["run_id"] for item in reporter} == runs
    for item in reporter:
        assert item["reporter_status"] != "active"
        assert item["credential_status"] != "active"
        assert item["source_signed"] != "active"
        assert item["identity_confidence"] == "unverified"
        assert "只读 Reporter 摘要" in item["safety_note"]


def test_ao15_ct_003_outbox_rows_are_read_only_and_do_not_fake_delivery():
    workbench = build_console_snapshot()["consoleData"]["sdlcRunWorkbench"]

    for item in workbench["outbox"]:
        assert item["outbox_status"] == "pending"
        assert item["sequence_state"] == "pending"
        assert item["pending_events"] != "0"
        assert item["oldest_pending_age"] != "0 分钟"
        assert "不在 Console 执行 Outbox Replay" in item["replay_boundary"]
        assert "不提供重放按钮" in item["safety_note"]


def test_ao15_ct_004_l5_eligibility_explains_failed_conditions():
    workbench = build_console_snapshot()["consoleData"]["sdlcRunWorkbench"]

    for item in workbench["eligibility"]:
        assert item["evidence_level"] != "L5"
        assert item["l5_result"] != "healthy"
        assert item["failed_conditions"] != "无"
        assert item["governance_loaded"] == "unverified"
        assert item["outbox_delivered"] == "pending"
        assert "verified_loaded" in item["next_action"]


def test_ao15_ct_005_sdlc_run_workbench_does_not_expose_raw_or_url_fields():
    workbench = build_console_snapshot()["consoleData"]["sdlcRunWorkbench"]

    assert not _contains_forbidden(workbench)
    assert "原始载荷" in " ".join(workbench["guardrails"])
