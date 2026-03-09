---
wave: 2
depends_on:
  - "02-PLAN-1"
files_modified:
  - server.py
autonomous: false
requirements:
  - DATA-01
  - DATA-02
  - DATA-03
  - ERR-01
  - ERR-02
  - ERR-03
---

# Plan 2.2: Core Market Data Tools

**Phase:** 2 - Core Tools
**Wave:** 2 (depends on Wave 1)
**Goal:** Implement three MCP tools for fetching stock data from Yahoo Finance

---

## Overview

This plan implements the three core MCP tools that provide financial data: `get_stock_info`, `get_historical_data`, and `get_realtime_quote`. Each tool uses the helper functions and caching from Plan 2.1, handles errors gracefully, and returns properly formatted JSON data.

**Success Criteria:**
- `get_stock_info` returns company profile (market cap, P/E, sector, etc.)
- `get_historical_data` returns OHLCV candles with configurable period/interval
- `get_realtime_quote` returns current price, change, volume
- Invalid symbols return informative error messages (not exceptions)
- Cached data is returned within TTL, fresh data after expiry
- Unit tests cover all tools with 80%+ coverage

---

## Tasks

<tasks>
<task id="02-02-01">
<summary>Implement get_stock_info tool</summary>
<details>
Add the get_stock_info MCP tool to server.py:

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

        return {
            "symbol": symbol.upper(),
            "companyName": info.get("longName") or info.get("shortName"),
            "marketCap": _safe(info.get("marketCap")),
            "currentPrice": _safe(info.get("currentPrice") or info.get("regularMarketPrice")),
            "previousClose": _safe(info.get("previousClose")),
            "dayChange": _safe(
                (info.get("currentPrice") or info.get("regularMarketPrice")) - 
                info.get("previousClose") 
                if (info.get("currentPrice") or info.get("regularMarketPrice")) and info.get("previousClose") 
                else None
            ),
            "dayChangePercent": _safe(
                ((info.get("currentPrice") or info.get("regularMarketPrice")) / 
                 info.get("previousClose") - 1) * 100
                if (info.get("currentPrice") or info.get("regularMarketPrice")) and info.get("previousClose")
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
```

Requirements: DATA-03, ERR-01, ERR-02
Location: Add after clear_cache tool, before if __name__ == "__main__"
</details>
<verify>
<automated>pytest tests/test_tools.py::test_get_stock_info -v</automated>
</verify>
</task>

<task id="02-02-02">
<summary>Implement get_historical_data tool</summary>
<details>
Add the get_historical_data MCP tool to server.py:

```python
@mcp.tool()
@cached(ttl=60)
def get_historical_data(
    symbol: str, 
    period: str = "1mo", 
    interval: str = "1d"
) -> dict | str:
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
            'Date' if 'Date' in str(c) or 'date' in str(c) else str(c)
            for c in df.columns
        ]

        return {
            "symbol": symbol.upper(),
            "period": period,
            "interval": interval,
            "data": _df_to_records(df),
            "metadata": {
                "count": len(df),
                "start": _iso_format(df['Date'].min()) if 'Date' in df.columns else None,
                "end": _iso_format(df['Date'].max()) if 'Date' in df.columns else None
            }
        }
    except Exception as e:
        logger.error(f"Failed to fetch historical data for '{symbol}': {e}", exc_info=True)
        return {"error": f"Failed to fetch historical data for '{symbol}': {str(e)}"}
```

Requirements: DATA-02, QUAL-03
Location: Add after get_stock_info tool
</details>
<verify>
<automated>pytest tests/test_tools.py::test_get_historical_data -v</automated>
</verify>
</task>

<task id="02-02-03">
<summary>Implement get_realtime_quote tool</summary>
<details>
Add the get_realtime_quote MCP tool to server.py:

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
            "change": _safe(
                current_price - previous_close 
                if current_price and previous_close 
                else None
            ),
            "changePercent": _safe(
                (current_price / previous_close - 1) * 100
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
            "timestamp": _iso_format(datetime.now())
        }
    except Exception as e:
        logger.error(f"Failed to fetch quote for '{symbol}': {e}", exc_info=True)
        return {"error": f"Failed to fetch quote for '{symbol}': {str(e)}"}
```

Requirements: DATA-01, ERR-03
Location: Add after get_historical_data tool
</details>
<verify>
<automated>pytest tests/test_tools.py::test_get_realtime_quote -v</automated>
</verify>
</task>

<task id="02-02-04">
<summary>Add unit tests for MCP tools</summary>
<details>
Update tests/test_tools.py with comprehensive tests:

1. **test_get_stock_info_valid()**
   - Mock yf.Ticker.info with sample company data
   - Verify return dict has all expected keys
   - Verify NaN values converted to None
   - Verify symbol is uppercased

2. **test_get_stock_info_invalid()**
   - Mock yf.Ticker.info = {}
   - Verify return is error dict
   - Verify error message includes symbol

3. **test_get_stock_info_exception()**
   - Mock yf.Ticker to raise Exception
   - Verify return is error dict
   - Verify error is logged

4. **test_get_historical_data_valid()**
   - Mock ticker.history() with sample DataFrame
   - Verify return dict has 'data' and 'metadata' keys
   - Verify metadata has count, start, end
   - Verify OHLCV columns present

5. **test_get_historical_data_empty()**
   - Mock ticker.history() with empty DataFrame
   - Verify return is error dict
   - Verify error mentions period/interval

6. **test_get_realtime_quote_valid()**
   - Mock yf.Ticker.info with quote data
   - Verify price, change, changePercent calculated correctly
   - Verify timestamp is ISO string

7. **test_get_realtime_quote_market_closed()**
   - Mock yf.Ticker.info with regularMarketPrice=None
   - Verify return is error dict

8. **test_caching_behavior()**
   - Call get_stock_info twice with same symbol
   - Verify second call returns cached data (mock count check)

9. **test_cache_expiry()**
   - Mock datetime.now to simulate time passing
   - Verify cache expires after TTL

Use unittest.mock.patch for all yfinance mocking.
</details>
<verify>
<automated>pytest tests/test_tools.py -v --cov=server --cov-report=term-missing</automated>
</verify>
</task>
</tasks>

---

## Must Haves

After completing this plan:

- [ ] server.py has get_stock_info() tool with @cached(ttl=300)
- [ ] server.py has get_historical_data() tool with @cached(ttl=60)
- [ ] server.py has get_realtime_quote() tool with @cached(ttl=30)
- [ ] All tools return error dicts for invalid symbols (not raise exceptions)
- [ ] All tools use _safe() for NaN/Inf handling
- [ ] All tools log errors with logger.error()
- [ ] tests/test_tools.py has 9+ test cases
- [ ] All tests pass: pytest tests/test_tools.py -v
- [ ] Coverage >= 80%: pytest --cov=server --cov-report=term-missing

---

## Verification

Run after plan completion:
```bash
# Lint
ruff check .
ruff format --check .

# Tests
pytest tests/test_tools.py -v --cov=server --cov-report=term-missing

# Verify MCP tools are discoverable
python server.py --host 127.0.0.1 --port 8000 &
sleep 2
curl -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | jq '.result.tools[] | .name'
pkill -f "python server.py"
```

Expected: tools/list returns 5 tools (health_check, clear_cache, get_stock_info, get_historical_data, get_realtime_quote)

---

*Plan created: 2026-03-09*
