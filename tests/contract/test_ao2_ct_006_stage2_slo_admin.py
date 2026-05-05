from agentops.api.view_models import STAGE2_PAGES, build_slo_snapshot, build_stage2_admin_view_models


def test_missing_slo_data_is_unknown_not_healthy():
    snapshot = build_slo_snapshot("policy_check")

    assert snapshot["status"] == "unknown"
    assert snapshot["degrade_action"]
    assert snapshot["request_id"]


def test_policy_check_degraded_when_over_threshold():
    snapshot = build_slo_snapshot("policy_check", p95_ms=900, error_rate=0.02)

    assert snapshot["status"] == "degraded"
    assert snapshot["review_required"] is True
    assert "require_online" in snapshot["degrade_action"]


def test_stage2_admin_models_are_actionable_and_safe():
    models = build_stage2_admin_view_models(
        {
            "policy_check": build_slo_snapshot("policy_check", p95_ms=900, error_rate=0.02),
            "approval_service": build_slo_snapshot("approval_service", p95_ms=100, error_rate=0),
            "evidence_query": build_slo_snapshot("evidence_query", p95_ms=100, error_rate=0),
        }
    )

    assert set(models) == set(STAGE2_PAGES)
    assert {state["state"] for state in models["Approval Center"]} >= {
        "pending",
        "needs_more_info",
        "approved",
        "rejected",
        "expired",
        "revoked",
        "escalated",
    }
    assert {state["state"] for state in models["Evidence Explorer"]} >= {
        "summary_only",
        "pending_approval",
        "approved_limited",
        "expired",
        "redaction_failed",
    }
    assert {state["state"] for state in models["Risk Triage"]} >= {"policy_block", "approval_overdue", "evidence_failed", "quality_drop"}
    for states in models.values():
        for state in states:
            assert state["display_name"]
            assert state["plain_language"]
            assert state["primary_action"]
            assert state["secondary_action"]
            assert state["owner_hint"]
            assert state["audit_id"] or state["request_id"]
            assert state["degrade_action"] is not None
            assert state["contains_raw_evidence"] is False
            if state["state"] == "permission_denied":
                assert state["denied_scope"]
