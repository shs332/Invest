import io
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

from scripts import update_company_bundle
from scripts.update_company_bundle import price_mode_default, run_command, source_for_market


class UpdateCompanyBundleTest(unittest.TestCase):
    def test_source_for_market(self):
        self.assertEqual(source_for_market("US"), "sec")
        self.assertEqual(source_for_market("KR"), "dart")

    def test_price_mode_default(self):
        self.assertEqual(price_mode_default(history=False), "quote")
        self.assertEqual(price_mode_default(history=True), "history")

    def test_update_company_bundle_calls_commands_in_order(self):
        with patch.object(update_company_bundle, "run_command") as run_command_mock:
            run_command_mock.side_effect = [
                "data/raw/sec/AAPL_raw.json",
                "data/normalized/AAPL_normalized.json",
                "data/raw/prices/AAPL_price.json",
                "data/reports/AAPL_bundle.md",
            ]

            result = update_company_bundle.update_company_bundle(
                "AAPL",
                "US",
                stale_days=7,
                price_history=False,
            )

        self.assertEqual(str(result), "data/reports/AAPL_bundle.md")
        self.assertEqual(
            run_command_mock.call_args_list,
            [
                unittest.mock.call([
                    sys.executable,
                    str(update_company_bundle.SCRIPT_DIR / "fetch_sec_companyfacts.py"),
                    "AAPL",
                    "--stale-days",
                    "7",
                ]),
                unittest.mock.call([
                    sys.executable,
                    str(update_company_bundle.SCRIPT_DIR / "normalize_financials.py"),
                    "--source",
                    "sec",
                    "--ticker",
                    "AAPL",
                    "--input",
                    "data/raw/sec/AAPL_raw.json",
                    "--dated",
                ]),
                unittest.mock.call([
                    sys.executable,
                    str(update_company_bundle.SCRIPT_DIR / "fetch_price_snapshot.py"),
                    "AAPL",
                    "--mode",
                    "quote",
                ]),
                unittest.mock.call([
                    sys.executable,
                    str(update_company_bundle.SCRIPT_DIR / "build_analysis_bundle.py"),
                    "AAPL",
                    "--financials",
                    "data/normalized/AAPL_normalized.json",
                    "--price",
                    "data/raw/prices/AAPL_price.json",
                ]),
            ],
        )

    def test_update_company_bundle_price_history_uses_history_mode(self):
        with patch.object(update_company_bundle, "run_command") as run_command_mock:
            run_command_mock.side_effect = [
                "raw.json",
                "normalized.json",
                "price.json",
                "bundle.md",
            ]

            update_company_bundle.update_company_bundle(
                "AAPL",
                "US",
                stale_days=7,
                price_history=True,
            )

        self.assertEqual(run_command_mock.call_args_list[2].args[0][-2:], ["--mode", "history"])

    def test_update_company_bundle_kr_stops_before_commands(self):
        with patch.object(update_company_bundle, "run_command") as run_command_mock:
            with self.assertRaises(SystemExit) as context:
                update_company_bundle.update_company_bundle(
                    "005930",
                    "KR",
                    stale_days=7,
                    price_history=False,
                )

        self.assertIn("DART", str(context.exception))
        run_command_mock.assert_not_called()

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
                run_command(["cmd"])

        message = str(context.exception)
        self.assertIn("command failed: cmd", message)
        self.assertIn("exit code: 2", message)
        self.assertIn("bad child", message)
        self.assertIn("stdout tail: line two", message)

    def test_update_company_bundle_price_failure_builds_without_price(self):
        with patch.object(update_company_bundle, "run_command") as run_command_mock:
            run_command_mock.side_effect = [
                "data/raw/sec/AAPL_raw.json",
                "data/normalized/AAPL_normalized.json",
                RuntimeError("price unavailable"),
                "data/reports/AAPL_bundle.md",
            ]
            with patch("sys.stderr", new_callable=io.StringIO) as stderr:
                result = update_company_bundle.update_company_bundle(
                    "AAPL",
                    "US",
                    stale_days=7,
                    price_history=False,
                )

        self.assertEqual(str(result), "data/reports/AAPL_bundle.md")
        self.assertIn("Price fetch failed: price unavailable", stderr.getvalue())
        self.assertEqual(
            run_command_mock.call_args_list[-1],
            unittest.mock.call([
                sys.executable,
                str(update_company_bundle.SCRIPT_DIR / "build_analysis_bundle.py"),
                "AAPL",
                "--financials",
                "data/normalized/AAPL_normalized.json",
            ]),
        )


if __name__ == "__main__":
    unittest.main()
