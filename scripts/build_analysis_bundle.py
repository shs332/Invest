from __future__ import annotations

import argparse
from pathlib import Path

try:
    from scripts.invest_utils import latest_matching, now_kst_iso, read_json, safe_symbol
except ModuleNotFoundError:
    from invest_utils import latest_matching, now_kst_iso, read_json, safe_symbol


def _format_period(period: dict) -> str:
    keys = [
        "revenue",
        "operating_income",
        "net_income",
        "operating_cash_flow",
        "capital_expenditure",
        "free_cash_flow",
        "cash",
        "debt",
    ]
    lines = [f"- year: {period.get('year')}"]
    for key in keys:
        if key in period:
            lines.append(f"- {key}: {period[key]}")
    return "\n".join(lines)


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


def _format_valuation_slots(financials: dict, price_data: dict | None) -> list[str]:
    summary = price_data.get("summary", {}) if price_data else {}
    market_cap = summary.get("market_cap")
    periods = financials.get("periods", [])
    latest_period = periods[0] if periods else {}
    net_income = latest_period.get("net_income")
    free_cash_flow = latest_period.get("free_cash_flow")

    trailing_pe = "missing"
    if market_cap and net_income and net_income > 0:
        trailing_pe = round(market_cap / net_income, 2)

    fcf_yield = "missing"
    if market_cap and free_cash_flow is not None:
        fcf_yield = f"{round(free_cash_flow / market_cap * 100, 2)}%"

    return [
        "## Valuation Slots",
        "",
        f"- market_cap: {market_cap if market_cap is not None else 'missing'}",
        "- enterprise_value: missing",
        f"- trailing_pe: {trailing_pe}",
        "- forward_pe: missing",
        "- ev_to_ebitda: missing",
        f"- fcf_yield: {fcf_yield}",
        "- peer_set: missing",
        "",
    ]


def _format_source_gaps(price_data: dict | None) -> list[str]:
    gaps = ["## Source Gaps", ""]
    summary = price_data.get("summary", {}) if price_data else {}
    if not summary.get("market_cap"):
        gaps.append("- valuation ratios require external/primary market-cap or enterprise-value source")
    else:
        gaps.append(
            "- enterprise_value, forward_pe, and ev_to_ebitda still require a debt/forward-estimate "
            "source beyond market_cap"
        )
    gaps.append("- peer comparison requires explicitly selected comparable companies")
    if price_data is None:
        gaps.append("- price source is missing")
    elif not summary.get("history_available"):
        gaps.append("- price history is quote-only; range return/drawdown needs history-capable provider")
    gaps.append("")
    return gaps


def build_bundle(
    ticker: str,
    output_dir: str | Path = "data/reports",
    financials_path: str | Path | None = None,
    price_path: str | Path | None = None,
) -> Path:
    symbol = safe_symbol(ticker)
    normalized = (
        Path(financials_path)
        if financials_path
        else latest_matching(f"data/normalized/{symbol}_*_normalized.json")
    )
    price = (
        Path(price_path)
        if price_path
        else latest_matching(f"data/raw/prices/{symbol}_*_price.json")
    )
    if normalized is None:
        raise SystemExit(f"No normalized financial file found for {ticker}.")

    financials = read_json(normalized)
    price_data = read_json(price) if price else None

    lines = [
        f"# {ticker.upper()} Analysis Bundle",
        "",
        f"- generated_at: {now_kst_iso()}",
        f"- financials: {normalized}",
        f"- price: {price or 'missing'}",
        "",
        "## Financial Periods",
        "",
    ]
    for period in financials.get("periods", [])[:5]:
        lines.append(_format_period(period))
        lines.append("")
    if price_data:
        lines.extend(["## Price Summary", ""])
        for key, value in price_data.get("summary", {}).items():
            lines.append(f"- {key}: {value}")
        lines.append("")
    lines.extend(_format_filing_sources(financials, price_data))
    lines.extend(_format_valuation_slots(financials, price_data))
    lines.extend(_format_source_gaps(price_data))
    lines.extend(
        [
            "## Memo Prompts",
            "",
            "- Run `financial-statement-review` on the financial periods above.",
            "- Run `market-move-explainer` if the price move is material.",
            "- Run `risk-manager-investment-memo` for conditional action and invalidation triggers.",
            "",
        ]
    )

    output = Path(output_dir) / f"{symbol}_{now_kst_iso()[:10]}_bundle.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a markdown bundle from latest normalized and price data.")
    parser.add_argument("ticker")
    parser.add_argument("--output-dir", default="data/reports")
    parser.add_argument("--financials", help="Explicit normalized financials path.")
    parser.add_argument("--price", help="Explicit price snapshot path.")
    args = parser.parse_args()
    print(build_bundle(args.ticker, args.output_dir, args.financials, args.price))


if __name__ == "__main__":
    main()
