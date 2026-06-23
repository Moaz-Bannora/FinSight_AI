"""Regression checks for Yahoo market-data query detection."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.market_data import detect_symbol, run_detected_market_data_tool


def test_detects_cash_ticker() -> None:
    assert detect_symbol("Give me the latest quote for $AAPL") == "AAPL"


def test_detects_company_alias() -> None:
    assert detect_symbol("What is the current Apple stock price?") == "AAPL"


def test_ignores_finance_acronym_as_ticker() -> None:
    assert detect_symbol("Explain NPV and WACC") is None


def test_market_tool_waits_for_market_intent() -> None:
    assert run_detected_market_data_tool("Explain AAPL from the uploaded annual report") is None


if __name__ == "__main__":
    test_detects_cash_ticker()
    test_detects_company_alias()
    test_ignores_finance_acronym_as_ticker()
    test_market_tool_waits_for_market_intent()
    print("market data tests passed")
