"""Unit test fixtures."""

import pytest

from agentops.storage.repository import InMemoryRepository


@pytest.fixture
def repository() -> InMemoryRepository:
    return InMemoryRepository()
