from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent


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


def update_company_bundle(
    ticker: str,
    market: str = "US",
    price_range: str = "1y",
    price_interval: str = "1d",
) -> Path:
    if market.upper() != "US":
        raise SystemExit("update_company_bundle currently supports US/SEC only.")

    raw_path = run_command([
        sys.executable,
        str(SCRIPT_DIR / "fetch_sec_companyfacts.py"),
        ticker,
    ])
    normalized_path = run_command([
        sys.executable,
        str(SCRIPT_DIR / "normalize_financials.py"),
        "--source",
        "sec",
        "--ticker",
        ticker,
        "--input",
        raw_path,
    ])
    try:
        price_path = run_command([
            sys.executable,
            str(SCRIPT_DIR / "fetch_price_snapshot.py"),
            ticker,
            "--range",
            price_range,
            "--interval",
            price_interval,
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
    parser = argparse.ArgumentParser(description="Fetch, normalize, price, and bundle a US company analysis snapshot.")
    parser.add_argument("ticker", help="US company ticker symbol, e.g. AAPL.")
    parser.add_argument("--market", choices=["US"], default="US")
    parser.add_argument("--price-range", default="1y")
    parser.add_argument("--price-interval", default="1d")
    args = parser.parse_args()
    print(update_company_bundle(args.ticker, args.market, args.price_range, args.price_interval))


if __name__ == "__main__":
    main()
