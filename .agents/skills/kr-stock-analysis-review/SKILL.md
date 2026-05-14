---
name: kr-stock-analysis-review
description: Use when the user asks for Korean listed stock analysis, DART financial review, KRX/KIND disclosure context, valuation, price-move explanation, or buy/hold/avoid judgment for Korean equities.
---

# Korean Stock Analysis Review

Purpose: adapt the US stock analysis workflow to Korean listed companies while preserving this workspace's survival-first investment rules.

## When To Use

Use for Korean common stocks, preferred shares, KOSPI/KOSDAQ names, chaebol subsidiaries, holding companies, banks, insurers, REITs, and Korean dividend/value/growth stock questions.

Do not use for Korean ETFs. Use or create an ETF-specific workflow for those because holdings, NAV, tracking index, expense ratio, and issuer data matter more than operating financials.

## Workflow

1. State base date in Seoul time.
2. Resolve the company when needed:
   - `uv run python scripts/resolve_company.py "<ticker-or-name>" --market KR`
3. Prefer the local pipeline when possible:
   - `uv run python scripts/fetch_dart_financials.py <CORP_CODE> --ticker <TICKER> --year <YYYY>`
   - `uv run python scripts/normalize_financials.py --source dart --ticker <TICKER> --input <RAW_JSON>`
   - `uv run python scripts/fetch_price_snapshot.py <TICKER>.KS --range 1y --interval 1d`
4. Use primary sources first:
   - DART annual, semiannual, quarterly reports.
   - DART current reports and major matters reports.
   - Company IR decks, earnings releases, shareholder letters.
   - KRX or KIND disclosures where relevant.
5. Use news only after primary facts are checked.
6. Analyze the business and financials using the same structure as US stock analysis, but adapt metrics to Korea-specific context.

## Korea-Specific Checks

Financial quality:

- Consolidated vs separate statements.
- Parent-only vs subsidiary-driven earnings.
- Operating profit vs net income quality.
- Operating cash flow vs reported profit.
- Capex burden and free cash flow.
- Cash, debt, net debt, interest burden.
- Receivables, inventory, and working-capital strain.
- One-time gains, asset sales, FX gains/losses, and equity-method income.

Valuation:

- P/E, P/B, EV/EBITDA, dividend yield, FCF yield when available.
- Historical valuation band.
- Peer group within Korea first, then global peers only when business mix is comparable.
- Holding-company discount, minority-shareholder discount, governance discount.
- Cyclical trough vs structural value trap.

Korea market structure:

- Chaebol group exposure and related-party transactions.
- Common vs preferred share spread.
- Treasury shares, cancellation policy, and shareholder return policy.
- Foreign ownership flow when material.
- FX exposure: KRW weakness/strength impact on sales, margins, and debt.
- Export cycle, memory/semiconductor cycle, shipbuilding cycle, battery/materials cycle, China exposure, and rate sensitivity where relevant.

Risk:

- Governance and capital allocation risk.
- Dilution, convertible bonds, paid-in capital increase.
- Customer concentration.
- Regulatory or policy risk.
- Liquidity and small-cap volatility.
- Dividend cut risk.

## Output

Use this structure:

```markdown
## 3-Line Conclusion
- Conditional action:
- Main reason:
- Main invalidation trigger:

## Source Base
- Base date:
- Primary sources checked:
- Local artifacts:
- Missing data:

## Business And Financial Quality
- Business model:
- Revenue/profit trend:
- Cash conversion:
- Balance sheet:
- Korea-specific flags:

## Valuation
| Metric | Current | Context | Interpretation |
|---|---:|---|---|

## Bull Case
- Conditions:
- Evidence:
- Invalidation:

## Bear Case
- Conditions:
- Evidence:
- Invalidation:

## Execution Rules
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

- `Buy`: evidence supports staged entry and downside is bounded.
- `Watch`: thesis is interesting, but price/data/timing is not strong enough.
- `Hold`: existing position still supported, but new buying is not obvious.
- `Trim`: risk/reward worsened or position size is too high.
- `Avoid`: thesis broken, valuation excessive, governance weak, or downside unclear.
- `Increase Cash`: uncertainty high or evidence weak.

## Rules

- No all-in advice.
- No leverage by default.
- No averaging down unless thesis, cash flow, balance sheet, and valuation still support it.
- Cash is a valid answer.
- Do not force US metrics when Korean disclosure format does not support them cleanly.
- If `OPENDART_API_KEY` is missing or provider data fails, say analysis is incomplete instead of filling gaps with guesses.
