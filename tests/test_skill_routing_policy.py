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

        self.assertIn("Default investment workflow is survival-first risk minimization.", text)
        self.assertIn("use `us-stock-return-opportunity`", text)
        self.assertIn("Risk-first verdict controls the final action label", text)

    def test_us_decision_workflow_delegates_explicit_return_requests(self):
        text = self.read(".agents/skills/us-stock-decision-workflow/SKILL.md")

        self.assertIn("Default Mode", text)
        self.assertIn("Return-Seeking Mode", text)
        self.assertIn("us-stock-return-opportunity", text)
        self.assertIn("Risk-first verdict controls the final action label", text)


if __name__ == "__main__":
    unittest.main()
