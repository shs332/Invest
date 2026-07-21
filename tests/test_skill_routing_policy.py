import re
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


class SkillRoutingPolicyTest(unittest.TestCase):
    def test_agents_and_readme_document_routing_policy(self):
        agents_text = _read("AGENTS.md")
        readme_text = _read("README.md")

        with self.subTest("risk vs return-seeking routing owns the final label"):
            self.assertIn("Default investment workflow is evidence-first risk/reward assessment.", agents_text)
            self.assertIn("use `us-stock-return-opportunity`", agents_text)
            self.assertIn("risk-management verdict controls the final action label", agents_text.lower())

        with self.subTest("young-investor return tilt still keeps risk gates"):
            self.assertIn("risk-aware growth tilt", agents_text)
            self.assertIn("risk-aware growth tilt", readme_text)
            self.assertIn("수익률 위주", agents_text)
            self.assertIn("position size/cap", agents_text)

        with self.subTest("ETF questions route to the project ETF skill"):
            self.assertIn("use `etf-analysis-review`", agents_text)

        with self.subTest("Public Equity Investing plugin stays supplemental"):
            for text in (agents_text, readme_text):
                self.assertIn("Public Equity Investing", text)
                self.assertIn("supplemental", text.lower())
                self.assertIn("must not override", text.lower())
                self.assertIn("local", text.lower())
            self.assertIn("final action labels", agents_text)
            self.assertIn("screen-grade", readme_text)
            self.assertIn("Korean equities", readme_text)

        with self.subTest("context pack and unified asset bundle scripts documented"):
            for text in (agents_text, readme_text):
                self.assertIn("build_context_pack.py", text)
                self.assertIn("portfolio_snapshot.py", text)
                self.assertIn("update_asset_bundle.py", text)
            self.assertIn("Inline answer by default", readme_text)
            self.assertIn("companies/thesis_tracker.yaml", readme_text)

    def test_skill_files_preserve_safety_boundaries_and_local_control(self):
        skill_paths = [
            ".agents/skills/us-stock-decision-workflow/SKILL.md",
            ".agents/skills/us-stock-return-opportunity/SKILL.md",
            ".agents/skills/kr-stock-analysis-review/SKILL.md",
            ".agents/skills/etf-analysis-review/SKILL.md",
            ".agents/skills/risk-manager-investment-memo/SKILL.md",
        ]
        for skill_path in skill_paths:
            with self.subTest(skill=skill_path):
                text = _read(skill_path)
                self.assertIn("Public Equity Investing", text)
                self.assertIn("must not", text.lower())

        with self.subTest("us-stock-return-opportunity specifics"):
            text = _read(".agents/skills/us-stock-return-opportunity/SKILL.md")
            self.assertIn("Return-Seeking US Stock Opportunity Workflow", text)
            self.assertIn("external `us-stock-analysis`", text)
            self.assertIn("risk-manager-investment-memo", text)
            self.assertIn("Do not override project labels", text)
            self.assertIn("invalidation", text.lower())
            self.assertIn("position sizing", text.lower())
            self.assertIn("small seed", text)
            self.assertIn("weak evidence", text)

        with self.subTest("us-stock-decision-workflow delegates explicit return requests"):
            text = _read(".agents/skills/us-stock-decision-workflow/SKILL.md")
            self.assertIn("Default Mode", text)
            self.assertIn("Return-Seeking Mode", text)
            self.assertIn("us-stock-return-opportunity", text)
            self.assertIn("risk-management verdict controls the final action label", text.lower())

        with self.subTest("etf-analysis-review skill content"):
            text = _read(".agents/skills/etf-analysis-review/SKILL.md")
            self.assertIn("ETF Analysis Review", text)
            self.assertIn("holdings", text.lower())
            self.assertIn("NAV", text)
            self.assertIn("expense ratio", text.lower())
            self.assertIn("tracking", text.lower())
            self.assertIn("Do not run company financial-statement workflows", text)

    def test_documented_skill_commands_match_repo_cli(self):
        skill_paths = [
            ".agents/skills/us-stock-decision-workflow/SKILL.md",
            ".agents/skills/us-stock-return-opportunity/SKILL.md",
            ".agents/skills/kr-stock-analysis-review/SKILL.md",
            ".agents/skills/etf-analysis-review/SKILL.md",
        ]
        commands: list[tuple[str, list[str]]] = []
        for skill_path in skill_paths:
            text = _read(skill_path)
            self.assertNotIn("scripts/update_asset_bundle.py <TICKER> --market KR", text)
            self.assertNotIn("--mode history", text)
            self.assertNotIn("--dated", text)
            for match in re.finditer(r"`(?:UV_CACHE_DIR=.uv-cache )?uv run python (scripts/[^`]+)`", text):
                parts = match.group(1).split()
                commands.append((parts[0], [part for part in parts[1:] if part.startswith("--")]))

        self.assertTrue(commands)
        help_cache: dict[str, str] = {}
        for script_path, flags in commands:
            full_path = ROOT / script_path
            self.assertTrue(full_path.exists(), script_path)
            if script_path not in help_cache:
                completed = subprocess.run(
                    [sys.executable, str(full_path), "--help"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                help_cache[script_path] = completed.stdout
            for flag in flags:
                with self.subTest(script=script_path, flag=flag):
                    self.assertIn(flag, help_cache[script_path])


if __name__ == "__main__":
    unittest.main()
