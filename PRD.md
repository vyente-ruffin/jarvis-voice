# PRD: JARVIS Memory Integration

## Introduction

Integrate long-term memory capabilities into JARVIS voice assistant, enabling it to remember user information across sessions. When complete, users will be able to tell JARVIS personal facts and have it recall them in future conversations, with visual feedback in the UI showing memory operations.

## Definition of Done

The project is complete when:
1. All unit tests pass (pytest)
2. All Playwright E2E tests pass
3. Type checks pass (mypy/pyright)
4. Application is deployed to Azure Container Apps
5. Application Insights monitoring is configured and receiving telemetry
6. Manual demo works: Say personal info → Recall later → JARVIS responds correctly

## User Experience When Complete

1. **Memory Storage**: Say "My favorite color is blue" → UI shows "Storing memory..." status → JARVIS acknowledges
2. **Memory Recall**: Ask "What's my favorite color?" → UI shows "Searching memory..." status → JARVIS responds "blue"
3. **Persistent Identity**: Refresh browser → Same user_id preserved → Memories persist
4. **Visual Feedback**: Memory operations visible in status indicator (cyan glow when searching, orange when storing)

## Goals

- Enable JARVIS to recall user information from previous sessions
- Automatically extract and store new facts during conversations
- Maintain <500ms memory retrieval latency
- Provide visual feedback for memory operations in UI
- Production deployment with monitoring

---

## Milestones

### Milestone 1: Backend Integration
Wire memory tools into Voice Live and handle function calls.

### Milestone 2: Frontend Integration
User identification and memory status UI.

### Milestone 3: Testing Suite
Unit tests, integration tests, and Playwright E2E tests.

### Milestone 4: Deployment & Monitoring
Docker build, Azure deployment, Application Insights.

---

## User Stories

### US-001: Extract user_id from WebSocket connection
**Description:** As a developer, I need to extract user_id from WebSocket query parameters so each user has isolated memories.

**TDD Approach:**
1. Write test: `test_websocket_extracts_user_id_from_query_params`
2. Write test: `test_websocket_defaults_to_anonymous_when_no_user_id`
3. Implement extraction in server.py
4. Verify tests pass

**MCP Servers:** Context7 (for FastAPI/Starlette WebSocket docs)

**Acceptance Criteria:**
- [x] Test: WebSocket with `?user_id=test123` extracts "test123"
- [x] Test: WebSocket without user_id defaults to "anonymous_user"
- [x] user_id logged on connection
- [x] user_id passed to VoiceLiveSession
- [x] Typecheck passes
- [x] `pytest tests/test_server.py -v` passes

---

### US-002: Add memory tools to VoiceLiveSession
**Description:** As a developer, I need to configure Voice Live with memory function tools so the model can call them.

**TDD Approach:**
1. Write test: `test_session_config_includes_memory_tools`
2. Write test: `test_session_config_has_tool_choice_auto`
3. Implement tools in voice_live.py
4. Verify tests pass

**MCP Servers:** Context7 (azure-ai-voicelive), Microsoft Learn (Voice Live API)

**Acceptance Criteria:**
- [x] Test: RequestSession includes search_memory and add_memory tools
- [x] Test: tool_choice is set to AUTO
- [x] MEMORY_TOOLS imported from memory_tools.py
- [x] Instructions updated to mention memory capabilities
- [x] Typecheck passes
- [x] `pytest tests/test_voice_live.py -v` passes

---

### US-003: Handle function call events
**Description:** As a developer, I need to detect and execute function calls from Voice Live so memory operations happen.

**TDD Approach:**
1. Write test: `test_detects_function_call_item_created`
2. Write test: `test_captures_function_call_arguments`
3. Write test: `test_executes_tool_handler_on_function_call`
4. Write test: `test_sends_function_output_back_to_voice_live`
5. Implement event handling in voice_live.py
6. Verify tests pass

**MCP Servers:** Context7 (azure-ai-voicelive), Microsoft Learn (Voice Live function calling)

**Acceptance Criteria:**
- [x] Test: CONVERSATION_ITEM_CREATED with FUNCTION_CALL type detected
- [x] Test: RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE captured
- [x] Test: tool_handler.handle_tool_call invoked with correct args
- [x] Test: FunctionCallOutputItem sent via conversation.item.create
- [x] Test: response.create called to continue conversation
- [x] Function calls logged for debugging
- [x] Typecheck passes
- [x] `pytest tests/test_voice_live.py -v` passes

---

### US-004: Add memory status callback
**Description:** As a developer, I need a callback for memory operations so the frontend can show status.

**TDD Approach:**
1. Write test: `test_on_memory_status_callback_called_on_search`
2. Write test: `test_on_memory_status_callback_called_on_add`
3. Implement callback in voice_live.py
4. Verify tests pass

**MCP Servers:** Context7 (Python async patterns)

**Acceptance Criteria:**
- [x] Test: on_memory_status("searching") called when search_memory starts
- [x] Test: on_memory_status("storing") called when add_memory starts
- [x] Test: on_memory_status("complete") called when operation finishes
- [x] Callback forwarded to WebSocket client
- [x] Typecheck passes
- [x] `pytest tests/test_voice_live.py -v` passes

---

### US-005: Frontend user_id generation
**Description:** As a user, I need a persistent identity so my memories are associated with me across sessions.

**TDD Approach (Playwright):**
1. Write test: `test_user_id_generated_on_first_visit`
2. Write test: `test_user_id_persisted_in_localstorage`
3. Write test: `test_websocket_url_includes_user_id`
4. Implement user-id.js
5. Verify tests pass

**MCP Servers:** Context7 (Playwright Python)

**Acceptance Criteria:**
- [x] Playwright test: UUID generated on first visit
- [x] Playwright test: Same UUID returned on refresh
- [x] Playwright test: WebSocket URL contains `?user_id=<uuid>`
- [x] user-id.js copied to src/static/js/
- [x] index.html includes user-id.js script
- [x] app.js uses getUserId() for WebSocket URL
- [x] `pytest tests/test_e2e.py::test_user_id -v` passes

---

### US-006: Memory status indicator in UI
**Description:** As a user, I want to see when JARVIS is accessing my memories so I understand what's happening.

**TDD Approach (Playwright):**
1. Write test: `test_status_shows_searching_memory`
2. Write test: `test_status_shows_storing_memory`
3. Write test: `test_status_clears_after_memory_operation`
4. Implement UI changes
5. Verify tests pass

**MCP Servers:** Context7 (Playwright Python)

**Acceptance Criteria:**
- [x] Playwright test: Status indicator shows "Searching memory..." during search
- [x] Playwright test: Status indicator shows "Storing memory..." during add
- [x] Playwright test: Status returns to normal after operation
- [x] Memory status messages handled in app.js
- [x] CSS styling for memory status states
- [x] `pytest tests/test_e2e.py::test_memory_status -v` passes

---

### US-007: Add environment variables
**Description:** As a developer, I need memory-related environment variables documented.

**TDD Approach:**
1. Write test: `test_memory_client_uses_env_var_for_url`
2. Write test: `test_memory_client_uses_env_var_for_timeout`
3. Write test: `test_memory_can_be_disabled_via_env`
4. Verify tests pass

**MCP Servers:** Context7 (python-dotenv)

**Acceptance Criteria:**
- [x] Test: MEMORY_API_URL configures API endpoint
- [x] Test: MEMORY_TIMEOUT_SECONDS configures timeout
- [x] Test: ENABLE_MEMORY=false disables memory calls
- [x] .env.example updated with memory variables
- [x] Typecheck passes
- [x] `pytest tests/test_memory_client.py -v` passes

---

### US-008: Copy memory tests
**Description:** As a developer, I need memory module tests in jarvis-voice.

**Acceptance Criteria:**
- [x] Copy ../tests/test_memory_client.py to ./tests/
- [x] Copy ../tests/test_tool_handler.py to ./tests/
- [x] Copy ../tests/test_memory_tools.py to ./tests/
- [x] All copied tests pass: `pytest tests/test_memory*.py tests/test_tool*.py -v`
- [x] Typecheck passes

---

### US-009: Playwright E2E test - Connect with user_id
**Description:** As a developer, I need E2E tests verifying WebSocket connects with user_id.

**TDD Approach (Playwright):**
1. Write test: Open browser → Check WebSocket URL has user_id
2. Write test: Refresh → Same user_id preserved
3. Verify tests pass

**MCP Servers:** Context7 (Playwright Python - expect_websocket, route_web_socket)

**Acceptance Criteria:**
- [x] Playwright test: page.expect_websocket() captures connection
- [x] Playwright test: WebSocket URL matches `/ws/voice?user_id=<uuid>`
- [x] Playwright test: Refresh preserves same user_id
- [x] tests/test_e2e.py created with pytest-playwright
- [x] `pytest tests/test_e2e.py::test_websocket_connection -v` passes

---

### US-010: Playwright E2E test - Mute/unmute functionality
**Description:** As a developer, I need E2E tests for mute button behavior.

**TDD Approach (Playwright):**
1. Write test: Click mute → Button shows muted state
2. Write test: Press M key → Toggles mute
3. Write test: Muted → No audio sent to WebSocket
4. Verify tests pass

**MCP Servers:** Context7 (Playwright Python)

**Acceptance Criteria:**
- [x] Playwright test: Click mute button toggles muted class
- [x] Playwright test: Press 'M' key toggles mute
- [x] Playwright test: Status shows "Muted" when muted
- [x] `pytest tests/test_e2e.py::test_mute -v` passes

---

### US-011: Playwright E2E test - Reconnection
**Description:** As a developer, I need E2E tests for WebSocket reconnection.

**TDD Approach (Playwright):**
1. Write test: Disconnect → Status shows "Offline"
2. Write test: Wait 2s → Reconnects automatically
3. Write test: Reconnect → Same user_id used
4. Verify tests pass

**MCP Servers:** Context7 (Playwright Python)

**Acceptance Criteria:**
- [x] Playwright test: Status indicator shows "Offline" on disconnect
- [x] Playwright test: Auto-reconnect after 2 seconds
- [x] Playwright test: Reconnection uses same user_id
- [x] `pytest tests/test_e2e.py::test_reconnection -v` passes

---

### US-012: Playwright E2E test - Error handling
**Description:** As a developer, I need E2E tests for error scenarios.

**TDD Approach (Playwright):**
1. Write test: Server error → Error displayed to user
2. Write test: Invalid response → Graceful degradation
3. Verify tests pass

**MCP Servers:** Context7 (Playwright Python)

**Acceptance Criteria:**
- [x] Playwright test: Server error message displayed
- [x] Playwright test: Invalid JSON doesn't crash app
- [x] `pytest tests/test_e2e.py::test_errors -v` passes

---

### US-013: Dockerfile for production
**Description:** As a developer, I need a Dockerfile that builds the jarvis-voice application.

**TDD Approach:**
1. Write test: Docker build succeeds
2. Write test: Container starts and responds to /health
3. Build and test locally
4. Verify tests pass

**MCP Servers:** Context7 (Docker best practices), Azure MCP (Container Apps)

**Acceptance Criteria:**
- [ ] Dockerfile created with Python 3.11 slim base
- [ ] Multi-stage build for smaller image
- [ ] Health check endpoint works in container
- [ ] `docker build -t jarvis-voice .` succeeds
- [ ] `docker run -p 8000:8000 jarvis-voice` starts
- [ ] `curl http://localhost:8000/health` returns 200

---

### US-014: Azure Container Apps deployment
**Description:** As a developer, I need to deploy jarvis-voice to Azure Container Apps.

**TDD Approach:**
1. Create Bicep IaC for Container App
2. Validate with `az deployment group what-if`
3. Deploy and verify health endpoint
4. Verify tests pass

**MCP Servers:** Azure MCP (Container Apps, deployment best practices), Microsoft Learn (Container Apps)

**Acceptance Criteria:**
- [ ] infra/main.bicep created for Container App
- [ ] Environment variables configured as secrets
- [ ] Container registry configured (ACR)
- [ ] `az deployment group what-if` validates successfully
- [ ] Deployment succeeds
- [ ] Public URL accessible and /health returns 200
- [ ] WebSocket connection works from browser

---

### US-015: Application Insights monitoring
**Description:** As a developer, I need Application Insights to monitor the production deployment.

**TDD Approach:**
1. Configure Application Insights in Bicep
2. Add telemetry to Python application
3. Deploy and verify telemetry flowing
4. Verify in Azure Portal

**MCP Servers:** Azure MCP (Application Insights), Microsoft Learn (Container Apps observability)

**Acceptance Criteria:**
- [ ] Application Insights resource in Bicep
- [ ] APPLICATIONINSIGHTS_CONNECTION_STRING env var configured
- [ ] opentelemetry-instrumentation-fastapi added to requirements
- [ ] Requests visible in Application Insights
- [ ] Custom events for memory operations logged
- [ ] Memory operation latency visible in metrics

---

### US-016: End-to-end production test
**Description:** As a user, I need to verify the complete flow works in production.

**Manual Test Steps:**
1. Open deployed URL in browser
2. Say "My name is [your name]"
3. Verify UI shows "Storing memory..." briefly
4. Check Application Insights for add_memory event
5. Refresh browser (new session)
6. Say "What's my name?"
7. Verify UI shows "Searching memory..." briefly
8. Verify JARVIS responds with correct name
9. Check Application Insights for search_memory event

**Acceptance Criteria:**
- [ ] Memory stored successfully (logs show add_memory)
- [ ] Memory recalled successfully (logs show search_memory)
- [ ] UI status indicators work in production
- [ ] Latency <500ms in Application Insights
- [ ] All Playwright E2E tests pass against production URL

---

## Non-Goals

- No changes to jarvis-cloud (memory API)
- No authentication system (user_id is anonymous UUID)
- No admin panel for viewing memories
- No memory deletion UI (API only)
- No multi-language support

## Technical Considerations

### Files to Modify

| File | Changes |
|------|---------|
| `src/server.py` | Extract user_id, forward memory status |
| `src/voice_live.py` | Add tools, handle function calls, memory callbacks |
| `src/static/index.html` | Add user-id.js script |
| `src/static/app.js` | User ID in WebSocket URL, memory status handling |
| `src/static/styles.css` | Memory status styling |
| `.env.example` | Memory environment variables |
| `requirements.txt` | Add playwright, opentelemetry |
| `Dockerfile` | Create production container |
| `infra/main.bicep` | Azure Container Apps + App Insights |

### MCP Server Usage Requirements

| Task Type | Required MCP Server |
|-----------|-------------------|
| Python/JS code patterns | Context7 |
| Azure Voice Live SDK | Context7 + Microsoft Learn |
| Azure deployment | Azure MCP |
| Azure monitoring | Azure MCP + Microsoft Learn |
| Playwright testing | Context7 |

### Testing Philosophy

**NO MOCKS. ALL REAL.**

- Memory tests call real jarvis-cloud API
- Playwright tests run against real browser
- Deployment tests hit real Azure resources

**Test User:** `jarvis_integration_test_user`

### API Endpoints

- Memory API: `https://mem0-api.greenstone-413be1c4.eastus.azurecontainerapps.io`
- Voice Live: Configured via `AZURE_VOICE_LIVE_ENDPOINT`

---

## Implementation Order

```
US-001 (user_id extraction)
    ↓
US-002 (memory tools config)
    ↓
US-003 (function call handling)
    ↓
US-004 (memory status callback)
    ↓
US-005 (frontend user_id)
    ↓
US-006 (memory status UI)
    ↓
US-007 (env variables)
    ↓
US-008 (copy tests)
    ↓
US-009-012 (Playwright E2E tests)
    ↓
US-013 (Dockerfile)
    ↓
US-014 (Azure deployment)
    ↓
US-015 (Application Insights)
    ↓
US-016 (production test)
```
