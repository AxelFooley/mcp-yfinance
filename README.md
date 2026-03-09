# Finance MCP Server

A Model Context Protocol (MCP) server that provides real-time access to Yahoo Finance data via yfinance.

## Features

- Real-time stock quotes and market data
- Historical OHLCV data with configurable periods
- Company profiles and financial statements
- Options chains and dividends
- Technical indicators (RSI, MACD, Bollinger Bands, ATR)
- Multi-stock comparison

## Quick Start

### Docker (Recommended)

```bash
docker compose up --build
```

### Local Development

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Run server
python server.py --host 0.0.0.0 --port 8000
```

## MCP Inspector

```bash
npx @modelcontextprotocol/inspector http://localhost:8000/mcp
```

## Configuration

Environment variables:
- `PYTHONUNBUFFERED=1`: Disable output buffering

## License

MIT
