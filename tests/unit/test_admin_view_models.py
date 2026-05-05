from agentops.api.view_models import PAGES, STATES, build_admin_view_models, build_slo_snapshot, build_stage2_admin_view_models


def test_admin_view_models_cover_all_stage1_pages_and_states():
    models = build_admin_view_models()

    assert set(models) == set(PAGES)
    for page in PAGES:
        assert {state["state"] for state in models[page]} == set(STATES)


def test_each_state_has_required_actions_and_safe_permission_denied():
    models = build_admin_view_models()

    for states in models.values():
        for state in states:
            assert state["primary_action"]
            assert state["secondary_action"]
            assert state["owner_hint"]
            assert state["audit_id"] or state["request_id"]
            assert state["contains_raw_evidence"] is False
            if state["state"] == "permission_denied":
                assert state["denied_scope"]


def test_stage2_view_models_include_risk_triage_and_permission_scope():
    models = build_stage2_admin_view_models({"policy_check": build_slo_snapshot("policy_check", p95_ms=900, error_rate=0.02)})

    assert "Risk Triage" in models
    assert "pending" in {state["state"] for state in models["Approval Center"]}
    assert "redaction_failed" in {state["state"] for state in models["Evidence Explorer"]}
    permission_states = [state for states in models.values() for state in states if state["state"] == "permission_denied"]
    assert permission_states
    assert all(state["denied_scope"] for state in permission_states)
