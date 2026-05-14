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
