# Broad Invest Analysis Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend this workspace from company-first analysis into broad evidence-backed analysis for US stocks, Korean stocks, US ETFs, and Korean ETFs.

**Architecture:** Keep the existing `fetch -> normalize -> bundle -> memo` shape. Add an instrument layer first, then add stock and ETF data collectors behind a shared orchestration script. Skills should consume generated bundles instead of embedding provider-specific fetch logic in prompts.

**Tech Stack:** Python standard library by default, `uv run python`, existing local scripts, local project skills under `skills/`, `unittest` tests under `tests/`.

---

## Scope Decisions

- US stocks: use SEC companyfacts, price snapshots, company filings, earnings releases, and valuation context.
- Korean stocks: use OpenDART when `OPENDART_API_KEY` exists, exchange/IR sources when needed, and price snapshots where provider support is available.
- US ETFs: use ticker price history plus issuer/fund profile, expense ratio, AUM, index, holdings, sector/country exposure, distributions, and official prospectus/summary prospectus links.
- Korean ETFs: use ticker price history plus issuer/fund profile, expense ratio, NAV/market price context when available, constituent/exposure data, and official issuer/product pages.
- No automated trading, no portfolio execution automation, no guarantee language.
- Raw/cache/report payloads stay local by default; final human-readable notes stay in `memos/`.

## File Map

- Create `scripts/resolve_instrument.py`: resolve query into a typed instrument record: `us_stock`, `kr_stock`, `us_etf`, `kr_etf`, or `unknown`.
- Modify `scripts/resolve_company.py`: keep company resolver as-is and let `resolve_instrument.py` call it for stocks.
- Create `scripts/fetch_etf_profile.py`: fetch or assemble ETF profile metadata from provider adapters and manual fallback inputs.
- Create `scripts/fetch_etf_holdings.py`: fetch issuer holdings CSV/JSON when supported and normalize top holdings/exposure.
- Create `scripts/normalize_etf.py`: normalize ETF profile and holdings into one stable schema.
- Create `scripts/build_asset_bundle.py`: build one markdown bundle for any instrument type.
- Create `scripts/update_asset_bundle.py`: orchestrate resolve, fetch, normalize, price, and bundle for stocks or ETFs.
- Modify `scripts/build_analysis_bundle.py`: keep company-specific bundle path for backward compatibility; do not overload it with ETF logic.
- Modify `scripts/fetch_price_snapshot.py`: add provider result fields needed by broad analysis, including `as_of`, `provider`, `market`, and range returns where available.
- Create `skills/etf-analysis-review/SKILL.md`: ETF-specific review workflow.
- Modify `skills/risk-manager-investment-memo/SKILL.md`: route ETF questions to ETF bundle fields and avoid company-only metrics.
- Modify `skills/market-move-explainer/SKILL.md`: keep ETF support, add ETF-specific drivers such as underlying index, rates, FX, flows, sector exposure, and NAV discount/premium.
- Create `skills/asset-allocation-risk-review/SKILL.md`: compare multiple assets and recommend watch/buy/hold/trim/avoid/cash labels.
- Create tests:
  - `tests/test_resolve_instrument.py`
  - `tests/test_etf_pipeline.py`
  - `tests/test_asset_bundle.py`
  - extend `tests/test_price_snapshot.py`
  - extend `tests/test_update_company_bundle.py` or create `tests/test_update_asset_bundle.py`

## Target Data Schemas

### Instrument Record

```json
{
  "query": "QQQ",
  "instrument_type": "us_etf",
  "symbol": "QQQ",
  "market": "US",
  "name": "Invesco QQQ Trust",
  "identifiers": {
    "cik": null,
    "corp_code": null,
    "isin": null
  },
  "confidence": "exact_ticker",
  "sources": ["cache", "provider"]
}
```

### ETF Normalized Record

```json
{
  "symbol": "QQQ",
  "market": "US",
  "instrument_type": "us_etf",
  "fund_name": "Invesco QQQ Trust",
  "issuer": "Invesco",
  "index_name": "Nasdaq-100 Index",
  "expense_ratio_pct": 0.2,
  "aum": null,
  "currency": "USD",
  "inception_date": null,
  "distribution_yield_pct": null,
  "holdings": [
    {"ticker": "MSFT", "name": "Microsoft Corp", "weight_pct": 8.0}
  ],
  "exposures": {
    "sector": [],
    "country": []
  },
  "source_urls": [],
  "as_of": "2026-05-12"
}
```

### Asset Bundle Sections

- Identity
- Price Summary
- Financial Quality for stocks
- ETF Profile for ETFs
- Holdings and Exposure for ETFs
- Valuation and Yield Context
- Main Drivers
- Risk Flags
- Memo Prompts
- Source Paths

## Task 1: Instrument Resolver

**Files:**
- Create: `scripts/resolve_instrument.py`
- Test: `tests/test_resolve_instrument.py`

- [ ] **Step 1: Write resolver tests**

Create tests for:

- `AAPL` resolves as `us_stock` when SEC resolver returns an exact ticker.
- `005930` resolves as `kr_stock` when DART resolver returns a listed stock.
- `SPY` resolves as `us_etf` from static seed registry.
- `069500.KS` resolves as `kr_etf` from static seed registry.
- Unknown query returns `unknown` with no crash.

Run:

```bash
uv run python -m unittest tests.test_resolve_instrument -v
```

Expected before implementation: import failure for `scripts.resolve_instrument`.

- [ ] **Step 2: Implement resolver with small static ETF seed**

Use a tiny built-in ETF registry first:

- US: `SPY`, `QQQ`, `VTI`, `VOO`, `SCHD`, `TLT`, `GLD`
- KR: `069500.KS`, `102110.KS`, `133690.KS`, `379800.KS`

Call `resolve_company.py` only after ETF exact-symbol checks. Keep provider network refresh out of this task.

- [ ] **Step 3: Verify resolver**

Run:

```bash
uv run python -m unittest tests.test_resolve_instrument -v
```

Expected: pass.

## Task 2: ETF Profile Fetcher

**Files:**
- Create: `scripts/fetch_etf_profile.py`
- Test: `tests/test_etf_pipeline.py`

- [ ] **Step 1: Write profile parser tests**

Test pure functions first:

- parse expense ratio text like `"0.20%"` into `0.2`
- parse AUM text like `"$300.5B"` into numeric value and currency when practical
- preserve `source_url`, `provider`, and `as_of`
- write raw profile payload under `data/raw/etf_profiles/`

Run:

```bash
uv run python -m unittest tests.test_etf_pipeline -v
```

Expected before implementation: import failure for `scripts.fetch_etf_profile`.

- [ ] **Step 2: Implement provider-neutral profile shape**

Start with provider adapters that can return partial data. Do not fail the whole profile when AUM or yield is missing. Required normalized fields:

- `symbol`
- `market`
- `fund_name`
- `issuer`
- `expense_ratio_pct`
- `index_name`
- `currency`
- `source_urls`
- `as_of`

- [ ] **Step 3: Add CLI**

Command:

```bash
uv run python scripts/fetch_etf_profile.py QQQ --market US
uv run python scripts/fetch_etf_profile.py 069500.KS --market KR
```

Expected output: written raw JSON path.

- [ ] **Step 4: Verify**

Run:

```bash
uv run python -m unittest tests.test_etf_pipeline -v
```

Expected: pass.

## Task 3: ETF Holdings Fetcher

**Files:**
- Create: `scripts/fetch_etf_holdings.py`
- Modify: `scripts/invest_utils.py` only if CSV helpers are useful across scripts
- Test: `tests/test_etf_pipeline.py`

- [ ] **Step 1: Write holdings parser tests**

Use fixture strings inside tests for common CSV shapes:

- columns: `Ticker,Name,Weight`
- columns: `종목코드,종목명,비중`
- weights with `%`
- cash or futures rows preserved with `asset_type`

Run:

```bash
uv run python -m unittest tests.test_etf_pipeline -v
```

Expected: fail until parser exists.

- [ ] **Step 2: Implement parser and raw writer**

Output raw holdings to:

```text
data/raw/etf_holdings/<SAFE_SYMBOL>_<DATE>_holdings.json
```

Normalized row fields:

- `ticker`
- `name`
- `weight_pct`
- `asset_type`
- `currency`
- `country`
- `sector`

- [ ] **Step 3: Keep network adapters optional**

If an issuer does not expose stable machine-readable holdings, support:

```bash
uv run python scripts/fetch_etf_holdings.py QQQ --market US --input path/to/issuer_holdings.csv
```

This gives deterministic analysis even when providers block scraping.

- [ ] **Step 4: Verify**

Run:

```bash
uv run python -m unittest tests.test_etf_pipeline -v
```

Expected: pass.

## Task 4: ETF Normalizer

**Files:**
- Create: `scripts/normalize_etf.py`
- Test: `tests/test_etf_pipeline.py`

- [ ] **Step 1: Write normalization tests**

Test that profile + holdings produce one normalized ETF artifact with:

- top 10 holdings sorted by weight
- top holding concentration
- top 5 concentration
- top 10 concentration
- missing profile fields preserved as `null`
- source paths included

Run:

```bash
uv run python -m unittest tests.test_etf_pipeline -v
```

Expected: fail until `normalize_etf.py` exists.

- [ ] **Step 2: Implement normalizer**

Output:

```text
data/normalized/<SAFE_SYMBOL>_<DATE>_etf_normalized.json
```

Do not mix ETF normalized output with `*_sec_normalized.json` or `*_dart_normalized.json`.

- [ ] **Step 3: Verify**

Run:

```bash
uv run python -m unittest tests.test_etf_pipeline -v
```

Expected: pass.

## Task 5: Generic Asset Bundle Builder

**Files:**
- Create: `scripts/build_asset_bundle.py`
- Test: `tests/test_asset_bundle.py`

- [ ] **Step 1: Write bundle tests**

Test three cases:

- US stock bundle includes financial periods and price summary.
- KR stock bundle includes DART normalized fields and price summary when present.
- ETF bundle includes ETF profile, holdings concentration, and ETF-specific memo prompts.

Run:

```bash
uv run python -m unittest tests.test_asset_bundle -v
```

Expected: fail until builder exists.

- [ ] **Step 2: Implement bundle builder**

CLI:

```bash
uv run python scripts/build_asset_bundle.py QQQ --instrument-type us_etf --normalized data/normalized/QQQ_2026-05-12_etf_normalized.json --price data/raw/prices/QQQ_2026-05-12_price.json
uv run python scripts/build_asset_bundle.py AAPL --instrument-type us_stock --normalized data/normalized/AAPL_2026-05-12_sec_normalized.json --price data/raw/prices/AAPL_2026-05-12_price.json
```

Output:

```text
data/reports/<SAFE_SYMBOL>_<DATE>_<INSTRUMENT_TYPE>_bundle.md
```

- [ ] **Step 3: Verify**

Run:

```bash
uv run python -m unittest tests.test_asset_bundle -v
```

Expected: pass.

## Task 6: Generic Orchestrator

**Files:**
- Create: `scripts/update_asset_bundle.py`
- Test: `tests/test_update_asset_bundle.py`

- [ ] **Step 1: Write orchestration tests with fake functions**

Test routing only:

- `AAPL` calls SEC company path.
- `005930` calls DART company path.
- `QQQ` calls ETF profile + holdings + ETF normalizer.
- price fetch failure does not block bundle creation.
- unknown instrument exits with clear message.

Run:

```bash
uv run python -m unittest tests.test_update_asset_bundle -v
```

Expected: fail until script exists.

- [ ] **Step 2: Implement orchestrator**

CLI:

```bash
uv run python scripts/update_asset_bundle.py AAPL --market US
uv run python scripts/update_asset_bundle.py 005930 --market KR
uv run python scripts/update_asset_bundle.py QQQ --market US --type etf
uv run python scripts/update_asset_bundle.py 069500.KS --market KR --type etf
```

Behavior:

- Resolve instrument first.
- Fetch raw data into `data/raw/`.
- Normalize into `data/normalized/`.
- Fetch price into `data/raw/prices/`.
- Build report into `data/reports/`.
- Print final bundle path.

- [ ] **Step 3: Verify**

Run:

```bash
uv run python -m unittest tests.test_update_asset_bundle -v
```

Expected: pass.

## Task 7: Skill Set Expansion

**Files:**
- Create: `skills/etf-analysis-review/SKILL.md`
- Create: `skills/asset-allocation-risk-review/SKILL.md`
- Modify: `skills/risk-manager-investment-memo/SKILL.md`
- Modify: `skills/market-move-explainer/SKILL.md`

- [ ] **Step 1: Add ETF analysis skill**

Required workflow:

- State base date in Seoul time.
- Prefer `uv run python scripts/update_asset_bundle.py <ticker> --type etf`.
- Review expense ratio, AUM, index, issuer, liquidity, holdings concentration, sector/country exposure, distributions, price trend, drawdown, and tracking/NAV caveats.
- Separate official source facts from inferred risk interpretation.
- Give `Buy`, `Watch`, `Hold`, `Trim`, `Avoid`, or `Increase Cash` only as conditional labels.

- [ ] **Step 2: Add asset allocation risk skill**

Required workflow:

- Compare multiple stocks/ETFs using generated bundles where available.
- Identify duplicated exposure, currency exposure, sector concentration, leverage/inverse risk, valuation heat, and cash alternative.
- Produce execution rules, not prediction.

- [ ] **Step 3: Modify existing skills**

`risk-manager-investment-memo`:

- If asset is ETF, avoid company-only metrics like operating income and free cash flow.
- Use ETF profile/holdings metrics instead.

`market-move-explainer`:

- ETF-specific drivers: underlying index, rates, FX, commodity price, sector rotation, flows, distributions, leverage reset, and NAV discount/premium.

- [ ] **Step 4: Verify skill routing manually**

Run:

```bash
rg -n "ETF|update_asset_bundle|expense ratio|holdings|Increase Cash" skills
```

Expected: ETF paths and risk labels appear in relevant skill files.

## Task 8: Provider Reality Checks

**Files:**
- Create: `docs/data_sources.md`
- Test: no unit test; verify by source list review.

- [ ] **Step 1: Document source hierarchy**

For each asset class, list primary and fallback sources:

- US stocks: SEC filings, company IR, exchange data, price providers.
- KR stocks: DART, company IR, KRX/KIND, price providers.
- US ETFs: issuer product page, prospectus/summary prospectus, holdings CSV, SEC fund filings, exchange price data.
- KR ETFs: issuer product page, fund documentation, exchange/NAV data where available, holdings files where available.

- [ ] **Step 2: Document provider limitations**

Include:

- Yahoo can rate-limit.
- Some ETF issuers block scraping or change CSV layouts.
- Korean ETF holdings may require issuer-specific adapters.
- Missing ETF data should mark analysis incomplete, not fabricate values.

- [ ] **Step 3: Verify**

Run:

```bash
rg -n "Yahoo|issuer|DART|SEC|ETF|incomplete" docs/data_sources.md
```

Expected: all listed terms found.

## Task 9: End-to-End Smoke Checks

**Files:**
- No new files unless failures expose needed tests.

- [ ] **Step 1: Run unit tests**

```bash
uv run python -m unittest discover -s tests -v
```

Expected: pass.

- [ ] **Step 2: Run US stock smoke**

```bash
uv run python scripts/update_asset_bundle.py AAPL --market US
```

Expected: prints `data/reports/..._us_stock_bundle.md` or a clear provider/API error with partial artifacts where appropriate.

- [ ] **Step 3: Run US ETF smoke**

```bash
uv run python scripts/update_asset_bundle.py QQQ --market US --type etf
```

Expected: prints `data/reports/..._us_etf_bundle.md`; profile/holdings missing fields are explicitly marked.

- [ ] **Step 4: Run Korean stock smoke when DART key exists**

```bash
uv run python scripts/update_asset_bundle.py 005930 --market KR
```

Expected with `OPENDART_API_KEY`: prints KR stock bundle path. Expected without key: clear missing-key message.

- [ ] **Step 5: Run Korean ETF smoke**

```bash
uv run python scripts/update_asset_bundle.py 069500.KS --market KR --type etf
```

Expected: prints KR ETF bundle path if provider/manual fixtures are available; otherwise marks profile or holdings incomplete.

## Implementation Order

1. Instrument resolver.
2. ETF profile parser/fetcher.
3. ETF holdings parser/fetcher.
4. ETF normalizer.
5. Generic asset bundle builder.
6. Generic update orchestrator.
7. Skill updates.
8. Data source docs.
9. Smoke checks.

This order avoids building memo prompts before the data schema exists.

## Success Criteria

- One command can generate an analysis bundle for `AAPL`, `005930`, `QQQ`, and `069500.KS`.
- ETF analysis no longer relies on company financial-statement fields.
- Missing provider data is visible in generated bundles.
- Current date/base date is stated in Seoul time in generated bundles or skill output.
- All raw/profile/holdings/price artifacts stay under `data/raw/`.
- All normalized artifacts stay under `data/normalized/`.
- Human-readable final notes stay under `memos/`.
- Unit tests pass with `uv run python -m unittest discover -s tests -v`.

