"""Application assembly boundary.

Stage 1 keeps API handlers as importable Python callables so contract tests can
verify semantics without requiring an HTTP server dependency.
"""


def create_app() -> dict[str, str]:
    return {
        "ingestion": "POST /v1/events",
        "ingestion_compatibility_alias": "POST /v1/events/batch",
        "credentials": "POST /v1/bootstrap/credentials",
        "credential_status": "GET /v1/bootstrap/credentials/{bootstrap_id}",
        "credential_revoke": "POST /v1/bootstrap/credentials/{bootstrap_id}/revoke",
        "credential_reissue": "POST /v1/bootstrap/credentials/{bootstrap_id}/reissue",
        "evidence": "/v1/runs/{run_id}/evidence-summary",
        "policy": "/v1/policy/decision",
        "store_summary": "/v1/store-summary/{agent_id}",
        "agent_store_metadata": "POST /v1/agent-store/metadata",
        "agent_store_discovery": "/v1/agent-store/discovery",
        "run_audit": "/v1/runs/{run_id}/audit",
        "durable_audit_log": "append-only JSONL runtime audit boundary",
        "runtime_audit_query": "GET /v1/audit/runtime",
        "runtime_audit_export_bundle": "POST /v1/audit/runtime/export-bundle",
        "runtime_ingestion": "POST /v1/runtime/events",
        "runtime_run_detail": "GET /v1/runtime/runs/{run_id}",
        "runtime_trace_timeline": "GET /v1/runtime/runs/{run_id}/trace",
        "runtime_evidence_summary": "GET /v1/runtime/runs/{run_id}/evidence-summary",
        "runtime_health_summary": "GET /v1/runtime/agents/{agent_id}/versions/{version}/health-summary",
        "health": "/v1/health",
        "console_snapshot": "/v1/console/snapshot",
        "production_auth_boundary": "upstream headers: X-AgentOps-Principal, X-AgentOps-Roles, X-AgentOps-Scopes",
    }
