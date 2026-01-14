"""Memory client for interacting with the jarvis-cloud memory API."""

import os
from typing import Any, cast

import httpx

from src.logging_config import get_memory_logger, log_api_call

# Default API URL for jarvis-cloud memory service
DEFAULT_MEMORY_API_URL = "https://mem0-api.greenstone-413be1c4.eastus.azurecontainerapps.io"

# Get the logger for memory operations
logger = get_memory_logger()

# Default timeout in seconds
DEFAULT_TIMEOUT_SECONDS = 3.0

# Default memory enabled state
DEFAULT_ENABLE_MEMORY = True


def _get_base_url() -> str:
    """Get the memory API base URL from environment or use default."""
    return os.getenv("MEMORY_API_URL", DEFAULT_MEMORY_API_URL)


def _get_timeout() -> float:
    """Get the timeout in seconds from environment or use default."""
    timeout_str = os.getenv("MEMORY_TIMEOUT_SECONDS")
    if timeout_str:
        try:
            return float(timeout_str)
        except ValueError:
            pass
    return DEFAULT_TIMEOUT_SECONDS


def is_memory_enabled() -> bool:
    """Check if memory feature is enabled via environment variable.

    Returns:
        True if memory is enabled, False otherwise.
        Defaults to True if ENABLE_MEMORY is not set.
    """
    enable_str = os.getenv("ENABLE_MEMORY", "true").lower()
    return enable_str in ("true", "1", "yes", "on")


async def search_memory(query: str, user_id: str) -> list[dict[str, Any]]:
    """
    Search user's long-term memory for relevant context.

    Args:
        query: What to search for in memories
        user_id: User identifier

    Returns:
        List of matching memory objects, or empty list on failure or if disabled
    """
    if not is_memory_enabled():
        logger.debug(
            "Memory feature disabled, skipping search",
            extra={"operation": "search_memory", "user_id": user_id},
        )
        return []
    try:
        async with log_api_call(
            operation="search_memory",
            user_id=user_id,
            api_endpoint="/api/v1/memories/filter",
        ) as ctx:
            async with httpx.AsyncClient(
                base_url=_get_base_url(),
                timeout=_get_timeout(),
            ) as client:
                response = await client.post(
                    "/api/v1/memories/filter",
                    json={"search_query": query, "user_id": user_id},
                )
                response.raise_for_status()
                data = response.json()
                # API returns {"results": [...]} or similar structure
                results: list[dict[str, Any]] = []
                if isinstance(data, list):
                    results = data
                elif isinstance(data, dict) and "results" in data:
                    results = cast(list[dict[str, Any]], data["results"])
                elif isinstance(data, dict) and "memories" in data:
                    results = cast(list[dict[str, Any]], data["memories"])
                # Log result count (not content for privacy)
                ctx["result_count"] = len(results)
                return results
    except (httpx.HTTPError, httpx.TimeoutException, Exception):
        # Graceful degradation: return empty list on any failure
        # Error already logged by log_api_call context manager
        return []


async def add_memory(
    text: str, user_id: str, app: str = "jarvis-voice"
) -> dict[str, Any]:
    """
    Store a new fact about the user.

    Args:
        text: The fact to remember about the user
        user_id: User identifier
        app: Application name for memory tagging

    Returns:
        Created memory object, or empty dict on failure or if disabled
    """
    if not is_memory_enabled():
        logger.debug(
            "Memory feature disabled, skipping add",
            extra={"operation": "add_memory", "user_id": user_id},
        )
        return {}
    try:
        async with log_api_call(
            operation="add_memory",
            user_id=user_id,
            api_endpoint="/api/v1/memories/",
        ) as ctx:
            async with httpx.AsyncClient(
                base_url=_get_base_url(),
                timeout=_get_timeout(),
            ) as client:
                response = await client.post(
                    "/api/v1/memories/",
                    json={
                        "text": text,
                        "user_id": user_id,
                        "app": app,
                        "infer": True,
                    },
                )
                response.raise_for_status()
                result: dict[str, Any] = response.json()
                # Log that memory was created (not content for privacy)
                ctx["result_count"] = 1 if result else 0
                return result
    except (httpx.HTTPError, httpx.TimeoutException, Exception):
        # Graceful degradation: return empty dict on any failure
        # Error already logged by log_api_call context manager
        return {}


async def get_memories(user_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """
    Get all memories for a user.

    Args:
        user_id: User identifier
        limit: Maximum number of memories to return

    Returns:
        List of memory objects, or empty list on failure or if disabled
    """
    if not is_memory_enabled():
        logger.debug(
            "Memory feature disabled, skipping get_memories",
            extra={"operation": "get_memories", "user_id": user_id},
        )
        return []
    try:
        async with log_api_call(
            operation="get_memories",
            user_id=user_id,
            api_endpoint="/api/v1/memories/",
        ) as ctx:
            async with httpx.AsyncClient(
                base_url=_get_base_url(),
                timeout=_get_timeout(),
            ) as client:
                response = await client.get(
                    "/api/v1/memories/",
                    params={"user_id": user_id, "limit": limit},
                )
                response.raise_for_status()
                data = response.json()
                # API may return list or dict with results
                results: list[dict[str, Any]] = []
                if isinstance(data, list):
                    results = data[:limit]
                elif isinstance(data, dict) and "results" in data:
                    results = cast(list[dict[str, Any]], data["results"][:limit])
                elif isinstance(data, dict) and "memories" in data:
                    results = cast(list[dict[str, Any]], data["memories"][:limit])
                # Log result count (not content for privacy)
                ctx["result_count"] = len(results)
                return results
    except (httpx.HTTPError, httpx.TimeoutException, Exception):
        # Graceful degradation: return empty list on any failure
        # Error already logged by log_api_call context manager
        return []


async def delete_user_memories(user_id: str) -> bool:
    """
    Delete all memories for a user (for test cleanup).

    Args:
        user_id: User identifier

    Returns:
        True if successful, False on failure
    """
    try:
        async with log_api_call(
            operation="delete_user_memories",
            user_id=user_id,
            api_endpoint="/api/v1/memories/",
        ):
            async with httpx.AsyncClient(
                base_url=_get_base_url(),
                timeout=_get_timeout(),
            ) as client:
                response = await client.delete(
                    "/api/v1/memories/",
                    params={"user_id": user_id},
                )
                response.raise_for_status()
                return True
    except (httpx.HTTPError, httpx.TimeoutException, Exception):
        # Error already logged by log_api_call context manager
        return False
