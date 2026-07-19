---
name: etf-analysis-review
description: Use when the user asks whether an ETF is worth buying, holding, trimming, avoiding, comparing, or watching, including US ETFs, Korean ETFs, sector ETFs, bond ETFs, dividend ETFs, commodity or gold ETFs, geopolitical or inflation hedges, leveraged/inverse ETF risk checks, or ETF price-move questions.
---

# ETF Analysis Review

Purpose: analyze ETFs using fund-specific evidence. ETF judgment must not be forced through company financial-statement workflows.

Public Equity Investing plugin can help with ETF/index constituent diligence, PM-style risk framing, scenario analysis, or polished artifacts after ETF issuer and index evidence is checked. It must not replace ETF-specific evidence such as holdings, NAV, expense ratio, tracking, liquidity, distribution policy, leverage/inverse structure, tax, and currency exposure.

## When To Use

Use for ETFs, funds, index products, sector baskets, bond ETFs, commodity ETFs, dividend ETFs, thematic ETFs, leveraged ETFs, inverse ETFs, and Korea-listed ETFs.

Do not run company financial-statement workflows for ETF analysis. For ETFs, holdings, index exposure, NAV, expense ratio, liquidity, distribution policy, and tracking behavior matter more than operating revenue, margins, cash flow, or corporate debt.

## Required Inputs

- Fund ticker or exact fund name.
- Intended role and horizon: core exposure, income, hedge, tactical trade, or satellite.
- Portfolio context when the user asks about fit or position size.
- Account, tax residency, or broker constraints when product structure can affect eligibility or withholding.

## Workflow

1. State base date in Seoul time.
2. Build a portfolio-aware route/context pack when the request names or implies a holding:
   - `UV_CACHE_DIR=.uv-cache uv run python scripts/build_context_pack.py "<QUESTION>" --ticker <ETF_SYMBOL>`
   - If current portfolio value, P/L, or weights matter, compute them after fresh prices/FX with `UV_CACHE_DIR=.uv-cache uv run python scripts/portfolio_snapshot.py`.
3. Fetch price context when useful:
   - `UV_CACHE_DIR=.uv-cache uv run python scripts/update_asset_bundle.py <ETF_SYMBOL> --market US --asset-type ETF`
   - `UV_CACHE_DIR=.uv-cache uv run python scripts/fetch_price_snapshot.py <ETF_SYMBOL> --range 1y --interval 1d`
4. Check primary or issuer-level sources first:
   - ETF issuer fund page.
   - Prospectus or summary prospectus.
   - Holdings file or portfolio composition page.
   - Index methodology page for passive ETFs.
   - Exchange quote page for price, volume, and trading status.
5. Review ETF-specific evidence:
   - Objective and index tracked.
   - Holdings concentration and top 10 weight.
   - Sector, country, currency, duration, credit, commodity, or factor exposure.
   - Expense ratio and other fund costs.
   - AUM, average volume, bid/ask spread, and liquidity risk.
   - NAV premium/discount when available.
   - Tracking difference or tracking error when available.
   - Distribution yield, payout policy, and tax/currency considerations.
   - Leverage, inverse reset risk, derivative use, and path dependency when relevant.
6. For commodity or gold products, run the conditional checks below.
7. Compare alternatives when the user asks for a choice:
   - Same exposure cheaper.
   - Same issuer family alternative.
   - Broader index alternative.
   - Cash or short-duration alternative when risk/reward is weak.
8. Send final action through `risk-manager-investment-memo` only after ETF-specific evidence is summarized.

## Commodity And Gold Checks

1. Classify the structure from issuer documents: physically backed trust, futures-based fund, commodity-producer equity fund, or ETN.
2. For physically backed products, check custody/backing, sponsor fee, tracking drag, liquidity, and the effects of real yields, the US dollar, official-sector demand, and ETF flows.
3. For futures-based products, check current commodity weights, energy concentration, roll schedule, contango/backwardation, collateral return, derivative counterparties, and volatility.
4. Check product-specific tax and broker constraints, including K-1/PTP or Section 1446(f) treatment when relevant. Mark unresolved eligibility or withholding as a pre-trade blocker.
5. Define the portfolio role before sizing. Treat hedges and diversifiers as bounded satellite positions with staged entry, a maximum weight, rebalance rule, and scenario-based invalidation.
6. Compare a cheaper or operationally simpler product with the same intended exposure when one exists.

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

## Validation And Failure Cases

- Confirm ticker, exposure, and legal structure from the issuer page or prospectus; do not infer structure from the fund name.
- If the local router treats a commodity product as an operating company, override that route and use this ETF workflow.
- If local price history is unavailable or quote-only, use a fresh external quote only for current sizing and mark return, drawdown, and volatility history incomplete.
- Reconcile proposed sizing to a fresh portfolio snapshot. If total assets or cash are stale, give a range and state the stale denominator.
- If tax, broker eligibility, holdings, or roll mechanics cannot be verified, do not invent them; state the gap and keep the action conditional.
