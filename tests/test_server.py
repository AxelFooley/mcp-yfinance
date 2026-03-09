"""
Finance MCP Server — full test suite.
All yfinance I/O is mocked; no network calls are made.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

import server
from tests.conftest import (
    MOCK_INFO,
    make_history_df,
)

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

SYMBOL = "AAPL"


def patch_ticker(mock_ticker):
    """Context-manager shorthand: patch server.yf.Ticker with mock_ticker."""
    return patch("server.yf.Ticker", return_value=mock_ticker)


# ─────────────────────────────────────────────────────────────
# 1. Cache helpers
# ─────────────────────────────────────────────────────────────


class TestCache:
    def test_miss_returns_none(self):
        assert server._cache_get("missing_key", ttl=60) is None

    def test_set_then_get_within_ttl(self):
        server._cache_set("k1", {"x": 1})
        assert server._cache_get("k1", ttl=60) == {"x": 1}

    def test_expired_returns_none(self):
        server._cache_set("k2", "value")
        server._CACHE_TS["k2"] = time.time() - 100  # backdate
        assert server._cache_get("k2", ttl=60) is None

    def test_overwrite(self):
        server._cache_set("k3", "first")
        server._cache_set("k3", "second")
        assert server._cache_get("k3", ttl=60) == "second"


# ─────────────────────────────────────────────────────────────
# 2. Helper functions
# ─────────────────────────────────────────────────────────────


class TestHelpers:
    def test_safe_nan_becomes_none(self):

        assert server._safe(float("nan")) is None

    def test_safe_inf_becomes_none(self):
        assert server._safe(float("inf")) is None

    def test_safe_numpy_int(self):
        import numpy as np

        assert server._safe(np.int64(42)) == 42
        assert isinstance(server._safe(np.int64(42)), int)

    def test_safe_numpy_float(self):
        import numpy as np

        result = server._safe(np.float64(3.14))
        assert abs(result - 3.14) < 1e-6
        assert isinstance(result, float)

    def test_safe_timestamp(self):
        ts = pd.Timestamp("2024-01-15")
        result = server._safe(ts)
        assert "2024-01-15" in result

    def test_safe_passthrough(self):
        assert server._safe("hello") == "hello"
        assert server._safe(42) == 42
        assert server._safe(None) is None

    def test_df_to_records_basic(self):
        df = make_history_df(n_rows=5)
        records = server._df_to_records(df)
        assert len(records) == 5
        assert "date" in records[0]
        assert "Close" in records[0]

    def test_clean_info_strips_none_and_empty(self):
        raw = {"a": 1, "b": None, "c": "", "d": "value"}
        result = server._clean_info(raw)
        assert result == {"a": 1, "d": "value"}


# ─────────────────────────────────────────────────────────────
# 3. get_stock_info
# ─────────────────────────────────────────────────────────────


class TestGetStockInfo:
    def test_returns_expected_fields(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_stock_info(SYMBOL)

        assert result["symbol"] == "AAPL"
        assert result["name"] == "Apple Inc."
        assert result["sector"] == "Technology"
        assert result["price"] == 175.0
        assert result["pe_ratio"] == 28.5
        assert result["market_cap"] == 3_000_000_000_000

    def test_cache_hit_skips_ticker(self, mock_ticker):
        with patch_ticker(mock_ticker) as mock_cls:
            server.get_stock_info(SYMBOL)
            server.get_stock_info(SYMBOL)  # second call
        # Ticker should only be constructed once
        assert mock_cls.call_count == 1

    def test_symbol_uppercased(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_stock_info("aapl")
        assert result["symbol"] == "AAPL"

    def test_none_values_excluded_from_info(self, mock_ticker):
        # Ensure _clean_info strips Nones before mapping
        mock_ticker.info = {**MOCK_INFO, "preMarketPrice": None}
        with patch_ticker(mock_ticker):
            result = server.get_stock_info(SYMBOL)
        assert result["symbol"] == "AAPL"


# ─────────────────────────────────────────────────────────────
# 4. get_historical_data
# ─────────────────────────────────────────────────────────────


class TestGetHistoricalData:
    def test_returns_records(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_historical_data(SYMBOL)

        assert result["symbol"] == "AAPL"
        assert result["count"] == 260
        assert len(result["data"]) == 260
        assert "Close" in result["data"][0]

    def test_empty_df_returns_error(self, mock_ticker):
        mock_ticker.history.return_value = pd.DataFrame()
        with patch_ticker(mock_ticker):
            result = server.get_historical_data(SYMBOL)
        assert "error" in result

    def test_custom_period_and_interval(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_historical_data(SYMBOL, period="3mo", interval="1wk")
        assert result["period"] == "3mo"
        assert result["interval"] == "1wk"

    def test_cache_on_second_call(self, mock_ticker):
        with patch_ticker(mock_ticker) as mock_cls:
            server.get_historical_data(SYMBOL, period="1y", interval="1d")
            server.get_historical_data(SYMBOL, period="1y", interval="1d")
        assert mock_cls.call_count == 1


# ─────────────────────────────────────────────────────────────
# 5. get_realtime_quote
# ─────────────────────────────────────────────────────────────


class TestGetRealtimeQuote:
    def test_price_and_change(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_realtime_quote(SYMBOL)

        assert result["price"] == 175.0
        assert result["previous_close"] == 170.0
        assert abs(result["change"] - 5.0) < 0.01
        assert abs(result["change_pct"] - (5.0 / 170.0 * 100)) < 0.01

    def test_missing_price_change_is_none(self, mock_ticker):
        info = {**MOCK_INFO, "currentPrice": None, "regularMarketPrice": None}
        mock_ticker.info = info
        with patch_ticker(mock_ticker):
            result = server.get_realtime_quote(SYMBOL)
        assert result["change"] is None
        assert result["change_pct"] is None

    def test_market_state_present(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_realtime_quote(SYMBOL)
        assert result["market_state"] == "REGULAR"


# ─────────────────────────────────────────────────────────────
# 6. get_technical_analysis
# ─────────────────────────────────────────────────────────────


class TestGetTechnicalAnalysis:
    def test_all_indicator_sections_present(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_technical_analysis(SYMBOL, period="2y")

        for key in (
            "moving_averages",
            "rsi",
            "macd",
            "bollinger_bands",
            "atr",
            "volume",
            "support_resistance",
            "price_vs_ma",
        ):
            assert key in result, f"Missing section: {key}"

    def test_sma200_has_value_with_enough_data(self, mock_ticker):
        # 260 rows is enough for SMA-200
        with patch_ticker(mock_ticker):
            result = server.get_technical_analysis(SYMBOL)
        assert result["moving_averages"]["sma_200"] is not None

    def test_rsi_signal_classification(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_technical_analysis(SYMBOL)
        assert result["rsi"]["signal"] in ("overbought", "oversold", "neutral")

    def test_macd_crossover_classification(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_technical_analysis(SYMBOL)
        assert result["macd"]["crossover"] in ("bullish", "bearish")

    def test_bollinger_bandwidth_positive(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_technical_analysis(SYMBOL)
        bw = result["bollinger_bands"]["bandwidth"]
        assert bw is not None and bw > 0

    def test_insufficient_data_returns_error(self, mock_ticker):
        mock_ticker.history.return_value = make_history_df(n_rows=10)
        with patch_ticker(mock_ticker):
            result = server.get_technical_analysis(SYMBOL)
        assert "error" in result

    def test_volume_vs_avg_pct_present(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_technical_analysis(SYMBOL)
        assert "vs_avg_pct" in result["volume"]


# ─────────────────────────────────────────────────────────────
# 7. get_options_chain
# ─────────────────────────────────────────────────────────────


class TestGetOptionsChain:
    def test_returns_calls_and_puts(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_options_chain(SYMBOL)

        assert result["symbol"] == "AAPL"
        assert len(result["calls"]) == 5
        assert len(result["puts"]) == 5
        assert result["expiration_date"] == "2024-03-15"
        assert len(result["all_expirations"]) == 3

    def test_specific_expiration(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_options_chain(SYMBOL, expiration_date="2024-04-19")
        assert result["expiration_date"] == "2024-04-19"

    def test_fallback_to_nearest_if_date_invalid(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_options_chain(SYMBOL, expiration_date="9999-01-01")
        # Falls back to first available
        assert result["expiration_date"] == "2024-03-15"

    def test_no_options_returns_error(self, mock_ticker):
        mock_ticker.options = ()
        with patch_ticker(mock_ticker):
            result = server.get_options_chain(SYMBOL)
        assert "error" in result

    def test_calls_have_expected_fields(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_options_chain(SYMBOL)
        call = result["calls"][0]
        assert "strike" in call
        assert "last_price" in call
        assert "iv" in call


# ─────────────────────────────────────────────────────────────
# 8. get_holders
# ─────────────────────────────────────────────────────────────


class TestGetHolders:
    def test_returns_all_holder_types(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_holders(SYMBOL)
        assert "institutional_holders" in result
        assert "major_holders" in result
        assert "mutualfund_holders" in result

    def test_institutional_holders_list(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_holders(SYMBOL)
        assert len(result["institutional_holders"]) == 2

    def test_empty_df_returns_empty_list(self, mock_ticker):
        mock_ticker.institutional_holders = pd.DataFrame()
        with patch_ticker(mock_ticker):
            result = server.get_holders(SYMBOL)
        assert result["institutional_holders"] == []

    def test_none_df_returns_empty_list(self, mock_ticker):
        mock_ticker.major_holders = None
        with patch_ticker(mock_ticker):
            result = server.get_holders(SYMBOL)
        assert result["major_holders"] == []


# ─────────────────────────────────────────────────────────────
# 9. get_earnings
# ─────────────────────────────────────────────────────────────


class TestGetEarnings:
    def test_price_targets_present(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_earnings(SYMBOL)
        assert result["price_targets"]["mean"] == 195.0
        assert result["price_targets"]["low"] == 155.0

    def test_recommendation_present(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_earnings(SYMBOL)
        assert result["recommendation"]["key"] == "buy"

    def test_earnings_dates_list(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_earnings(SYMBOL)
        assert isinstance(result["earnings_dates"], list)
        assert len(result["earnings_dates"]) == 2

    def test_missing_earnings_dates_attr(self, mock_ticker):
        del mock_ticker.earnings_dates
        with patch_ticker(mock_ticker):
            result = server.get_earnings(SYMBOL)
        assert result["earnings_dates"] == []


# ─────────────────────────────────────────────────────────────
# 10. get_analyst_recommendations
# ─────────────────────────────────────────────────────────────


class TestGetAnalystRecommendations:
    def test_current_recommendation(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_analyst_recommendations(SYMBOL)
        assert result["current_recommendation"] == "buy"
        assert result["target_price_mean"] == 195.0

    def test_upgrades_downgrades_list(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_analyst_recommendations(SYMBOL)
        assert isinstance(result["upgrades_downgrades"], list)
        assert len(result["upgrades_downgrades"]) == 2

    def test_missing_attr_returns_empty_list(self, mock_ticker):
        del mock_ticker.upgrades_downgrades
        del mock_ticker.recommendations
        with patch_ticker(mock_ticker):
            result = server.get_analyst_recommendations(SYMBOL)
        assert result["upgrades_downgrades"] == []
        assert result["recommendations"] == []


# ─────────────────────────────────────────────────────────────
# 11. get_financial_statements
# ─────────────────────────────────────────────────────────────


class TestGetFinancialStatements:
    def test_annual_returns_three_sections(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_financial_statements(SYMBOL, frequency="annual")
        assert "income_statement" in result
        assert "balance_sheet" in result
        assert "cash_flow" in result
        assert result["frequency"] == "annual"

    def test_quarterly_uses_quarterly_attrs(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_financial_statements(SYMBOL, frequency="quarterly")
        assert result["frequency"] == "quarterly"

    def test_income_stmt_has_date_keys(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_financial_statements(SYMBOL)
        income = result["income_statement"]
        # Keys should be date strings
        assert len(income) > 0
        sample_key = next(iter(income))
        assert "-" in sample_key  # looks like a date

    def test_empty_stmt_returns_empty_dict(self, mock_ticker):
        mock_ticker.income_stmt = pd.DataFrame()
        mock_ticker.balance_sheet = pd.DataFrame()
        mock_ticker.cashflow = pd.DataFrame()
        with patch_ticker(mock_ticker):
            result = server.get_financial_statements(SYMBOL)
        assert result["income_statement"] == {}


# ─────────────────────────────────────────────────────────────
# 12. get_news
# ─────────────────────────────────────────────────────────────


class TestGetNews:
    def test_returns_articles_list(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_news(SYMBOL)
        assert result["symbol"] == "AAPL"
        assert result["count"] == 1
        assert result["articles"][0]["title"] == "Apple Beats Earnings"

    def test_article_fields_populated(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_news(SYMBOL)
        article = result["articles"][0]
        assert article["publisher"] == "Reuters"
        assert article["url"] == "https://reuters.com/apple"
        assert "AAPL" in article["tickers"]

    def test_legacy_news_format(self, mock_ticker):
        # Older yfinance uses flat keys instead of nested "content"
        mock_ticker.news = [
            {
                "title": "Old format news",
                "publisher": "Bloomberg",
                "link": "https://bloomberg.com/news",
                "providerPublishTime": 1706745600,
                "relatedTickers": ["AAPL"],
            }
        ]
        with patch_ticker(mock_ticker):
            result = server.get_news(SYMBOL)
        assert result["articles"][0]["title"] == "Old format news"
        assert result["articles"][0]["publisher"] == "Bloomberg"

    def test_limit_respected(self, mock_ticker):
        mock_ticker.news = mock_ticker.news * 25  # 25 items
        with patch_ticker(mock_ticker):
            result = server.get_news(SYMBOL, limit=5)
        assert result["count"] == 5

    def test_empty_news_list(self, mock_ticker):
        mock_ticker.news = []
        with patch_ticker(mock_ticker):
            result = server.get_news(SYMBOL)
        assert result["count"] == 0


# ─────────────────────────────────────────────────────────────
# 13. get_dividend_history
# ─────────────────────────────────────────────────────────────


class TestGetDividendHistory:
    def test_dividend_records_parsed(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_dividend_history(SYMBOL)
        assert result["symbol"] == "AAPL"
        # 3 non-zero dividends in make_history_df
        assert result["total_payments"] == 3

    def test_annual_dividends_aggregated(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_dividend_history(SYMBOL)
        assert isinstance(result["annual_dividends"], dict)

    def test_last_dividend_present(self, mock_ticker):
        with patch_ticker(mock_ticker):
            result = server.get_dividend_history(SYMBOL)
        assert result["last_dividend"] is not None
        assert result["last_dividend"]["amount"] == pytest.approx(0.24, abs=1e-5)

    def test_no_dividends_returns_empty(self, mock_ticker):
        df = make_history_df()
        df["Dividends"] = 0.0
        mock_ticker.history.return_value = df
        with patch_ticker(mock_ticker):
            result = server.get_dividend_history(SYMBOL)
        assert result["total_payments"] == 0
        assert result["last_dividend"] is None


# ─────────────────────────────────────────────────────────────
# 14. compare_stocks
# ─────────────────────────────────────────────────────────────


class TestCompareStocks:
    def test_returns_sorted_by_return(self, mock_ticker):
        with patch("server.yf.Ticker", return_value=mock_ticker):
            result = server.compare_stocks("AAPL,MSFT,GOOGL")

        assert result["symbols"] == ["AAPL", "MSFT", "GOOGL"]
        returns = [c["period_return_pct"] for c in result["comparison"] if "period_return_pct" in c]
        assert returns == sorted(returns, reverse=True)

    def test_empty_symbols_returns_error(self, mock_ticker):
        result = server.compare_stocks("  ,  ")
        assert "error" in result

    def test_single_symbol(self, mock_ticker):
        with patch("server.yf.Ticker", return_value=mock_ticker):
            result = server.compare_stocks("AAPL")
        assert len(result["comparison"]) == 1

    def test_ticker_exception_handled(self, mock_ticker):
        bad_ticker = MagicMock()
        bad_ticker.info = {}
        bad_ticker.history.side_effect = RuntimeError("network error")
        with patch("server.yf.Ticker", return_value=bad_ticker):
            result = server.compare_stocks("FAIL")
        assert "error" in result["comparison"][0]

    def test_empty_history_marked_as_error(self, mock_ticker):
        mock_ticker.history.return_value = pd.DataFrame()
        with patch("server.yf.Ticker", return_value=mock_ticker):
            result = server.compare_stocks("AAPL")
        assert "error" in result["comparison"][0]


# ─────────────────────────────────────────────────────────────
# 15. search_symbol
# ─────────────────────────────────────────────────────────────


class TestSearchSymbol:
    def test_returns_results(self):
        mock_search = MagicMock()
        mock_search.quotes = [
            {
                "symbol": "AAPL",
                "longname": "Apple Inc.",
                "quoteType": "EQUITY",
                "exchange": "NMS",
                "sector": "Technology",
                "industry": "Consumer Electronics",
            }
        ]
        with patch("yfinance.Search", return_value=mock_search):
            result = server.search_symbol("Apple")

        assert result["query"] == "Apple"
        assert len(result["results"]) == 1
        assert result["results"][0]["symbol"] == "AAPL"

    def test_empty_quotes_list(self):
        mock_search = MagicMock()
        mock_search.quotes = []
        with patch("yfinance.Search", return_value=mock_search):
            result = server.search_symbol("XYZ123")
        assert result["results"] == []

    def test_search_exception_handled(self):
        mock_search = MagicMock()
        # Accessing .quotes raises
        type(mock_search).quotes = property(lambda s: (_ for _ in ()).throw(RuntimeError("err")))
        with patch("yfinance.Search", return_value=mock_search):
            result = server.search_symbol("bad")
        assert "results" in result


# ─────────────────────────────────────────────────────────────
# 16. get_market_overview
# ─────────────────────────────────────────────────────────────


class TestGetMarketOverview:
    def test_returns_all_indices(self, mock_ticker):
        with patch("server.yf.Ticker", return_value=mock_ticker):
            result = server.get_market_overview()

        assert "timestamp" in result
        assert len(result["indices"]) == len(server._INDICES)

    def test_change_pct_computed(self, mock_ticker):
        with patch("server.yf.Ticker", return_value=mock_ticker):
            result = server.get_market_overview()
        # price=175, prev=170 → change_pct ≈ 2.94
        for item in result["indices"]:
            if "change_pct" in item and item.get("change_pct") is not None:
                assert isinstance(item["change_pct"], float)
                break

    def test_individual_ticker_error_isolated(self):
        def ticker_factory(sym):
            t = MagicMock()
            if sym == "^GSPC":
                t.info = {}  # missing price/prev → change_pct None
            else:
                t.info = MOCK_INFO.copy()
            return t

        with patch("server.yf.Ticker", side_effect=ticker_factory):
            result = server.get_market_overview()
        assert "indices" in result

    def test_market_overview_cached(self, mock_ticker):
        with patch("server.yf.Ticker", return_value=mock_ticker) as mock_cls:
            server.get_market_overview()
            server.get_market_overview()
        # 10 indices on first call, 0 on second (cache hit)
        assert mock_cls.call_count == len(server._INDICES)


# ─────────────────────────────────────────────────────────────
# 17. clear_cache
# ─────────────────────────────────────────────────────────────


class TestClearCache:
    def test_clears_populated_cache(self):
        server._cache_set("a", 1)
        server._cache_set("b", 2)
        result = server.clear_cache()
        assert result["cleared"] == 2
        assert result["status"] == "ok"
        assert len(server._CACHE) == 0

    def test_clear_empty_cache(self):
        result = server.clear_cache()
        assert result["cleared"] == 0


# ─────────────────────────────────────────────────────────────
# 18. Internal TA helpers
# ─────────────────────────────────────────────────────────────


class TestTAHelpers:
    def setup_method(self):
        df = make_history_df(n_rows=100)
        self.close = df["Close"]
        self.high = df["High"]
        self.low = df["Low"]

    def test_rsi_range(self):
        rsi = server._compute_rsi(self.close)
        valid = rsi.dropna()
        assert (valid >= 0).all() and (valid <= 100).all()

    def test_macd_returns_three_series(self):
        macd, signal, hist = server._compute_macd(self.close)
        assert len(macd) == len(self.close)
        assert len(signal) == len(self.close)
        assert len(hist) == len(self.close)

    def test_bollinger_upper_gt_lower(self):
        upper, mid, lower = server._compute_bollinger(self.close)
        valid = upper.dropna()
        valid_low = lower.dropna()
        assert (valid.values > valid_low.values).all()

    def test_atr_positive(self):
        atr = server._compute_atr(self.high, self.low, self.close)
        valid = atr.dropna()
        assert (valid > 0).all()

    def test_support_resistance_ordering(self):
        sr = server._support_resistance(self.close)
        assert sr["support"] <= sr["resistance"]
