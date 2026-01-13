"""
FastAPI WebSocket server for Jarvis Voice Assistant.

Provides:
- /health endpoint for health checks
- /ws/voice WebSocket endpoint for voice communication
- Static file serving for frontend
"""

import os
import asyncio
import logging
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from dotenv import load_dotenv

from src.voice_live import VoiceLiveSession

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI(title="Jarvis Voice API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Voice Live configuration from environment
VOICE_LIVE_ENDPOINT = os.getenv("AZURE_VOICE_LIVE_ENDPOINT", "")
VOICE_LIVE_API_KEY = os.getenv("AZURE_VOICE_LIVE_API_KEY", "")
VOICE_LIVE_MODEL = os.getenv("AZURE_VOICE_LIVE_MODEL", "gpt-4o-mini-realtime-preview")
VOICE_LIVE_VOICE = os.getenv("AZURE_VOICE_LIVE_VOICE", "en-US-AvaNeural")
VOICE_LIVE_INSTRUCTIONS = os.getenv(
    "AZURE_VOICE_LIVE_INSTRUCTIONS",
    "You are JARVIS, a helpful and intelligent voice assistant. Be conversational, concise, and helpful."
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.websocket("/ws/voice")
async def websocket_voice(websocket: WebSocket):
    """WebSocket endpoint for voice communication."""
    await websocket.accept()

    # Send connected message
    await websocket.send_json({"type": "connected"})

    # Check if Voice Live credentials are configured
    if not VOICE_LIVE_ENDPOINT or not VOICE_LIVE_API_KEY:
        await websocket.send_json({
            "type": "error",
            "message": "Voice Live API not configured. Set AZURE_VOICE_LIVE_ENDPOINT and AZURE_VOICE_LIVE_API_KEY."
        })
        # Continue without Voice Live for testing
        try:
            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type")

                if msg_type == "mute":
                    muted = data.get("muted", False)
                    await websocket.send_json({"type": "mute_status", "muted": muted})

        except WebSocketDisconnect:
            pass
        return

    # Create Voice Live session
    session = VoiceLiveSession(
        endpoint=VOICE_LIVE_ENDPOINT,
        api_key=VOICE_LIVE_API_KEY,
        model=VOICE_LIVE_MODEL,
        voice=VOICE_LIVE_VOICE,
        instructions=VOICE_LIVE_INSTRUCTIONS,
    )

    # Set up callbacks to forward events to WebSocket client
    async def on_audio(audio_base64: str):
        """Forward audio from Voice Live to client."""
        try:
            logger.info(f"AUDIO: Received {len(audio_base64) if audio_base64 else 0} bytes")
            await websocket.send_json({"type": "audio", "data": audio_base64})
        except Exception as e:
            logger.error(f"AUDIO ERROR: {e}")

    async def on_transcript(text: str):
        """Forward transcript from Voice Live to client."""
        try:
            logger.info(f"TRANSCRIPT: {text}")
            await websocket.send_json({"type": "transcript", "text": text})
        except Exception as e:
            logger.error(f"TRANSCRIPT ERROR: {e}")

    async def on_speech_started():
        """User started speaking - send barge-in signal."""
        try:
            await websocket.send_json({"type": "clear_audio"})
        except Exception:
            pass

    async def on_status(status: str):
        """Forward status updates to client."""
        try:
            await websocket.send_json({"type": "status", "state": status})
        except Exception:
            pass

    async def on_error(error: str):
        """Forward errors to client."""
        try:
            await websocket.send_json({"type": "error", "message": error})
        except Exception:
            pass

    # Register callbacks
    session.on_audio = on_audio
    session.on_transcript = on_transcript
    session.on_speech_started = on_speech_started
    session.on_status = on_status
    session.on_error = on_error

    muted = False

    try:
        # Connect to Voice Live
        logger.info(f"Connecting to Voice Live: {VOICE_LIVE_ENDPOINT}")
        await session.connect()
        logger.info("Voice Live connected successfully")

        while True:
            # Receive message from client
            data = await websocket.receive_json()

            msg_type = data.get("type")

            if msg_type == "audio":
                # Forward audio to Voice Live (only if not muted)
                if not muted:
                    audio_data = data.get("data", "")
                    if audio_data:
                        await session.send_audio(audio_data)

            elif msg_type == "mute":
                # Handle mute toggle
                muted = data.get("muted", False)
                await websocket.send_json({"type": "mute_status", "muted": muted})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        # Clean up Voice Live session
        await session.disconnect()


# Mount static files (must be last to not override other routes)
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/", StaticFiles(directory=str(static_path), html=True), name="static")
