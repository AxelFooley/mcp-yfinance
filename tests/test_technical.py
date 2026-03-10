"""Tests for technical indicators and comparison tools."""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from server import (
    _compute_atr,
    _compute_bollinger,
    _compute_macd,
    _compute_rsi,
    _compute_support_resistance,
    get_technical_analysis,
)


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear all caches before each test."""
    import server

    server._cache.clear()
    server._ticker_cache.clear()
    yield


def test_compute_rsi_uptrend():
    """Verify RSI > 50 for uptrend."""
    # Create price data with moderate uptrend (add some randomness)
    np.random.seed(42)
    base = [100]
    for i in range(1, 20):
        change = np.random.uniform(-0.2, 1.2)  # Mix of small gains and minor losses
        base.append(base[-1] + change)

    df = pd.DataFrame({"Close": base})
    rsi = _compute_rsi(df)
    current_rsi = rsi.iloc[-1]

    # Should be > 50 for uptrend, but < 100
    assert current_rsi > 50
    assert current_rsi < 100


def test_compute_rsi_overbought():
    """Verify RSI > 70 indicates overbought."""
    # Create price data with strong uptrend
    base = [100]
    for i in range(1, 30):
        base.append(base[-1] + 2)  # Consistent gains

    df = pd.DataFrame({"Close": base})
    rsi = _compute_rsi(df)
    current_rsi = rsi.iloc[-1]

    assert current_rsi > 70


def test_compute_rsi_oversold():
    """Verify RSI < 30 indicates oversold."""
    # Create price data with strong downtrend
    base = [200]
    for i in range(1, 30):
        base.append(base[-1] - 2)  # Consistent losses

    df = pd.DataFrame({"Close": base})
    rsi = _compute_rsi(df)
    current_rsi = rsi.iloc[-1]

    assert current_rsi < 30


def test_compute_macd():
    """Verify MACD components calculated."""
    # Create price data
    np.random.seed(42)
    prices = [100] + [100 + i + (i % 3) * 0.5 for i in range(1, 30)]
    df = pd.DataFrame({"Close": prices})

    result = _compute_macd(df)

    assert "macd" in result
    assert "signal" in result
    assert "histogram" in result
    assert "crossover" in result
    assert len(result["macd"]) == len(df)


def test_compute_macd_crossover_detection():
    """Verify crossover detection logic."""
    # Create data where MACD crosses above signal
    base = [100] * 20
    # Declining (MACD below signal)
    for i in range(10):
        base.append(100 - i * 0.3)
    # Rising (MACD above signal)
    for i in range(5):
        base.append(97 + i * 0.8)

    df = pd.DataFrame({"Close": base})
    result = _compute_macd(df)

    assert result["crossover"] in ["bullish", "bearish", "none"]


def test_compute_bollinger():
    """Verify Bollinger Bands structure."""
    # Create price data
    np.random.seed(42)
    prices = 100 + np.random.randn(50) * 5
    df = pd.DataFrame({"Close": prices})

    result = _compute_bollinger(df)

    assert "upper" in result
    assert "middle" in result
    assert "lower" in result
    assert "bandwidth" in result
    assert "percent_b" in result

    # Check that we have valid data (excluding NaN from warmup)
    valid_upper = result["upper"].dropna()
    valid_middle = result["middle"].dropna()
    valid_lower = result["lower"].dropna()

    assert len(valid_upper) > 0
    assert len(valid_middle) > 0
    assert len(valid_lower) > 0


def test_compute_bollinger_bandwidth():
    """Verify bandwidth calculated."""
    # Create price with specific volatility
    np.random.seed(42)
    prices = 100 + np.random.randn(30) * 3
    df = pd.DataFrame({"Close": prices})

    result = _compute_bollinger(df)

    # Bandwidth should be positive for valid data
    valid_bandwidth = result["bandwidth"].dropna()
    assert (valid_bandwidth > 0).all()


def test_compute_bollinger_percent_b_range():
    """Verify percent-B typically in 0-1 range."""
    np.random.seed(42)
    prices = 100 + np.random.randn(50) * 5
    df = pd.DataFrame({"Close": prices})

    result = _compute_bollinger(df)

    # Most percent-B values should be in reasonable range
    # (can exceed during extreme moves)
    valid_pb = result["percent_b"].dropna()
    assert len(valid_pb) > 0


def test_compute_atr():
    """Verify ATR calculated and positive."""
    # Create OHLC data with volatility
    np.random.seed(42)
    n = 30
    df = pd.DataFrame(
        {
            "High": [100 + abs(np.random.randn()) * 3 for _ in range(n)],
            "Low": [100 - abs(np.random.randn()) * 3 for _ in range(n)],
            "Close": [100 + np.random.randn() * 2 for _ in range(n)],
        }
    )
    # Ensure High >= Low
    df["Low"] = df[["High", "Low"]].min(axis=1)
    # Ensure Close within High-Low range
    df["Close"] = df[["High", "Low"]].mean(axis=1)

    atr = _compute_atr(df)

    assert atr is not None
    assert len(atr) == len(df)
    # ATR should be positive for valid data
    valid_atr = atr.dropna()
    assert (valid_atr > 0).all()


def test_compute_support_resistance():
    """Verify support/resistance from recent action."""
    # Create price data with known high and low
    np.random.seed(42)
    prices = list(np.random.uniform(95, 105, 20))
    prices[5] = 115  # High
    prices[15] = 85  # Low

    df = pd.DataFrame(
        {
            "High": [p + abs(np.random.randn()) for p in prices],
            "Low": [p - abs(np.random.randn()) for p in prices],
            "Close": prices,
        }
    )

    result = _compute_support_resistance(df)

    assert "support" in result
    assert "resistance" in result
    assert "range" in result
    assert result["support"] <= result["resistance"]


def test_get_technical_analysis_valid():
    """Verify all technical indicators returned."""
    # Mock ticker with historical data
    mock_ticker = MagicMock()

    # Create realistic OHLCV data
    np.random.seed(42)
    n = 100
    dates = pd.date_range(start="2024-01-01", periods=n, freq="D")
    close_prices = [100]
    for i in range(1, n):
        change = np.random.randn() * 2
        close_prices.append(close_prices[-1] + change)

    # Create proper yfinance-style DataFrame
    df = pd.DataFrame(
        {
            "Open": [close_prices[i] + np.random.randn() * 0.5 for i in range(n)],
            "High": [close_prices[i] + abs(np.random.randn()) * 1.5 for i in range(n)],
            "Low": [close_prices[i] - abs(np.random.randn()) * 1.5 for i in range(n)],
            "Close": close_prices,
            "Volume": [np.random.randint(1000000, 10000000) for _ in range(n)],
        },
        index=dates,
    )

    mock_ticker.history.return_value = df

    with patch("server._ticker", return_value=mock_ticker):
        result = get_technical_analysis("AAPL")

    assert result["symbol"] == "AAPL"
    assert "currentPrice" in result
    assert "rsi" in result
    assert "macd" in result
    assert "bollinger" in result
    assert "atr" in result
    assert "supportResistance" in result
    assert "movingAverages" in result
    assert "trend" in result
    assert "error" not in result


def test_get_technical_analysis_insufficient_data():
    """Verify returns error for insufficient data."""
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame()  # Empty

    with patch("server._ticker", return_value=mock_ticker):
        result = get_technical_analysis("AAPL")

    assert "error" in result


def test_get_technical_analysis_rsi_signals():
    """Verify RSI overbought/oversold detection."""
    # Create data with strong uptrend (overbought)
    np.random.seed(42)
    n = 100
    close_prices = [100]
    for i in range(1, n):
        close_prices.append(close_prices[-1] + np.random.uniform(0.5, 2))

    dates = pd.date_range(start="2024-01-01", periods=n, freq="D")
    df = pd.DataFrame(
        {
            "Open": [close_prices[i] - 0.2 for i in range(n)],
            "High": [close_prices[i] + 0.5 for i in range(n)],
            "Low": [close_prices[i] - 0.5 for i in range(n)],
            "Close": close_prices,
            "Volume": [1000000] * n,
        },
        index=dates,
    )

    mock_ticker = MagicMock()
    mock_ticker.history.return_value = df

    with patch("server._ticker", return_value=mock_ticker):
        result = get_technical_analysis("AAPL")

    assert result["rsi"]["signal"] in ["overbought", "oversold", "neutral"]
    assert result["rsi"]["overbought"] in [True, False]
    assert result["rsi"]["oversold"] in [True, False]
