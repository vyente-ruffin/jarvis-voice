"""
Voice Live Session Manager.

Wraps the Azure AI VoiceLive SDK to provide a clean interface for
managing voice sessions with callbacks for audio, transcripts, and events.
"""

import asyncio
import base64
import json
import logging
from typing import Optional, Callable, Any

logger = logging.getLogger(__name__)
from azure.core.credentials import AzureKeyCredential
from azure.ai.voicelive.aio import connect
from azure.ai.voicelive.models import (
    AudioEchoCancellation,
    AudioNoiseReduction,
    AzureStandardVoice,
    FunctionCallOutputItem,
    FunctionTool,
    InputAudioFormat,
    ItemType,
    Modality,
    OutputAudioFormat,
    RequestSession,
    ServerEventType,
    ServerVad,
    Tool,
    ToolChoiceLiteral,
)

from src.memory_tools import MEMORY_TOOLS
from src.tool_handler import handle_tool_call

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
        voice: str = "en-US-AvaNeural",
        instructions: str = VOICE_LIVE_INSTRUCTIONS,
        user_id: str = "anonymous_user",
        tools: Optional[list[dict[str, Any]]] = None
    ):
        self.endpoint = endpoint
        self.api_key = api_key
        self.model = model
        self.voice = voice
        self.instructions = instructions
        self.user_id = user_id
        self.tools = tools if tools is not None else MEMORY_TOOLS
        
        # Internal connection state
        self._context_manager = None
        self._connection = None
        self._event_task: Optional[asyncio.Task] = None
        self._connected = False

        # Function call tracking state
        self._pending_function_call: Optional[dict[str, Any]] = None

        # Callbacks (all optional)
        self.on_audio: Optional[Callable[[bytes], Any]] = None
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
            
        credential = AzureKeyCredential(self.api_key)
        
        self._context_manager = connect(
            endpoint=self.endpoint,
            credential=credential,
            model=self.model,
        )
        self._connection = await self._context_manager.__aenter__()
        
        # Configure session
        voice_config = AzureStandardVoice(name=self.voice)

        # Convert tool definitions to FunctionTool objects
        function_tools: list[Tool] = []
        for tool_def in self.tools:
            if tool_def.get("type") == "function":
                function_tools.append(
                    FunctionTool(
                        name=tool_def["name"],
                        description=tool_def.get("description", ""),
                        parameters=tool_def.get("parameters", {}),
                    )
                )

        session_config = RequestSession(
            modalities=[Modality.TEXT, Modality.AUDIO],
            instructions=self.instructions,
            voice=voice_config,
            input_audio_format=InputAudioFormat.PCM16,
            output_audio_format=OutputAudioFormat.PCM16,
            turn_detection=ServerVad(
                threshold=0.5,
                prefix_padding_ms=300,
                silence_duration_ms=500
            ),
            input_audio_echo_cancellation=AudioEchoCancellation(),
            input_audio_noise_reduction=AudioNoiseReduction(type="azure_deep_noise_suppression"),
            tools=function_tools if function_tools else None,
            tool_choice=ToolChoiceLiteral.AUTO if function_tools else None,
        )
        
        await self._connection.session.update(session=session_config)
        self._connected = True
        
        # Start event processing loop
        self._event_task = asyncio.create_task(self._process_events())
    
    async def disconnect(self) -> None:
        """Close the Voice Live connection."""
        if self._event_task:
            self._event_task.cancel()
            try:
                await self._event_task
            except asyncio.CancelledError:
                pass
            self._event_task = None
        
        if self._context_manager:
            await self._context_manager.__aexit__(None, None, None)
            self._context_manager = None
            self._connection = None
        
        self._connected = False
    
    async def send_audio(self, audio_base64: str) -> None:
        """Send audio data to Voice Live API."""
        if not self._connection:
            raise RuntimeError("Not connected. Call connect() first.")
        
        await self._connection.input_audio_buffer.append(audio=audio_base64)
    
    async def _process_events(self) -> None:
        """Process events from Voice Live connection."""
        try:
            async for event in self._connection:
                await self._handle_event(event)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            if self.on_error:
                await self._call_callback(self.on_error, str(e))
    
    async def _handle_event(self, event) -> None:
        """Handle individual Voice Live events."""
        logger.info(f"Voice Live event: {event.type}")
        if event.type == ServerEventType.SESSION_UPDATED:
            if self.on_status:
                await self._call_callback(self.on_status, "ready")
        
        elif event.type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED:
            if self.on_speech_started:
                await self._call_callback(self.on_speech_started)
            if self.on_status:
                await self._call_callback(self.on_status, "listening")
        
        elif event.type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED:
            if self.on_speech_stopped:
                await self._call_callback(self.on_speech_stopped)
            if self.on_status:
                await self._call_callback(self.on_status, "processing")
        
        elif event.type == ServerEventType.RESPONSE_AUDIO_DELTA:
            if self.on_audio:
                # event.delta is raw PCM16 bytes - encode to base64 for JSON transmission
                audio_base64_str = base64.b64encode(event.delta).decode('utf-8')
                await self._call_callback(self.on_audio, audio_base64_str)
        
        elif event.type == ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DELTA:
            if self.on_transcript:
                await self._call_callback(self.on_transcript, event.delta)
        
        elif event.type == ServerEventType.RESPONSE_AUDIO_DONE:
            if self.on_status:
                await self._call_callback(self.on_status, "ready")
        
        elif event.type == ServerEventType.ERROR:
            if self.on_error:
                await self._call_callback(self.on_error, event.error.message)

        elif event.type == ServerEventType.CONVERSATION_ITEM_CREATED:
            # Detect function call items
            if hasattr(event, 'item') and event.item is not None:
                if event.item.type == ItemType.FUNCTION_CALL:
                    logger.info(f"Function call detected: {event.item.name} (call_id={event.item.call_id})")
                    self._pending_function_call = {
                        "name": event.item.name,
                        "call_id": event.item.call_id,
                        "previous_item_id": event.item.id,
                    }

        elif event.type == ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE:
            # Capture the arguments for the pending function call
            if self._pending_function_call and event.call_id == self._pending_function_call["call_id"]:
                logger.info(f"Function arguments received for {self._pending_function_call['name']}: {event.arguments}")
                self._pending_function_call["arguments"] = event.arguments
                # Execute the function call
                await self._execute_function_call()

    async def _execute_function_call(self) -> None:
        """Execute a pending function call and send the result back."""
        if not self._pending_function_call or "arguments" not in self._pending_function_call:
            return

        function_name = self._pending_function_call["name"]
        call_id = self._pending_function_call["call_id"]
        previous_item_id = self._pending_function_call["previous_item_id"]
        arguments_str = self._pending_function_call["arguments"]

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
        if self._connection:
            function_output = FunctionCallOutputItem(
                call_id=call_id,
                output=json.dumps(result),
            )
            await self._connection.conversation.item.create(
                previous_item_id=previous_item_id,
                item=function_output,
            )
            logger.info(f"Function output sent for call_id={call_id}")

            # Request new response to continue the conversation
            await self._connection.response.create()
            logger.info("Requested new response after function call")

        # Clear the pending function call
        self._pending_function_call = None

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
