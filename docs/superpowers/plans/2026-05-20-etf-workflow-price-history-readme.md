# ETF Workflow, Price History, README, And Bundle Slots Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add ETF routing, make price-history output honest, document which question uses which skill/script, and extend US analysis bundles with source and valuation slots.

**Architecture:** Keep the repo's current no-dependency Python pipeline. Add one project-local ETF skill, adjust the existing price snapshot script so quote-only data is not presented as range history, add a repo README, and extend the bundle markdown with explicit evidence gaps instead of inventing unavailable valuation data.

**Tech Stack:** Python 3.9+, `unittest`, project-local `.agents/skills`, markdown docs, existing `uv run python scripts/...` workflow.

---

## Branch And Commit Strategy

Create branch before editing:

```bash
git switch -c codex/etf-workflow-price-history-readme
```

Use three commits:

```bash
git add AGENTS.md .agents/skills/etf-analysis-review/SKILL.md tests/test_skill_routing_policy.py
git commit -m "feat(skills): add ETF analysis workflow"

git add scripts/fetch_price_snapshot.py tests/test_price_snapshot.py
git commit -m "fix(prices): separate quote and history output"

git add README.md scripts/build_analysis_bundle.py tests/test_update_company_bundle.py
git commit -m "docs: map workflows and add bundle evidence slots"
```

Run full verification before each commit:

```bash
.venv/bin/python -m unittest discover -s tests
```

Run `uv` verification when cache access is available:

```bash
uv run python -m unittest discover -s tests
```

---

## File Map

- Create: `.agents/skills/etf-analysis-review/SKILL.md`
  - Responsibility: route ETF questions through ETF-specific evidence checks rather than company-financial workflows.
- Modify: `AGENTS.md`
  - Responsibility: top-level ETF routing rule.
- Modify: `tests/test_skill_routing_policy.py`
  - Responsibility: ensure ETF skill exists, AGENTS routes ETF questions, and documented script commands remain valid.
- Modify: `scripts/fetch_price_snapshot.py`
  - Responsibility: distinguish quote-only snapshots from range history and expose history availability in summary.
- Modify: `tests/test_price_snapshot.py`
  - Responsibility: lock price-history semantics with provider-free unit tests.
- Create: `README.md`
  - Responsibility: repo map for question type -> skill -> script -> output.
- Modify: `scripts/build_analysis_bundle.py`
  - Responsibility: add filing-source, valuation, and source-gap sections to generated bundles.
- Modify: `tests/test_update_company_bundle.py`
  - Responsibility: verify bundle sections without network.

---

### Task 1: Add ETF Workflow Skill And Routing

**Files:**
- Create: `.agents/skills/etf-analysis-review/SKILL.md`
- Modify: `AGENTS.md`
- Modify: `tests/test_skill_routing_policy.py`

- [ ] **Step 1: Write failing routing tests**

Add this test method to `tests/test_skill_routing_policy.py` inside `SkillRoutingPolicyTest`:

```python
    def test_etf_questions_route_to_project_etf_skill(self):
        agents_text = self.read("AGENTS.md")
        skill_text = self.read(".agents/skills/etf-analysis-review/SKILL.md")

        self.assertIn("use `etf-analysis-review`", agents_text)
        self.assertIn("ETF Analysis Review", skill_text)
        self.assertIn("holdings", skill_text.lower())
        self.assertIn("NAV", skill_text)
        self.assertIn("expense ratio", skill_text.lower())
        self.assertIn("tracking", skill_text.lower())
        self.assertIn("Do not run company financial-statement workflows", skill_text)
```

Also extend `skill_paths` in `test_documented_skill_commands_match_repo_cli`:

```python
        skill_paths = [
            ".agents/skills/us-stock-decision-workflow/SKILL.md",
            ".agents/skills/us-stock-return-opportunity/SKILL.md",
            ".agents/skills/kr-stock-analysis-review/SKILL.md",
            ".agents/skills/etf-analysis-review/SKILL.md",
        ]
```

- [ ] **Step 2: Run routing tests and verify failure**

Run:

```bash
.venv/bin/python -m unittest tests.test_skill_routing_policy -v
```

Expected: FAIL because `.agents/skills/etf-analysis-review/SKILL.md` does not exist or `AGENTS.md` has no ETF skill routing line.

- [ ] **Step 3: Add ETF skill**

Create `.agents/skills/etf-analysis-review/SKILL.md` with this content:

```markdown
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
```

- [ ] **Step 4: Add AGENTS routing**

Add this line to `AGENTS.md` after the recent-data rule or near existing stock-routing rules:

```markdown
- For ETF judgment, comparison, price-move, holdings, NAV, expense, tracking, dividend/yield, leveraged ETF, or inverse ETF questions, use `etf-analysis-review`; do not force ETF questions through company financial-statement workflows.
```

- [ ] **Step 5: Run routing tests and verify pass**

Run:

```bash
.venv/bin/python -m unittest tests.test_skill_routing_policy -v
```

Expected: PASS.

- [ ] **Step 6: Commit Task 1**

Run:

```bash
git add AGENTS.md .agents/skills/etf-analysis-review/SKILL.md tests/test_skill_routing_policy.py
git commit -m "feat(skills): add ETF analysis workflow"
```

---

### Task 2: Separate Quote-Only And Historical Price Semantics

**Files:**
- Modify: `scripts/fetch_price_snapshot.py`
- Modify: `tests/test_price_snapshot.py`

- [ ] **Step 1: Write failing tests for quote-only metadata**

Add this test to `tests/test_price_snapshot.py`:

```python
    def test_stooq_quote_marks_history_unavailable(self):
        csv_text = "\n".join(
            [
                "Symbol,Date,Time,Open,High,Low,Close,Volume",
                "AAPL.US,2026-05-11,22:00:19,291.979,293.88,290.23,292.68,41166897",
            ]
        )

        result = summarize_stooq_quote_csv(csv_text, "AAPL")

        self.assertEqual(result["source"], "stooq_quote_csv")
        self.assertFalse(result["history_available"])
        self.assertEqual(result["history_points"], 1)
        self.assertIsNone(result["period_return_pct"])
```

Add this test for history-capable summary:

```python
    def test_stooq_history_marks_history_available(self):
        csv_text = "\n".join(
            [
                "Date,Open,High,Low,Close,Volume",
                "2026-01-02,100,101,99,100,1000",
                "2026-01-03,105,106,104,110,1200",
            ]
        )

        result = summarize_stooq_csv(csv_text, "AAPL")

        self.assertTrue(result["history_available"])
        self.assertEqual(result["history_points"], 2)
        self.assertEqual(result["period_return_pct"], 10.0)
```

- [ ] **Step 2: Run price tests and verify failure**

Run:

```bash
.venv/bin/python -m unittest tests.test_price_snapshot -v
```

Expected: FAIL because summaries do not yet expose `history_available` and `history_points`.

- [ ] **Step 3: Add summary metadata**

Modify `scripts/fetch_price_snapshot.py` so `summarize_stooq_csv()` returns these keys:

```python
        "history_available": len(closes) > 1,
        "history_points": len(closes),
```

Modify `summarize_stooq_quote_csv()` so it returns these keys:

```python
        "history_available": False,
        "history_points": 1,
```

Modify `summarize_nasdaq_quote()` so it returns:

```python
        "history_available": False,
        "history_points": 1,
```

Modify `summarize_yahoo_chart()` so it returns:

```python
        "history_available": len(closes) > 1,
        "history_points": len(closes),
```

- [ ] **Step 4: Add failing test for default range behavior**

Add this test to `tests/test_price_snapshot.py`:

```python
    def test_range_request_skips_quote_only_provider_when_history_required(self):
        calls = []

        def fake_stooq(symbol, range_, interval):
            calls.append("stooq")
            return {
                "summary": {
                    "source": "stooq_quote_csv",
                    "history_available": False,
                    "history_points": 1,
                },
                "raw": "csv",
            }

        def fake_nasdaq(symbol, range_, interval):
            calls.append("nasdaq")
            return {
                "summary": {
                    "source": "nasdaq_quote",
                    "history_available": False,
                    "history_points": 1,
                },
                "raw": {},
            }

        def fake_yahoo(symbol, range_, interval):
            calls.append("yahoo")
            return {
                "summary": {
                    "source": "yahoo_chart",
                    "history_available": True,
                    "history_points": 252,
                },
                "raw": {},
            }

        result = fetch_price_snapshot("AAPL", "1y", "1d", stooq_fetcher=fake_stooq, nasdaq_fetcher=fake_nasdaq, yahoo_fetcher=fake_yahoo)

        self.assertEqual(result["summary"]["source"], "yahoo_chart")
        self.assertEqual(calls, ["stooq", "nasdaq", "yahoo"])
        self.assertEqual(result["_fetch"]["attempts"][0]["status"], "quote_only")
        self.assertEqual(result["_fetch"]["attempts"][1]["status"], "quote_only")
```

- [ ] **Step 5: Implement history requirement gate**

Add this helper near `fetch_price_snapshot()`:

```python
def requires_history(range_: str) -> bool:
    normalized = range_.strip().lower()
    return normalized not in {"", "latest", "quote", "1d"}
```

Modify success path in `fetch_price_snapshot()` after `data = fetcher(...)`:

```python
            summary = data.get("summary", {})
            if requires_history(range_) and not summary.get("history_available"):
                attempts.append({
                    "provider": provider,
                    "status": "quote_only",
                    "reason": f"range={range_} requires history but provider returned {summary.get('history_points', 0)} point(s)",
                })
                continue
```

Keep existing final success block:

```python
        data.setdefault("_fetch", {})
        data["_fetch"]["attempts"] = attempts + [{"provider": provider, "status": "ok"}]
        return data
```

- [ ] **Step 6: Update existing tests for new default behavior**

Current `test_uses_stooq_before_yahoo` expects Stooq to win on default `range_="1y"`. Change fake Stooq summary to history-capable:

```python
            return {"summary": {"source": "stooq_csv", "history_available": True, "history_points": 252}, "raw": "csv"}
```

Current `test_falls_back_to_nasdaq_when_stooq_fails` expects Nasdaq to win on default `range_="1y"`. Since Nasdaq is quote-only, call `fetch_price_snapshot("AAPL", "quote", "1d", ...)` in that test.

- [ ] **Step 7: Run price tests and verify pass**

Run:

```bash
.venv/bin/python -m unittest tests.test_price_snapshot -v
```

Expected: PASS.

- [ ] **Step 8: Run full tests and commit Task 2**

Run:

```bash
.venv/bin/python -m unittest discover -s tests
git add scripts/fetch_price_snapshot.py tests/test_price_snapshot.py
git commit -m "fix(prices): separate quote and history output"
```

---

### Task 3: Add README Workflow Map

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README**

Create `README.md` with this content:

```markdown
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
```

- [ ] **Step 2: Verify README exists and contains routing table**

Run:

```bash
test -f README.md
rg -n "Which Question Uses Which Skill/Script|etf-analysis-review|update_company_bundle.py|Verification" README.md
```

Expected: `rg` prints matching lines for all patterns.

---

### Task 4: Extend US Analysis Bundle With Source And Valuation Slots

**Files:**
- Modify: `scripts/build_analysis_bundle.py`
- Modify: `tests/test_update_company_bundle.py`

- [ ] **Step 1: Write failing bundle-section test**

Add this test to `BuildBundleExplicitInputTest` in `tests/test_update_company_bundle.py`:

```python
    def test_build_bundle_includes_source_and_valuation_slots(self):
        from scripts.build_analysis_bundle import build_bundle

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "reports"
            with unittest.mock.patch("scripts.build_analysis_bundle.now_kst_iso", return_value="2026-05-14T10:00:00+09:00"):
                with unittest.mock.patch("scripts.build_analysis_bundle.read_json") as read_json_mock:
                    read_json_mock.side_effect = [
                        {
                            "ticker": "AAPL",
                            "market": "US",
                            "source": "sec_companyfacts",
                            "cik": "0000320193",
                            "periods": [{"year": 2024, "free_cash_flow": 108807000000}],
                        },
                        {
                            "_fetch": {
                                "source_url": "https://stooq.com/q/l/?s=aapl.us&f=sd2t2ohlcv&h=&e=csv",
                                "provider": "stooq",
                            },
                            "summary": {
                                "latest_close": 123.45,
                                "history_available": False,
                                "history_points": 1,
                            },
                        },
                    ]
                    output = build_bundle(
                        "AAPL",
                        output_dir=output_dir,
                        financials_path="explicit_financials.json",
                        price_path="explicit_price.json",
                    )

            text = output.read_text(encoding="utf-8")

        self.assertIn("## Filing Sources", text)
        self.assertIn("- financial_source: sec_companyfacts", text)
        self.assertIn("- cik: 0000320193", text)
        self.assertIn("- price_source_url: https://stooq.com/q/l/?s=aapl.us&f=sd2t2ohlcv&h=&e=csv", text)
        self.assertIn("## Valuation Slots", text)
        self.assertIn("- trailing_pe: missing", text)
        self.assertIn("- fcf_yield: missing", text)
        self.assertIn("## Source Gaps", text)
        self.assertIn("- valuation ratios require external/primary market-cap or enterprise-value source", text)
        self.assertIn("- price history is quote-only; range return/drawdown needs history-capable provider", text)
```

- [ ] **Step 2: Run bundle tests and verify failure**

Run:

```bash
.venv/bin/python -m unittest tests.test_update_company_bundle -v
```

Expected: FAIL because bundle does not include the new sections.

- [ ] **Step 3: Add helper functions**

Add these helpers to `scripts/build_analysis_bundle.py` after `_format_period()`:

```python
def _format_filing_sources(financials: dict, price_data: dict | None) -> list[str]:
    lines = ["## Filing Sources", ""]
    lines.append(f"- financial_source: {financials.get('source', 'missing')}")
    lines.append(f"- market: {financials.get('market', 'missing')}")
    lines.append(f"- cik: {financials.get('cik', 'missing')}")
    price_fetch = price_data.get("_fetch", {}) if price_data else {}
    lines.append(f"- price_provider: {price_fetch.get('provider', 'missing')}")
    lines.append(f"- price_source_url: {price_fetch.get('source_url', 'missing')}")
    lines.append("")
    return lines


def _format_valuation_slots() -> list[str]:
    return [
        "## Valuation Slots",
        "",
        "- market_cap: missing",
        "- enterprise_value: missing",
        "- trailing_pe: missing",
        "- forward_pe: missing",
        "- ev_to_ebitda: missing",
        "- fcf_yield: missing",
        "- peer_set: missing",
        "",
    ]


def _format_source_gaps(price_data: dict | None) -> list[str]:
    gaps = [
        "## Source Gaps",
        "",
        "- valuation ratios require external/primary market-cap or enterprise-value source",
        "- peer comparison requires explicitly selected comparable companies",
    ]
    summary = price_data.get("summary", {}) if price_data else {}
    if price_data is None:
        gaps.append("- price source is missing")
    elif not summary.get("history_available"):
        gaps.append("- price history is quote-only; range return/drawdown needs history-capable provider")
    gaps.append("")
    return gaps
```

- [ ] **Step 4: Insert sections in bundle output**

Modify `build_bundle()` after price summary block and before `## Memo Prompts`:

```python
    lines.extend(_format_filing_sources(financials, price_data))
    lines.extend(_format_valuation_slots())
    lines.extend(_format_source_gaps(price_data))
```

- [ ] **Step 5: Run bundle tests and verify pass**

Run:

```bash
.venv/bin/python -m unittest tests.test_update_company_bundle -v
```

Expected: PASS.

---

### Task 5: Final Verification And Commit Docs/Bundle Work

**Files:**
- Create: `README.md`
- Modify: `scripts/build_analysis_bundle.py`
- Modify: `tests/test_update_company_bundle.py`

- [ ] **Step 1: Run full local verification**

Run:

```bash
.venv/bin/python -m unittest discover -s tests
```

Expected: all tests PASS.

- [ ] **Step 2: Run uv verification when available**

Run:

```bash
uv run python -m unittest discover -s tests
```

Expected when cache access is allowed: all tests PASS. If sandbox blocks `~/.cache/uv`, record the exact error in the final report and rely on `.venv/bin/python` verification.

- [ ] **Step 3: Commit Task 3 and Task 4**

Run:

```bash
git add README.md scripts/build_analysis_bundle.py tests/test_update_company_bundle.py
git commit -m "docs: map workflows and add bundle evidence slots"
```

- [ ] **Step 4: Review final diff**

Run:

```bash
git status --short
git log --oneline -3
```

Expected:

```text
feat(skills): add ETF analysis workflow
fix(prices): separate quote and history output
docs: map workflows and add bundle evidence slots
```

Self-check:

- ETF questions have project-local routing.
- Price summaries expose quote-only versus history-capable data.
- README maps user question types to skills/scripts.
- Bundle contains source, valuation, and source-gap sections without fabricated ratios.
- No generated `data/raw`, `data/normalized`, or `data/reports` payloads are staged.

---

## Execution Handoff

Plan complete. Two execution options:

1. **Subagent-Driven (recommended)** - dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - execute tasks in this session using executing-plans, batch execution with checkpoints.
