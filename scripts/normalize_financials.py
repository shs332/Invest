from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    from scripts.invest_utils import (
        now_kst_date,
        now_kst_iso,
        parse_amount,
        read_json,
        safe_symbol,
        write_json,
    )
except ModuleNotFoundError:
    from invest_utils import (
        now_kst_date,
        now_kst_iso,
        parse_amount,
        read_json,
        safe_symbol,
        write_json,
    )


SEC_CONCEPTS = {
    "revenue": [
        "Revenues",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
    ],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "operating_cash_flow": [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    ],
    "capital_expenditure": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
    ],
    "cash": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    ],
    "assets": ["Assets"],
    "liabilities": ["Liabilities"],
    "equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "debt": [
        "LongTermDebt",
        "LongTermDebtAndFinanceLeaseObligations",
        "ShortTermBorrowings",
    ],
}


DART_PATTERNS = {
    "revenue": ["매출액", "영업수익"],
    "operating_income": ["영업이익"],
    "net_income": ["당기순이익", "분기순이익", "반기순이익"],
    "operating_cash_flow": ["영업활동 현금흐름", "영업활동으로 인한 현금흐름"],
    "capital_expenditure": ["유형자산의 취득", "유형자산 취득", "유형자산의취득"],
    "cash": ["현금및현금성자산"],
    "assets": ["자산총계"],
    "liabilities": ["부채총계"],
    "equity": ["자본총계"],
}


def _sec_annual_values(raw: dict[str, Any], concept_names: list[str]) -> dict[int, int | float]:
    facts = raw.get("facts", {}).get("us-gaap", {})
    values_by_year: dict[int, tuple[str, int | float]] = {}
    for concept_name in concept_names:
        concept = facts.get(concept_name)
        if not concept:
            continue
        for unit_values in concept.get("units", {}).values():
            for item in unit_values:
                if item.get("fp") != "FY":
                    continue
                if not str(item.get("form", "")).startswith("10-K"):
                    continue
                year = parse_amount(item.get("fy"))
                value = parse_amount(item.get("val"))
                if year is None or value is None:
                    continue
                filed = str(item.get("filed", ""))
                current = values_by_year.get(int(year))
                if current is None or filed >= current[0]:
                    values_by_year[int(year)] = (filed, value)
    return {year: value for year, (_, value) in values_by_year.items()}


def _add_free_cash_flow(period: dict[str, Any]) -> None:
    cfo = period.get("operating_cash_flow")
    capex = period.get("capital_expenditure")
    if cfo is not None and capex is not None:
        period["capital_expenditure"] = abs(capex)
        period["free_cash_flow"] = cfo - abs(capex)


def normalize_sec_companyfacts(raw: dict[str, Any], ticker: str, market: str = "US") -> dict[str, Any]:
    metric_values = {
        metric: _sec_annual_values(raw, concepts)
        for metric, concepts in SEC_CONCEPTS.items()
    }
    years = sorted({year for values in metric_values.values() for year in values}, reverse=True)
    periods = []
    for year in years:
        period: dict[str, Any] = {"year": year}
        for metric, values in metric_values.items():
            if year in values:
                period[metric] = values[year]
        _add_free_cash_flow(period)
        periods.append(period)

    return {
        "ticker": ticker.upper(),
        "market": market,
        "source": "sec_companyfacts",
        "company_name": raw.get("entityName"),
        "cik": raw.get("cik"),
        "generated_at": now_kst_iso(),
        "periods": periods,
    }


def _matches_any(account_name: str, patterns: list[str]) -> bool:
    compact = account_name.replace(" ", "")
    return any(pattern.replace(" ", "") in compact for pattern in patterns)


def normalize_dart_financials(raw: dict[str, Any], ticker: str, market: str = "KR") -> dict[str, Any]:
    grouped: dict[int, dict[str, Any]] = defaultdict(dict)
    for item in raw.get("list", []):
        year = parse_amount(item.get("bsns_year"))
        amount = parse_amount(item.get("thstrm_amount"))
        account_name = str(item.get("account_nm", ""))
        if year is None or amount is None:
            continue
        period = grouped[int(year)]
        period["year"] = int(year)
        for metric, patterns in DART_PATTERNS.items():
            if metric not in period and _matches_any(account_name, patterns):
                period[metric] = amount
    periods = []
    for year in sorted(grouped, reverse=True):
        period = grouped[year]
        _add_free_cash_flow(period)
        periods.append(period)

    return {
        "ticker": ticker.upper(),
        "market": market,
        "source": "dart_fnltt",
        "generated_at": now_kst_iso(),
        "status": raw.get("status"),
        "message": raw.get("message"),
        "periods": periods,
    }


def normalized_output_path(
    ticker: str,
    source: str,
    output_dir: str | Path,
    date_text: str | None = None,
) -> Path:
    symbol = safe_symbol(ticker)
    if date_text:
        return Path(output_dir) / f"{symbol}_{date_text}_{source}_normalized.json"
    return Path(output_dir) / f"{symbol}_{source}_normalized.json"


def normalize_file(
    source: str,
    ticker: str,
    input_path: str | Path,
    output_dir: str | Path,
    dated: bool = False,
) -> Path:
    raw = read_json(input_path)
    if source == "sec":
        result = normalize_sec_companyfacts(raw, ticker)
    elif source == "dart":
        result = normalize_dart_financials(raw, ticker)
    else:
        raise ValueError(f"unknown source: {source}")
    output = normalized_output_path(
        ticker,
        source,
        output_dir,
        now_kst_date() if dated else None,
    )
    return write_json(output, result)


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize raw financial statement data.")
    parser.add_argument("--source", choices=["sec", "dart"], required=True)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", default="data/normalized")
    parser.add_argument(
        "--dated",
        action="store_true",
        help="Write date-stamped normalized output for reproducible bundles.",
    )
    args = parser.parse_args()
    output = normalize_file(
        args.source,
        args.ticker,
        args.input,
        args.output_dir,
        dated=args.dated,
    )
    print(output)


if __name__ == "__main__":
    main()
