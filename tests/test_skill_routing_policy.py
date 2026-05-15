import re
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SkillRoutingPolicyTest(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def test_return_opportunity_skill_has_project_safety_boundaries(self):
        text = self.read(".agents/skills/us-stock-return-opportunity/SKILL.md")

        self.assertIn("Return-Seeking US Stock Opportunity Workflow", text)
        self.assertIn("external `us-stock-analysis`", text)
        self.assertIn("risk-manager-investment-memo", text)
        self.assertIn("Do not override project labels", text)
        self.assertIn("invalidation", text.lower())
        self.assertIn("position sizing", text.lower())

    def test_agents_routes_risk_and_return_modes(self):
        text = self.read("AGENTS.md")

        self.assertIn("Default investment workflow is evidence-first risk/reward assessment.", text)
        self.assertIn("use `us-stock-return-opportunity`", text)
        self.assertIn("risk-management verdict controls the final action label", text.lower())

    def test_us_decision_workflow_delegates_explicit_return_requests(self):
        text = self.read(".agents/skills/us-stock-decision-workflow/SKILL.md")

        self.assertIn("Default Mode", text)
        self.assertIn("Return-Seeking Mode", text)
        self.assertIn("us-stock-return-opportunity", text)
        self.assertIn("risk-management verdict controls the final action label", text.lower())

    def test_documented_skill_commands_match_repo_cli(self):
        skill_paths = [
            ".agents/skills/us-stock-decision-workflow/SKILL.md",
            ".agents/skills/us-stock-return-opportunity/SKILL.md",
            ".agents/skills/kr-stock-analysis-review/SKILL.md",
        ]
        commands: list[tuple[str, list[str]]] = []
        for skill_path in skill_paths:
            text = self.read(skill_path)
            self.assertNotIn("scripts/update_asset_bundle.py", text)
            self.assertNotIn("--mode history", text)
            self.assertNotIn("--dated", text)
            for match in re.finditer(r"`uv run python (scripts/[^`]+)`", text):
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
                self.assertIn(flag, help_cache[script_path], f"{flag} missing from {script_path} --help")


if __name__ == "__main__":
    unittest.main()
