"""
Finance MCP Server — Streamable HTTP
Powered by FastMCP + yfinance

Provides real-time stock data, technical analysis, financials,
options, news, dividends, earnings, and more.
"""

from __future__ import annotations

import argparse
import uvicorn
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# ──────────────────────────────────────────────
# Server
# ──────────────────────────────────────────────

# Disable DNS-rebinding protection so clients connecting from Docker bridge
# networks (non-localhost Host headers) aren't rejected with 421.
# The FastMCP constructor auto-enables protection when host="127.0.0.1"
# (the default), so we must pass this explicitly.
mcp = FastMCP(
    name="Finance MCP Server",
    instructions=(
        "Real-time stock market data, technical analysis, financials, "
        "options chains, news, dividends, earnings, and sector comparison "
        "— all sourced from Yahoo Finance via yfinance."
    ),
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)

# ──────────────────────────────────────────────
# Tools (placeholder - will be implemented in Phase 2)
# ──────────────────────────────────────────────

@mcp.tool()
def health_check() -> str:
    """Health check endpoint for container orchestration."""
    return "ok"

# ──────────────────────────────────────────────
# Entry-point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Finance MCP Server (streamable HTTP)")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument(
        "--transport",
        default="streamable-http",
        choices=["streamable-http", "sse", "stdio"],
        help="MCP transport (default: streamable-http)",
    )
    args = parser.parse_args()

    print(f"🚀  Finance MCP Server starting on {args.host}:{args.port}  [{args.transport}]")

    # Get the ASGI app for the specified transport
    if args.transport == "streamable-http":
        mcp_app = mcp.streamable_http_app()
    elif args.transport == "sse":
        mcp_app = mcp.sse_app()
    else:
        # stdio doesn't use HTTP, use the default run method
        mcp.run(transport=args.transport)
        exit(0)

    # Create a wrapper app with CORS middleware for MCP Inspector compatibility
    app = Starlette(
        routes=[Mount("/", app=mcp_app)],
        middleware=[
            Middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        ]
    )

    uvicorn.run(app, host=args.host, port=args.port)
