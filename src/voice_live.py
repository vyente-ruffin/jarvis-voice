"""
Voice Live Session Manager.

Wraps the Azure OpenAI Realtime API to provide a clean interface for
managing voice sessions with callbacks for audio, transcripts, and events.
"""

import asyncio
import base64
import json
import logging
from typing import Optional, Callable, Any

import websockets
from websockets.asyncio.client import connect as ws_connect

from src.memory_tools import MEMORY_TOOLS
from src.tool_handler import handle_tool_call

logger = logging.getLogger(__name__)

# Default instructions with memory capabilities
VOICE_LIVE_INSTRUCTIONS = """You are JARVIS, a helpful AI assistant with long-term memory.
You can remember facts about the user across sessions.
Use search_memory before answering personal questions like "what's my favorite..." or "do you remember...".
Use add_memory when the user shares personal information, preferences, or important details.
Be conversational, concise, and helpful."""


class VoiceLiveSession:
    """
    Manages a Voice Live API session with callback-based event handling.

    Usage:
        session = VoiceLiveSession(endpoint=..., api_key=...)
        session.on_audio = my_audio_handler
        session.on_transcript = my_transcript_handler

        async with session:
            await session.send_audio(base64_audio)
    """

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        model: str = "gpt-4o-mini-realtime-preview",
        voice: str = "alloy",
        instructions: str = VOICE_LIVE_INSTRUCTIONS,
        user_id: str = "anonymous_user",
        tools: Optional[list[dict[str, Any]]] = None
    ):
        self.endpoint = endpoint.rstrip('/')
        self.api_key = api_key
        self.model = model
        self.voice = voice
        self.instructions = instructions
        self.user_id = user_id
        self.tools = tools if tools is not None else MEMORY_TOOLS

        # Build WebSocket URL (GA format)
        self._ws_url = f"{self.endpoint.replace('https://', 'wss://')}/openai/v1/realtime?model={self.model}"

        # Internal connection state
        self._ws = None
        self._event_task: Optional[asyncio.Task] = None
        self._connected = False

        # Callbacks (all optional)
        self.on_audio: Optional[Callable[[str], Any]] = None
        self.on_transcript: Optional[Callable[[str], Any]] = None
        self.on_speech_started: Optional[Callable[[], Any]] = None
        self.on_speech_stopped: Optional[Callable[[], Any]] = None
        self.on_status: Optional[Callable[[str], Any]] = None
        self.on_error: Optional[Callable[[str], Any]] = None
        self.on_function_call: Optional[Callable[[str, dict[str, Any], dict[str, Any]], Any]] = None

    async def connect(self) -> None:
        """Establish connection to Voice Live API."""
        if self._connected:
            return

        # Connect with api-key header (Azure OpenAI requirement)
        headers = [("api-key", self.api_key)]

        logger.info(f"Connecting to: {self._ws_url}")
        self._ws = await ws_connect(self._ws_url, additional_headers=headers)
        logger.info("WebSocket connected")

        # Wait for session.created event
        msg = await self._ws.recv()
        data = json.loads(msg)
        if data.get("type") == "session.created":
            logger.info(f"Session created: {data.get('session', {}).get('id', 'unknown')}")
        else:
            logger.warning(f"Unexpected first message: {data.get('type')}")

        # Configure session
        await self._configure_session()
        self._connected = True

        # Send ready status to client
        if self.on_status:
            await self._call_callback(self.on_status, "ready")

        # Start event processing loop
        self._event_task = asyncio.create_task(self._process_events())

    async def _configure_session(self) -> None:
        """Configure the Voice Live session."""
        # Convert tools to OpenAI format
        openai_tools = []
        for tool in self.tools:
            if tool.get("type") == "function":
                openai_tools.append({
                    "type": "function",
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {}),
                })

        # Build session update message (type: "realtime" required for Azure GA API)
        session_config = {
            "type": "realtime",
            "instructions": self.instructions,
        }

        # Add tools if present
        if openai_tools:
            session_config["tools"] = openai_tools
            session_config["tool_choice"] = "auto"
            logger.info(f"Configured {len(openai_tools)} tools: {[t['name'] for t in openai_tools]}")

        update_msg = {
            "type": "session.update",
            "session": session_config
        }

        logger.info(f"Session config: {json.dumps(session_config, indent=2)}")
        await self._ws.send(json.dumps(update_msg))
        logger.info("Session configuration sent")

        # Wait for session.updated event
        msg = await self._ws.recv()
        data = json.loads(msg)
        if data.get("type") == "session.updated":
            logger.info("Session configured successfully")
        else:
            logger.warning(f"Unexpected response to session.update: {data.get('type')} - {json.dumps(data.get('error', {}))}")

    async def disconnect(self) -> None:
        """Close the Voice Live connection."""
        if self._event_task:
            self._event_task.cancel()
            try:
                await self._event_task
            except asyncio.CancelledError:
                pass
            self._event_task = None

        if self._ws:
            await self._ws.close()
            self._ws = None

        self._connected = False

    async def send_audio(self, audio_base64: str) -> None:
        """Send audio data to Voice Live API."""
        if not self._ws:
            raise RuntimeError("Not connected. Call connect() first.")

        msg = {
            "type": "input_audio_buffer.append",
            "audio": audio_base64
        }
        await self._ws.send(json.dumps(msg))
        logger.info(f"Sent audio chunk: {len(audio_base64)} bytes")

    async def _process_events(self) -> None:
        """Process events from Voice Live connection."""
        try:
            async for msg in self._ws:
                data = json.loads(msg)
                await self._handle_event(data)
        except asyncio.CancelledError:
            raise
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Event processing error: {e}")
            if self.on_error:
                await self._call_callback(self.on_error, str(e))

    async def _handle_event(self, event: dict) -> None:
        """Handle individual Voice Live events."""
        event_type = event.get("type", "unknown")
        logger.info(f"Voice Live event: {event_type}")

        if event_type == "session.created":
            logger.info(f"Session created: {event.get('session', {}).get('id', 'unknown')}")

        elif event_type == "session.updated":
            if self.on_status:
                await self._call_callback(self.on_status, "ready")

        elif event_type == "input_audio_buffer.speech_started":
            if self.on_speech_started:
                await self._call_callback(self.on_speech_started)
            if self.on_status:
                await self._call_callback(self.on_status, "listening")

        elif event_type == "input_audio_buffer.speech_stopped":
            if self.on_speech_stopped:
                await self._call_callback(self.on_speech_stopped)
            if self.on_status:
                await self._call_callback(self.on_status, "processing")

        elif event_type == "response.audio.delta" or event_type == "response.output_audio.delta":
            if self.on_audio:
                # event["delta"] is base64 encoded audio
                await self._call_callback(self.on_audio, event.get("delta", ""))

        elif event_type == "response.audio_transcript.delta" or event_type == "response.output_audio_transcript.delta":
            if self.on_transcript:
                await self._call_callback(self.on_transcript, event.get("delta", ""))

        elif event_type == "response.done":
            if self.on_status:
                await self._call_callback(self.on_status, "ready")

        elif event_type == "response.function_call_arguments.done":
            # Handle function call
            await self._handle_function_call(event)

        elif event_type == "error":
            error_msg = event.get("error", {}).get("message", str(event))
            logger.error(f"Voice Live error: {error_msg}")
            if self.on_error:
                await self._call_callback(self.on_error, error_msg)

    async def _handle_function_call(self, event: dict) -> None:
        """Handle function call from the model."""
        function_name = event.get("name", "")
        call_id = event.get("call_id", "")
        arguments_str = event.get("arguments", "")

        logger.info(f"Function call: {function_name} (call_id={call_id})")

        # Parse arguments
        try:
            arguments = json.loads(arguments_str) if arguments_str else {}
        except json.JSONDecodeError:
            logger.error(f"Failed to parse function arguments: {arguments_str}")
            arguments = {}

        # Inject user_id for memory functions
        if function_name in ("search_memory", "add_memory"):
            arguments["user_id"] = self.user_id
            logger.info(f"Injected user_id={self.user_id} for {function_name}")

        logger.info(f"Executing function: {function_name} with args: {arguments}")

        # Call the tool handler
        result = await handle_tool_call(function_name, arguments)
        logger.info(f"Function result: {result}")

        # Notify via callback if set
        if self.on_function_call:
            await self._call_callback(self.on_function_call, function_name, arguments, result)

        # Send result back to Voice Live
        if self._ws:
            response_msg = {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(result)
                }
            }
            await self._ws.send(json.dumps(response_msg))
            logger.info(f"Function output sent for call_id={call_id}")

            # Request new response to continue the conversation
            await self._ws.send(json.dumps({"type": "response.create"}))
            logger.info("Requested new response after function call")

    async def _call_callback(self, callback: Callable, *args) -> None:
        """Call a callback, handling both sync and async callbacks."""
        if asyncio.iscoroutinefunction(callback):
            await callback(*args)
        else:
            callback(*args)

    # Async context manager support
    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
        return False
