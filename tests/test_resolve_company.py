import json
import tempfile
import unittest
from pathlib import Path

from scripts.resolve_company import resolve_kr_company, resolve_us_company


class ResolveCompanyTest(unittest.TestCase):
    def test_resolves_us_by_ticker_from_sec_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sec_company_tickers.json"
            cache.write_text(
                json.dumps(
                    {
                        "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
                        "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corp"},
                    }
                ),
                encoding="utf-8",
            )

            matches = resolve_us_company("aapl", cache)

            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["ticker"], "AAPL")
            self.assertEqual(matches[0]["cik"], "0000320193")
            self.assertEqual(matches[0]["confidence"], "exact_ticker")

    def test_resolves_kr_by_stock_code_from_dart_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "dart_corp_codes.json"
            cache.write_text(
                json.dumps(
                    [
                        {"corp_code": "00126380", "corp_name": "삼성전자", "stock_code": "005930", "modify_date": "20240101"},
                        {"corp_code": "00164779", "corp_name": "삼성전자우", "stock_code": "005935", "modify_date": "20240101"},
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            matches = resolve_kr_company("005930", cache)

            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["ticker"], "005930")
            self.assertEqual(matches[0]["corp_code"], "00126380")
            self.assertEqual(matches[0]["confidence"], "exact_stock_code")


if __name__ == "__main__":
    unittest.main()

