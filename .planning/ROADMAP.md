# Roadmap: Finance MCP Server

**Created:** 2026-03-09
**Granularity:** Coarse (fewer, broader phases)
**Total Phases:** 4
**Total Requirements:** 45

---

## Phase Overview

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 1 | Foundation | Project infrastructure and deployment pipeline | 17 | Server runs locally and in Docker, CI/CD builds images |
| 2 | Core Tools | Basic financial data retrieval with caching | 11 | Claude can fetch stock quotes, historical data, and company info |
| 3 | Advanced Data | Options, financials, earnings, dividends, search | 6 | Claude can access advanced market data and search symbols |
| 4 | Analysis | Technical indicators and multi-stock comparison | 7 | Claude can analyze stocks with technical indicators |

---

## Phase 1: Foundation

**Goal:** Establish project infrastructure with working MCP server and deployment pipeline

**Requirements (17):**
- MCP-01 through MCP-06: MCP server infrastructure
- DOCKER-01 through DOCKER-06: Docker deployment
- CI-01 through CI-06: CI/CD pipeline
- DEPS-01 through DEPS-06: Dependencies

**Success Criteria:**
1. Server starts with `docker compose up` and responds to health checks
2. CI/CD pipeline builds and pushes multi-arch Docker images to GHCR
3. MCP Inspector can connect and list tools (CORS working)
4. Server runs without TLS or DNS-rebinding errors

**Plans (3):**
1. Project structure and dependencies
2. MCP server with CORS and Docker
3. CI/CD pipeline

---

## Phase 2: Core Tools

**Goal:** Implement basic financial data retrieval with caching

**Requirements (11):**
- DATA-01 through DATA-03: Core market data
- QUAL-01 through QUAL-04: Data quality
- CACHE-01 through CACHE-06: Caching
- ERR-01 through ERR-03: Error handling

**Success Criteria:**
1. `get_stock_info` returns company profile for valid symbols
2. `get_historical_data` returns OHLCV candles with configurable period/interval
3. `get_realtime_quote` returns current price and change
4. Cached data is returned within TTL, fresh data fetched after expiry
5. Invalid symbols return informative error messages

**Plans (2):**
1. Helper functions and data quality
2. Core market data tools with caching

---

## Phase 3: Advanced Data

**Goal:** Add advanced market data and search functionality

**Requirements (6):**
- ADV-01 through ADV-04: Options, financials, dividends, earnings
- SRC-01 through SRC-02: Search and market overview

**Success Criteria:**
1. `get_options_chain` returns calls/puts for specified expiration
2. `get_financial_statements` returns income/balance/cashflow for annual or quarterly periods
3. `get_dividend_history` returns payment history with yield
4. `get_earnings` returns upcoming dates and historical EPS
5. `search_symbol` finds tickers by company name
6. `get_market_overview` returns major indices snapshot

**Plans (2):**
1. Options and financial statements
2. Dividends, earnings, and search

---

## Phase 4: Analysis

**Goal:** Implement technical analysis and comparative features

**Requirements (7):**
- TECH-01 through TECH-06: Technical indicators
- COMP-01: Comparative analysis

**Success Criteria:**
1. `get_technical_analysis` returns RSI, MACD, Bollinger Bands, ATR, moving averages
2. RSI signal correctly identifies overbought (>70) and oversold (<30) conditions
3. MACD crossover detects bullish (MACD > signal) and bearish (MACD < signal) trends
4. Bollinger Bands include bandwidth and percent-B metrics
5. `compare_stocks` returns side-by-side comparison with performance metrics
6. All technical indicators calculated from pandas DataFrames

**Plans (2):**
1. Technical indicator calculations
2. Multi-stock comparison

---

## Traceability Matrix

| Requirement | Phase | Plan | Status |
|-------------|-------|------|--------|
| MCP-01 | Phase 1 | 1.1 | Pending |
| MCP-02 | Phase 1 | 1.1 | Pending |
| MCP-03 | Phase 1 | 1.1 | Pending |
| MCP-04 | Phase 1 | 1.1 | Pending |
| MCP-05 | Phase 1 | 1.2 | Pending |
| MCP-06 | Phase 1 | 1.2 | Pending |
| DOCKER-01 | Phase 1 | 1.2 | Pending |
| DOCKER-02 | Phase 1 | 1.2 | Pending |
| DOCKER-03 | Phase 1 | 1.2 | Pending |
| DOCKER-04 | Phase 1 | 1.2 | Pending |
| DOCKER-05 | Phase 1 | 1.2 | Pending |
| DOCKER-06 | Phase 1 | 1.2 | Pending |
| CI-01 | Phase 1 | 1.3 | Pending |
| CI-02 | Phase 1 | 1.3 | Pending |
| CI-03 | Phase 1 | 1.3 | Pending |
| CI-04 | Phase 1 | 1.3 | Pending |
| CI-05 | Phase 1 | 1.3 | Pending |
| CI-06 | Phase 1 | 1.3 | Pending |
| DEPS-01 | Phase 1 | 1.1 | Pending |
| DEPS-02 | Phase 1 | 1.1 | Pending |
| DEPS-03 | Phase 1 | 1.1 | Pending |
| DEPS-04 | Phase 1 | 1.1 | Pending |
| DEPS-05 | Phase 1 | 1.1 | Pending |
| DEPS-06 | Phase 1 | 1.1 | Pending |
| DATA-01 | Phase 2 | 2.2 | Pending |
| DATA-02 | Phase 2 | 2.2 | Pending |
| DATA-03 | Phase 2 | 2.2 | Pending |
| QUAL-01 | Phase 2 | 2.1 | Pending |
| QUAL-02 | Phase 2 | 2.1 | Pending |
| QUAL-03 | Phase 2 | 2.1 | Pending |
| QUAL-04 | Phase 2 | 2.1 | Pending |
| CACHE-01 | Phase 2 | 2.1 | Pending |
| CACHE-02 | Phase 2 | 2.1 | Pending |
| CACHE-03 | Phase 2 | 2.1 | Pending |
| CACHE-04 | Phase 2 | 2.1 | Pending |
| CACHE-05 | Phase 2 | 2.1 | Pending |
| CACHE-06 | Phase 2 | 2.1 | Pending |
| ERR-01 | Phase 2 | 2.1 | Pending |
| ERR-02 | Phase 2 | 2.1 | Pending |
| ERR-03 | Phase 2 | 2.1 | Pending |
| ADV-01 | Phase 3 | 3.1 | Pending |
| ADV-02 | Phase 3 | 3.1 | Pending |
| ADV-03 | Phase 3 | 3.2 | Pending |
| ADV-04 | Phase 3 | 3.2 | Pending |
| SRC-01 | Phase 3 | 3.2 | Pending |
| SRC-02 | Phase 3 | 3.2 | Pending |
| TECH-01 | Phase 4 | 4.1 | Pending |
| TECH-02 | Phase 4 | 4.1 | Pending |
| TECH-03 | Phase 4 | 4.1 | Pending |
| TECH-04 | Phase 4 | 4.1 | Pending |
| TECH-05 | Phase 4 | 4.1 | Pending |
| TECH-06 | Phase 4 | 4.1 | Pending |
| COMP-01 | Phase 4 | 4.2 | Pending |

---

## Phase Details

### Phase 1: Foundation

**Plan 1.1: Project Structure and Dependencies**
- Create requirements.txt with mcp[cli]>=1.6.0, yfinance>=1.2.0, pandas, numpy, uvicorn
- Create requirements-dev.txt with ruff>=0.4.0, pytest, pytest-cov
- Create pyproject.toml with ruff configuration
- Create .gitignore for Python, Docker, and IDE files
- Create basic README.md with project description

**Plan 1.2: MCP Server with CORS and Docker**
- Create server.py with FastMCP setup
- Add CORSMiddleware wrapper for MCP Inspector compatibility
- Disable DNS-rebinding protection at construction
- Create Dockerfile (multi-stage: builder + runtime)
- Create docker-compose.yml for local development
- Add healthcheck.py for container health checks

**Plan 1.3: CI/CD Pipeline**
- Create .github/workflows/ci.yml
- Add lint job (ruff check and ruff format --check)
- Add test job (pytest with --cov>=80%)
- Add docker job (buildx multi-arch build and push to GHCR)
- Configure image tags: :latest and commit SHA

---

### Phase 2: Core Tools

**Plan 2.1: Helper Functions and Data Quality**
- Implement _safe() to convert NaN/Inf to null
- Implement _df_to_records() to format DataFrames as list of dicts
- Implement _series_to_dict() to format Series as dict
- Implement cache functions (_cache_get, _cache_set) with TTL
- Implement _ticker() to get/create yf.Ticker objects

**Plan 2.2: Core Market Data Tools**
- Implement @mcp.tool() decorator for get_stock_info
- Implement @mcp.tool() decorator for get_historical_data
- Implement @mcp.tool() decorator for get_realtime_quote
- Add error handling with try/except blocks
- Add logging for debugging
- Write tests for each tool

---

### Phase 3: Advanced Data

**Plan 3.1: Options and Financial Statements**
- Implement get_options_chain tool with expiration parameter
- Implement get_financial_statements tool with frequency parameter
- Add DataFrame formatting for financial data
- Handle empty data gracefully

**Plan 3.2: Dividends, Earnings, and Search**
- Implement get_dividend_history tool with annual aggregation
- Implement get_earnings tool with dates and price targets
- Implement search_symbol tool using yfinance Search
- Implement get_market_overview tool for major indices

---

### Phase 4: Analysis

**Plan 4.1: Technical Indicator Calculations**
- Implement _compute_rsi() function (14-period)
- Implement _compute_macd() function (12, 26, 9)
- Implement _compute_bollinger() function (20, 2)
- Implement _compute_atr() function (14-period)
- Implement _support_resistance() function (recent high/low)
- Implement get_technical_analysis tool

**Plan 4.2: Multi-Stock Comparison**
- Implement compare_stocks tool accepting comma-separated symbols
- Calculate period returns, volatility, Sharpe ratio
- Return sorted comparison table

---

## Deployment

**CI/CD:** GitHub Actions → Docker (multi-arch) → GHCR
**Registry:** ghcr.io/axelfooley/yfinance-mcp-server:latest
**Platforms:** linux/amd64, linux/arm64
**Local:** docker compose up --build

**Remote Deployment:**
```bash
docker compose pull
docker compose up -d
docker compose logs -f
```

---

*Roadmap created: 2026-03-09*
*Last updated: 2026-03-09 after initial creation*
