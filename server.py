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


@mcp.tool()
@cached(ttl=300)
def get_dividend_history(symbol: str) -> dict | str:
    """
    Get dividend payment history for a stock symbol.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Dictionary with dividend payments and calculated annual yield.
        Returns empty array if no dividends.
    """
    try:
        ticker = _ticker(symbol.upper())
        divs = ticker.dividends

        if divs.empty:
            return {"symbol": symbol.upper(), "dividends": [], "metadata": {"count": 0}}

        df = divs.reset_index()
        df.columns = ["Date", "Amount"]

        # Calculate yield (need current price)
        info = ticker.info
        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        if df.empty:
            annual_div = 0
        else:
            annual_div = df.tail(4)["Amount"].sum()  # Last 4 quarters

        return {
            "symbol": symbol.upper(),
            "currentPrice": _safe(current_price),
            "annualYield": _safe((annual_div / current_price * 100) if current_price else None),
            "dividends": _df_to_records(df),
            "metadata": {"count": len(df)},
        }
    except Exception as e:
        logger.error(f"Failed to fetch dividends for '{symbol}': {e}", exc_info=True)
        return {"error": f"Failed to fetch dividends for '{symbol}': {str(e)}"}


@mcp.tool()
@cached(ttl=300)
def get_earnings(symbol: str) -> dict | str:
    """
    Get earnings dates and EPS data for a stock symbol.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Dictionary with upcoming earnings date and historical EPS data.
    """
    try:
        ticker = _ticker(symbol.upper())
        info = ticker.info

        # Upcoming earnings
        next_earnings = {
            "date": _iso_format(info.get("nextEarningsDate")),
            "estimate": _safe(info.get("epsForward")),
            "previous": _safe(info.get("epsTrailingTwelveMonths")),
        }

        # Historical earnings (from earnings_dates DataFrame)
        earnings_df = ticker.earnings_dates
        if earnings_df.empty:
            return {
                "symbol": symbol.upper(),
                "upcoming": next_earnings,
                "history": [],
                "metadata": {"count": 0},
            }

        return {
            "symbol": symbol.upper(),
            "upcoming": next_earnings,
            "history": _df_to_records(earnings_df.reset_index()),
            "metadata": {"count": len(earnings_df)},
        }
    except Exception as e:
        logger.error(f"Failed to fetch earnings for '{symbol}': {e}", exc_info=True)
        return {"error": f"Failed to fetch earnings for '{symbol}': {str(e)}"}


@mcp.tool()
def search_symbol(query: str) -> dict | str:
    """
    Search for stock ticker symbols by company name.

    Note: yfinance doesn't provide a search API. This matches common symbols
    and suggests using external services for comprehensive search.

    Args:
        query: Company name or partial name

    Returns:
        Dictionary with matching symbols and company names.
    """
    # Common major tickers
    major_tickers = {
        "apple": "AAPL",
        "microsoft": "MSFT",
        "google": "GOOGL",
        "alphabet": "GOOGL",
        "amazon": "AMZN",
        "tesla": "TSLA",
        "meta": "META",
        "facebook": "META",
        "nvidia": "NVDA",
        "netflix": "NFLX",
        "johnson": "JNJ",
        "jpmorgan": "JPM",
        "bank": "BAC",
        "walmart": "WMT",
        "disney": "DIS",
        "pfizer": "PFE",
        "coca": "KO",
        "ibm": "IBM",
        "intel": "INTC",
        "amd": "AMD",
    }

    query_lower = query.lower()
    matches = {name: ticker for name, ticker in major_tickers.items() if query_lower in name}

    if matches:
        return {
            "query": query,
            "matches": [
                {"name": name.title(), "symbol": ticker} for name, ticker in matches.items()
            ],
        }

    # Try direct ticker lookup
    try:
        test_ticker = yf.Ticker(query.upper())
        if test_ticker.info and test_ticker.info.get("longName"):
            return {
                "query": query,
                "matches": [{"name": test_ticker.info.get("longName"), "symbol": query.upper()}],
            }
    except Exception:
        pass

    return {
        "query": query,
        "matches": [],
        "note": "For comprehensive search, use Yahoo Finance search directly",
    }


@mcp.tool()
def get_market_overview() -> dict | str:
    """
    Get snapshot of major market indices and commodities.

    Returns:
        Dictionary with current values and changes for S&P 500, NASDAQ, DOW,
        VIX, 10Y Treasury, Gold, Crude Oil, EUR/USD, and BTC/USD.
    """
    indices = {
        "S&P 500": "^GSPC",
        "NASDAQ": "^IXIC",
        "DOW": "^DJI",
        "VIX": "^VIX",
        "10Y Treasury": "^TNX",
        "Gold": "GC=F",
        "Crude Oil": "CL=F",
        "EUR/USD": "EURUSD=X",
        "BTC/USD": "BTC-USD",
    }

    result = {}
    for name, symbol in indices.items():
        try:
            idx_ticker = yf.Ticker(symbol)
            idx_info = idx_ticker.info
            current = idx_info.get("regularMarketPrice") or idx_info.get("currentPrice")
            previous = idx_info.get("previousClose") or 0
            result[name] = {
                "symbol": symbol,
                "value": _safe(current),
                "change": _safe(current - previous if current else None),
            }
        except Exception:
            result[name] = {"error": "Data not available"}

    return {"indices": result, "timestamp": _iso_format(datetime.now())}


# ──────────────────────────────────────────────
# Technical Indicator Helpers
# ──────────────────────────────────────────────


def _compute_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index (RSI)."""
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def _compute_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """Calculate MACD (Moving Average Convergence Divergence)."""
    exp1 = df["Close"].ewm(span=fast, adjust=False).mean()
    exp2 = df["Close"].ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    histogram = macd - signal_line

    # Crossover detection
    crossover = "none"
    if len(macd) >= 2:
        if macd.iloc[-2] <= signal_line.iloc[-2] and macd.iloc[-1] > signal_line.iloc[-1]:
            crossover = "bullish"
        elif macd.iloc[-2] >= signal_line.iloc[-2] and macd.iloc[-1] < signal_line.iloc[-1]:
            crossover = "bearish"

    return {
        "macd": macd,
        "signal": signal_line,
        "histogram": histogram,
        "crossover": crossover,
    }


def _compute_bollinger(df: pd.DataFrame, period: int = 20, std_dev: float = 2) -> dict:
    """Calculate Bollinger Bands."""
    sma = df["Close"].rolling(window=period).mean()
    std = df["Close"].rolling(window=period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)

    # Bandwidth and percent-B
    bandwidth = (upper - lower) / sma * 100
    percent_b = (df["Close"] - lower) / (upper - lower)

    return {
        "upper": upper,
        "middle": sma,
        "lower": lower,
        "bandwidth": bandwidth,
        "percent_b": percent_b,
    }


def _compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range (ATR)."""
    high = df["High"]
    low = df["Low"]
    close_prev = df["Close"].shift(1)

    tr1 = high - low
    tr2 = (high - close_prev).abs()
    tr3 = (low - close_prev).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr


def _compute_support_resistance(df: pd.DataFrame, lookback: int = 20) -> dict:
    """Calculate support and resistance levels from recent price action."""
    recent = df.tail(lookback)
    support = recent["Low"].min()
    resistance = recent["High"].max()

    return {
        "support": _safe(support),
        "resistance": _safe(resistance),
        "range": _safe(resistance - support),
    }


@mcp.tool()
@cached(ttl=300)
def get_technical_analysis(symbol: str, period: str = "3mo", interval: str = "1d") -> dict | str:
    """
    Get technical analysis indicators for a stock symbol.

    Args:
        symbol: Stock ticker symbol
        period: Time period for historical data (default: "3mo")
        interval: Data interval (default: "1d")

    Returns:
        Dictionary with RSI, MACD, Bollinger Bands, ATR, moving averages,
        and support/resistance levels.
    """
    try:
        ticker = _ticker(symbol.upper())
        df = ticker.history(period=period, interval=interval)

        if df.empty or len(df) < 50:
            return {"error": f"Insufficient data for technical analysis on '{symbol}'"}

        # Normalize column names (handle multi-index from yfinance)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [str(c[1]) if len(c) > 1 else str(c[0]) for c in df.columns.values]
        else:
            df.columns = [str(c).split()[-1] if " " in str(c) else str(c) for c in df.columns]

        # Calculate all indicators
        rsi = _compute_rsi(df)
        macd = _compute_macd(df)
        bollinger = _compute_bollinger(df)
        atr = _compute_atr(df)
        sr = _compute_support_resistance(df)

        # Moving averages
        sma_20 = df["Close"].rolling(window=20).mean().iloc[-1]
        sma_50 = df["Close"].rolling(window=50).mean().iloc[-1]
        sma_200 = df["Close"].rolling(window=200).mean().iloc[-1]
        ema_12 = df["Close"].ewm(span=12).mean().iloc[-1]
        ema_26 = df["Close"].ewm(span=26).mean().iloc[-1]

        current_price = df["Close"].iloc[-1]
        current_rsi = rsi.iloc[-1]

        # RSI signal
        rsi_signal = "neutral"
        if current_rsi > 70:
            rsi_signal = "overbought"
        elif current_rsi < 30:
            rsi_signal = "oversold"

        return {
            "symbol": symbol.upper(),
            "currentPrice": _safe(current_price),
            "rsi": {
                "value": _safe(current_rsi),
                "signal": rsi_signal,
                "overbought": current_rsi > 70,
                "oversold": current_rsi < 30,
            },
            "macd": {
                "value": _safe(macd["macd"].iloc[-1]),
                "signal": _safe(macd["signal"].iloc[-1]),
                "histogram": _safe(macd["histogram"].iloc[-1]),
                "crossover": macd["crossover"],
            },
            "bollinger": {
                "upper": _safe(bollinger["upper"].iloc[-1]),
                "middle": _safe(bollinger["middle"].iloc[-1]),
                "lower": _safe(bollinger["lower"].iloc[-1]),
                "bandwidth": _safe(bollinger["bandwidth"].iloc[-1]),
                "percent_b": _safe(bollinger["percent_b"].iloc[-1]),
            },
            "atr": _safe(atr.iloc[-1]),
            "supportResistance": sr,
            "movingAverages": {
                "sma20": _safe(sma_20),
                "sma50": _safe(sma_50),
                "sma200": _safe(sma_200),
                "ema12": _safe(ema_12),
                "ema26": _safe(ema_26),
            },
            "trend": {
                "priceVsSma20": current_price > sma_20 if pd.notna(sma_20) else None,
                "sma20VsSma50": sma_20 > sma_50 if pd.notna(sma_20) and pd.notna(sma_50) else None,
            },
        }
    except Exception as e:
        logger.error(f"Failed to compute technical analysis for '{symbol}': {e}", exc_info=True)
        return {"error": f"Failed to compute technical analysis for '{symbol}': {str(e)}"}


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
