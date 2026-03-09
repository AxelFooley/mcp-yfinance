---
phase: 3
slug: advanced-data
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-09
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest tests/ -v --no-cov -k "test_"` |
| **Full suite command** | `pytest tests/ -v --cov=yfinance_mcp --cov-report=term-missing` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -v --no-cov -k "test_"`
- **After every plan wave:** Run `pytest tests/ -v --cov=yfinance_mcp --cov-report=term-missing`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | ADV-01 | unit | `pytest tests/test_options.py -v` | ✅ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | ADV-02 | unit | `pytest tests/test_financials.py -v` | ✅ W0 | ⬜ pending |
| 03-02-01 | 02 | 1 | ADV-03 | unit | `pytest tests/test_dividends.py -v` | ✅ W0 | ⬜ pending |
| 03-02-02 | 02 | 1 | ADV-04 | unit | `pytest tests/test_earnings.py -v` | ✅ W0 | ⬜ pending |
| 03-02-03 | 02 | 2 | SRC-01 | unit | `pytest tests/test_search.py -v` | ✅ W0 | ⬜ pending |
| 03-02-04 | 02 | 2 | SRC-02 | unit | `pytest tests/test_market_overview.py -v` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_options.py` — stubs for get_options_chain (ADV-01)
- [ ] `tests/test_financials.py` — stubs for get_financial_statements (ADV-02)
- [ ] `tests/test_dividends.py` — stubs for get_dividend_history (ADV-03)
- [ ] `tests/test_earnings.py` — stubs for get_earnings (ADV-04)
- [ ] `tests/test_search.py` — stubs for search_symbol (SRC-01)
- [ ] `tests/test_market_overview.py` — stubs for get_market_overview (SRC-02)
- [ ] `tests/conftest.py` — shared fixtures (already exists)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| MCP Inspector tool listing | All | Requires manual inspector interaction | Run `docker compose up`, connect MCP Inspector, verify tools appear |
| Real options chain data | ADV-01 | Options data is time-sensitive, market-dependent | Call get_options_chain for AAPL during market hours, verify calls/puts returned |
| Financial statement completeness | ADV-02 | Requires manual verification of statement structure | Call get_financial_statements for MSFT, verify income/balance/cashflow all present |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
