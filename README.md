# Finance MCP Server

A **streamable HTTP** MCP server that exposes real-time stock market data,
technical analysis, financials, options, news, and more — powered by
[yfinance](https://github.com/ranaroussi/yfinance) and
[FastMCP](https://github.com/jlowin/fastmcp).

---

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run (streamable-http on port 8000)
python server.py

# Custom host / port
python server.py --host 127.0.0.1 --port 9000

# SSE transport
python server.py --transport sse

# stdio (for Claude Desktop)
python server.py --transport stdio
```

The server exposes the MCP endpoint at:

```
http://localhost:8000/mcp
```

---

## Claude Desktop config

```json
{
  "mcpServers": {
    "finance": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

For **stdio** transport (no server process needed):

```json
{
  "mcpServers": {
    "finance": {
      "command": "python",
      "args": ["/absolute/path/to/server.py", "--transport", "stdio"]
    }
  }
}
```

---

## Tools

| Tool | Description |
|---|---|
| `get_stock_info` | Full company profile, market metrics, valuation ratios |
| `get_historical_data` | OHLCV history — configurable period & interval |
| `get_realtime_quote` | Live price, change %, pre/post-market |
| `get_technical_analysis` | SMA, EMA, RSI, MACD, Bollinger Bands, ATR, support/resistance |
| `get_options_chain` | Full calls + puts chain for any expiry |
| `get_holders` | Institutional, mutual fund & major holders |
| `get_earnings` | Upcoming earnings dates, EPS history, analyst targets |
| `get_analyst_recommendations` | Upgrade/downgrade history, consensus |
| `get_financial_statements` | Income statement, balance sheet, cash flow (annual or quarterly) |
| `get_news` | Latest headlines with publisher, URL, related tickers |
| `get_dividend_history` | Payment history, annual totals, yield stats |
| `compare_stocks` | Side-by-side comparison: return, volatility, Sharpe, PE, beta |
| `get_market_overview` | Snapshot of S&P 500, NASDAQ, VIX, Gold, BTC, EUR/USD, etc. |
| `search_symbol` | Find tickers by company name or keyword |
| `clear_cache` | Flush the in-memory TTL cache |

---

## Caching

All responses are cached in-memory with per-tool TTLs:

| Data type | TTL |
|---|---|
| Real-time quotes | 30 s |
| Historical data | 60 s |
| Technical analysis | 5 min |
| News | 5 min |
| Market overview | 60 s |
| Earnings / holders / financials | 1 h |

Call `clear_cache` to force a refresh.

---

## Example prompts (Claude)

```
What is the current price and analyst consensus for NVDA?
Show me technical analysis for TSLA — is it overbought?
Compare AAPL, MSFT, GOOGL over the past year
What are the latest news headlines for META?
Give me AAPL's quarterly income statement
What's the options chain for SPY expiring this Friday?
Show me the market overview right now
```
