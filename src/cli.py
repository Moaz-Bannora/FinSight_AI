"""Command line interface for Finance Docs Insights."""

from __future__ import annotations

import argparse
import json
import os

from .agents import FinanceAssistant, response_to_markdown
from .config import SAMPLE_DOCS_DIR, ensure_project_dirs
from .evaluation import run_evaluation
from .rag import FinanceRAG


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Finance Docs Insights CLI")
    parser.add_argument("--offline-demo", action="store_true", help="Use deterministic local fallback instead of Ollama.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser("ingest-samples", help="Ingest sample finance documents.")
    ingest.add_argument("--reset", action="store_true", help="Reset vector store before ingesting.")

    ask = subparsers.add_parser("ask", help="Ask a question.")
    ask.add_argument("question")
    ask.add_argument("--mode", default="General Document Q&A")
    ask.add_argument("--no-rag", action="store_true")
    ask.add_argument("--no-tools", action="store_true")
    ask.add_argument("--no-checker", action="store_true")

    subparsers.add_parser("evaluate", help="Run the evaluation suite.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.offline_demo:
        os.environ["FIN_DOC_LLM_OFFLINE_DEMO"] = "1"

    ensure_project_dirs()

    if args.command == "ingest-samples":
        rag = FinanceRAG()
        count = rag.ingest_directory(SAMPLE_DOCS_DIR, reset=args.reset)
        print(f"Ingested {count} chunks from {SAMPLE_DOCS_DIR}.")
        return

    if args.command == "ask":
        rag = FinanceRAG()
        rag.ingest_directory(SAMPLE_DOCS_DIR, reset=True)
        assistant = FinanceAssistant(rag=rag)
        response = assistant.answer(
            args.question,
            mode=args.mode,
            use_rag=not args.no_rag,
            use_tools=not args.no_tools,
            use_checker=not args.no_checker,
        )
        print(response_to_markdown(response))
        return

    if args.command == "evaluate":
        summary = run_evaluation(offline_demo=args.offline_demo)
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

