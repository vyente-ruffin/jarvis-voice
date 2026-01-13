"""
Tests for Task 1.3: src/voice_live.py

Tests the Voice Live session manager that wraps Azure AI VoiceLive SDK.

IMPORTANT: These tests are based on the ACTUAL Azure SDK API (validated via Microsoft Learn):
- azure.ai.voicelive.aio.connect() function returns a connection object
- Connection is async iterable (async for event in connection)
- Audio sent via connection.input_audio_buffer.append()
- Events have .type attribute (ServerEventType enum)

These tests should FAIL initially (red phase of TDD) since no implementation exists.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio


class TestVoiceLiveSessionExists:
    """Tests to verify the VoiceLiveSession class exists with correct interface."""

    def test_voice_live_module_importable(self):
        """src.voice_live module should be importable."""
        try:
            from src import voice_live
            assert voice_live is not None
        except ImportError as e:
            pytest.fail(f"Could not import src.voice_live: {e}")

    def test_voice_live_session_class_exists(self):
        """VoiceLiveSession class should exist in src.voice_live."""
        from src.voice_live import VoiceLiveSession
        assert VoiceLiveSession is not None

    def test_voice_live_session_is_class(self):
        """VoiceLiveSession should be a class."""
        from src.voice_live import VoiceLiveSession
        assert isinstance(VoiceLiveSession, type)


class TestVoiceLiveSessionInit:
    """Tests for VoiceLiveSession initialization."""

    def test_init_accepts_endpoint_and_key(self):
        """VoiceLiveSession should accept endpoint and api_key parameters."""
        from src.voice_live import VoiceLiveSession

        session = VoiceLiveSession(
            endpoint="https://test.api.cognitive.microsoft.com/",
            api_key="test-key"
        )
        assert session is not None

    def test_init_accepts_model_parameter(self):
        """VoiceLiveSession should accept optional model parameter."""
        from src.voice_live import VoiceLiveSession

        session = VoiceLiveSession(
            endpoint="https://test.api.cognitive.microsoft.com/",
            api_key="test-key",
            model="gpt-4o-mini-realtime-preview"
        )
        assert session is not None

    def test_init_accepts_voice_parameter(self):
        """VoiceLiveSession should accept optional voice parameter."""
        from src.voice_live import VoiceLiveSession

        session = VoiceLiveSession(
            endpoint="https://test.api.cognitive.microsoft.com/",
            api_key="test-key",
            voice="en-US-AvaNeural"
        )
        assert session is not None


class TestVoiceLiveSessionMethods:
    """Tests for VoiceLiveSession methods."""

    def test_connect_method_exists(self):
        """VoiceLiveSession should have a connect() method."""
        from src.voice_live import VoiceLiveSession

        session = VoiceLiveSession(
            endpoint="https://test.api.cognitive.microsoft.com/",
            api_key="test-key"
        )
        assert hasattr(session, 'connect')
        assert callable(session.connect)

    def test_connect_is_async(self):
        """connect() should be an async method."""
        from src.voice_live import VoiceLiveSession
        import inspect

        session = VoiceLiveSession(
            endpoint="https://test.api.cognitive.microsoft.com/",
            api_key="test-key"
        )
        assert inspect.iscoroutinefunction(session.connect)

    def test_disconnect_method_exists(self):
        """VoiceLiveSession should have a disconnect() method."""
        from src.voice_live import VoiceLiveSession

        session = VoiceLiveSession(
            endpoint="https://test.api.cognitive.microsoft.com/",
            api_key="test-key"
        )
        assert hasattr(session, 'disconnect')
        assert callable(session.disconnect)

    def test_send_audio_method_exists(self):
        """VoiceLiveSession should have a send_audio() method."""
        from src.voice_live import VoiceLiveSession

        session = VoiceLiveSession(
            endpoint="https://test.api.cognitive.microsoft.com/",
            api_key="test-key"
        )
        assert hasattr(session, 'send_audio')
        assert callable(session.send_audio)

    def test_send_audio_is_async(self):
        """send_audio() should be an async method."""
        from src.voice_live import VoiceLiveSession
        import inspect

        session = VoiceLiveSession(
            endpoint="https://test.api.cognitive.microsoft.com/",
            api_key="test-key"
        )
        assert inspect.iscoroutinefunction(session.send_audio)


class TestVoiceLiveSessionCallbacks:
    """Tests for VoiceLiveSession callback registration."""

    def test_on_audio_callback_settable(self):
        """VoiceLiveSession should allow setting on_audio callback."""
        from src.voice_live import VoiceLiveSession

        session = VoiceLiveSession(
            endpoint="https://test.api.cognitive.microsoft.com/",
            api_key="test-key"
        )

        callback = AsyncMock()
        session.on_audio = callback
        assert session.on_audio == callback

    def test_on_transcript_callback_settable(self):
        """VoiceLiveSession should allow setting on_transcript callback."""
        from src.voice_live import VoiceLiveSession

        session = VoiceLiveSession(
            endpoint="https://test.api.cognitive.microsoft.com/",
            api_key="test-key"
        )

        callback = AsyncMock()
        session.on_transcript = callback
        assert session.on_transcript == callback

    def test_on_speech_started_callback_settable(self):
        """VoiceLiveSession should allow setting on_speech_started callback."""
        from src.voice_live import VoiceLiveSession

        session = VoiceLiveSession(
            endpoint="https://test.api.cognitive.microsoft.com/",
            api_key="test-key"
        )

        callback = AsyncMock()
        session.on_speech_started = callback
        assert session.on_speech_started == callback

    def test_on_status_callback_settable(self):
        """VoiceLiveSession should allow setting on_status callback."""
        from src.voice_live import VoiceLiveSession

        session = VoiceLiveSession(
            endpoint="https://test.api.cognitive.microsoft.com/",
            api_key="test-key"
        )

        callback = AsyncMock()
        session.on_status = callback
        assert session.on_status == callback


class TestVoiceLiveSessionSendAudio:
    """Tests for send_audio() method behavior."""

    @pytest.mark.asyncio
    async def test_send_audio_accepts_base64_string(self):
        """send_audio() should accept a base64 encoded string."""
        from src.voice_live import VoiceLiveSession

        session = VoiceLiveSession(
            endpoint="https://test.api.cognitive.microsoft.com/",
            api_key="test-key"
        )

        # Mock the internal connection to avoid real API calls
        session._connection = AsyncMock()
        session._connection.input_audio_buffer = AsyncMock()
        session._connection.input_audio_buffer.append = AsyncMock()

        # This should not raise an exception
        base64_audio = "SGVsbG8gV29ybGQ="  # "Hello World" in base64
        await session.send_audio(base64_audio)

    @pytest.mark.asyncio
    async def test_send_audio_raises_without_connection(self):
        """send_audio() should raise error if not connected."""
        from src.voice_live import VoiceLiveSession

        session = VoiceLiveSession(
            endpoint="https://test.api.cognitive.microsoft.com/",
            api_key="test-key"
        )

        # Should raise some kind of error when not connected
        with pytest.raises(Exception):
            await session.send_audio("SGVsbG8=")


class TestVoiceLiveSessionContextManager:
    """Tests for async context manager support."""

    def test_supports_async_context_manager(self):
        """VoiceLiveSession should support async context manager protocol."""
        from src.voice_live import VoiceLiveSession

        session = VoiceLiveSession(
            endpoint="https://test.api.cognitive.microsoft.com/",
            api_key="test-key"
        )

        # Should have __aenter__ and __aexit__ methods
        assert hasattr(session, '__aenter__')
        assert hasattr(session, '__aexit__')
