from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta
from pathlib import Path

try:
    from scripts.invest_utils import http_json, load_project_env, now_kst_date, safe_symbol, write_json
    from scripts.resolve_company import resolve_company
except ModuleNotFoundError:
    from invest_utils import http_json, load_project_env, now_kst_date, safe_symbol, write_json
    from resolve_company import resolve_company


SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"


def _headers() -> dict[str, str]:
    user_agent = os.environ.get("SEC_USER_AGENT", "invest-workspace/0.1 contact@example.com")
    return {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate", "Host": "data.sec.gov"}


def resolve_cik(ticker: str) -> str:
    for match in resolve_company(ticker, "US", limit=1):
        if match.get("cik"):
            return str(match["cik"]).zfill(10)
    raise SystemExit(f"Ticker not found in SEC company_tickers.json: {ticker}")


def fetch_companyfacts(ticker: str, cik: str | None = None) -> dict:
    resolved = (cik or resolve_cik(ticker)).zfill(10)
    url = SEC_COMPANYFACTS_URL.format(cik=resolved)
    data = http_json(url, headers=_headers())
    data["_fetch"] = {
        "source_url": url,
        "ticker": ticker.upper(),
        "cik": resolved,
        "note": "Set SEC_USER_AGENT to a descriptive contact string for production use.",
    }
    return data


def choose_companyfacts_output(ticker: str, out_dir: str | Path, date_text: str | None = None) -> Path:
    date_part = date_text or now_kst_date()
    return Path(out_dir) / f"{safe_symbol(ticker)}_{date_part}_companyfacts.json.gz"


def latest_companyfacts_file(ticker: str, out_dir: str | Path) -> Path | None:
    root = Path(out_dir)
    symbol = safe_symbol(ticker)
    matches = list(root.glob(f"{symbol}_*_companyfacts.json")) + list(root.glob(f"{symbol}_*_companyfacts.json.gz"))
    # mtime selects the most recently written local artifact, not the date in the filename.
    return sorted(matches, key=lambda p: p.stat().st_mtime, reverse=True)[0] if matches else None


def is_fresh_file(path: Path, stale_days: int) -> bool:
    if stale_days < 0:
        return False
    modified = datetime.fromtimestamp(path.stat().st_mtime)
    return datetime.now() - modified <= timedelta(days=stale_days)


def should_reuse_companyfacts(existing: Path | None, refresh: bool, cik: str | None, stale_days: int) -> bool:
    return bool(existing and not refresh and not cik and is_fresh_file(existing, stale_days))


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch SEC companyfacts JSON for a US ticker.")
    parser.add_argument("ticker")
    parser.add_argument("--cik")
    parser.add_argument("--out-dir", default="data/raw/sec")
    parser.add_argument("--stale-days", type=int, default=7, help="Reuse latest local raw file if this fresh. Use -1 to force stale.")
    parser.add_argument("--refresh", action="store_true", help="Always fetch even if a fresh local raw file exists.")
    args = parser.parse_args()
    load_project_env()
    out_dir = Path(args.out_dir)
    existing = latest_companyfacts_file(args.ticker, out_dir)
    if should_reuse_companyfacts(existing, args.refresh, args.cik, args.stale_days):
        print(existing)
        return
    data = fetch_companyfacts(args.ticker, args.cik)
    output = choose_companyfacts_output(args.ticker, out_dir)
    print(write_json(output, data, compact=True))


if __name__ == "__main__":
    main()
