"""Metadata extraction helpers for finance-document retrieval."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


COMPANY_ALIASES: dict[str, tuple[str, ...]] = {
    "nile_retail": ("nile retail", "nile retail holdings"),
    "amazon": ("amazon", "amzn"),
    "apple": ("apple", "aapl"),
    "google": ("google", "alphabet", "googl", "goog"),
    "microsoft": ("microsoft", "msft"),
    "tesla": ("tesla", "tsla"),
    "nvidia": ("nvidia", "nvda"),
    "meta": ("meta", "facebook", "fb"),
}

QUARTER_ALIASES: dict[str, tuple[str, ...]] = {
    "q1": ("q1", "first quarter", "1st quarter"),
    "q2": ("q2", "second quarter", "2nd quarter"),
    "q3": ("q3", "third quarter", "3rd quarter"),
    "q4": ("q4", "fourth quarter", "4th quarter"),
}


def extract_query_filters(query: str) -> dict[str, str]:
    """Extract SEC-style metadata filters from a natural-language query."""

    text = _normalize(query)
    filters: dict[str, str] = {}

    companies = _match_companies(text)
    multi_company_query = len(companies) > 1
    if len(companies) == 1:
        company = next(iter(companies))
        filters["company_name"] = company

    doc_types = _match_doc_types(text)
    if len(doc_types) == 1 and not multi_company_query:
        doc_type = next(iter(doc_types))
        filters["doc_type"] = doc_type

    fiscal_year = _match_year(text)
    if fiscal_year:
        filters["fiscal_year"] = fiscal_year

    fiscal_quarter = _match_quarter(text)
    if fiscal_quarter and not multi_company_query:
        filters["fiscal_quarter"] = fiscal_quarter

    return filters


def infer_financial_metadata(source: str | Path | None, text: str = "") -> dict[str, str]:
    """Infer document metadata from a path and optional extracted text."""

    source_text = str(source or "")
    path = Path(source_text) if source_text else Path("")
    haystack = _normalize(" ".join([source_text, " ".join(path.parts), path.stem, text[:1000]]))
    metadata: dict[str, str] = {}

    company = _match_company(haystack)
    if company:
        metadata["company_name"] = company

    doc_type = _match_doc_type(haystack)
    if doc_type:
        metadata["doc_type"] = doc_type

    fiscal_year = _match_year(haystack)
    if fiscal_year:
        metadata["fiscal_year"] = fiscal_year

    fiscal_quarter = _match_quarter(haystack)
    if fiscal_quarter:
        metadata["fiscal_quarter"] = fiscal_quarter

    content_type = _match_content_type(haystack)
    if content_type:
        metadata["content_type"] = content_type

    page = _match_page(path.name)
    if page is not None:
        metadata["page"] = str(page)

    return metadata


def metadata_filter_score(filters: dict[str, str], metadata: dict[str, Any]) -> float:
    """Return a reranking bonus or penalty for metadata filter matches."""

    if not filters:
        return 0.0

    score = 0.0
    for key, expected in filters.items():
        actual = metadata.get(key)
        if actual is None:
            continue
        if _normalize(str(actual)) == _normalize(str(expected)):
            score += 0.35
        else:
            score -= 0.25
    return score


def sanitize_metadata(metadata: dict[str, Any]) -> dict[str, str | int | float | bool]:
    """Keep metadata values compatible with Chroma and Streamlit display."""

    cleaned: dict[str, str | int | float | bool] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            cleaned[key] = value
        else:
            cleaned[key] = str(value)
    return cleaned


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _contains_term(text: str, term: str) -> bool:
    normalized_term = _normalize(term)
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(normalized_term)}(?![a-z0-9])", text))


def _match_company(text: str) -> str | None:
    companies = _match_companies(text)
    return next(iter(companies)) if len(companies) == 1 else None


def _match_companies(text: str) -> set[str]:
    matches: set[str] = set()
    for company, aliases in COMPANY_ALIASES.items():
        if any(_contains_term(text, alias) for alias in aliases):
            matches.add(company)
    return matches


def _match_doc_type(text: str) -> str | None:
    doc_types = _match_doc_types(text)
    return next(iter(doc_types)) if len(doc_types) == 1 else None


def _match_doc_types(text: str) -> set[str]:
    matches: set[str] = set()
    if re.search(r"\b10\s*k\b|\b10k\b|\bannual report\b", text):
        matches.add("10-k")
    if re.search(r"\b10\s*q\b|\b10q\b|\bquarterly report\b", text) or _match_quarter(text):
        matches.add("10-q")
    if re.search(r"\b8\s*k\b|\b8k\b|\bcurrent report\b", text):
        matches.add("8-k")
    return matches


def _match_year(text: str) -> str | None:
    match = re.search(r"\b(20[0-9]{2})\b", text)
    return match.group(1) if match else None


def _match_quarter(text: str) -> str | None:
    compact_match = re.search(r"\bq([1-4])\b", text)
    if compact_match:
        return f"q{compact_match.group(1)}"
    for quarter, aliases in QUARTER_ALIASES.items():
        if any(_contains_term(text, alias) for alias in aliases):
            return quarter
    return None


def _match_content_type(text: str) -> str | None:
    if _contains_term(text, "tables") or _contains_term(text, "table"):
        return "table"
    if _contains_term(text, "images desc") or _contains_term(text, "image description"):
        return "image_description"
    if _contains_term(text, "images") or _contains_term(text, "image"):
        return "image"
    if _contains_term(text, "markdown"):
        return "text"
    return None


def _match_page(filename: str) -> int | None:
    match = re.search(r"(?:page[_ -]?)([0-9]+)", filename.lower())
    return int(match.group(1)) if match else None
