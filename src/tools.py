"""Deterministic finance tools and tool routing."""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass
from typing import Any, Callable


@dataclass
class ToolResult:
    tool_name: str
    formula: str
    inputs: dict[str, Any]
    result: float
    interpretation: str
    benchmark: str

    def to_markdown(self) -> str:
        result = f"{self.result:,.4f}".rstrip("0").rstrip(".")
        formula = self._latex_formula()
        return (
            f"**{self.tool_name}**\n\n"
            f"- Formula: ${formula}$\n"
            f"- Inputs: `{json.dumps(self.inputs)}`\n"
            f"- Result: `{result}`\n"
            f"- Interpretation: {self.interpretation}\n"
            f"- Benchmark: {self.benchmark}"
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def _latex_formula(self) -> str:
        formulas = {
            "Current Assets / Current Liabilities": r"\frac{\text{Current Assets}}{\text{Current Liabilities}}",
            "Total Debt / Total Equity": r"\frac{\text{Total Debt}}{\text{Total Equity}}",
            "(Revenue - Cost of Goods Sold) / Revenue * 100": r"\frac{\text{Revenue} - \text{COGS}}{\text{Revenue}} \times 100",
            "Net Income / Revenue * 100": r"\frac{\text{Net Income}}{\text{Revenue}} \times 100",
            "Net Income / Shareholder Equity * 100": r"\frac{\text{Net Income}}{\text{Shareholder Equity}} \times 100",
            "(Gain - Cost) / Cost * 100": r"\frac{\text{Gain} - \text{Cost}}{\text{Cost}} \times 100",
            "sum(Cash Flow_t / (1 + r)^t)": r"\sum_{t=0}^{n}\frac{CF_t}{(1+r)^t}",
        }
        return formulas.get(self.formula, self.formula)


def current_ratio(current_assets: float, current_liabilities: float) -> ToolResult:
    if current_liabilities == 0:
        raise ValueError("Current liabilities cannot be zero.")
    value = current_assets / current_liabilities
    return ToolResult(
        "Current Ratio",
        "Current Assets / Current Liabilities",
        {"current_assets": current_assets, "current_liabilities": current_liabilities},
        value,
        f"The company has {value:.2f} in current assets for every 1.00 of current liabilities.",
        "A value above 1.0 usually means short-term assets exceed short-term obligations; 1.5 to 3.0 is often comfortable, but industry context matters.",
    )


def debt_to_equity(total_debt: float, total_equity: float) -> ToolResult:
    if total_equity == 0:
        raise ValueError("Total equity cannot be zero.")
    value = total_debt / total_equity
    return ToolResult(
        "Debt-to-Equity Ratio",
        "Total Debt / Total Equity",
        {"total_debt": total_debt, "total_equity": total_equity},
        value,
        f"The company has {value:.2f} of debt for every 1.00 of equity.",
        "Lower values usually indicate less leverage. Acceptable levels vary strongly by industry and business model.",
    )


def gross_margin(revenue: float, cost_of_goods_sold: float) -> ToolResult:
    if revenue == 0:
        raise ValueError("Revenue cannot be zero.")
    value = ((revenue - cost_of_goods_sold) / revenue) * 100
    return ToolResult(
        "Gross Margin",
        "(Revenue - Cost of Goods Sold) / Revenue * 100",
        {"revenue": revenue, "cost_of_goods_sold": cost_of_goods_sold},
        value,
        f"{value:.2f}% of revenue remains after direct production or service costs.",
        "Higher gross margin can suggest stronger pricing power or cost control. Compare with peers.",
    )


def net_profit_margin(net_income: float, revenue: float) -> ToolResult:
    if revenue == 0:
        raise ValueError("Revenue cannot be zero.")
    value = (net_income / revenue) * 100
    return ToolResult(
        "Net Profit Margin",
        "Net Income / Revenue * 100",
        {"net_income": net_income, "revenue": revenue},
        value,
        f"{value:.2f}% of revenue becomes profit after all expenses.",
        "Positive and stable net margins are generally healthier, but normal levels vary by industry.",
    )


def return_on_equity(net_income: float, shareholder_equity: float) -> ToolResult:
    if shareholder_equity == 0:
        raise ValueError("Shareholder equity cannot be zero.")
    value = (net_income / shareholder_equity) * 100
    return ToolResult(
        "Return on Equity",
        "Net Income / Shareholder Equity * 100",
        {"net_income": net_income, "shareholder_equity": shareholder_equity},
        value,
        f"The company generated {value:.2f}% return on shareholder equity.",
        "ROE above the cost of equity is generally favorable, but high leverage can inflate ROE.",
    )


def return_on_investment(gain: float, cost: float) -> ToolResult:
    if cost == 0:
        raise ValueError("Investment cost cannot be zero.")
    value = ((gain - cost) / cost) * 100
    return ToolResult(
        "Return on Investment",
        "(Gain - Cost) / Cost * 100",
        {"gain": gain, "cost": cost},
        value,
        f"The investment return is {value:.2f}% relative to its cost.",
        "A positive ROI means gain exceeds cost. Risk, timing, and alternatives still matter.",
    )


def net_present_value(discount_rate: float, cash_flows: list[float]) -> ToolResult:
    if discount_rate < 0:
        raise ValueError("Discount rate cannot be negative.")
    value = sum(cash_flow / ((1 + discount_rate) ** period) for period, cash_flow in enumerate(cash_flows))
    return ToolResult(
        "Net Present Value",
        "sum(Cash Flow_t / (1 + r)^t)",
        {"discount_rate": discount_rate, "cash_flows": cash_flows},
        value,
        f"The project has an NPV of {value:.2f}. Positive NPV suggests value creation under the stated assumptions.",
        "NPV is sensitive to forecast cash flows and discount rate assumptions.",
    )


TOOL_KEYWORDS: dict[str, tuple[Callable[..., ToolResult], list[str]]] = {
    "current_ratio": (current_ratio, ["current ratio", "liquidity", "current assets", "current liabilities"]),
    "debt_to_equity": (debt_to_equity, ["debt-to-equity", "debt to equity", "leverage", "debt equity"]),
    "gross_margin": (gross_margin, ["gross margin", "gross profit", "cogs", "cost of goods"]),
    "net_profit_margin": (net_profit_margin, ["net margin", "net profit margin", "net income margin"]),
    "return_on_equity": (return_on_equity, ["roe", "return on equity"]),
    "return_on_investment": (return_on_investment, ["roi", "return on investment"]),
    "net_present_value": (net_present_value, ["npv", "net present value", "discounted cash flow"]),
}


def parse_numbers(query: str) -> list[float]:
    """Extract plain numbers, commas, negatives, and percentages from user text."""

    matches = re.findall(r"-?\$?\d[\d,]*(?:\.\d+)?%?", query)
    numbers: list[float] = []
    for match in matches:
        cleaned = match.replace("$", "").replace(",", "")
        is_percent = cleaned.endswith("%")
        cleaned = cleaned.rstrip("%")
        try:
            value = float(cleaned)
        except ValueError:
            continue
        numbers.append(value / 100 if is_percent else value)
    return numbers


def detect_tool_name(query: str) -> str | None:
    lowered = query.lower()
    for name, (_, keywords) in TOOL_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return name
    return None


def run_detected_tool(query: str) -> ToolResult | None:
    """Run the first relevant finance tool detected in the query."""

    tool_name = detect_tool_name(query)
    if not tool_name:
        return None

    numbers = parse_numbers(query)
    func = TOOL_KEYWORDS[tool_name][0]

    if tool_name == "net_present_value":
        if len(numbers) < 2:
            return None
        discount_candidates = [number for number in numbers if 0 <= number <= 1]
        discount_rate = discount_candidates[0] if discount_candidates else 0.10
        cash_flows = [number for number in numbers if number != discount_rate]
        return func(discount_rate, cash_flows)

    if len(numbers) < 2:
        return None

    return func(numbers[0], numbers[1])


def estimate_company_health_score(context: str, tool_results: list[ToolResult]) -> tuple[int, str]:
    """Simple educational company health heuristic for the MVP."""

    score = 60
    lowered = context.lower()

    positive_terms = ["revenue growth", "positive operating cash flow", "improved margin", "cash flow remained positive", "lower debt"]
    risk_terms = ["risk", "decline", "pressure", "debt increased", "liquidity pressure", "margin declined", "lawsuit", "uncertainty"]

    score += 5 * sum(term in lowered for term in positive_terms)
    score -= 5 * sum(term in lowered for term in risk_terms)

    for result in tool_results:
        name = result.tool_name.lower()
        value = result.result
        if "current ratio" in name:
            score += 8 if value >= 1.5 else -8
        elif "debt-to-equity" in name:
            score += 5 if value <= 1.5 else -8
        elif "margin" in name or "return" in name:
            score += 5 if value > 0 else -8
        elif "net present value" in name:
            score += 5 if value > 0 else -5

    score = max(0, min(100, score))
    risk_level = "Low" if score >= 75 else "Medium" if score >= 50 else "High"
    return score, risk_level


def get_langchain_tools() -> list[Any]:
    """Expose finance tools as LangChain StructuredTool objects when LangChain is installed."""

    try:
        from langchain_core.tools import StructuredTool
    except Exception:
        return []

    return [
        StructuredTool.from_function(current_ratio, name="current_ratio", description="Calculate current assets divided by current liabilities."),
        StructuredTool.from_function(debt_to_equity, name="debt_to_equity", description="Calculate total debt divided by total equity."),
        StructuredTool.from_function(gross_margin, name="gross_margin", description="Calculate gross margin percentage."),
        StructuredTool.from_function(net_profit_margin, name="net_profit_margin", description="Calculate net profit margin percentage."),
        StructuredTool.from_function(return_on_equity, name="return_on_equity", description="Calculate return on equity percentage."),
        StructuredTool.from_function(return_on_investment, name="return_on_investment", description="Calculate return on investment percentage."),
        StructuredTool.from_function(net_present_value, name="net_present_value", description="Calculate NPV from a discount rate and cash flows."),
    ]
