"""Read-only Yahoo Finance market data tools.

The production app treats live market data as an external evidence source, not
as investment advice. This module is intentionally small and MCP-ready: the
public function accepts a natural-language query, detects a likely ticker, and
returns a structured tool result that can later be exposed through an MCP server.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from .tools import ToolResult

try:
    import yfinance as yf

    YFINANCE_AVAILABLE = True
except Exception:
    yf = None
    YFINANCE_AVAILABLE = False


CACHE_TTL_SECONDS = int(os.getenv("FIN_DOC_LLM_MARKET_CACHE_TTL_SECONDS", "300"))

MARKET_INTENT_KEYWORDS = [
    "stock price",
    "share price",
    "latest price",
    "current price",
    "quote",
    "market cap",
    "pe ratio",
    "p/e",
    "beta",
    "dividend",
    "52-week",
    "52 week",
    "yahoo",
    "ticker",
    "live market",
    "market data",
]

COMPANY_ALIASES = {
    "apple": "AAPL",
    "microsoft": "MSFT",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "amazon": "AMZN",
    "tesla": "TSLA",
    "nvidia": "NVDA",
    "meta": "META",
    "facebook": "META",
    "netflix": "NFLX",
    "berkshire": "BRK-B",
}

TICKER_STOPWORDS = {
    "AI",
    "API",
    "APR",
    "ATM",
    "CAPM",
    "CEO",
    "CFO",
    "CSV",
    "DCF",
    "DOC",
    "DOCX",
    "EPS",
    "ETF",
    "GDP",
    "IRR",
    "LLM",
    "MCP",
    "NPV",
    "OCR",
    "PDF",
    "PE",
    "PEG",
    "QA",
    "QOQ",
    "RAG",
    "ROA",
    "ROE",
    "ROI",
    "SEC",
    "USD",
    "VAR",
    "WACC",
    "YOY",
}

_CACHE: dict[str, tuple[datetime, ToolResult]] = {}


def run_detected_market_data_tool(query: str) -> ToolResult | None:
    """Return a Yahoo Finance snapshot when the query clearly asks for market data."""

    if not _has_market_intent(query):
        return None

    symbol = detect_symbol(query)
    if not symbol:
        return _unavailable_result(
            symbol="unknown",
            status="ticker_missing",
            message="Market data was requested, but no clear ticker symbol was detected.",
        )

    return fetch_yahoo_snapshot(symbol)


def detect_symbol(query: str) -> str | None:
    """Detect a likely Yahoo Finance ticker from a user query."""

    lowered = query.lower()
    for alias, symbol in COMPANY_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", lowered):
            return symbol

    cash_ticker = re.search(r"\$([A-Za-z]{1,5}(?:[-.][A-Za-z]{1,2})?)\b", query)
    if cash_ticker:
        return _normalize_symbol(cash_ticker.group(1))

    labeled_ticker = re.search(
        r"\b(?:ticker|symbol|quote)\s+([A-Za-z]{1,5}(?:[-.][A-Za-z]{1,2})?)\b",
        query,
        flags=re.IGNORECASE,
    )
    if labeled_ticker:
        return _normalize_symbol(labeled_ticker.group(1))

    candidates = re.findall(r"\b[A-Z]{1,5}(?:[-.][A-Z]{1,2})?\b", query)
    for candidate in candidates:
        normalized = _normalize_symbol(candidate)
        if normalized not in TICKER_STOPWORDS:
            return normalized

    return None


def fetch_yahoo_snapshot(symbol: str) -> ToolResult:
    """Fetch a compact Yahoo Finance snapshot with caching and clear provenance."""

    normalized = _normalize_symbol(symbol)
    now = datetime.now(timezone.utc)
    cached = _CACHE.get(normalized)
    if cached and now - cached[0] < timedelta(seconds=CACHE_TTL_SECONDS):
        return cached[1]

    if not YFINANCE_AVAILABLE:
        return _unavailable_result(
            normalized,
            "package_unavailable",
            "The yfinance package is not installed, so live Yahoo Finance data cannot be loaded.",
        )

    try:
        ticker = yf.Ticker(normalized)
        fast_info = _safe_mapping(getattr(ticker, "fast_info", {}) or {})
        info = _safe_mapping(ticker.get_info() or {})
    except Exception as exc:
        return _unavailable_result(
            normalized,
            "fetch_failed",
            f"Yahoo Finance data could not be loaded for {normalized}: {str(exc)[:160]}",
        )

    price = _first_number(
        fast_info,
        ["last_price", "lastPrice", "regular_market_price", "regularMarketPrice"],
    )
    previous_close = _first_number(
        fast_info,
        ["previous_close", "previousClose", "regular_market_previous_close", "regularMarketPreviousClose"],
    )
    change_pct = _pct_change(price, previous_close)
    market_cap = _first_number(fast_info, ["market_cap", "marketCap"]) or _as_float(info.get("marketCap"))
    currency = fast_info.get("currency") or info.get("currency") or ""
    short_name = info.get("shortName") or info.get("longName") or normalized

    details: dict[str, Any] = {
        "symbol": normalized,
        "name": short_name,
        "currency": currency,
        "previous_close": _round_or_none(previous_close),
        "day_change_pct": _round_or_none(change_pct),
        "market_cap": _round_or_none(market_cap),
        "trailing_pe": _round_or_none(_as_float(info.get("trailingPE"))),
        "forward_pe": _round_or_none(_as_float(info.get("forwardPE"))),
        "dividend_yield": _round_or_none(_as_float(info.get("dividendYield"))),
        "beta": _round_or_none(_as_float(info.get("beta"))),
        "fifty_two_week_low": _round_or_none(_first_number(fast_info, ["year_low", "yearLow"])),
        "fifty_two_week_high": _round_or_none(_first_number(fast_info, ["year_high", "yearHigh"])),
        "cache_ttl_seconds": CACHE_TTL_SECONDS,
    }
    interpretation = _interpret_snapshot(normalized, price, previous_close, change_pct, currency)
    result = ToolResult(
        tool_name="Yahoo Finance Market Snapshot",
        formula="Read-only Yahoo Finance quote and fundamentals lookup",
        inputs={"symbol": normalized},
        result=float(price or 0.0),
        interpretation=interpretation,
        benchmark=(
            "External market data can be delayed, incomplete, or unavailable. "
            "Use it for context, not as a buy/sell recommendation."
        ),
        details=details,
        source="Yahoo Finance via yfinance",
        timestamp=now.isoformat(timespec="seconds"),
    )
    _CACHE[normalized] = (now, result)
    return result


def _has_market_intent(query: str) -> bool:
    lowered = query.lower()
    if any(keyword in lowered for keyword in MARKET_INTENT_KEYWORDS):
        return True
    has_upper_ticker = bool(re.search(r"\b[A-Z]{2,5}(?:[-.][A-Z]{1,2})?\b", query))
    return has_upper_ticker and any(word in lowered for word in ["analyze", "valuation", "price", "stock", "share"])


def _normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper().replace(".", "-")


def _safe_mapping(value: Any) -> dict[str, Any]:
    try:
        return dict(value)
    except Exception:
        return {}


def _first_number(mapping: dict[str, Any], keys: list[str]) -> float | None:
    for key in keys:
        value = _as_float(mapping.get(key))
        if value is not None:
            return value
    return None


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pct_change(price: float | None, previous_close: float | None) -> float | None:
    if price is None or previous_close in {None, 0}:
        return None
    return ((price - previous_close) / previous_close) * 100


def _round_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 4)


def _interpret_snapshot(
    symbol: str,
    price: float | None,
    previous_close: float | None,
    change_pct: float | None,
    currency: str,
) -> str:
    if price is None:
        return f"Yahoo Finance returned metadata for {symbol}, but no current price was available."
    price_text = f"{price:,.2f} {currency}".strip()
    if previous_close is None or change_pct is None:
        return f"{symbol} last traded around {price_text}. Previous-close comparison was unavailable."
    direction = "up" if change_pct >= 0 else "down"
    return f"{symbol} last traded around {price_text}, {direction} {abs(change_pct):.2f}% versus the previous close."


def _unavailable_result(symbol: str, status: str, message: str) -> ToolResult:
    return ToolResult(
        tool_name="Yahoo Finance Market Snapshot",
        formula="Read-only Yahoo Finance quote and fundamentals lookup",
        inputs={"symbol": symbol},
        result=0.0,
        interpretation=message,
        benchmark="Live market data unavailable. Continue with document analysis or configure the market data dependency.",
        details={"status": status},
        source="Yahoo Finance via yfinance",
        timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
