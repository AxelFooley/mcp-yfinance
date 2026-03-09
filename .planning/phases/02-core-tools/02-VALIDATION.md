---
phase: 2
slug: core-tools
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-09
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml (already configured in Phase 1) |
| **Quick run command** | `pytest tests/ -v -k "test_" --tb=short` |
| **Full suite command** | `pytest tests/ -v --cov=server --cov-report=term-missing --cov-fail-under=80` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -v -k "test_" --tb=short`
- **After every plan wave:** Run `pytest tests/ -v --cov=server --cov-report=term-missing`
- **Before `/gsd:verify-work`:** Full suite must be green (80% coverage)
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 1 | 1 | QUAL-01, QUAL-02 | unit | `pytest tests/test_helpers.py -v` | ✅ W0 | ⬜ pending |
| 02-01-02 | 1 | 1 | CACHE-01 through CACHE-06 | unit | `pytest tests/test_cache.py -v` | ✅ W0 | ⬜ pending |
| 02-02-01 | 2 | 2 | DATA-03, ERR-01, ERR-02 | unit | `pytest tests/test_tools.py::test_get_stock_info -v` | ✅ W0 | ⬜ pending |
| 02-02-02 | 2 | 2 | DATA-02, QUAL-03 | unit | `pytest tests/test_tools.py::test_get_historical_data -v` | ✅ W0 | ⬜ pending |
| 02-02-03 | 2 | 2 | DATA-01, ERR-03 | unit | `pytest tests/test_tools.py::test_get_realtime_quote -v` | ✅ W0 | ⬜ pending |
| 02-02-04 | 2 | 3 | All Phase 2 | integration | `pytest tests/test_integration.py -v` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_helpers.py` — stubs for QUAL-01, QUAL-02 (_safe, _df_to_records, _series_to_dict, _iso_format)
- [ ] `tests/test_cache.py` — stubs for CACHE-01 through CACHE-06 (_cache_get, _cache_set, clear_cache, @cached decorator)
- [ ] `tests/test_tools.py` — stubs for DATA-01, DATA-02, DATA-03, ERR-01, ERR-02, ERR-03
- [ ] `tests/conftest.py` — shared fixtures (mock yfinance Ticker, sample DataFrames)
- [ ] `tests/__init__.py` — empty file for pytest package discovery

**Note:** Existing infrastructure from Phase 1 (pytest, coverage) covers all needs.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| MCP Inspector connects and lists tools | MCP-05 | Requires browser interaction | Run `npx @modelcontextprotocol/inspector http://localhost:8000/mcp` and verify all 4 tools appear |
| CORS headers present | MCP-03 | Requires HTTP request from non-local origin | Run `curl -i -X OPTIONS http://localhost:8000/mcp -H "Origin: http://localhost:5173"` |
| Real data from Yahoo Finance | DATA-01, DATA-02, DATA-03 | Integration with external API | Call tools with real symbols (AAPL, MSFT) and verify data accuracy |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
