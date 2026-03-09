# Architecture Research: Finance MCP Server

**Research Date:** 2026-03-09

---

## Component Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Container                      │
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │              MCP Server Layer                      │ │
│  │  • FastMCP initialization                         │ │
│  │  • Transport configuration (streamable HTTP)       │ │
│  │  • CORS middleware injection                       │ │
│  │  • Transport security settings                     │ │
│  └──────────────┬────────────────────────────────────┘ │
│                 │                                        │
│  ┌──────────────▼────────────────────────────────────┐ │
│  │              Tool Layer                           │ │
│  │  • Tool decorators (@mcp.tool())                  │ │
│  │  • Input validation (type hints)                  │ │
│  │  • Response formatting (_safe, _df_to_records)    │ │
│  │  • Error handling (try/except, informative msgs)   │ │
│  └──────────────┬────────────────────────────────────┘ │
│                 │                                        │
│  ┌──────────────▼────────────────────────────────────┐ │
│  │              Data Layer                           │ │
│  │  • yfinance Ticker objects                        │ │
│  │  • In-memory cache (dict with TTL)                │ │
│  │  • Rate limiting (implicit via yfinance)           │ │
│  │  • Error handling for API failures                │ │
│  └──────────────┬────────────────────────────────────┘ │
│                 │                                        │
│  ┌──────────────▼────────────────────────────────────┐ │
│  │          External Services                        │ │
│  │  • Yahoo Finance API (via yfinance)               │ │
│  └──────────────────────────────────────────────────┘ │
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │           Health Check Endpoint                   │ │
│  │  • HTTP GET /health or /mcp (MCP init)            │ │
│  │  • Returns 200 if server is responsive            │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                   CI/CD Layer                           │
│  • GitHub Actions workflows                            │
│  • Lint (ruff) → Test (pytest) → Docker (buildx)       │
│  • Push to GHCR on main branch                         │
└─────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. MCP Server Layer

**Responsibility:** Initialize and configure the MCP server with FastMCP

**Components:**
- FastMCP instance with name, instructions, transport_security
- Streamable HTTP transport configuration
- CORS middleware wrapper (Starlette with CORSMiddleware)
- uvicorn ASGI server

**Interfaces:**
- HTTP POST `/mcp` - Main MCP endpoint (JSON-RPC over HTTP)
- HTTP GET `/health` - Health check endpoint
- HTTP OPTIONS `/*` - CORS preflight (handled by middleware)

**Configuration:**
```python
mcp = FastMCP(
    name="Finance MCP Server",
    instructions="...",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    )
)

app = Starlette(
    routes=[Mount("/", app=mcp.streamable_http_app())],
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"]
        )
    ]
)

uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Dependencies:**
- mcp.server.fastmcp.FastMCP
- starlette.applications.Starlette
- starlette.middleware.Middleware
- starlette.middleware.cors.CORSMiddleware
- starlette.routing.Mount
- uvicorn

**Build Order:** **FIRST** - All other layers depend on this

---

### 2. Tool Layer

**Responsibility:** Define and implement MCP tools for financial data

**Components:**
- Tool functions decorated with `@mcp.tool()`
- Input validation via type hints
- Response formatting via helper functions
- Error handling with informative messages

**Tool Categories:**
1. **Core Tools** (3-4 tools)
   - `get_stock_info(symbol)` - Company profile
   - `get_historical_data(symbol, period, interval)` - OHLCV data
   - `get_realtime_quote(symbol)` - Current price

2. **Advanced Tools** (4-5 tools)
   - `get_options_chain(symbol, expiration)` - Options data
   - `get_financial_statements(symbol, frequency)` - Financial statements
   - `get_dividend_history(symbol, period)` - Dividends
   - `get_earnings(symbol)` - Earnings data

3. **Analysis Tools** (1-2 tools)
   - `get_technical_analysis(symbol, period)` - RSI, MACD, Bollinger Bands
   - `compare_stocks(symbols, period)` - Multi-stock comparison

4. **Search Tools** (1-2 tools)
   - `search_symbol(query)` - Symbol lookup
   - `get_market_overview()` - Major indices

**Interfaces:**
- Each tool accepts parameters via MCP protocol
- Returns JSON-serializable dictionaries
- Uses `_safe()`, `_df_to_records()`, `_series_to_dict()` helpers

**Dependencies:**
- FastMCP decorator
- yfinance (for data fetching)
- pandas/numpy (for data processing)

**Build Order:** **SECOND** - Depends on MCP Server Layer

---

### 3. Data Layer

**Responsibility:** Fetch and cache financial data from Yahoo Finance

**Components:**
- `yf.Ticker` objects for each symbol
- In-memory cache (`_CACHE` dict with `_CACHE_TS` timestamps)
- TTL-based cache invalidation
- Error handling for API failures

**Cache Strategy:**
```python
_CACHE: dict[str, Any] = {}
_CACHE_TS: dict[str, float] = {}

def _cache_get(key: str, ttl: int) -> Any | None:
    if key in _CACHE and (time.time() - _CACHE_TS.get(key, 0)) < ttl:
        return _CACHE[key]
    return None

def _cache_set(key: str, value: Any) -> None:
    _CACHE[key] = value
    _CACHE_TS[key] = time.time()
```

**TTL Values:**
- Real-time quotes: 30 seconds
- Historical data: 60 seconds
- Company info: 300 seconds (5 minutes)
- Financial statements: 3600 seconds (1 hour)
- News: 300 seconds (5 minutes)

**Error Handling:**
- Try/except around yfinance calls
- Return error dict on failure: `{"error": "message"}`
- Log errors for debugging

**Dependencies:**
- yfinance
- time (for TTL calculations)

**Build Order:** **THIRD** - Depends on Tool Layer (tools use cache)

---

### 4. Health Check Layer

**Responsibility:** Provide health status for container orchestration

**Components:**
- HTTP endpoint (`/health` or `/mcp`)
- MCP protocol handshake (acts as health check)
- Docker HEALTHCHECK configuration

**Implementation:**
```python
# Option 1: Standalone health endpoint
@app.get("/health")
async def health():
    return {"status": "ok"}

# Option 2: Use MCP init endpoint
# Docker HEALTHCHECK sends MCP init request
```

**Docker HEALTHCHECK:**
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD ["python", "/app/healthcheck.py"]
```

**Dependencies:**
- Starlette (if custom endpoint)
- Python urllib (if healthcheck.py script)

**Build Order:** **FOURTH** (Can be built alongside MCP Server Layer)

---

### 5. CI/CD Layer

**Responsibility:** Automated testing, linting, and deployment

**Components:**
1. **Lint Job** - ruff check and ruff format --check
2. **Test Job** - pytest with coverage
3. **Docker Job** - Multi-arch build and push to GHCR

**Workflow:**
```yaml
on:
  push:
    branches: ["main"]
  pull_request:
    branches: ["**"]

jobs:
  lint → test → docker (only on main)
```

**Docker Build Strategy:**
- Multi-stage: builder (dependencies) + runtime (minimal)
- Multi-arch: linux/amd64, linux/arm64
- Cache: GitHub Actions cache for pip layers
- Push: ghcr.io/axelfooley/yfinance-mcp-server:latest

**Dependencies:**
- GitHub Actions
- Docker buildx
- pytest, ruff

**Build Order:** **Can be built in parallel** with development

---

## Data Flow

```
1. Claude Desktop sends JSON-RPC request
   ↓
2. Starlette + CORS middleware receives HTTP POST
   ↓
3. FastMCP routes to appropriate tool function
   ↓
4. Tool function checks cache
   ├─ Cache hit → Return cached data
   └─ Cache miss → Continue
   ↓
5. Tool function calls yfinance API
   ↓
6. yfinance fetches data from Yahoo Finance
   ↓
7. Tool function formats response (helpers)
   ↓
8. Tool function caches response (if cacheable)
   ↓
9. FastMCP serializes to JSON-RPC response
   ↓
10. Starlette returns HTTP response
```

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    GitHub Repo                          │
│  • Source code (server.py, requirements.txt, Dockerfile)│
│  • CI/CD workflows (.github/workflows/ci.yml)           │
└──────────────────────┬──────────────────────────────────┘
                       │ push to main
                       ▼
┌─────────────────────────────────────────────────────────┐
│              GitHub Actions (CI/CD)                     │
│  • Lint → Test → Build → Push                          │
└──────────────────────┬──────────────────────────────────┘
                       │ build + push
                       ▼
┌─────────────────────────────────────────────────────────┐
│          GitHub Container Registry (GHCR)               │
│  • ghcr.io/axelfooley/yfinance-mcp-server:latest        │
│  • Multi-arch: amd64, arm64                             │
└──────────────────────┬──────────────────────────────────┘
                       │ docker pull
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Remote Node (Docker)                       │
│  • docker compose pull                                  │
│  • docker compose up -d                                 │
│  • Health check ensures running                         │
└─────────────────────────────────────────────────────────┘
```

---

## Build Order

**Phase 1: Foundation (MCP Infrastructure)**
1. Project structure (requirements.txt, Dockerfile, docker-compose.yml)
2. MCP server initialization (FastMCP setup)
3. CORS middleware
4. Health check endpoint
5. CI/CD pipeline skeleton

**Phase 2: Core Tools (Data Retrieval)**
1. Helper functions (_safe, _df_to_records, cache)
2. Basic tools (stock info, historical data, real-time quote)
3. Error handling

**Phase 3: Advanced Tools**
1. Options chains
2. Financial statements
3. Dividends, earnings
4. Search functionality

**Phase 4: Analysis Tools**
1. Technical indicators (RSI, MACD, Bollinger Bands)
2. Multi-stock comparison

**Phase 5: Polish**
1. Improved caching
2. Better error messages
3. Documentation
4. Tests

---

*Last updated: 2026-03-09*
