from __future__ import annotations

import argparse
import os
import urllib.parse
from datetime import datetime
from pathlib import Path

try:
    from scripts.invest_utils import http_json, load_project_env, now_kst_date, safe_symbol, validate_dart_response, write_json
except ModuleNotFoundError:
    from invest_utils import http_json, load_project_env, now_kst_date, safe_symbol, validate_dart_response, write_json


DART_FINANCIALS_URL = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"


def fetch_dart_financials(
    corp_code: str,
    year: int,
    report_code: str = "11011",
    fs_div: str = "CFS",
    api_key: str | None = None,
    allow_empty: bool = False,
) -> dict:
    key = api_key or os.environ.get("OPENDART_API_KEY") or os.environ.get("DART_API_KEY")
    if not key:
        raise SystemExit("Missing OPENDART_API_KEY or DART_API_KEY environment variable.")
    params = {
        "crtfc_key": key,
        "corp_code": corp_code,
        "bsns_year": str(year),
        "reprt_code": report_code,
        "fs_div": fs_div,
    }
    url = f"{DART_FINANCIALS_URL}?{urllib.parse.urlencode(params)}"
    data = http_json(url)
    data["_fetch"] = {
        "source_url": DART_FINANCIALS_URL,
        "corp_code": corp_code,
        "bsns_year": year,
        "reprt_code": report_code,
        "fs_div": fs_div,
    }
    validate_dart_response(data, allow_empty=allow_empty)
    return data


def main() -> None:
    default_year = datetime.now().year - 1
    parser = argparse.ArgumentParser(description="Fetch OpenDART single-company full financial statements.")
    parser.add_argument("corp_code", help="OpenDART corp_code, not stock ticker.")
    parser.add_argument("--ticker", help="Optional stock ticker used only for output filename.")
    parser.add_argument("--year", type=int, default=default_year)
    parser.add_argument("--report-code", help="11011 annual, 11013 Q1, 11012 half, 11014 Q3.")
    parser.add_argument("--fs-div", default="CFS", choices=["CFS", "OFS"])
    parser.add_argument("--allow-empty", action="store_true", help="Write provider response even when OpenDART has no rows.")
    parser.add_argument("--out-dir", default="data/raw/dart")
    args = parser.parse_args()
    load_project_env()
    if args.report_code is None and args.year >= datetime.now().year:
        raise SystemExit("Current-year DART fetch requires explicit --report-code (11013 Q1, 11012 half, 11014 Q3, or 11011 annual after filing).")
    report_code = args.report_code or "11011"
    try:
        data = fetch_dart_financials(args.corp_code, args.year, report_code, args.fs_div, allow_empty=args.allow_empty)
    except RuntimeError as exc:
        raise SystemExit(str(exc))
    label = args.ticker or args.corp_code
    output = Path(args.out_dir) / f"{safe_symbol(label)}_{args.year}_{report_code}_{now_kst_date()}_dart.json"
    print(write_json(output, data))


if __name__ == "__main__":
    main()
