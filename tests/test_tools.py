"""Tests for MCP tools."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from server import (
    _cache,
    get_historical_data,
    get_realtime_quote,
    get_stock_info,
)


@pytest.fixture
def mock_ticker_factory():
    """Factory for creating mock yfinance Ticker objects."""

    def _create(info=None, history_df=None):
        ticker = MagicMock()
        ticker.info = info or {}
        if history_df is not None:
            ticker.history.return_value = history_df
        return ticker

    return _create


def test_get_stock_info_valid(mock_ticker_factory, mock_ticker):
    """Verify return dict has all expected keys."""
    import server
    server._ticker_cache.clear()

    with patch("server._ticker", return_value=mock_ticker):
        result = get_stock_info("AAPL")

        assert result["symbol"] == "AAPL"
        assert result["companyName"] == "Test Company Inc"
        assert result["marketCap"] == 1000000000000
        assert result["sector"] == "Technology"
        assert "description" in result
        assert "error" not in result


def test_get_stock_info_uppercases_symbol(mock_ticker_factory, mock_ticker):
    """Verify symbol is uppercased even if passed lowercase."""
    import server
    server._ticker_cache.clear()

    with patch("server._ticker", return_value=mock_ticker):
        result = get_stock_info("aapl")

        assert result["symbol"] == "AAPL"


def test_get_stock_info_invalid():
    """Verify return is error dict for invalid symbol."""
    import server
    server._ticker_cache.clear()

    empty_ticker = MagicMock()
    empty_ticker.info = {}

    with patch("server._ticker", return_value=empty_ticker):
        result = get_stock_info("INVALID")

    assert "error" in result
    assert "INVALID" in result["error"]


def test_get_stock_info_exception():
    """Verify return is error dict when exception raised."""
    import server
    server._ticker_cache.clear()

    def raise_error(*args, **kwargs):
        raise Exception("Network error")

    failing_ticker = MagicMock()
    type(failing_ticker).info = property(raise_error)

    with patch("server._ticker", return_value=failing_ticker):
        result = get_stock_info("FAIL")

    assert "error" in result
    assert "FAIL" in result["error"]


def test_get_historical_data_valid():
    """Verify return dict has data and metadata keys."""
    import server
    server._ticker_cache.clear()

    df = pd.DataFrame({
        "Open": [100.0, 101.0],
        "High": [105.0, 106.0],
        "Low": [99.0, 100.0],
        "Close": [104.0, 105.0],
        "Volume": [1000000, 1100000],
    })
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = df

    with patch("server._ticker", return_value=mock_ticker):
        result = get_historical_data("AAPL", period="5d", interval="1d")

    assert result["symbol"] == "AAPL"
    assert result["period"] == "5d"
    assert result["interval"] == "1d"
    assert "data" in result
    assert len(result["data"]) == 2
    assert "metadata" in result
    assert result["metadata"]["count"] == 2
    assert "error" not in result


def test_get_historical_data_empty():
    """Verify return is error dict for empty DataFrame."""
    import server
    server._ticker_cache.clear()

    empty_df = pd.DataFrame()
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = empty_df

    with patch("server._ticker", return_value=mock_ticker):
        result = get_historical_data("AAPL", period="invalid", interval="1d")

    assert "error" in result
    assert "invalid" in result["error"]


def test_get_realtime_quote_valid(mock_ticker):
    """Verify price, change, changePercent calculated correctly."""
    import server
    server._ticker_cache.clear()

    with patch("server._ticker", return_value=mock_ticker):
        result = get_realtime_quote("AAPL")

        assert result["symbol"] == "AAPL"
        assert result["price"] == 150.0
        assert result["change"] == 5.0  # 150 - 145
        assert abs(result["changePercent"] - 3.45) < 0.1  # (150/145 - 1) * 100
        assert result["volume"] == 50000000
        assert isinstance(result["timestamp"], str)
        assert "error" not in result


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear all caches before each test."""
    import server
    server._cache.clear()
    server._ticker_cache.clear()
    yield


def test_get_realtime_quote_market_closed():
    """Verify return is error dict when market closed."""
    closed_ticker = MagicMock()
    closed_ticker.info = {"regularMarketPrice": None}

    with patch("server._ticker", return_value=closed_ticker):
        result = get_realtime_quote("AAPL")

        assert "error" in result
        assert "market closed" in result["error"].lower()


def test_caching_behavior(mock_ticker):
    """Verify second call returns cached data."""
    import server

    # Clear cache first
    server._cache.clear()
    server._ticker_cache.clear()

    with patch("server._ticker", return_value=mock_ticker):
        # First call - should hit yfinance
        result1 = get_stock_info("AAPL")

        # Check cache was populated
        cache_keys = list(server._cache.keys())
        assert len(cache_keys) > 0
        assert "AAPL" in cache_keys[0]

        # Second call - should use cache
        result2 = get_stock_info("AAPL")

        assert result1 == result2

    # Cleanup
    server._cache.clear()


def test_cache_expiry():
    """Verify cache expires after TTL."""
    import server
    import time

    server._cache.clear()
    server._ticker_cache.clear()

    # Create a function with short TTL
    @server.cached(ttl=1)
    def test_func(symbol: str) -> str:
        return f"result_{symbol}_{time.time()}"

    # First call
    result1 = test_func("AAPL")
    time.sleep(0.5)

    # Cache hit
    result2 = test_func("AAPL")
    assert result1 == result2

    # Wait for expiry
    time.sleep(0.6)

    # Cache miss - should return different result
    result3 = test_func("AAPL")
    assert result2 != result3

    # Cleanup
    server._cache.clear()
