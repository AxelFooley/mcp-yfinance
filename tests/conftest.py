"""
Shared pytest fixtures for the Finance MCP Server test suite.
All yfinance network calls are mocked — no internet required.
"""

from __future__ import annotations

from collections import namedtuple
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

# ──────────────────────────────────────────────────────────────────────────────
# Canonical mock data
# ──────────────────────────────────────────────────────────────────────────────

MOCK_INFO: dict = {
    "longName": "Apple Inc.",
    "shortName": "Apple Inc.",
    "sector": "Technology",
    "industry": "Consumer Electronics",
    "longBusinessSummary": "Apple Inc. designs, manufactures and markets smartphones.",
    "website": "https://www.apple.com",
    "fullTimeEmployees": 164000,
    "country": "United States",
    "currency": "USD",
    "exchange": "NMS",
    "marketCap": 3_000_000_000_000,
    "enterpriseValue": 3_050_000_000_000,
    "currentPrice": 175.0,
    "regularMarketPrice": 175.0,
    "previousClose": 170.0,
    "open": 172.0,
    "dayLow": 171.0,
    "dayHigh": 176.0,
    "fiftyTwoWeekLow": 120.0,
    "fiftyTwoWeekHigh": 200.0,
    "volume": 50_000_000,
    "averageVolume": 55_000_000,
    "beta": 1.2,
    "trailingPE": 28.5,
    "forwardPE": 25.0,
    "pegRatio": 2.1,
    "priceToBook": 42.0,
    "priceToSalesTrailing12Months": 7.5,
    "trailingEps": 6.14,
    "forwardEps": 7.0,
    "dividendRate": 0.96,
    "dividendYield": 0.0055,
    "payoutRatio": 0.156,
    "totalRevenue": 383_000_000_000,
    "grossProfits": 169_000_000_000,
    "ebitda": 125_000_000_000,
    "netIncomeToCommon": 97_000_000_000,
    "profitMargins": 0.253,
    "operatingMargins": 0.298,
    "returnOnEquity": 1.72,
    "returnOnAssets": 0.304,
    "debtToEquity": 181.0,
    "currentRatio": 0.998,
    "freeCashflow": 90_000_000_000,
    "targetMeanPrice": 195.0,
    "targetLowPrice": 155.0,
    "targetMedianPrice": 200.0,
    "targetHighPrice": 220.0,
    "recommendationKey": "buy",
    "recommendationMean": 2.0,
    "numberOfAnalystOpinions": 38,
    "sharesOutstanding": 15_500_000_000,
    "floatShares": 15_400_000_000,
    "shortRatio": 1.2,
    "shortPercentOfFloat": 0.007,
    "marketState": "REGULAR",
    "preMarketPrice": None,
    "postMarketPrice": None,
    "exDividendDate": "2024-02-09",
}


def make_history_df(n_rows: int = 260, seed: int = 42) -> pd.DataFrame:
    """
    Generate a deterministic OHLCV history DataFrame.
    n_rows >= 200 ensures SMA-200 has values.
    """
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(end="2024-03-01", periods=n_rows)
    close = 150.0 + np.cumsum(rng.normal(0, 1.5, n_rows))
    close = np.abs(close)
    high = close + rng.uniform(0.5, 3.0, n_rows)
    low = close - rng.uniform(0.5, 3.0, n_rows)
    open_ = close + rng.normal(0, 1.0, n_rows)
    volume = rng.integers(30_000_000, 80_000_000, n_rows).astype(float)

    # Sprinkle a few dividends (guard indices for small DataFrames)
    dividends = np.zeros(n_rows)
    if n_rows > 50:
        dividends[50] = 0.24
    if n_rows > 130:
        dividends[130] = 0.24
    if n_rows > 210:
        dividends[210] = 0.24

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
            "Dividends": dividends,
            "Stock Splits": 0.0,
        },
        index=dates,
    )


def make_options_df(n_strikes: int = 5) -> pd.DataFrame:
    strikes = [170.0 + i * 5 for i in range(n_strikes)]
    return pd.DataFrame(
        {
            "contractSymbol": [f"AAPL240315C{int(s):08d}" for s in strikes],
            "strike": strikes,
            "lastPrice": [5.0 + i for i in range(n_strikes)],
            "bid": [4.9 + i for i in range(n_strikes)],
            "ask": [5.1 + i for i in range(n_strikes)],
            "change": [0.1] * n_strikes,
            "percentChange": [2.0] * n_strikes,
            "volume": [1000.0 + i * 100 for i in range(n_strikes)],
            "openInterest": [5000.0 + i * 200 for i in range(n_strikes)],
            "impliedVolatility": [0.3 + i * 0.02 for i in range(n_strikes)],
            "inTheMoney": [i < 3 for i in range(n_strikes)],
        }
    )


def make_financial_stmt_df() -> pd.DataFrame:
    cols = pd.DatetimeIndex(["2023-09-30", "2022-09-30", "2021-09-30"])
    return pd.DataFrame(
        {
            "TotalRevenue": [383e9, 394e9, 366e9],
            "NetIncome": [97e9, 100e9, 95e9],
            "OperatingIncome": [114e9, 119e9, 109e9],
        },
        index=["TotalRevenue", "NetIncome", "OperatingIncome"],
        columns=cols,
    )


def make_holders_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Holder": ["Vanguard Group Inc", "BlackRock Inc"],
            "Shares": [1_300_000_000, 1_000_000_000],
            "Date Reported": pd.to_datetime(["2023-12-31", "2023-12-31"]),
            "% Out": [0.084, 0.065],
            "Value": [227_000_000_000, 175_000_000_000],
        }
    )


def make_recommendations_df() -> pd.DataFrame:
    idx = pd.DatetimeIndex(["2024-01-10", "2024-01-15"])
    return pd.DataFrame(
        {
            "Firm": ["Goldman Sachs", "Morgan Stanley"],
            "To Grade": ["Buy", "Overweight"],
            "From Grade": ["Neutral", "Equal-Weight"],
            "Action": ["upgrade", "upgrade"],
        },
        index=idx,
    )


def make_earnings_dates_df() -> pd.DataFrame:
    idx = pd.DatetimeIndex(["2024-05-02", "2024-02-01"])
    return pd.DataFrame(
        {
            "EPS Estimate": [1.50, 2.10],
            "Reported EPS": [None, 2.18],
            "Surprise(%)": [None, 3.8],
        },
        index=idx,
    )


OptionChain = namedtuple("OptionChain", ["calls", "puts"])


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def clear_server_cache():
    """Reset the in-memory cache before every test."""
    import server

    server._CACHE.clear()
    server._CACHE_TS.clear()
    yield
    server._CACHE.clear()
    server._CACHE_TS.clear()


@pytest.fixture()
def mock_ticker():
    """Return a fully configured MagicMock for yf.Ticker."""
    t = MagicMock()
    t.info = MOCK_INFO.copy()
    hist = make_history_df()
    t.history.return_value = hist
    t.options = ("2024-03-15", "2024-04-19", "2024-05-17")
    calls_df = make_options_df()
    puts_df = make_options_df()
    t.option_chain.return_value = OptionChain(calls=calls_df, puts=puts_df)
    t.institutional_holders = make_holders_df()
    t.major_holders = pd.DataFrame(
        {"Value": [0.07, 0.93], "Breakdown": ["% held by insiders", "% held by institutions"]}
    )
    t.mutualfund_holders = make_holders_df()
    t.earnings_dates = make_earnings_dates_df()
    t.earnings_history = pd.DataFrame()
    t.recommendations = make_recommendations_df()
    t.upgrades_downgrades = make_recommendations_df()
    t.income_stmt = make_financial_stmt_df()
    t.balance_sheet = make_financial_stmt_df()
    t.cashflow = make_financial_stmt_df()
    t.quarterly_income_stmt = make_financial_stmt_df()
    t.quarterly_balance_sheet = make_financial_stmt_df()
    t.quarterly_cashflow = make_financial_stmt_df()
    t.news = [
        {
            "content": {
                "title": "Apple Beats Earnings",
                "pubDate": "2024-02-01T22:00:00Z",
                "summary": "Apple reported strong Q1 results.",
                "provider": {"displayName": "Reuters"},
                "canonicalUrl": {"url": "https://reuters.com/apple"},
                "finance": {"stockTickers": [{"symbol": "AAPL"}]},
            }
        }
    ]
    return t
