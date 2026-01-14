"""Tool call handler for routing Voice Live function calls to memory operations."""

import logging
from typing import Any

from src.memory_client import add_memory, search_memory

# Configure logging
logger = logging.getLogger(__name__)


async def handle_tool_call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Handle function calls from Voice Live API and execute corresponding memory operations.

    Args:
        name: The name of the tool being called
        arguments: The arguments passed to the tool

    Returns:
        Structured response for Voice Live to consume
    """
    logger.info("Tool call received: %s with arguments: %s", name, arguments)

    if name == "search_memory":
        return await _handle_search_memory(arguments)
    elif name == "add_memory":
        return await _handle_add_memory(arguments)
    else:
        logger.warning("Unknown tool name: %s", name)
        return {
            "success": False,
            "error": f"Unknown tool: {name}",
        }


async def _handle_search_memory(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle search_memory tool calls."""
    query = arguments.get("query")
    user_id = arguments.get("user_id")

    if not query or not user_id:
        logger.warning("Missing required arguments for search_memory: %s", arguments)
        return {
            "success": False,
            "error": "Missing required arguments: query and user_id",
        }

    if not isinstance(query, str) or not isinstance(user_id, str):
        logger.warning("Invalid argument types for search_memory: %s", arguments)
        return {
            "success": False,
            "error": "Arguments query and user_id must be strings",
        }

    logger.info("Searching memory for user %s with query: %s", user_id, query)
    results = await search_memory(query, user_id)
    logger.info("Search returned %d results", len(results))

    return {
        "success": True,
        "memories": results,
        "count": len(results),
    }


async def _handle_add_memory(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle add_memory tool calls."""
    text = arguments.get("text")
    user_id = arguments.get("user_id")

    if not text or not user_id:
        logger.warning("Missing required arguments for add_memory: %s", arguments)
        return {
            "success": False,
            "error": "Missing required arguments: text and user_id",
        }

    if not isinstance(text, str) or not isinstance(user_id, str):
        logger.warning("Invalid argument types for add_memory: %s", arguments)
        return {
            "success": False,
            "error": "Arguments text and user_id must be strings",
        }

    logger.info("Adding memory for user %s: %s", user_id, text[:50])
    result = await add_memory(text, user_id)

    if result:
        logger.info("Memory added successfully")
        return {
            "success": True,
            "memory": result,
        }
    else:
        logger.warning("Failed to add memory")
        return {
            "success": False,
            "error": "Failed to add memory",
        }
