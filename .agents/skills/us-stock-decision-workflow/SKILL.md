---
name: us-stock-decision-workflow
description: Use when the user asks for US stock investment judgment, company analysis, valuation, peer comparison, price-move interpretation, or buy/hold/avoid decision support.
---

# US Stock Decision Workflow

Purpose: make the project-local evidence pipeline the primary engine for US stock analysis, while using the external `us-stock-analysis` skill only as a supplemental checklist.

## Priority Order

1. State base date in Seoul time.
2. Use local artifacts and scripts first:
   - `uv run python scripts/update_company_bundle.py <TICKER> --market US`
   - `uv run python scripts/fetch_price_snapshot.py <TICKER> --mode history`
   - `uv run python scripts/build_analysis_bundle.py <TICKER>`
3. Check primary sources:
   - SEC 10-K, 10-Q, 8-K.
   - Company IR, earnings release, shareholder letter, transcript if needed.
   - Exchange data for price/volume context.
4. Apply project-owned analysis:
   - `financial-statement-review` for financial quality.
   - `market-move-explainer` for recent move cause.
   - `risk-manager-investment-memo` for final action label and execution rules.
5. Use external `us-stock-analysis` only after the above, as a completeness checklist for:
   - peer comparison;
   - valuation ratio coverage;
   - technical levels;
   - bull/bear report structure.

## Rules

- Primary sources outrank secondary market sites.
- News, analyst targets, technical indicators, and Yahoo-style metrics are context, not proof.
- Do not let the external skill's `Buy/Hold/Sell`, target price, or conviction wording override this project's conditional labels.
- Use only these action labels: `Buy`, `Watch`, `Hold`, `Trim`, `Avoid`, `Increase Cash`.
- Keep survival first: loss control, no leverage by default, cash as a valid position, no averaging down unless thesis, cash flow, balance sheet, and valuation still support it.
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
