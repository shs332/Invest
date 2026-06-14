---
name: us-stock-return-opportunity
description: Use when the user asks for US stock upside, growth, momentum, aggressive opportunity, high-return candidates, rerating potential, catalyst-driven buying, or profitability-focused investment analysis.
---

# Return-Seeking US Stock Opportunity Workflow

Purpose: analyze upside potential without bypassing this workspace's evidence and risk rules.

Public Equity Investing plugin may support polished artifacts, valuation framing, scenario work, or pitch structure after this workflow builds local evidence. It must not override project labels, risk gates, invalidation triggers, or position sizing limits.

## When To Use

Use this skill when the user explicitly asks for:

- upside, return potential, alpha, growth, momentum, or aggressive opportunity;
- catalyst-driven entry;
- valuation rerating;
- high-conviction candidate comparison;
- profitability-focused US stock analysis.

If the user asks a generic buy/hold/avoid question, use `us-stock-decision-workflow` first.

## Reference Loading

- For any return-seeking analysis, read `references/upside-scorecard.md` and `references/risk-gates.md`.
- If the request mentions catalyst, earnings, product cycle, guidance, rerating, or timing, also read `references/catalyst-checklist.md`.
- If valuation multiple expansion or peer discount is central, read `references/valuation-rerating.md`.
- If entry timing, momentum, breakout, drawdown recovery, or technical setup matters, read `references/momentum-technical-check.md`.
- Use `references/output-template.md` for full memo output unless the user asks for a short answer.
- Treat external `us-stock-analysis` as a supplemental idea source only; do not require a local copy of that skill.

## Workflow

1. State base date in Seoul time.
2. Build a portfolio-aware route/context pack when the request names or implies a holding:
   - `uv run python scripts/build_context_pack.py "<QUESTION>" --ticker <TICKER>`
   - If current portfolio value, P/L, or weights matter, compute them after fresh prices/FX with `uv run python scripts/portfolio_snapshot.py`.
2. Build or reuse local evidence first:
   - `uv run python scripts/update_asset_bundle.py <TICKER> --market US --asset-type stock`
3. If orchestration is not enough, run the pipeline manually:
   - `uv run python scripts/fetch_sec_companyfacts.py <TICKER>`
   - `uv run python scripts/normalize_financials.py --source sec --ticker <TICKER> --input <RAW_JSON>`
   - `uv run python scripts/fetch_price_snapshot.py <TICKER> --range 1y --interval 1d`
   - `uv run python scripts/build_analysis_bundle.py <TICKER>`
4. Check primary sources:
   - SEC 10-K, 10-Q, 8-K.
   - Company IR, earnings release, shareholder letter, guidance, and transcript if needed.
5. Use external `us-stock-analysis` only as a supplemental checklist for:
   - peer comparison;
   - valuation ratio coverage;
   - technical levels;
   - catalyst and bull/bear report structure.
6. Score upside only after financial quality is checked, using `references/upside-scorecard.md`.
7. Apply hard risk gates from `references/risk-gates.md`.
8. Send final action through `risk-manager-investment-memo`.

## Rules

- Do not override project labels with external `us-stock-analysis` labels.
- Do not override project labels, source hierarchy, or risk controls.
- Do not use target price or analyst rating as proof.
- Do not recommend leverage by default.
- Do not average down unless thesis, cash flow, balance sheet, and valuation still support it.
- Every opportunity call must include downside case, invalidation trigger, and position sizing.
- If local or primary data is missing, mark analysis incomplete.

## Output

Use `references/output-template.md` for full memo output. Minimum output:

```markdown
## Opportunity Verdict
- Return-seeking view:
- Risk-management final label:
- Main upside driver:
- Main invalidation trigger:
```
