"""Repository construction for local and production AgentOps API servers."""

from __future__ import annotations

import os

from agentops.storage.postgres_repository import PostgresRepository
from agentops.storage.repository import InMemoryRepository

DATABASE_URL_ENV = "AGENTOPS_DATABASE_URL"
POSTGRES_AUTO_MIGRATE_ENV = "AGENTOPS_POSTGRES_AUTO_MIGRATE"


def repository_from_env(*, require_auth: bool = False) -> InMemoryRepository:
    database_url = os.environ.get(DATABASE_URL_ENV, "").strip()
    if database_url:
        return PostgresRepository(
            database_url,
            install_schema=_env_flag(POSTGRES_AUTO_MIGRATE_ENV),
        )

    if require_auth:
        raise RuntimeError(
            "AGENTOPS_DATABASE_URL is required when starting AgentOps in "
            "production auth mode without an explicit repository."
        )

    return InMemoryRepository()


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}
