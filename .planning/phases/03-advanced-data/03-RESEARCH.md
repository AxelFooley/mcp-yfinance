# Research: Phase 3 - Advanced Data

**Phase:** 3 - Advanced Data
**Goal:** Add advanced market data and search functionality
**Researched:** 2026-03-09

---

## Executive Summary

Phase 3 implements advanced financial data tools and search functionality. The implementation requires:

1. **Options data**: Calls, puts, strike prices, expiry dates, implied volatility
2. **Financial statements**: Income statement, balance sheet, cash flow (annual/quarterly)
3. **Corporate actions**: Dividend history with yield, earnings dates and EPS
4. **Search & discovery**: Symbol lookup by company name, market overview of major indices

**Key insight:** yfinance provides all this data through existing Ticker objects. The main challenge is formatting complex nested structures (options have multi-level indexing) and handling missing data gracefully.

---

## Technical Approach

### 1. Options Chain (Plan 3.1)

**Data source:** `ticker.options` property and `ticker.option_chain()` method

**Structure:**
```python
# ticker.options returns list of expiry dates
expirations = ticker.options

# ticker.option_chain(date) returns a tuple with calls and puts
calls, puts = ticker.option_chain('2024-03-15')

# Both are DataFrames with columns:
# - lastTradeDate, strike, lastPrice, bid, ask, change, %change, volume
# - openInterest, impliedVolatility, itm, contractSize
```

**Implementation:**
```python
@mcp.tool()
@cached(ttl=300)  # Options don't change rapidly
def get_options_chain(symbol: str, expiry: str | None = None) -> dict | str:
    """
    Get options chain for a stock symbol.

    Args:
        symbol: Stock ticker symbol
        expiry: Optional expiry date (YYYY-MM-DD). If None, uses nearest expiry.

    Returns:
        Dict with 'calls' and 'puts' keys containing lists of option contracts.
        Each contract has strike, lastPrice, bid, ask, volume, openInterest, impliedVolatility.
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
            return {"error": f"Expiry '{target_expiry}' not available. Options: {expirations[:5]}"}

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
            }
        }
    except Exception as e:
        logger.error(f"Failed to fetch options for '{symbol}': {e}", exc_info=True)
        return {"error": f"Failed to fetch options for '{symbol}': {str(e)}"}
```

**Edge cases:**
- No options data available (index funds, some ETFs)
- Invalid expiry date
- MultiIndex columns in options DataFrame

---

### 2. Financial Statements (Plan 3.1)

**Data source:** `ticker.income_stmt`, `ticker.balance_sheet`, `ticker.cashflow`

**Structure:**
```python
# Annual statements (default)
income = ticker.income_stmt  # DataFrame with columns as years, rows as line items
balance = ticker.balance_sheet
cashflow = ticker.cashflow

# Quarterly statements
income_q = ticker.income_stmt
balance_q = ticker.quarterly_balance_sheet
cashflow_q = ticker.quarterly_cashflow
```

**Implementation:**
```python
@mcp.tool()
@cached(ttl=3600)  # 1 hour - financials update quarterly
def get_financial_statements(
    symbol: str,
    statement_type: str = "income",
    frequency: str = "annual"
) -> dict | str:
    """
    Get financial statements for a stock symbol.

    Args:
        symbol: Stock ticker symbol
        statement_type: 'income', 'balance', or 'cashflow'
        frequency: 'annual' or 'quarterly'

    Returns:
        Dict with financial data. Rows are line items, columns are time periods.
        Values are properly formatted with NaN handling.
    """
    try:
        ticker = _ticker(symbol.upper())

        # Get appropriate statement
        if statement_type == "income":
            if frequency == "quarterly":
                df = ticker.quarterly_income_stmt
            else:
                df = ticker.income_stmt
        elif statement_type == "balance":
            if frequency == "quarterly":
                df = ticker.quarterly_balance_sheet
            else:
                df = ticker.balance_sheet
        elif statement_type == "cashflow":
            if frequency == "quarterly":
                df = ticker.quarterly_cashflow
            else:
                df = ticker.cashflow
        else:
            return {"error": f"Invalid statement_type '{statement_type}'. Use: income, balance, cashflow"}

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
                "periods": df.shape[1] - 1,  # -1 for the index column
            }
        }
    except Exception as e:
        logger.error(f"Failed to fetch financials for '{symbol}': {e}", exc_info=True)
        return {"error": f"Failed to fetch financials for '{symbol}': {str(e)}"}
```

**Edge cases:**
- Empty DataFrames (no data available)
- MultiIndex columns
- Companies with different reporting periods

---

### 3. Dividends and Earnings (Plan 3.2)

**Dividends source:** `ticker.dividends`

**Earnings source:** `ticker.earnings_dates`, `ticker.info` for upcoming dates

**Implementation:**
```python
@mcp.tool()
@cached(ttl=300)
def get_dividend_history(symbol: str) -> dict | str:
    """Get dividend payment history."""
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


@mcp.tool()
@cached(ttl=300)
def get_earnings(symbol: str) -> dict | str:
    """Get earnings dates and EPS data."""
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
        return {"error": f"Failed to fetch earnings for '{symbol}': {str(e)}"}
```

---

### 4. Search and Market Overview (Plan 3.2)

**Search source:** No direct yfinance search API, but can use ticker symbols or external APIs

**Market overview source:** Ticker objects for major indices

**Implementation:**
```python
@mcp.tool()
def search_symbol(query: str) -> dict | str:
    """
    Search for stock ticker symbols by company name.

    Note: yfinance doesn't provide a search API. This returns common symbols
    and suggests using external services for comprehensive search.

    For now, returns major tickers if query matches, else suggests alternatives.
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
        # ... add more
    }

    query_lower = query.lower()
    matches = {name: ticker for name, ticker in major_tickers.items() if query_lower in name}

    if matches:
        return {
            "query": query,
            "matches": [{"name": name, "symbol": ticker} for name, ticker in matches.items()]
        }

    # Try direct ticker lookup
    try:
        test_ticker = yf.Ticker(query.upper())
        if test_ticker.info:
            return {
                "query": query,
                "matches": [{"name": test_ticker.info.get("longName") or test_ticker.info.get("shortName"), "symbol": query.upper()}]
            }
    except:
        pass

    return {
        "query": query,
        "matches": [],
        "note": "For comprehensive search, consider using Yahoo Finance search directly"
    }


@mcp.tool()
@cached(ttl=60)
def get_market_overview() -> dict | str:
    """Get snapshot of major market indices."""
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
            ticker = yf.Ticker(symbol)
            info = ticker.info
            result[name] = {
                "symbol": symbol,
                "value": _safe(info.get("regularMarketPrice") or info.get("currentPrice")),
                "change": _safe(
                    (info.get("regularMarketPrice") or info.get("currentPrice")) -
                    (info.get("previousClose") or 0)
                    if info.get("regularMarketPrice") or info.get("currentPrice") else None
                ),
            }
        except Exception:
            result[name] = {"error": "Data not available"}

    return {"indices": result, "timestamp": _iso_format(datetime.now())}
```

---

## Dependencies

**No additional pip packages required** — all functionality uses existing yfinance API.

---

## Testing Approach

**Unit tests (pytest):**

1. **Test get_options_chain:**
   - Mock ticker.options and option_chain()
   - Verify calls and puts are returned
   - Verify expiry validation
   - Test with no options available

2. **Test get_financial_statements:**
   - Mock income_stmt, balance_sheet, cashflow
   - Test annual vs quarterly
   - Test invalid statement_type
   - Handle empty DataFrames

3. **Test get_dividend_history:**
   - Mock dividends Series
   - Verify yield calculation
   - Test with no dividends

4. **Test get_earnings:**
   - Mock earnings_dates and info
   - Verify upcoming and historical data

5. **Test search_symbol:**
   - Test known symbols
   - Test unknown symbols

6. **Test get_market_overview:**
   - Mock multiple index tickers
   - Verify all indices returned

**Coverage target:** 80%

---

## Error Handling Strategy

**Options-specific errors:**
- No options data → return error with message
- Invalid expiry → list available expirations

**Financial statements:**
- Empty DataFrame → return error
- Invalid statement_type → return error with valid options

**Dividends/Earnings:**
- No data → return empty arrays, not errors
- Calculation errors (division by zero) → use _safe()

---

## Validation Architecture

**Dimension 1: Tool Contract Compliance**
- Verify get_options_chain returns dict with calls/puts
- Verify get_financial_statements returns all three statement types
- Verify get_dividend_history calculates yield correctly
- Verify get_earnings includes upcoming dates

**Dimension 2: Data Quality Gates**
- Verify all NaN values handled via _safe()
- Verify Timestamps converted via _iso_format()
- Verify DataFrames converted via _df_to_records()

**Dimension 3: Cache Correctness**
- Verify options cached for 300s
- Verify financials cached for 3600s (1 hour)
- Verify dividends cached for 300s
- Verify market overview cached for 60s

**Dimension 4: Error Gracefulness**
- Verify invalid symbols return error dicts
- Verify invalid statement_type returns helpful message
- Verify exceptions don't crash server

**Dimension 5: MCP Protocol Compliance**
- Verify all tools discoverable
- Verify tool descriptions clear
- Verify parameter schemas correct

**Dimension 6: Performance SLA**
- Options queries < 5 seconds
- Financial statements < 3 seconds
- Market overview < 10 seconds (8 tickers)

**Dimension 7: Resource Safety**
- Verify no memory leaks in large DataFrames
- Verify cache size bounded

**Dimension 8: End-to-End Integration**
- Verify MCP Inspector connects
- Verify tools work with real data (AAPL options, etc.)

---

## Open Questions

**Q1: Search functionality**
**A:** yfinance doesn't provide search API. Current implementation matches major symbols by name. For v1, this is acceptable. Users can search on Yahoo Finance directly and paste symbols.

**Q2: Options data limits**
**A:** yfinance returns all strikes for an expiry. Could be hundreds of contracts. This is fine for v1 - users can filter client-side.

**Q3: Financial statement period limits**
**A:** yfinance returns ~4 years of annual data, ~5 quarters of quarterly. No way to get more historical data. Acceptable for v1.

---

## Implementation Risks

| Risk | Mitigation |
|------|------------|
| Options data not available for some symbols | Return informative error message |
| Financial statements have different columns | Normalize column names |
| Search API limitation | Document limitation, suggest Yahoo Finance search |
| Large DataFrames for options | Use _df_to_records which handles any size |
| Dividend yield calculation (no current price) | Use _safe() to handle division by zero |

---

## Decision Log

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 1hr cache for financials | Updates quarterly, can cache longer | ✓ Proceed |
| Nearest expiry for options | Most users want current options | ✓ Proceed |
| All three financial statements | Users need all three types | ✓ Proceed |
| Major indices for overview | Most commonly requested data | ✓ Proceed |
| Limited search functionality | yfinance limitation, acceptable for v1 | ✓ Proceed |

---

## RESEARCH COMPLETE ✓

**Next:** Proceed to planning — create 03-PLAN.md files.

**Artifacts created:**
- `.planning/phases/03-advanced-data/03-RESEARCH.md`

---

*Research completed: 2026-03-09*
