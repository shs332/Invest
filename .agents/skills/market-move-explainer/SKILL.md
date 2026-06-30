---
name: market-move-explainer
description: Use when the user asks why a stock, ETF, sector, or company share price moved recently, including "why did it rise/fall", "what happened today", earnings reactions, news-driven moves, or unexplained volatility in Korean or US markets.
---

# Market Move Explainer

Purpose: explain recent price movement without overclaiming causality.

## Workflow

1. State base date in Seoul time.
2. If possible, fetch price context first:
   - `UV_CACHE_DIR=.uv-cache uv run python scripts/fetch_price_snapshot.py <YAHOO_SYMBOL>`
   - Examples: `AAPL`, `005930.KS`
3. Confirm the move: ticker, market, current/last price, 1D, 1M, 3M, and 1Y return when relevant.
4. Search recent primary sources first: filings, earnings releases, IR, exchange notices, company announcements.
5. Check high-credibility secondary context: major news, analyst revisions, macro/sector data.
6. Separate evidence levels:
   - Confirmed cause: directly supported by company filing, earnings release, exchange notice, or official data.
   - Likely driver: supported by multiple credible sources, but not directly proven.
   - Possible noise: plausible but weak evidence.
7. Explain whether the move changes investment thesis, valuation, or only sentiment.

## Output

Use this structure:

```markdown
## Move Summary
- Base date:
- Price move:
- Most likely driver:

## Evidence
- Confirmed:
- Likely:
- Unclear/noise:

## Interpretation
- Business impact:
- Financial impact:
- Valuation/sentiment impact:

## What To Check Next
1.
2.
3.
```

## Rules

- Never present correlation as confirmed causation.
- If current data is unavailable, say so and mark analysis as incomplete.
- For large moves, explicitly check whether earnings, guidance, regulation, litigation, dilution, credit stress, or macro shocks are involved.
