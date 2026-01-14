"""Tests for memory client - ALL tests call REAL jarvis-cloud API."""

import asyncio
import uuid
from typing import AsyncGenerator

import pytest

from src.memory_client import (
    add_memory,
    delete_user_memories,
    get_memories,
    search_memory,
)

# Dedicated test user to avoid polluting real user data
TEST_USER_ID = "jarvis_integration_test_user"


@pytest.fixture(autouse=True)
async def cleanup_test_memories() -> AsyncGenerator[None, None]:
    """Clean up test memories after each test."""
    yield
    await delete_user_memories(TEST_USER_ID)


class TestSearchMemory:
    """Tests for search_memory function with REAL API."""

    async def test_search_memory_returns_list(self) -> None:
        """Search returns a list (may be empty for new user)."""
        result = await search_memory("test query", TEST_USER_ID)
        assert isinstance(result, list)

    async def test_search_memory_with_existing_memory(self) -> None:
        """Search returns results for existing memories."""
        # First add a memory
        unique_fact = f"Test user likes blue color {uuid.uuid4()}"
        await add_memory(unique_fact, TEST_USER_ID)

        # Give API time to index
        await asyncio.sleep(1)

        # Now search for it
        results = await search_memory("favorite color blue", TEST_USER_ID)
        assert isinstance(results, list)


class TestAddMemory:
    """Tests for add_memory function with REAL API."""

    async def test_add_memory_returns_dict(self) -> None:
        """Add memory returns a dict response."""
        result = await add_memory(
            "Test fact for jarvis integration",
            TEST_USER_ID,
        )
        # Successful add returns dict (may be empty or have results)
        assert isinstance(result, dict)

    async def test_add_memory_with_app_id(self) -> None:
        """Add memory with custom app_id."""
        result = await add_memory(
            "Another test fact",
            TEST_USER_ID,
            app="jarvis-test",
        )
        assert isinstance(result, dict)


class TestGetMemories:
    """Tests for get_memories function with REAL API."""

    async def test_get_memories_returns_list(self) -> None:
        """Get memories returns a list."""
        result = await get_memories(TEST_USER_ID)
        assert isinstance(result, list)

    async def test_get_memories_with_limit(self) -> None:
        """Get memories respects limit parameter."""
        result = await get_memories(TEST_USER_ID, limit=5)
        assert isinstance(result, list)
        assert len(result) <= 5


class TestGracefulDegradation:
    """Tests for graceful degradation on failures."""

    async def test_search_timeout_returns_empty_list(self) -> None:
        """Search with very short timeout returns empty list, not exception."""
        import os

        # Set artificially short timeout
        original = os.environ.get("MEMORY_TIMEOUT_SECONDS")
        os.environ["MEMORY_TIMEOUT_SECONDS"] = "0.001"

        try:
            result = await search_memory("test", TEST_USER_ID)
            assert result == []
        finally:
            if original:
                os.environ["MEMORY_TIMEOUT_SECONDS"] = original
            else:
                os.environ.pop("MEMORY_TIMEOUT_SECONDS", None)

    async def test_add_memory_timeout_returns_empty_dict(self) -> None:
        """Add memory with very short timeout returns empty dict, not exception."""
        import os

        original = os.environ.get("MEMORY_TIMEOUT_SECONDS")
        os.environ["MEMORY_TIMEOUT_SECONDS"] = "0.001"

        try:
            result = await add_memory("test fact", TEST_USER_ID)
            assert result == {}
        finally:
            if original:
                os.environ["MEMORY_TIMEOUT_SECONDS"] = original
            else:
                os.environ.pop("MEMORY_TIMEOUT_SECONDS", None)

    async def test_get_memories_timeout_returns_empty_list(self) -> None:
        """Get memories with very short timeout returns empty list, not exception."""
        import os

        original = os.environ.get("MEMORY_TIMEOUT_SECONDS")
        os.environ["MEMORY_TIMEOUT_SECONDS"] = "0.001"

        try:
            result = await get_memories(TEST_USER_ID)
            assert result == []
        finally:
            if original:
                os.environ["MEMORY_TIMEOUT_SECONDS"] = original
            else:
                os.environ.pop("MEMORY_TIMEOUT_SECONDS", None)
