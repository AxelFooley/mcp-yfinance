# Finance MCP Server

## What This Is

A Model Context Protocol (MCP) server that provides real-time access to Yahoo Finance data via yfinance. The server runs in Docker and exposes a streamable HTTP transport, allowing Claude and other MCP clients to query stock prices, historical data, financial statements, options chains, and more.

## Core Value

Claude can reliably fetch real-time and historical financial data from Yahoo Finance through a standardized MCP interface.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] **MCP Server Infrastructure**: Streamable HTTP transport with CORS support for browser-based MCP Inspector
- [ ] **Real-time Data**: Current stock prices, quotes, and market data
- [ ] **Historical Data**: OHLCV historical price data with configurable periods and intervals
- [ ] **Stock Info**: Comprehensive company profiles (market cap, P/E ratios, sector, etc.)
- [ ] **Technical Analysis**: RSI, MACD, Bollinger Bands, ATR, moving averages
- [ ] **Options Chains**: Full options data with calls/puts for any expiration
- [ ] **Financial Statements**: Income statement, balance sheet, cash flow (annual/quarterly)
- [ ] **Corporate Actions**: Dividends, earnings dates, splits
- [ ] **News**: Latest news and headlines for symbols
- [ ] **Search**: Symbol lookup by company name or keyword
- [ ] **Multi-symbol Comparison**: Side-by-side stock comparison with performance metrics
- [ ] **Docker Deployment**: Production-ready containerized deployment
- [ ] **CI/CD Pipeline**: Automated builds and tests via GitHub Actions
- [ ] **Health Monitoring**: Health check endpoint for container orchestration

### Out of Scope

- Real-time WebSocket streaming (yfinance polling is sufficient)
- Authentication/authorization (single-tenant deployment)
- Data persistence/caching (optional future enhancement)
- Alternative data providers (Yahoo Finance via yfinance only)

## Context

Building on the excellent work of [akshatbindal/finance-mcp-server](https://github.com/akshatbindal/finance-mcp-server) as inspiration. The project uses FastMCP (official MCP SDK) for streamable HTTP transport, yfinance for data fetching, and includes Docker deployment with GitHub Actions CI/CD.

**Technical Environment:**
- Python 3.12+
- FastMCP from mcp[cli]>=1.6.0
- yfinance>=1.2.0 (handles Yahoo Finance TLS/SNI requirements)
- Docker multi-arch builds (amd64/arm64)
- GitHub Container Registry for distribution

**Known Issues from Inspiration Project:**
- yfinance<1.2.0 has TLS/SNI issues with Yahoo Finance (resolved in 1.2.0)
- DNS-rebinding protection blocks connections from Docker bridge networks (resolved via TransportSecuritySettings)
- CORS headers needed for MCP Inspector browser compatibility

## Constraints

- **Transport**: Must use streamable HTTP (not stdio or SSE) for Claude Desktop connector compatibility
- **TLS/SSL**: yfinance>=1.2.0 required for Yahoo Finance API compatibility
- **Multi-arch**: Docker images must support both amd64 and arm64
- **No breaking changes**: Public API (MCP tools) must remain stable across versions
- **Single-file server**: Keep server.py self-contained for simplicity

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| FastMCP over custom implementation | Official MCP SDK, better maintained, standardized transport | ✓ Good |
| Streamable HTTP only | Claude Desktop connector requirement, avoids SSE complexity | — Pending |
| CORS enabled by default | Allows MCP Inspector for local debugging and development | ✓ Good |
| yfinance>=1.2.0 floor | Resolves TLSV1_ALERT_UNRECOGNIZED_NAME with Yahoo Finance | ✓ Good |
| Multi-stage Docker build | Smaller production images, faster deployment | — Pending |
| GHCR over Docker Hub | Better GitHub Actions integration, no rate limits | — Pending |

---
*Last updated: 2026-03-09 after project initialization*
