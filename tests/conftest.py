"""Pytest configuration and shared fixtures."""

import math
from datetime import datetime
from unittest.mock import MagicMock

import pandas as pd
import pytest


@pytest.fixture
def mock_ticker():
    """Mock yfinance Ticker with sample data."""
    ticker = MagicMock()
    ticker.info = {
        "longName": "Test Company Inc",
        "shortName": "Test Co",
        "marketCap": 1000000000000,
        "currentPrice": 150.0,
        "previousClose": 145.0,
        "sector": "Technology",
        "industry": "Software",
        "longBusinessSummary": "A test company for unit testing.",
        "website": "https://example.com",
        "fullTimeEmployees": 100000,
        "trailingPE": 25.0,
        "dividendYield": 0.02,
        "beta": 1.2,
        "trailingEps": 6.0,
        "fiftyTwoWeekHigh": 180.0,
        "fiftyTwoWeekLow": 120.0,
        "regularMarketPrice": 150.0,
        "regularMarketVolume": 50000000,
        "bid": 149.5,
        "ask": 150.5,
        "bidSize": 100,
        "askSize": 200,
        "regularMarketDayHigh": 155.0,
        "regularMarketDayLow": 148.0,
        "regularMarketOpen": 149.0,
    }
    return ticker


@pytest.fixture
def sample_df():
    """Sample pandas DataFrame with NaN values."""
    return pd.DataFrame({
        "Date": pd.date_range("2024-01-01", periods=5),
        "Open": [100.0, 101.0, math.nan, 103.0, 104.0],
        "High": [105.0, 106.0, 107.0, 108.0, 109.0],
        "Low": [99.0, 100.0, 101.0, 102.0, 103.0],
        "Close": [104.0, 105.0, 106.0, 107.0, 108.0],
        "Volume": [1000000, 1100000, 1200000, 1300000, 1400000],
    })


@pytest.fixture
def sample_timestamp():
    """Sample pandas Timestamp."""
    return pd.Timestamp("2024-01-15 10:30:00")
