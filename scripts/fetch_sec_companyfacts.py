from __future__ import annotations

import argparse
import os
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch SEC companyfacts JSON for a US ticker.")
    parser.add_argument("ticker")
    parser.add_argument("--cik")
    parser.add_argument("--out-dir", default="data/raw/sec")
    args = parser.parse_args()
    load_project_env()
    try:
        data = fetch_companyfacts(args.ticker, args.cik)
    except RuntimeError as exc:
        raise SystemExit(str(exc))
    output = Path(args.out_dir) / f"{safe_symbol(args.ticker)}_{now_kst_date()}_companyfacts.json"
    print(write_json(output, data))


if __name__ == "__main__":
    main()
