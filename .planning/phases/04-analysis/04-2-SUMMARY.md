---
plan: 04-2
phase: 4
status: complete
date: 2026-03-10
commits:
  - hash: e881d45
    message: feat(04-02): implement multi-stock comparison tool
---

# Plan 04-2: Multi-Stock Comparison - Summary

**Status:** Complete
**Date:** 2026-03-10

---

## What Was Built

Implemented a side-by-side stock comparison tool that enables users to compare multiple stocks with performance metrics. The tool calculates key financial metrics and presents a sorted comparison table.

**Key Features:**
1. **compare_stocks MCP tool** — Accepts comma-separated symbols (2-10)
2. **Period returns** — Percentage change over the specified period
3. **Volatility** — Standard deviation of daily returns (annualized)
4. **Sharpe ratio** — Risk-adjusted return measure (simplified formula)
5. **Max drawdown** — Largest peak-to-trough decline
6. **Sorted output** — Results sorted by performance (best first)
7. **Summary statistics** — Best/worst performers, average return, highest volatility
8. **Error handling** — Invalid symbols don't block valid ones

---

## Implementation Details

### Files Modified

| File | Changes | Lines Added |
|------|---------|-------------|
| server.py | Added compare_stocks tool | ~110 |
| tests/test_technical.py | Added 8 comparison tests | ~340 |

### Tool: compare_stocks

**Function signature:**
```python
@mcp.tool()
def compare_stocks(symbols: str, period: str = "3mo", interval: str = "1d") -> dict | str
```

**Input validation:**
- Minimum 2 symbols required
- Maximum 10 symbols allowed
- Symbols are uppercased and whitespace-trimmed

**Metrics calculated per symbol:**
| Metric | Description |
|--------|-------------|
| currentPrice | Most recent closing price |
| periodReturn | % change from start to end of period |
| volatility | Std dev of daily returns * 100 (proxy for annualized) |
| sharpeRatio | (avg_daily_return * 252) / (volatility/100 * sqrt(252)) |
| maxDrawdown | Minimum peak-to-trough decline % |
| dataPoints | Number of price data points used |

**Output structure:**
```json
{
  "period": "3mo",
  "interval": "1d",
  "comparisons": [
    {
      "symbol": "AAPL",
      "currentPrice": 178.52,
      "periodReturn": 12.4,
      "volatility": 15.2,
      "sharpeRatio": 1.8,
      "maxDrawdown": -8.3,
      "dataPoints": 60
    }
  ],
  "summary": {
    "bestPerforming": "AAPL",
    "worstPerforming": "GOOGL",
    "averageReturn": 8.7,
    "highestVolatility": "MSFT"
  },
  "metadata": {"count": 3}
}
```

---

## Testing

### Test Coverage

All 8 comparison tests pass:

| Test | Description |
|------|-------------|
| test_compare_stocks_valid | Side-by-side comparison with sorting |
| test_compare_stocks_too_many | Error for 11+ symbols |
| test_compare_stocks_too_few | Error for single symbol |
| test_compare_stocks_invalid_symbol | Mixed valid/invalid symbols |
| test_compare_stocks_volatility_calculation | Volatility distinguishes stocks |
| test_compare_stocks_sharpe_ratio | Sharpe rewards high-return low-volatility |
| test_compare_stocks_max_drawdown | Max drawdown calculation |
| test_compare_stocks_summary | Summary statistics accuracy |

**Total tests in file:** 21 (13 technical + 8 comparison)

### Coverage

- **Overall file:** ~35% (includes all functions from previous phases)
- **New compare_stocks function:** >85% (exception paths only uncovered, hard to test without network failures)
- **All happy paths:** Covered

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_compare_stocks_max_drawdown**
- **Found during:** Task 2 verification
- **Issue:** Test passed only 1 symbol "DROP" but compare_stocks requires minimum 2 symbols
- **Fix:** Added second stock "STABLE" to meet minimum requirement
- **Files modified:** tests/test_technical.py
- **Commit:** e881d45

---

## Verification

Run after plan completion:

```bash
# Lint (✅ passes)
ruff check .
ruff format --check .

# Tests (✅ 21/21 passing)
PYTHONPATH=. python3 -m pytest tests/test_technical.py -v

# MCP tools discoverable
python server.py --host 127.0.0.1 --port 8000 &
sleep 2
curl -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | jq '.result.tools[] | .name'
pkill -f "python server.py"
```

**Expected tools (13 total):** health_check, clear_cache, get_stock_info, get_historical_data, get_realtime_quote, get_options_chain, get_financial_statements, get_dividend_history, get_earnings, search_symbol, get_market_overview, get_technical_analysis, compare_stocks

---

## Must Haves — All Complete

- [x] server.py has compare_stocks() tool
- [x] Accepts comma-separated symbols (2-10 symbols)
- [x] Calculates period returns (% change)
- [x] Calculates volatility (std dev of daily returns)
- [x] Calculates Sharpe ratio (risk-adjusted return)
- [x] Calculates max drawdown
- [x] Returns sorted comparison (best performer first)
- [x] Handles invalid symbols gracefully
- [x] tests/test_technical.py has comparison tests (8 additional tests)
- [x] All tests pass: pytest tests/test_technical.py -v
- [x] Linting passes: ruff check && ruff format --check

---

## Notable Decisions

1. **Symbol range limit (2-10)** — Prevents API abuse while ensuring meaningful comparisons
2. **Sort by period return** — Most intuitive comparison metric for users
3. **Graceful error handling** — Invalid symbols don't fail entire request
4. **Simplified Sharpe ratio** — Uses 0% risk-free rate for simplicity

---

*Summary created: 2026-03-10*
