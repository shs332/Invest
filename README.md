# Invest Workspace

This repo is a local, user-initiated investment research workspace. It supports evidence-based decision memos for stocks, ETFs, price moves, and company financial review. It is not an automated trading system.

## Base Rules

- State the base date in Seoul time for current market data.
- Use primary sources first: SEC, DART, company IR, issuer ETF pages, exchange data, central bank data.
- Use news only as context after primary facts are checked.
- Keep outputs risk-aware: downside control, valuation heat checks, cash as a valid position, no leverage by default.
- A young or long-horizon investor with a modest seed can reasonably use a higher expected-return tilt, but this repo treats that as a risk-aware growth tilt rather than permission for leverage, all-in concentration, or weaker evidence.
- For aggressive or return-first prompts, state the upside driver, evidence quality, downside case, position size/cap, and invalidation trigger.
- Store generated raw data under `data/raw/`, normalized data under `data/normalized/`, report bundles under `data/reports/`, and final memos under `memos/`.

## Which Question Uses Which Skill/Script

| Question type | Primary skill | Local scripts | Output |
|---|---|---|---|
| Any named security question | Routed project skill | `uv run python scripts/build_context_pack.py "<QUESTION>"` | Portfolio-aware route, matched holding/watchlist, PEI role |
| US stock buy/hold/avoid | `us-stock-decision-workflow` | `uv run python scripts/update_asset_bundle.py <TICKER> --market US --asset-type stock` | `data/reports/<TICKER>_<DATE>_bundle.md` |
| US stock upside/growth/momentum/aggressive return | `us-stock-return-opportunity` | Same unified US bundle command first | Return-opportunity memo with risk-management final label |
| Korean stock analysis | `kr-stock-analysis-review` | `uv run python scripts/update_asset_bundle.py <TICKER>.KS --market KR --asset-type stock --corp-code <CORP_CODE>` | DART/price/report bundle when source access is available |
| ETF judgment/comparison | `etf-analysis-review` | `uv run python scripts/update_asset_bundle.py <ETF> --market US|KR --asset-type ETF` plus issuer/primary sources for holdings, NAV, expense, tracking | ETF-specific risk/reward memo |
| Price move explanation | `market-move-explainer` | `fetch_price_snapshot.py <SYMBOL> --range 1y --interval 1d` | Move summary with confirmed/likely/unclear evidence split |
| Financial statement quality | `financial-statement-review` | SEC or DART fetch plus `normalize_financials.py` | Financial quality section |
| Final risk/reward memo | `risk-manager-investment-memo` | `build_analysis_bundle.py <TICKER>` when normalized data exists | Conditional action label and execution rules |
| Portfolio exposure/P&L | `risk-manager-investment-memo` context | `uv run python scripts/portfolio_snapshot.py --prices-json <FRESH_PRICES.json> --usd-krw <RATE>` | Current value, P/L, and known-position weights |

## Default Operating Loop

1. Build a context pack:

```bash
uv run python scripts/build_context_pack.py "AAPL 더 살까?"
```

2. Refresh or prepare the local asset bundle:

```bash
uv run python scripts/update_asset_bundle.py AAPL --market US --asset-type stock
uv run python scripts/update_asset_bundle.py 005930.KS --market KR --asset-type stock --corp-code 00126380
uv run python scripts/update_asset_bundle.py 360750.KS --market KR --asset-type ETF
```

3. For portfolio-aware answers, compute exposure after fresh prices and FX are available:

```bash
uv run python scripts/portfolio_snapshot.py --prices-json data/raw/prices/latest_portfolio_prices.json --usd-krw 1350
```

4. Answer with the routed project-owned skill, then let `risk-manager-investment-memo` own the final local action label.

## Public Equity Investing Plugin Policy

This repo's local scripts and project-owned skills remain the primary workflow for investment advice and decision support. The Public Equity Investing plugin is a supplemental institutional research layer: use it when the requested output is a polished public-equity artifact, model, valuation package, pitch, tracker, or QC review.

Inline answer by default for ordinary buy/hold/trim/avoid, valuation, news, and portfolio questions. Use Public Equity Investing HTML/XLSX artifacts only when the user asks for a formal report, model, tracker, pitch, scenario package, or QC review.

| Use case | Primary route in this repo | Public Equity Investing role |
|---|---|---|
| Current buy/hold/trim/avoid judgment | Local scripts plus project-owned US/KR/ETF skills | Optional background structure only; it must not override local action labels or risk controls |
| Company baseline / issuer overview | Local evidence first when available | `company-tearsheet` for a source-backed HTML issuer baseline |
| Earnings preview or post-print analysis | Local fresh data and primary filings first | `earnings-preview` or `earnings-deep-dive` for institutional report structure |
| Comps, DCF, 3-statement, model update | Local/company data plus user-provided model files | Use PEI model/valuation skills when a workbook or formal valuation package is needed |
| Long/short pitch, catalyst, scenario, sizing | Local evidence and portfolio context first | Use PEI pitch/event/scenario/risk skills for PM-style framing; missing trade data caps readiness |
| Deck, report, or model QC | Existing artifact required | Use `deck-report-qc` or `model-audit-tieout` to find source, formula, and circulation risks |

PEI source categories are optional inputs, not proof that a connector is available. If filings/IR, transcripts, market data/estimates, internal research, or portfolio models are unavailable, label the gap and keep the output preliminary or screen-grade. Do not invent consensus, ownership, borrow, liquidity, options, or internal thesis context.

For Korean equities and Korea-listed ETFs, gather DART/KRX/KIND/issuer evidence through the local workflow first. Use PEI only after that for report structure, valuation framing, scenario analysis, or polished artifacts.

## Portfolio And Thesis Tracking

- `companies/portfolio_profile.yaml`: local-only user-level portfolio policy, cash, accounts, and stale-data warnings.
- `companies/holdings.yaml`: local-only source of truth for ticker, market, account, asset type, shares, average price, currency, and thesis.
- `companies/watchlist.yaml`: local-only names to revisit that are not current holdings.
- `companies/thesis_tracker.yaml`: local-only append-only thesis status, catalysts, kill criteria, next review gates, and action-log entries.

These real portfolio files are ignored by git. Use the tracked `companies/*.example.yaml` templates to recreate them on another machine without exposing personal positions, cash balances, cost basis, or thesis notes.

Do not change shares or average price unless the user explicitly reports a trade, transfer, split adjustment, or correction. Use `portfolio_snapshot.py` to compute derived values from fresh market data instead of editing recorded facts.

## Current Pipeline

Unified US stock path:

```bash
uv run python scripts/update_asset_bundle.py AAPL --market US --asset-type stock
```

Manual US path:

```bash
uv run python scripts/fetch_sec_companyfacts.py AAPL
uv run python scripts/normalize_financials.py --source sec --ticker AAPL --input data/raw/sec/<RAW_FILE>.json
uv run python scripts/fetch_price_snapshot.py AAPL --range 1y --interval 1d
uv run python scripts/build_analysis_bundle.py AAPL
```

Unified KR stock path:

```bash
uv run python scripts/resolve_company.py "Samsung Electronics" --market KR
uv run python scripts/update_asset_bundle.py 005930.KS --market KR --asset-type stock --corp-code <CORP_CODE> --year <YYYY> --report-code 11011
```

ETF path:

```bash
uv run python scripts/update_asset_bundle.py VOO --market US --asset-type ETF
```

Then check issuer/primary sources for holdings, index, expense ratio, AUM/liquidity, NAV premium/discount, tracking quality, distribution policy, leverage/inverse structure, tax, and currency exposure.

## Verification

Canonical local check:

```bash
.venv/bin/pytest
```

`uv` check when the runner can access its cache:

```bash
UV_CACHE_DIR=.uv-cache uv run pytest
```

`pytest` is a declared dev dependency (`pyproject.toml` `[dependency-groups.dev]`); `uv sync` installs it. Test classes are still `unittest.TestCase`-based (pytest runs them natively) — write new tests either way, but run the suite with `pytest`, not `python -m unittest discover`.

Network-fetch scripts can fail inside a sandbox before approval even when the script is correct. Re-run provider fetches with network approval or use existing cache artifacts under `data/cache/` when available.
