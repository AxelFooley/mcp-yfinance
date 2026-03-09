"""Tests for advanced tools (options, financials, dividends, earnings, search)."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from server import get_financial_statements, get_options_chain


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear all caches before each test."""
    import server

    server._cache.clear()
    server._ticker_cache.clear()
    yield


def test_get_options_chain_valid():
    """Verify returns calls and puts for valid options data."""
    # Mock ticker.options and option_chain
    mock_ticker = MagicMock()
    mock_ticker.options = ["2024-03-15", "2024-03-22"]

    mock_calls_df = pd.DataFrame(
        {
            "strike": [150.0, 155.0],
            "lastPrice": [5.0, 3.0],
            "volume": [1000, 500],
        }
    )
    mock_puts_df = pd.DataFrame(
        {
            "strike": [150.0, 155.0],
            "lastPrice": [4.0, 2.0],
            "volume": [800, 400],
        }
    )

    mock_opt = MagicMock()
    mock_opt.calls = mock_calls_df
    mock_opt.puts = mock_puts_df

    mock_ticker.option_chain.return_value = mock_opt

    with patch("server._ticker", return_value=mock_ticker):
        result = get_options_chain("AAPL")

    assert result["symbol"] == "AAPL"
    assert "calls" in result
    assert "puts" in result
    assert len(result["calls"]) == 2
    assert len(result["puts"]) == 2
    assert result["availableExpirations"] == ["2024-03-15", "2024-03-22"]
    assert "error" not in result


def test_get_options_chain_no_options():
    """Verify returns error dict when no options available."""
    mock_ticker = MagicMock()
    mock_ticker.options = None

    with patch("server._ticker", return_value=mock_ticker):
        result = get_options_chain("INDEX")

    assert "error" in result
    assert "No options data available" in result["error"]


def test_get_options_chain_invalid_expiry():
    """Verify returns error with available expirations when invalid expiry requested."""
    mock_ticker = MagicMock()
    mock_ticker.options = ["2024-03-15", "2024-03-22"]

    with patch("server._ticker", return_value=mock_ticker):
        result = get_options_chain("AAPL", expiry="2024-03-01")

    assert "error" in result
    assert "not available" in result["error"]
    assert "2024-03-15" in result["error"] or "2024-03-22" in result["error"]


def test_get_financial_statements_income():
    """Verify returns income statement."""
    mock_ticker = MagicMock()

    mock_df = pd.DataFrame(
        {
            "Total Revenue": [100_000_000, 110_000_000],
            "Net Income": [20_000_000, 22_000_000],
        }
    )
    mock_ticker.income_stmt = mock_df
    mock_ticker.quarterly_income_stmt = mock_df

    with patch("server._ticker", return_value=mock_ticker):
        result = get_financial_statements("AAPL", statement_type="income", frequency="annual")

    assert result["symbol"] == "AAPL"
    assert result["statementType"] == "income"
    assert result["frequency"] == "annual"
    assert "data" in result
    assert len(result["data"]) == 2
    assert "error" not in result


def test_get_financial_statements_balance():
    """Verify returns balance sheet."""
    mock_ticker = MagicMock()

    mock_df = pd.DataFrame(
        {
            "Total Assets": [200_000_000, 210_000_000],
            "Total Liabilities": [80_000_000, 85_000_000],
        }
    )
    mock_ticker.balance_sheet = mock_df
    mock_ticker.quarterly_balance_sheet = mock_df

    with patch("server._ticker", return_value=mock_ticker):
        result = get_financial_statements("AAPL", statement_type="balance", frequency="annual")

    assert result["statementType"] == "balance"
    assert len(result["data"]) == 2


def test_get_financial_statements_cashflow():
    """Verify returns cash flow statement."""
    mock_ticker = MagicMock()

    mock_df = pd.DataFrame(
        {
            "Operating Cash Flow": [30_000_000, 32_000_000],
            "Free Cash Flow": [25_000_000, 27_000_000],
        }
    )
    mock_ticker.cashflow = mock_df
    mock_ticker.quarterly_cashflow = mock_df

    with patch("server._ticker", return_value=mock_ticker):
        result = get_financial_statements("AAPL", statement_type="cashflow", frequency="annual")

    assert result["statementType"] == "cashflow"
    assert len(result["data"]) == 2


def test_get_financial_statements_quarterly():
    """Verify quarterly frequency works."""
    mock_ticker = MagicMock()

    mock_df = pd.DataFrame(
        {
            "Total Revenue": [25_000_000, 26_000_000],
            "Net Income": [5_000_000, 5_200_000],
        }
    )
    mock_ticker.income_stmt = pd.DataFrame({"Total Revenue": [100_000_000, 110_000_000]})
    mock_ticker.quarterly_income_stmt = mock_df

    with patch("server._ticker", return_value=mock_ticker):
        result = get_financial_statements("AAPL", statement_type="income", frequency="quarterly")

    assert result["frequency"] == "quarterly"
    assert len(result["data"]) == 2


def test_get_financial_statements_invalid_type():
    """Verify returns error for invalid statement type."""
    mock_ticker = MagicMock()
    mock_ticker.income_stmt = pd.DataFrame({"Revenue": [100_000_000]})

    with patch("server._ticker", return_value=mock_ticker):
        result = get_financial_statements("AAPL", statement_type="invalid")

    assert "error" in result
    assert "Invalid statement_type" in result["error"]


def test_get_financial_statements_empty():
    """Verify returns error when statement is empty."""
    mock_ticker = MagicMock()
    mock_ticker.income_stmt = pd.DataFrame()  # Empty
    mock_ticker.balance_sheet = pd.DataFrame()
    mock_ticker.cashflow = pd.DataFrame()

    with patch("server._ticker", return_value=mock_ticker):
        result = get_financial_statements("AAPL", statement_type="income")

    assert "error" in result
    assert "No income statement available" in result["error"]
