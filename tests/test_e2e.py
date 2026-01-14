"""
End-to-end Playwright tests for JARVIS Voice Interface.

These tests run against a real browser and verify the frontend behavior,
including WebSocket connections, user ID persistence, and UI interactions.

Run with: pytest tests/test_e2e.py -v
"""

import re
import pytest
from playwright.sync_api import Page, expect


# Use localhost server for E2E tests
BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context with permissions for microphone."""
    return {
        **browser_context_args,
        "permissions": ["microphone"],
    }


class TestWebSocketConnection:
    """Tests for WebSocket connection with user_id (US-009)."""

    def test_websocket_connection_includes_user_id(self, page: Page):
        """Test that WebSocket URL contains user_id query parameter.

        Verifies:
        - WebSocket connection is established to /ws/voice endpoint
        - URL includes user_id query parameter
        - user_id is a valid UUID format
        """
        captured_ws_url = None

        def handle_websocket(ws):
            nonlocal captured_ws_url
            captured_ws_url = ws.url

        page.on("websocket", handle_websocket)

        # Navigate to the app
        page.goto(BASE_URL)

        # Wait for WebSocket connection
        page.wait_for_timeout(1000)

        # Verify WebSocket was captured
        assert captured_ws_url is not None, "WebSocket connection should be established"

        # Verify URL pattern: /ws/voice?user_id=<uuid>
        assert "/ws/voice" in captured_ws_url, f"WebSocket URL should contain /ws/voice: {captured_ws_url}"
        assert "user_id=" in captured_ws_url, f"WebSocket URL should contain user_id: {captured_ws_url}"

        # Extract and validate user_id (UUID format)
        user_id_match = re.search(r'user_id=([a-f0-9-]{36})', captured_ws_url)
        assert user_id_match is not None, f"user_id should be a valid UUID: {captured_ws_url}"

    def test_user_id_persisted_in_localstorage(self, page: Page):
        """Test that user_id is stored in localStorage.

        Verifies:
        - User ID is saved to localStorage with key 'jarvis_user_id'
        - User ID is a valid UUID format
        """
        # Navigate to the app
        page.goto(BASE_URL)
        page.wait_for_timeout(500)

        # Get user_id from localStorage
        user_id = page.evaluate("localStorage.getItem('jarvis_user_id')")

        assert user_id is not None, "user_id should be stored in localStorage"
        assert len(user_id) == 36, f"user_id should be UUID format (36 chars): {user_id}"

        # Validate UUID format
        uuid_pattern = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$')
        assert uuid_pattern.match(user_id), f"user_id should match UUID pattern: {user_id}"

    def test_user_id_preserved_on_refresh(self, page: Page):
        """Test that user_id remains the same after page refresh.

        Verifies:
        - Initial user_id is generated and stored
        - After refresh, same user_id is used
        - WebSocket connection uses preserved user_id
        """
        # Navigate to the app
        page.goto(BASE_URL)
        page.wait_for_timeout(500)

        # Get initial user_id
        initial_user_id = page.evaluate("localStorage.getItem('jarvis_user_id')")
        assert initial_user_id is not None, "Initial user_id should be set"

        # Capture WebSocket URL after refresh
        captured_ws_url = None

        def handle_websocket(ws):
            nonlocal captured_ws_url
            captured_ws_url = ws.url

        page.on("websocket", handle_websocket)

        # Refresh the page
        page.reload()
        page.wait_for_timeout(1000)

        # Get user_id after refresh
        refreshed_user_id = page.evaluate("localStorage.getItem('jarvis_user_id')")

        # Verify user_id is preserved
        assert refreshed_user_id == initial_user_id, \
            f"user_id should be preserved: {initial_user_id} vs {refreshed_user_id}"

        # Verify WebSocket uses preserved user_id
        assert captured_ws_url is not None, "WebSocket should reconnect after refresh"
        assert initial_user_id in captured_ws_url, \
            f"WebSocket should use preserved user_id: {captured_ws_url}"

    def test_user_id_displayed_in_ui(self, page: Page):
        """Test that user_id suffix is displayed in the UI.

        Verifies:
        - User ID suffix (last 4 chars) is displayed in the connection status area
        """
        # Navigate to the app
        page.goto(BASE_URL)
        page.wait_for_timeout(500)

        # Get full user_id
        user_id = page.evaluate("localStorage.getItem('jarvis_user_id')")
        expected_suffix = user_id[-4:] if user_id else ""

        # Check UI element
        user_id_element = page.locator("#user-id-suffix")
        expect(user_id_element).to_be_visible()
        expect(user_id_element).to_have_text(expected_suffix)


class TestUserIdGeneration:
    """Tests for user ID generation (US-005 E2E verification)."""

    def test_new_user_gets_new_id(self, page: Page, context):
        """Test that a new browser context gets a new user_id.

        Verifies:
        - New session without localStorage generates new user_id
        """
        # Clear localStorage first
        page.goto(BASE_URL)
        page.evaluate("localStorage.clear()")

        # Reload to trigger new ID generation
        page.reload()
        page.wait_for_timeout(500)

        user_id = page.evaluate("localStorage.getItem('jarvis_user_id')")
        assert user_id is not None, "New user_id should be generated"
        assert len(user_id) == 36, "user_id should be UUID format"


class TestMuteUnmute:
    """Tests for mute/unmute functionality (US-010)."""

    def test_click_mute_button_toggles_muted_class(self, page: Page):
        """Test that clicking the mute button toggles the muted class.

        Verifies:
        - Initially, mute button does not have 'muted' class
        - After click, button has 'muted' class
        - After second click, button does not have 'muted' class
        """
        page.goto(BASE_URL)
        page.wait_for_timeout(500)

        mute_button = page.locator("#mute-button")

        # Initially not muted
        expect(mute_button).not_to_have_class(re.compile(r'\bmuted\b'))

        # Click to mute
        mute_button.click()
        expect(mute_button).to_have_class(re.compile(r'\bmuted\b'))

        # Click again to unmute
        mute_button.click()
        expect(mute_button).not_to_have_class(re.compile(r'\bmuted\b'))

    def test_press_m_key_toggles_mute(self, page: Page):
        """Test that pressing 'M' key toggles mute state.

        Verifies:
        - Pressing 'M' key mutes when unmuted
        - Pressing 'M' key again unmutes when muted
        """
        page.goto(BASE_URL)
        page.wait_for_timeout(500)

        mute_button = page.locator("#mute-button")

        # Initially not muted
        expect(mute_button).not_to_have_class(re.compile(r'\bmuted\b'))

        # Press M to mute
        page.keyboard.press("m")
        expect(mute_button).to_have_class(re.compile(r'\bmuted\b'))

        # Press M again to unmute
        page.keyboard.press("m")
        expect(mute_button).not_to_have_class(re.compile(r'\bmuted\b'))

    def test_status_shows_muted_when_muted(self, page: Page):
        """Test that status indicator shows 'Muted' when muted.

        Verifies:
        - User status shows 'Muted' when mute button is clicked
        - User status no longer shows 'Muted' when unmuted
        """
        page.goto(BASE_URL)
        page.wait_for_timeout(500)

        user_status = page.locator("#user-status")
        mute_button = page.locator("#mute-button")

        # Initially not showing "Muted"
        expect(user_status).not_to_have_text("Muted")

        # Click to mute
        mute_button.click()
        expect(user_status).to_have_text("Muted")
        expect(user_status).to_have_class(re.compile(r'\bmuted\b'))

        # Click to unmute
        mute_button.click()
        expect(user_status).not_to_have_text("Muted")
