# Invest Workflow Efficiency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce repeated fetch time, repository bloat, and storage growth while preserving evidence-backed investment analysis reproducibility.

**Architecture:** Keep the current `fetch -> normalize -> bundle -> memo` pipeline, but make raw payloads compressed/local, fetches stale-aware, bundles deterministic, and repeated workflows available through one orchestration script. Preserve backwards compatibility with existing `.json` artifacts while writing new raw SEC artifacts as `.json.gz`.

**Tech Stack:** Python standard library only, `unittest`, `uv run python`, existing scripts under `scripts/`.

---

## File Map

- Modify `scripts/invest_utils.py`: gzip-aware JSON read/write, compact JSON option, date parsing helpers if needed.
- Modify `scripts/fetch_sec_companyfacts.py`: write `*.json.gz`, add `--stale-days`, `--refresh`, existing-file reuse.
- Modify `scripts/normalize_financials.py`: accept gzipped raw input, add optional date-stamped normalized output.
- Modify `scripts/build_analysis_bundle.py`: accept explicit `--financials` and `--price`, prefer filename date over mtime when auto-selecting.
- Modify `scripts/fetch_price_snapshot.py`: separate quote vs history modes and make range semantics truthful.
- Create `scripts/update_company_bundle.py`: one command for resolve/fetch-if-stale/normalize/price/bundle.
- Modify `.gitignore`: keep generated raw/cache/report payloads out of git by default.
- Create or modify tests under `tests/`: coverage for gzip JSON, stale reuse, deterministic bundle selection, price mode behavior, orchestrator dry-run/faked functions.
- Optional docs update: add a short workflow note to `AGENTS.md` or a new `docs/workflow.md` after implementation if CLI behavior changes.

## Task 1: Gzip-Aware JSON Utilities

**Files:**
- Modify: `scripts/invest_utils.py`
- Test: `tests/test_invest_utils.py`    

- [ ] **Step 1: Write failing tests**

Create `tests/test_invest_utils.py`:

```python
import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.invest_utils import read_json, write_json


class InvestUtilsTest(unittest.TestCase):
    def test_write_and_read_gzip_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.json.gz"

            output = write_json(path, {"b": 2, "a": 1})

            self.assertEqual(output, path)
            self.assertEqual(read_json(path), {"a": 1, "b": 2})
            with gzip.open(path, "rt", encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"a": 1, "b": 2})

    def test_write_compact_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.json"

            write_json(path, {"a": 1, "b": 2}, compact=True)

            self.assertEqual(path.read_text(encoding="utf-8"), '{"a":1,"b":2}\n')


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_invest_utils -v`

Expected: fail because `write_json(..., compact=True)` is unsupported and `.json.gz` is not gzip-written.

- [ ] **Step 3: Implement minimal utility changes**

In `scripts/invest_utils.py`, update imports and functions:

```python
import gzip
import json
import re
import zipfile
```

Replace `read_json` and `write_json` with:

```python
def read_json(path: str | Path) -> Any:
    input_path = Path(path)
    opener = gzip.open if input_path.suffix == ".gz" else open
    with opener(input_path, "rt", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str | Path, data: Any, compact: bool = False) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if output.suffix == ".gz" else open
    kwargs = {"ensure_ascii": False, "sort_keys": True}
    if compact:
        kwargs["separators"] = (",", ":")
    else:
        kwargs["indent"] = 2
    with opener(output, "wt", encoding="utf-8") as f:
        json.dump(data, f, **kwargs)
        f.write("\n")
    return output
```

- [ ] **Step 4: Run utility tests**

Run: `.venv/bin/python -m unittest tests.test_invest_utils -v`

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/invest_utils.py tests/test_invest_utils.py
git commit -m "feat: support gzip json artifacts"
```

## Task 2: Compressed and Stale-Aware SEC Fetch

**Files:**
- Modify: `scripts/fetch_sec_companyfacts.py`
- Test: `tests/test_financial_pipeline.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_financial_pipeline.py`:

```python
import tempfile
from pathlib import Path

from scripts.fetch_sec_companyfacts import choose_companyfacts_output, latest_companyfacts_file, is_fresh_file


class SecFetchPolicyTest(unittest.TestCase):
    def test_companyfacts_output_is_gzipped(self):
        path = choose_companyfacts_output("AAPL", Path("data/raw/sec"), date_text="2026-05-12")
        self.assertEqual(path, Path("data/raw/sec/AAPL_2026-05-12_companyfacts.json.gz"))

    def test_latest_companyfacts_accepts_json_and_json_gz(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "AAPL_2026-05-10_companyfacts.json"
            new = root / "AAPL_2026-05-12_companyfacts.json.gz"
            old.write_text("{}", encoding="utf-8")
            new.write_bytes(b"not real gzip needed for selection")

            self.assertEqual(latest_companyfacts_file("AAPL", root), new)

    def test_is_fresh_file_uses_mtime_age(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AAPL_2026-05-12_companyfacts.json.gz"
            path.write_text("{}", encoding="utf-8")

            self.assertTrue(is_fresh_file(path, stale_days=7))
```

- [ ] **Step 2: Run tests to verify fail**

Run: `.venv/bin/python -m unittest tests.test_financial_pipeline -v`

Expected: import failure for new helper functions.

- [ ] **Step 3: Implement output selection and stale reuse**

In `scripts/fetch_sec_companyfacts.py`, add:

```python
from datetime import datetime, timedelta
```

Add helpers:

```python
def choose_companyfacts_output(ticker: str, out_dir: str | Path, date_text: str | None = None) -> Path:
    date_part = date_text or now_kst_date()
    return Path(out_dir) / f"{safe_symbol(ticker)}_{date_part}_companyfacts.json.gz"


def latest_companyfacts_file(ticker: str, out_dir: str | Path) -> Path | None:
    root = Path(out_dir)
    symbol = safe_symbol(ticker)
    matches = list(root.glob(f"{symbol}_*_companyfacts.json")) + list(root.glob(f"{symbol}_*_companyfacts.json.gz"))
    return sorted(matches, key=lambda p: p.stat().st_mtime, reverse=True)[0] if matches else None


def is_fresh_file(path: Path, stale_days: int) -> bool:
    if stale_days < 0:
        return False
    modified = datetime.fromtimestamp(path.stat().st_mtime)
    return datetime.now() - modified <= timedelta(days=stale_days)
```

Update CLI args and `main()`:

```python
parser.add_argument("--stale-days", type=int, default=7, help="Reuse latest local raw file if this fresh. Use -1 to force stale.")
parser.add_argument("--refresh", action="store_true", help="Always fetch even if a fresh local raw file exists.")
```

Then:

```python
out_dir = Path(args.out_dir)
existing = latest_companyfacts_file(args.ticker, out_dir)
if existing and not args.refresh and is_fresh_file(existing, args.stale_days):
    print(existing)
    return
data = fetch_companyfacts(args.ticker, args.cik)
output = choose_companyfacts_output(args.ticker, out_dir)
print(write_json(output, data, compact=True))
```

- [ ] **Step 4: Run SEC tests**

Run: `.venv/bin/python -m unittest tests.test_financial_pipeline -v`

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/fetch_sec_companyfacts.py tests/test_financial_pipeline.py
git commit -m "feat: compress and reuse sec raw data"
```

## Task 3: Reproducible Normalized Snapshots

**Files:**
- Modify: `scripts/normalize_financials.py`
- Test: `tests/test_financial_pipeline.py`

- [ ] **Step 1: Add failing test**

Append:

```python
from scripts.normalize_financials import normalized_output_path


class NormalizedOutputPolicyTest(unittest.TestCase):
    def test_normalized_output_can_be_date_stamped(self):
        path = normalized_output_path("AAPL", "sec", Path("data/normalized"), date_text="2026-05-12")
        self.assertEqual(path, Path("data/normalized/AAPL_2026-05-12_sec_normalized.json"))

    def test_normalized_output_keeps_legacy_default(self):
        path = normalized_output_path("AAPL", "sec", Path("data/normalized"), date_text=None)
        self.assertEqual(path, Path("data/normalized/AAPL_sec_normalized.json"))
```

- [ ] **Step 2: Run tests to verify fail**

Run: `.venv/bin/python -m unittest tests.test_financial_pipeline -v`

Expected: import failure for `normalized_output_path`.

- [ ] **Step 3: Implement output helper and CLI flag**

In `scripts/normalize_financials.py`, import `now_kst_date`:

```python
from scripts.invest_utils import now_kst_date, now_kst_iso, parse_amount, read_json, safe_symbol, write_json
```

Add:

```python
def normalized_output_path(ticker: str, source: str, output_dir: str | Path, date_text: str | None = None) -> Path:
    symbol = safe_symbol(ticker)
    if date_text:
        return Path(output_dir) / f"{symbol}_{date_text}_{source}_normalized.json"
    return Path(output_dir) / f"{symbol}_{source}_normalized.json"
```

Change `normalize_file` signature:

```python
def normalize_file(source: str, ticker: str, input_path: str | Path, output_dir: str | Path, dated: bool = False) -> Path:
```

Change output line:

```python
output = normalized_output_path(ticker, source, output_dir, now_kst_date() if dated else None)
```

Add parser flag:

```python
parser.add_argument("--dated", action="store_true", help="Write date-stamped normalized output for reproducible bundles.")
```

Call:

```python
output = normalize_file(args.source, args.ticker, args.input, args.output_dir, dated=args.dated)
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m unittest tests.test_financial_pipeline -v`

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/normalize_financials.py tests/test_financial_pipeline.py
git commit -m "feat: add dated normalized outputs"
```

## Task 4: Deterministic Bundle Inputs

**Files:**
- Modify: `scripts/build_analysis_bundle.py`
- Test: `tests/test_financial_pipeline.py`

- [ ] **Step 1: Add failing tests**

Append:

```python
from scripts.build_analysis_bundle import latest_artifact_by_name


class BundleSelectionTest(unittest.TestCase):
    def test_latest_artifact_uses_filename_date_before_mtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "AAPL_2026-05-01_sec_normalized.json"
            new = root / "AAPL_2026-05-12_sec_normalized.json"
            old.write_text("{}", encoding="utf-8")
            new.write_text("{}", encoding="utf-8")

            self.assertEqual(latest_artifact_by_name(root, "AAPL", "*_sec_normalized.json"), new)
```

- [ ] **Step 2: Run tests to verify fail**

Run: `.venv/bin/python -m unittest tests.test_financial_pipeline -v`

Expected: import failure.

- [ ] **Step 3: Implement deterministic selector and explicit CLI inputs**

In `scripts/build_analysis_bundle.py`, add:

```python
import re
```

Add:

```python
DATE_RE = re.compile(r"_(\d{4}-\d{2}-\d{2})_")


def _artifact_sort_key(path: Path) -> tuple[str, float]:
    match = DATE_RE.search(path.name)
    date_part = match.group(1) if match else ""
    return (date_part, path.stat().st_mtime)


def latest_artifact_by_name(root: str | Path, symbol: str, suffix_pattern: str) -> Path | None:
    safe = safe_symbol(symbol)
    matches = list(Path(root).glob(f"{safe}_{suffix_pattern}"))
    if not matches:
        return None
    return sorted(matches, key=_artifact_sort_key, reverse=True)[0]
```

Change `build_bundle` signature:

```python
def build_bundle(
    ticker: str,
    output_dir: str | Path = "data/reports",
    financials_path: str | Path | None = None,
    price_path: str | Path | None = None,
) -> Path:
```

Replace auto-selection:

```python
normalized = Path(financials_path) if financials_path else latest_artifact_by_name("data/normalized", symbol, "*_normalized.json")
price = Path(price_path) if price_path else latest_artifact_by_name("data/raw/prices", symbol, "*_price.json")
```

Add parser args:

```python
parser.add_argument("--financials")
parser.add_argument("--price")
```

Call:

```python
print(build_bundle(args.ticker, args.output_dir, args.financials, args.price))
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m unittest tests.test_financial_pipeline -v`

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_analysis_bundle.py tests/test_financial_pipeline.py
git commit -m "feat: make analysis bundles deterministic"
```

## Task 5: Price Quote vs History Modes

**Files:**
- Modify: `scripts/fetch_price_snapshot.py`
- Test: `tests/test_price_snapshot.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_price_snapshot.py`:

```python
from scripts.fetch_price_snapshot import build_stooq_history_url, build_stooq_quote_url


class PriceModeUrlTest(unittest.TestCase):
    def test_builds_stooq_quote_url(self):
        url = build_stooq_quote_url("AAPL")
        self.assertIn("q/l/", url)
        self.assertIn("s=aapl.us", url)

    def test_builds_stooq_history_url(self):
        url = build_stooq_history_url("AAPL", start="2025-05-12", end="2026-05-12")
        self.assertIn("q/d/l/", url)
        self.assertIn("s=aapl.us", url)
        self.assertIn("d1=20250512", url)
        self.assertIn("d2=20260512", url)
```

- [ ] **Step 2: Run tests to verify fail**

Run: `.venv/bin/python -m unittest tests.test_price_snapshot -v`

Expected: import failure for URL builders.

- [ ] **Step 3: Implement mode-specific URL builders**

In `scripts/fetch_price_snapshot.py`, add:

```python
from datetime import datetime, timedelta
```

Add constant:

```python
STOOQ_HISTORY_URL = "https://stooq.com/q/d/l/"
```

Add helpers:

```python
def _stooq_date(value: str) -> str:
    return value.replace("-", "")


def build_stooq_quote_url(symbol: str) -> str:
    params = {"s": yahoo_symbol_to_stooq(symbol), "f": "sd2t2ohlcv", "h": "", "e": "csv"}
    return f"{STOOQ_QUOTE_URL}?{urllib.parse.urlencode(params)}"


def build_stooq_history_url(symbol: str, start: str, end: str) -> str:
    params = {"s": yahoo_symbol_to_stooq(symbol), "i": "d", "d1": _stooq_date(start), "d2": _stooq_date(end)}
    return f"{STOOQ_HISTORY_URL}?{urllib.parse.urlencode(params)}"
```

Update `fetch_stooq_price_snapshot` to use `build_stooq_quote_url`.

Add `fetch_stooq_price_history`:

```python
def fetch_stooq_price_history(symbol: str, range_: str = "1y", interval: str = "1d") -> dict:
    if interval != "1d":
        raise RuntimeError("stooq history provider supports interval=1d only")
    end = datetime.now().date()
    start = end - timedelta(days=365 if range_ == "1y" else 30)
    url = build_stooq_history_url(symbol, start=start.isoformat(), end=end.isoformat())
    csv_text = http_bytes(url).decode("utf-8")
    return {
        "_fetch": {"provider": "stooq_history", "source_url": url, "symbol": symbol, "range": range_, "interval": interval},
        "summary": summarize_stooq_csv(csv_text, symbol),
        "raw": csv_text,
    }
```

Add CLI arg:

```python
parser.add_argument("--mode", choices=["quote", "history"], default="quote")
```

In `main()`, if `args.mode == "history"` and providers default was not changed, use `providers=["stooq_history", "yahoo"]`; otherwise keep quote behavior.

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m unittest tests.test_price_snapshot -v`

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/fetch_price_snapshot.py tests/test_price_snapshot.py
git commit -m "feat: split price quote and history modes"
```

## Task 6: One-Command Company Bundle Orchestrator

**Files:**
- Create: `scripts/update_company_bundle.py`
- Test: `tests/test_update_company_bundle.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_update_company_bundle.py`:

```python
import unittest

from scripts.update_company_bundle import source_for_market, price_mode_default


class UpdateCompanyBundleTest(unittest.TestCase):
    def test_source_for_market(self):
        self.assertEqual(source_for_market("US"), "sec")
        self.assertEqual(source_for_market("KR"), "dart")

    def test_price_mode_default(self):
        self.assertEqual(price_mode_default(history=False), "quote")
        self.assertEqual(price_mode_default(history=True), "history")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify fail**

Run: `.venv/bin/python -m unittest tests.test_update_company_bundle -v`

Expected: module import failure.

- [ ] **Step 3: Implement orchestrator**

Create `scripts/update_company_bundle.py`:

```python
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def source_for_market(market: str) -> str:
    normalized = market.upper()
    if normalized == "US":
        return "sec"
    if normalized == "KR":
        return "dart"
    raise ValueError(f"unknown market: {market}")


def price_mode_default(history: bool) -> str:
    return "history" if history else "quote"


def run_command(args: list[str]) -> str:
    completed = subprocess.run(args, check=True, text=True, capture_output=True)
    return completed.stdout.strip().splitlines()[-1]


def update_company_bundle(ticker: str, market: str, stale_days: int, price_history: bool) -> Path:
    source = source_for_market(market)
    if source != "sec":
        raise SystemExit("KR/DART orchestration needs OPENDART_API_KEY and should be enabled after DART E2E is verified.")

    raw_path = run_command([
        sys.executable,
        "scripts/fetch_sec_companyfacts.py",
        ticker,
        "--stale-days",
        str(stale_days),
    ])
    normalized_path = run_command([
        sys.executable,
        "scripts/normalize_financials.py",
        "--source",
        source,
        "--ticker",
        ticker,
        "--input",
        raw_path,
        "--dated",
    ])
    price_path = run_command([
        sys.executable,
        "scripts/fetch_price_snapshot.py",
        ticker,
        "--mode",
        price_mode_default(price_history),
    ])
    bundle_path = run_command([
        sys.executable,
        "scripts/build_analysis_bundle.py",
        ticker,
        "--financials",
        normalized_path,
        "--price",
        price_path,
    ])
    return Path(bundle_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch, normalize, price, and bundle a company analysis snapshot.")
    parser.add_argument("ticker")
    parser.add_argument("--market", choices=["US", "KR"], default="US")
    parser.add_argument("--stale-days", type=int, default=7)
    parser.add_argument("--price-history", action="store_true")
    args = parser.parse_args()
    print(update_company_bundle(args.ticker, args.market, args.stale_days, args.price_history))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run orchestrator tests**

Run: `.venv/bin/python -m unittest tests.test_update_company_bundle -v`

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/update_company_bundle.py tests/test_update_company_bundle.py
git commit -m "feat: add company bundle orchestrator"
```

## Task 7: Git Data Policy

**Files:**
- Modify: `.gitignore`
- Optional modify: `AGENTS.md`

- [ ] **Step 1: Update `.gitignore`**

Append:

```gitignore

# Generated investment data; final human-readable notes live in memos/
data/cache/*.json
data/raw/**/*.json
data/raw/**/*.json.gz
data/reports/*.md
```

- [ ] **Step 2: Keep directory placeholders tracked**

Run:

```bash
git add data/raw/.gitkeep data/normalized/.gitkeep data/reports/.gitkeep
```

Expected: placeholders remain available.

- [ ] **Step 3: Remove generated payloads from git index only**

Run:

```bash
git rm --cached data/cache/*.json data/raw/prices/*.json data/raw/sec/*.json data/reports/*.md
```

Expected: files remain on disk but are no longer tracked.

- [ ] **Step 4: Document policy in `AGENTS.md`**

Add one line after existing storage policy:

```markdown
- Keep generated raw/cache/report payloads local by default; commit final investment notes under `memos/` unless a specific raw artifact is needed for review.
```

- [ ] **Step 5: Commit**

```bash
git add .gitignore AGENTS.md data/raw/.gitkeep data/normalized/.gitkeep data/reports/.gitkeep
git commit -m "chore: keep generated market data local"
```

## Task 8: Final Verification

**Files:**
- All changed files

- [ ] **Step 1: Run full unit tests**

Run:

```bash
.venv/bin/python -m unittest -v
```

Expected: all tests pass.

- [ ] **Step 2: Run CLI help checks**

Run:

```bash
.venv/bin/python scripts/fetch_sec_companyfacts.py --help
.venv/bin/python scripts/normalize_financials.py --help
.venv/bin/python scripts/fetch_price_snapshot.py --help
.venv/bin/python scripts/build_analysis_bundle.py --help
.venv/bin/python scripts/update_company_bundle.py --help
```

Expected: each command exits 0 and shows expected new flags.

- [ ] **Step 3: Run no-network local smoke using existing raw file**

Run:

```bash
.venv/bin/python scripts/normalize_financials.py --source sec --ticker AAPL --input data/raw/sec/AAPL_2026-05-12_companyfacts.json --dated
.venv/bin/python scripts/build_analysis_bundle.py AAPL --financials data/normalized/AAPL_$(date +%Y-%m-%d)_sec_normalized.json --price data/raw/prices/AAPL_2026-05-12_price.json
```

Expected: dated normalized file and bundle are created locally.

- [ ] **Step 4: Inspect storage impact**

Run:

```bash
du -ah data | sort -h | tail -20
git status --short
```

Expected: new raw SEC outputs are `.json.gz`; generated raw/report payloads show as ignored or removed from index per policy.

- [ ] **Step 5: Commit final fixes if verification required changes**

```bash
git add scripts tests .gitignore AGENTS.md
git commit -m "test: verify efficient invest workflow"
```

## Self-Review

- Spec coverage: covers raw compression, stale fetch, git bloat, price quote/history ambiguity, deterministic bundles, normalized reproducibility, one-command workflow, verification.
- No placeholders: tasks include exact files, commands, and expected outcomes.
- Type consistency: helper names are introduced before later use: `write_json(..., compact=True)`, `choose_companyfacts_output`, `normalized_output_path`, `latest_artifact_by_name`, `build_stooq_*_url`, `source_for_market`.
- Risk note: `git rm --cached` changes tracked state but does not delete local files. Review `git status --short` before committing.
