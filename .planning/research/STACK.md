# Stack Research: Finance MCP Server

**Research Date:** 2026-03-09
**Domain:** Python MCP Server with yfinance integration

---

## Core Runtime

### Python 3.12+
- **Version:** `python:3.12-slim` (Docker base image)
- **Rationale:** Latest stable Python with performance improvements, type hints, and pattern matching. Slim image keeps container size minimal.
- **Alternatives considered:**
  - Python 3.11: Good, but 3.12 has better perf
  - Python 3.13: Too new, potential compatibility issues
- **Confidence:** High

---

## MCP SDK

### FastMCP (from `mcp[cli]>=1.6.0`)
- **Version:** `>=1.6.0`
- **Rationale:** Official MCP SDK with first-class streamable HTTP transport support. Actively maintained by ModelContextProtocol team. Better than custom implementations.
- **Alternatives considered:**
  - Custom SSE implementation: More complex, less maintained
  - `fastmcp` third-party package: Abandoned, conflicts with official mcp package
- **Critical:** Use `mcp.server.fastmcp.FastMCP`, NOT the third-party `fastmcp` package
- **Confidence:** High

---

## Data Layer

### yfinance
- **Version:** `>=1.2.0` (floor requirement, not pinned)
- **Rationale:** 1.2.0+ fixes critical TLS/SNI issue with Yahoo Finance (`TLSV1_ALERT_UNRECOGNIZED_NAME`). Using floor allows patch updates but prevents broken versions.
- **Alternatives considered:**
  - yfinance 0.2.x: Has TLS issues, deprecated
  - yfinance 0.1.x: Ancient, missing features
  - Yahoo Finance API directly: TOS violation, requires auth
- **Critical:** Pin floor at 1.2.0 to avoid TLS errors
- **Confidence:** High

---

## Web Framework

### Starlette (via FastMCP)
- **Version:** Bundled with mcp package
- **Rationale:** FastMCP uses Starlette internally for HTTP transport. No additional web framework needed.
- **Alternatives considered:**
  - Flask/FastAPI on top: Unnecessary complexity
  - Pure ASGI: Too low-level
- **Note:** Starlette accessible via `mcp.streamable_http_app()` for CORS middleware injection
- **Confidence:** High

---

## Data Processing

### pandas
- **Version:** `>=2.0.0`
- **Rationale:** Required by yfinance for DataFrame operations. Version 2.0+ has cleaner API and better performance.
- **Confidence:** High

### numpy
- **Version:** `>=1.26.0`
- **Rationale:** Required by pandas and yfinance for numerical operations.
- **Confidence:** High

---

## CORS Middleware

### starlette.middleware.cors.CORSMiddleware
- **Version:** Bundled with Starlette/mcp
- **Rationale:** Required for MCP Inspector (browser-based) to make cross-origin requests. Must be added via `Middleware()` wrapper.
- **Critical:** Use `Middleware(CORSMiddleware, allow_origins=["*"], ...)` format, NOT tuple format
- **Confidence:** High

---

## Dev Dependencies

### ruff
- **Version:** `>=0.4.0`
- **Rationale:** Fast Python linter/formatter. Replaces pylint, black, isort. Single tool for linting and formatting.
- **Usage:** `ruff check` for linting, `ruff format` for formatting
- **Confidence:** High

### pytest
- **Version:** (via `mcp[cli]`)
- **Rationale:** Test runner bundled with MCP SDK
- **Confidence:** High

### pytest-cov
- **Version:** (via dev dependencies)
- **Rationale:** Coverage reporting for test suite
- **Confidence:** High

---

## Deployment

### Docker
- **Base Image:** `python:3.12-slim`
- **Strategy:** Multi-stage build (builder + runtime)
- **Platforms:** `linux/amd64`, `linux/arm64`
- **Rationale:**
  - Multi-stage reduces final image size
  - Multi-arch supports both Intel and Apple Silicon
  - Slim base minimizes attack surface
- **Confidence:** High

### uvicorn
- **Version:** `>=0.30.0` (explicit dependency)
- **Rationale:** ASGI server required when using `mcp.streamable_http_app()` directly. Not bundled with mcp.
- **Critical:** Add to requirements.txt explicitly
- **Confidence:** High

---

## CI/CD

### GitHub Actions
- **Rationale:** Native GitHub integration, free for public repos, supports multi-arch Docker builds via `docker/setup-buildx-action`
- **Confidence:** High

### GitHub Container Registry (GHCR)
- **Rationale:** Better GitHub Actions integration than Docker Hub, no rate limits, supports CI tokens
- **Pattern:** `ghcr.io/{username}/{repo}:latest`
- **Confidence:** High

---

## Security

### Transport Security Settings
- **Setting:** `TransportSecuritySettings(enable_dns_rebinding_protection=False)`
- **Rationale:** FastMCP auto-enables DNS-rebinding protection when constructed with default host. This blocks connections from Docker bridge IPs (172.16.x.x). Must disable at construction time.
- **Confidence:** High

---

## What NOT to Use

| Library | Why NOT to Use |
|---------|----------------|
| `fastmcp` (PyPI package) | Abandoned third-party package, conflicts with official mcp SDK |
| Flask/FastAPI | Unecessary abstraction over FastMCP's Starlette app |
| requests | yfinance uses urllib3 internally, don't add another HTTP client |
| redis | Optional caching, not required for MVP |
| celery | Overkill for simple polling, yfinance handles rate limiting internally |

---

## Version Pinning Strategy

- **Floor versions with `>=`:** yfinance, pandas, numpy (allow patch updates)
- **Exact versions:** Not recommended unless specific bug fix needed
- **Bundled deps:** Don't pin mcp internals (Starlette, anyio)
- **Dev tools:** Pin to minor version to avoid workflow breakage

---

*Last updated: 2026-03-09*
