---
name: us-stock-decision-workflow
description: Use when the user asks for US stock investment judgment, company analysis, valuation, peer comparison, price-move interpretation, or buy/hold/avoid decision support.
---

# US Stock Decision Workflow

Purpose: make the project-local evidence pipeline the primary engine for US stock analysis, while using the external `us-stock-analysis` skill only as a supplemental checklist.

Public Equity Investing plugin is also supplemental for this workflow. Use it only after local evidence and primary-source checks when the user needs an institutional-style artifact such as a tearsheet, earnings report, comps/DCF package, memo, pitch, scenario, or QC review. It must not override this project's labels, source hierarchy, position sizing, or risk controls.

## Mode Routing

### Default Mode

Use this workflow for generic US stock judgment, company analysis, valuation, peer comparison, price-move interpretation, or buy/hold/avoid decision support.

### Return-Seeking Mode

If the user explicitly asks for upside, growth, momentum, alpha, aggressive opportunity, rerating, or catalyst-driven buying, call `us-stock-return-opportunity` after local evidence and primary-source checks.

Risk-management verdict controls the final action label. The return-seeking view can raise interest level, but it cannot remove invalidation triggers, position sizing, or downside controls.

## Priority Order

1. State base date in Seoul time.
2. Build a portfolio-aware route/context pack when the request names or implies a holding:
   - `uv run python scripts/build_context_pack.py "<QUESTION>" --ticker <TICKER>`
   - If current portfolio value, P/L, or weights matter, compute them after fresh prices/FX with `uv run python scripts/portfolio_snapshot.py`.
2. Use local artifacts and scripts first when available:
   - `uv run python scripts/update_asset_bundle.py <TICKER> --market US --asset-type stock`
3. If orchestration is not enough, run the pipeline manually:
   - `uv run python scripts/fetch_sec_companyfacts.py <TICKER>`
   - `uv run python scripts/normalize_financials.py --source sec --ticker <TICKER> --input <RAW_JSON>`
   - `uv run python scripts/fetch_price_snapshot.py <TICKER> --range 1y --interval 1d`
   - `uv run python scripts/build_analysis_bundle.py <TICKER>`
4. Check primary sources:
   - SEC 10-K, 10-Q, 8-K.
   - Company IR, earnings release, shareholder letter, transcript if needed.
   - Exchange data for price/volume context.
5. Apply project-owned analysis:
   - `financial-statement-review` for financial quality.
   - `market-move-explainer` for recent move cause.
   - `risk-manager-investment-memo` for final action label and execution rules.
6. Use external `us-stock-analysis` only after the above, as a completeness checklist for:
   - peer comparison;
   - valuation ratio coverage;
   - technical levels;
   - bull/bear report structure.

## Rules

- Primary sources outrank secondary market sites.
- News, analyst targets, technical indicators, and Yahoo-style metrics are context, not proof.
- Do not let the external skill's `Buy/Hold/Sell`, target price, or conviction wording override this project's conditional labels.
- Use only these action labels: `Buy`, `Watch`, `Hold`, `Trim`, `Avoid`, `Increase Cash`.
- Keep analysis risk-aware: downside control, no leverage by default, cash as a valid position, no averaging down unless thesis, cash flow, balance sheet, and valuation still support it.
- If local or primary data is missing, mark the answer incomplete instead of filling gaps with guesses.

## Output

Use this structure unless the user asks for a shorter answer:

```markdown
## 3-Line Conclusion
- Conditional action:
- Main reason:
- Main invalidation trigger:

## Evidence Base
- Base date:
- Local artifacts:
- Primary sources:
- Missing data:

## Financial Quality
- Growth:
- Profitability:
- Cash conversion:
- Balance sheet:
- Red flags:

## Valuation And Context
| Metric | Current | Context | Interpretation |
|---|---:|---|---|

## Supplemental Checklist
- Peer comparison:
- Technical level:
- Analyst/news context:
- What changed after checking `us-stock-analysis`:

## Execution Rules
- New entry:
- Current holding:
- Max weight / trim rule:
- Exit rule:
```
