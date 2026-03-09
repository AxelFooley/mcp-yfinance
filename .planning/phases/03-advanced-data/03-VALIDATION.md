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
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml (already configured) |
| **Quick run command** | `pytest tests/ -v -k "test_" --tb=short` |
| **Full suite command** | `pytest tests/ -v --cov=server --cov-report=term-missing --cov-fail-under=80` |
| **Estimated runtime** | ~40 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -v -k "test_" --tb=short`
- **After every plan wave:** Run `pytest tests/ -v --cov=server --cov-report=term-missing`
- **Before `/gsd:verify-work`:** Full suite must be green (80% coverage)
- **Max feedback latency:** 40 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 1 | 1 | ADV-01 | unit | `pytest tests/test_advanced.py::test_get_options_chain -v` | ✅ W0 | ⬜ pending |
| 03-01-02 | 1 | 1 | ADV-02 | unit | `pytest tests/test_advanced.py::test_get_financial_statements -v` | ✅ W0 | ⬜ pending |
| 03-02-01 | 2 | 2 | ADV-03, ADV-04 | unit | `pytest tests/test_advanced.py::test_get_dividends -v` | ✅ W0 | ⬜ pending |
| 03-02-02 | 2 | 2 | ADV-03, ADV-04 | unit | `pytest tests/test_advanced.py::test_get_earnings -v` | ✅ W0 | ⬜ pending |
| 03-02-03 | 2 | 2 | SRC-01 | unit | `pytest tests/test_search.py::test_search_symbol -v` | ✅ W0 | ⬜ pending |
| 03-02-04 | 2 | 2 | SRC-02 | unit | `pytest tests/test_search.py::test_market_overview -v` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_advanced.py` — stubs for ADV-01, ADV-02, ADV-03, ADV-04
- [ ] `tests/test_search.py` — stubs for SRC-01, SRC-02
- [ ] Update `tests/conftest.py` — add fixtures for options, financials DataFrames

**Note:** Existing infrastructure from Phase 1-2 (pytest, coverage) covers all needs.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Options with real expiry | ADV-01 | Requires valid expiry date | Call get_options_chain("AAPL") with real expiry |
| Financial statements | ADV-02 | Requires real company data | Call get_financial_statements("AAPL") |
| Market overview all indices | SRC-02 | Multiple external calls | Call get_market_overview() verify 8 indices |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 40s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
