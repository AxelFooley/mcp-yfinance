# Pitfalls Research: Finance MCP Server

**Research Date:** 2026-03-09
**Reference:** https://github.com/akshatbindal/finance-mcp-server

---

## Critical Pitfalls (Must Avoid)

### 1. yfinance TLS/SNI Error

**Description:** Yahoo Finance changed their SSL/SNI configuration in early 2025. Older yfinance versions (<1.2.0) fail with `TLSV1_ALERT_UNRECOGNIZED_NAME` error.

**Warning Signs:**
- Tool calls return "Failed to perform"
- Logs show `curl: (35) TLS connect error`
- Error mentions `TLSV1_ALERT_UNRECOGNIZED_NAME`

**Prevention Strategy:**
```python
# requirements.txt
yfinance>=1.2.0  # Floor requirement, not pinned
```

**Which Phase:** Phase 1 (Foundation) - Pin correct version before any development

**Confidence:** High - This is a known issue with a known fix

**Reference:** https://github.com/ranaroussi/yfinance/releases

---

### 2. Wrong MCP Package Import

**Description:** Using the third-party `fastmcp` PyPI package instead of `mcp.server.fastmcp` from the official MCP SDK. This causes import conflicts and API incompatibilities.

**Warning Signs:**
- `import fastmcp` works but APIs don't match documentation
- Package manager shows both `mcp` and `fastmcp` installed
- AttributeError when accessing `FastMCP` methods

**Prevention Strategy:**
```python
# CORRECT
from mcp.server.fastmcp import FastMCP

# WRONG
import fastmcp  # Third-party package, abandoned
```

**requirements.txt:**
```txt
mcp[cli]>=1.6.0  # Official SDK
# Do NOT add: fastmcp
```

**Which Phase:** Phase 1 (Foundation) - Setup correct imports

**Confidence:** High - Clear documentation on official MCP SDK

---

### 3. CORS Preflight Blocking MCP Inspector

**Description:** MCP Inspector (browser-based) sends OPTIONS preflight requests. Without CORS middleware, these return 405 Method Not Allowed, blocking the Inspector.

**Warning Signs:**
- MCP Inspector shows "Connection failed"
- Browser console shows CORS errors
- curl POST works but browser doesn't

**Prevention Strategy:**
```python
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

app = Starlette(
    routes=[Mount("/", app=mcp.streamable_http_app())],
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
```

**Which Phase:** Phase 1 (Foundation) - Add CORS middleware to server initialization

**Confidence:** High - Standard Starlette pattern

---

### 4. DNS-Rebinding Protection Blocking Docker

**Description:** FastMCP auto-enables DNS-rebinding protection when constructed with default host. This blocks connections from Docker bridge IPs (172.16.x.x) with HTTP 421 errors.

**Warning Signs:**
- Container logs show "421 Misdirected Request"
- Connections work locally (localhost) but fail from Docker
- Claude Desktop can list tools but tool calls fail

**Prevention Strategy:**
```python
from mcp.server.transport_security import TransportSecuritySettings

mcp = FastMCP(
    name="Finance MCP Server",
    instructions="...",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False  # CRITICAL
    )
)
```

**Which Phase:** Phase 1 (Foundation) - Set at FastMCP construction time

**Confidence:** High - Settings must be applied at construction, cannot be changed later

---

### 5. Starlette Routes Assignment Error

**Description:** Attempting to set `app.routes` after Starlette construction raises `AttributeError: property 'routes' of 'Starlette' object has no setter`.

**Warning Signs:**
- Server crashes on startup
- Error mentions routes property
- Code tries to modify app.routes after initialization

**Prevention Strategy:**
```python
# CORRECT - Pass routes to constructor
app = Starlette(
    routes=[Mount("/", app=mcp_app)],
    middleware=[...]
)

# WRONG - Try to set routes after construction
app = Starlette(middleware=[...])
app.routes = [Mount("/", app=mcp_app)]  # AttributeError!
```

**Which Phase:** Phase 1 (Foundation) - Correct Starlette initialization

**Confidence:** High - Well-documented Starlette API

---

### 6. Missing uvicorn Dependency

**Description:** Using `mcp.streamable_http_app()` directly requires uvicorn, but it's not bundled with mcp package. This causes ModuleNotFoundError on startup.

**Warning Signs:**
- Server crashes with `ModuleNotFoundError: No module named 'uvicorn'`
- Works in local venv but fails in Docker

**Prevention Strategy:**
```txt
# requirements.txt
mcp[cli]>=1.6.0
uvicorn>=0.30.0  # Explicit dependency
```

**Which Phase:** Phase 1 (Foundation) - Add to requirements.txt

**Confidence:** High - Documented in MCP SDK migration guide

---

## Common Pitfalls (Annoying but Not Critical)

### 7. Wrong Middleware Format

**Description:** Passing middleware as list of tuples instead of Middleware objects causes `ValueError: not enough values to unpack (expected 3, got 2)`.

**Warning Signs:**
- Server crashes on first request
- Error mentions middleware unpacking
- Error trace shows build_middleware_stack

**Prevention Strategy:**
```python
# CORRECT - Use Middleware class
from starlette.middleware import Middleware

middleware=[
    Middleware(CORSMiddleware, allow_origins=["*"])
]

# WRONG - Tuple format
middleware=[
    (CORSMiddleware, {"allow_origins": ["*"]})  # ValueError!
]
```

**Which Phase:** Phase 1 (Foundation) - Correct middleware format

**Confidence:** High - Starlette API documentation

---

### 8. Calling streamable_http_app as Property

**Description:** `mcp.streamable_http_app` is a method, not a property. Calling it without `()` causes TypeError.

**Warning Signs:**
- TypeError: 'method' object is not callable
- Server crashes during initialization

**Prevention Strategy:**
```python
# CORRECT - Call the method
mcp_app = mcp.streamable_http_app()

# WRONG - Access as property
mcp_app = mcp.streamable_http_app  # Wrong type
```

**Which Phase:** Phase 1 (Foundation) - Correct method invocation

**Confidence:** High - FastMCP API documentation

---

### 9. Cache Thread Safety Issues

**Description:** Global `_CACHE` dict accessed concurrently by multiple requests can cause race conditions and data corruption.

**Warning Signs:**
- Intermittent cache misses
- Corrupted cache data
- KeyError exceptions on cache access

**Prevention Strategy:**
```python
import threading

_CACHE_LOCK = threading.Lock()

def _cache_set(key: str, value: Any) -> None:
    with _CACHE_LOCK:
        _CACHE[key] = value
        _CACHE_TS[key] = time.time()

def _cache_get(key: str, ttl: int) -> Any | None:
    with _CACHE_LOCK:
        if key in _CACHE and (time.time() - _CACHE_TS.get(key, 0)) < ttl:
            return _CACHE[key]
    return None
```

**Alternative:** Use `functools.lru_cache` with maxsize and TTL wrapper

**Which Phase:** Phase 2 (Core Tools) - Add when implementing cache

**Confidence:** Medium - Single-threaded uvicorn may not need this, but good practice

---

### 10. Docker Build Cache Using Old Dependencies

**Description:** Docker layer caching can cause old yfinance version (<1.2.0) to persist even after requirements.txt is updated.

**Warning Signs:**
- requirements.txt shows yfinance>=1.2.0
- But container still has TLS error
- `pip list` in container shows old version

**Prevention Strategy:**
```bash
# Always rebuild with --no-cache when updating dependencies
docker compose build --no-cache

# Or use specific cache busting in Dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```

**Which Phase:** Ongoing - Be aware during deployment

**Confidence:** High - Common Docker issue

---

## Future Considerations (Not for v1)

### 11. Yahoo Finance Rate Limiting

**Description:** Yahoo Finance may rate-limit excessive requests. Currently yfinance handles this internally, but aggressive use could trigger blocks.

**Warning Signs:**
- HTTP 429 responses
- Sudden increase in failed requests
- IP temporarily blocked

**Prevention Strategy:**
- Implement rate limiting at application level
- Use cache to reduce redundant requests
- Add exponential backoff for retries
- Consider rate limit headers if Yahoo provides them

**Which Phase:** Phase 5 (Future) - Not needed for MVP

**Confidence:** Medium - yfinance handles this, but undefined behavior

---

### 12. Memory Leaks from Unclosed Sessions

**Description:** Creating many `yf.Ticker` objects without releasing them could cause memory leaks over time.

**Warning Signs:**
- Memory usage grows over time
- Container OOM killed after hours/days
- Profiling shows increasing object count

**Prevention Strategy:**
```python
# Reuse Ticker objects when possible
_ticker_cache: dict[str, yf.Ticker] = {}

def _ticker(symbol: str) -> yf.Ticker:
    if symbol not in _ticker_cache:
        _ticker_cache[symbol] = yf.Ticker(symbol)
    return _ticker_cache[symbol]
```

**Which Phase:** Phase 5 (Future) - Not needed for MVP, good for production

**Confidence:** Low - Unclear if yf.Ticker holds network resources

---

## Pitfall Summary

| Pitfall | Severity | Phase | Confidence |
|---------|----------|-------|------------|
| 1. yfinance TLS error | Critical | 1 | High |
| 2. Wrong MCP import | Critical | 1 | High |
| 3. CORS blocking Inspector | Critical | 1 | High |
| 4. DNS-rebinding blocking | Critical | 1 | High |
| 5. Starlette routes error | Critical | 1 | High |
| 6. Missing uvicorn | Critical | 1 | High |
| 7. Middleware format | High | 1 | High |
| 8. streamable_http_app call | High | 1 | High |
| 9. Cache thread safety | Medium | 2 | Medium |
| 10. Docker build cache | Medium | Ongoing | High |
| 11. Rate limiting | Low | 5 | Medium |
| 12. Memory leaks | Low | 5 | Low |

---

*Last updated: 2026-03-09*
