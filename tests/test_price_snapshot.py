import unittest
from unittest.mock import MagicMock

import pandas as pd

from scripts.fetch_price_snapshot import (
    fetch_price_snapshot,
    fetch_yfinance_price_snapshot,
    summarize_yfinance_history,
    _normalize_period,
)


def _fake_history(closes, volumes=None):
    volumes = volumes or [1000] * len(closes)
    return pd.DataFrame({"Close": closes, "Volume": volumes})


class SummarizeYfinanceHistoryTest(unittest.TestCase):
    def test_summarizes_multi_row_history_as_history_available(self):
        history = _fake_history([100.0, 105.0, 110.0], [1000, 1100, 1200])
        fast_info = {"currency": "USD", "exchange": "NMS", "marketCap": 3_000_000_000_000}

        result = summarize_yfinance_history(history, fast_info, "aapl")

        self.assertEqual(result["symbol"], "AAPL")
        self.assertEqual(result["source"], "yfinance")
        self.assertEqual(result["currency"], "USD")
        self.assertEqual(result["latest_close"], 110.0)
        self.assertEqual(result["period_return_pct"], 10.0)
        self.assertEqual(result["max_close"], 110.0)
        self.assertEqual(result["min_close"], 100.0)
        self.assertEqual(result["latest_volume"], 1200)
        self.assertEqual(result["points"], 3)
        self.assertTrue(result["history_available"])
        self.assertEqual(result["market_cap"], 3_000_000_000_000)

    def test_single_row_history_is_not_history_available(self):
        history = _fake_history([292.68], [41166897])

        result = summarize_yfinance_history(history, {}, "AAPL")

        self.assertEqual(result["points"], 1)
        self.assertFalse(result["history_available"])

    def test_empty_history_raises_runtime_error(self):
        with self.assertRaises(RuntimeError):
            summarize_yfinance_history(pd.DataFrame({"Close": [], "Volume": []}), {}, "AAPL")

    def test_none_history_raises_runtime_error(self):
        with self.assertRaises(RuntimeError):
            summarize_yfinance_history(None, {}, "AAPL")


class NormalizePeriodTest(unittest.TestCase):
    def test_empty_and_quote_like_values_map_to_a_short_window(self):
        for value in ("", "latest", "quote"):
            self.assertEqual(_normalize_period(value), "5d")

    def test_real_periods_pass_through_lowercased(self):
        self.assertEqual(_normalize_period("1Y"), "1y")
        self.assertEqual(_normalize_period("6mo"), "6mo")


class FetchYfinancePriceSnapshotTest(unittest.TestCase):
    def _make_ticker_factory(self, history, fast_info=None, raise_on_call=None):
        def factory(symbol):
            if raise_on_call is not None:
                raise raise_on_call
            ticker = MagicMock()
            ticker.history.return_value = history
            ticker.fast_info = fast_info or {}
            return ticker

        return factory

    def test_returns_summary_and_fetch_metadata_on_success(self):
        history = _fake_history([244000.0, 259000.0], [26804038, 22263917])
        factory = self._make_ticker_factory(history, {"currency": "KRW", "exchange": "KSC"})

        result = fetch_yfinance_price_snapshot("005930.KS", "1mo", "1d", ticker_factory=factory)

        self.assertEqual(result["summary"]["source"], "yfinance")
        self.assertEqual(result["summary"]["currency"], "KRW")
        self.assertEqual(result["_fetch"]["provider"], "yfinance")
        self.assertEqual(result["_fetch"]["period_used"], "1mo")
        self.assertEqual(result["_fetch"]["attempts"], 1)

    def test_retries_on_transient_failure_then_succeeds(self):
        calls = []
        history = _fake_history([100.0, 101.0])

        def flaky_factory(symbol):
            calls.append(symbol)
            if len(calls) < 3:
                raise RuntimeError("YFRateLimitError: Too Many Requests")
            ticker = MagicMock()
            ticker.history.return_value = history
            ticker.fast_info = {}
            return ticker

        sleeps = []
        result = fetch_yfinance_price_snapshot(
            "MSFT", "1y", "1d", sleep=lambda seconds: sleeps.append(seconds), ticker_factory=flaky_factory
        )

        self.assertEqual(len(calls), 3)
        self.assertEqual(len(sleeps), 2)
        self.assertEqual(result["_fetch"]["attempts"], 3)

    def test_gives_up_after_max_retries_and_raises_runtime_error(self):
        def always_fails(symbol):
            raise RuntimeError("boom")

        with self.assertRaises(RuntimeError) as context:
            fetch_yfinance_price_snapshot(
                "MSFT", "1y", "1d", sleep=lambda seconds: None, ticker_factory=always_fails
            )

        self.assertIn("yfinance fetch failed", str(context.exception))


class FetchPriceSnapshotProviderChainTest(unittest.TestCase):
    def test_default_provider_is_yfinance(self):
        calls = []

        def fake_yfinance(symbol, range_, interval):
            calls.append(symbol)
            return {"summary": {"source": "yfinance"}, "_fetch": {}}

        result = fetch_price_snapshot("AAPL", yfinance_fetcher=fake_yfinance)

        self.assertEqual(result["summary"]["source"], "yfinance")
        self.assertEqual(calls, ["AAPL"])

    def test_unknown_provider_name_raises_value_error(self):
        with self.assertRaises(ValueError):
            fetch_price_snapshot("AAPL", providers=["not-a-real-provider"])

    def test_all_providers_failing_raises_runtime_error_with_attempts(self):
        def failing_yfinance(symbol, range_, interval):
            raise RuntimeError("yfinance fetch failed for AAPL after 3 attempts: boom")

        with self.assertRaises(RuntimeError) as context:
            fetch_price_snapshot("AAPL", yfinance_fetcher=failing_yfinance)

        self.assertIn("all price providers failed", str(context.exception))


if __name__ == "__main__":
    unittest.main()
