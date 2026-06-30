---
name: risk-manager-investment-memo
description: Use when the user asks whether a stock or ETF is worth buying, holding, trimming, avoiding, or watching for a mid- to long-term horizon, especially after financial statement review, valuation review, or price-move analysis.
---

# Risk-Manager Investment Memo

Purpose: turn evidence into disciplined risk/reward decision support. No return guarantees.

This is the final local action-label layer for this repo. External plugins, including Public Equity Investing, may improve source review, valuation framing, artifacts, or QC, but they must not override the final conditional label, execution rules, or risk controls.

## Default Assumptions

- Horizon: mid- to long-term, 3 to 12 months or longer.
- Current holding: assume 0% if unknown.
- Investor mode: beginner-friendly, but skip glossary unless the user asks.

## Workflow

1. State base date in Seoul time.
2. If the question is portfolio-aware, read the portfolio files and use `UV_CACHE_DIR=.uv-cache uv run python scripts/portfolio_snapshot.py` after fresh prices/FX are available to compute current value, P/L, and weights.
3. If normalized data exists, build a local bundle first:
   - `UV_CACHE_DIR=.uv-cache uv run python scripts/build_analysis_bundle.py <TICKER>`
4. Check `companies/thesis_tracker.yaml` for stored thesis/catalyst/action-log scaffolding when the user asks for ongoing tracking or update persistence.
5. Summarize thesis in 3 lines.
6. Select 8-12 indicators appropriate to sector. Do not force irrelevant metrics.
7. Cover at least:
   - Price context: 1M, 3M, 1Y returns, drawdown/volatility if useful.
   - Valuation: trailing/forward P/E, P/B, EV/EBITDA, FCF yield, or sector-specific alternative.
   - Quality: revenue growth, margins, ROE/ROIC, FCF margin.
   - Financial health: cash, debt, interest coverage, dilution risk.
   - Events/risks: earnings, guidance, regulation, supply chain, macro exposure.
6. Build bull and bear scenarios with invalidation conditions.
7. Give execution rules, not absolute prediction.

## Output

```markdown
## 3-Line Conclusion
- Conditional action:
- Main reason:
- Main invalidation trigger:

## Key Indicators
| Metric | Meaning | Source | Interpretation |
|---|---|---|---|

## Bull Scenario
- Conditions:
- Invalidation:

## Bear Scenario
- Conditions:
- Invalidation:

## Execution Principles
- New entry:
- Current holding:
- Max weight / trim rule:
- Exit rule:

## 3 To-Dos
1.
2.
3.
```

## Decision Labels

Use conditional labels only:

- `Buy`: evidence supports staged entry and risk is bounded.
- `Watch`: thesis interesting, but price/data/timing not strong enough.
- `Hold`: existing position still supported, but new buying not obvious.
- `Trim`: risk/reward worsened or position size too high.
- `Avoid`: thesis broken, valuation excessive, or downside risk unclear.
- `Increase Cash`: broad uncertainty high or evidence weak.

## Rules

- No all-in advice.
- No leverage by default.
- No averaging down unless thesis, cash flow, balance sheet, and valuation still support it.
- Cash is a valid answer.
- Warn against bubble signals: narrative overheating, valuation spike, volatility explosion, debt expansion, dilution, or price rising without improving fundamentals.
