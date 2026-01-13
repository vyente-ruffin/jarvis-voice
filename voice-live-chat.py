"""
Voice Live Chat - Azure Voice Live API with proper barge-in support
"""
from __future__ import annotations
import asyncio
import base64
import os
import queue
import signal
from typing import Optional, Union

from azure.core.credentials import AzureKeyCredential
from azure.ai.voicelive.aio import connect
from azure.ai.voicelive.models import (
    AudioEchoCancellation,
    AudioNoiseReduction,
    AzureStandardVoice,
    InputAudioFormat,
    Modality,
    OutputAudioFormat,
    RequestSession,
    ServerEventType,
    ServerVad
)
from dotenv import load_dotenv
import pyaudio

# Load environment variables from .env file
load_dotenv()

# Configuration from environment variables
ENDPOINT = os.getenv("AZURE_VOICELIVE_ENDPOINT")
API_KEY = os.getenv("AZURE_VOICELIVE_API_KEY")
MODEL = os.getenv("AZURE_VOICELIVE_MODEL", "gpt-4o-mini-realtime-preview")
VOICE = os.getenv("AZURE_VOICELIVE_VOICE", "en-US-AvaNeural")
INSTRUCTIONS = os.getenv(
    "AZURE_VOICELIVE_INSTRUCTIONS",
    "You are a helpful voice assistant. Be conversational and concise. Respond naturally."
)

# Validate required environment variables
if not ENDPOINT or not API_KEY:
    raise ValueError(
        "Missing required environment variables.\n"
        "Please create a .env file with AZURE_VOICELIVE_ENDPOINT and AZURE_VOICELIVE_API_KEY.\n"
        "See .env.example for reference."
    )


class AudioPlaybackPacket:
    """Represents a packet for audio playback."""
    def __init__(self, seq_num: int, data: Optional[bytes]):
        self.seq_num = seq_num
        self.data = data


class AudioProcessor:
    """Handles real-time audio capture and playback."""

    def __init__(self, connection):
        self.connection = connection
        self.audio = pyaudio.PyAudio()
        self.loop: asyncio.AbstractEventLoop = None

        # Audio config - PCM16, 24kHz, mono
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 24000
        self.chunk_size = 1200  # 50ms

        # Streams
        self.input_stream = None
        self.output_stream = None

        # Playback queue
        self.playback_queue: queue.Queue[AudioPlaybackPacket] = queue.Queue()
        self.playback_base = 0
        self.next_seq_num = 0

    def start_capture(self):
        """Start capturing audio from microphone."""
        def _capture_callback(in_data, _frame_count, _time_info, _status_flags):
            audio_base64 = base64.b64encode(in_data).decode("utf-8")
            asyncio.run_coroutine_threadsafe(
                self.connection.input_audio_buffer.append(audio=audio_base64),
                self.loop
            )
            return (None, pyaudio.paContinue)

        if self.input_stream:
            return

        self.loop = asyncio.get_event_loop()

        self.input_stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk_size,
            stream_callback=_capture_callback
        )

    def start_playback(self):
        """Start audio playback system."""
        if self.output_stream:
            return

        remaining = bytes()

        def _playback_callback(_in_data, frame_count, _time_info, _status_flags):
            nonlocal remaining
            frame_count *= pyaudio.get_sample_size(pyaudio.paInt16)

            out = remaining[:frame_count]
            remaining = remaining[frame_count:]

            while len(out) < frame_count:
                try:
                    packet = self.playback_queue.get_nowait()
                except queue.Empty:
                    out = out + bytes(frame_count - len(out))
                    return (out, pyaudio.paContinue)

                if not packet or not packet.data:
                    break

                if packet.seq_num < self.playback_base:
                    continue

                num_to_take = frame_count - len(out)
                out = out + packet.data[:num_to_take]
                remaining = packet.data[num_to_take:]

            return (out, pyaudio.paContinue) if len(out) >= frame_count else (out, pyaudio.paComplete)

        self.output_stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            output=True,
            frames_per_buffer=self.chunk_size,
            stream_callback=_playback_callback
        )

    def _get_and_increase_seq_num(self):
        seq = self.next_seq_num
        self.next_seq_num += 1
        return seq

    def queue_audio(self, audio_data: Optional[bytes]):
        """Queue audio data for playback."""
        self.playback_queue.put(
            AudioPlaybackPacket(
                seq_num=self._get_and_increase_seq_num(),
                data=audio_data
            )
        )

    def skip_pending_audio(self):
        """Skip current audio in playback queue (for interruption)."""
        self.playback_base = self._get_and_increase_seq_num()

    def shutdown(self):
        """Clean up audio resources."""
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
            self.input_stream = None

        if self.output_stream:
            self.skip_pending_audio()
            self.queue_audio(None)
            self.output_stream.stop_stream()
            self.output_stream.close()
            self.output_stream = None

        if self.audio:
            self.audio.terminate()


class VoiceLiveAssistant:
    """Voice assistant using Azure Voice Live API with barge-in support."""

    def __init__(self):
        self.connection = None
        self.audio_processor: Optional[AudioProcessor] = None
        self.session_ready = False

    async def start(self):
        """Start the voice assistant session."""
        credential = AzureKeyCredential(API_KEY)

        print("🔌 Connecting to Voice Live API...")

        try:
            async with connect(
                endpoint=ENDPOINT,
                credential=credential,
                model=MODEL,
            ) as connection:
                self.connection = connection
                self.audio_processor = AudioProcessor(connection)

                await self._setup_session()

                self.audio_processor.start_playback()

                print("\n" + "=" * 50)
                print("🎤 VOICE LIVE ASSISTANT READY")
                print("Start speaking - you can interrupt anytime!")
                print("Press Ctrl+C to exit")
                print("=" * 50 + "\n")

                await self._process_events()
        finally:
            if self.audio_processor:
                self.audio_processor.shutdown()

    async def _setup_session(self):
        """Configure the Voice Live session."""
        # Azure voice config
        voice_config = AzureStandardVoice(name=VOICE)

        # Turn detection with sensible defaults
        turn_detection = ServerVad(
            threshold=0.5,
            prefix_padding_ms=300,
            silence_duration_ms=500
        )

        # Session config with echo cancellation and noise reduction
        session_config = RequestSession(
            modalities=[Modality.TEXT, Modality.AUDIO],
            instructions=INSTRUCTIONS,
            voice=voice_config,
            input_audio_format=InputAudioFormat.PCM16,
            output_audio_format=OutputAudioFormat.PCM16,
            turn_detection=turn_detection,
            input_audio_echo_cancellation=AudioEchoCancellation(),
            input_audio_noise_reduction=AudioNoiseReduction(type="azure_deep_noise_suppression"),
        )

        await self.connection.session.update(session=session_config)

    async def _process_events(self):
        """Process events from Voice Live connection."""
        async for event in self.connection:
            await self._handle_event(event)

    async def _handle_event(self, event):
        """Handle different types of Voice Live events."""
        ap = self.audio_processor

        if event.type == ServerEventType.SESSION_UPDATED:
            print(f"✅ Connected: {event.session.id}")
            self.session_ready = True
            ap.start_capture()

        elif event.type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED:
            print("🎤 Listening... (you can interrupt!)")
            ap.skip_pending_audio()  # Immediately stop playback for barge-in

        elif event.type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED:
            print("🤔 Processing...")

        elif event.type == ServerEventType.RESPONSE_CREATED:
            pass  # Response started

        elif event.type == ServerEventType.RESPONSE_AUDIO_DELTA:
            ap.queue_audio(event.delta)

        elif event.type == ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DELTA:
            print(f"{event.delta}", end="", flush=True)

        elif event.type == ServerEventType.RESPONSE_AUDIO_DONE:
            print("\n🎤 Ready...")

        elif event.type == ServerEventType.RESPONSE_DONE:
            pass  # Response complete

        elif event.type == ServerEventType.ERROR:
            msg = event.error.message
            if "no active response" not in msg.lower():
                print(f"❌ Error: {msg}")


async def main():
    assistant = VoiceLiveAssistant()

    def signal_handler(_sig, _frame):
        raise KeyboardInterrupt()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await assistant.start()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
