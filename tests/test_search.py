"""Tests for dividends, earnings, search, and market overview tools."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from server import get_dividend_history, get_earnings, get_market_overview, search_symbol


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear all caches before each test."""
    import server

    server._cache.clear()
    server._ticker_cache.clear()
    yield


def test_get_dividend_history_valid():
    """Verify returns dividends and yield for valid symbol."""
    mock_ticker = MagicMock()

    # Mock dividends DataFrame
    divs_df = pd.DataFrame(
        {
            "Dividends": [0.92, 0.92, 0.92, 0.92],  # 4 quarters
        },
        index=pd.to_datetime(["2024-03-01", "2023-12-01", "2023-09-01", "2023-06-01"]),
    )
    mock_ticker.dividends = divs_df

    # Mock info for current price
    mock_ticker.info = {"currentPrice": 175.0}

    with patch("server._ticker", return_value=mock_ticker):
        result = get_dividend_history("AAPL")

    assert result["symbol"] == "AAPL"
    assert "dividends" in result
    assert len(result["dividends"]) == 4
    assert result["currentPrice"] == 175.0
    assert result["annualYield"] == pytest.approx((0.92 * 4) / 175.0 * 100, rel=1e-3)
    assert "error" not in result


def test_get_dividend_history_no_dividends():
    """Verify returns empty array when no dividends."""
    mock_ticker = MagicMock()
    mock_ticker.dividends = pd.DataFrame()  # Empty
    mock_ticker.info = {}

    with patch("server._ticker", return_value=mock_ticker):
        result = get_dividend_history("NVDA")

    assert result["symbol"] == "NVDA"
    assert result["dividends"] == []
    assert result["metadata"]["count"] == 0


def test_get_earnings_valid():
    """Verify returns upcoming and historical earnings."""
    mock_ticker = MagicMock()

    # Mock earnings dates
    earnings_df = pd.DataFrame(
        {
            "EPS Estimate": [4.5, 4.2],
            "Reported EPS": [4.6, 4.1],
        },
        index=pd.to_datetime(["2024-03-31", "2023-12-31"]),
    )
    mock_ticker.earnings_dates = earnings_df

    # Mock info for upcoming earnings
    mock_ticker.info = {
        "nextEarningsDate": "2024-04-25",
        "epsForward": 4.8,
        "epsTrailingTwelveMonths": 4.6,
    }

    with patch("server._ticker", return_value=mock_ticker):
        result = get_earnings("AAPL")

    assert result["symbol"] == "AAPL"
    assert "upcoming" in result
    assert "history" in result
    assert len(result["history"]) == 2
    assert result["upcoming"]["date"] == "2024-04-25"
    assert result["upcoming"]["estimate"] == 4.8


def test_get_earnings_no_data():
    """Verify returns empty history when no earnings data."""
    mock_ticker = MagicMock()
    mock_ticker.earnings_dates = pd.DataFrame()  # Empty
    mock_ticker.info = {}

    with patch("server._ticker", return_value=mock_ticker):
        result = get_earnings("INDEX")

    assert result["symbol"] == "INDEX"
    assert result["history"] == []
    assert result["metadata"]["count"] == 0
    assert "upcoming" in result


def test_search_symbol_match():
    """Verify finds ticker by company name."""
    result = search_symbol("apple")

    assert result["query"] == "apple"
    assert len(result["matches"]) > 0
    assert any(m["symbol"] == "AAPL" for m in result["matches"])
    assert "error" not in result


def test_search_symbol_no_match():
    """Verify returns empty matches for unknown company."""
    result = search_symbol("unknown company xyz")

    assert result["query"] == "unknown company xyz"
    assert result["matches"] == []
    assert "note" in result


def test_search_symbol_direct_lookup():
    """Verify direct ticker lookup works."""
    mock_ticker = MagicMock()
    mock_ticker.info = {"longName": "Apple Inc."}

    with patch("yfinance.Ticker", return_value=mock_ticker):
        result = search_symbol("AAPL")

    assert result["query"] == "AAPL"
    assert len(result["matches"]) == 1
    assert result["matches"][0]["symbol"] == "AAPL"
    assert result["matches"][0]["name"] == "Apple Inc."


def test_get_market_overview():
    """Verify returns all 9 indices."""
    # Mock multiple index tickers
    mock_indices = {}

    for symbol in ["^GSPC", "^IXIC", "^DJI", "^VIX", "^TNX", "GC=F", "CL=F", "EURUSD=X", "BTC-USD"]:
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "regularMarketPrice": 100.0,
            "previousClose": 99.0,
        }
        mock_indices[symbol] = mock_ticker

    def mock_ticker_factory(symbol):
        return mock_indices.get(symbol, MagicMock())

    with patch("yfinance.Ticker", side_effect=mock_ticker_factory):
        result = get_market_overview()

    assert "indices" in result
    assert len(result["indices"]) == 9  # All 9 indices
    assert "S&P 500" in result["indices"]
    assert "BTC/USD" in result["indices"]
    assert "timestamp" in result
    for name, data in result["indices"].items():
        assert "value" in data or "error" in data
