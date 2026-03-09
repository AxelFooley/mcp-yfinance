# Plan: Phase 1 - Foundation

**Phase:** 1 - Foundation
**Goal:** Establish project infrastructure with working MCP server and deployment pipeline
**Requirements:** 17 (MCP-01 through MCP-06, DOCKER-01 through DOCKER-06, CI-01 through CI-06, DEPS-01 through DEPS-06)

---

## Overview

This phase creates the foundational infrastructure for the Finance MCP Server. We'll set up the project structure, create a working MCP server with CORS middleware, containerize with Docker, and establish a CI/CD pipeline for automated builds and deployments.

**Success Criteria:**
1. ✅ Server starts with `docker compose up` and responds to health checks
2. ✅ CI/CD pipeline builds and pushes multi-arch Docker images to GHCR
3. ✅ MCP Inspector can connect and list tools (CORS working)
4. ✅ Server runs without TLS or DNS-rebinding errors

---

## Plan 1.1: Project Structure and Dependencies

### Tasks

#### 1. Create requirements.txt
**File:** `requirements.txt`

**Content:**
```txt
mcp[cli]>=1.6.0
yfinance>=1.2.0
pandas>=2.0.0
numpy>=1.26.0
uvicorn>=0.30.0
```

**Rationale:**
- `mcp[cli]>=1.6.0`: Official MCP SDK with FastMCP support
- `yfinance>=1.2.0`: Floor version for TLS fix (avoid TLSV1_ALERT_UNRECOGNIZED_NAME)
- `pandas>=2.0.0`, `numpy>=1.26.0`: Required by yfinance for data operations
- `uvicorn>=0.30.0`: Explicit dependency when using `streamable_http_app()` directly

**Avoid:**
- Do NOT add `fastmcp` (third-party package, abandoned)

---

#### 2. Create requirements-dev.txt
**File:** `requirements-dev.txt`

**Content:**
```txt
-r requirements.txt
ruff>=0.4.0
pytest>=8.0.0
pytest-cov>=4.0.0
pytest-asyncio>=0.23.0
```

**Rationale:**
- `ruff`: Fast linter/formatter (replaces pylint, black, isort)
- `pytest`, `pytest-cov`: Test coverage reporting
- `pytest-asyncio`: Async test support for FastMCP

---

#### 3. Create pyproject.toml
**File:** `pyproject.toml`

**Content:**
```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "UP"]
ignore = [
    "E501",   # line-length enforced by formatter only
    "UP007",  # Optional[X] → X | None — keep compat annotation style
]

[tool.ruff.lint.isort]
known-first-party = ["server"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = [
    "-v",
    "--tb=short",
    "--cov=server",
    "--cov-report=term-missing",
    "--cov-report=xml:coverage.xml",
    "--cov-fail-under=80",
]

[tool.coverage.run]
source = ["server"]
omit = ["tests/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if __name__ == .__main__.:",
    "raise NotImplementedError",
]
```

**Rationale:**
- Line length 100 for readability
- Python 3.12 target (matches Docker image)
- 80% coverage requirement
- XML coverage for CI integration

---

#### 4. Create .gitignore
**File:** `.gitignore`

**Content:**
```gitignore
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# PyInstaller
*.manifest
*.spec

# Unit test / coverage reports
htmlcov/
.tox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
.hypothesis/
.pytest_cache/

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDEs
.idea/
.vscode/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# GSD (optional - remove if commit_docs=false)
# .planning/
```

**Rationale:**
- Standard Python ignores
- IDE ignores
- Coverage reports
- Virtual environments

---

#### 5. Create README.md
**File:** `README.md`

**Content:**
```markdown
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
```

---

## Plan 1.2: MCP Server with CORS and Docker

### Tasks

#### 1. Create server.py (minimal, just infrastructure)
**File:** `server.py`

**Content:**
```python
"""
Finance MCP Server — Streamable HTTP
Powered by FastMCP + yfinance

Provides real-time stock data, technical analysis, financials,
options, news, dividends, earnings, and more.
"""

from __future__ import annotations

import argparse
import uvicorn
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# ──────────────────────────────────────────────
# Server
# ──────────────────────────────────────────────

# Disable DNS-rebinding protection so clients connecting from Docker bridge
# networks (non-localhost Host headers) aren't rejected with 421.
# The FastMCP constructor auto-enables protection when host="127.0.0.1"
# (the default), so we must pass this explicitly.
mcp = FastMCP(
    name="Finance MCP Server",
    instructions=(
        "Real-time stock market data, technical analysis, financials, "
        "options chains, news, dividends, earnings, and sector comparison "
        "— all sourced from Yahoo Finance via yfinance."
    ),
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)

# ──────────────────────────────────────────────
# Tools (placeholder - will be implemented in Phase 2)
# ──────────────────────────────────────────────

@mcp.tool()
def health_check() -> str:
    """Health check endpoint for container orchestration."""
    return "ok"

# ──────────────────────────────────────────────
# Entry-point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Finance MCP Server (streamable HTTP)")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument(
        "--transport",
        default="streamable-http",
        choices=["streamable-http", "sse", "stdio"],
        help="MCP transport (default: streamable-http)",
    )
    args = parser.parse_args()

    print(f"🚀  Finance MCP Server starting on {args.host}:{args.port}  [{args.transport}]")

    # Get the ASGI app for the specified transport
    if args.transport == "streamable-http":
        mcp_app = mcp.streamable_http_app()
    elif args.transport == "sse":
        mcp_app = mcp.sse_app()
    else:
        # stdio doesn't use HTTP, use the default run method
        mcp.run(transport=args.transport)
        exit(0)

    # Create a wrapper app with CORS middleware for MCP Inspector compatibility
    app = Starlette(
        routes=[Mount("/", app=mcp_app)],
        middleware=[
            Middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        ]
    )

    uvicorn.run(app, host=args.host, port=args.port)
```

**Critical Implementation Details:**

1. **Import Path:** `from mcp.server.fastmcp import FastMCP` (NOT `import fastmcp`)

2. **DNS-Rebinding:** Pass `transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False)` at construction time (cannot be changed later)

3. **CORS Middleware:** Use `Middleware(CORSMiddleware, ...)` format (NOT tuple format)

4. **Starlette Routes:** Pass `routes=[Mount("/", app=mcp_app)]` to constructor (NOT `app.routes = ...`)

5. **streamable_http_app():** Call as method: `mcp.streamable_http_app()` (NOT `mcp.streamable_http_app`)

---

#### 2. Create Dockerfile
**File:** `Dockerfile`

**Content:**
```dockerfile
# ── Stage 1: dependency installer ────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build deps into an isolated prefix so we can copy just the artifacts
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: lean runtime image ───────────────────────────────────────────────
FROM python:3.12-slim

# Non-root user for security
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY server.py .

# Ownership
RUN chown -R appuser:appuser /app

USER appuser

# Runtime env
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Run the server
CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "8000"]
```

**Rationale:**
- Multi-stage build reduces final image size
- Non-root user for security
- Python 3.12-slim for minimal base
- PYTHONUNBUFFERED for immediate log output

---

#### 3. Create docker-compose.yml
**File:** `docker-compose.yml`

**Content:**
```yaml
services:
  finance-mcp:
    build: .
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
```

**Rationale:**
- Simple local development configuration
- Port 8000 exposed
- Restart policy for reliability

---

#### 4. Create .dockerignore
**File:** `.dockerignore`

**Content:**
```dockerignore
.git
.github
.planning
*.md
tests/
.env
.venv
venv/
__pycache__/
*.pyc
.coverage
coverage.xml
pytest-cache-files/
```

**Rationale:**
- Exclude development artifacts from Docker build context
- Speed up builds by excluding unnecessary files

---

## Plan 1.3: CI/CD Pipeline

### Tasks

#### 1. Create CI workflow
**File:** `.github/workflows/ci.yml`

**Content:**
```yaml
name: CI

on:
  push:
    branches: ["main"]
  pull_request:
    branches: ["**"]
  tags: ["v*.*.*"]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

env:
  REGISTRY: ghcr.io
  IMAGE: ghcr.io/axelfooley/finance-mcp-server

jobs:
  # ── 1. Lint ────────────────────────────────────────────────
  lint:
    name: Lint (ruff)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: Install ruff
        run: pip install "ruff>=0.4.0"

      - name: Check style
        run: ruff check .

      - name: Check formatting
        run: ruff format --check .


  # ── 2. Test ────────────────────────────────────────────────
  test:
    name: Test (pytest + coverage)
    runs-on: ubuntu-latest
    needs: lint

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: Install dev dependencies
        run: pip install -r requirements-dev.txt

      - name: Run test suite
        run: pytest


  # ── 3. Docker build + push ─────────────────────────────────
  docker:
    name: Docker (build & push)
    runs-on: ubuntu-latest
    needs: test

    # Only publish on pushes to main or on version tags — never on PRs
    if: >
      github.event_name == 'push' &&
      (github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/tags/v'))

    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v4

      - name: Set up QEMU (multi-arch)
        uses: docker/setup-qemu-action@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Docker metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.IMAGE }}
          tags: |
            type=raw,value=latest,enable={{is_default_branch}}
            type=sha,prefix=,format=short
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          platforms: linux/amd64,linux/arm64
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

**Rationale:**
- Lint → Test → Docker (sequential gates)
- Only push to GHCR on main branch or tags
- Multi-arch: amd64, arm64
- GitHub Actions cache for faster builds
- Semantic versioning tags

---

## Verification Steps

After completing this phase:

### 1. Local Development
```bash
# Install dependencies
pip install -r requirements-dev.txt

# Run linting
ruff check .
ruff format --check .

# Run server
python server.py

# Test MCP endpoint (another terminal)
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

Expected: JSON-RPC response with server capabilities

---

### 2. Docker
```bash
# Build and run
docker compose up --build

# Check logs
docker compose logs -f

# Test MCP endpoint from host
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

Expected: List of available tools (including `health_check`)

---

### 3. CORS Verification
```bash
# Test OPTIONS preflight
curl -i -X OPTIONS http://localhost:8000/mcp \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: POST"
```

Expected: HTTP 200 with CORS headers:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: *
Access-Control-Allow-Headers: *
```

---

### 4. MCP Inspector
```bash
npx @modelcontextprotocol/inspector http://localhost:8000/mcp
```

Expected: Inspector connects and shows `health_check` tool

---

## Rollout Plan

1. **Commit changes:**
   ```bash
   git add .
   git commit -m "feat: phase 1 - foundation"
   ```

2. **Push to main:**
   ```bash
   git push origin main
   ```

3. **Verify CI/CD:**
   - Check GitHub Actions: https://github.com/AxelFooley/TrackFolio/actions
   - Verify all jobs pass (lint, test, docker)
   - Confirm image pushed to GHCR

---

## Success Criteria Validation

| Criterion | How to Verify | Expected Result |
|-----------|----------------|-----------------|
| Server starts with docker compose up | `docker compose up` | Container runs, logs show "Finance MCP Server starting" |
| CI/CD builds images | GitHub Actions | Docker job completes, image pushed to GHCR |
| MCP Inspector connects | `npx @modelcontextprotocol/inspector http://localhost:8000/mcp` | Inspector shows `health_check` tool |
| No TLS errors | Tool calls | No `TLSV1_ALERT_UNRECOGNIZED_NAME` errors |
| No DNS-reblocking errors | Tool calls from Docker | No 421 errors |

---

*Plan created: 2026-03-09*
