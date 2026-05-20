# Invest Workspace

This repo is a local, user-initiated investment research workspace. It supports evidence-based decision memos for stocks, ETFs, price moves, and company financial review. It is not an automated trading system.

## Base Rules

- State the base date in Seoul time for current market data.
- Use primary sources first: SEC, DART, company IR, issuer ETF pages, exchange data, central bank data.
- Use news only as context after primary facts are checked.
- Keep outputs risk-aware: downside control, valuation heat checks, cash as a valid position, no leverage by default.
- Store generated raw data under `data/raw/`, normalized data under `data/normalized/`, report bundles under `data/reports/`, and final memos under `memos/`.

## Which Question Uses Which Skill/Script

| Question type | Primary skill | Local scripts | Output |
|---|---|---|---|
| US stock buy/hold/avoid | `us-stock-decision-workflow` | `uv run python scripts/update_company_bundle.py <TICKER> --market US` | `data/reports/<TICKER>_<DATE>_bundle.md` |
| US stock upside/growth/momentum | `us-stock-return-opportunity` | Same US bundle command first | Return-opportunity memo with risk-management final label |
| Korean stock analysis | `kr-stock-analysis-review` | `resolve_company.py`, `fetch_dart_financials.py`, `normalize_financials.py`, `fetch_price_snapshot.py` | Manual KR evidence bundle until KR orchestration exists |
| ETF judgment/comparison | `etf-analysis-review` | `fetch_price_snapshot.py` for price context; issuer/primary sources for holdings, NAV, expense, tracking | ETF-specific risk/reward memo |
| Price move explanation | `market-move-explainer` | `fetch_price_snapshot.py <SYMBOL> --range 1y --interval 1d` | Move summary with confirmed/likely/unclear evidence split |
| Financial statement quality | `financial-statement-review` | SEC or DART fetch plus `normalize_financials.py` | Financial quality section |
| Final risk/reward memo | `risk-manager-investment-memo` | `build_analysis_bundle.py <TICKER>` when normalized data exists | Conditional action label and execution rules |

## Current Pipeline

US stock path:

```bash
uv run python scripts/update_company_bundle.py AAPL --market US
```

Manual US path:

```bash
uv run python scripts/fetch_sec_companyfacts.py AAPL
uv run python scripts/normalize_financials.py --source sec --ticker AAPL --input data/raw/sec/<RAW_FILE>.json
uv run python scripts/fetch_price_snapshot.py AAPL --range 1y --interval 1d
uv run python scripts/build_analysis_bundle.py AAPL
```

Manual KR path:

```bash
uv run python scripts/resolve_company.py "Samsung Electronics" --market KR
uv run python scripts/fetch_dart_financials.py <CORP_CODE> --ticker 005930 --year <YYYY> --report-code 11011
uv run python scripts/normalize_financials.py --source dart --ticker 005930 --input data/raw/dart/<RAW_FILE>.json
uv run python scripts/fetch_price_snapshot.py 005930.KS --range 1y --interval 1d
```

ETF path:

```bash
uv run python scripts/fetch_price_snapshot.py VOO --range 1y --interval 1d
```

Then check issuer/primary sources for holdings, index, expense ratio, AUM/liquidity, NAV premium/discount, tracking quality, distribution policy, leverage/inverse structure, tax, and currency exposure.

## Verification

Canonical local check:

```bash
.venv/bin/python -m unittest discover -s tests
```

`uv` check when the runner can access its cache:

```bash
uv run python -m unittest discover -s tests
```

Do not use `uv run pytest` unless `pytest` is added as a declared dependency. Current tests are `unittest`-native.

Network-fetch scripts can fail inside a sandbox before approval even when the script is correct. Re-run provider fetches with network approval or use existing cache artifacts under `data/cache/` when available.
