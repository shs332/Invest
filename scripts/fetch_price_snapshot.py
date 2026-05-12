from __future__ import annotations

import argparse
import csv
from io import StringIO
import urllib.parse
from pathlib import Path

try:
    from scripts.invest_utils import http_bytes, http_json, now_kst_date, pct_change, safe_symbol, write_json
except ModuleNotFoundError:
    from invest_utils import http_bytes, http_json, now_kst_date, pct_change, safe_symbol, write_json


YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
STOOQ_QUOTE_URL = "https://stooq.com/q/l/"
NASDAQ_QUOTE_URL = "https://api.nasdaq.com/api/quote/{symbol}/info?assetclass=stocks"
NASDAQ_HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}


def yahoo_symbol_to_stooq(symbol: str) -> str:
    normalized = symbol.strip().lower()
    if "." in normalized:
        return normalized
    return f"{normalized}.us"


def _parse_number(value) -> float | None:
    if value in (None, "", "N/A", "NA"):
        return None
    cleaned = str(value).replace("$", "").replace(",", "").replace("%", "").strip()
    if not cleaned:
        return None
    return float(cleaned)


def _parse_int(value) -> int | None:
    number = _parse_number(value)
    return int(number) if number is not None else None


def summarize_stooq_csv(csv_text: str, symbol: str) -> dict:
    rows = list(csv.DictReader(StringIO(csv_text)))
    if not rows or "Close" not in rows[0]:
        raise RuntimeError("stooq returned no price rows")

    closes = [float(row["Close"]) for row in rows if row.get("Close") not in (None, "", "N/A")]
    volumes = [int(float(row["Volume"])) for row in rows if row.get("Volume") not in (None, "", "N/A")]
    if not closes:
        raise RuntimeError("stooq returned no close prices")

    latest = closes[-1]
    first = closes[0]
    return {
        "symbol": symbol.upper(),
        "source": "stooq_csv",
        "currency": None,
        "exchange": "stooq",
        "regular_market_price": latest,
        "latest_close": latest,
        "period_return_pct": pct_change(first, latest),
        "max_close": max(closes),
        "min_close": min(closes),
        "latest_volume": volumes[-1] if volumes else None,
        "points": len(closes),
    }


def summarize_stooq_quote_csv(csv_text: str, symbol: str) -> dict:
    rows = list(csv.DictReader(StringIO(csv_text)))
    if not rows or "Close" not in rows[0]:
        raise RuntimeError("stooq quote returned no price rows")
    row = rows[0]
    latest = _parse_number(row.get("Close"))
    if latest is None:
        raise RuntimeError("stooq quote returned no close price")
    return {
        "symbol": symbol.upper(),
        "source": "stooq_quote_csv",
        "currency": None,
        "exchange": "stooq",
        "regular_market_price": latest,
        "latest_close": latest,
        "period_return_pct": None,
        "max_close": _parse_number(row.get("High")),
        "min_close": _parse_number(row.get("Low")),
        "latest_volume": _parse_int(row.get("Volume")),
        "points": 1,
    }


def summarize_nasdaq_quote(raw: dict, symbol: str) -> dict:
    data = raw.get("data") or {}
    primary = data.get("primaryData") or {}
    latest = _parse_number(primary.get("lastSalePrice"))
    if latest is None:
        raise RuntimeError("nasdaq returned no last sale price")
    range_text = ((data.get("keyStats") or {}).get("fiftyTwoWeekHighLow") or {}).get("value")
    low = high = None
    if isinstance(range_text, str) and " - " in range_text:
        low_text, high_text = range_text.split(" - ", 1)
        low = _parse_number(low_text)
        high = _parse_number(high_text)
    return {
        "symbol": symbol.upper(),
        "source": "nasdaq_quote",
        "currency": None,
        "exchange": data.get("exchange"),
        "regular_market_price": latest,
        "latest_close": latest,
        "period_return_pct": None,
        "max_close": high,
        "min_close": low,
        "latest_volume": _parse_int(primary.get("volume")),
        "points": 1,
    }


def summarize_yahoo_chart(raw: dict, symbol: str) -> dict:
    result = raw.get("chart", {}).get("result", [{}])[0]
    meta = result.get("meta", {})
    quote = result.get("indicators", {}).get("quote", [{}])[0]
    closes = [value for value in quote.get("close", []) if value is not None]
    volumes = [value for value in quote.get("volume", []) if value is not None]
    latest = closes[-1] if closes else None
    first = closes[0] if closes else None
    return {
        "symbol": symbol.upper(),
        "source": "yahoo_chart",
        "currency": meta.get("currency"),
        "exchange": meta.get("exchangeName"),
        "regular_market_price": meta.get("regularMarketPrice"),
        "latest_close": latest,
        "period_return_pct": pct_change(first, latest),
        "max_close": max(closes) if closes else None,
        "min_close": min(closes) if closes else None,
        "latest_volume": volumes[-1] if volumes else None,
        "points": len(closes),
    }


def fetch_yahoo_price_snapshot(symbol: str, range_: str = "1y", interval: str = "1d") -> dict:
    encoded = urllib.parse.quote(symbol, safe="")
    url = f"{YAHOO_CHART_URL.format(symbol=encoded)}?range={range_}&interval={interval}"
    raw = http_json(url)
    return {
        "_fetch": {"provider": "yahoo", "source_url": url, "symbol": symbol, "range": range_, "interval": interval},
        "summary": summarize_yahoo_chart(raw, symbol),
        "raw": raw,
    }


def fetch_stooq_price_snapshot(symbol: str, range_: str = "1y", interval: str = "1d") -> dict:
    if interval != "1d":
        raise RuntimeError("stooq provider supports interval=1d only")
    stooq_symbol = yahoo_symbol_to_stooq(symbol)
    params = {"s": stooq_symbol, "f": "sd2t2ohlcv", "h": "", "e": "csv"}
    url = f"{STOOQ_QUOTE_URL}?{urllib.parse.urlencode(params)}"
    csv_text = http_bytes(url).decode("utf-8")
    return {
        "_fetch": {
            "provider": "stooq",
            "source_url": url,
            "symbol": symbol,
            "stooq_symbol": stooq_symbol,
            "range": range_,
            "interval": interval,
        },
        "summary": summarize_stooq_quote_csv(csv_text, symbol),
        "raw": csv_text,
    }


def fetch_nasdaq_price_snapshot(symbol: str, range_: str = "1y", interval: str = "1d") -> dict:
    if "." in symbol:
        raise RuntimeError("nasdaq provider supports plain US tickers only")
    url = NASDAQ_QUOTE_URL.format(symbol=urllib.parse.quote(symbol.upper(), safe=""))
    raw = http_json(url, headers=NASDAQ_HEADERS)
    return {
        "_fetch": {"provider": "nasdaq", "source_url": url, "symbol": symbol, "range": range_, "interval": interval},
        "summary": summarize_nasdaq_quote(raw, symbol),
        "raw": raw,
    }


def fetch_price_snapshot(
    symbol: str,
    range_: str = "1y",
    interval: str = "1d",
    providers: list[str] | None = None,
    stooq_fetcher=fetch_stooq_price_snapshot,
    nasdaq_fetcher=fetch_nasdaq_price_snapshot,
    yahoo_fetcher=fetch_yahoo_price_snapshot,
) -> dict:
    selected = providers or ["stooq", "nasdaq", "yahoo"]
    attempts = []
    fetchers = {"stooq": stooq_fetcher, "nasdaq": nasdaq_fetcher, "yahoo": yahoo_fetcher}
    for provider in selected:
        fetcher = fetchers.get(provider)
        if fetcher is None:
            raise ValueError(f"unknown price provider: {provider}")
        try:
            data = fetcher(symbol, range_, interval)
        except Exception as exc:
            attempts.append({"provider": provider, "error": str(exc)})
            continue
        data.setdefault("_fetch", {})
        data["_fetch"]["attempts"] = attempts + [{"provider": provider, "status": "ok"}]
        return data
    raise RuntimeError(f"all price providers failed: {attempts}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch a price snapshot with provider fallback.")
    parser.add_argument("symbol", help="Ticker symbol, e.g. AAPL or 005930.KS.")
    parser.add_argument("--range", default="1y")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--providers", default="stooq,nasdaq,yahoo", help="Comma-separated provider order: stooq,nasdaq,yahoo")
    parser.add_argument("--out-dir", default="data/raw/prices")
    args = parser.parse_args()
    providers = [provider.strip() for provider in args.providers.split(",") if provider.strip()]
    data = fetch_price_snapshot(args.symbol, args.range, args.interval, providers=providers)
    output = Path(args.out_dir) / f"{safe_symbol(args.symbol)}_{now_kst_date()}_price.json"
    print(write_json(output, data))


if __name__ == "__main__":
    main()
