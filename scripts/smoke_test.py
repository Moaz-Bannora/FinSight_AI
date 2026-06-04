"""Smoke test for the local Finance Docs Insights project."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline-demo", action="store_true", help="Force deterministic local fallback.")
    args = parser.parse_args()

    if args.offline_demo:
        os.environ["FIN_DOC_LLM_OFFLINE_DEMO"] = "1"

    from src.agents import FinanceAssistant
    from src.config import OUTPUTS_DIR, SAMPLE_DOCS_DIR, ensure_project_dirs
    from src.rag import FinanceRAG
    from src.tools import current_ratio

    ensure_project_dirs()

    tool_result = current_ratio(2500, 1000)
    assert round(tool_result.result, 2) == 2.5

    rag = FinanceRAG(persist_dir=OUTPUTS_DIR / "smoke_test_chroma_db")
    chunk_count = rag.ingest_directory(SAMPLE_DOCS_DIR, reset=True)
    assert chunk_count > 0, "Sample documents were not ingested."

    retrieved = rag.retrieve("What risks and liquidity issues affect Nile Retail Holdings?", top_k=3)
    assert retrieved, "RAG did not retrieve any sample chunks."

    assistant = FinanceAssistant(rag=rag)
    response = assistant.answer(
        "Calculate the current ratio if current assets are 2500 and current liabilities are 1000. What does it say about liquidity?",
        mode="Finance Study Assistant",
    )
    assert response.tool_results, "Tool routing did not execute a calculation."
    assert "current" in response.answer.lower(), "Assistant answer did not mention the current ratio."

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUTS_DIR / "smoke_test_result.json"
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "status": "passed",
                "chunks_ingested": chunk_count,
                "retrieved_sources": [chunk.citation() for chunk in retrieved],
                "tool_result": tool_result.to_dict(),
                "model_provider": response.model_provider,
                "answer_preview": response.answer[:500],
            },
            file,
            indent=2,
        )

    print(f"Smoke test passed. Wrote {output_path}.")


if __name__ == "__main__":
    main()
