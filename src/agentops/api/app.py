"""Application assembly boundary.

Stage 1 keeps API handlers as importable Python callables so contract tests can
verify semantics without requiring an HTTP server dependency.
"""


def create_app() -> dict[str, str]:
    return {
        "ingestion": "POST /v1/events",
        "ingestion_compatibility_alias": "POST /v1/events/batch",
        "credentials": "/v1/bootstrap/credentials",
        "evidence": "/v1/runs/{run_id}/evidence-summary",
        "policy": "/v1/policy/decision",
        "store_summary": "/v1/store-summary/{agent_id}",
        "agent_store_metadata": "POST /v1/agent-store/metadata",
        "agent_store_discovery": "/v1/agent-store/discovery",
        "run_audit": "/v1/runs/{run_id}/audit",
        "health": "/v1/health",
        "console_snapshot": "/v1/console/snapshot",
    }
