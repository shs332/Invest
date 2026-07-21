import os
import unittest
from unittest.mock import patch

from scripts.fetch_dart_financials import fetch_dart_financials
from scripts.normalize_financials import normalize_dart_financials, normalize_sec_companyfacts


class NormalizeFinancialsTest(unittest.TestCase):
    def test_normalizes_sec_companyfacts_annual_cash_flow(self):
        raw = {
            "cik": "0000320193",
            "entityName": "Example Inc.",
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {
                            "USD": [
                                {
                                    "fy": 2023,
                                    "fp": "FY",
                                    "form": "10-K",
                                    "filed": "2024-01-31",
                                    "val": 1000,
                                }
                            ]
                        }
                    },
                    "NetIncomeLoss": {
                        "units": {"USD": [{"fy": 2023, "fp": "FY", "form": "10-K", "filed": "2024-01-31", "val": 100}]}
                    },
                    "NetCashProvidedByUsedInOperatingActivities": {
                        "units": {"USD": [{"fy": 2023, "fp": "FY", "form": "10-K", "filed": "2024-01-31", "val": 160}]}
                    },
                    "PaymentsToAcquirePropertyPlantAndEquipment": {
                        "units": {"USD": [{"fy": 2023, "fp": "FY", "form": "10-K", "filed": "2024-01-31", "val": 50}]}
                    },
                }
            },
        }

        result = normalize_sec_companyfacts(raw, "AAPL")

        self.assertEqual(result["ticker"], "AAPL")
        self.assertEqual(result["source"], "sec_companyfacts")
        self.assertEqual(result["company_name"], "Example Inc.")
        self.assertEqual(result["periods"][0]["year"], 2023)
        self.assertEqual(result["periods"][0]["revenue"], 1000)
        self.assertEqual(result["periods"][0]["free_cash_flow"], 110)

    def test_normalizes_dart_financial_statement_amounts(self):
        raw = {
            "status": "000",
            "list": [
                {"bsns_year": "2023", "account_nm": "매출액", "thstrm_amount": "1,000"},
                {"bsns_year": "2023", "account_nm": "영업이익", "thstrm_amount": "200"},
                {"bsns_year": "2023", "account_nm": "당기순이익", "thstrm_amount": "100"},
                {"bsns_year": "2023", "account_nm": "영업활동 현금흐름", "thstrm_amount": "160"},
                {"bsns_year": "2023", "account_nm": "유형자산의 취득", "thstrm_amount": "50"},
            ],
        }

        result = normalize_dart_financials(raw, "005930", market="KR")

        self.assertEqual(result["ticker"], "005930")
        self.assertEqual(result["market"], "KR")
        self.assertEqual(result["source"], "dart_fnltt")
        self.assertEqual(result["periods"][0]["year"], 2023)
        self.assertEqual(result["periods"][0]["operating_income"], 200)
        self.assertEqual(result["periods"][0]["free_cash_flow"], 110)

    def test_normalize_dart_financials_guards_empty_provider_response(self):
        raw = {"status": "013", "message": "조회된 데이타가 없습니다."}

        with self.subTest("rejects by default"):
            with self.assertRaises(RuntimeError) as context:
                normalize_dart_financials(raw, "005930", market="KR")
            message = str(context.exception)
            self.assertIn("OpenDART returned unusable financial data", message)
            self.assertIn("013", message)
            self.assertIn("조회된 데이타가 없습니다.", message)

        with self.subTest("allows when explicit"):
            result = normalize_dart_financials(raw, "005930", market="KR", allow_empty=True)
            self.assertEqual(result["status"], "013")
            self.assertEqual(result["periods"], [])

    def test_fetch_dart_financials_guards_empty_response_and_loads_project_env(self):
        raw = {"status": "013", "message": "조회된 데이타가 없습니다."}

        with self.subTest("rejects by default"):
            with patch("scripts.fetch_dart_financials.http_json", return_value=raw):
                with self.assertRaises(RuntimeError) as context:
                    fetch_dart_financials("00126380", 2026, "11013", api_key="test-key")
            self.assertIn("OpenDART returned unusable financial data", str(context.exception))

        with self.subTest("allows when explicit"):
            with patch("scripts.fetch_dart_financials.http_json", return_value=raw):
                result = fetch_dart_financials("00126380", 2026, "11013", api_key="test-key", allow_empty=True)
            self.assertEqual(result["status"], "013")
            self.assertEqual(result["_fetch"]["corp_code"], "00126380")

        with self.subTest("loads project .env when no api_key is passed"):
            previous = os.environ.get("OPENDART_API_KEY")
            os.environ.pop("OPENDART_API_KEY", None)

            def load_env() -> dict[str, str]:
                os.environ["OPENDART_API_KEY"] = "from-env-file"
                return {"OPENDART_API_KEY": "from-env-file"}

            try:
                with patch("scripts.fetch_dart_financials.load_project_env", side_effect=load_env):
                    with patch("scripts.fetch_dart_financials.http_json", return_value=raw) as http_json:
                        fetch_dart_financials("00126380", 2026, "11013", allow_empty=True)
            finally:
                if previous is None:
                    os.environ.pop("OPENDART_API_KEY", None)
                else:
                    os.environ["OPENDART_API_KEY"] = previous

            requested_url = http_json.call_args.args[0]
            self.assertIn("crtfc_key=from-env-file", requested_url)


if __name__ == "__main__":
    unittest.main()
