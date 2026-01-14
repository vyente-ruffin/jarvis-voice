# PRD: JARVIS Memory Integration into jarvis-voice

## Introduction

Integrate the memory modules from `jarvis-cloud-and-memory` into the `jarvis-voice` Azure Voice Live application. This enables JARVIS to remember user information across sessions.

**Source Code:** `../src/` (memory modules already built and tested)
**Target:** `./jarvis-voice/` (Azure Voice Live app)

**Approach: Copy and Wire**
- Copy existing memory modules into jarvis-voice
- Modify server.py to use memory tools
- Modify voice_live.py to handle function calls
- No new code to write - just integration

**Research Constraints (MANDATORY)**
- Code/Library docs → Use **Context7 MCP server** ONLY
- Microsoft/Azure docs → Use **Microsoft Learn MCP server** ONLY
- Azure operations → Use **Azure MCP server** ONLY
- DO NOT use general web search or WebFetch for documentation

## Goals

- Enable JARVIS to recall user information from previous sessions
- Automatically extract and store new facts during conversations
- Maintain <500ms memory retrieval latency
- All existing tests continue to pass
- New integration tests pass

## User Stories

### US-001: Copy memory modules into jarvis-voice
**Description:** As a developer, I need to copy the memory integration modules into the jarvis-voice src directory.

**Acceptance Criteria:**
- [x] Copy `../src/memory_client.py` to `./src/memory_client.py`
- [x] Copy `../src/memory_tools.py` to `./src/memory_tools.py`
- [x] Copy `../src/tool_handler.py` to `./src/tool_handler.py`
- [x] Copy `../src/logging_config.py` to `./src/logging_config.py`
- [x] Verify imports work: `python -c "from src.memory_client import search_memory"`
- [x] Typecheck passes

---

### US-002: Update requirements.txt
**Description:** As a developer, I need to add memory client dependencies.

**Acceptance Criteria:**
- [x] Add `httpx>=0.25.0` to requirements.txt
- [x] Add `python-dotenv>=1.0.0` to requirements.txt (if not present)
- [x] Run `pip install -r requirements.txt` successfully
- [x] Typecheck passes

---

### US-003: Extract user_id from WebSocket connection
**Description:** As a developer, I need to extract the user_id from the WebSocket query string.

**Acceptance Criteria:**
- [x] Modify `server.py` websocket_voice function to extract user_id from query params
- [x] Default to "anonymous_user" if no user_id provided
- [x] Log user_id on connection
- [x] Pass user_id to VoiceLiveSession
- [x] Typecheck passes

**Implementation:**
```python
# In websocket_voice function
from urllib.parse import parse_qs

query_string = websocket.scope.get("query_string", b"").decode()
params = parse_qs(query_string)
user_id = params.get("user_id", ["anonymous_user"])[0]
logger.info(f"WebSocket connected: user_id={user_id}")
```

---

### US-004: Add memory tools to VoiceLiveSession
**Description:** As a developer, I need to configure Voice Live with memory function calling tools.

**Acceptance Criteria:**
- [x] Import MEMORY_TOOLS from memory_tools.py
- [x] Modify VoiceLiveSession.__init__ to accept tools parameter
- [x] Pass tools in RequestSession configuration
- [x] Set tool_choice to "auto"
- [x] Update instructions to mention memory capabilities
- [x] Typecheck passes

**Updated Instructions:**
```python
VOICE_LIVE_INSTRUCTIONS = """You are JARVIS, a helpful AI assistant with long-term memory.
You can remember facts about the user across sessions.
Use search_memory before answering personal questions like "what's my favorite..." or "do you remember...".
Use add_memory when the user shares personal information, preferences, or important details.
Be conversational, concise, and helpful."""
```

---

### US-005: Handle function call events in voice_live.py
**Description:** As a developer, I need to handle function call events from Voice Live and execute memory operations.

**Acceptance Criteria:**
- [x] Import tool_handler module
- [x] Add on_function_call callback to VoiceLiveSession
- [x] Detect function call events in _handle_events loop
- [x] Call tool_handler.handle_tool_call with function name and arguments
- [x] Send function output back via conversation.item.create
- [x] Trigger response.create to continue conversation
- [x] Log function calls for debugging
- [x] Typecheck passes

---

### US-006: Update frontend to send user_id
**Description:** As a developer, I need the frontend to generate and send user_id with WebSocket connection.

**Acceptance Criteria:**
- [ ] Copy `../static/js/user-id.js` to `./src/static/js/user-id.js`
- [ ] Update frontend HTML/JS to include user-id.js
- [ ] Modify WebSocket connection URL to include user_id query param
- [ ] Display user_id suffix in UI (last 4 chars)
- [ ] Verify changes work in browser

---

### US-007: Add environment variables
**Description:** As a developer, I need to add memory-related environment variables.

**Acceptance Criteria:**
- [ ] Add MEMORY_API_URL to .env.example
- [ ] Add MEMORY_TIMEOUT_SECONDS to .env.example
- [ ] Add ENABLE_MEMORY to .env.example
- [ ] Document variables in README
- [ ] Typecheck passes

**Environment Variables:**
```bash
# Memory Integration
MEMORY_API_URL=https://mem0-api.greenstone-413be1c4.eastus.azurecontainerapps.io
MEMORY_TIMEOUT_SECONDS=3
ENABLE_MEMORY=true
```

---

### US-008: Copy and run tests
**Description:** As a developer, I need to copy memory tests and verify everything works.

**Acceptance Criteria:**
- [ ] Copy `../tests/test_memory_client.py` to `./tests/`
- [ ] Copy `../tests/test_tool_handler.py` to `./tests/`
- [ ] Copy `../tests/test_integration.py` to `./tests/`
- [ ] Run all tests: `pytest tests/`
- [ ] All tests pass
- [ ] Typecheck passes

---

### US-009: Test end-to-end locally
**Description:** As a developer, I need to verify the integration works locally.

**Acceptance Criteria:**
- [ ] Start server locally: `python -m src.server`
- [ ] Connect via browser
- [ ] Tell JARVIS something personal (e.g., "My favorite color is blue")
- [ ] Verify memory is stored (check jarvis-cloud API or logs)
- [ ] Ask JARVIS to recall (e.g., "What's my favorite color?")
- [ ] Verify JARVIS remembers correctly
- [ ] All tests pass
- [ ] Typecheck passes

---

## Non-Goals

- No changes to jarvis-cloud (memory API)
- No new Azure resources
- No changes to deployment infrastructure (Bicep stays same)
- No authentication system

## Technical Considerations

### Files to Copy

| Source | Destination |
|--------|-------------|
| `../src/memory_client.py` | `./src/memory_client.py` |
| `../src/memory_tools.py` | `./src/memory_tools.py` |
| `../src/tool_handler.py` | `./src/tool_handler.py` |
| `../src/logging_config.py` | `./src/logging_config.py` |
| `../static/js/user-id.js` | `./src/static/js/user-id.js` |
| `../tests/test_memory_client.py` | `./tests/test_memory_client.py` |
| `../tests/test_tool_handler.py` | `./tests/test_tool_handler.py` |
| `../tests/test_integration.py` | `./tests/test_integration.py` |

### Files to Modify

| File | Changes |
|------|---------|
| `./src/server.py` | Extract user_id, pass to session |
| `./src/voice_live.py` | Add tools config, handle function calls |
| `./src/static/index.html` | Include user-id.js, update WebSocket URL |
| `./requirements.txt` | Add httpx |
| `./.env.example` | Add memory env vars |

### Integration Points

```
Browser → WebSocket(/ws/voice?user_id=xxx) → server.py
                                               ↓
                                         VoiceLiveSession
                                               ↓
                                         Azure Voice Live
                                               ↓
                                         Function Call Event
                                               ↓
                                         tool_handler.py
                                               ↓
                                         memory_client.py
                                               ↓
                                         jarvis-cloud API
```

## Testing Philosophy

**NO MOCKS. ALL REAL.**

All tests call the real jarvis-cloud API at:
`https://mem0-api.greenstone-413be1c4.eastus.azurecontainerapps.io`

## Implementation Order

```
US-001 (copy modules)
    ↓
US-002 (requirements)
    ↓
US-003 (user_id extraction)
    ↓
US-004 (memory tools config)
    ↓
US-005 (function call handling)
    ↓
US-006 (frontend user_id)
    ↓
US-007 (env vars)
    ↓
US-008 (copy tests)
    ↓
US-009 (e2e test)
```
