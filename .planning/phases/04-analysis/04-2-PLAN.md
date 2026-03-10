---
wave: 2
depends_on:
  - "04-1-PLAN"
files_modified:
  - server.py
  - tests/test_technical.py
autonomous: false
requirements:
  - COMP-01
---

# Plan 4.2: Multi-Stock Comparison

**Phase:** 4 - Analysis
**Wave:** 2 (depends on Wave 1)
**Goal:** Implement side-by-side stock comparison with performance metrics

---

## Overview

This plan implements a comparison tool that allows users to compare multiple stocks side-by-side. The tool calculates performance metrics (period returns, volatility, Sharpe ratio) and presents a sorted comparison table. This enables users to quickly assess relative performance between stocks.

**Success Criteria:**
- `compare_stocks` accepts comma-separated symbols
- Returns side-by-side comparison with period returns
- Calculates volatility (standard deviation of returns)
- Calculates Sharpe ratio (risk-adjusted return)
- Returns sorted comparison table
- Unit tests cover all comparison scenarios

---

## Tasks

<tasks>
<task id="04-02-01">
<summary>Implement compare_stocks tool</summary>
<details>
Add the compare_stocks MCP tool to server.py:

```python
@mcp.tool()
@cached(ttl=300)
def compare_stocks(symbols: str, period: str = "3mo", interval: str = "1d") -> dict | str:
    """
    Compare multiple stocks side-by-side with performance metrics.
    
    Args:
        symbols: Comma-separated stock symbols (e.g., "AAPL,MSFT,GOOGL")
        period: Time period for historical data (default: "3mo")
        interval: Data interval (default: "1d")
    
    Returns:
        Dictionary with comparison metrics for each symbol, sorted by performance.
    """
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        
        if len(symbol_list) > 10:
            return {"error": "Maximum 10 symbols allowed for comparison"}
        
        if len(symbol_list) < 2:
            return {"error": "At least 2 symbols required for comparison"}
        
        comparisons = []
        
        for symbol in symbol_list:
            try:
                ticker = _ticker(symbol)
                df = ticker.history(period=period, interval=interval)
                
                if df.empty or len(df) < 10:
                    comparisons.append({
                        "symbol": symbol,
                        "error": "Insufficient data",
                    })
                    continue
                
                # Calculate metrics
                current_price = df["Close"].iloc[-1]
                start_price = df["Close"].iloc[0]
                period_return = ((current_price / start_price) - 1) * 100
                
                # Daily returns for volatility
                daily_returns = df["Close"].pct_change().dropna()
                volatility = daily_returns.std() * 100  # Annualized roughly
                
                # Sharpe ratio (simplified, assuming 2% risk-free rate)
                avg_daily_return = daily_returns.mean()
                sharpe_ratio = (avg_daily_return * 252) / (volatility / 100 * (252 ** 0.5)) if volatility > 0 else 0
                
                # Max drawdown
                rolling_max = df["Close"].expanding().max()
                drawdown = (df["Close"] - rolling_max) / rolling_max
                max_drawdown = drawdown.min() * 100
                
                comparisons.append({
                    "symbol": symbol,
                    "currentPrice": _safe(current_price),
                    "periodReturn": _safe(period_return),
                    "volatility": _safe(volatility),
                    "sharpeRatio": _safe(sharpe_ratio),
                    "maxDrawdown": _safe(max_drawdown),
                    "dataPoints": len(df),
                })
                
            except Exception as e:
                logger.error(f"Failed to compare '{symbol}': {e}")
                comparisons.append({
                    "symbol": symbol,
                    "error": str(e),
                })
        
        # Sort by period return (descending)
        comparisons_with_return = [c for c in comparisons if "periodReturn" in c]
        comparisons_with_error = [c for c in comparisons if "error" in c]
        
        comparisons_with_return.sort(key=lambda x: x["periodReturn"], reverse=True)
        
        sorted_comparisons = comparisons_with_return + comparisons_with_error
        
        # Calculate summary stats
        valid_returns = [c["periodReturn"] for c in comparisons_with_return if c["periodReturn"] is not None]
        
        summary = {}
        if valid_returns:
            summary = {
                "bestPerforming": comparisons_with_return[0]["symbol"],
                "worstPerforming": comparisons_with_return[-1]["symbol"],
                "averageReturn": _safe(sum(valid_returns) / len(valid_returns)),
                "highestVolatility": max(comparisons_with_return, key=lambda x: x["volatility"] or 0)["symbol"],
            }
        
        return {
            "period": period,
            "interval": interval,
            "comparisons": sorted_comparisons,
            "summary": summary,
            "metadata": {"count": len(symbol_list)},
        }
    except Exception as e:
        logger.error(f"Failed to compare stocks: {e}", exc_info=True)
        return {"error": f"Failed to compare stocks: {str(e)}"}
```

Requirements: COMP-01
Location: Add after get_technical_analysis tool
</details>
<verify>
<automated>pytest tests/test_technical.py::test_compare_stocks -v</automated>
</verify>
</task>

<task id="04-02-02">
<summary>Add unit tests for stock comparison</summary>
<details>
Update tests/test_technical.py with comparison tests:

1. **test_compare_stocks_valid()**
   - Mock 3 tickers with different performance
   - Verify returns sorted by performance
   - Verify all metrics calculated

2. **test_compare_stocks_too_many()**
   - Request 11 symbols
   - Verify returns error

3. **test_compare_stocks_too_few()**
   - Request 1 symbol
   - Verify returns error

4. **test_compare_stocks_invalid_symbol()**
   - Mix valid and invalid symbols
   - Verify error handling for invalid symbol
   - Verify valid symbols still compared

5. **test_compare_stocks_volatility_calculation()**
   - Mock volatile stock
   - Verify higher volatility than stable stock

6. **test_compare_stocks_sharpe_ratio()**
   - Mock high-return low-volatility stock
   - Verify higher Sharpe ratio

7. **test_compare_stocks_max_drawdown()**
   - Mock stock with significant drop
   - Verify max drawdown calculated

8. **test_compare_stocks_summary()**
   - Mock 3 stocks
   - Verify summary includes best/worst performers
   - Verify average return calculated

Use unittest.mock.patch for all yfinance mocking.
</details>
<verify>
<automated>pytest tests/test_technical.py -v --cov=server --cov-report=term-missing</automated>
</verify>
</task>
</tasks>

---

## Must Haves

After completing this plan:

- [ ] server.py has compare_stocks() tool with @cached(ttl=300)
- [ ] Accepts comma-separated symbols (2-10 symbols)
- [ ] Calculates period returns (% change)
- [ ] Calculates volatility (std dev of daily returns)
- [ ] Calculates Sharpe ratio (risk-adjusted return)
- [ ] Calculates max drawdown
- [ ] Returns sorted comparison (best performer first)
- [ ] Handles invalid symbols gracefully
- [ ] tests/test_technical.py has comparison tests (8+ additional tests)
- [ ] All tests pass: pytest tests/test_technical.py -v
- [ ] Coverage >= 80%: pytest --cov=server --cov-report=term-missing

---

## Verification

Run after plan completion:
```bash
# Lint
ruff check .
ruff format --check .

# Tests
pytest tests/test_technical.py tests/test_advanced.py tests/test_search.py tests/test_tools.py -v --cov=server --cov-report=term-missing

# Verify MCP tools are discoverable
python server.py --host 127.0.0.1 --port 8000 &
sleep 2
curl -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | jq '.result.tools[] | .name'
pkill -f "python server.py"
```

Expected: tools/list returns 13 tools (all previous + compare_stocks)

---

*Plan created: 2026-03-10*
