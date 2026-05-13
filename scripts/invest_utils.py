from __future__ import annotations

import json
import os
import re
import zipfile
import gzip
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


KST = ZoneInfo("Asia/Seoul")
ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def now_kst_date() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def now_kst_iso() -> str:
    return datetime.now(KST).isoformat(timespec="seconds")


def safe_symbol(symbol: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", symbol.strip())


def _strip_env_comment(value: str) -> str:
    quote: str | None = None
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char in {"'", '"'}:
            quote = None if quote == char else char if quote is None else quote
            continue
        if char == "#" and quote is None and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
    return value.strip()


def _parse_env_value(value: str) -> str:
    stripped = _strip_env_comment(value)
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {"'", '"'}:
        quote = stripped[0]
        stripped = stripped[1:-1]
        if quote == '"':
            return (
                stripped
                .replace(r"\n", "\n")
                .replace(r"\r", "\r")
                .replace(r"\t", "\t")
                .replace(r'\"', '"')
                .replace(r"\\", "\\")
            )
    return stripped


def load_project_env(path: str | Path | None = None, override: bool = False) -> dict[str, str]:
    env_path = Path(path) if path is not None else PROJECT_ROOT / ".env"
    if not env_path.exists():
        return {}

    loaded: dict[str, str] = {}
    for line_number, raw_line in enumerate(env_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        if "=" not in line:
            raise ValueError(f"invalid env line {line_number} in {env_path}: missing '='")
        name, value = line.split("=", 1)
        name = name.strip()
        if not ENV_NAME_RE.match(name):
            raise ValueError(f"invalid env name on line {line_number} in {env_path}: {name}")
        if override or name not in os.environ:
            parsed = _parse_env_value(value)
            os.environ[name] = parsed
            loaded[name] = parsed
    return loaded


def read_json(path: str | Path) -> Any:
    input_path = Path(path)
    opener = gzip.open if input_path.suffix == ".gz" else open
    with opener(input_path, "rt", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str | Path, data: Any, compact: bool = False) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if output.suffix == ".gz" else open
    kwargs = {"ensure_ascii": False, "sort_keys": True}
    if compact:
        kwargs["separators"] = (",", ":")
    else:
        kwargs["indent"] = 2
    with opener(output, "wt", encoding="utf-8") as f:
        json.dump(data, f, **kwargs)
        f.write("\n")
    return output


def latest_matching(pattern: str, root: str | Path = ".") -> Path | None:
    matches = sorted(Path(root).glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def http_json(url: str, headers: dict[str, str] | None = None, timeout: int = 30) -> Any:
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            if response.headers.get("Content-Encoding") == "gzip" or body.startswith(b"\x1f\x8b"):
                body = gzip.decompress(body)
            return json.loads(body.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {url}: {body[:500]}") from exc


def http_bytes(url: str, headers: dict[str, str] | None = None, timeout: int = 30) -> bytes:
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            if response.headers.get("Content-Encoding") == "gzip" or body.startswith(b"\x1f\x8b"):
                return gzip.decompress(body)
            return body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {url}: {body[:500]}") from exc


def read_zip_text(zip_bytes: bytes, suffix: str) -> str:
    from io import BytesIO

    with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
        for name in archive.namelist():
            if name.lower().endswith(suffix.lower()):
                return archive.read(name).decode("utf-8")
    raise ValueError(f"zip member not found: *{suffix}")


def parse_amount(value: Any) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    if not text or text in {"-", "nan", "NaN"}:
        return None
    negative = text.startswith("(") and text.endswith(")")
    cleaned = text.strip("()").replace(",", "").replace(" ", "")
    try:
        number: int | float
        if "." in cleaned:
            number = float(cleaned)
        else:
            number = int(cleaned)
    except ValueError:
        return None
    return -number if negative else number


def pct_change(first: float | int | None, last: float | int | None) -> float | None:
    if first in (None, 0) or last is None:
        return None
    return round((float(last) / float(first) - 1.0) * 100.0, 2)
