---
phase: 4
slug: analysis
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest tests/ -v --no-cov -k "test_"` |
| **Full suite command** | `pytest tests/ -v --cov=yfinance_mcp --cov-report=term-missing` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -v --no-cov -k "test_"`
- **After every plan wave:** Run `pytest tests/ -v --cov=yfinance_mcp --cov-report=term-missing`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | TECH-01-06 | unit | `pytest tests/test_technical.py -v` | ✅ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | TECH-01-06 | unit | `pytest tests/test_technical.py::test_get_technical_analysis -v` | ✅ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | TECH-01-06 | unit | `pytest tests/test_technical.py -v --cov` | ✅ W0 | ⬜ pending |
| 04-02-01 | 02 | 2 | COMP-01 | unit | `pytest tests/test_technical.py::test_compare_stocks -v` | ✅ W0 | ⬜ pending |
| 04-02-02 | 02 | 2 | COMP-01 | unit | `pytest tests/test_technical.py -v --cov` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_technical.py` — stubs for all technical analysis tests
- [ ] `tests/conftest.py` — shared fixtures (already exists)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Technical indicator accuracy | TECH-01-06 | Requires domain knowledge | Compare calculated values with known sources (TradingView, Yahoo Finance) |
| RSI overbought/oversold signals | TECH-02 | Market-dependent verification | Test on highly volatile stock during extreme moves |
| MACD crossover timing | TECH-03 | Requires visual chart confirmation | Verify crossover aligns with price reversals |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
