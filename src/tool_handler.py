"""Tool call handler for routing Voice Live function calls to memory operations."""

import logging
import os
import time
from typing import Any

from src.memory_client import add_memory, search_memory

# Configure logging
logger = logging.getLogger(__name__)

# OpenTelemetry tracing (optional)
tracer = None
try:
    if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
        from opentelemetry import trace
        tracer = trace.get_tracer(__name__)
except ImportError:
    pass


def _record_memory_event(operation: str, user_id: str, latency_ms: float, success: bool, **extra):
    """Record custom telemetry event for memory operations."""
    if tracer:
        with tracer.start_as_current_span(f"memory.{operation}") as span:
            span.set_attribute("memory.operation", operation)
            span.set_attribute("memory.user_id", user_id)
            span.set_attribute("memory.latency_ms", latency_ms)
            span.set_attribute("memory.success", success)
            for key, value in extra.items():
                span.set_attribute(f"memory.{key}", value)


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
    start_time = time.time()
    results = await search_memory(query, user_id)
    latency_ms = (time.time() - start_time) * 1000
    logger.info("Search returned %d results in %.2fms", len(results), latency_ms)

    # Record telemetry
    _record_memory_event("search", user_id, latency_ms, True, result_count=len(results))

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
    start_time = time.time()
    result = await add_memory(text, user_id)
    latency_ms = (time.time() - start_time) * 1000

    # Record telemetry
    _record_memory_event("add", user_id, latency_ms, True)

    if result:
        logger.info("Memory added successfully in %.2fms", latency_ms)
        return {
            "success": True,
            "memory": result,
            "message": "Memory stored successfully",
        }
    else:
        # API returns null when memory is deduplicated or no new facts extracted
        # This is expected behavior, not an error
        logger.info("Memory processed (deduplicated or no new facts) in %.2fms", latency_ms)
        return {
            "success": True,
            "memory": None,
            "message": "Memory already exists or no new facts to store",
        }
