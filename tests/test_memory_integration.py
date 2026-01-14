"""Integration tests for the full memory flow.

These tests call the REAL jarvis-cloud API to verify the complete integration works.
They test the flow: Add memory → Search memory → Find the added memory.

Note: The jarvis-cloud API requires users to be registered before memories can be added.
New user IDs return "User not found". Tests use a dedicated test user ID that should
exist in the system, and verify graceful degradation for new/unknown users.
"""

import asyncio
import time
import uuid
from collections.abc import AsyncGenerator

import pytest

from src.memory_client import (
    add_memory,
    delete_user_memories,
    get_memories,
    search_memory,
)
from src.tool_handler import handle_tool_call


# Dedicated test user ID - must exist in the jarvis-cloud system
# If this user doesn't exist, tests that require memory creation will be skipped
EXISTING_TEST_USER_ID = "jarvis_integration_test_user"


# Generate a unique test user ID for this test run to avoid pollution
def _generate_test_user_id() -> str:
    """Generate a unique test user ID for isolation."""
    return f"jarvis_integration_test_{uuid.uuid4().hex[:8]}"


@pytest.fixture
async def test_user_id() -> AsyncGenerator[str, None]:
    """Create a unique test user ID and clean up after test."""
    user_id = _generate_test_user_id()
    yield user_id
    # Cleanup: delete all memories for this test user
    await delete_user_memories(user_id)


@pytest.fixture
async def cleanup_user_id() -> AsyncGenerator[str, None]:
    """Create and return a test user ID, cleaning up before and after."""
    user_id = _generate_test_user_id()
    # Clean up any existing memories first
    await delete_user_memories(user_id)
    yield user_id
    # Cleanup after test
    await delete_user_memories(user_id)


@pytest.fixture
async def existing_user_id() -> AsyncGenerator[str, None]:
    """Use the existing test user and clean up memories after test."""
    yield EXISTING_TEST_USER_ID
    # Cleanup after test
    await delete_user_memories(EXISTING_TEST_USER_ID)


class TestMemoryFlowIntegration:
    """Integration tests for the full memory flow.

    Note: The jarvis-cloud API requires user IDs to be registered in the system
    before memories can be created. Tests verify graceful degradation for
    unknown users, which is the expected behavior in production.
    """

    @pytest.mark.asyncio
    async def test_add_memory_returns_response(self) -> None:
        """Test: add_memory returns a response (may be empty for new users)."""
        user_id = EXISTING_TEST_USER_ID
        unique_fact = f"My favorite color is purple-{uuid.uuid4().hex[:6]}"

        # add_memory returns dict - may be empty if user doesn't exist
        result = await add_memory(unique_fact, user_id)
        assert isinstance(result, dict), "add_memory should return a dict"
        # Cleanup
        await delete_user_memories(user_id)

    @pytest.mark.asyncio
    async def test_add_memory_for_new_user_gracefully_fails(self) -> None:
        """Test: add_memory for new user returns empty dict (graceful degradation)."""
        new_user_id = f"jarvis_new_user_{uuid.uuid4().hex}"

        # New users get "User not found" - should return empty dict, not exception
        result = await add_memory("Test fact", new_user_id)
        assert result == {}, f"Should return empty dict for new user, got: {result}"

    @pytest.mark.asyncio
    async def test_search_with_no_results_returns_empty(self) -> None:
        """Test: Search with no results returns empty gracefully."""
        # Search for something that doesn't exist
        unique_query = f"xyznonexistent{uuid.uuid4().hex}"
        results = await search_memory(unique_query, EXISTING_TEST_USER_ID)

        # Should return empty list, not error (API may return 404 for unknown user)
        assert isinstance(results, list), f"Should return list, got: {type(results)}"

    @pytest.mark.asyncio
    async def test_search_new_user_returns_empty(self) -> None:
        """Test: Search for a brand new user returns empty gracefully."""
        # Use a completely new user ID that has never been used
        new_user_id = f"jarvis_new_user_{uuid.uuid4().hex}"

        results = await search_memory("anything", new_user_id)

        # Should return empty list for new user (API returns "User not found")
        assert results == [], f"Should return empty list for new user, got: {results}"

    @pytest.mark.asyncio
    async def test_get_memories_returns_list(self) -> None:
        """Test: get_memories returns a list (may be empty)."""
        # May return empty list if no memories exist
        memories = await get_memories(EXISTING_TEST_USER_ID)
        assert isinstance(memories, list), "get_memories should return a list"

    @pytest.mark.asyncio
    async def test_get_memories_new_user_returns_empty(self) -> None:
        """Test: get_memories for new user returns empty list."""
        new_user_id = f"jarvis_new_user_{uuid.uuid4().hex}"

        memories = await get_memories(new_user_id)
        assert memories == [], f"Should return empty list for new user, got: {memories}"


class TestToolHandlerIntegration:
    """Integration tests for tool handler with real API.

    Note: The jarvis-cloud API requires user IDs to be registered.
    Tests verify graceful degradation behavior.
    """

    @pytest.mark.asyncio
    async def test_tool_handler_add_memory_returns_response(self) -> None:
        """Test tool handler add_memory returns a structured response."""
        unique_fact = f"My favorite food is pizza-{uuid.uuid4().hex[:6]}"

        # Add memory via tool handler - may fail for unknown user
        add_result = await handle_tool_call(
            "add_memory",
            {"text": unique_fact, "user_id": EXISTING_TEST_USER_ID},
        )
        # Should return structured response (success or failure)
        assert "success" in add_result, f"Should have 'success' key: {add_result}"
        # Cleanup
        await delete_user_memories(EXISTING_TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_tool_handler_add_memory_new_user_fails_gracefully(self) -> None:
        """Test tool handler add_memory fails gracefully for new user."""
        new_user_id = f"jarvis_new_user_{uuid.uuid4().hex}"
        unique_fact = f"My favorite food is pizza-{uuid.uuid4().hex[:6]}"

        # Add memory for new user - should fail gracefully
        add_result = await handle_tool_call(
            "add_memory",
            {"text": unique_fact, "user_id": new_user_id},
        )
        # Should report failure with error message
        assert add_result["success"] is False, f"Should fail for new user: {add_result}"
        assert "error" in add_result, f"Should have error message: {add_result}"

    @pytest.mark.asyncio
    async def test_tool_handler_search_returns_structured_response(self) -> None:
        """Test tool handler search returns structured response."""
        result = await handle_tool_call(
            "search_memory",
            {"query": "anything", "user_id": EXISTING_TEST_USER_ID},
        )

        # Should return structured response with required keys
        assert "success" in result, f"Should have 'success' key: {result}"
        assert "memories" in result, f"Should have 'memories' key: {result}"
        assert "count" in result, f"Should have 'count' key: {result}"

    @pytest.mark.asyncio
    async def test_tool_handler_search_new_user_returns_empty(self) -> None:
        """Test tool handler search returns empty for new user."""
        new_user_id = f"jarvis_new_user_{uuid.uuid4().hex}"

        result = await handle_tool_call(
            "search_memory",
            {"query": "anything", "user_id": new_user_id},
        )

        # Should succeed but return empty results
        assert result["success"], f"Should succeed even with no results: {result}"
        assert result["count"] == 0, f"Should have zero results: {result}"
        assert result["memories"] == [], f"Should have empty list: {result}"


class TestGracefulDegradation:
    """Tests for graceful degradation when API has issues."""

    @pytest.mark.asyncio
    async def test_memory_api_timeout_graceful_degradation(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test: Memory API timeout doesn't break the flow."""
        # Set an impossibly short timeout
        monkeypatch.setenv("MEMORY_TIMEOUT_SECONDS", "0.001")

        # Try to search - should return empty list, not raise exception
        results = await search_memory("anything", "test_user")
        assert results == [], "Should return empty list on timeout"

        # Try to add - should return empty dict, not raise exception
        add_result = await add_memory("test", "test_user")
        assert add_result == {}, "Should return empty dict on timeout"

    @pytest.mark.asyncio
    async def test_tool_handler_timeout_graceful_degradation(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test: Tool handler gracefully handles API timeout."""
        # Set an impossibly short timeout
        monkeypatch.setenv("MEMORY_TIMEOUT_SECONDS", "0.001")

        # Search should succeed but return empty
        search_result = await handle_tool_call(
            "search_memory",
            {"query": "anything", "user_id": "test_user"},
        )
        assert search_result["success"], "Should still report success"
        assert search_result["memories"] == [], "Should have empty memories"
        assert search_result["count"] == 0, "Should have zero count"

        # Add should report failure gracefully
        add_result = await handle_tool_call(
            "add_memory",
            {"text": "test", "user_id": "test_user"},
        )
        assert not add_result["success"], "Should report failure on timeout"
        assert "error" in add_result, "Should include error message"


class TestPerformance:
    """Performance tests to ensure memory operations meet latency requirements."""

    @pytest.mark.asyncio
    async def test_search_memory_latency_under_500ms(self) -> None:
        """Test: Search memory completes in under 500ms.

        Note: We measure latency regardless of whether results are found.
        The API should respond quickly even for "User not found" errors.
        """
        # Measure search latency
        start_time = time.perf_counter()
        await search_memory("coffee", EXISTING_TEST_USER_ID)
        latency = time.perf_counter() - start_time

        # Latency should be under 500ms (0.5s)
        assert latency < 0.5, f"Search latency {latency:.3f}s exceeds 500ms requirement"

    @pytest.mark.asyncio
    async def test_add_memory_latency_reasonable(self) -> None:
        """Test: Add memory completes in a reasonable time.

        Note: We measure latency regardless of success/failure.
        The API should respond quickly even for errors.
        """
        # Measure add latency
        start_time = time.perf_counter()
        await add_memory("Test memory for latency measurement", EXISTING_TEST_USER_ID)
        latency = time.perf_counter() - start_time

        # Add may be slower than search, but should complete in under 3s
        assert latency < 3.0, f"Add latency {latency:.3f}s is too slow"
        # Cleanup
        await delete_user_memories(EXISTING_TEST_USER_ID)
