---
wave: 1
depends_on: []
files_modified:
  - server.py
  - tests/test_advanced.py
autonomous: true
requirements:
  - ADV-01
  - ADV-02
---

# Plan 3.1: Options and Financial Statements

**Phase:** 3 - Advanced Data
**Wave:** 1 (autonomous)
**Goal:** Implement options chain and financial statements tools

---

## Overview

This plan implements two advanced financial data tools: `get_options_chain` for retrieving calls/puts with strike prices and implied volatility, and `get_financial_statements` for retrieving income statements, balance sheets, and cash flow statements. Both tools use the existing caching and helper infrastructure from Phase 2.

**Success Criteria:**
- `get_options_chain` returns calls and puts for specified expiry
- `get_financial_statements` returns all three statement types (income/balance/cashflow)
- Both annual and quarterly frequencies supported
- Invalid expiry dates return informative error messages
- Unit tests cover all tools with 80%+ coverage

---

## Tasks

<tasks>
<task id="03-01-01">
<summary>Implement get_options_chain tool</summary>
<details>
Add the get_options_chain MCP tool to server.py:

```python
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
            return {"error": f"Expiry '{target_expiry}' not available. Options: {', '.join(expirations[:5])}"}

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
        logger.error(f"Failed to fetch options for '{symbol}": {e}", exc_info=True)
        return {"error": f"Failed to fetch options for '{symbol}': {str(e)}"}
```

Requirements: ADV-01
Location: Add after get_realtime_quote tool
</details>
<verify>
<automated>pytest tests/test_advanced.py::test_get_options_chain -v</automated>
</verify>
</task>

<task id="03-01-02">
<summary>Implement get_financial_statements tool</summary>
<details>
Add the get_financial_statements MCP tool to server.py:

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
        Returns error dict if statement not available.
    """
    try:
        ticker = _ticker(symbol.upper())

        # Get appropriate statement
        if statement_type == "income":
            df = ticker.quarterly_income_stmt if frequency == "quarterly" else ticker.income_stmt
        elif statement_type == "balance":
            df = ticker.quarterly_balance_sheet if frequency == "quarterly" else ticker.balance_sheet
        elif statement_type == "cashflow":
            df = ticker.quarterly_cashflow if frequency == "quarterly" else ticker.cashflow
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
                "periods": df.shape[1] - 1,
            }
        }
    except Exception as e:
        logger.error(f"Failed to fetch financials for '{symbol}': {e}", exc_info=True)
        return {"error": f"Failed to fetch financials for '{symbol}': {str(e)}"}
```

Requirements: ADV-02
Location: Add after get_options_chain tool
</details>
<verify>
<automated>pytest tests/test_advanced.py::test_get_financial_statements -v</automated>
</verify>
</task>

<task id="03-01-03">
<summary>Add unit tests for advanced tools</summary>
<details>
Create tests/test_advanced.py with tests for options and financials:

1. **test_get_options_chain_valid()**
   - Mock ticker.options and option_chain()
   - Verify returns calls and puts
   - Verify availableExpirations included

2. **test_get_options_chain_no_options()**
   - Mock ticker.options = None
   - Verify returns error dict

3. **test_get_options_chain_invalid_expiry()**
   - Mock ticker.options with list of dates
   - Request invalid expiry
   - Verify error includes available expirations

4. **test_get_financial_statements_income()**
   - Mock ticker.income_stmt with sample data
   - Verify returns income statement

5. **test_get_financial_statements_balance()**
   - Mock ticker.balance_sheet with sample data
   - Verify returns balance sheet

6. **test_get_financial_statements_cashflow()**
   - Mock ticker.cashflow with sample data
   - Verify returns cash flow statement

7. **test_get_financial_statements_quarterly()**
   - Mock ticker.quarterly_income_stmt
   - Verify frequency parameter works

8. **test_get_financial_statements_invalid_type()**
   - Request invalid statement_type
   - Verify returns error with valid options

9. **test_get_financial_statements_empty()**
   - Mock empty DataFrame
   - Verify returns error

Use unittest.mock.patch for all yfinance mocking.
</details>
<verify>
<automated>pytest tests/test_advanced.py -v --cov=server --cov-report=term-missing</automated>
</verify>
</task>
</tasks>

---

## Must Haves

After completing this plan:

- [ ] server.py has get_options_chain() tool with @cached(ttl=300)
- [ ] server.py has get_financial_statements() tool with @cached(ttl=3600)
- [ ] get_options_chain returns calls/puts with metadata
- [ ] get_financial_statements supports income/balance/cashflow
- [ ] get_financial_statements supports annual/quarterly
- [ ] tests/test_advanced.py has 9+ test cases
- [ ] All tests pass: pytest tests/test_advanced.py -v
- [ ] Coverage >= 80%: pytest --cov=server --cov-report=term-missing

---

## Verification

Run after plan completion:
```bash
# Lint
ruff check .
ruff format --check .

# Tests
pytest tests/test_advanced.py -v --cov=server --cov-report=term-missing

# Verify MCP tools are discoverable
python server.py --host 127.0.0.1 --port 8000 &
sleep 2
curl -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | jq '.result.tools[] | .name'
pkill -f "python server.py"
```

Expected: tools/list returns 7 tools (health_check, clear_cache, get_stock_info, get_historical_data, get_realtime_quote, get_options_chain, get_financial_statements)

---

*Plan created: 2026-03-09*
