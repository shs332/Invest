---
name: etf-analysis-review
description: Use when the user asks whether an ETF is worth buying, holding, trimming, avoiding, comparing, or watching, including US ETFs, Korean ETFs, sector ETFs, bond ETFs, dividend ETFs, leveraged/inverse ETF risk checks, or ETF price-move questions.
---

# ETF Analysis Review

Purpose: analyze ETFs using fund-specific evidence. ETF judgment must not be forced through company financial-statement workflows.

## When To Use

Use for ETFs, funds, index products, sector baskets, bond ETFs, commodity ETFs, dividend ETFs, thematic ETFs, leveraged ETFs, inverse ETFs, and Korea-listed ETFs.

Do not run company financial-statement workflows for ETF analysis. For ETFs, holdings, index exposure, NAV, expense ratio, liquidity, distribution policy, and tracking behavior matter more than operating revenue, margins, cash flow, or corporate debt.

## Workflow

1. State base date in Seoul time.
2. Fetch price context when useful:
   - `uv run python scripts/fetch_price_snapshot.py <ETF_SYMBOL> --range 1y --interval 1d`
3. Check primary or issuer-level sources first:
   - ETF issuer fund page.
   - Prospectus or summary prospectus.
   - Holdings file or portfolio composition page.
   - Index methodology page for passive ETFs.
   - Exchange quote page for price, volume, and trading status.
4. Review ETF-specific evidence:
   - Objective and index tracked.
   - Holdings concentration and top 10 weight.
   - Sector, country, currency, duration, credit, commodity, or factor exposure.
   - Expense ratio and other fund costs.
   - AUM, average volume, bid/ask spread, and liquidity risk.
   - NAV premium/discount when available.
   - Tracking difference or tracking error when available.
   - Distribution yield, payout policy, and tax/currency considerations.
   - Leverage, inverse reset risk, derivative use, and path dependency when relevant.
5. Compare alternatives when the user asks for a choice:
   - Same exposure cheaper.
   - Same issuer family alternative.
   - Broader index alternative.
   - Cash or short-duration alternative when risk/reward is weak.
6. Send final action through `risk-manager-investment-memo` only after ETF-specific evidence is summarized.

## Output

```markdown
## 3-Line Conclusion
- Conditional action:
- Main reason:
- Main invalidation trigger:

## Source Base
- Base date:
- Primary/issuer sources:
- Price source:
- Missing data:

## ETF Exposure
- Objective/index:
- Top holdings/concentration:
- Sector/country/currency exposure:
- Duration/credit/commodity/factor exposure:

## Cost And Trading Quality
- Expense ratio:
- AUM/liquidity:
- Bid/ask spread:
- NAV premium/discount:
- Tracking quality:

## Risk/Reward
- Bull case:
- Bear case:
- Key risks:

## Execution Rules
- New entry:
- Current holding:
- Max weight / trim rule:
- Exit rule:
```

## Decision Labels

Use conditional labels only:

- `Buy`: exposure is useful, cost/liquidity are acceptable, and downside is bounded.
- `Watch`: exposure is interesting, but valuation, timing, liquidity, or source data is incomplete.
- `Hold`: existing position still fits the portfolio, but new buying is not obvious.
- `Trim`: exposure, concentration, valuation, liquidity, or macro risk has become too high.
- `Avoid`: product structure, liquidity, leverage, tracking, or exposure risk is unclear or unfavorable.
- `Increase Cash`: uncertainty is high or ETF evidence is weak.

## Rules

- Do not treat ETF holdings as if the ETF itself has operating margins or free cash flow.
- Do not recommend leveraged or inverse ETFs for long-term holding by default.
- Do not treat yield as return without checking distribution source and price erosion.
- If holdings, expense ratio, or NAV/tracking data is missing, mark analysis incomplete.
