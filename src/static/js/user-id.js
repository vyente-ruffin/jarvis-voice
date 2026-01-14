/**
 * User ID management for JARVIS voice assistant.
 * Generates and persists a unique user ID in localStorage.
 */

const JARVIS_USER_ID_KEY = 'jarvis_user_id';

/**
 * Get the current user ID, generating a new one if none exists.
 * @returns {string} The user's UUID
 */
function getUserId() {
    let userId = localStorage.getItem(JARVIS_USER_ID_KEY);
    if (!userId) {
        userId = crypto.randomUUID();
        localStorage.setItem(JARVIS_USER_ID_KEY, userId);
    }
    return userId;
}

/**
 * Get the last 4 characters of the user ID for display purposes.
 * @returns {string} Last 4 characters of user ID
 */
function getUserIdSuffix() {
    const userId = getUserId();
    return userId.slice(-4);
}

/**
 * Build a WebSocket URL with user_id as query parameter.
 * @param {string} baseUrl - Base WebSocket URL (e.g., "ws://localhost:8000/ws")
 * @returns {string} WebSocket URL with user_id parameter
 */
function buildWebSocketUrl(baseUrl) {
    const userId = getUserId();
    const separator = baseUrl.includes('?') ? '&' : '?';
    return `${baseUrl}${separator}user_id=${encodeURIComponent(userId)}`;
}

/**
 * Update a UI element to display the user ID suffix.
 * @param {string} elementId - ID of the element to update
 */
function displayUserIdInElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = getUserIdSuffix();
    }
}

/**
 * Clear the stored user ID (for testing purposes).
 */
function clearUserId() {
    localStorage.removeItem(JARVIS_USER_ID_KEY);
}

// Export for testing if module environment
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        getUserId,
        getUserIdSuffix,
        buildWebSocketUrl,
        displayUserIdInElement,
        clearUserId,
        JARVIS_USER_ID_KEY
    };
}
