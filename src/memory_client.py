"""Memory client for Redis agent-memory-server.

Per Redis agent-memory-server docs:
- POST /v1/long-term-memory/ - Create memories
- POST /v1/long-term-memory/search - Semantic search
"""

import os
import uuid
from typing import Any, Optional

import httpx

from src.logging_config import get_memory_logger, log_api_call

# Get the logger for memory operations
logger = get_memory_logger()

# Default timeout in seconds
DEFAULT_TIMEOUT_SECONDS = 30.0

# Default memory enabled state
DEFAULT_ENABLE_MEMORY = True


def _get_base_url() -> str:
    """Get the memory server URL from environment or use default."""
    return os.getenv("MEMORY_SERVER_URL", "http://localhost:8000")


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
    Search user's long-term memory using semantic search.

    Per Redis agent-memory-server docs:
    POST /v1/long-term-memory/search with user_id filter

    Args:
        query: What to search for in memories
        user_id: User identifier

    Returns:
        List of matching memory objects with text and score
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
            api_endpoint="/v1/long-term-memory/search",
        ) as ctx:
            async with httpx.AsyncClient(
                base_url=_get_base_url(),
                timeout=_get_timeout(),
            ) as client:
                # Per docs: POST /v1/long-term-memory/search
                response = await client.post(
                    "/v1/long-term-memory/search",
                    json={
                        "text": query,
                        "user_id": {"eq": user_id},
                        "limit": 10,
                    },
                )
                response.raise_for_status()
                data = response.json()

                # Per docs: response has "memories" array with text, dist, etc.
                memories = data.get("memories", [])
                results = [
                    {
                        "id": m.get("id"),
                        "content": m.get("text"),
                        "score": 1 - m.get("dist", 0),  # Convert distance to similarity
                        "topics": m.get("topics", []),
                        "created_at": m.get("created_at"),
                    }
                    for m in memories
                ]

                ctx["result_count"] = len(results)
                return results
    except (httpx.HTTPError, httpx.TimeoutException, Exception) as e:
        logger.error(f"Memory search error: {type(e).__name__}: {e}")
        return []


async def add_memory(
    text: str, user_id: str, app: str = "jarvis-voice"
) -> dict[str, Any]:
    """
    Store a new fact about the user in long-term memory.

    Per Redis agent-memory-server docs:
    POST /v1/long-term-memory/ with memories array

    Args:
        text: The fact to remember about the user
        user_id: User identifier
        app: Application name for memory tagging

    Returns:
        Created memory object, or empty dict on failure
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
            api_endpoint="/v1/long-term-memory/",
        ) as ctx:
            async with httpx.AsyncClient(
                base_url=_get_base_url(),
                timeout=_get_timeout(),
            ) as client:
                # Per docs: POST /v1/long-term-memory/ with memories array
                # id field is required per Redis agent-memory-server API
                memory_id = f"jarvis-{uuid.uuid4().hex[:12]}"
                response = await client.post(
                    "/v1/long-term-memory/",
                    json={
                        "memories": [
                            {
                                "id": memory_id,
                                "text": text,
                                "memory_type": "semantic",
                                "user_id": user_id,
                                "topics": [app],
                            }
                        ]
                    },
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"Memory added successfully: {result}")
                ctx["success"] = True
                return result if result else {}
    except (httpx.HTTPError, httpx.TimeoutException, Exception) as e:
        logger.error(f"Memory add error: {type(e).__name__}: {e}")
        return {}


async def get_memories(user_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """
    Get all memories for a user.

    Uses search with empty query to get recent memories.

    Args:
        user_id: User identifier
        limit: Maximum number of memories to return

    Returns:
        List of memory objects
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
            api_endpoint="/v1/long-term-memory/search",
        ) as ctx:
            async with httpx.AsyncClient(
                base_url=_get_base_url(),
                timeout=_get_timeout(),
            ) as client:
                # Search with empty text to get all memories for user
                response = await client.post(
                    "/v1/long-term-memory/search",
                    json={
                        "text": "",
                        "user_id": {"eq": user_id},
                        "limit": limit,
                    },
                )
                response.raise_for_status()
                data = response.json()

                memories = data.get("memories", [])
                results = [
                    {
                        "id": m.get("id"),
                        "content": m.get("text"),
                        "topics": m.get("topics", []),
                        "created_at": m.get("created_at"),
                    }
                    for m in memories
                ]

                ctx["result_count"] = len(results)
                return results
    except (httpx.HTTPError, httpx.TimeoutException, Exception) as e:
        logger.error(f"Get memories error: {type(e).__name__}: {e}")
        return []


async def delete_user_memories(user_id: str) -> bool:
    """
    Delete all memories for a user (for test cleanup).

    Note: Redis agent-memory-server uses /v1/long-term-memory/forget endpoint.

    Args:
        user_id: User identifier

    Returns:
        True if successful, False on failure
    """
    try:
        async with log_api_call(
            operation="delete_user_memories",
            user_id=user_id,
            api_endpoint="/v1/long-term-memory/forget",
        ):
            async with httpx.AsyncClient(
                base_url=_get_base_url(),
                timeout=_get_timeout(),
            ) as client:
                response = await client.post(
                    "/v1/long-term-memory/forget",
                    json={
                        "user_id": user_id,
                        "dry_run": False,
                    },
                )
                response.raise_for_status()
                return True
    except (httpx.HTTPError, httpx.TimeoutException, Exception) as e:
        logger.error(f"Delete memories error: {type(e).__name__}: {e}")
        return False
