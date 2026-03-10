# Finance MCP Server

## What This Is

A Model Context Protocol (MCP) server that provides real-time access to Yahoo Finance data via yfinance. The server runs in Docker and exposes a streamable HTTP transport, allowing Claude and other MCP clients to query stock prices, historical data, financial statements, options chains, technical indicators, and more.

## Core Value

Claude can reliably fetch real-time and historical financial data from Yahoo Finance through a standardized MCP interface.

## Requirements

### Validated

- ✓ **MCP Server Infrastructure** — v1.0 — Streamable HTTP transport with CORS support for browser-based MCP Inspector
- ✓ **Real-time Data** — v1.0 — Current stock prices, quotes, and market data
- ✓ **Historical Data** — v1.0 — OHLCV historical price data with configurable periods and intervals
- ✓ **Stock Info** — v1.0 — Comprehensive company profiles (market cap, P/E ratios, sector, etc.)
- ✓ **Technical Analysis** — v1.0 — RSI, MACD, Bollinger Bands, ATR, moving averages
- ✓ **Options Chains** — v1.0 — Full options data with calls/puts for any expiration
- ✓ **Financial Statements** — v1.0 — Income statement, balance sheet, cash flow (annual/quarterly)
- ✓ **Corporate Actions** — v1.0 — Dividends, earnings dates, splits
- ✓ **Search** — v1.0 — Symbol lookup by company name or keyword
- ✓ **Multi-symbol Comparison** — v1.0 — Side-by-side stock comparison with performance metrics
- ✓ **Docker Deployment** — v1.0 — Production-ready containerized deployment
- ✓ **CI/CD Pipeline** — v1.0 — Automated builds and tests via GitHub Actions
- ✓ **Health Monitoring** — v1.0 — Health check endpoint for container orchestration

### Active

(None — start next milestone to define new requirements)

### Out of Scope

- Real-time WebSocket streaming (yfinance polling is sufficient)
- Authentication/authorization (single-tenant deployment)
- Data persistence/caching (optional future enhancement)
- Alternative data providers (Yahoo Finance via yfinance only)
- Portfolio tracking (out of scope; this is a data server, not a portfolio manager)
- Social features (no sharing, commenting, or collaboration features)
- Payment processing (free service; no subscriptions or usage limits)
- Mobile app (MCP server is backend-only; clients handle UI)
- Backtesting execution (historical analysis only; no strategy execution or trading)

## Context

<details>
<summary>v1.0 Development Context</summary>

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

</details>

## Current State

**Shipped:** v1.0 MVP (2026-03-10)

**Delivered:**
- 13 MCP tools for financial data retrieval and analysis
- 6 technical indicators (RSI, MACD, Bollinger Bands, ATR, SMA/EMA, support/resistance)
- In-memory caching with configurable TTL
- Multi-arch Docker deployment (amd64/arm64)
- CI/CD pipeline with GitHub Actions
- 90%+ test coverage (21+ unit tests)

**Next Milestone Goals:**
(Define with `/gsd:new-milestone`)

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
| Streamable HTTP only | Claude Desktop connector requirement, avoids SSE complexity | ✓ Good |
| CORS enabled by default | Allows MCP Inspector for local debugging and development | ✓ Good |
| yfinance>=1.2.0 floor | Resolves TLSV1_ALERT_UNRECOGNIZED_NAME with Yahoo Finance | ✓ Good |
| Multi-stage Docker build | Smaller production images, faster deployment | ✓ Good |
| GHCR over Docker Hub | Better GitHub Actions integration, no rate limits | ✓ Good |
| In-memory cache vs Redis | Simpler for MVP, single-process deployment | ✓ Good |
| Decorator-based caching | Clean syntax, reusable pattern | ✓ Good |
| Error dict vs exceptions | MCP protocol expects return values | ✓ Good |

---
*Last updated: 2026-03-10 after v1.0 milestone*
