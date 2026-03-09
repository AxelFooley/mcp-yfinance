---
wave: 3
depends_on:
  - "02-PLAN-2"
files_modified:
  - tests/
autonomous: false
requirements:
  - ALL_PHASE_2
---

# Plan 2.3: Integration Testing and Validation

**Phase:** 2 - Core Tools
**Wave:** 3 (depends on Wave 2)
**Goal:** End-to-end testing and manual validation of Phase 2 implementation

---

## Overview

This plan validates the complete Phase 2 implementation through integration tests and manual verification. It ensures all three MCP tools work correctly together, caching behaves as expected, and the server integrates properly with MCP Inspector.

**Success Criteria:**
- Integration tests pass with real Yahoo Finance data
- MCP Inspector connects and lists all tools
- CORS headers present for browser compatibility
- Cache works correctly (hits, misses, expiry)
- All 11 Phase 2 requirements validated

---

## Tasks

<tasks>
<task id="02-03-01">
<summary>Create integration tests</summary>
<details>
Create tests/test_integration.py with end-to-end tests:

1. **test_tools_list()**
   - Start server in subprocess
   - Call tools/list via MCP protocol
   - Verify 5 tools returned

2. **test_get_stock_info_real()**
   - Call get_stock_info with "AAPL"
   - Verify response structure
   - Verify companyName is "Apple Inc."
   - Verify marketCap > 0

3. **test_get_historical_data_real()**
   - Call get_historical_data with "AAPL", period="1mo"
   - Verify data array has 20+ entries
   - Verify OHLCV columns present
   - Verify dates are ISO strings

4. **test_get_realtime_quote_real()**
   - Call get_realtime_quote with "AAPL"
   - Verify price > 0
   - Verify change is not None
   - Verify timestamp is recent

5. **test_cache_behavior()**
   - Call get_stock_info("AAPL") twice
   - Measure time difference (< 50ms for second call)
   - Verify cache hit

6. **test_cache_expiry()**
   - Call get_stock_info with low TTL
   - Sleep past TTL
   - Verify cache miss (refetch)

7. **test_invalid_symbol_error()**
   - Call get_stock_info("INVALIDSYMBOL123")
   - Verify error dict returned
   - Verify error message is informative

8. **test_clear_cache()**
   - Call tools to populate cache
   - Call clear_cache()
   - Verify subsequent calls fetch fresh data

Use subprocess to start server for real HTTP calls.
Mark as integration tests (use @pytest.mark.integration).
Skip in CI if no network access (use pytest.mark.skipif).
</details>
<verify>
<automated>pytest tests/test_integration.py -v -m integration</automated>
</verify>
</task>

<task id="02-03-02">
<summary>Manual MCP Inspector verification</summary>
<details>
Manual verification steps:

1. **Start server:**
   ```bash
   docker compose up --build
   ```

2. **Open MCP Inspector:**
   ```bash
   npx @modelcontextprotocol/inspector http://localhost:8000/mcp
   ```

3. **Verify tools listed:**
   - health_check
   - clear_cache
   - get_stock_info
   - get_historical_data
   - get_realtime_quote

4. **Test get_stock_info:**
   - Enter "AAPL" as symbol
   - Verify response includes companyName, marketCap, sector, etc.
   - Verify all values are numbers or strings (no NaN)

5. **Test get_historical_data:**
   - Enter symbol="AAPL", period="5d", interval="1d"
   - Verify data array has 5 entries
   - Verify Date, Open, High, Low, Close, Volume columns

6. **Test get_realtime_quote:**
   - Enter "AAPL"
   - Verify price, change, changePercent present
   - Verify changePercent matches (price/previousClose - 1) * 100

7. **Test error handling:**
   - Enter invalid symbol "INVALID"
   - Verify error message returned (not crash)

8. **Verify CORS:**
   - Check browser network tab for OPTIONS request
   - Verify Access-Control-Allow-Origin: * header present

Document results in .planning/phases/02-core-tools/02-MANUAL-TEST.md
</details>
<verify>
<manual>Run MCP Inspector and test all tools manually</manual>
</verify>
</task>

<task id="02-03-03">
<summary>Verify all Phase 2 requirements</summary>
<details>
Create a requirements traceability verification:

For each of the 11 requirements, create a test or verification:

1. **DATA-01** (real-time quotes): test_get_realtime_quote_real()
2. **DATA-02** (historical data): test_get_historical_data_real()
3. **DATA-03** (company info): test_get_stock_info_real()
4. **QUAL-01** (NaN handling): test_safe_nan(), integration test with real data
5. **QUAL-02** (Timestamp formatting): test_iso_format_timestamp()
6. **QUAL-03** (empty DataFrame): test_get_historical_data_empty()
7. **QUAL-04** (column normalization): test_df_to_records_multiindex()
8. **CACHE-01** (in-memory cache): test_cache_behavior()
9. **CACHE-02** (30s TTL): test_realtime_quote_cached(), verify TTL=30
10. **CACHE-03** (60s TTL): test_historical_data_cached(), verify TTL=60
11. **CACHE-04** (300s TTL): test_stock_info_cached(), verify TTL=300
12. **CACHE-05** (1hr TTL - NOT in Phase 2): Skip (financial statements are Phase 3)
13. **CACHE-06** (clear_cache): test_clear_cache()
14. **ERR-01** (exception handling): test_exception_returns_error_dict()
15. **ERR-02** (invalid symbol): test_invalid_symbol_error()
16. **ERR-03** (error logging): Verify logger.error called in exceptions

Update VALIDATION.md with all tests passing.
</details>
<verify>
<automated>pytest tests/ -v --cov=server --cov-fail-under=80</automated>
</verify>
</task>

<task id="02-03-04">
<summary>Update STATE.md and create SUMMARY</summary>
<details>
1. Update .planning/STATE.md:
   - Change Current Phase to "Phase 2 - Complete"
   - Add Phase 2 to progress table with 100%
   - Update overall progress to 22% (2 of 9 plans)
   - Update Recent Activity with Phase 2 completion
   - Update Next Steps to Phase 3

2. Create .planning/phases/02-core-tools/02-SUMMARY.md:
   ```markdown
   # Phase 2 Summary: Core Tools

   **Completed:** 2026-03-09
   **Plans:** 3 (Helper Functions, Core Tools, Integration Testing)

   ## What Was Built

   - Data quality helpers: _safe(), _iso_format(), _df_to_records(), _series_to_dict()
   - In-memory caching: _cache_get/set, @cached decorator, clear_cache tool
   - MCP tools: get_stock_info, get_historical_data, get_realtime_quote
   - Test suite: 25+ unit tests, 8+ integration tests

   ## Requirements Satisfied

   All 11 Phase 2 requirements validated:
   - DATA-01, DATA-02, DATA-03: Core market data tools working
   - QUAL-01, QUAL-02, QUAL-03, QUAL-04: Data quality handling verified
   - CACHE-01 through CACHE-06: Caching implemented with correct TTLs
   - ERR-01, ERR-02, ERR-03: Error handling graceful

   ## Test Results

   - Unit tests: 25 passed
   - Integration tests: 8 passed
   - Coverage: 85%
   - MCP Inspector: All tools discoverable and working

   ## Issues Encountered

   - None (implementation went smoothly)

   ## Next Phase

   Phase 3: Advanced Data (Options, Financials, Dividends, Earnings, Search)
   ```
</details>
<verify>
<automated>git status shows clean working directory</automated>
</verify>
</task>
</tasks>

---

## Must Haves

After completing this plan:

- [ ] tests/test_integration.py exists with 8+ integration tests
- [ ] All integration tests pass (network-dependent, skip if offline)
- [ ] MCP Inspector connects and lists all 5 tools
- [ ] Manual testing documented in 02-MANUAL-TEST.md
- [ ] All 11 Phase 2 requirements have passing tests
- [ ] pytest tests/ -v --cov=server passes with >= 80% coverage
- [ ] STATE.md updated with Phase 2 complete
- [ ] 02-SUMMARY.md created
- [ ] git status shows clean directory (all committed)

---

## Verification

Run after plan completion:
```bash
# Full test suite
pytest tests/ -v --cov=server --cov-report=term-missing --cov-fail-under=80

# Lint
ruff check .
ruff format --check .

# Docker build
docker compose up --build
docker compose logs -f

# In another terminal: MCP Inspector
npx @modelcontextprotocol/inspector http://localhost:8000/mcp

# Verify tools manually, then Ctrl+C to stop
```

Expected: All tests green, Docker container runs, MCP Inspector shows 5 tools, manual testing successful

---

*Plan created: 2026-03-09*
