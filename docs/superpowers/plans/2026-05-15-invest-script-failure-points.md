# Invest Script Failure Points And Fix Plan

Base date: 2026-05-15 KST.

Goal: make the local `fetch -> normalize -> bundle -> memo` workflow reliable enough that script failures are explicit, recoverable, and not confused with investment-analysis errors.

## Execution Status

Implemented on branch `codex/invest-script-failure-fixes`.

- Local verification now uses `unittest`; stale policy assertions are updated.
- `docs/verification.md` documents sandbox-aware verification commands.
- Shared HTTP helpers now wrap sandbox/DNS/provider failures with actionable messages and redact sensitive query parameters.
- `update_company_bundle.py` reports failing pipeline stages.
- `fetch_price_snapshot.py` treats Stooq `N/D` as missing data and skips Nasdaq for non-US/dotted symbols.
- DART fetch/normalization now reject empty or non-`000` OpenDART responses by default; `--allow-empty` is available for provider debugging.
- Current-year DART CLI fetches require explicit `--report-code`.
- KR orchestrator remains intentionally unsupported in `update_company_bundle.py`; CLI now says `US/SEC only` clearly instead of failing argparse choice validation.

## Current Failure Map

| Area | Reproduction | Current result | Root cause | Impact |
|---|---|---|---|---|
| `uv` runner | `uv run pytest` | `Failed to initialize cache at /Users/seunghyun/.cache/uv ... Operation not permitted` in sandbox; approved run then fails with `Failed to spawn: pytest` | Two separate issues: sandbox cannot read the user-level uv cache; project has no dev/test dependency declaring `pytest` | Default project instruction says prefer `uv run`, but common validation command is not reliable |
| Test dependency | `.venv/bin/python -m pytest` | `No module named pytest` | `pyproject.toml` has no dev dependency group or optional extra for tests | Pytest-based verification cannot run in fresh/current env |
| Unit tests | `.venv/bin/python -m unittest discover -s tests` | 24 tests run, 2 failures in `test_skill_routing_policy.py` | Tests still assert old policy phrases: `survival-first risk minimization` and `Risk-first verdict`; repo policy now uses `evidence-first risk/reward assessment` and `risk-management verdict` | CI/local verification is red even when scripts are otherwise usable |
| Sandbox network | `.venv/bin/python scripts/update_company_bundle.py AAPL` | SEC resolver fails with `urllib.error.URLError: <urlopen error [Errno 8] nodename nor servname provided, or not known>` | Subprocess network is blocked until approval; web search and Python subprocess networking are separate controls | User-facing workflow fails unless agent escalates or cached data exists |
| Approved US bundle | `.venv/bin/python scripts/update_company_bundle.py AAPL` with network approval | Succeeds: `data/reports/AAPL_2026-05-15_bundle.md` | Orchestrator itself works when SEC cache/network and price provider are available | Good baseline; do not rewrite broad pipeline before fixing env/test issues |
| KR orchestration | `.venv/bin/python scripts/update_company_bundle.py 005930 --market KR` | argparse rejects `KR`; choices are `US` only | `update_company_bundle.py` explicitly supports US/SEC only | Korean-stock workflow is manual despite skill docs asking to prefer local pipeline |
| KR price snapshot | `.venv/bin/python scripts/fetch_price_snapshot.py 005930.KS --range 1y --interval 1d` with approval | all providers fail: Stooq has `N/D`, Nasdaq rejects dotted/non-US symbols, Yahoo returns HTTP 429 | Provider stack is US-oriented; Stooq quote parser does not treat `N/D` as missing; Yahoo is rate-limited | KR current-price fetch is unreliable; analysis falls back to web/manual quote |
| DART annual/current-year fetch | `.venv/bin/python scripts/fetch_dart_financials.py 00126380 --ticker 005930 --year 2026` | OpenDART status `013`, message `조회된 데이타가 없습니다.` | Default annual report code `11011` is not available for current fiscal year; 2026 annual filing does not exist yet | Normalization writes an empty `periods: []` file without flagging that this is unusable for memo work |
| DART Q1 current-year fetch | same command with `--report-code 11013` | OpenDART status `013` in current run | OpenDART full financial endpoint did not return current-year Q1 data for this call; could be filing timing, endpoint coverage, or parameter mismatch | KR financial pipeline can silently produce empty normalized output |

## Fix Strategy

Do not start by adding more providers or large abstractions. First make failure modes visible and tests green. Then add targeted KR support.

## Phase 1: Restore Local Verification

1. Add a dev/test dependency path.
   - Option A: add `[dependency-groups] dev = ["pytest"]` if current uv version supports it.
   - Option B: use `unittest` as canonical verification and stop documenting `pytest`.
   - Preferred: Option B for now, because current tests are `unittest`-native and repo has no runtime dependencies.

2. Update stale policy tests.
   - In `tests/test_skill_routing_policy.py`, replace old expected phrases with current policy wording:
     - `Default investment workflow is evidence-first risk/reward assessment.`
     - `risk-management verdict controls the final action label`
   - Match case exactly or assert case-insensitively for policy intent.

3. Document sandbox-aware verification.
   - Add a short `README` or docs note:
     - Normal local check: `.venv/bin/python -m unittest discover -s tests`
     - Full uv check after cache access is available: `uv run python -m unittest discover -s tests`
   - Avoid `uv run pytest` until pytest is declared.

Verification:

```bash
.venv/bin/python -m unittest discover -s tests
uv run python -m unittest discover -s tests
```

## Phase 2: Make Network Failures Actionable

1. Add a small shared network-error wrapper in `invest_utils.py`.
   - Convert `urllib.error.URLError` and timeout failures into short messages:
     - provider/url
     - likely cause: sandbox/network/DNS/provider
     - retry hint: rerun with approval or use cached artifact
   - Keep raw exception chained for debugging.

2. Add cache-aware messaging to `resolve_company.py`.
   - If cache exists and refresh is false, resolver should not fetch.
   - If fetch fails and cache is missing, error should say which cache file is missing.

3. In `update_company_bundle.py`, split child failure labels.
   - Current `run_command()` reports command and stderr, but not pipeline stage.
   - Add stage names: `resolve/fetch SEC`, `normalize`, `fetch price`, `build bundle`.
   - Preserve price-fetch tolerance; financial fetch failure should still stop.

Verification:

```bash
.venv/bin/python scripts/update_company_bundle.py AAPL
.venv/bin/python scripts/resolve_company.py AAPL --market US
```

Run once in sandbox and once with approval; error text should differ clearly.

## Phase 3: Fix KR Price Fetch Boundary

1. Treat Stooq `N/D` as missing, not a float parse crash.
   - Extend `_parse_number()` to return `None` for `N/D`.
   - This makes error message become `stooq quote returned no close price`, which is clearer.

2. Add provider eligibility before fetch.
   - `nasdaq` should be skipped for non-US/dotted symbols with a structured attempt reason.
   - `stooq` should be marked unsupported when it returns no quote for KR tickers.

3. Add a Korean quote provider or explicit unsupported status.
   - Best target: KRX/Naver-compatible endpoint only if a stable no-auth endpoint is chosen.
   - If no stable endpoint, make script return a clear unsupported-provider failure and rely on web-verified quote in memo.

Verification:

```bash
.venv/bin/python scripts/fetch_price_snapshot.py 005930.KS --range 1y --interval 1d
.venv/bin/python scripts/fetch_price_snapshot.py AAPL --range 1y --interval 1d
```

Expected after minimal fix: AAPL still succeeds; KR failure is clean and non-misleading.

## Phase 4: Fix DART Empty Data Handling

1. Add status validation in `fetch_dart_financials.py` or `normalize_financials.py`.
   - If `status != "000"` or `list` is missing, fail by default with OpenDART status/message.
   - Optional flag: `--allow-empty` for debugging raw provider responses.

2. Improve current-period report selection.
   - Keep annual `11011` for completed prior fiscal years.
   - For current year, require explicit `--report-code` or add a helper that tries available quarterly codes in order.
   - Do not write normalized files with empty `periods` unless explicitly allowed.

3. Add tests for empty DART provider response.
   - Input: `{"status": "013", "message": "조회된 데이타가 없습니다."}`
   - Expected: normalization/fetch path raises clear error or marks artifact unusable, depending chosen design.

Verification:

```bash
.venv/bin/python scripts/fetch_dart_financials.py 00126380 --ticker 005930 --year 2025 --report-code 11011
.venv/bin/python scripts/fetch_dart_financials.py 00126380 --ticker 005930 --year 2026 --report-code 11013
.venv/bin/python scripts/normalize_financials.py --source dart --ticker 005930 --input data/raw/dart/<file>.json
```

## Phase 5: Decide KR Orchestrator Scope

Current `update_company_bundle.py` supports US only. Keep that honest until KR pieces are reliable.

Options:

1. Add `update_kr_company_bundle.py`.
   - Resolve DART corp code.
   - Fetch DART financials.
   - Normalize DART.
   - Try KR price snapshot.
   - Build bundle with missing price allowed.

2. Extend `update_company_bundle.py --market KR`.
   - Requires market-specific branches inside one script.
   - More convenient long term, but easier to overgrow.

Preferred: start with option 1 if implementation stays small; merge into generic orchestrator later only if duplication becomes painful.

## Implementation Order

1. Fix tests and verification docs.
2. Improve error messages for network/provider failures.
3. Fix price parser and provider eligibility.
4. Add DART empty-response guard.
5. Add KR orchestrator only after DART and KR price behavior is explicit.

## Non-Goals

- Do not track generated `data/raw`, `data/normalized`, or `data/reports` outputs in git.
- Do not make this an automated trading system.
- Do not hide missing primary data behind web-search summaries.
- Do not add paid/provider-specific dependencies before the no-dependency path is exhausted.

## Current Evidence

- `uv run pytest`: fails at uv cache in sandbox; approved run cannot spawn `pytest`.
- `.venv/bin/python -m pytest`: no `pytest` module.
- `.venv/bin/python -m unittest discover -s tests`: 24 tests, 2 stale policy failures.
- `.venv/bin/python scripts/update_company_bundle.py AAPL`: sandbox network failure; approved run succeeds.
- `.venv/bin/python scripts/update_company_bundle.py 005930 --market KR`: unsupported market.
- `fetch_price_snapshot.py 005930.KS`: Stooq `N/D`, Nasdaq unsupported, Yahoo 429.
- DART `005930`, year 2026, report codes `11011` and `11013`: status `013`, no data.
