"""Regression checks for SEC-style financial metadata extraction."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.financial_metadata import extract_query_filters, infer_financial_metadata
from src.rag import FinanceRAG


def test_query_filters_single_company() -> None:
    filters = extract_query_filters("Amazon Q3 2024 revenue")
    assert filters == {
        "company_name": "amazon",
        "doc_type": "10-q",
        "fiscal_year": "2024",
        "fiscal_quarter": "q3",
    }


def test_query_filters_multi_company_do_not_overfilter() -> None:
    filters = extract_query_filters("Compare Apple 2024 annual report revenue with Amazon Q3 2024 revenue")
    assert filters == {"fiscal_year": "2024"}


def test_path_metadata_inference() -> None:
    metadata = infer_financial_metadata("data/rag-data/tables/apple/apple 10-k 2024/table_47_page_59.md")
    assert metadata["company_name"] == "apple"
    assert metadata["doc_type"] == "10-k"
    assert metadata["fiscal_year"] == "2024"
    assert metadata["content_type"] == "table"
    assert metadata["page"] == "59"


def test_metadata_reranking_prefers_matching_company() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        apple_doc = Path(tmpdir) / "apple 10-k 2024.md"
        amazon_doc = Path(tmpdir) / "amazon 10-q 2024 q3.md"
        apple_doc.write_text("Apple annual report revenue and net sales discussion.", encoding="utf-8")
        amazon_doc.write_text("Amazon Q3 2024 revenue increased in online stores and services.", encoding="utf-8")

        rag = FinanceRAG(persist_dir=Path(tmpdir) / "chroma")
        rag.ingest_directory(tmpdir, reset=True)
        results = rag.retrieve("Amazon Q3 2024 revenue", top_k=2)

    assert results
    assert "amazon" in Path(results[0].source).name.lower()


if __name__ == "__main__":
    test_query_filters_single_company()
    test_query_filters_multi_company_do_not_overfilter()
    test_path_metadata_inference()
    test_metadata_reranking_prefers_matching_company()
    print("financial metadata tests passed")
