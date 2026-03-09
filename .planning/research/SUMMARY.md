# Research Summary: Finance MCP Server

**Research Date:** 2026-03-09
**Status:** Complete

---

## Executive Summary

Building a production-ready MCP server for Yahoo Finance data using Python, FastMCP, and yfinance. The research identifies a clear technical path with known pitfalls and their solutions.

---

## Key Findings

### Stack Decisions

| Component | Choice | Version | Confidence |
|-----------|--------|---------|------------|
| Runtime | Python | 3.12+ | High |
| MCP SDK | FastMCP (from mcp[cli]) | >=1.6.0 | High |
| Data Layer | yfinance | >=1.2.0 | High (TLS fix) |
| Web Framework | Starlette (bundled) | - | High |
| ASGI Server | uvicorn | >=0.30.0 | High |
| Data Processing | pandas, numpy | >=2.0.0, >=1.26.0 | High |
| Linting | ruff | >=0.4.0 | High |

**Critical:** Use `mcp.server.fastmcp.FastMCP` NOT the third-party `fastmcp` package.

---

### Architecture

```
Docker Container
├── MCP Server Layer (FastMCP + CORS + uvicorn)
├── Tool Layer (@mcp.tool() decorators)
├── Data Layer (yfinance + cache)
└── Health Check (HTTP endpoint)
```

**Data Flow:** Claude Desktop → Starlette/CORS → FastMCP → Tool → yfinance → Yahoo Finance

---

### Features Scope

**Table Stakes (21 tools total):**
- MCP Infrastructure: 3 tools (initialize, tools/list, tools/call - automatic)
- Core Market Data: 3 tools (quotes, historical, info)
- Advanced Data: 4 tools (options, financials, dividends, earnings)
- Search & Discovery: 2 tools (symbol lookup, market overview)
- Technical Analysis: 6 indicators (RSI, MACD, Bollinger Bands, ATR, SMA/EMA, support/resistance)
- Comparative Analysis: 1 tool (multi-stock comparison)
- Developer Experience: 2 tools (cache, documentation)

**Differentiators:**
- Technical indicators with pandas calculations
- Multi-stock comparison
- TTL-based caching
- CORS support for MCP Inspector

**Out of Scope:**
- Real-time WebSocket streaming (yfinance limitation)
- Authentication/authorization (single-tenant)
- Portfolio tracking (data server only)

---

### Critical Pitfalls (Must Address in Phase 1)

1. **yfinance TLS Error** - Pin `>=1.2.0` to fix `TLSV1_ALERT_UNRECOGNIZED_NAME`
2. **Wrong MCP Import** - Use `mcp.server.fastmcp`, NOT third-party `fastmcp`
3. **CORS Blocking** - Add CORSMiddleware for MCP Inspector compatibility
4. **DNS-Rebinding** - Disable protection at FastMCP construction
5. **Starlette Routes** - Pass routes to constructor, don't set later
6. **Missing uvicorn** - Add explicit dependency to requirements.txt

---

### Build Strategy

**Phase 1: Foundation** (Prerequisites for everything)
- Project structure (requirements.txt, Dockerfile, docker-compose.yml)
- MCP server with CORS middleware
- Health check endpoint
- CI/CD pipeline

**Phase 2: Core Tools**
- Helper functions (_safe, _df_to_records, cache)
- Basic tools (stock info, historical, quote)

**Phase 3: Advanced Tools**
- Options, financials, dividends, earnings
- Search functionality

**Phase 4: Analysis Tools**
- Technical indicators
- Multi-stock comparison

**Phase 5: Polish**
- Improved error handling
- Documentation
- Tests

---

### Deployment Strategy

**CI/CD:** GitHub Actions → Docker (multi-arch) → GHCR
**Registry:** `ghcr.io/axelfooley/yfinance-mcp-server:latest`
**Platforms:** linux/amd64, linux/arm64
**Pull:** `docker compose pull && docker compose up -d`

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Yahoo Finance API changes | Medium | High | Pin yfinance version, monitor releases |
| Rate limiting | Low | Medium | Cache requests, add rate limiting in future |
| MCP SDK breaking changes | Low | Medium | Pin to >=1.6.0, watch for major versions |
| Docker build cache issues | Medium | Low | Use --no-cache for dependency updates |

---

## Next Steps

1. ✅ Research complete
2. **Next:** Define requirements (REQUIREMENTS.md)
3. **Then:** Create roadmap (ROADMAP.md)
4. **Then:** Execute Phase 1

---

## Research Artifacts

- **STACK.md** - Technology choices with versions and rationale
- **FEATURES.md** - Feature breakdown (table stakes, differentiators, anti-features)
- **ARCHITECTURE.md** - Component structure and data flow
- **PITFALLS.md** - Known issues with prevention strategies

---

*Last updated: 2026-03-09*
