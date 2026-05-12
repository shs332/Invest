import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from scripts.fetch_sec_companyfacts import (
    choose_companyfacts_output,
    is_fresh_file,
    latest_companyfacts_file,
    should_reuse_companyfacts,
)
from scripts.build_analysis_bundle import build_bundle, latest_artifact_by_name
from scripts.normalize_financials import (
    normalize_dart_financials,
    normalize_file,
    normalize_sec_companyfacts,
    normalized_output_path,
)


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


class SecFetchPolicyTest(unittest.TestCase):
    def test_companyfacts_output_is_gzipped(self):
        path = choose_companyfacts_output("AAPL", Path("data/raw/sec"), date_text="2026-05-12")
        self.assertEqual(path, Path("data/raw/sec/AAPL_2026-05-12_companyfacts.json.gz"))

    def test_latest_companyfacts_accepts_json_and_json_gz(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "AAPL_2026-05-10_companyfacts.json"
            new = root / "AAPL_2026-05-12_companyfacts.json.gz"
            old.write_text("{}", encoding="utf-8")
            new.write_bytes(b"not real gzip needed for selection")
            os.utime(old, (1000, 1000))
            os.utime(new, (2000, 2000))

            self.assertEqual(latest_companyfacts_file("AAPL", root), new)

    def test_is_fresh_file_uses_mtime_age(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AAPL_2026-05-12_companyfacts.json.gz"
            path.write_text("{}", encoding="utf-8")

            self.assertTrue(is_fresh_file(path, stale_days=7))

    def test_is_fresh_file_rejects_stale_mtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AAPL_2026-05-12_companyfacts.json.gz"
            path.write_text("{}", encoding="utf-8")
            old_time = time.time() - (8 * 24 * 60 * 60)
            os.utime(path, (old_time, old_time))

            self.assertFalse(is_fresh_file(path, stale_days=7))

    def test_is_fresh_file_rejects_negative_stale_days(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AAPL_2026-05-12_companyfacts.json.gz"
            path.write_text("{}", encoding="utf-8")

            self.assertFalse(is_fresh_file(path, stale_days=-1))

    def test_should_reuse_companyfacts_respects_cik_and_refresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AAPL_2026-05-12_companyfacts.json.gz"
            path.write_text("{}", encoding="utf-8")

            self.assertTrue(should_reuse_companyfacts(path, refresh=False, cik=None, stale_days=7))
            self.assertFalse(should_reuse_companyfacts(path, refresh=False, cik="0000320193", stale_days=7))
            self.assertFalse(should_reuse_companyfacts(path, refresh=True, cik=None, stale_days=7))


class NormalizedOutputPolicyTest(unittest.TestCase):
    def test_normalized_output_can_be_date_stamped(self):
        path = normalized_output_path("AAPL", "sec", Path("data/normalized"), date_text="2026-05-12")
        self.assertEqual(path, Path("data/normalized/AAPL_2026-05-12_sec_normalized.json"))

    def test_normalized_output_keeps_legacy_default(self):
        path = normalized_output_path("AAPL", "sec", Path("data/normalized"), date_text=None)
        self.assertEqual(path, Path("data/normalized/AAPL_sec_normalized.json"))

    def test_normalize_file_dated_writes_date_stamped_output(self):
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
                    }
                }
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "companyfacts.json"
            output_dir = root / "normalized"
            input_path.write_text(json.dumps(raw), encoding="utf-8")

            output = normalize_file("sec", "AAPL", input_path, output_dir, dated=True)

            self.assertRegex(output.name, r"^AAPL_\d{4}-\d{2}-\d{2}_sec_normalized\.json$")
            self.assertTrue(output.exists())


class BundleSelectionTest(unittest.TestCase):
    def test_latest_artifact_uses_filename_date_before_mtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "AAPL_2026-05-01_sec_normalized.json"
            new = root / "AAPL_2026-05-12_sec_normalized.json"
            old.write_text("{}", encoding="utf-8")
            new.write_text("{}", encoding="utf-8")
            os.utime(new, (1000, 1000))
            os.utime(old, (2000, 2000))

            self.assertEqual(latest_artifact_by_name(root, "AAPL", "*_sec_normalized.json"), new)


class BundleBuildTest(unittest.TestCase):
    def test_build_bundle_honors_explicit_financials_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            auto_dir = root / "data" / "normalized"
            auto_dir.mkdir(parents=True)
            explicit = root / "explicit_financials.json"
            discovered = auto_dir / "AAPL_2026-05-12_sec_normalized.json"
            explicit.write_text(json.dumps({"periods": [{"year": 2024, "revenue": 111}]}), encoding="utf-8")
            discovered.write_text(json.dumps({"periods": [{"year": 2025, "revenue": 999}]}), encoding="utf-8")

            cwd = os.getcwd()
            try:
                os.chdir(root)
                output = build_bundle("AAPL", root / "reports", financials_path=explicit)
            finally:
                os.chdir(cwd)

            text = output.read_text(encoding="utf-8")
            self.assertIn(f"- financials: {explicit}", text)
            self.assertIn("- revenue: 111", text)
            self.assertNotIn("- revenue: 999", text)

    def test_build_bundle_missing_auto_price_writes_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            normalized_dir = root / "data" / "normalized"
            normalized_dir.mkdir(parents=True)
            financials = normalized_dir / "AAPL_2026-05-12_sec_normalized.json"
            financials.write_text(json.dumps({"periods": [{"year": 2024, "revenue": 111}]}), encoding="utf-8")

            cwd = os.getcwd()
            try:
                os.chdir(root)
                output = build_bundle("AAPL", root / "reports")
            finally:
                os.chdir(cwd)

            text = output.read_text(encoding="utf-8")
            self.assertIn("- price: missing", text)

    def test_build_bundle_includes_explicit_price_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financials = root / "financials.json"
            price = root / "price.json"
            financials.write_text(json.dumps({"periods": [{"year": 2024, "revenue": 111}]}), encoding="utf-8")
            price.write_text(json.dumps({"summary": {"close": 123.45, "currency": "USD"}}), encoding="utf-8")

            output = build_bundle("AAPL", root / "reports", financials_path=financials, price_path=price)

            text = output.read_text(encoding="utf-8")
            self.assertIn(f"- price: {price}", text)
            self.assertIn("## Price Summary", text)
            self.assertIn("- close: 123.45", text)
            self.assertIn("- currency: USD", text)


if __name__ == "__main__":
    unittest.main()
