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
    def test_update_company_bundle_calls_current_cli_contracts(self):
        with patch.object(update_company_bundle, "run_command") as run_command_mock:
            run_command_mock.side_effect = [
                "data/raw/sec/AAPL_raw.json",
                "data/normalized/AAPL_sec_normalized.json",
                "data/raw/prices/AAPL_price.json",
                "data/reports/AAPL_bundle.md",
            ]

            result = update_company_bundle.update_company_bundle(
                "AAPL",
                "US",
                price_range="6mo",
                price_interval="1d",
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

    def test_update_company_bundle_rejects_non_us_market(self):
        with patch.object(update_company_bundle, "run_command") as run_command_mock:
            with self.assertRaises(SystemExit) as context:
                update_company_bundle.update_company_bundle("005930", "KR")

        self.assertIn("US/SEC only", str(context.exception))
        run_command_mock.assert_not_called()

    def test_update_company_bundle_price_failure_builds_without_price(self):
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

    def test_run_command_returns_last_non_empty_line(self):
        completed = Mock(stdout="\nfirst\n\nsecond\n")
        with patch.object(update_company_bundle.subprocess, "run", return_value=completed) as run_mock:
            self.assertEqual(run_command(["cmd"]), "second")

        run_mock.assert_called_once_with(
            ["cmd"],
            check=True,
            text=True,
            capture_output=True,
            cwd=update_company_bundle.REPO_ROOT,
        )

    def test_run_command_empty_stdout_raises_runtime_error(self):
        completed = Mock(stdout="\n \n")
        with patch.object(update_company_bundle.subprocess, "run", return_value=completed):
            with self.assertRaises(RuntimeError) as context:
                run_command(["cmd"])

        self.assertIn("produced no output", str(context.exception))

    def test_run_command_child_failure_includes_stderr(self):
        error = subprocess.CalledProcessError(
            returncode=2,
            cmd=["cmd"],
            output="line one\nline two\n",
            stderr="bad child",
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
    def test_build_bundle_honors_explicit_paths(self):
        from scripts.build_analysis_bundle import build_bundle

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "reports"
            with unittest.mock.patch("scripts.build_analysis_bundle.now_kst_iso", return_value="2026-05-14T10:00:00+09:00"):
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


if __name__ == "__main__":
    unittest.main()
