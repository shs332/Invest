import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.resolve_company import ensure_dart_cache, resolve_kr_company, resolve_us_company


class ResolveCompanyTest(unittest.TestCase):
    def test_resolves_us_ticker_and_kr_stock_code_from_their_caches(self):
        with self.subTest("US ticker via SEC cache"):
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

        with self.subTest("KR stock code via DART cache"):
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

    def test_ensure_dart_cache_loads_project_env_when_called_as_function(self):
        previous = os.environ.get("OPENDART_API_KEY")
        os.environ.pop("OPENDART_API_KEY", None)

        def load_env() -> dict[str, str]:
            os.environ["OPENDART_API_KEY"] = "from-env-file"
            return {"OPENDART_API_KEY": "from-env-file"}

        xml_text = (
            "<result>"
            "<list>"
            "<corp_code>00126380</corp_code>"
            "<corp_name>삼성전자</corp_name>"
            "<stock_code>005930</stock_code>"
            "<modify_date>20240101</modify_date>"
            "</list>"
            "</result>"
        )

        try:
            with tempfile.TemporaryDirectory() as tmp:
                cache = Path(tmp) / "dart_corp_codes.json"
                with patch("scripts.resolve_company.load_project_env", side_effect=load_env):
                    with patch("scripts.resolve_company.http_bytes", return_value=b"zip") as http_bytes:
                        with patch("scripts.resolve_company.read_zip_text", return_value=xml_text):
                            ensure_dart_cache(cache, refresh=True)
        finally:
            if previous is None:
                os.environ.pop("OPENDART_API_KEY", None)
            else:
                os.environ["OPENDART_API_KEY"] = previous

        requested_url = http_bytes.call_args.args[0]
        self.assertIn("crtfc_key=from-env-file", requested_url)


if __name__ == "__main__":
    unittest.main()
