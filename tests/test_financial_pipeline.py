import unittest

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


if __name__ == "__main__":
    unittest.main()

