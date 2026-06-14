from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from scripts.build_analysis_bundle import build_bundle
    from scripts.fetch_dart_financials import fetch_dart_financials
    from scripts.fetch_price_snapshot import fetch_price_snapshot
    from scripts.invest_utils import KST, now_kst_date, now_kst_iso, safe_symbol, write_json
    from scripts.normalize_financials import normalize_file
    from scripts.resolve_company import resolve_company
    from scripts.update_company_bundle import update_company_bundle
except ModuleNotFoundError:
    from build_analysis_bundle import build_bundle
    from fetch_dart_financials import fetch_dart_financials
    from fetch_price_snapshot import fetch_price_snapshot
    from invest_utils import KST, now_kst_date, now_kst_iso, safe_symbol, write_json
    from normalize_financials import normalize_file
    from resolve_company import resolve_company
    from update_company_bundle import update_company_bundle


def _plain_kr_ticker(symbol: str) -> str:
    return symbol.upper().removesuffix(".KS").removesuffix(".KQ")


def determine_asset_route(symbol: str, market: str, asset_type: str = "auto") -> dict[str, Any]:
    normalized_market = market.upper()
    normalized_type = asset_type.lower()
    if normalized_type == "etf":
        return {"pipeline": "etf", "symbol": symbol, "market": normalized_market}
    if normalized_market == "US":
        return {"pipeline": "us_stock", "symbol": symbol.upper(), "market": "US"}
    if normalized_market == "KR":
        return {"pipeline": "kr_stock", "symbol": symbol.upper(), "market": "KR"}
    raise ValueError(f"unknown market: {market}")


def _write_price(symbol: str, output_dir: str | Path, price_range: str, price_interval: str) -> Path:
    price_data = fetch_price_snapshot(symbol, price_range, price_interval)
    output = Path(output_dir) / "raw" / "prices" / f"{safe_symbol(symbol)}_{now_kst_date()}_price.json"
    return write_json(output, price_data)


def _build_etf_bundle(symbol: str, price_path: str | Path | None, output_dir: str | Path = "data") -> Path:
    lines = [
        f"# {symbol.upper()} ETF Bundle",
        "",
        f"- generated_at: {now_kst_iso()}",
        f"- price: {price_path or 'missing'}",
        "",
        "## ETF Evidence Checklist",
        "",
        "- issuer_fund_page: missing",
        "- prospectus_or_summary_prospectus: missing",
        "- holdings_or_portfolio_composition: missing",
        "- index_methodology: missing",
        "- expense_ratio: missing",
        "- AUM_liquidity_bid_ask: missing",
        "- NAV_premium_discount: missing",
        "- tracking_difference_or_error: missing",
        "- distribution_tax_currency_notes: missing",
        "",
        "## Memo Prompts",
        "",
        "- Run `etf-analysis-review` after issuer and index evidence is checked.",
        "- Run `risk-manager-investment-memo` only after ETF-specific evidence is summarized.",
        "",
    ]
    output = Path(output_dir) / "reports" / f"{safe_symbol(symbol)}_{now_kst_date()}_etf_bundle.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def _resolve_corp_code(symbol: str, corp_code: str | None) -> str:
    if corp_code:
        return corp_code
    query = _plain_kr_ticker(symbol)
    matches = resolve_company(query, "KR", limit=1)
    if not matches:
        raise RuntimeError(f"No DART corp_code match for {symbol}. Pass --corp-code explicitly.")
    return str(matches[0]["corp_code"])


def update_asset_bundle(
    symbol: str,
    market: str,
    asset_type: str = "auto",
    corp_code: str | None = None,
    year: int | None = None,
    report_code: str = "11011",
    output_dir: str | Path = "data",
    price_range: str = "1y",
    price_interval: str = "1d",
) -> Path:
    route = determine_asset_route(symbol, market, asset_type)
    if route["pipeline"] == "us_stock":
        return update_company_bundle(route["symbol"], "US", price_range, price_interval)
    if route["pipeline"] == "etf":
        try:
            price_path = _write_price(route["symbol"], output_dir, price_range, price_interval)
        except RuntimeError:
            price_path = None
        return _build_etf_bundle(route["symbol"], price_path, output_dir)

    selected_year = year or datetime.now(KST).year - 1
    selected_corp_code = _resolve_corp_code(route["symbol"], corp_code)
    ticker = _plain_kr_ticker(route["symbol"])
    raw = fetch_dart_financials(selected_corp_code, selected_year, report_code)
    raw_path = Path(output_dir) / "raw" / "dart" / f"{safe_symbol(ticker)}_{selected_year}_{report_code}_{now_kst_date()}_dart.json"
    write_json(raw_path, raw)
    normalized_path = normalize_file("dart", ticker, raw_path, Path(output_dir) / "normalized")
    try:
        price_path = _write_price(route["symbol"], output_dir, price_range, price_interval)
    except RuntimeError:
        price_path = None
    return build_bundle(ticker, Path(output_dir) / "reports", normalized_path, price_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch, normalize, price, and bundle a US stock, Korean stock, or ETF.")
    parser.add_argument("symbol")
    parser.add_argument("--market", choices=["US", "KR"], required=True)
    parser.add_argument("--asset-type", choices=["auto", "stock", "ETF", "etf"], default="auto")
    parser.add_argument("--corp-code", help="Required for KR stocks when resolver cache/env is unavailable.")
    parser.add_argument("--year", type=int)
    parser.add_argument("--report-code", default="11011")
    parser.add_argument("--output-dir", default="data")
    parser.add_argument("--price-range", default="1y")
    parser.add_argument("--price-interval", default="1d")
    args = parser.parse_args()
    try:
        output = update_asset_bundle(
            args.symbol,
            args.market,
            args.asset_type,
            args.corp_code,
            args.year,
            args.report_code,
            args.output_dir,
            args.price_range,
            args.price_interval,
        )
    except RuntimeError as exc:
        raise SystemExit(str(exc))
    print(output)


if __name__ == "__main__":
    main()
