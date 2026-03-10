# Requirements: Finance MCP Server

**Defined:** 2026-03-09
**Core Value:** Claude can reliably fetch real-time and historical financial data from Yahoo Finance through a standardized MCP interface.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### MCP Infrastructure

- [ ] **MCP-01**: Server uses FastMCP from mcp[cli]>=1.6.0 (not third-party fastmcp package)
- [ ] **MCP-02**: Server exposes streamable HTTP transport on port 8000
- [ ] **MCP-03**: CORS middleware allows OPTIONS preflight from any origin
- [ ] **MCP-04**: DNS-rebinding protection disabled at FastMCP construction time
- [ ] **MCP-05**: Health check endpoint responds to HTTP GET /health or /mcp
- [ ] **MCP-06**: Uvicorn ASGI server configured with host=0.0.0.0

### Core Market Data

- [ ] **DATA-01**: Server fetches real-time quotes (price, change, volume) for any valid symbol
- [ ] **DATA-02**: Server fetches historical OHLCV data with configurable period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max) and interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1mo, 3mo)
- [ ] **DATA-03**: Server fetches comprehensive company info (market cap, P/E, sector, industry, description, website, employees)

### Advanced Market Data

- [ ] **ADV-01**: Server fetches options chains (calls and puts) for any expiration date
- [ ] **ADV-02**: Server fetches financial statements (income, balance, cash flow) for annual or quarterly periods
- [ ] **ADV-03**: Server fetches dividend payment history with yield and payout ratio
- [ ] **ADV-04**: Server fetches earnings dates and historical EPS data

### Search & Discovery

- [ ] **SRC-01**: Server searches for ticker symbols by company name or keyword (returns up to 10 results)
- [ ] **SRC-02**: Server returns market overview snapshot of major indices (S&P 500, NASDAQ, Dow, VIX, 10Y Treasury, Gold, Crude Oil, EUR/USD, BTC/USD)

### Technical Analysis

- [ ] **TECH-01**: Server calculates SMA (20, 50, 200) and EMA (12, 26) for historical data
- [ ] **TECH-02**: Server calculates RSI (14-period) with overbought/oversold signals
- [ ] **TECH-03**: Server calculates MACD (12, 26, 9) with histogram and crossover detection
- [ ] **TECH-04**: Server calculates Bollinger Bands (20, 2) with bandwidth and percent-B
- [ ] **TECH-05**: Server calculates ATR (14-period) for volatility measurement
- [ ] **TECH-06**: Server identifies support and resistance levels from recent price action

### Comparative Analysis

- [x] **COMP-01**: Server compares multiple stocks side-by-side with performance metrics (period return, volatility, Sharpe ratio)

### Data Quality

- [ ] **QUAL-01**: Server safely handles NaN/Inf values in yfinance responses (converts to null)
- [ ] **QUAL-02**: Server formats pandas Timestamps to ISO 8601 strings
- [ ] **QUAL-03**: Server handles empty DataFrames gracefully (returns error message)
- [ ] **QUAL-04**: Server normalizes column names and data types for consistent JSON serialization

### Caching

- [ ] **CACHE-01**: Server implements in-memory cache with TTL for each data type
- [ ] **CACHE-02**: Real-time quotes cached for 30 seconds
- [ ] **CACHE-03**: Historical data cached for 60 seconds
- [ ] **CACHE-04**: Company info cached for 5 minutes (300 seconds)
- [ ] **CACHE-05**: Financial statements cached for 1 hour (3600 seconds)
- [ ] **CACHE-06**: Server provides tool to manually clear cache

### Docker Deployment

- [ ] **DOCKER-01**: Dockerfile uses python:3.12-slim base image
- [ ] **DOCKER-02**: Docker build is multi-stage (builder + runtime) to minimize image size
- [ ] **DOCKER-03**: Docker image supports linux/amd64 and linux/arm64 architectures
- [ ] **DOCKER-04**: Container exposes HTTP port 8000
- [ ] **DOCKER-05**: Container includes HEALTHCHECK configuration for orchestration
- [ ] **DOCKER-06**: docker-compose.yml provides local development configuration

### CI/CD Pipeline

- [ ] **CI-01**: GitHub Actions workflow runs on push to main and pull requests
- [ ] **CI-02**: Workflow includes lint job (ruff check and ruff format --check)
- [ ] **CI-03**: Workflow includes test job (pytest with coverage >=80%)
- [ ] **CI-04**: Workflow builds and pushes multi-arch Docker image to GHCR on main branch
- [ ] **CI-05**: Image tagged as `:latest` and with commit SHA

### Dependencies

- [ ] **DEPS-01**: requirements.txt specifies mcp[cli]>=1.6.0
- [ ] **DEPS-02**: requirements.txt specifies yfinance>=1.2.0 (floor version for TLS fix)
- [ ] **DEPS-03**: requirements.txt specifies pandas>=2.0.0 and numpy>=1.26.0
- [ ] **DEPS-04**: requirements.txt specifies uvicorn>=0.30.0 (explicit dependency)
- [ ] **DEPS-05**: requirements-dev.txt specifies ruff>=0.4.0 for linting
- [ ] **DEPS-06**: pyproject.toml configures ruff with line-length=100 and target-version=py312

### Error Handling

- [ ] **ERR-01**: Server catches yfinance exceptions and returns error dict with message
- [ ] **ERR-02**: Server provides informative error messages for invalid symbols
- [ ] **ERR-03**: Server logs errors for debugging while returning user-friendly messages

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Performance & Scalability

- **PERF-01**: Server implements Redis-backed cache for horizontal scaling
- **PERF-02**: Server adds rate limiting to prevent API abuse
- **PERF-03**: Server implements connection pooling for yfinance sessions

### Observability

- **OBS-01**: Server emits structured logs in JSON format
- **OBS-02**: Server exposes /metrics endpoint for Prometheus scraping
- **OBS-03**: Server adds request tracing with correlation IDs

### Advanced Features

- **FEAT-01**: Server supports real-time streaming updates (if yfinance adds support)
- **FEAT-02**: Server provides backtesting capabilities for technical strategies
- **FEAT-03**: Server supports custom date ranges for historical data queries

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Real-time WebSocket streaming | yfinance doesn't support it; would require polling or paid API |
| Authentication/Authorization | Single-tenant deployment; adds complexity without clear benefit |
| Data persistence (database) | In-memory cache is sufficient for MVP; DB adds operational overhead |
| Alternative data providers | Yahoo Finance via yfinance is sufficient for v1 |
| Portfolio tracking | Out of scope; this is a data server, not a portfolio manager |
| Social features | No sharing, commenting, or collaboration features |
| Payment processing | Free service; no subscriptions or usage limits |
| Mobile app | MCP server is backend-only; clients handle UI |
| Backtesting execution | Historical analysis only; no strategy execution or trading |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| MCP-01 through MCP-06 | Phase 1 | Pending |
| DATA-01 through DATA-03 | Phase 2 | Pending |
| ADV-01 through ADV-04 | Phase 3 | Pending |
| SRC-01 through SRC-02 | Phase 3 | Pending |
| TECH-01 through TECH-06 | Phase 4 | Pending |
| COMP-01 | Phase 4 | Complete |
| QUAL-01 through QUAL-04 | Phase 2 | Pending |
| CACHE-01 through CACHE-06 | Phase 2 | Pending |
| DOCKER-01 through DOCKER-06 | Phase 1 | Pending |
| CI-01 through CI-06 | Phase 1 | Pending |
| DEPS-01 through DEPS-06 | Phase 1 | Pending |
| ERR-01 through ERR-03 | Phase 2 | Pending |

**Coverage:**
- v1 requirements: 45 total
- Mapped to phases: 45
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-09*
*Last updated: 2026-03-09 after initial definition*
