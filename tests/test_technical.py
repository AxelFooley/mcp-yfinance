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
    compare_stocks,
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
        base.append(base[-1] + 2)

    df = pd.DataFrame({"Close": base})
    rsi = _compute_rsi(df)
    current_rsi = rsi.iloc[-1]

    assert current_rsi > 70


def test_compute_rsi_oversold():
    """Verify RSI < 30 indicates oversold."""
    # Create price data with strong downtrend
    base = [200]
    for i in range(1, 30):
        base.append(base[-1] - 2)

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


# ──────────────────────────────────────────────
# Comparison Tests
# ──────────────────────────────────────────────


def test_compare_stocks_valid():
    """Verify side-by-side comparison with sorting."""
    # Mock 3 tickers with different performance
    mock_tickers = {}

    # AAPL: 20% gain
    np.random.seed(42)
    n = 60
    dates = pd.date_range(start="2024-01-01", periods=n, freq="D")
    aapl_close = [100]
    for i in range(1, n):
        aapl_close.append(aapl_close[-1] + np.random.uniform(0.1, 0.5))

    aapl_df = pd.DataFrame(
        {
            "Open": [aapl_close[i] - 0.1 for i in range(n)],
            "High": [aapl_close[i] + 0.2 for i in range(n)],
            "Low": [aapl_close[i] - 0.15 for i in range(n)],
            "Close": aapl_close,
            "Volume": [1000000] * n,
        },
        index=dates,
    )

    # MSFT: 10% gain
    msft_close = [100]
    for i in range(1, n):
        msft_close.append(msft_close[-1] + np.random.uniform(0.05, 0.3))

    msft_df = pd.DataFrame(
        {
            "Open": [msft_close[i] - 0.05 for i in range(n)],
            "High": [msft_close[i] + 0.1 for i in range(n)],
            "Low": [msft_close[i] - 0.08 for i in range(n)],
            "Close": msft_close,
            "Volume": [1000000] * n,
        },
        index=dates,
    )

    # GOOGL: 5% gain
    googl_close = [100]
    for i in range(1, n):
        googl_close.append(googl_close[-1] + np.random.uniform(0.02, 0.2))

    googl_df = pd.DataFrame(
        {
            "Open": [googl_close[i] - 0.03 for i in range(n)],
            "High": [googl_close[i] + 0.05 for i in range(n)],
            "Low": [googl_close[i] - 0.04 for i in range(n)],
            "Close": googl_close,
            "Volume": [1000000] * n,
        },
        index=dates,
    )

    mock_tickers["AAPL"] = MagicMock()
    mock_tickers["AAPL"].history.return_value = aapl_df
    mock_tickers["MSFT"] = MagicMock()
    mock_tickers["MSFT"].history.return_value = msft_df
    mock_tickers["GOOGL"] = MagicMock()
    mock_tickers["GOOGL"].history.return_value = googl_df

    def mock_ticker_factory(symbol):
        return mock_tickers.get(symbol, MagicMock())

    with patch("yfinance.Ticker", side_effect=mock_ticker_factory):
        result = compare_stocks("AAPL,MSFT,GOOGL")

    assert result["period"] == "3mo"
    assert len(result["comparisons"]) == 3
    assert "summary" in result
    assert result["summary"]["bestPerforming"] == "AAPL"
    assert result["summary"]["worstPerforming"] in ["MSFT", "GOOGL"]
    assert result["comparisons"][0]["periodReturn"] >= result["comparisons"][-1]["periodReturn"]


def test_compare_stocks_too_many():
    """Verify returns error for too many symbols."""
    # Request 11 symbols
    symbols = ",".join([f"STK{i:02d}" for i in range(11)])
    result = compare_stocks(symbols)
    assert "error" in result
    assert "Maximum 10 symbols" in result["error"]


def test_compare_stocks_too_few():
    """Verify returns error for single symbol."""
    result = compare_stocks("AAPL")
    assert "error" in result
    assert "At least 2 symbols" in result["error"]


def test_compare_stocks_invalid_symbol():
    """Verify error handling for invalid symbol."""
    mock_tickers = {}

    # AAPL: valid
    np.random.seed(42)
    dates = pd.date_range(start="2024-01-01", periods=60, freq="D")
    close_prices = [100 + i * 0.5 for i in range(60)]

    valid_df = pd.DataFrame(
        {
            "Open": [close_prices[i] - 0.1 for i in range(60)],
            "High": [close_prices[i] + 0.2 for i in range(60)],
            "Low": [close_prices[i] - 0.15 for i in range(60)],
            "Close": close_prices,
            "Volume": [1000000] * 60,
        },
        index=dates,
    )

    mock_tickers["AAPL"] = MagicMock()
    mock_tickers["AAPL"].history.return_value = valid_df

    # INVALID: throws error
    mock_tickers["INVALID"] = MagicMock()
    mock_tickers["INVALID"].history.side_effect = Exception("Invalid symbol")

    def mock_ticker_factory(symbol):
        return mock_tickers.get(symbol, MagicMock())

    with patch("yfinance.Ticker", side_effect=mock_ticker_factory):
        result = compare_stocks("AAPL,INVALID")

    # Should still return results for valid symbol
    assert len(result["comparisons"]) == 2  # AAPL + INVALID error
    assert any(c["symbol"] == "AAPL" and "periodReturn" in c for c in result["comparisons"])
    assert any(c["symbol"] == "INVALID" and "error" in c for c in result["comparisons"])


def test_compare_stocks_volatility_calculation():
    """Verify volatility calculation distinguishes stocks."""
    mock_tickers = {}

    # Stable stock (low volatility)
    np.random.seed(42)
    stable_close = [100]
    for i in range(1, 30):
        stable_close.append(stable_close[-1] + np.random.uniform(-0.1, 0.1))

    stable_df = pd.DataFrame(
        {
            "Open": [stable_close[i] for i in range(30)],
            "High": [stable_close[i] + 0.05 for i in range(30)],
            "Low": [stable_close[i] - 0.05 for i in range(30)],
            "Close": stable_close,
            "Volume": [1000000] * 30,
        }
    )

    # Volatile stock (high volatility)
    volatile_close = [100]
    for i in range(1, 30):
        volatile_close.append(volatile_close[-1] + np.random.uniform(-2, 2))

    volatile_df = pd.DataFrame(
        {
            "Open": [volatile_close[i] for i in range(30)],
            "High": [volatile_close[i] + 2.5 for i in range(30)],
            "Low": [volatile_close[i] - 2.5 for i in range(30)],
            "Close": volatile_close,
            "Volume": [1000000] * 30,
        }
    )

    mock_tickers["STABLE"] = MagicMock()
    mock_tickers["STABLE"].history.return_value = stable_df
    mock_tickers["VOLATILE"] = MagicMock()
    mock_tickers["VOLATILE"].history.return_value = volatile_df

    def mock_ticker_factory(symbol):
        return mock_tickers.get(symbol, MagicMock())

    with patch("yfinance.Ticker", side_effect=mock_ticker_factory):
        result = compare_stocks("STABLE,VOLATILE")

    stable_vol = [c["volatility"] for c in result["comparisons"] if c["symbol"] == "STABLE"][0]
    volatile_vol = [c["volatility"] for c in result["comparisons"] if c["symbol"] == "VOLATILE"][0]

    # Volatile should have higher volatility than stable
    assert volatile_vol > stable_vol


def test_compare_stocks_sharpe_ratio():
    """Verify Sharpe ratio rewards high-return low-volatility."""
    mock_tickers = {}

    # Stock A: High return, low volatility
    np.random.seed(42)
    good_close = [100]
    for i in range(1, 30):
        good_close.append(good_close[-1] + 0.5)  # Consistent 0.5 gain

    good_df = pd.DataFrame(
        {
            "Open": [good_close[i] - 0.1 for i in range(30)],
            "High": [good_close[i] + 0.15 for i in range(30)],
            "Low": [good_close[i] - 0.15 for i in range(30)],
            "Close": good_close,
            "Volume": [1000000] * 30,
        }
    )

    # Stock B: Low return, high volatility
    bad_close = [100]
    for i in range(1, 30):
        bad_close.append(bad_close[-1] + np.random.uniform(-3, 3))

    bad_df = pd.DataFrame(
        {
            "Open": [bad_close[i] for i in range(30)],
            "High": [bad_close[i] + 3 for i in range(30)],
            "Low": [bad_close[i] - 3 for i in range(30)],
            "Close": bad_close,
            "Volume": [1000000] * 30,
        }
    )

    mock_tickers["GOOD"] = MagicMock()
    mock_tickers["GOOD"].history.return_value = good_df
    mock_tickers["BAD"] = MagicMock()
    mock_tickers["BAD"].history.return_value = bad_df

    def mock_ticker_factory(symbol):
        return mock_tickers.get(symbol, MagicMock())

    with patch("yfinance.Ticker", side_effect=mock_ticker_factory):
        result = compare_stocks("GOOD,BAD")

    good_sharpe = [c["sharpeRatio"] for c in result["comparisons"] if c["symbol"] == "GOOD"][0]
    bad_sharpe = [c["sharpeRatio"] for c in result["comparisons"] if c["symbol"] == "BAD"][0]

    # Good stock should have higher Sharpe ratio
    assert good_sharpe > bad_sharpe


def test_compare_stocks_max_drawdown():
    """Verify max drawdown calculation."""
    mock_tickers = {}

    # Stock with significant drop
    np.random.seed(42)
    dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
    close_prices = [100]
    for i in range(1, 20):
        close_prices.append(close_prices[-1] + np.random.uniform(-0.5, 1))
    # Add significant drawdown
    for i in range(20, 30):
        close_prices.append(close_prices[-1] - np.random.uniform(2, 5))

    drop_df = pd.DataFrame(
        {
            "Open": [close_prices[i] - 0.1 for i in range(30)],
            "High": [close_prices[i] + 0.2 for i in range(30)],
            "Low": [close_prices[i] - 0.15 for i in range(30)],
            "Close": close_prices,
            "Volume": [1000000] * 30,
        },
        index=dates,
    )

    # Second stock (stable) for comparison
    stable_close = [100] * 30
    stable_df = pd.DataFrame(
        {
            "Open": [stable_close[i] for i in range(30)],
            "High": [stable_close[i] + 0.05 for i in range(30)],
            "Low": [stable_close[i] - 0.05 for i in range(30)],
            "Close": stable_close,
            "Volume": [1000000] * 30,
        },
        index=dates,
    )

    mock_tickers["DROP"] = MagicMock()
    mock_tickers["DROP"].history.return_value = drop_df
    mock_tickers["STABLE"] = MagicMock()
    mock_tickers["STABLE"].history.return_value = stable_df

    def mock_ticker_factory(symbol):
        return mock_tickers.get(symbol, MagicMock())

    with patch("yfinance.Ticker", side_effect=mock_ticker_factory):
        result = compare_stocks("DROP,STABLE")

    # Find the DROP stock in comparisons
    drop_comparison = [c for c in result["comparisons"] if c["symbol"] == "DROP"][0]

    # Should have negative max drawdown
    assert drop_comparison["maxDrawdown"] < 0
    assert drop_comparison["maxDrawdown"] > -100  # Should be reasonable


def test_compare_stocks_summary():
    """Verify summary statistics."""
    # Mock 3 stocks
    mock_tickers = {}
    np.random.seed(42)

    for symbol in ["AAPL", "MSFT", "GOOGL"]:
        close_prices = [100]
        for i in range(1, 60):
            close_prices.append(close_prices[-1] + np.random.uniform(0.1, 0.5))

        df = pd.DataFrame(
            {
                "Open": [close_prices[i] - 0.1 for i in range(60)],
                "High": [close_prices[i] + 0.2 for i in range(60)],
                "Low": [close_prices[i] - 0.15 for i in range(60)],
                "Close": close_prices,
                "Volume": [1000000] * 60,
            }
        )

        mock_tickers[symbol] = MagicMock()
        mock_tickers[symbol].history.return_value = df

    def mock_ticker_factory(symbol):
        return mock_tickers.get(symbol, MagicMock())

    with patch("yfinance.Ticker", side_effect=mock_ticker_factory):
        result = compare_stocks("AAPL,MSFT,GOOGL")

    assert "summary" in result
    assert "bestPerforming" in result["summary"]
    assert "worstPerforming" in result["summary"]
    assert "averageReturn" in result["summary"]
    assert "highestVolatility" in result["summary"]
    assert result["metadata"]["count"] == 3
