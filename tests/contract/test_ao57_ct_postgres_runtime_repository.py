from __future__ import annotations

import pytest

from agentops.api.server import create_http_handler
from agentops.storage.factory import repository_from_env
from agentops.storage.postgres_repository import (
    PostgresRepository,
    runtime_operations_schema_sql,
)
from agentops.storage.repository import InMemoryRepository


def test_ao57_ct_001_postgres_runtime_schema_defines_canonical_fact_tables():
    schema = runtime_operations_schema_sql()

    for table_name in (
        "agentops_runtime_idempotency",
        "agentops_runtime_runs",
        "agentops_trace_spans",
        "agentops_guardrail_results",
        "agentops_runtime_dlq",
        "agentops_runtime_outbox_receipts",
        "agentops_audit_records",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table_name}" in schema

    assert "PRIMARY KEY (run_id, trace_id, attempt_no_identity, span_id)" in schema
    assert "idx_agentops_runtime_runs_agent_version" in schema
    assert "idx_agentops_trace_spans_run_time" in schema
    assert "idx_agentops_runtime_dlq_agent_version" in schema
    assert "idx_agentops_runtime_outbox_receipts_batch" in schema
    assert "JSONB NOT NULL" in schema


def test_ao57_ct_002_repository_factory_defaults_to_in_memory_for_local_dev(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("AGENTOPS_DATABASE_URL", raising=False)

    repository = repository_from_env()

    assert isinstance(repository, InMemoryRepository)
    assert not isinstance(repository, PostgresRepository)


def test_ao57_ct_003_repository_factory_uses_postgres_when_database_url_is_set(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("AGENTOPS_DATABASE_URL", "postgresql://agentops@example/db")
    monkeypatch.delenv("AGENTOPS_POSTGRES_AUTO_MIGRATE", raising=False)

    repository = repository_from_env()

    assert isinstance(repository, PostgresRepository)
    assert repository.database_url == "postgresql://agentops@example/db"


def test_ao57_ct_004_production_auth_mode_requires_database_without_explicit_repo(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("AGENTOPS_DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="AGENTOPS_DATABASE_URL is required"):
        repository_from_env(require_auth=True)


def test_ao57_ct_004a_http_handler_fails_closed_for_production_without_database(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("AGENTOPS_DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="AGENTOPS_DATABASE_URL is required"):
        create_http_handler(require_auth=True)
