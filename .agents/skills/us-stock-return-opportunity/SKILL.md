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
   - `uv run python scripts/fetch_sec_companyfacts.py <TICKER>`
   - `uv run python scripts/normalize_financials.py --source sec --ticker <TICKER> --input <RAW_JSON>`
   - `uv run python scripts/fetch_price_snapshot.py <TICKER> --range 1y --interval 1d`
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
