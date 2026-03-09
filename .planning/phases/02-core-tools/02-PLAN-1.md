---
wave: 1
depends_on: []
files_modified:
  - server.py
autonomous: true
requirements:
  - QUAL-01
  - QUAL-02
  - QUAL-03
  - QUAL-04
  - CACHE-01
  - CACHE-02
  - CACHE-03
  - CACHE-04
  - CACHE-05
  - CACHE-06
---

# Plan 2.1: Helper Functions and Data Quality

**Phase:** 2 - Core Tools
**Wave:** 1 (autonomous)
**Goal:** Implement data quality helpers and in-memory caching infrastructure

---

## Overview

This plan implements the foundational utilities needed for Phase 2: data quality helpers (NaN handling, DataFrame serialization, Timestamp formatting) and an in-memory caching system with configurable TTL. These utilities are prerequisites for the MCP tools in Plan 2.2.

**Success Criteria:**
- `_safe()` converts NaN/Inf to None
- `_df_to_records()` converts DataFrames to list of dicts with proper serialization
- `_iso_format()` converts Timestamps to ISO strings recursively
- `_cache_get/set` implements time-based cache expiration
- `@cached` decorator provides reusable caching pattern
- Unit tests cover all helpers with 80%+ coverage

---

## Tasks

<tasks>
<task id="02-01-01">
<summary>Implement data quality helper functions</summary>
<details>
Add the following helper functions to server.py:

1. **_safe(value: Any) -> Any | None**
   - Converts pandas NaN/Inf values to JSON-compatible None
   - Use math.isnan() and math.isinf() for detection
   - Return value as-is if not a float

2. **_iso_format(value: Any) -> Any**
   - Converts pandas Timestamps to ISO 8601 strings (format="%Y-%m-%dT%H:%M:%S%z")
   - Handles nested dicts and lists recursively
   - Returns value as-is if not a Timestamp

3. **_df_to_records(df: pd.DataFrame) -> list[dict]**
   - Converts DataFrame to list of dicts using df.to_dict('records')
   - Handles empty DataFrame: return []
   - Applies _safe() and _iso_format() to all values
   - Flatten multi-index columns if present

4. **_series_to_dict(series: pd.Series) -> dict**
   - Converts Series to dict using series.to_dict()
   - Applies _safe() to all values

Import requirements: math, pandas, datetime

Location: Add these functions in server.py after the imports and before the mcp = FastMCP(...) line.
</details>
<verify>
<automated>pytest tests/test_helpers.py -v</automated>
</verify>
</task>

<task id="02-01-02">
<summary>Implement in-memory caching system</summary>
<details>
Add the following caching infrastructure to server.py:

1. **Cache storage**
   - `_cache: dict[str, tuple[Any, datetime]]` global variable

2. **_cache_key(symbol: str, data_type: str, **kwargs) -> str**
   - Generates cache key from symbol, data_type, and sorted kwargs
   - Format: "symbol:data_type:key1=value1:key2=value2"

3. **_cache_get(key: str, ttl: int) -> Any | None**
   - Returns cached value if exists and not expired
   - Deletes expired entries automatically
   - Returns None on cache miss

4. **_cache_set(key: str, value: Any, ttl: int) -> None**
   - Stores value with expiry time (now + timedelta(seconds=ttl))

5. **cached(ttl: int) decorator**
   - Decorator factory that wraps functions
   - Generates cache key from symbol + kwargs
   - Checks cache before calling function
   - Stores result after function returns

6. **clear_cache() tool**
   - @mcp.tool() decorator
   - Clears _cache dict
   - Returns "Cache cleared" message

Import requirements: datetime, timedelta, functools.wraps, typing.Any, typing.Callable

Location: Add after helper functions, before mcp = FastMCP(...).
</details>
<verify>
<automated>pytest tests/test_cache.py -v</automated>
</verify>
</task>

<task id="02-01-03">
<summary>Add _ticker() helper for yfinance Ticker reuse</summary>
<details>
Add the following function to server.py:

1. **_ticker_cache: dict[str, yf.Ticker]**
   - Module-level cache for Ticker objects

2. **_ticker(symbol: str) -> yf.Ticker**
   - Converts symbol to uppercase
   - Returns cached Ticker if exists
   - Creates new yf.Ticker and caches if not exists
   - Import: import yfinance as yf

Rationale: Reusing Ticker objects maintains yfinance session and reduces overhead.

Location: Add after caching functions, before mcp = FastMCP(...).
</details>
<verify>
<automated>pytest tests/test_helpers.py::test_ticker_cache -v</automated>
</verify>
</task>

<task id="02-01-04">
<summary>Create test stubs for Wave 0</summary>
<details>
Create the following test files:

1. **tests/__init__.py** (empty file)

2. **tests/conftest.py**
   - @pytest.fixture: mock_ticker (mock yf.Ticker with sample data)
   - @pytest.fixture: sample_df (pandas DataFrame with NaN values)
   - @pytest.fixture: sample_timestamp (pandas Timestamp)

3. **tests/test_helpers.py**
   - test_safe_nan(): Verify _safe(math.nan) returns None
   - test_safe_inf(): Verify _safe(math.inf) returns None
   - test_safe_normal(): Verify _safe(42.0) returns 42.0
   - test_iso_format_timestamp(): Converts Timestamp to ISO string
   - test_iso_format_nested(): Handles nested dicts with Timestamps
   - test_df_to_records_empty(): Returns [] for empty DataFrame
   - test_df_to_records_normal(): Converts DataFrame with NaN handling
   - test_ticker_cache(): Verifies Ticker object reuse

4. **tests/test_cache.py**
   - test_cache_get_miss(): Returns None for non-existent key
   - test_cache_get_hit(): Returns value within TTL
   - test_cache_get_expired(): Returns None after TTL
   - test_cached_decorator(): Caches function return value
   - test_cached_decorator_ttl_expiry(): Refetches after TTL
   - test_clear_cache(): Empties _cache dict
   - test_cache_key_generation(): Creates consistent keys

All tests should use unittest.mock for yfinance mocking.
</details>
<verify>
<automated>pytest tests/test_helpers.py tests/test_cache.py -v</automated>
</verify>
</task>
</tasks>

---

## Must Haves

After completing this plan:

- [ ] server.py has _safe(), _iso_format(), _df_to_records(), _series_to_dict() functions
- [ ] server.py has _cache storage, _cache_get(), _cache_set(), cached decorator
- [ ] server.py has clear_cache() MCP tool
- [ ] server.py has _ticker() helper with Ticker caching
- [ ] tests/test_helpers.py exists with 8+ test cases
- [ ] tests/test_cache.py exists with 7+ test cases
- [ ] All tests pass: pytest tests/test_helpers.py tests/test_cache.py -v
- [ ] Coverage >= 80%: pytest --cov=server --cov-report=term-missing

---

## Verification

Run after plan completion:
```bash
# Lint
ruff check .
ruff format --check .

# Tests
pytest tests/test_helpers.py tests/test_cache.py -v --cov=server --cov-report=term-missing

# Verify server still runs
python server.py --host 127.0.0.1 --port 8000 &
sleep 2
curl -X POST http://127.0.0.1:8000/mcp -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
pkill -f "python server.py"
```

Expected: tools/list returns 2 tools (health_check, clear_cache)

---

*Plan created: 2026-03-09*
