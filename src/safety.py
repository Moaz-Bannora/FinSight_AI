"""Safety rules for the finance document assistant."""

from __future__ import annotations

from dataclasses import dataclass


DISCLAIMER = (
    "This assistant is for educational and analytical support only. "
    "It does not provide personalized investment, legal, tax, or financial advice. "
    "Consult qualified professionals before making financial decisions."
)


REFUSAL_MESSAGE = (
    "I cannot help with personalized financial advice, guaranteed predictions, illegal activity, "
    "or misuse of private financial data. I can still help explain finance concepts, analyze "
    "uploaded documents, and show educational calculations."
)


BLOCKED_PATTERNS = [
    "guaranteed profit",
    "guarantee profit",
    "which stock should i buy",
    "tell me what stock to buy",
    "should i invest all",
    "insider trading",
    "evade tax",
    "hide income",
    "forge",
    "fake financial",
]


CAUTION_PATTERNS = [
    "buy",
    "sell",
    "short",
    "price target",
    "investment advice",
    "tax advice",
    "legal advice",
    "guarantee",
]


@dataclass(frozen=True)
class SafetyDecision:
    allowed: bool
    message: str
    caution_required: bool = False


def check_query(query: str) -> SafetyDecision:
    """Apply simple finance-domain safety rules before generation."""

    lowered = query.lower()
    if any(pattern in lowered for pattern in BLOCKED_PATTERNS):
        return SafetyDecision(False, REFUSAL_MESSAGE, True)

    caution = any(pattern in lowered for pattern in CAUTION_PATTERNS)
    return SafetyDecision(True, DISCLAIMER if caution else "", caution)


def add_disclaimer(answer: str) -> str:
    """Append the domain disclaimer if it is not already present."""

    if "educational and analytical support" in answer.lower():
        return answer
    return f"{answer.rstrip()}\n\n**Disclaimer:** {DISCLAIMER}"
