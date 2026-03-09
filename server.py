"""
Finance MCP Server — Streamable HTTP
Powered by FastMCP + yfinance

Provides real-time stock data, technical analysis, financials,
options, news, dividends, earnings, and more.
"""

from __future__ import annotations

import argparse
import logging
import math
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable

import pandas as pd
import uvicorn
import yfinance as yf
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Data Quality Helpers
# ──────────────────────────────────────────────


def _safe(value: Any) -> Any | None:
    """Convert pandas NaN/Inf values to JSON-compatible None."""
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
    return value


def _iso_format(value: Any) -> Any:
    """Convert pandas Timestamps to ISO 8601 strings recursively."""
    if isinstance(value, datetime):
        return value.isoformat()
    elif isinstance(value, dict):
        return {k: _iso_format(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_iso_format(v) for v in value]
    return value


def _df_to_records(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame to list of dicts with proper serialization."""
    if df.empty:
        return []
    records = df.to_dict("records")
    return [{k: _safe(_iso_format(v)) for k, v in record.items()} for record in records]


def _series_to_dict(series: pd.Series) -> dict:
    """Convert Series to dict with NaN handling."""
    return {k: _safe(v) for k, v in series.to_dict().items()}


# ──────────────────────────────────────────────
# In-Memory Cache
# ──────────────────────────────────────────────

_cache: dict[str, tuple[Any, datetime]] = {}


def _cache_key(symbol: str, data_type: str, **kwargs: Any) -> str:
    """Generate cache key from symbol, data_type, and sorted kwargs."""
    parts = [symbol, data_type] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
    return ":".join(str(p) for p in parts)


def _cache_get(key: str, ttl: int) -> Any | None:
    """Get cached value if exists and not expired."""
    if key in _cache:
        value, expiry = _cache[key]
        if datetime.now() < expiry:
            return value
        del _cache[key]
    return None


def _cache_set(key: str, value: Any, ttl: int) -> None:
    """Store value with expiry time."""
    expiry = datetime.now() + timedelta(seconds=ttl)
    _cache[key] = (value, expiry)


def cached(ttl: int):
    """Decorator factory for caching function results."""

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(symbol: str, **kwargs: Any) -> Any:
            key = _cache_key(symbol, fn.__name__, **kwargs)
            if (cached_value := _cache_get(key, ttl)) is not None:
                return cached_value
            result = fn(symbol, **kwargs)
            _cache_set(key, result, ttl)
            return result

        return wrapper

    return decorator


# ──────────────────────────────────────────────
# Ticker Cache
# ──────────────────────────────────────────────

_ticker_cache: dict[str, yf.Ticker] = {}


def _ticker(symbol: str) -> yf.Ticker:
    """Get or create cached yfinance Ticker object."""
    symbol = symbol.upper()
    if symbol not in _ticker_cache:
        _ticker_cache[symbol] = yf.Ticker(symbol)
    return _ticker_cache[symbol]


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
# Tools
# ──────────────────────────────────────────────


@mcp.tool()
def health_check() -> str:
    """Health check endpoint for container orchestration."""
    return "ok"


@mcp.tool()
def clear_cache() -> str:
    """Clear all cached data."""
    _cache.clear()
    return "Cache cleared"


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
        ],
    )

    uvicorn.run(app, host=args.host, port=args.port)
