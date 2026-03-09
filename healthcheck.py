"""Docker HEALTHCHECK — probes the MCP HTTP endpoint."""

import sys
import urllib.request

req = urllib.request.Request(
    "http://localhost:8000/mcp",
    data=b'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"healthcheck","version":"1.0"}}}',
    headers={
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    },
)
try:
    urllib.request.urlopen(req, timeout=5)
    sys.exit(0)
except Exception:
    sys.exit(1)
