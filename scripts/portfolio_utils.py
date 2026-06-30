from __future__ import annotations

from pathlib import Path
from typing import Any


def _strip_comment(line: str) -> str:
    quote: str | None = None
    for index, char in enumerate(line):
        if char in {"'", '"'}:
            quote = None if quote == char else char if quote is None else quote
        if char == "#" and quote is None and (index == 0 or line[index - 1].isspace()):
            return line[:index]
    return line


def _parse_scalar(value: str) -> Any:
    text = value.strip()
    if text == "[]":
        return []
    if text in {"{}", ""}:
        return {}
    if text.lower() in {"true", "false"}:
        return text.lower() == "true"
    if text.lower() in {"null", "none"}:
        return None
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        return text[1:-1]
    if text.startswith("0") and len(text) > 1 and text.replace(".", "", 1).isdigit():
        return text
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text


def _split_key_value(text: str) -> tuple[str, str]:
    if ":" not in text:
        raise ValueError(f"invalid yaml line: {text}")
    key, value = text.split(":", 1)
    return key.strip(), value.strip()


def _prepare_lines(path: Path) -> list[tuple[int, str]]:
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        cleaned = _strip_comment(raw).rstrip()
        if not cleaned.strip():
            continue
        lines.append((len(cleaned) - len(cleaned.lstrip(" ")), cleaned.strip()))
    return lines


def _parse_mapping(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    while index < len(lines):
        line_indent, text = lines[index]
        if line_indent < indent:
            break
        if line_indent > indent:
            break
        if text.startswith("- "):
            break
        key, value = _split_key_value(text)
        index += 1
        if value:
            result[key] = _parse_scalar(value)
            continue
        if index < len(lines) and lines[index][0] > line_indent:
            result[key], index = _parse_block(lines, index, lines[index][0])
        else:
            result[key] = {}
    return result, index


def _parse_list(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[list[Any], int]:
    result: list[Any] = []
    while index < len(lines):
        line_indent, text = lines[index]
        if line_indent < indent:
            break
        if line_indent != indent or not text.startswith("- "):
            break
        rest = text[2:].strip()
        index += 1
        if not rest:
            if index < len(lines) and lines[index][0] > line_indent:
                item, index = _parse_block(lines, index, lines[index][0])
            else:
                item = None
            result.append(item)
            continue
        if ":" in rest:
            key, value = _split_key_value(rest)
            item: dict[str, Any] = {}
            if value:
                item[key] = _parse_scalar(value)
            elif index < len(lines) and lines[index][0] > line_indent:
                item[key], index = _parse_block(lines, index, lines[index][0])
            else:
                item[key] = {}
            if index < len(lines) and lines[index][0] > line_indent:
                extra, index = _parse_mapping(lines, index, lines[index][0])
                item.update(extra)
            result.append(item)
            continue
        result.append(_parse_scalar(rest))
    return result, index


def _parse_block(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[Any, int]:
    if index >= len(lines):
        return {}, index
    text = lines[index][1]
    if text.startswith("- "):
        return _parse_list(lines, index, indent)
    return _parse_mapping(lines, index, indent)


def read_simple_yaml(path: str | Path) -> Any:
    yaml_path = Path(path)
    stripped = "\n".join(
        _strip_comment(line).strip()
        for line in yaml_path.read_text(encoding="utf-8").splitlines()
        if _strip_comment(line).strip()
    )
    if not stripped:
        return {}
    if stripped == "[]":
        return []
    lines = _prepare_lines(yaml_path)
    if not lines:
        return {}
    parsed, _ = _parse_block(lines, 0, lines[0][0])
    return parsed


def load_portfolio_context(root: str | Path = ".") -> dict[str, Any]:
    base = Path(root)
    companies = base / "companies"
    return {
        "profile": read_simple_yaml(companies / "portfolio_profile.yaml"),
        "holdings": read_simple_yaml(companies / "holdings.yaml"),
        "watchlist": read_simple_yaml(companies / "watchlist.yaml"),
        "paths": {
            "profile": str(companies / "portfolio_profile.yaml"),
            "holdings": str(companies / "holdings.yaml"),
            "watchlist": str(companies / "watchlist.yaml"),
        },
    }


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def find_security(context: dict[str, Any], query: str, ticker: str | None = None) -> dict[str, Any] | None:
    wanted = normalize_symbol(ticker) if ticker else None
    query_upper = query.upper()
    query_lower = query.casefold()
    for source_name in ("holdings", "watchlist"):
        for item in context.get(source_name, []) or []:
            item_ticker = normalize_symbol(str(item.get("ticker", "")))
            item_name = str(item.get("name", "")).casefold()
            if wanted and item_ticker == wanted:
                return dict(item, source=source_name[:-1] if source_name.endswith("s") else source_name)
            if item_ticker and item_ticker in query_upper:
                return dict(item, source=source_name[:-1] if source_name.endswith("s") else source_name)
            if item_name and item_name in query_lower:
                return dict(item, source=source_name[:-1] if source_name.endswith("s") else source_name)
    return None


def is_price_move_question(query: str) -> bool:
    lowered = query.casefold()
    keywords = [
        "왜",
        "올랐",
        "오른",
        "상승",
        "떨어",
        "하락",
        "급등",
        "급락",
        "뉴스",
        "무슨 일",
        "price move",
        "why",
        "news",
    ]
    return any(keyword in lowered for keyword in keywords)


def is_return_seeking_question(query: str) -> bool:
    lowered = query.casefold()
    keywords = [
        "upside",
        "growth",
        "momentum",
        "alpha",
        "aggressive",
        "rerating",
        "catalyst",
        "성장",
        "모멘텀",
        "수익률",
        "공격",
        "고수익",
        "상승여력",
        "알파",
    ]
    return any(keyword in lowered for keyword in keywords)
