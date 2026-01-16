/**
 * User ID management for JARVIS voice assistant.
 * Generates and persists a unique user ID in localStorage.
 */

const JARVIS_USER_ID_KEY = 'jarvis_user_id';

/**
 * Generate a UUID (fallback for non-secure contexts where crypto.randomUUID is unavailable)
 * @returns {string} A UUID string
 */
function generateUUID() {
    // Use crypto.randomUUID if available (secure contexts only)
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
        return crypto.randomUUID();
    }
    // Fallback using crypto.getRandomValues if available
    if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
        return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
            (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
        );
    }
    // Last resort fallback using Math.random
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

/**
 * Get the current user ID.
 * Always returns "sudo" since the memory API requires pre-registered users.
 * @returns {string} The user's ID
 */
function getUserId() {
    // Always use "sudo" - memory API requires pre-registered users
    return "sudo";
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
