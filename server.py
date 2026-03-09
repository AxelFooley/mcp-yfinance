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
from collections.abc import Callable
from datetime import datetime, timedelta
from functools import wraps
from typing import Any

import pandas as pd
import uvicorn
import yfinance as yf
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount

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


@mcp.tool()
@cached(ttl=300)
def get_stock_info(symbol: str) -> dict | str:
    """
    Get comprehensive company information for a stock symbol.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "MSFT")

    Returns:
        Dictionary with company info including market cap, P/E ratio,
        sector, industry, description, website, employees, etc.
        Returns error dict if symbol is invalid.
    """
    try:
        ticker = _ticker(symbol.upper())
        info = ticker.info

        if not info or info == {}:
            return {"error": f"Symbol '{symbol}' not found"}

        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        previous_close = info.get("previousClose")

        return {
            "symbol": symbol.upper(),
            "companyName": info.get("longName") or info.get("shortName"),
            "marketCap": _safe(info.get("marketCap")),
            "currentPrice": _safe(current_price),
            "previousClose": _safe(previous_close),
            "dayChange": _safe(
                current_price - previous_close if current_price and previous_close else None
            ),
            "dayChangePercent": _safe(
                ((current_price / previous_close) - 1) * 100
                if current_price and previous_close
                else None
            ),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "description": info.get("longBusinessSummary"),
            "website": info.get("website"),
            "employees": _safe(info.get("fullTimeEmployees")),
            "peRatio": _safe(info.get("trailingPE") or info.get("forwardPE")),
            "dividendYield": _safe(info.get("dividendYield")),
            "beta": _safe(info.get("beta")),
            "eps": _safe(info.get("trailingEps") or info.get("forwardEps")),
            "52WeekHigh": _safe(info.get("fiftyTwoWeekHigh")),
            "52WeekLow": _safe(info.get("fiftyTwoWeekLow")),
        }
    except Exception as e:
        logger.error(f"Failed to fetch info for '{symbol}': {e}", exc_info=True)
        return {"error": f"Failed to fetch info for '{symbol}': {str(e)}"}


@mcp.tool()
@cached(ttl=60)
def get_historical_data(symbol: str, period: str = "1mo", interval: str = "1d") -> dict | str:
    """
    Get historical OHLCV data for a stock symbol.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "MSFT")
        period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1mo, 3mo)

    Returns:
        Dictionary with 'data' key containing list of OHLCV records,
        and 'metadata' with query parameters. Returns error dict if symbol is invalid.
    """
    try:
        ticker = _ticker(symbol.upper())
        df = ticker.history(period=period, interval=interval)

        if df.empty:
            return {
                "error": f"No data found for symbol '{symbol}' with period={period}, interval={interval}"
            }

        # Reset index to make Date a column
        df = df.reset_index()

        # Normalize column names (handle multi-index from yfinance)
        df.columns = [
            "Date" if "Date" in str(c) or "date" in str(c) else str(c) for c in df.columns
        ]

        return {
            "symbol": symbol.upper(),
            "period": period,
            "interval": interval,
            "data": _df_to_records(df),
            "metadata": {
                "count": len(df),
                "start": _iso_format(df["Date"].min()) if "Date" in df.columns else None,
                "end": _iso_format(df["Date"].max()) if "Date" in df.columns else None,
            },
        }
    except Exception as e:
        logger.error(f"Failed to fetch historical data for '{symbol}': {e}", exc_info=True)
        return {"error": f"Failed to fetch historical data for '{symbol}': {str(e)}"}


@mcp.tool()
@cached(ttl=30)
def get_realtime_quote(symbol: str) -> dict | str:
    """
    Get real-time quote for a stock symbol.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "MSFT")

    Returns:
        Dictionary with current price, day change, volume, bid/ask, etc.
        Returns error dict if symbol is invalid.
    """
    try:
        ticker = _ticker(symbol.upper())
        info = ticker.info

        if not info or info.get("regularMarketPrice") is None:
            return {"error": f"Symbol '{symbol}' not found or market closed"}

        current_price = info.get("regularMarketPrice") or info.get("currentPrice")
        previous_close = info.get("previousClose") or info.get("regularMarketPreviousClose")

        return {
            "symbol": symbol.upper(),
            "price": _safe(current_price),
            "change": _safe(
                current_price - previous_close if current_price and previous_close else None
            ),
            "changePercent": _safe(
                ((current_price / previous_close) - 1) * 100
                if current_price and previous_close
                else None
            ),
            "volume": _safe(info.get("regularMarketVolume") or info.get("volume")),
            "bid": _safe(info.get("bid")),
            "ask": _safe(info.get("ask")),
            "bidSize": _safe(info.get("bidSize")),
            "askSize": _safe(info.get("askSize")),
            "high": _safe(info.get("regularMarketDayHigh") or info.get("dayHigh")),
            "low": _safe(info.get("regularMarketDayLow") or info.get("dayLow")),
            "open": _safe(info.get("regularMarketOpen") or info.get("open")),
            "previousClose": _safe(previous_close),
            "marketCap": _safe(info.get("marketCap")),
            "timestamp": _iso_format(datetime.now()),
        }
    except Exception as e:
        logger.error(f"Failed to fetch quote for '{symbol}': {e}", exc_info=True)
        return {"error": f"Failed to fetch quote for '{symbol}': {str(e)}"}


@mcp.tool()
@cached(ttl=300)
def get_options_chain(symbol: str, expiry: str | None = None) -> dict | str:
    """
    Get options chain for a stock symbol.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "MSFT")
        expiry: Optional expiry date (YYYY-MM-DD). If None, uses nearest expiry.

    Returns:
        Dictionary with 'calls' and 'puts' keys containing lists of option contracts.
        Each contract has strike, lastPrice, bid, ask, volume, openInterest, impliedVolatility.
        Returns error dict if no options data available.
    """
    try:
        ticker = _ticker(symbol.upper())

        # Get available expirations
        expirations = ticker.options
        if not expirations:
            return {"error": f"No options data available for '{symbol}'"}

        # Use provided expiry or nearest
        target_expiry = expiry or expirations[0]

        # Validate expiry exists
        if target_expiry not in expirations:
            return {
                "error": f"Expiry '{target_expiry}' not available. Options: {', '.join(expirations[:5])}"
            }

        # Get option chain
        opt = ticker.option_chain(target_expiry)
        calls = _df_to_records(opt.calls)
        puts = _df_to_records(opt.puts)

        return {
            "symbol": symbol.upper(),
            "expiry": target_expiry,
            "calls": calls,
            "puts": puts,
            "availableExpirations": expirations,
            "metadata": {
                "callsCount": len(calls),
                "putsCount": len(puts),
            },
        }
    except Exception as e:
        logger.error(f"Failed to fetch options for '{symbol}': {e}", exc_info=True)
        return {"error": f"Failed to fetch options for '{symbol}': {str(e)}"}


@mcp.tool()
@cached(ttl=3600)  # 1 hour - financials update quarterly
def get_financial_statements(
    symbol: str,
    statement_type: str = "income",
    frequency: str = "annual",
) -> dict | str:
    """
    Get financial statements for a stock symbol.

    Args:
        symbol: Stock ticker symbol
        statement_type: 'income', 'balance', or 'cashflow'
        frequency: 'annual' or 'quarterly'

    Returns:
        Dict with financial data. Rows are line items, columns are time periods.
        Returns error dict if statement not available.
    """
    try:
        ticker = _ticker(symbol.upper())

        # Get appropriate statement
        if statement_type == "income":
            df = ticker.quarterly_income_stmt if frequency == "quarterly" else ticker.income_stmt
        elif statement_type == "balance":
            df = (
                ticker.quarterly_balance_sheet if frequency == "quarterly" else ticker.balance_sheet
            )
        elif statement_type == "cashflow":
            df = ticker.quarterly_cashflow if frequency == "quarterly" else ticker.cashflow
        else:
            return {
                "error": f"Invalid statement_type '{statement_type}'. Use: income, balance, cashflow"
            }

        if df.empty:
            return {"error": f"No {statement_type} statement available for '{symbol}'"}

        # Reset index to make line items a column
        df = df.reset_index()

        return {
            "symbol": symbol.upper(),
            "statementType": statement_type,
            "frequency": frequency,
            "data": _df_to_records(df),
            "metadata": {
                "lineItems": len(df),
                "periods": df.shape[1] - 1,
            },
        }
    except Exception as e:
        logger.error(f"Failed to fetch financials for '{symbol}': {e}", exc_info=True)
        return {"error": f"Failed to fetch financials for '{symbol}': {str(e)}"}


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
