---
wave: 2
depends_on:
  - "03-1-PLAN"
files_modified:
  - server.py
  - tests/test_search.py
autonomous: false
requirements:
  - ADV-03
  - ADV-04
  - SRC-01
  - SRC-02
---

# Plan 3.2: Dividends, Earnings, and Search

**Phase:** 3 - Advanced Data
**Wave:** 2 (depends on Wave 1)
**Goal:** Implement dividend history, earnings data, symbol search, and market overview

---

## Overview

This plan implements tools for corporate actions (dividends and earnings), search functionality, and market overview. Dividend history includes yield calculation, earnings includes upcoming dates and historical EPS, search finds tickers by company name, and market overview provides a snapshot of major indices.

**Success Criteria:**
- `get_dividend_history` returns payment history with annual yield
- `get_earnings` returns upcoming dates and historical EPS
- `search_symbol` finds tickers by company name
- `get_market_overview` returns snapshot of 8 major indices
- Unit tests cover all tools with 80%+ coverage

---

## Tasks

<tasks>
<task id="03-02-01">
<summary>Implement get_dividend_history tool</summary>
<details>
Add the get_dividend_history MCP tool to server.py:

```python
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
            "metadata": {"count": len(df)}
        }
    except Exception as e:
        logger.error(f"Failed to fetch dividends for '{symbol}': {e}", exc_info=True)
        return {"error": f"Failed to fetch dividends for '{symbol}': {str(e)}"}
```

Requirements: ADV-03
Location: Add after get_financial_statements tool
</details>
<verify>
<automated>pytest tests/test_search.py::test_get_dividend_history -v</automated>
</verify>
</task>

<task id="03-02-02">
<summary>Implement get_earnings tool</summary>
<details>
Add the get_earnings MCP tool to server.py:

```python
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
                "metadata": {"count": 0}
            }

        return {
            "symbol": symbol.upper(),
            "upcoming": next_earnings,
            "history": _df_to_records(earnings_df.reset_index()),
            "metadata": {"count": len(earnings_df)}
        }
    except Exception as e:
        logger.error(f"Failed to fetch earnings for '{symbol}': {e}", exc_info=True)
        return {"error": f"Failed to fetch earnings for '{symbol}": {str(e)}"}
```

Requirements: ADV-04
Location: Add after get_dividend_history tool
</details>
<verify>
<automated>pytest tests/test_search.py::test_get_earnings -v</automated>
</verify>
</task>

<task id="03-02-03">
<summary>Implement search_symbol tool</summary>
<details>
Add the search_symbol MCP tool to server.py:

```python
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
            "matches": [{"name": name.title(), "symbol": ticker} for name, ticker in matches.items()]
        }

    # Try direct ticker lookup
    try:
        test_ticker = yf.Ticker(query.upper())
        if test_ticker.info and test_ticker.info.get("longName"):
            return {
                "query": query,
                "matches": [{"name": test_ticker.info.get("longName"), "symbol": query.upper()}]
            }
    except Exception:
        pass

    return {
        "query": query,
        "matches": [],
        "note": "For comprehensive search, use Yahoo Finance search directly"
    }
```

Requirements: SRC-01
Location: Add after get_earnings tool
</details>
<verify>
<automated>pytest tests/test_search.py::test_search_symbol -v</automated>
</verify>
</task>

<task id="03-02-04">
<summary>Implement get_market_overview tool</summary>
<details>
Add the get_market_overview MCP tool to server.py:

```python
@mcp.tool()
@cached(ttl=60)
def get_market_overview() -> dict | str:
    """
    Get snapshot of major market indices and commodities.

    Returns:
        Dictionary with current values and changes for S&P 500, NASDAQ, DOW,
        VIX, 10Y Treasury, Gold, Crude Oil, and EUR/USD.
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
```

Requirements: SRC-02
Location: Add after search_symbol tool
</details>
<verify>
<automated>pytest tests/test_search.py::test_get_market_overview -v</automated>
</verify>
</task>

<task id="03-02-05">
<summary>Add unit tests for dividends, earnings, search</summary>
<details>
Update tests/test_search.py with comprehensive tests:

1. **test_get_dividend_history_valid()**
   - Mock ticker.dividends with sample payments
   - Verify dividends returned
   - Verify yield calculated correctly

2. **test_get_dividend_history_no_dividends()**
   - Mock empty dividends DataFrame
   - Verify returns empty array

3. **test_get_earnings_valid()**
   - Mock ticker.earnings_dates and info
   - Verify upcoming and historical data

4. **test_get_earnings_no_data()**
   - Mock empty earnings DataFrame
   - Verify returns history=[] with upcoming

5. **test_search_symbol_match()**
   - Search for "apple"
   - Verify returns AAPL

6. **test_search_symbol_no_match()**
   - Search for unknown company
   - Verify returns empty matches with note

7. **test_search_symbol_direct_lookup()**
   - Mock direct ticker lookup
   - Verify returns symbol if valid

8. **test_get_market_overview()**
   - Mock multiple index tickers
   - Verify all 8 indices returned

Use unittest.mock.patch for all yfinance mocking.
</details>
<verify>
<automated>pytest tests/test_search.py -v --cov=server --cov-report=term-missing</automated>
</verify>
</task>
</tasks>

---

## Must Haves

After completing this plan:

- [ ] server.py has get_dividend_history() tool
- [ ] server.py has get_earnings() tool
- [ ] server.py has search_symbol() tool
- [ ] server.py has get_market_overview() tool
- [ ] Dividend yield calculated correctly (annual div / current price)
- [ ] Earnings includes upcoming date and EPS estimate
- [ ] Search matches major symbols by name
- [ ] Market overview returns 8 indices
- [ ] tests/test_search.py has 8+ test cases
- [ ] All tests pass: pytest tests/test_search.py -v
- [ ] Coverage >= 80%: pytest --cov=server --cov-report=term-missing

---

## Verification

Run after plan completion:
```bash
# Lint
ruff check .
ruff format --check .

# Tests
pytest tests/test_search.py tests/test_advanced.py -v --cov=server --cov-report=term-missing

# Verify MCP tools are discoverable
python server.py --host 127.0.0.1 --port 8000 &
sleep 2
curl -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | jq '.result.tools[] | .name'
pkill -f "python server.py"
```

Expected: tools/list returns 11 tools (health_check, clear_cache, get_stock_info, get_historical_data, get_realtime_quote, get_options_chain, get_financial_statements, get_dividend_history, get_earnings, search_symbol, get_market_overview)

---

*Plan created: 2026-03-09*
