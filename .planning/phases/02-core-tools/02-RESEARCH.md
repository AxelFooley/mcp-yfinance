# Research: Phase 2 - Core Tools

**Phase:** 2 - Core Tools
**Goal:** Implement basic financial data retrieval with caching
**Researched:** 2026-03-09

---

## Executive Summary

Phase 2 implements the three core MCP tools that provide real-time and historical stock data from Yahoo Finance. The implementation requires:

1. **Helper utilities** for data quality (NaN handling, DataFrame serialization, Timestamp formatting)
2. **In-memory caching** with configurable TTL for each data type
3. **Three MCP tools**: `get_stock_info`, `get_historical_data`, `get_realtime_quote`

**Key insight:** yfinance returns data in pandas DataFrames with various edge cases (NaN values, Timestamp objects, multi-level columns) that must be normalized before JSON serialization through MCP.

---

## Technical Approach

### 1. Helper Functions (Plan 2.1)

#### `_safe(value: Any) -> Any | None`
Converts pandas NaN/Inf values to JSON-compatible null.

```python
import math
def _safe(value):
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
    return value
```

**Rationale:** JSON doesn't support NaN/Inf. These appear frequently in yfinance data (e.g., when a stock has no P/E ratio).

#### `_df_to_records(df: pd.DataFrame) -> list[dict]`
Converts DataFrame to list of dicts, handling all edge cases.

```python
def _df_to_records(df):
    if df.empty:
        return []
    records = df.to_dict('records')
    return [{k: _safe(_iso_format(v)) for k, v in record.items()} for record in records]
```

**Edge cases:**
- Empty DataFrame → `[]`
- MultiIndex columns → flatten to single level
- Timestamp index → convert to ISO 8601 strings

#### `_series_to_dict(series: pd.Series) -> dict`
Converts pandas Series to dict, applying `_safe()` to values.

#### `_iso_format(value: Any) -> Any`
Converts pandas Timestamps to ISO 8601 strings recursively (handles nested dicts/lists).

#### `_ticker(symbol: str) -> yf.Ticker`
Creates or retrieves cached yf.Ticker object. Ticker objects maintain their own session and can be reused.

---

### 2. Caching Strategy (Plan 2.1)

**Design decision:** Use simple in-memory dict-based cache with time-based expiration.

**Rationale:**
- Single-process deployment (Docker container)
- No horizontal scaling in v1 (PERF-01 is v2)
- Simpler than Redis for MVP
- Cache is ephemeral (acceptable for data that becomes stale quickly)

**Implementation:**

```python
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable

_cache: dict[str, tuple[Any, datetime]] = {}

def _cache_key(symbol: str, data_type: str, **kwargs) -> str:
    parts = [symbol, data_type] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
    return ":".join(parts)

def _cache_get(key: str, ttl: int) -> Any | None:
    if key in _cache:
        value, expiry = _cache[key]
        if datetime.now() < expiry:
            return value
        del _cache[key]
    return None

def _cache_set(key: str, value: Any, ttl: int) -> None:
    expiry = datetime.now() + timedelta(seconds=ttl)
    _cache[key] = (value, expiry)

def cached(ttl: int):
    def decorator(fn: Callable):
        @wraps(fn)
        def wrapper(symbol: str, **kwargs):
            key = _cache_key(symbol, fn.__name__, **kwargs)
            if (cached_value := _cache_get(key, ttl)) is not None:
                return cached_value
            result = fn(symbol, **kwargs)
            _cache_set(key, result, ttl)
            return result
        return wrapper
    return decorator
```

**TTL values (from CACHE-02 through CACHE-05):**
- Real-time quotes: 30 seconds
- Historical data: 60 seconds
- Company info: 300 seconds (5 minutes)

**Cache clearing (CACHE-06):**
```python
@mcp.tool()
def clear_cache() -> str:
    """Clear all cached data."""
    _cache.clear()
    return "Cache cleared"
```

---

### 3. Core Tools Implementation (Plan 2.2)

#### Tool 1: `get_stock_info`

**Purpose:** Fetch comprehensive company profile (market cap, P/E, sector, industry, description, etc.)

**Implementation:**

```python
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

        # Extract and normalize key fields
        return {
            "symbol": symbol.upper(),
            "companyName": info.get("longName") or info.get("shortName"),
            "marketCap": _safe(info.get("marketCap")),
            "currentPrice": _safe(info.get("currentPrice") or info.get("regularMarketPrice")),
            "previousClose": _safe(info.get("previousClose")),
            "dayChange": _safe(info.get("currentPrice") - info.get("previousClose") if info.get("currentPrice") and info.get("previousClose") else None),
            "dayChangePercent": _safe(info.get("currentPrice") / info.get("previousClose") - 1 if info.get("currentPrice") and info.get("previousClose") else None),
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
        return {"error": f"Failed to fetch info for '{symbol}': {str(e)}"}
```

**Error handling (ERR-01, ERR-02):**
- Empty `.info` dict → invalid symbol
- Exception catch-all → return error dict with message
- Logging (ERR-03): use `logging` module for debug info

---

#### Tool 2: `get_historical_data`

**Purpose:** Fetch OHLCV historical data with configurable period/interval

**Parameters:**
- `symbol`: Stock ticker
- `period`: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
- `interval`: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1mo, 3mo

**Implementation:**

```python
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
            return {"error": f"No data found for symbol '{symbol}' with period={period}, interval={interval}"}

        # Reset index to make Date a column
        df = df.reset_index()

        # Normalize column names (handle multi-index from yfinance)
        df.columns = [
            'Date' if 'Date' in str(c) else c
            for c in df.columns
        ]

        return {
            "symbol": symbol.upper(),
            "period": period,
            "interval": interval,
            "data": _df_to_records(df),
            "metadata": {
                "count": len(df),
                "start": _iso_format(df['Date'].min()),
                "end": _iso_format(df['Date'].max())
            }
        }
    except Exception as e:
        return {"error": f"Failed to fetch historical data for '{symbol}': {str(e)}"}
```

**Edge cases (QUAL-03):**
- Empty DataFrame (invalid period/interval combo, delisted stock)
- MultiIndex columns (yfinance bug with certain interval/period combos)

---

#### Tool 3: `get_realtime_quote`

**Purpose:** Fetch current price, change, volume for a symbol

**Implementation:**

```python
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
            "change": _safe(current_price - previous_close if current_price and previous_close else None),
            "changePercent": _safe(
                (current_price / previous_close - 1) * 100
                if current_price and previous_close else None
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
            "timestamp": _iso_format(datetime.now())
        }
    except Exception as e:
        return {"error": f"Failed to fetch quote for '{symbol}': {str(e)}"}
```

---

## Dependencies

**Existing (from Phase 1):**
- `yfinance>=1.2.0` — already in requirements.txt
- `pandas>=2.0.0` — already in requirements.txt
- `numpy>=1.26.0` — already in requirements.txt

**New imports needed:**
```python
import yfinance as yf
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable
import math
```

**No additional pip packages required** — all dependencies are already in requirements.txt from Phase 1.

---

## Testing Approach

**Unit tests (pytest):**

1. **Test helper functions:**
   - `_safe()` with NaN, Inf, normal values
   - `_df_to_records()` with empty and non-empty DataFrames
   - `_iso_format()` with Timestamp and nested structures

2. **Test caching:**
   - Cache hit returns same object
   - Cache miss after TTL expiry
   - Different symbols have different cache entries
   - `clear_cache()` empties cache

3. **Test tools with mock yfinance:**
   - Valid symbol returns structured data
   - Invalid symbol returns error dict
   - Empty DataFrame handled gracefully

**Integration tests:**
- Start server, call tools via MCP protocol
- Verify CORS headers still work
- Test with real Yahoo Finance data (AAPL, MSFT)

**Coverage target:** 80% (already configured in pyproject.toml from Phase 1)

---

## Error Handling Strategy

**yfinance-specific errors:**
- **Invalid symbol:** `.info` returns `{}` or `None` → return `{"error": "Symbol 'X' not found"}`
- **Market closed:** `.info` has `currentPrice=None` → return quote with available data or error
- **Rate limiting:** yfinance may throttle → return error dict with "try again later" message
- **Network timeout:** Exception catch → return error dict with timeout message

**Logging (ERR-03):**
```python
import logging
logger = logging.getLogger(__name__)

# In error handlers:
logger.error(f"Failed to fetch quote for '{symbol}': {e}", exc_info=True)
```

---

## Validation Architecture

**Dimension 1: Tool Contract Compliance**
- Verify `get_stock_info` returns dict with all expected keys
- Verify `get_historical_data` returns dict with `data` and `metadata` keys
- Verify `get_realtime_quote` returns dict with price and change keys
- Verify all tools return error dict on failure (not raise exceptions)

**Dimension 2: Data Quality Gates**
- Verify no NaN/Inf values in tool output (use `_safe()` everywhere)
- Verify all Timestamps converted to ISO strings
- Verify empty DataFrames return `[]` or error message (not crash)

**Dimension 3: Cache Correctness**
- Verify cached data is returned within TTL
- Verify fresh data is fetched after TTL expiry
- Verify different cache keys for different symbols/parameters

**Dimension 4: Error Gracefulness**
- Verify invalid symbols return informative error messages
- Verify exceptions don't crash the server
- Verify error logs are written for debugging

**Dimension 5: MCP Protocol Compliance**
- Verify tools are discoverable via `tools/list`
- Verify tool descriptions are clear
- Verify tool parameter schemas are correct

**Dimension 6: Performance SLA**
- Verify real-time quote tool completes within 2 seconds (excluding cache)
- Verify historical data tool completes within 5 seconds
- Verify cache hit returns within 50ms

**Dimension 7: Resource Safety**
- Verify no memory leaks in cache implementation
- Verify Ticker objects are properly reused
- Verify cache size doesn't grow unbounded

**Dimension 8: End-to-End Integration**
- Verify MCP Inspector can connect and call tools
- Verify CORS headers still present
- Verify Docker container runs with new tools

**Verification method:**
- Manual testing with MCP Inspector
- Unit tests with mocked yfinance
- Integration tests with real data (AAPL, MSFT, INVALID)
- Cache timing tests (sleep, verify expiry)

---

## Open Questions

**Q1: Should cache be persisted across container restarts?**
**A:** No — v2 requirement (PERF-01) is for Redis-backed cache. In-memory cache is acceptable for MVP.

**Q2: How to handle yfinance rate limiting?**
**A:** yfinance doesn't have official rate limiting, but aggressive requests may be throttled. The cache (30s TTL) naturally limits request rate. No additional backoff needed for v1.

**Q3: What timezone for timestamps?**
**A:** yfinance returns timestamps in the symbol's exchange timezone. Keep as-is — let clients handle timezone conversion. ISO format preserves timezone info.

**Q4: Should we support batch requests (multiple symbols)?**
**A:** Not in v1 — COMP-01 covers multi-stock comparison, but that's Phase 4. Keep tools simple for now.

---

## Implementation Risks

| Risk | Mitigation |
|------|------------|
| yfinance API changes | Pin to `>=1.2.0` which has stable API |
| MultiIndex column bug | Normalize columns in `_df_to_records()` |
| Cache memory growth | TTL ensures entries expire; unbounded OK for v1 |
| Empty data edge cases | Explicit checks with `if df.empty` |
| JSON serialization | Recursive `_iso_format()` + `_safe()` |

---

## Decision Log

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| In-memory cache vs Redis | Simpler for v1, single-process deployment | ✓ Proceed |
| Decorator-based caching | Clean syntax, reusable TTL pattern | ✓ Proceed |
| Error dict vs exceptions | MCP protocol expects return values, not raises | ✓ Proceed |
| Ticker object caching | Reuse yfinance session, reduce overhead | ✓ Proceed |

---

## RESEARCH COMPLETE ✓

**Next:** Proceed to planning — create 02-PLAN.md with tasks organized into waves.

**Artifacts created:**
- `.planning/phases/02-core-tools/02-RESEARCH.md`

---

*Research completed: 2026-03-09*
