from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.invest_utils import now_kst_date, read_json
    from scripts.portfolio_utils import load_portfolio_context, normalize_symbol
except ModuleNotFoundError:
    from invest_utils import now_kst_date, read_json
    from portfolio_utils import load_portfolio_context, normalize_symbol


def _number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def _price_for(prices: dict[str, Any], ticker: str) -> dict[str, Any] | None:
    direct = prices.get(ticker) or prices.get(normalize_symbol(ticker))
    if isinstance(direct, dict):
        return direct
    if isinstance(direct, (int, float)):
        return {"price": direct}
    return None


def _value_krw(value: float | None, currency: str, usd_krw: float | None) -> int | None:
    if value is None:
        return None
    if currency.upper() == "KRW":
        return int(round(value))
    if currency.upper() == "USD" and usd_krw is not None:
        return int(round(value * usd_krw))
    return None


def build_snapshot(
    root: str | Path = ".",
    prices: dict[str, Any] | None = None,
    usd_krw: float | None = None,
) -> dict[str, Any]:
    context = load_portfolio_context(root)
    price_map = prices or {}
    positions = []
    for holding in context.get("holdings", []) or []:
        ticker = str(holding.get("ticker", ""))
        currency = str(holding.get("currency", "KRW")).upper()
        shares = _number(holding.get("shares"))
        avg_price = _number(holding.get("avg_price"))
        price_entry = _price_for(price_map, ticker) or {}
        current_price = _number(price_entry.get("price"))
        current_currency = str(price_entry.get("currency") or currency).upper()
        local_value = shares * current_price if shares is not None and current_price is not None else None
        current_value_krw = _value_krw(local_value, current_currency, usd_krw)
        if current_value_krw is None:
            current_value_krw = _number(holding.get("user_reported_value_krw"))
            current_value_krw = int(round(current_value_krw)) if current_value_krw is not None else None
        pnl_pct = None
        if avg_price not in (None, 0) and current_price is not None:
            pnl_pct = round((current_price / avg_price - 1.0) * 100.0, 2)
        positions.append(
            {
                "ticker": ticker,
                "name": holding.get("name"),
                "asset_type": holding.get("asset_type"),
                "account": holding.get("account"),
                "shares": shares,
                "avg_price": avg_price,
                "currency": currency,
                "current_price": current_price,
                "current_price_currency": current_currency if current_price is not None else None,
                "current_value_krw": current_value_krw,
                "pnl_pct": pnl_pct,
                "price_status": "fresh_input" if current_price is not None else "missing_price_using_reported_or_none",
            }
        )
    known_total = sum(position["current_value_krw"] or 0 for position in positions)
    for position in positions:
        value = position["current_value_krw"]
        position["known_positions_weight_pct"] = round(value / known_total * 100.0, 2) if value and known_total else None
    return {
        "base_date_seoul": now_kst_date(),
        "profile_as_of": context.get("profile", {}).get("as_of"),
        "usd_krw": usd_krw,
        "known_positions_value_krw": known_total,
        "portfolio_total_assets_krw": context.get("profile", {}).get("total_assets_krw"),
        "positions": positions,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute a portfolio snapshot from recorded holdings and supplied fresh prices.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--prices-json", help="JSON mapping ticker -> {price, currency}.")
    parser.add_argument("--usd-krw", type=float)
    args = parser.parse_args()
    prices = read_json(args.prices_json) if args.prices_json else {}
    print(json.dumps(build_snapshot(args.root, prices, args.usd_krw), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
