import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import update_company_bundle
from scripts.update_company_bundle import run_command


class UpdateCompanyBundleTest(unittest.TestCase):
    def test_update_company_bundle_wires_subprocess_calls_across_scenarios(self):
        with self.subTest("calls current CLI contracts in order and returns the bundle path"):
            with patch.object(update_company_bundle, "run_command") as run_command_mock:
                run_command_mock.side_effect = [
                    "data/raw/sec/AAPL_raw.json",
                    "data/normalized/AAPL_sec_normalized.json",
                    "data/raw/prices/AAPL_price.json",
                    "data/reports/AAPL_bundle.md",
                ]

                result = update_company_bundle.update_company_bundle(
                    "AAPL", "US", price_range="6mo", price_interval="1d"
                )

            self.assertEqual(str(result), "data/reports/AAPL_bundle.md")
            self.assertEqual(
                run_command_mock.call_args_list,
                [
                    unittest.mock.call([
                        sys.executable,
                        str(update_company_bundle.SCRIPT_DIR / "fetch_sec_companyfacts.py"),
                        "AAPL",
                    ], stage="fetch SEC companyfacts"),
                    unittest.mock.call([
                        sys.executable,
                        str(update_company_bundle.SCRIPT_DIR / "normalize_financials.py"),
                        "--source",
                        "sec",
                        "--ticker",
                        "AAPL",
                        "--input",
                        "data/raw/sec/AAPL_raw.json",
                    ], stage="normalize financials"),
                    unittest.mock.call([
                        sys.executable,
                        str(update_company_bundle.SCRIPT_DIR / "fetch_price_snapshot.py"),
                        "AAPL",
                        "--range",
                        "6mo",
                        "--interval",
                        "1d",
                    ], stage="fetch price"),
                    unittest.mock.call([
                        sys.executable,
                        str(update_company_bundle.SCRIPT_DIR / "build_analysis_bundle.py"),
                        "AAPL",
                        "--financials",
                        "data/normalized/AAPL_sec_normalized.json",
                        "--price",
                        "data/raw/prices/AAPL_price.json",
                    ], stage="build bundle"),
                ],
            )

        with self.subTest("rejects non-US market before calling run_command"):
            with patch.object(update_company_bundle, "run_command") as run_command_mock:
                with self.assertRaises(RuntimeError) as context:
                    update_company_bundle.update_company_bundle("005930", "KR")
            self.assertIn("US/SEC only", str(context.exception))
            run_command_mock.assert_not_called()

        with self.subTest("builds without price when the price stage fails"):
            with patch.object(update_company_bundle, "run_command") as run_command_mock:
                run_command_mock.side_effect = [
                    "data/raw/sec/AAPL_raw.json",
                    "data/normalized/AAPL_sec_normalized.json",
                    RuntimeError("price unavailable"),
                    "data/reports/AAPL_bundle.md",
                ]
                with patch("sys.stderr", new_callable=io.StringIO) as stderr:
                    result = update_company_bundle.update_company_bundle("AAPL")

            self.assertEqual(str(result), "data/reports/AAPL_bundle.md")
            self.assertIn("Price fetch failed: price unavailable", stderr.getvalue())
            self.assertEqual(
                run_command_mock.call_args_list[-1],
                unittest.mock.call([
                    sys.executable,
                    str(update_company_bundle.SCRIPT_DIR / "build_analysis_bundle.py"),
                    "AAPL",
                    "--financials",
                    "data/normalized/AAPL_sec_normalized.json",
                ], stage="build bundle"),
            )

    def test_run_command_success_and_failure_modes(self):
        with self.subTest("returns the last non-empty stdout line"):
            completed = Mock(stdout="\nfirst\n\nsecond\n")
            with patch.object(update_company_bundle.subprocess, "run", return_value=completed) as run_mock:
                self.assertEqual(run_command(["cmd"]), "second")
            run_mock.assert_called_once_with(
                ["cmd"], check=True, text=True, capture_output=True, cwd=update_company_bundle.REPO_ROOT
            )

        with self.subTest("empty stdout raises RuntimeError"):
            completed = Mock(stdout="\n \n")
            with patch.object(update_company_bundle.subprocess, "run", return_value=completed):
                with self.assertRaises(RuntimeError) as context:
                    run_command(["cmd"])
            self.assertIn("produced no output", str(context.exception))

        with self.subTest("child process failure includes stage, exit code, and stderr"):
            error = subprocess.CalledProcessError(
                returncode=2, cmd=["cmd"], output="line one\nline two\n", stderr="bad child"
            )
            with patch.object(update_company_bundle.subprocess, "run", side_effect=error):
                with self.assertRaises(RuntimeError) as context:
                    run_command(["cmd"], stage="fetch SEC")
            message = str(context.exception)
            self.assertIn("stage failed: fetch SEC", message)
            self.assertIn("command failed: cmd", message)
            self.assertIn("exit code: 2", message)
            self.assertIn("bad child", message)
            self.assertIn("stdout tail: line two", message)


class BuildBundleExplicitInputTest(unittest.TestCase):
    def test_build_bundle_wires_explicit_paths_into_filing_sources_and_gaps(self):
        from scripts.build_analysis_bundle import build_bundle

        with self.subTest("honors explicit financials/price paths"):
            with tempfile.TemporaryDirectory() as tmp:
                output_dir = Path(tmp) / "reports"
                with unittest.mock.patch(
                    "scripts.build_analysis_bundle.now_kst_iso", return_value="2026-05-14T10:00:00+09:00"
                ):
                    with unittest.mock.patch("scripts.build_analysis_bundle.read_json") as read_json_mock:
                        read_json_mock.side_effect = [
                            {"periods": [{"year": 2024, "revenue": 111}]},
                            {"summary": {"latest_close": 123.45}},
                        ]
                        output = build_bundle(
                            "AAPL",
                            output_dir=output_dir,
                            financials_path="explicit_financials.json",
                            price_path="explicit_price.json",
                        )
                text = output.read_text(encoding="utf-8")
            self.assertIn("- financials: explicit_financials.json", text)
            self.assertIn("- price: explicit_price.json", text)
            self.assertIn("- revenue: 111", text)
            self.assertIn("- latest_close: 123.45", text)

        with self.subTest("includes filing sources, missing valuation slots, and source gaps"):
            with tempfile.TemporaryDirectory() as tmp:
                output_dir = Path(tmp) / "reports"
                with unittest.mock.patch(
                    "scripts.build_analysis_bundle.now_kst_iso", return_value="2026-05-14T10:00:00+09:00"
                ):
                    with unittest.mock.patch("scripts.build_analysis_bundle.read_json") as read_json_mock:
                        read_json_mock.side_effect = [
                            {
                                "ticker": "AAPL",
                                "market": "US",
                                "source": "sec_companyfacts",
                                "cik": "0000320193",
                                "periods": [{"year": 2024, "free_cash_flow": 108807000000}],
                            },
                            {
                                "_fetch": {
                                    "source_url": "https://stooq.com/q/l/?s=aapl.us&f=sd2t2ohlcv&h=&e=csv",
                                    "provider": "stooq",
                                },
                                "summary": {
                                    "latest_close": 123.45,
                                    "history_available": False,
                                    "history_points": 1,
                                },
                            },
                        ]
                        output = build_bundle(
                            "AAPL",
                            output_dir=output_dir,
                            financials_path="explicit_financials.json",
                            price_path="explicit_price.json",
                        )
                text = output.read_text(encoding="utf-8")

            self.assertIn("## Filing Sources", text)
            self.assertIn("- financial_source: sec_companyfacts", text)
            self.assertIn("- cik: 0000320193", text)
            self.assertIn(
                "- price_source_url: https://stooq.com/q/l/?s=aapl.us&f=sd2t2ohlcv&h=&e=csv", text
            )
            self.assertIn("## Valuation Slots", text)
            self.assertIn("- trailing_pe: missing", text)
            self.assertIn("- fcf_yield: missing", text)
            self.assertIn("## Source Gaps", text)
            self.assertIn(
                "- valuation ratios require external/primary market-cap or enterprise-value source", text
            )
            self.assertIn(
                "- price history is quote-only; range return/drawdown needs history-capable provider", text
            )

    def test_build_bundle_computes_valuation_slots_when_market_cap_is_available(self):
        from scripts.build_analysis_bundle import build_bundle

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "reports"
            with unittest.mock.patch("scripts.build_analysis_bundle.now_kst_iso", return_value="2026-07-21T10:00:00+09:00"):
                with unittest.mock.patch("scripts.build_analysis_bundle.read_json") as read_json_mock:
                    read_json_mock.side_effect = [
                        {
                            "ticker": "MSFT",
                            "market": "US",
                            "source": "sec_companyfacts",
                            "cik": "0000789019",
                            "periods": [
                                {"year": 2025, "net_income": 101832000000, "free_cash_flow": 71611000000}
                            ],
                        },
                        {
                            "_fetch": {"provider": "yfinance"},
                            "summary": {
                                "latest_close": 398.45,
                                "history_available": True,
                                "history_points": 252,
                                "market_cap": 2959859898487.93,
                            },
                        },
                    ]
                    output = build_bundle(
                        "MSFT",
                        output_dir=output_dir,
                        financials_path="explicit_financials.json",
                        price_path="explicit_price.json",
                    )

            text = output.read_text(encoding="utf-8")

        self.assertIn("- market_cap: 2959859898487.93", text)
        self.assertIn("- trailing_pe: 29.07", text)
        self.assertIn("- fcf_yield: 2.42%", text)
        self.assertIn(
            "- enterprise_value, forward_pe, and ev_to_ebitda still require a debt/forward-estimate "
            "source beyond market_cap",
            text,
        )
        self.assertNotIn(
            "- valuation ratios require external/primary market-cap or enterprise-value source", text
        )


if __name__ == "__main__":
    unittest.main()
