from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.invest_utils import now_kst_date
    from scripts.portfolio_utils import (
        find_security,
        is_price_move_question,
        is_return_seeking_question,
        load_portfolio_context,
        normalize_symbol,
    )
except ModuleNotFoundError:
    from invest_utils import now_kst_date
    from portfolio_utils import (
        find_security,
        is_price_move_question,
        is_return_seeking_question,
        load_portfolio_context,
        normalize_symbol,
    )


def _asset_type(security: dict[str, Any] | None) -> str:
    if not security:
        return "stock"
    return str(security.get("asset_type") or "stock").lower()


def _market(security: dict[str, Any] | None, ticker: str | None) -> str:
    if security and security.get("market"):
        return str(security["market"]).upper()
    if ticker and normalize_symbol(ticker).endswith(".KS"):
        return "KR"
    return "US"


def _route(query: str, security: dict[str, Any] | None, ticker: str | None) -> dict[str, Any]:
    symbol = normalize_symbol(str((security or {}).get("ticker") or ticker or "UNKNOWN"))
    market = _market(security, symbol)
    asset_type = _asset_type(security)

    if is_price_move_question(query):
        primary_skill = "market-move-explainer"
    elif asset_type == "etf":
        primary_skill = "etf-analysis-review"
    elif market == "KR":
        primary_skill = "kr-stock-analysis-review"
    elif is_return_seeking_question(query):
        primary_skill = "us-stock-return-opportunity"
    else:
        primary_skill = "us-stock-decision-workflow"

    script_asset_type = "ETF" if asset_type == "etf" else "stock"
    return {
        "primary_skill": primary_skill,
        "market": market,
        "asset_type": asset_type,
        "local_scripts": [
            f"uv run python scripts/update_asset_bundle.py {symbol} --market {market} --asset-type {script_asset_type}"
        ],
        "final_label_owner": "risk-manager-investment-memo",
    }


def build_context_pack(query: str, root: str | Path = ".", ticker: str | None = None) -> dict[str, Any]:
    context = load_portfolio_context(root)
    security = find_security(context, query, ticker)
    route = _route(query, security, ticker)
    portfolio_aware = security is not None or route["primary_skill"] in {
        "us-stock-decision-workflow",
        "us-stock-return-opportunity",
        "kr-stock-analysis-review",
        "etf-analysis-review",
    }
    return {
        "base_date_seoul": now_kst_date(),
        "query": query,
        "portfolio_aware": portfolio_aware,
        "portfolio_files": context["paths"],
        "profile_as_of": context.get("profile", {}).get("as_of"),
        "matched_security": security,
        "route": route,
        "public_equity_investing": {
            "role": "supplemental",
            "use_when": "formal artifact, model, tracker, pitch, scenario, or QC is explicitly requested",
            "must_not_override": ["local final action labels", "portfolio files", "risk controls"],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a portfolio-aware routing context pack for an investment question.")
    parser.add_argument("query")
    parser.add_argument("--ticker")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    print(json.dumps(build_context_pack(args.query, args.root, args.ticker), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
