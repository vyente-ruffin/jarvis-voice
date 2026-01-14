"""Unit tests for the tool call handler."""

import pytest

from src.tool_handler import handle_tool_call


@pytest.mark.asyncio
async def test_search_memory_routing() -> None:
    """Test that search_memory calls are routed to memory client correctly."""
    result = await handle_tool_call(
        "search_memory",
        {"query": "test query", "user_id": "jarvis_integration_test_user"},
    )

    assert result["success"] is True
    assert "memories" in result
    assert "count" in result
    assert isinstance(result["memories"], list)


@pytest.mark.asyncio
async def test_add_memory_routing() -> None:
    """Test that add_memory calls are routed to memory client correctly."""
    result = await handle_tool_call(
        "add_memory",
        {"text": "Test fact for tool handler", "user_id": "jarvis_integration_test_user"},
    )

    # add_memory may succeed or fail based on API, but should always return valid structure
    assert "success" in result
    if result["success"]:
        assert "memory" in result
    else:
        assert "error" in result


@pytest.mark.asyncio
async def test_unknown_tool_name_returns_error() -> None:
    """Test that unknown tool names return an error response."""
    result = await handle_tool_call(
        "unknown_tool",
        {"arg1": "value1"},
    )

    assert result["success"] is False
    assert "error" in result
    assert "Unknown tool" in result["error"]


@pytest.mark.asyncio
async def test_search_memory_missing_query() -> None:
    """Test search_memory with missing query argument."""
    result = await handle_tool_call(
        "search_memory",
        {"user_id": "jarvis_integration_test_user"},
    )

    assert result["success"] is False
    assert "error" in result
    assert "Missing required" in result["error"]


@pytest.mark.asyncio
async def test_search_memory_missing_user_id() -> None:
    """Test search_memory with missing user_id argument."""
    result = await handle_tool_call(
        "search_memory",
        {"query": "test query"},
    )

    assert result["success"] is False
    assert "error" in result
    assert "Missing required" in result["error"]


@pytest.mark.asyncio
async def test_add_memory_missing_text() -> None:
    """Test add_memory with missing text argument."""
    result = await handle_tool_call(
        "add_memory",
        {"user_id": "jarvis_integration_test_user"},
    )

    assert result["success"] is False
    assert "error" in result
    assert "Missing required" in result["error"]


@pytest.mark.asyncio
async def test_add_memory_missing_user_id() -> None:
    """Test add_memory with missing user_id argument."""
    result = await handle_tool_call(
        "add_memory",
        {"text": "test fact"},
    )

    assert result["success"] is False
    assert "error" in result
    assert "Missing required" in result["error"]


@pytest.mark.asyncio
async def test_search_memory_invalid_query_type() -> None:
    """Test search_memory with invalid query type."""
    result = await handle_tool_call(
        "search_memory",
        {"query": 123, "user_id": "jarvis_integration_test_user"},
    )

    assert result["success"] is False
    assert "error" in result
    assert "must be strings" in result["error"]


@pytest.mark.asyncio
async def test_add_memory_invalid_text_type() -> None:
    """Test add_memory with invalid text type."""
    result = await handle_tool_call(
        "add_memory",
        {"text": ["list", "not", "string"], "user_id": "jarvis_integration_test_user"},
    )

    assert result["success"] is False
    assert "error" in result
    assert "must be strings" in result["error"]


@pytest.mark.asyncio
async def test_empty_arguments() -> None:
    """Test tool calls with empty arguments dict."""
    result = await handle_tool_call("search_memory", {})

    assert result["success"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_none_arguments() -> None:
    """Test tool calls with None values in arguments."""
    result = await handle_tool_call(
        "add_memory",
        {"text": None, "user_id": "jarvis_integration_test_user"},
    )

    assert result["success"] is False
    assert "error" in result
