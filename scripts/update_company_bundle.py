from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent


def source_for_market(market: str) -> str:
    normalized = market.upper()
    if normalized == "US":
        return "sec"
    if normalized == "KR":
        return "dart"
    raise ValueError(f"unknown market: {market}")


def price_mode_default(history: bool) -> str:
    return "history" if history else "quote"


def _command_text(args: list[str]) -> str:
    return " ".join(args)


def run_command(args: list[str], cwd: Path = REPO_ROOT) -> str:
    try:
        completed = subprocess.run(args, check=True, text=True, capture_output=True, cwd=cwd)
    except subprocess.CalledProcessError as exc:
        stdout_lines = [line for line in (exc.stdout or "").splitlines() if line.strip()]
        details = [
            f"command failed: {_command_text(args)}",
            f"exit code: {exc.returncode}",
        ]
        if exc.stderr:
            details.append(f"stderr: {exc.stderr.strip()}")
        if stdout_lines:
            details.append(f"stdout tail: {stdout_lines[-1]}")
        raise RuntimeError("\n".join(details)) from exc

    stdout_lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not stdout_lines:
        raise RuntimeError(f"command produced no output: {_command_text(args)}")
    return stdout_lines[-1]


def update_company_bundle(ticker: str, market: str, stale_days: int, price_history: bool) -> Path:
    source = source_for_market(market)
    if source != "sec":
        raise SystemExit("KR/DART orchestration needs OPENDART_API_KEY and should be enabled after DART E2E is verified.")

    raw_path = run_command([
        sys.executable,
        str(SCRIPT_DIR / "fetch_sec_companyfacts.py"),
        ticker,
        "--stale-days",
        str(stale_days),
    ])
    normalized_path = run_command([
        sys.executable,
        str(SCRIPT_DIR / "normalize_financials.py"),
        "--source",
        source,
        "--ticker",
        ticker,
        "--input",
        raw_path,
        "--dated",
    ])
    try:
        price_path = run_command([
            sys.executable,
            str(SCRIPT_DIR / "fetch_price_snapshot.py"),
            ticker,
            "--mode",
            price_mode_default(price_history),
        ])
    except RuntimeError as exc:
        print(f"Price fetch failed: {exc}", file=sys.stderr)
        price_path = None

    bundle_args = [
        sys.executable,
        str(SCRIPT_DIR / "build_analysis_bundle.py"),
        ticker,
        "--financials",
        normalized_path,
    ]
    if price_path:
        bundle_args.extend(["--price", price_path])
    bundle_path = run_command(bundle_args)
    return Path(bundle_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch, normalize, price, and bundle a company analysis snapshot.")
    parser.add_argument("ticker", help="Company ticker symbol, e.g. AAPL.")
    parser.add_argument("--market", choices=["US", "KR"], default="US", help="Listing market. US is enabled; KR stops until DART E2E is verified.")
    parser.add_argument("--stale-days", type=int, default=7, help="Reuse SEC raw data when latest local file is this fresh.")
    parser.add_argument("--price-history", action="store_true", help="Fetch price history instead of latest quote.")
    args = parser.parse_args()
    print(update_company_bundle(args.ticker, args.market, args.stale_days, args.price_history))


if __name__ == "__main__":
    main()
