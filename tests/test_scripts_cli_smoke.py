"""Generic smoke test: every CLI script under scripts/ must import cleanly and
respond to --help with exit code 0.

This is deliberately dumb and deliberately cheap: no network, no fixtures. Its only
job is to catch a script that is broken before anyone gets to the point of running it
for real -- a syntax error, a bad argparse config, an import that only works from one
cwd, a missing dependency. Those failures are silent otherwise: nothing else in this
test suite imports every script, so a script with zero dedicated test file (like
fetch_sec_companyfacts.py) could ship a broken import and nothing would catch it
until a human ran it manually.
"""

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"


def _discover_cli_scripts() -> list[Path]:
    scripts = []
    for path in sorted(SCRIPTS_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        text = path.read_text(encoding="utf-8")
        if '__name__ == "__main__"' in text and "argparse" in text:
            scripts.append(path)
    return scripts


class ScriptCliSmokeTest(unittest.TestCase):
    def test_at_least_the_known_cli_scripts_are_discovered(self):
        # Guards against the discovery heuristic itself silently finding nothing
        # (e.g. after a refactor that drops the __main__ guard convention).
        found = {path.name for path in _discover_cli_scripts()}
        expected = {
            "build_analysis_bundle.py",
            "build_context_pack.py",
            "fetch_dart_financials.py",
            "fetch_price_snapshot.py",
            "fetch_sec_companyfacts.py",
            "normalize_financials.py",
            "portfolio_snapshot.py",
            "resolve_company.py",
            "update_asset_bundle.py",
            "update_company_bundle.py",
        }
        missing = expected - found
        self.assertFalse(missing, f"expected CLI scripts not discovered: {missing}")

    def test_every_cli_script_responds_to_help_without_network(self):
        failures = {}
        for script in _discover_cli_scripts():
            completed = subprocess.run(
                [sys.executable, str(script), "--help"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if completed.returncode != 0:
                failures[script.name] = completed.stderr.strip()[-2000:]
        self.assertFalse(
            failures,
            "the following scripts failed --help (syntax/import/argparse error, "
            f"not a network issue): {failures}",
        )

    def test_every_cli_script_has_a_dedicated_or_shared_test_file(self):
        # Coverage-gap tripwire, not a correctness check. A script with no test file
        # can still break silently between --help runs (e.g. a bug only reachable
        # once real arguments are parsed and a function body executes).
        covered_by_module_reference = set()
        for test_file in (ROOT / "tests").glob("test_*.py"):
            text = test_file.read_text(encoding="utf-8")
            for script in _discover_cli_scripts():
                module_name = script.stem
                if f"scripts.{module_name}" in text or f"scripts import {module_name}" in text:
                    covered_by_module_reference.add(script.name)
                if f"from scripts import {module_name}" in text:
                    covered_by_module_reference.add(script.name)

        uncovered = {path.name for path in _discover_cli_scripts()} - covered_by_module_reference
        self.assertFalse(
            uncovered,
            "these scripts are exercised only by --help, with no test importing their "
            f"functions: {uncovered}. Add at least a mocked-network unit test.",
        )


if __name__ == "__main__":
    unittest.main()
