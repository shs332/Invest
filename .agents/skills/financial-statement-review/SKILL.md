---
name: financial-statement-review
description: Use when the user asks to review company financial statements, earnings, cash flow, balance sheet quality, profitability, debt, margins, or whether reported profit is backed by cash flow for US or Korean listed companies.
---

# Financial Statement Review

Purpose: judge financial quality and durability before valuation or investment memo.

## Workflow

1. State base date in Seoul time and source period.
2. Use local pipeline when possible:
   - Resolve identifier first when missing:
     - US: `UV_CACHE_DIR=.uv-cache uv run python scripts/resolve_company.py "<ticker-or-company-name>" --market US`
     - Korea: `UV_CACHE_DIR=.uv-cache uv run python scripts/resolve_company.py "<ticker-or-company-name>" --market KR`
   - US: `UV_CACHE_DIR=.uv-cache uv run python scripts/fetch_sec_companyfacts.py <TICKER>`
   - Korea: `UV_CACHE_DIR=.uv-cache uv run python scripts/fetch_dart_financials.py <CORP_CODE> --ticker <TICKER> --year <YYYY>`
   - Normalize: `UV_CACHE_DIR=.uv-cache uv run python scripts/normalize_financials.py --source sec|dart --ticker <TICKER> --input <RAW_JSON>`
   - DART commands and function-call paths load the project `.env`; use `OPENDART_API_KEY` or `DART_API_KEY` from there before asking the user for credentials.
3. Use primary filings when possible:
   - US: SEC 10-K, 10-Q, 8-K, earnings release, IR deck.
   - Korea: DART annual/quarterly/semiannual report, IR release, earnings announcement.
4. Identify accounting basis: consolidated vs separate, annual vs quarterly, currency, fiscal period.
5. Review five blocks:
   - Growth: revenue, gross profit, operating income, net income.
   - Profitability: gross margin, operating margin, net margin, ROE/ROIC when available.
   - Cash flow: operating cash flow, capex, free cash flow, FCF margin.
   - Balance sheet: cash, debt, net debt, current ratio, debt/equity, interest coverage when available.
   - Quality flags: one-time gains/losses, working-capital strain, stock compensation, dilution, inventory/receivable buildup.
6. Compare trend across at least 3 years when available; otherwise state limitation.

## Output

```markdown
## Financial Quality
- Base date:
- Source period:
- Accounting basis:

## Key Numbers
- Revenue:
- Operating income:
- Net income:
- Operating cash flow:
- Free cash flow:
- Cash/debt:

## Interpretation
- Growth:
- Profitability:
- Cash conversion:
- Balance sheet:

## Red Flags
-

## Missing Data
-
```

## Rules

- Cash flow matters more than headline net income for quality judgment.
- Distinguish cyclical weakness from structural deterioration.
- Mark value-trap risk when low valuation pairs with declining cash flow, high debt, dilution, or shrinking margins.
