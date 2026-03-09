"""
Finance MCP Server — Streamable HTTP
Powered by FastMCP + yfinance

Provides real-time stock data, technical analysis, financials,
options, news, dividends, earnings, and more.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf
from mcp.server.fastmcp import FastMCP

# ──────────────────────────────────────────────
# Server
# ──────────────────────────────────────────────

mcp = FastMCP(
    name="Finance MCP Server",
    instructions=(
        "Real-time stock market data, technical analysis, financials, "
        "options chains, news, dividends, earnings, and sector comparison "
        "— all sourced from Yahoo Finance via yfinance."
    ),
)

# ──────────────────────────────────────────────
# Simple TTL cache
# ──────────────────────────────────────────────

_CACHE: dict[str, Any] = {}
_CACHE_TS: dict[str, float] = {}


def _cache_get(key: str, ttl: int) -> Any | None:
    if key in _CACHE and (time.time() - _CACHE_TS.get(key, 0)) < ttl:
        return _CACHE[key]
    return None


def _cache_set(key: str, value: Any) -> None:
    _CACHE[key] = value
    _CACHE_TS[key] = time.time()


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _ticker(symbol: str) -> yf.Ticker:
    return yf.Ticker(symbol.upper().strip())


def _safe(value: Any) -> Any:
    """Convert non-JSON-serialisable types."""
    if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def _df_to_records(df: pd.DataFrame) -> list[dict]:
    df = df.copy()
    if isinstance(df.index, pd.DatetimeIndex):
        df.index = df.index.strftime("%Y-%m-%d")
    df = df.where(pd.notnull(df), None)
    records = []
    for idx, row in df.iterrows():
        record = {"date": idx}
        record.update({col: _safe(row[col]) for col in df.columns})
        records.append(record)
    return records


def _series_to_dict(series: pd.Series) -> dict:
    return {str(k): _safe(v) for k, v in series.items()}


def _clean_info(info: dict) -> dict:
    return {k: _safe(v) for k, v in info.items() if v is not None and v != ""}


# ──────────────────────────────────────────────
# 1. Comprehensive Stock Info
# ──────────────────────────────────────────────


@mcp.tool()
def get_stock_info(symbol: str) -> dict:
    """
    Return a comprehensive company profile and market snapshot.

    Includes: sector, industry, description, market cap, P/E, EPS,
    52-week range, dividend yield, beta, analyst target price, and more.

    Args:
        symbol: Stock ticker symbol (e.g. "AAPL", "TSLA").
    """
    key = f"info:{symbol}"
    cached = _cache_get(key, ttl=300)
    if cached:
        return cached

    t = _ticker(symbol)
    info = _clean_info(t.info)

    result = {
        "symbol": symbol.upper(),
        "name": info.get("longName") or info.get("shortName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "description": info.get("longBusinessSummary"),
        "website": info.get("website"),
        "employees": info.get("fullTimeEmployees"),
        "country": info.get("country"),
        "currency": info.get("currency"),
        "exchange": info.get("exchange"),
        "market_cap": info.get("marketCap"),
        "enterprise_value": info.get("enterpriseValue"),
        "price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "previous_close": info.get("previousClose"),
        "open": info.get("open"),
        "day_low": info.get("dayLow"),
        "day_high": info.get("dayHigh"),
        "52_week_low": info.get("fiftyTwoWeekLow"),
        "52_week_high": info.get("fiftyTwoWeekHigh"),
        "volume": info.get("volume"),
        "avg_volume": info.get("averageVolume"),
        "beta": info.get("beta"),
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "peg_ratio": info.get("pegRatio"),
        "price_to_book": info.get("priceToBook"),
        "price_to_sales": info.get("priceToSalesTrailing12Months"),
        "eps": info.get("trailingEps"),
        "forward_eps": info.get("forwardEps"),
        "dividend_rate": info.get("dividendRate"),
        "dividend_yield": info.get("dividendYield"),
        "payout_ratio": info.get("payoutRatio"),
        "revenue": info.get("totalRevenue"),
        "gross_profit": info.get("grossProfits"),
        "ebitda": info.get("ebitda"),
        "net_income": info.get("netIncomeToCommon"),
        "profit_margin": info.get("profitMargins"),
        "operating_margin": info.get("operatingMargins"),
        "roe": info.get("returnOnEquity"),
        "roa": info.get("returnOnAssets"),
        "debt_to_equity": info.get("debtToEquity"),
        "current_ratio": info.get("currentRatio"),
        "free_cashflow": info.get("freeCashflow"),
        "analyst_target_price": info.get("targetMeanPrice"),
        "recommendation": info.get("recommendationKey"),
        "analyst_count": info.get("numberOfAnalystOpinions"),
        "shares_outstanding": info.get("sharesOutstanding"),
        "float_shares": info.get("floatShares"),
        "short_ratio": info.get("shortRatio"),
        "short_percent_float": info.get("shortPercentOfFloat"),
    }

    _cache_set(key, result)
    return result


# ──────────────────────────────────────────────
# 2. Historical Price Data
# ──────────────────────────────────────────────


@mcp.tool()
def get_historical_data(
    symbol: str,
    period: str = "1y",
    interval: str = "1d",
) -> dict:
    """
    Return OHLCV historical price data for a given symbol.

    Args:
        symbol:   Ticker symbol (e.g. "AAPL").
        period:   Lookback window. Valid values:
                  1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max.
        interval: Bar size. Valid values:
                  1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo.
    """
    key = f"hist:{symbol}:{period}:{interval}"
    cached = _cache_get(key, ttl=60)
    if cached:
        return cached

    t = _ticker(symbol)
    df = t.history(period=period, interval=interval, auto_adjust=True)

    if df.empty:
        return {"error": f"No historical data found for {symbol}"}

    records = _df_to_records(df)
    result = {
        "symbol": symbol.upper(),
        "period": period,
        "interval": interval,
        "count": len(records),
        "data": records,
    }
    _cache_set(key, result)
    return result


# ──────────────────────────────────────────────
# 3. Real-time Quote
# ──────────────────────────────────────────────


@mcp.tool()
def get_realtime_quote(symbol: str) -> dict:
    """
    Return the latest real-time price quote with change and volume.

    Args:
        symbol: Ticker symbol (e.g. "MSFT").
    """
    key = f"quote:{symbol}"
    cached = _cache_get(key, ttl=30)
    if cached:
        return cached

    t = _ticker(symbol)
    info = t.info
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    prev = info.get("previousClose")
    change = round(price - prev, 4) if (price and prev) else None
    change_pct = round(change / prev * 100, 4) if (change and prev) else None

    result = {
        "symbol": symbol.upper(),
        "price": price,
        "previous_close": prev,
        "change": change,
        "change_pct": change_pct,
        "open": info.get("open"),
        "day_low": info.get("dayLow"),
        "day_high": info.get("dayHigh"),
        "volume": info.get("volume"),
        "avg_volume": info.get("averageVolume"),
        "market_cap": info.get("marketCap"),
        "currency": info.get("currency"),
        "market_state": info.get("marketState"),
        "pre_market_price": info.get("preMarketPrice"),
        "post_market_price": info.get("postMarketPrice"),
    }
    _cache_set(key, result)
    return result


# ──────────────────────────────────────────────
# 4. Technical Analysis
# ──────────────────────────────────────────────


def _compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _compute_macd(close: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _compute_bollinger(close: pd.Series, period=20, std_dev=2):
    sma = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = sma + std_dev * std
    lower = sma - std_dev * std
    return upper, sma, lower


def _compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period=14) -> pd.Series:
    tr = pd.concat(
        [
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean()


def _support_resistance(close: pd.Series, window=20) -> dict:
    recent = close.tail(window)
    return {
        "support": round(float(recent.min()), 4),
        "resistance": round(float(recent.max()), 4),
    }


@mcp.tool()
def get_technical_analysis(symbol: str, period: str = "6mo") -> dict:
    """
    Return a full set of technical indicators for a symbol.

    Indicators: SMA (20/50/200), EMA (12/26), RSI (14), MACD (12/26/9),
    Bollinger Bands (20,2), ATR (14), volume SMA, support/resistance.

    Args:
        symbol: Ticker symbol (e.g. "NVDA").
        period: Lookback window for price history (default "6mo").
    """
    key = f"ta:{symbol}:{period}"
    cached = _cache_get(key, ttl=300)
    if cached:
        return cached

    t = _ticker(symbol)
    df = t.history(period=period, interval="1d", auto_adjust=True)

    if df.empty or len(df) < 30:
        return {"error": f"Insufficient data for {symbol}"}

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    # Moving averages
    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()

    # RSI
    rsi = _compute_rsi(close)

    # MACD
    macd_line, signal_line, histogram = _compute_macd(close)

    # Bollinger Bands
    bb_upper, bb_mid, bb_lower = _compute_bollinger(close)

    # ATR
    atr = _compute_atr(high, low, close)

    # Volume SMA
    vol_sma20 = volume.rolling(20).mean()

    # Support / Resistance
    sr = _support_resistance(close)

    last = close.iloc[-1]

    def _last(s: pd.Series) -> float | None:
        v = s.dropna()
        return round(float(v.iloc[-1]), 4) if not v.empty else None

    result = {
        "symbol": symbol.upper(),
        "period": period,
        "current_price": round(float(last), 4),
        "moving_averages": {
            "sma_20": _last(sma20),
            "sma_50": _last(sma50),
            "sma_200": _last(sma200),
            "ema_12": _last(ema12),
            "ema_26": _last(ema26),
        },
        "price_vs_ma": {
            "above_sma_20": bool(last > sma20.iloc[-1]) if not pd.isna(sma20.iloc[-1]) else None,
            "above_sma_50": bool(last > sma50.iloc[-1]) if not pd.isna(sma50.iloc[-1]) else None,
            "above_sma_200": bool(last > sma200.iloc[-1]) if not pd.isna(sma200.iloc[-1]) else None,
        },
        "rsi": {
            "value": _last(rsi),
            "signal": (
                "overbought"
                if _last(rsi) and _last(rsi) > 70
                else "oversold"
                if _last(rsi) and _last(rsi) < 30
                else "neutral"
            ),
        },
        "macd": {
            "macd": _last(macd_line),
            "signal": _last(signal_line),
            "histogram": _last(histogram),
            "crossover": (
                "bullish" if (_last(macd_line) or 0) > (_last(signal_line) or 0) else "bearish"
            ),
        },
        "bollinger_bands": {
            "upper": _last(bb_upper),
            "middle": _last(bb_mid),
            "lower": _last(bb_lower),
            "bandwidth": round(_last(bb_upper) - _last(bb_lower), 4)
            if (_last(bb_upper) and _last(bb_lower))
            else None,
            "percent_b": round(
                (float(last) - _last(bb_lower)) / (_last(bb_upper) - _last(bb_lower)), 4
            )
            if (_last(bb_upper) and _last(bb_lower) and _last(bb_upper) != _last(bb_lower))
            else None,
        },
        "atr": {
            "value": _last(atr),
            "atr_pct": round(_last(atr) / float(last) * 100, 4) if _last(atr) else None,
        },
        "volume": {
            "current": int(volume.iloc[-1]),
            "sma_20": round(float(vol_sma20.iloc[-1]), 0)
            if not pd.isna(vol_sma20.iloc[-1])
            else None,
            "vs_avg_pct": round((volume.iloc[-1] / vol_sma20.iloc[-1] - 1) * 100, 2)
            if not pd.isna(vol_sma20.iloc[-1])
            else None,
        },
        "support_resistance": sr,
    }

    _cache_set(key, result)
    return result


# ──────────────────────────────────────────────
# 5. Options Chain
# ──────────────────────────────────────────────


@mcp.tool()
def get_options_chain(
    symbol: str,
    expiration_date: str | None = None,
) -> dict:
    """
    Return the full options chain (calls + puts) for a symbol.

    Args:
        symbol:          Ticker symbol (e.g. "SPY").
        expiration_date: Expiry in YYYY-MM-DD format.
                         If omitted, uses the nearest available expiry.
    """
    key = f"opts:{symbol}:{expiration_date}"
    cached = _cache_get(key, ttl=300)
    if cached:
        return cached

    t = _ticker(symbol)
    expirations = t.options
    if not expirations:
        return {"error": f"No options data available for {symbol}"}

    # Pick the requested or nearest expiry
    exp = expiration_date if expiration_date in expirations else expirations[0]
    chain = t.option_chain(exp)

    def _format_chain(df: pd.DataFrame) -> list[dict]:
        df = df.copy().where(pd.notnull(df), None)
        cols = [
            "contractSymbol",
            "strike",
            "lastPrice",
            "bid",
            "ask",
            "change",
            "percentChange",
            "volume",
            "openInterest",
            "impliedVolatility",
            "inTheMoney",
        ]
        cols = [c for c in cols if c in df.columns]
        return (
            df[cols]
            .rename(
                columns={
                    "contractSymbol": "contract",
                    "lastPrice": "last_price",
                    "percentChange": "change_pct",
                    "openInterest": "open_interest",
                    "impliedVolatility": "iv",
                    "inTheMoney": "itm",
                }
            )
            .to_dict(orient="records")
        )

    result = {
        "symbol": symbol.upper(),
        "expiration_date": exp,
        "all_expirations": list(expirations),
        "calls": _format_chain(chain.calls),
        "puts": _format_chain(chain.puts),
    }
    _cache_set(key, result)
    return result


# ──────────────────────────────────────────────
# 6. Institutional & Major Holders
# ──────────────────────────────────────────────


@mcp.tool()
def get_holders(symbol: str) -> dict:
    """
    Return institutional and major (insider) shareholder information.

    Args:
        symbol: Ticker symbol.
    """
    key = f"holders:{symbol}"
    cached = _cache_get(key, ttl=3600)
    if cached:
        return cached

    t = _ticker(symbol)

    def _df_clean(df) -> list[dict]:
        if df is None or (hasattr(df, "empty") and df.empty):
            return []
        df = df.copy().where(pd.notnull(df), None)
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime("%Y-%m-%d")
        return df.to_dict(orient="records")

    result = {
        "symbol": symbol.upper(),
        "institutional_holders": _df_clean(t.institutional_holders),
        "major_holders": _df_clean(t.major_holders),
        "mutualfund_holders": _df_clean(t.mutualfund_holders),
    }
    _cache_set(key, result)
    return result


# ──────────────────────────────────────────────
# 7. Earnings Calendar & History
# ──────────────────────────────────────────────


@mcp.tool()
def get_earnings(symbol: str) -> dict:
    """
    Return earnings calendar (upcoming), historical EPS, and analyst
    price targets for a symbol.

    Args:
        symbol: Ticker symbol.
    """
    key = f"earnings:{symbol}"
    cached = _cache_get(key, ttl=3600)
    if cached:
        return cached

    t = _ticker(symbol)
    info = t.info

    def _df_clean(df) -> list[dict]:
        if df is None or (hasattr(df, "empty") and df.empty):
            return []
        df = df.copy().where(pd.notnull(df), None)
        if isinstance(df.index, pd.DatetimeIndex):
            df.index = df.index.strftime("%Y-%m-%d")
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime("%Y-%m-%d")
        records = []
        for idx, row in df.iterrows():
            record = {"date": idx} if not isinstance(idx, int) else {}
            record.update({k: _safe(v) for k, v in row.items()})
            records.append(record)
        return records

    result = {
        "symbol": symbol.upper(),
        "earnings_dates": _df_clean(t.earnings_dates) if hasattr(t, "earnings_dates") else [],
        "earnings_history": _df_clean(t.earnings_history) if hasattr(t, "earnings_history") else [],
        "price_targets": {
            "low": info.get("targetLowPrice"),
            "mean": info.get("targetMeanPrice"),
            "median": info.get("targetMedianPrice"),
            "high": info.get("targetHighPrice"),
        },
        "recommendation": {
            "key": info.get("recommendationKey"),
            "mean": info.get("recommendationMean"),
            "count": info.get("numberOfAnalystOpinions"),
        },
    }
    _cache_set(key, result)
    return result


# ──────────────────────────────────────────────
# 8. Analyst Recommendations
# ──────────────────────────────────────────────


@mcp.tool()
def get_analyst_recommendations(symbol: str) -> dict:
    """
    Return analyst upgrade/downgrade history and current consensus.

    Args:
        symbol: Ticker symbol.
    """
    key = f"recs:{symbol}"
    cached = _cache_get(key, ttl=3600)
    if cached:
        return cached

    t = _ticker(symbol)

    def _recs(df) -> list[dict]:
        if df is None or (hasattr(df, "empty") and df.empty):
            return []
        df = df.copy().where(pd.notnull(df), None)
        if isinstance(df.index, pd.DatetimeIndex):
            df.index = df.index.strftime("%Y-%m-%d")
        records = []
        for idx, row in df.iterrows():
            record = {"date": str(idx)}
            record.update({k: _safe(v) for k, v in row.items()})
            records.append(record)
        return records

    info = t.info
    result = {
        "symbol": symbol.upper(),
        "current_recommendation": info.get("recommendationKey"),
        "target_price_mean": info.get("targetMeanPrice"),
        "upgrades_downgrades": _recs(t.upgrades_downgrades)
        if hasattr(t, "upgrades_downgrades")
        else [],
        "recommendations": _recs(t.recommendations) if hasattr(t, "recommendations") else [],
    }
    _cache_set(key, result)
    return result


# ──────────────────────────────────────────────
# 9. Financial Statements
# ──────────────────────────────────────────────


@mcp.tool()
def get_financial_statements(
    symbol: str,
    frequency: str = "annual",
) -> dict:
    """
    Return income statement, balance sheet, and cash flow statement.

    Args:
        symbol:    Ticker symbol.
        frequency: "annual" or "quarterly".
    """
    key = f"fin:{symbol}:{frequency}"
    cached = _cache_get(key, ttl=3600)
    if cached:
        return cached

    t = _ticker(symbol)
    quarterly = frequency.lower().startswith("q")

    def _stmt(df) -> dict:
        if df is None or (hasattr(df, "empty") and df.empty):
            return {}
        df = df.copy()
        if isinstance(df.columns, pd.DatetimeIndex):
            df.columns = df.columns.strftime("%Y-%m-%d")
        df = df.where(pd.notnull(df), None)
        result = {}
        for col in df.columns:
            result[col] = {str(k): _safe(v) for k, v in df[col].items()}
        return result

    if quarterly:
        income = t.quarterly_income_stmt
        balance = t.quarterly_balance_sheet
        cashflow = t.quarterly_cashflow
    else:
        income = t.income_stmt
        balance = t.balance_sheet
        cashflow = t.cashflow

    result = {
        "symbol": symbol.upper(),
        "frequency": frequency,
        "income_statement": _stmt(income),
        "balance_sheet": _stmt(balance),
        "cash_flow": _stmt(cashflow),
    }
    _cache_set(key, result)
    return result


# ──────────────────────────────────────────────
# 10. News
# ──────────────────────────────────────────────


@mcp.tool()
def get_news(symbol: str, limit: int = 20) -> dict:
    """
    Return the latest news headlines for a symbol.

    Args:
        symbol: Ticker symbol.
        limit:  Max number of articles to return (default 20).
    """
    key = f"news:{symbol}:{limit}"
    cached = _cache_get(key, ttl=300)
    if cached:
        return cached

    t = _ticker(symbol)
    news = t.news or []

    articles = []
    for item in news[:limit]:
        ct = item.get("content", {})
        pub_date = ct.get("pubDate") or item.get("providerPublishTime")
        if isinstance(pub_date, (int, float)):
            pub_date = pd.Timestamp(pub_date, unit="s").isoformat()
        articles.append(
            {
                "title": ct.get("title") or item.get("title"),
                "publisher": ct.get("provider", {}).get("displayName") or item.get("publisher"),
                "url": (ct.get("canonicalUrl") or {}).get("url") or item.get("link"),
                "published": pub_date,
                "summary": ct.get("summary"),
                "tickers": [r.get("symbol") for r in ct.get("finance", {}).get("stockTickers", [])]
                or item.get("relatedTickers", []),
            }
        )

    result = {
        "symbol": symbol.upper(),
        "count": len(articles),
        "articles": articles,
    }
    _cache_set(key, result)
    return result


# ──────────────────────────────────────────────
# 11. Dividend History
# ──────────────────────────────────────────────


@mcp.tool()
def get_dividend_history(symbol: str, period: str = "5y") -> dict:
    """
    Return full dividend payment history and summary statistics.

    Args:
        symbol: Ticker symbol.
        period: Lookback window (default "5y").
    """
    key = f"div:{symbol}:{period}"
    cached = _cache_get(key, ttl=3600)
    if cached:
        return cached

    t = _ticker(symbol)
    info = t.info
    df = t.history(period=period, auto_adjust=False)

    divs = df["Dividends"][df["Dividends"] > 0].copy()
    divs.index = divs.index.strftime("%Y-%m-%d")
    records = [{"date": idx, "amount": round(float(v), 6)} for idx, v in divs.items()]

    annual: dict[str, float] = {}
    for rec in records:
        yr = rec["date"][:4]
        annual[yr] = round(annual.get(yr, 0) + rec["amount"], 6)

    result = {
        "symbol": symbol.upper(),
        "dividend_rate": info.get("dividendRate"),
        "dividend_yield": info.get("dividendYield"),
        "payout_ratio": info.get("payoutRatio"),
        "ex_dividend_date": info.get("exDividendDate"),
        "last_dividend": records[-1] if records else None,
        "total_payments": len(records),
        "annual_dividends": annual,
        "history": records,
    }
    _cache_set(key, result)
    return result


# ──────────────────────────────────────────────
# 12. Sector / Multi-stock Comparison
# ──────────────────────────────────────────────


@mcp.tool()
def compare_stocks(
    symbols: str,
    period: str = "1y",
) -> dict:
    """
    Compare multiple stocks side-by-side on performance and key metrics.

    Args:
        symbols: Comma-separated ticker symbols (e.g. "AAPL,MSFT,GOOGL").
        period:  Lookback window for return calculation (default "1y").
    """
    tickers = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not tickers:
        return {"error": "Provide at least one symbol"}

    key = f"compare:{','.join(tickers)}:{period}"
    cached = _cache_get(key, ttl=300)
    if cached:
        return cached

    comparison = []
    for sym in tickers:
        try:
            t = _ticker(sym)
            info = t.info
            df = t.history(period=period, auto_adjust=True)

            if df.empty:
                comparison.append({"symbol": sym, "error": "No data"})
                continue

            start_price = float(df["Close"].iloc[0])
            end_price = float(df["Close"].iloc[-1])
            period_return = round((end_price / start_price - 1) * 100, 4)

            daily_returns = df["Close"].pct_change().dropna()
            volatility = round(float(daily_returns.std() * (252**0.5) * 100), 4)
            sharpe = (
                round(float(daily_returns.mean() / daily_returns.std() * (252**0.5)), 4)
                if daily_returns.std() > 0
                else None
            )

            comparison.append(
                {
                    "symbol": sym,
                    "name": info.get("shortName"),
                    "sector": info.get("sector"),
                    "price": info.get("currentPrice") or end_price,
                    "market_cap": info.get("marketCap"),
                    "pe_ratio": info.get("trailingPE"),
                    "beta": info.get("beta"),
                    "dividend_yield": info.get("dividendYield"),
                    "period_return_pct": period_return,
                    "annualised_volatility_pct": volatility,
                    "sharpe_ratio": sharpe,
                    "52w_high": info.get("fiftyTwoWeekHigh"),
                    "52w_low": info.get("fiftyTwoWeekLow"),
                }
            )
        except Exception as e:
            comparison.append({"symbol": sym, "error": str(e)})

    result = {
        "period": period,
        "symbols": tickers,
        "comparison": sorted(comparison, key=lambda x: x.get("period_return_pct", 0), reverse=True),
    }
    _cache_set(key, result)
    return result


# ──────────────────────────────────────────────
# 13. Search / Symbol Lookup
# ──────────────────────────────────────────────


@mcp.tool()
def search_symbol(query: str) -> dict:
    """
    Search for ticker symbols matching a company name or keyword.

    Args:
        query: Company name or keyword (e.g. "Tesla", "electric vehicle").
    """
    import yfinance as yf

    results = yf.Search(query, max_results=10)
    quotes = []
    try:
        for q in results.quotes or []:
            quotes.append(
                {
                    "symbol": q.get("symbol"),
                    "name": q.get("longname") or q.get("shortname"),
                    "type": q.get("quoteType"),
                    "exchange": q.get("exchange"),
                    "sector": q.get("sector"),
                    "industry": q.get("industry"),
                }
            )
    except Exception:
        pass
    return {"query": query, "results": quotes}


# ──────────────────────────────────────────────
# 14. Market Overview (indices snapshot)
# ──────────────────────────────────────────────

_INDICES = {
    "S&P 500": "^GSPC",
    "NASDAQ": "^IXIC",
    "Dow Jones": "^DJI",
    "Russell 2000": "^RUT",
    "VIX": "^VIX",
    "10Y Treasury": "^TNX",
    "Gold": "GC=F",
    "Crude Oil": "CL=F",
    "EUR/USD": "EURUSD=X",
    "BTC/USD": "BTC-USD",
}


@mcp.tool()
def get_market_overview() -> dict:
    """
    Return a real-time snapshot of major market indices, commodities,
    forex, and crypto (S&P 500, NASDAQ, Dow, VIX, Gold, BTC, etc.).
    """
    cached = _cache_get("market_overview", ttl=60)
    if cached:
        return cached

    snapshot = []
    for name, sym in _INDICES.items():
        try:
            info = yf.Ticker(sym).info
            price = info.get("regularMarketPrice") or info.get("currentPrice")
            prev = info.get("previousClose")
            change_pct = round((price - prev) / prev * 100, 2) if (price and prev) else None
            snapshot.append(
                {
                    "name": name,
                    "symbol": sym,
                    "price": price,
                    "change_pct": change_pct,
                    "currency": info.get("currency"),
                }
            )
        except Exception as e:
            snapshot.append({"name": name, "symbol": sym, "error": str(e)})

    result = {"timestamp": pd.Timestamp.now().isoformat(), "indices": snapshot}
    _cache_set("market_overview", result)
    return result


# ──────────────────────────────────────────────
# 15. Cache management
# ──────────────────────────────────────────────


@mcp.tool()
def clear_cache() -> dict:
    """Clear the in-memory price/data cache."""
    count = len(_CACHE)
    _CACHE.clear()
    _CACHE_TS.clear()
    return {"cleared": count, "status": "ok"}


# ──────────────────────────────────────────────
# Entry-point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    from starlette.middleware import Middleware
    from starlette.types import ASGIApp, Receive, Scope, Send

    class NormalizeHostMiddleware:
        """Rewrite the Host header to 'localhost' so the MCP SDK's DNS-rebinding
        protection doesn't reject connections from Docker bridge IPs or any other
        non-loopback address that appears in the Host header."""

        def __init__(self, app: ASGIApp) -> None:
            self.app = app

        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            if scope["type"] == "http":
                headers = {k: v for k, v in scope["headers"]}
                headers[b"host"] = b"localhost"
                scope["headers"] = list(headers.items())
            await self.app(scope, receive, send)

    parser = argparse.ArgumentParser(description="Finance MCP Server (streamable HTTP)")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument(
        "--transport",
        default="streamable-http",
        choices=["streamable-http", "sse", "stdio"],
        help="MCP transport (default: streamable-http)",
    )
    args = parser.parse_args()

    # host / port are set on the FastMCP instance before run()
    mcp.settings.host = args.host
    mcp.settings.port = args.port

    print(f"🚀  Finance MCP Server starting on {args.host}:{args.port}  [{args.transport}]")
    mcp.run(
        transport=args.transport,
        middleware=[Middleware(NormalizeHostMiddleware)],
    )
