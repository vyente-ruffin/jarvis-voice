"""Memory tool definitions for Azure Voice Live API function calling.

This module defines the function calling tools that enable JARVIS to
interact with long-term memory during voice conversations.
"""

from typing import Any

# Tool definitions following Azure Voice Live API schema
MEMORY_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "search_memory",
        "description": (
            "Search user's long-term memory for relevant context. "
            "Call this BEFORE answering personal questions like "
            "'what's my favorite...' or 'do you remember...'"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for in memories",
                },
                "user_id": {
                    "type": "string",
                    "description": "User identifier",
                },
            },
            "required": ["query", "user_id"],
        },
    },
    {
        "type": "function",
        "name": "add_memory",
        "description": (
            "Store a new fact about the user. "
            "Call this when user shares personal information, preferences, "
            "or important details worth remembering."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The fact to remember about the user",
                },
                "user_id": {
                    "type": "string",
                    "description": "User identifier",
                },
            },
            "required": ["text", "user_id"],
        },
    },
]
