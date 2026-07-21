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
    def test_normalizes_quote_like_values_and_passes_through_real_periods(self):
        with self.subTest("empty/latest/quote map to a short window"):
            for value in ("", "latest", "quote"):
                self.assertEqual(_normalize_period(value), "5d")

        with self.subTest("real periods pass through lowercased"):
            self.assertEqual(_normalize_period("1Y"), "1y")
            self.assertEqual(_normalize_period("6mo"), "6mo")


class FetchYfinancePriceSnapshotTest(unittest.TestCase):
    def test_succeeds_immediately_or_after_transient_retries(self):
        with self.subTest("succeeds immediately with fetch metadata"):
            history = _fake_history([244000.0, 259000.0], [26804038, 22263917])

            def factory(symbol):
                ticker = MagicMock()
                ticker.history.return_value = history
                ticker.fast_info = {"currency": "KRW", "exchange": "KSC"}
                return ticker

            result = fetch_yfinance_price_snapshot("005930.KS", "1mo", "1d", ticker_factory=factory)

            self.assertEqual(result["summary"]["source"], "yfinance")
            self.assertEqual(result["summary"]["currency"], "KRW")
            self.assertEqual(result["_fetch"]["provider"], "yfinance")
            self.assertEqual(result["_fetch"]["period_used"], "1mo")
            self.assertEqual(result["_fetch"]["attempts"], 1)

        with self.subTest("retries transient failures with backoff then succeeds"):
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
    def test_provider_chain_dispatch_and_failure_modes(self):
        with self.subTest("default provider is yfinance"):
            calls = []

            def fake_yfinance(symbol, range_, interval):
                calls.append(symbol)
                return {"summary": {"source": "yfinance"}, "_fetch": {}}

            result = fetch_price_snapshot("AAPL", yfinance_fetcher=fake_yfinance)
            self.assertEqual(result["summary"]["source"], "yfinance")
            self.assertEqual(calls, ["AAPL"])

        with self.subTest("unknown provider name raises ValueError"):
            with self.assertRaises(ValueError):
                fetch_price_snapshot("AAPL", providers=["not-a-real-provider"])

        with self.subTest("all providers failing raises RuntimeError with attempts"):
            def failing_yfinance(symbol, range_, interval):
                raise RuntimeError("yfinance fetch failed for AAPL after 3 attempts: boom")

            with self.assertRaises(RuntimeError) as context:
                fetch_price_snapshot("AAPL", yfinance_fetcher=failing_yfinance)
            self.assertIn("all price providers failed", str(context.exception))


if __name__ == "__main__":
    unittest.main()
