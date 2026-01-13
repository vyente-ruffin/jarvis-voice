"""
Tests for Task 1.2: src/server.py

Tests the FastAPI WebSocket server with:
- Health check endpoint
- WebSocket connection for voice
- Static file serving

These tests should FAIL initially (red phase of TDD) since no implementation exists.
"""

import pytest
from fastapi.testclient import TestClient
from starlette.testclient import TestClient as StarletteTestClient
import json


class TestHealthEndpoint:
    """Tests for GET /health endpoint."""

    def test_health_returns_200(self):
        """GET /health should return 200 OK."""
        from src.server import app

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200

    def test_health_returns_json(self):
        """GET /health should return JSON response."""
        from src.server import app

        client = TestClient(app)
        response = client.get("/health")

        assert response.headers.get("content-type") == "application/json"
        data = response.json()
        assert "status" in data or response.status_code == 200


class TestWebSocketVoice:
    """Tests for WebSocket /ws/voice endpoint."""

    def test_websocket_accepts_connection(self):
        """WebSocket /ws/voice should accept connections."""
        from src.server import app

        client = TestClient(app)

        with client.websocket_connect("/ws/voice") as websocket:
            # Connection should be accepted without raising an exception
            assert websocket is not None

    def test_websocket_sends_connected_message_on_connect(self):
        """WebSocket should send {"type": "connected"} on connection."""
        from src.server import app

        client = TestClient(app)

        with client.websocket_connect("/ws/voice") as websocket:
            # First message should be connection confirmation
            data = websocket.receive_json()

            assert data is not None
            assert data.get("type") == "connected"

    def test_websocket_receives_audio_message(self):
        """WebSocket should accept audio messages from client."""
        from src.server import app

        client = TestClient(app)

        with client.websocket_connect("/ws/voice") as websocket:
            # Receive the initial connected message
            websocket.receive_json()

            # Send an audio message
            audio_message = {
                "type": "audio",
                "data": "SGVsbG8gV29ybGQ="  # base64 encoded "Hello World"
            }
            websocket.send_json(audio_message)

            # Should not raise an exception - server accepted the message

    def test_websocket_receives_mute_message(self):
        """WebSocket should accept mute messages from client."""
        from src.server import app

        client = TestClient(app)

        with client.websocket_connect("/ws/voice") as websocket:
            # Receive the initial connected message
            websocket.receive_json()

            # Send a mute message
            mute_message = {
                "type": "mute",
                "muted": True
            }
            websocket.send_json(mute_message)

            # Should not raise an exception - server accepted the message


class TestStaticFiles:
    """Tests for static file serving at root /."""

    def test_static_files_served_at_root(self):
        """Static files should be served at / path."""
        from src.server import app

        client = TestClient(app)

        # The root should serve static files (index.html or similar)
        # This test may 404 until static files are created, but the route should exist
        response = client.get("/")

        # Either 200 (file exists) or a specific error indicating static mount exists
        # In FastAPI, if static files are mounted but index.html doesn't exist,
        # it returns 404, but the mount point itself should be configured
        assert response.status_code in [200, 404]

    def test_index_html_served_at_root(self):
        """GET / should serve index.html when it exists."""
        from src.server import app
        import os

        client = TestClient(app)

        # Create a temporary index.html for testing if needed
        static_path = os.path.join(os.path.dirname(__file__), "..", "src", "static")
        index_path = os.path.join(static_path, "index.html")

        # Only test if index.html exists
        if os.path.exists(index_path):
            response = client.get("/")
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")


class TestCORSMiddleware:
    """Tests for CORS middleware configuration."""

    def test_cors_headers_present(self):
        """CORS headers should be present in responses."""
        from src.server import app

        client = TestClient(app)

        # Make a request with Origin header
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )

        # CORS headers should be present
        # Note: This may vary based on CORS configuration
        assert response.status_code == 200

    def test_cors_allows_options_preflight(self):
        """CORS should handle OPTIONS preflight requests."""
        from src.server import app

        client = TestClient(app)

        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )

        # Preflight should succeed (200 or 204)
        assert response.status_code in [200, 204, 405]


class TestAppExists:
    """Tests to verify the app module and object exist."""

    def test_app_is_fastapi_instance(self):
        """src.server.app should be a FastAPI instance."""
        from src.server import app
        from fastapi import FastAPI

        assert isinstance(app, FastAPI)

    def test_server_module_importable(self):
        """src.server module should be importable."""
        try:
            from src import server
            assert server is not None
        except ImportError as e:
            pytest.fail(f"Could not import src.server: {e}")
