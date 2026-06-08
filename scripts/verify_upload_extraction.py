"""Verify that an uploaded document is retrievable and answered from evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def default_verification_file() -> Path:
    matches = sorted((PROJECT_ROOT / "data" / "uploads").glob("*AdvancedCalculus*.pdf"))
    if matches:
        return matches[-1]

    upload_dir = PROJECT_ROOT / "data" / "uploads"
    uploads = sorted(
        path
        for path in upload_dir.glob("*")
        if path.suffix.lower() in {".pdf", ".docx", ".txt", ".md", ".csv"}
    )
    if uploads:
        return uploads[-1]

    return PROJECT_ROOT / "data" / "sample_docs" / "capital_budgeting_npv_irr_payback.md"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path, default=None, help="Uploaded file to verify.")
    parser.add_argument(
        "--question",
        default=None,
        help="Question to ask about the uploaded file.",
    )
    args = parser.parse_args()

    from src.agents import FinanceAssistant
    from src.config import OUTPUTS_DIR, ensure_project_dirs
    from src.rag import FinanceRAG

    ensure_project_dirs()
    upload_path = args.file or default_verification_file()
    if not upload_path.is_absolute():
        upload_path = PROJECT_ROOT / upload_path
    if not upload_path.exists():
        raise FileNotFoundError(upload_path)

    rag = FinanceRAG(persist_dir=OUTPUTS_DIR / "test_chroma_upload_extraction")
    rag.reset()
    chunk_count = rag.ingest_files([upload_path])
    assert chunk_count > 0, "Uploaded file produced no searchable chunks."

    assistant = FinanceAssistant(rag=rag)
    question = args.question or (
        "what can you understand from the uploaded pdf file about calculus"
        if "advancedcalculus" in upload_path.name.lower()
        else "explain NPV and capital budgeting from this finance document"
    )
    response = assistant.answer(question, mode="Document Extraction Test", top_k=8)
    answer_lower = response.answer.lower()
    blocked_phrases = [
        "does not provide any information",
        "empty or incomplete",
        "no extractable text",
        "no relevant document context",
    ]
    assert response.sources, "No sources were retrieved for the uploaded file."
    assert not any(phrase in answer_lower for phrase in blocked_phrases), response.answer

    if "advancedcalculus" in upload_path.name.lower():
        expected_terms = ["calculus", "hopital", "rates of growth", "limit"]
        assert any(term in answer_lower for term in expected_terms), response.answer

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUTS_DIR / "upload_extraction_verification.json"
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "status": "passed",
                "file": str(upload_path),
                "chunks_ingested": chunk_count,
                "mode": response.mode,
                "sources": [source.citation() for source in response.sources],
                "answer": response.answer,
            },
            file,
            indent=2,
        )

    print(f"Upload extraction verification passed. Wrote {output_path}.")
    print(response.answer[:1200])


if __name__ == "__main__":
    main()
