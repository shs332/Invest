from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

try:
    from scripts.invest_utils import http_bytes, http_json, read_json, read_zip_text, write_json
except ModuleNotFoundError:
    from invest_utils import http_bytes, http_json, read_json, read_zip_text, write_json


SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
DART_CORP_CODE_URL = "https://opendart.fss.or.kr/api/corpCode.xml"
DEFAULT_SEC_CACHE = Path("data/cache/sec_company_tickers.json")
DEFAULT_DART_CACHE = Path("data/cache/dart_corp_codes.json")


def _sec_headers() -> dict[str, str]:
    return {"User-Agent": os.environ.get("SEC_USER_AGENT", "invest-workspace/0.1 contact@example.com")}


def ensure_sec_cache(path: Path = DEFAULT_SEC_CACHE, refresh: bool = False) -> Path:
    if path.exists() and not refresh:
        return path
    data = http_json(SEC_TICKERS_URL, headers=_sec_headers())
    return write_json(path, data)


def ensure_dart_cache(path: Path = DEFAULT_DART_CACHE, refresh: bool = False, api_key: str | None = None) -> Path:
    if path.exists() and not refresh:
        return path
    key = api_key or os.environ.get("OPENDART_API_KEY") or os.environ.get("DART_API_KEY")
    if not key:
        raise SystemExit("Missing OPENDART_API_KEY or DART_API_KEY environment variable.")
    url = f"{DART_CORP_CODE_URL}?{urllib.parse.urlencode({'crtfc_key': key})}"
    xml_text = read_zip_text(http_bytes(url), ".xml")
    root = ET.fromstring(xml_text)
    rows = []
    for item in root.findall("list"):
        row = {child.tag: (child.text or "").strip() for child in item}
        if row:
            rows.append(row)
    return write_json(path, rows)


def _normalize_text(value: str) -> str:
    return value.casefold().replace(" ", "").replace(".", "").replace(",", "").strip()


def _load_sec_rows(cache_path: Path) -> list[dict[str, Any]]:
    data = read_json(cache_path)
    rows = []
    for item in data.values() if isinstance(data, dict) else data:
        rows.append(
            {
                "market": "US",
                "ticker": str(item.get("ticker", "")).upper(),
                "cik": str(item.get("cik_str", "")).zfill(10),
                "name": item.get("title"),
            }
        )
    return rows


def resolve_us_company(query: str, cache_path: str | Path = DEFAULT_SEC_CACHE, limit: int = 10) -> list[dict[str, Any]]:
    rows = _load_sec_rows(Path(cache_path))
    wanted = query.strip().upper()
    wanted_text = _normalize_text(query)
    exact_ticker = [dict(row, confidence="exact_ticker") for row in rows if row["ticker"] == wanted]
    if exact_ticker:
        return exact_ticker[:limit]
    exact_name = [dict(row, confidence="exact_name") for row in rows if _normalize_text(str(row.get("name", ""))) == wanted_text]
    if exact_name:
        return exact_name[:limit]
    contains = [
        dict(row, confidence="name_contains")
        for row in rows
        if wanted_text and wanted_text in _normalize_text(str(row.get("name", "")))
    ]
    return contains[:limit]


def _load_dart_rows(cache_path: Path) -> list[dict[str, Any]]:
    data = read_json(cache_path)
    rows = []
    for item in data:
        stock_code = str(item.get("stock_code", "")).strip()
        rows.append(
            {
                "market": "KR",
                "ticker": stock_code,
                "corp_code": str(item.get("corp_code", "")).strip(),
                "name": item.get("corp_name"),
                "modify_date": item.get("modify_date"),
                "listed": bool(stock_code),
            }
        )
    return rows


def resolve_kr_company(query: str, cache_path: str | Path = DEFAULT_DART_CACHE, limit: int = 10) -> list[dict[str, Any]]:
    rows = _load_dart_rows(Path(cache_path))
    wanted = query.strip()
    wanted_text = _normalize_text(query)
    exact_stock = [dict(row, confidence="exact_stock_code") for row in rows if row["ticker"] == wanted]
    if exact_stock:
        return exact_stock[:limit]
    exact_name = [dict(row, confidence="exact_name") for row in rows if _normalize_text(str(row.get("name", ""))) == wanted_text]
    if exact_name:
        return sorted(exact_name, key=lambda row: not row["listed"])[:limit]
    contains = [
        dict(row, confidence="name_contains")
        for row in rows
        if wanted_text and wanted_text in _normalize_text(str(row.get("name", "")))
    ]
    return sorted(contains, key=lambda row: not row["listed"])[:limit]


def resolve_company(query: str, market: str, refresh: bool = False, limit: int = 10) -> list[dict[str, Any]]:
    if market.upper() == "US":
        cache = ensure_sec_cache(refresh=refresh)
        return resolve_us_company(query, cache, limit)
    if market.upper() == "KR":
        cache = ensure_dart_cache(refresh=refresh)
        return resolve_kr_company(query, cache, limit)
    raise ValueError(f"unknown market: {market}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve company names/tickers to SEC CIK or DART corp_code.")
    parser.add_argument("query")
    parser.add_argument("--market", choices=["US", "KR"], required=True)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--json", action="store_true", help="Print raw JSON matches.")
    args = parser.parse_args()
    matches = resolve_company(args.query, args.market, args.refresh, args.limit)
    if args.json:
        print(json.dumps(matches, ensure_ascii=False, indent=2))
        return
    if not matches:
        raise SystemExit(f"No match for {args.query} in {args.market}.")
    for i, match in enumerate(matches, 1):
        if args.market == "US":
            print(f"{i}. {match['ticker']} | CIK {match['cik']} | {match['name']} | {match['confidence']}")
        else:
            print(f"{i}. {match['ticker'] or '-'} | corp_code {match['corp_code']} | {match['name']} | {match['confidence']}")


if __name__ == "__main__":
    main()

