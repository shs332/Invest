# Dual Risk And Return Workflows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let this repo run two explicit US stock analysis modes: survival-first risk minimization by default, and return-seeking opportunity analysis when the user asks for upside, growth, momentum, or aggressive opportunity review.

**Architecture:** Keep `AGENTS.md` as the short routing layer. Keep project-owned workflows under `.agents/skills/`. Add one project-owned return-opportunity skill that can consult the external `skills/us-stock-analysis` reference, then force every final action through the existing risk-manager labels and execution rules. Use small text tests to prevent accidental drift in routing policy.

**Tech Stack:** Markdown project skills, `.codex/config.toml`, Python standard library `unittest`, `uv run python`.

---

## Existing Plan Review

### Reviewed Plans

- `docs/superpowers/plans/2026-05-12-invest-workflow-efficiency.md`
- `docs/superpowers/plans/2026-05-12-broad-invest-analysis-coverage.md`

These two source plans were deleted after this merge because the useful parts are captured below and the remaining work is either already implemented or intentionally out of scope for this plan.

### Merged From `2026-05-12-invest-workflow-efficiency.md`

- Reuse the already implemented local pipeline shape: `fetch -> normalize -> bundle -> memo`.
- Preserve the local-first rule: use `uv run python scripts/update_company_bundle.py <TICKER> --market US` before ad hoc web-only analysis when a relevant script exists.
- Preserve generated-data policy: raw/cache/report payloads stay local; final human-readable notes belong under `memos/`.
- Keep bundle generation tolerant of missing price/provider data; missing data should mark analysis incomplete, not block the memo path.

Not merged: compression/stale-fetch implementation tasks, because current repo already has the relevant script and test files.

### Merged From `2026-05-12-broad-invest-analysis-coverage.md`

- Borrow the idea of explicit instrument/workflow routing, but scope this plan to US stock risk-vs-return mode separation.
- Borrow the source hierarchy discipline: primary sources and local artifacts outrank market-site summaries.
- Borrow the idea that ETF or broader asset work should remain separate from company financial-statement analysis.

Not merged: ETF resolver/profile/holdings/bundle tasks, because they are a separate asset-class expansion and would distract from the current risk-vs-return workflow goal.

## Target Behavior

- Default US stock judgment uses `us-stock-decision-workflow`.
- Return-seeking US stock requests use new `us-stock-return-opportunity`.
- Ambiguous requests should show both lenses briefly, with risk-first action label controlling the final decision.
- External `skills/us-stock-analysis` stays a supplemental reference. It can inform peer comparison, technical levels, valuation ratios, and bull/bear report shape. It must not override project labels, source hierarchy, or position-sizing rules.
- Final labels remain only: `Buy`, `Watch`, `Hold`, `Trim`, `Avoid`, `Increase Cash`.

## File Map

- Create: `.agents/skills/us-stock-return-opportunity/SKILL.md`
- Modify: `.codex/config.toml`
- Modify: `AGENTS.md`
- Modify: `.agents/skills/us-stock-decision-workflow/SKILL.md`
- Create: `tests/test_skill_routing_policy.py`

## Task 1: Add Return-Opportunity Skill

**Files:**
- Create: `.agents/skills/us-stock-return-opportunity/SKILL.md`
- Test: `tests/test_skill_routing_policy.py`

- [ ] **Step 1: Create policy test for new skill**

Create `tests/test_skill_routing_policy.py`:

```python
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

    def test_config_enables_return_opportunity_skill(self):
        text = self.read(".codex/config.toml")

        self.assertIn('path = ".agents/skills/us-stock-return-opportunity"', text)
        self.assertIn("enabled = true", text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
uv run python -m unittest tests.test_skill_routing_policy -v
```

Expected: fail because `.agents/skills/us-stock-return-opportunity/SKILL.md` does not exist and routing text is not yet present.

- [ ] **Step 3: Add return-opportunity skill**

Create `.agents/skills/us-stock-return-opportunity/SKILL.md`:

````markdown
---
name: us-stock-return-opportunity
description: Use when the user asks for US stock upside, growth, momentum, aggressive opportunity, high-return candidates, rerating potential, catalyst-driven buying, or profitability-focused investment analysis.
---

# Return-Seeking US Stock Opportunity Workflow

Purpose: analyze upside potential without bypassing this workspace's evidence and risk rules.

## When To Use

Use this skill when the user explicitly asks for:

- upside, return potential, alpha, growth, momentum, or aggressive opportunity;
- catalyst-driven entry;
- valuation rerating;
- high-conviction candidate comparison;
- profitability-focused US stock analysis.

If the user asks a generic buy/hold/avoid question, use `us-stock-decision-workflow` first.

## Workflow

1. State base date in Seoul time.
2. Build or reuse local evidence first:
   - `uv run python scripts/update_company_bundle.py <TICKER> --market US`
   - `uv run python scripts/fetch_price_snapshot.py <TICKER> --mode history`
   - `uv run python scripts/build_analysis_bundle.py <TICKER>`
3. Check primary sources:
   - SEC 10-K, 10-Q, 8-K.
   - Company IR, earnings release, shareholder letter, guidance, and transcript if needed.
4. Use external `us-stock-analysis` only as a supplemental checklist for:
   - peer comparison;
   - valuation ratio coverage;
   - technical levels;
   - catalyst and bull/bear report structure.
5. Score upside only after financial quality is checked:
   - revenue growth and durability;
   - margin expansion potential;
   - free cash flow conversion;
   - balance sheet capacity;
   - valuation rerating path;
   - catalyst timing;
   - relative strength and technical setup.
6. Send final action through `risk-manager-investment-memo`.

## Rules

- Do not override project labels with external `us-stock-analysis` labels.
- Do not override project labels, source hierarchy, or survival-first constraints.
- Do not use target price or analyst rating as proof.
- Do not recommend leverage by default.
- Do not average down unless thesis, cash flow, balance sheet, and valuation still support it.
- Every opportunity call must include downside case, invalidation trigger, and position sizing.
- If local or primary data is missing, mark analysis incomplete.

## Output

```markdown
## Opportunity Verdict
- Return-seeking view:
- Risk-first final label:
- Main upside driver:
- Main invalidation trigger:

## Evidence Base
- Base date:
- Local artifacts:
- Primary sources:
- Missing data:

## Upside Case
- Growth driver:
- Margin/FCF driver:
- Rerating driver:
- Catalyst:
- Technical setup:

## Risk Gate
- Financial quality:
- Balance sheet:
- Valuation heat:
- Bubble/narrative risk:
- Downside scenario:

## Supplemental Checklist From `us-stock-analysis`
- Peer comparison:
- Valuation ratio coverage:
- Technical level:
- Bull/bear structure:
- What changed after supplemental check:

## Execution Rules
- New entry:
- Current holding:
- Position sizing:
- Trim rule:
- Exit rule:
```
````

- [ ] **Step 4: Run policy test**

Run:

```bash
uv run python -m unittest tests.test_skill_routing_policy -v
```

Expected: still fails because `AGENTS.md` and `.codex/config.toml` are not updated yet.

## Task 2: Register Skill And Route Modes In `AGENTS.md`

**Files:**
- Modify: `.codex/config.toml`
- Modify: `AGENTS.md`
- Test: `tests/test_skill_routing_policy.py`

- [ ] **Step 1: Register project skill**

Append to `.codex/config.toml`:

```toml

[[skills.config]]
path = ".agents/skills/us-stock-return-opportunity"
enabled = true
```

- [ ] **Step 2: Add `AGENTS.md` routing policy**

Append these lines after the existing US stock judgment rule in `AGENTS.md`:

```markdown
- Default investment workflow is survival-first risk minimization.
- For return-seeking US stock analysis, use project-owned `us-stock-return-opportunity` when the user explicitly asks for upside, growth, momentum, alpha, aggressive opportunity, rerating, or catalyst-driven buying.
- If the user request is ambiguous, present both lenses briefly: risk-first verdict and return-opportunity verdict. Risk-first verdict controls the final action label.
- External `us-stock-analysis` remains a supplemental checklist only; it must not override project labels, source hierarchy, position sizing, or survival-first rules.
```

- [ ] **Step 3: Run policy test**

Run:

```bash
uv run python -m unittest tests.test_skill_routing_policy -v
```

Expected: pass for the current return-opportunity skill, config, and `AGENTS.md` checks.

## Task 3: Update US Decision Workflow To Delegate Return Mode

**Files:**
- Modify: `.agents/skills/us-stock-decision-workflow/SKILL.md`
- Test: `tests/test_skill_routing_policy.py`

- [ ] **Step 1: Extend policy test**

Add this method to `tests/test_skill_routing_policy.py`:

```python
    def test_us_decision_workflow_delegates_explicit_return_requests(self):
        text = self.read(".agents/skills/us-stock-decision-workflow/SKILL.md")

        self.assertIn("Default Mode", text)
        self.assertIn("Return-Seeking Mode", text)
        self.assertIn("us-stock-return-opportunity", text)
        self.assertIn("Risk-first verdict controls the final action label", text)
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
uv run python -m unittest tests.test_skill_routing_policy -v
```

Expected: fail because `us-stock-decision-workflow` does not yet define the two modes.

- [ ] **Step 3: Add mode routing section**

In `.agents/skills/us-stock-decision-workflow/SKILL.md`, add this section after `Purpose`:

```markdown
## Mode Routing

### Default Mode

Use this workflow for generic US stock judgment, company analysis, valuation, peer comparison, price-move interpretation, or buy/hold/avoid decision support.

### Return-Seeking Mode

If the user explicitly asks for upside, growth, momentum, alpha, aggressive opportunity, rerating, or catalyst-driven buying, call `us-stock-return-opportunity` after local evidence and primary-source checks.

Risk-first verdict controls the final action label. The return-seeking view can raise interest level, but it cannot remove invalidation triggers, position sizing, or downside controls.
```

- [ ] **Step 4: Run policy test**

Run:

```bash
uv run python -m unittest tests.test_skill_routing_policy -v
```

Expected: pass.

## Task 4: Verify Skill Discoverability

**Files:**
- No source changes unless verification exposes missing config.

- [ ] **Step 1: Confirm file layout**

Run:

```bash
find .agents/skills -maxdepth 2 -type f -name 'SKILL.md' -print | sort
```

Expected output includes:

```text
.agents/skills/us-stock-return-opportunity/SKILL.md
```

- [ ] **Step 2: Confirm model-visible prompt input when available**

Run:

```bash
codex debug prompt-input > /tmp/invest_prompt_input.json
rg -n "us-stock-return-opportunity|us-stock-decision-workflow|risk-manager-investment-memo" /tmp/invest_prompt_input.json
```

Expected: all three skill names appear.

If `codex debug prompt-input` is unavailable in the current runtime, run the policy test and file-layout check, then note discoverability remains unverified.

## Task 5: Final Verification

**Files:**
- All changed files.

- [ ] **Step 1: Run policy test**

Run:

```bash
uv run python -m unittest tests.test_skill_routing_policy -v
```

Expected: pass.

- [ ] **Step 2: Run full unit suite**

Run:

```bash
uv run python -m unittest discover -s tests -v
```

Expected: pass.

- [ ] **Step 3: Inspect final diff**

Run:

```bash
git diff -- AGENTS.md .codex/config.toml .agents/skills/us-stock-decision-workflow/SKILL.md .agents/skills/us-stock-return-opportunity/SKILL.md tests/test_skill_routing_policy.py
```

Expected:

- `AGENTS.md` contains mode routing.
- `.codex/config.toml` enables `us-stock-return-opportunity`.
- `us-stock-decision-workflow` keeps survival-first default and delegates explicit return-seeking mode.
- `us-stock-return-opportunity` says external `us-stock-analysis` is supplemental only.
- Tests assert routing policy text.

## Success Criteria

- Generic US stock judgment still defaults to survival-first risk minimization.
- Explicit return-seeking requests route to `us-stock-return-opportunity`.
- Final action labels remain project-owned conditional labels.
- External `skills/us-stock-analysis` remains supplemental and reinstallable, not a project policy source.
- `AGENTS.md` stays short and only holds routing/priority rules.
- Policy test and full unit suite pass.

## Execution Order

1. Add `tests/test_skill_routing_policy.py`.
2. Add `.agents/skills/us-stock-return-opportunity/SKILL.md`.
3. Register new skill in `.codex/config.toml`.
4. Add routing lines to `AGENTS.md`.
5. Add mode routing to `.agents/skills/us-stock-decision-workflow/SKILL.md`.
6. Verify with policy test, full unit suite, and `codex debug prompt-input` when available.
