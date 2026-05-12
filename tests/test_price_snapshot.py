import unittest

from scripts.fetch_price_snapshot import (
    fetch_price_snapshot,
    summarize_nasdaq_quote,
    summarize_stooq_quote_csv,
    summarize_stooq_csv,
    yahoo_symbol_to_stooq,
)


class PriceSnapshotTest(unittest.TestCase):
    def test_summarizes_stooq_csv(self):
        csv_text = "\n".join(
            [
                "Date,Open,High,Low,Close,Volume",
                "2026-01-02,100,101,99,100,1000",
                "2026-01-03,105,106,104,110,1200",
            ]
        )

        result = summarize_stooq_csv(csv_text, "AAPL")

        self.assertEqual(result["symbol"], "AAPL")
        self.assertEqual(result["source"], "stooq_csv")
        self.assertEqual(result["latest_close"], 110.0)
        self.assertEqual(result["period_return_pct"], 10.0)
        self.assertEqual(result["max_close"], 110.0)
        self.assertEqual(result["min_close"], 100.0)
        self.assertEqual(result["latest_volume"], 1200)
        self.assertEqual(result["points"], 2)

    def test_summarizes_stooq_quote_csv(self):
        csv_text = "\n".join(
            [
                "Symbol,Date,Time,Open,High,Low,Close,Volume",
                "AAPL.US,2026-05-11,22:00:19,291.979,293.88,290.23,292.68,41166897",
            ]
        )

        result = summarize_stooq_quote_csv(csv_text, "AAPL")

        self.assertEqual(result["source"], "stooq_quote_csv")
        self.assertEqual(result["regular_market_price"], 292.68)
        self.assertEqual(result["latest_close"], 292.68)
        self.assertEqual(result["latest_volume"], 41166897)
        self.assertEqual(result["points"], 1)

    def test_summarizes_nasdaq_quote(self):
        raw = {
            "data": {
                "symbol": "AAPL",
                "primaryData": {
                    "lastSalePrice": "$292.68",
                    "volume": "42,247,485",
                    "lastTradeTimestamp": "May 11, 2026",
                },
                "keyStats": {"fiftyTwoWeekHighLow": {"value": "193.46 - 294.76"}},
            }
        }

        result = summarize_nasdaq_quote(raw, "AAPL")

        self.assertEqual(result["source"], "nasdaq_quote")
        self.assertEqual(result["regular_market_price"], 292.68)
        self.assertEqual(result["latest_close"], 292.68)
        self.assertEqual(result["latest_volume"], 42247485)
        self.assertEqual(result["min_close"], 193.46)
        self.assertEqual(result["max_close"], 294.76)

    def test_uses_stooq_before_yahoo(self):
        calls = []

        def fake_stooq(symbol, range_, interval):
            calls.append("stooq")
            return {"summary": {"source": "stooq_csv"}, "raw": "csv"}

        def fake_nasdaq(symbol, range_, interval):
            calls.append("nasdaq")
            return {"summary": {"source": "nasdaq_quote"}, "raw": {}}

        def fake_yahoo(symbol, range_, interval):
            calls.append("yahoo")
            return {"summary": {"source": "yahoo_chart"}, "raw": {}}

        result = fetch_price_snapshot("AAPL", stooq_fetcher=fake_stooq, nasdaq_fetcher=fake_nasdaq, yahoo_fetcher=fake_yahoo)

        self.assertEqual(result["summary"]["source"], "stooq_csv")
        self.assertEqual(calls, ["stooq"])

    def test_falls_back_to_nasdaq_when_stooq_fails(self):
        calls = []

        def fake_stooq(symbol, range_, interval):
            calls.append("stooq")
            raise RuntimeError("stooq unavailable")

        def fake_nasdaq(symbol, range_, interval):
            calls.append("nasdaq")
            return {"summary": {"source": "nasdaq_quote"}, "raw": {}}

        def fake_yahoo(symbol, range_, interval):
            calls.append("yahoo")
            return {"summary": {"source": "yahoo_chart"}, "raw": {}}

        result = fetch_price_snapshot("AAPL", stooq_fetcher=fake_stooq, nasdaq_fetcher=fake_nasdaq, yahoo_fetcher=fake_yahoo)

        self.assertEqual(result["summary"]["source"], "nasdaq_quote")
        self.assertEqual(calls, ["stooq", "nasdaq"])
        self.assertEqual(result["_fetch"]["attempts"][0]["provider"], "stooq")
        self.assertIn("stooq unavailable", result["_fetch"]["attempts"][0]["error"])

    def test_maps_plain_us_symbol_to_stooq_us_suffix(self):
        self.assertEqual(yahoo_symbol_to_stooq("AAPL"), "aapl.us")
        self.assertEqual(yahoo_symbol_to_stooq("BRK-B"), "brk-b.us")
        self.assertEqual(yahoo_symbol_to_stooq("005930.KS"), "005930.ks")


if __name__ == "__main__":
    unittest.main()
