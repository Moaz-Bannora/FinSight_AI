"""Simple evaluation comparing baseline vs full assistant."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .agents import FinanceAssistant
from .config import EVALUATION_DIR, OUTPUTS_DIR, SAMPLE_DOCS_DIR, ensure_project_dirs
from .rag import FinanceRAG


@dataclass
class EvalCase:
    id: str
    question: str
    mode: str
    expected_terms: list[str]
    expects_tool: bool = False
    expects_rag: bool = True


def load_eval_cases(path: Path | None = None) -> list[EvalCase]:
    path = path or EVALUATION_DIR / "test_questions.jsonl"
    cases: list[EvalCase] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            item = json.loads(line)
            cases.append(EvalCase(**item))
    return cases


def score_answer(answer: str, expected_terms: list[str]) -> float:
    lowered = answer.lower()
    if not expected_terms:
        return 1.0
    hits = sum(term.lower() in lowered for term in expected_terms)
    return hits / len(expected_terms)


def run_evaluation(offline_demo: bool = True) -> dict[str, Any]:
    ensure_project_dirs()
    if offline_demo:
        os.environ["FIN_DOC_LLM_OFFLINE_DEMO"] = "1"
    rag = FinanceRAG(persist_dir=OUTPUTS_DIR / "evaluation_chroma_db")
    rag.ingest_directory(SAMPLE_DOCS_DIR, reset=True)
    assistant = FinanceAssistant(rag=rag)

    cases = load_eval_cases()
    rows = []
    for case in cases:
        baseline = assistant.baseline_answer(case.question)
        full = assistant.answer(
            case.question,
            mode=case.mode,
            use_rag=True,
            use_tools=True,
            use_checker=True,
        )
        rows.append(
            {
                "id": case.id,
                "question": case.question,
                "mode": case.mode,
                "baseline_score": score_answer(baseline, case.expected_terms),
                "full_score": score_answer(full.answer, case.expected_terms),
                "tool_used": bool(full.tool_results),
                "rag_sources": len(full.sources),
                "expected_terms": case.expected_terms,
                "answer_preview": full.answer[:500],
            }
        )

    summary = {
        "cases": len(rows),
        "average_baseline_score": sum(row["baseline_score"] for row in rows) / (len(rows) or 1),
        "average_full_score": sum(row["full_score"] for row in rows) / (len(rows) or 1),
        "tool_cases_passed": sum(1 for row in rows if row["tool_used"]),
        "rag_cases_with_sources": sum(1 for row in rows if row["rag_sources"] > 0),
        "rows": rows,
    }

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    with (OUTPUTS_DIR / "evaluation_results.json").open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)

    with (OUTPUTS_DIR / "evaluation_report.md").open("w", encoding="utf-8") as file:
        file.write("# Finance Docs Insights Evaluation Report\n\n")
        file.write(f"- Cases: {summary['cases']}\n")
        file.write(f"- Average baseline score: {summary['average_baseline_score']:.2f}\n")
        file.write(f"- Average full-system score: {summary['average_full_score']:.2f}\n")
        file.write(f"- Cases with tool use: {summary['tool_cases_passed']}\n")
        file.write(f"- Cases with retrieved sources: {summary['rag_cases_with_sources']}\n\n")
        for row in rows:
            file.write(f"## {row['id']}\n")
            file.write(f"Question: {row['question']}\n\n")
            file.write(f"Baseline score: {row['baseline_score']:.2f} | Full score: {row['full_score']:.2f}\n\n")
            file.write(f"Tool used: {row['tool_used']} | RAG sources: {row['rag_sources']}\n\n")

    return summary

