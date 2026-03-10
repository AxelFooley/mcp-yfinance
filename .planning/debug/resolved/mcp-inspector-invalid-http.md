---
status: resolved
trigger: "Connecting with MCP Inspector gives 'finance-mcp-1  | WARNING:  Invalid HTTP request received.'"
created: "2026-03-10T12:00:00.000Z"
updated: "2026-03-10T12:57:00.000Z"
resolved: "2026-03-10T13:00:00.000Z"
---

## Current Focus
hypothesis: ROOT CAUSE FOUND - MCP Inspector doesn't properly handle session IDs in stateful mode. Solution: Enable stateless_http=True mode to create a new transport per request, eliminating the need for session management.
test: Verified through curl testing that stateless mode works correctly - multiple sequential requests succeed without requiring session ID headers
expecting: MCP Inspector should now connect successfully and list available tools
next_action: Request user verification with MCP Inspector

## Symptoms
expected: MCP Inspector should connect and list available tools
actual: WARNING: Invalid HTTP request received (from docker logs)
errors: finance-mcp-1  | WARNING:  Invalid HTTP request received.
reproduction: User runs docker compose up and tries to connect MCP Inspector to http://localhost:8000/mcp
started: Unknown if this ever worked before

## Eliminated

## Evidence
- timestamp: 2026-03-10T12:00:00.000Z
  checked: server.py, docker-compose.yml, Dockerfile, STATE.md
  found: Server uses FastMCP with streamable-http transport, wraps in Starlette app with CORS middleware
  implication: Server implementation looks correct for MCP HTTP transport

- timestamp: 2026-03-10T12:15:00.000Z
  checked: Docker logs and uvicorn source code
  found: WARNING: Invalid HTTP request received. comes from h11.RemoteProtocolError in uvicorn's HTTP parser
  implication: The server is receiving malformed HTTP requests, or requests that violate the HTTP protocol

- timestamp: 2026-03-10T12:25:00.000Z
  checked: Docker logs exception traceback
  found: RuntimeError: Task group is not initialized. Make sure to use run(). in streamable_http_manager.py line 144
  implication: The StreamableHTTPSessionManager requires proper async initialization through mcp.run() or similar

- timestamp: 2026-03-10T12:35:00.000Z
  checked: StreamableHTTPSessionManager source code
  found: The run() method creates the task group and must be called during lifespan before handle_request()
  implication: The current implementation manually creates the Starlette app without calling session_manager.run()

- timestamp: 2026-03-10T12:45:00.000Z
  checked: Testing after fix
  found: Server starts without errors, no "Invalid HTTP request received" warnings, proper HTTP responses
  implication: The task group is being properly initialized via the streamable_http_app() lifespan

- timestamp: 2026-03-10T12:50:00.000Z
  checked: Docker logs showing session ID creation and 400 errors
  found: Pattern shows first POST creates session (200 OK), second POST with same session fails (400 Bad Request)
  implication: MCP Inspector is not sending the mcp-session-id header in subsequent requests

- timestamp: 2026-03-10T12:55:00.000Z
  checked: curl testing with and without session ID headers
  found: 1) Request without session ID creates new session (200), 2) Request WITH session ID works (200), 3) Request without session ID fails (400 - "Missing session ID")
  implication: The server requires session ID in stateful mode, but MCP Inspector doesn't send it

- timestamp: 2026-03-10T12:57:00.000Z
  checked: FastMCP source code for stateless_http option
  found: FastMCP constructor accepts stateless_http parameter, which creates a new transport per request without session management
  implication: Enabling stateless_http=True will fix the compatibility issue with MCP Inspector

## Resolution
root_cause: server.py was creating a new Starlette app with Mount() to wrap the MCP app for CORS support, but this bypassed the lifespan of the inner MCP app. The lifespan is where session_manager.run() is called, which initializes the _task_group required by StreamableHTTPSessionManager.handle_request(). After fixing that issue, a second issue emerged: MCP Inspector was not sending the mcp-session-id header in subsequent requests after session creation, causing 400 Bad Request errors.
fix:
  1. Changed from wrapping the MCP app in a new Starlette app to using app.add_middleware() on the existing MCP app. This preserves the lifespan while adding CORS support for MCP Inspector compatibility.
  2. Enabled stateless_http=True mode in FastMCP constructor. In stateless mode, the server creates a new transport for each request, eliminating the need for session management and making it compatible with clients that don't properly handle session IDs.
verification:
  - Docker logs show clean startup with "StreamableHTTP session manager started"
  - No "Invalid HTTP request received" warnings
  - Server returns proper HTTP responses (406 for missing Accept header)
  - Multiple sequential requests work without requiring session ID headers
  - Server works in stateless mode, creating a fresh transport per request
files_changed: ["server.py"]
