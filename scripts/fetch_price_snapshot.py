from __future__ import annotations

import argparse
from pathlib import Path

try:
    from scripts.invest_utils import now_kst_date, pct_change, safe_symbol, write_json
except ModuleNotFoundError:
    from invest_utils import now_kst_date, pct_change, safe_symbol, write_json


# Historical note (2026-07-21): this module used to scrape stooq, nasdaq, and yahoo
# directly via urllib with a provider-fallback chain. All three had real problems:
# stooq's quote endpoint (/q/l/) is deprecated (404) and its historical endpoint is
# gated behind a JS proof-of-work bot check no plain HTTP client can pass; nasdaq's
# endpoint only ever returns a single quote point, so it could never satisfy a
# history-requiring range; yahoo's raw chart endpoint intermittently 429s in a way
# that survived matching curl's headers exactly, consistent with TLS/HTTP client
# fingerprinting rather than a fixable header issue. yfinance (which wraps the same
# Yahoo data via curl_cffi, maintained against Yahoo's anti-bot changes by its
# community) replaced all three as the sole provider. Free API-key alternatives were
# evaluated and rejected: Alpha Vantage free tier is 25 requests/day, Twelve Data
# gates Korea Exchange (KRX) behind its paid Pro plan (this repo holds KRX tickers),
# and Finnhub's free tier returns 403 on historical candles entirely.
YFINANCE_MAX_RETRIES = 3
YFINANCE_RETRY_BACKOFF_SECONDS = 1.5


def _parse_number(value) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:  # NaN check without importing math
        return None
    return number


def summarize_yfinance_history(history, fast_info: dict, symbol: str) -> dict:
    if history is None or history.empty:
        raise RuntimeError(f"yfinance returned no price rows for {symbol}")

    closes = [value for value in history["Close"].tolist() if value == value]  # drop NaN
    volumes = [int(value) for value in history.get("Volume", []).tolist() if value == value]
    if not closes:
        raise RuntimeError(f"yfinance returned no usable close prices for {symbol}")

    latest = closes[-1]
    first = closes[0]
    return {
        "symbol": symbol.upper(),
        "source": "yfinance",
        "currency": fast_info.get("currency"),
        "exchange": fast_info.get("exchange"),
        "regular_market_price": _parse_number(fast_info.get("lastPrice")) or latest,
        "latest_close": latest,
        "period_return_pct": pct_change(first, latest),
        "max_close": max(closes),
        "min_close": min(closes),
        "latest_volume": volumes[-1] if volumes else None,
        "points": len(closes),
        "history_available": len(closes) > 1,
        "history_points": len(closes),
        "market_cap": _parse_number(fast_info.get("marketCap")),
        "year_high": _parse_number(fast_info.get("yearHigh")),
        "year_low": _parse_number(fast_info.get("yearLow")),
    }


def _normalize_period(range_: str) -> str:
    normalized = range_.strip().lower()
    if normalized in {"", "latest", "quote"}:
        return "5d"  # yfinance has no true single-quote period; shortest usable window
    return normalized


def fetch_yfinance_price_snapshot(
    symbol: str, range_: str = "1y", interval: str = "1d", sleep=None, ticker_factory=None
) -> dict:
    import time as _time

    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError(
            "yfinance is not installed. Run `uv sync` (or `pip install yfinance`) to install it."
        ) from exc

    sleep = sleep or _time.sleep
    period = _normalize_period(range_)
    make_ticker = ticker_factory or yf.Ticker

    last_error: Exception | None = None
    for attempt in range(YFINANCE_MAX_RETRIES):
        try:
            ticker = make_ticker(symbol)
            history = ticker.history(period=period, interval=interval)
            fast_info = dict(ticker.fast_info) if history is not None and not history.empty else {}
            summary = summarize_yfinance_history(history, fast_info, symbol)
            return {
                "_fetch": {
                    "provider": "yfinance",
                    "symbol": symbol,
                    "range": range_,
                    "period_used": period,
                    "interval": interval,
                    "attempts": attempt + 1,
                },
                "summary": summary,
            }
        except Exception as exc:  # yfinance raises varied exception types (requests, curl_cffi, etc.)
            last_error = exc
            if attempt == YFINANCE_MAX_RETRIES - 1:
                break
            sleep(YFINANCE_RETRY_BACKOFF_SECONDS * (attempt + 1))
    raise RuntimeError(f"yfinance fetch failed for {symbol} after {YFINANCE_MAX_RETRIES} attempts: {last_error}")


def fetch_price_snapshot(
    symbol: str,
    range_: str = "1y",
    interval: str = "1d",
    providers: list[str] | None = None,
    yfinance_fetcher=fetch_yfinance_price_snapshot,
) -> dict:
    selected = providers or ["yfinance"]
    attempts = []
    fetchers = {"yfinance": yfinance_fetcher}
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
    parser = argparse.ArgumentParser(description="Fetch a price snapshot (yfinance-backed).")
    parser.add_argument("symbol", help="Ticker symbol, e.g. AAPL or 005930.KS.")
    parser.add_argument("--range", default="1y")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--providers", default="yfinance", help="Comma-separated provider order (currently: yfinance)")
    parser.add_argument("--out-dir", default="data/raw/prices")
    args = parser.parse_args()
    providers = [provider.strip() for provider in args.providers.split(",") if provider.strip()]
    try:
        data = fetch_price_snapshot(args.symbol, args.range, args.interval, providers=providers)
    except RuntimeError as exc:
        raise SystemExit(str(exc))
    output = Path(args.out_dir) / f"{safe_symbol(args.symbol)}_{now_kst_date()}_price.json"
    print(write_json(output, data))


if __name__ == "__main__":
    main()
