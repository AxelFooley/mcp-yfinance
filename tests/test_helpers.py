"""Tests for helper functions."""

import math

import pandas as pd

from server import _df_to_records, _iso_format, _safe, _series_to_dict, _ticker


def test_safe_nan():
    """Verify _safe(math.nan) returns None."""
    assert _safe(math.nan) is None


def test_safe_inf():
    """Verify _safe(math.inf) returns None."""
    assert _safe(math.inf) is None
    assert _safe(-math.inf) is None


def test_safe_normal():
    """Verify _safe(42.0) returns 42.0."""
    assert _safe(42.0) == 42.0
    assert _safe("string") == "string"
    assert _safe(None) is None


def test_iso_format_timestamp(sample_timestamp):
    """Verify Timestamp converts to ISO string."""
    result = _iso_format(sample_timestamp)
    assert isinstance(result, str)
    assert "2024-01-15" in result


def test_iso_format_nested():
    """Verify handles nested dicts with Timestamps."""
    ts = pd.Timestamp("2024-01-15")
    nested = {"outer": {"inner": ts, "value": 42}, "list": [ts, 1, 2]}
    result = _iso_format(nested)
    assert isinstance(result["outer"]["inner"], str)
    assert isinstance(result["list"][0], str)


def test_df_to_records_empty():
    """Verify returns [] for empty DataFrame."""
    df = pd.DataFrame()
    assert _df_to_records(df) == []


def test_df_to_records_normal(sample_df):
    """Verify converts DataFrame with NaN handling."""
    result = _df_to_records(sample_df)
    assert len(result) == 5
    assert result[2]["Open"] is None  # NaN converted to None
    assert result[0]["Open"] == 100.0
    assert isinstance(result[0]["Date"], str)


def test_series_to_dict():
    """Verify Series converts to dict with NaN handling."""
    s = pd.Series([1.0, math.nan, 3.0], index=["a", "b", "c"])
    result = _series_to_dict(s)
    assert result == {"a": 1.0, "b": None, "c": 3.0}


def test_ticker_cache(monkeypatch):
    """Verify Ticker object reuse."""

    # Mock yfinance.Ticker
    class MockTicker:
        def __init__(self, symbol):
            self.symbol = symbol

    monkeypatch.setattr("server.yf.Ticker", MockTicker)

    # Clear cache first
    import server

    server._ticker_cache.clear()

    # First call creates new Ticker
    t1 = _ticker("AAPL")
    # Second call returns cached Ticker
    t2 = _ticker("AAPL")
    # Different symbol creates new Ticker
    t3 = _ticker("MSFT")

    assert t1 is t2
    assert t1 is not t3
    assert t1.symbol == "AAPL"
    assert t3.symbol == "MSFT"
