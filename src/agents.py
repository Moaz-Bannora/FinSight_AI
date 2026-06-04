"""Multi-agent orchestration for Finance Docs Insights."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from .config import DEFAULT_TOP_K
from .llm import LocalLLM
from .prompts import CHECKER_PROMPT, MODE_INSTRUCTIONS, RESEARCHER_PROMPT, SYSTEM_PROMPT
from .rag import FinanceRAG, RetrievedChunk, format_context
from .safety import SafetyDecision, add_disclaimer, check_query
from .tools import ToolResult, estimate_company_health_score, run_detected_tool


@dataclass
class AgentStep:
    role: str
    summary: str
    output: str


@dataclass
class AssistantResponse:
    question: str
    mode: str
    answer: str
    safety: SafetyDecision
    sources: list[RetrievedChunk] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    trace: list[AgentStep] = field(default_factory=list)
    model_provider: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "mode": self.mode,
            "answer": self.answer,
            "safety": asdict(self.safety),
            "sources": [asdict(source) for source in self.sources],
            "tool_results": [tool.to_dict() for tool in self.tool_results],
            "trace": [asdict(step) for step in self.trace],
            "model_provider": self.model_provider,
        }


class ResearcherAgent:
    def __init__(self, llm: LocalLLM) -> None:
        self.llm = llm

    def draft(self, question: str, mode: str, context: str, tool_results: list[ToolResult]) -> AgentStep:
        tool_text = "\n\n".join(tool.to_markdown() for tool in tool_results) or "No tool output."
        user_prompt = (
            f"MODE: {mode}\n"
            f"MODE INSTRUCTIONS:\n{MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS['General Document Q&A'])}\n\n"
            f"QUESTION:\n{question}\n\n"
            f"RETRIEVED CONTEXT:\n{context}\n\n"
            f"TOOL OUTPUTS:\n{tool_text}\n\n"
            "DRAFT ANSWER:"
        )
        result = self.llm.generate(f"{SYSTEM_PROMPT}\n\n{RESEARCHER_PROMPT}", user_prompt)
        return AgentStep("Researcher/Answerer", "Drafted an evidence-aware finance answer.", result.text)


class CheckerAgent:
    def __init__(self, llm: LocalLLM) -> None:
        self.llm = llm

    def review(self, question: str, mode: str, context: str, tool_results: list[ToolResult], draft: str) -> AgentStep:
        tool_text = "\n\n".join(tool.to_markdown() for tool in tool_results) or "No tool output."
        user_prompt = (
            f"MODE: {mode}\n\n"
            f"QUESTION:\n{question}\n\n"
            f"RETRIEVED CONTEXT:\n{context}\n\n"
            f"TOOL OUTPUTS:\n{tool_text}\n\n"
            f"DRAFT ANSWER:\n{draft}\n\n"
            "FINAL CHECKED ANSWER:\n"
        )
        result = self.llm.generate(f"{SYSTEM_PROMPT}\n\n{CHECKER_PROMPT}", user_prompt)
        cleaned = self._clean_final_answer(result.text)
        if self._looks_like_checker_leak(cleaned):
            cleaned = draft.strip()
        return AgentStep("Checker", "Reviewed grounding, safety, and calculation consistency.", cleaned)

    @staticmethod
    def _clean_final_answer(text: str) -> str:
        """Strip checker meta-analysis when a small model leaks the review process."""

        cleaned = text.strip()
        markers = [
            "Revised Final Checked Answer:",
            "Final Checked Answer:",
            "FINAL CHECKED ANSWER:",
            "Final Answer:",
            "FINAL ANSWER:",
        ]
        for marker in markers:
            index = cleaned.lower().rfind(marker.lower())
            if index != -1:
                cleaned = cleaned[index + len(marker) :].strip()
                break

        leaked_headings = [
            "Unsupported Claims:",
            "Arithmetic or Formula Mistakes:",
            "Missing Citations or Source References:",
            "Unsafe Personalized Financial Advice:",
            "Missing Uncertainty or Disclaimer:",
        ]
        if any(heading.lower() in cleaned.lower() for heading in leaked_headings):
            paragraphs = [part.strip() for part in cleaned.split("\n\n") if part.strip()]
            user_facing = [
                paragraph
                for paragraph in paragraphs
                if not any(heading.lower() in paragraph.lower() for heading in leaked_headings)
                and not paragraph.lower().startswith(("the draft answer", "however, upon closer examination"))
            ]
            if user_facing:
                cleaned = "\n\n".join(user_facing).strip()

        return cleaned

    @staticmethod
    def _looks_like_checker_leak(text: str) -> bool:
        lowered = text.lower().strip()
        leaked_markers = [
            "unsupported claims:",
            "arithmetic or formula mistakes:",
            "missing citations or source references:",
            "unsafe personalized financial advice:",
            "missing uncertainty or disclaimer:",
            "the draft answer",
            "review the draft",
        ]
        return any(marker in lowered for marker in leaked_markers)


class FinanceAssistant:
    """High-level assistant combining safety, RAG, tools, and agents."""

    def __init__(self, rag: FinanceRAG | None = None, llm: LocalLLM | None = None) -> None:
        self.rag = rag or FinanceRAG()
        self.llm = llm or LocalLLM()
        self.researcher = ResearcherAgent(self.llm)
        self.checker = CheckerAgent(self.llm)

    def answer(
        self,
        question: str,
        mode: str = "General Document Q&A",
        use_rag: bool = True,
        use_tools: bool = True,
        use_checker: bool = True,
        top_k: int = DEFAULT_TOP_K,
    ) -> AssistantResponse:
        safety = check_query(question)
        if not safety.allowed:
            return AssistantResponse(question, mode, safety.message, safety, model_provider=self.llm.provider)

        sources = self.rag.retrieve(question, top_k=top_k) if use_rag else []
        context = format_context(sources)
        math_extraction_mode = self._looks_like_nonfinance_math(question, context)
        effective_mode = "Document Extraction Test" if math_extraction_mode else mode
        if math_extraction_mode:
            context = (
                f"{context}\n\n"
                "Document extraction note:\n"
                "The retrieved sources contain readable mathematics/calculus text. "
                "Answer from the retrieved text and do not describe the uploaded file as empty or incomplete. "
                "Do not print source labels inside the main answer."
            )
        form_hint = self._form_section_hint(question, context)
        if form_hint:
            context = f"{context}\n\n{form_hint}"

        tool_results: list[ToolResult] = []
        if use_tools:
            try:
                tool_result = run_detected_tool(question)
            except ValueError as exc:
                tool_result = None
                context = f"{context}\n\nTool error: {exc}"
            if tool_result is not None:
                tool_results.append(tool_result)

        if effective_mode in {"Company Health Analysis", "Company Health Analyzer"} and tool_results:
            score, risk_level = estimate_company_health_score(context, tool_results)
            context = f"{context}\n\nEducational health score heuristic: {score}/100. Risk level: {risk_level}."

        trace: list[AgentStep] = []
        draft = self.researcher.draft(question, effective_mode, context, tool_results)
        trace.append(draft)

        if use_checker:
            checked = self.checker.review(question, effective_mode, context, tool_results, draft.output)
            trace.append(checked)
            answer = checked.output
        else:
            answer = draft.output

        answer = self.clean_answer_text(answer)

        if self._needs_finance_disclaimer(question, context, effective_mode, safety):
            answer = add_disclaimer(answer)

        return AssistantResponse(
            question=question,
            mode=effective_mode,
            answer=answer,
            safety=safety,
            sources=sources,
            tool_results=tool_results,
            trace=trace,
            model_provider=self.llm.provider,
        )

    def baseline_answer(self, question: str) -> str:
        result = self.llm.generate(SYSTEM_PROMPT, f"QUESTION:\n{question}\n\nAnswer without retrieval, tools, or checker.")
        return result.text

    @staticmethod
    def _needs_finance_disclaimer(question: str, context: str, mode: str, safety: SafetyDecision) -> bool:
        if mode in {"Company Health Analysis", "Company Health Analyzer"}:
            return True
        if not safety.caution_required:
            return False
        text = f"{question}\n{context}".lower()
        finance_markers = [
            "stock",
            "investment",
            "invest",
            "trading",
            "portfolio",
            "tax",
            "legal",
            "financial",
            "finance",
            "company",
            "ratio",
            "npv",
            "net present value",
            "asset",
            "liability",
            "debt",
            "equity",
            "cash flow",
            "revenue",
            "profit",
        ]
        return any(marker in text for marker in finance_markers)

    @staticmethod
    def _strip_inline_source_references(answer: str) -> str:
        """Keep evidence citations in the UI source panel instead of the answer body."""

        source_heading_pattern = re.compile(
            r"^\s*(?:#{1,6}\s*)?(?:\*\*)?\s*"
            r"(?:sources?|sources used|retrieved sources?|source references?|citations?|"
            r"evidence from (?:file|documents?)(?:,\s*with source labels)?|"
            r"evidence\s+with\s+source\s+labels)"
            r"\s*(?:\*\*)?\s*:?\s*$",
            re.IGNORECASE,
        )
        source_line_pattern = re.compile(
            r"^\s*(?:[-*]\s*)?(?:\[)?Source\s+\d+[\]:：-].*$",
            re.IGNORECASE,
        )

        output: list[str] = []
        skipping_source_section = False
        for line in answer.splitlines():
            stripped = line.strip()
            if source_heading_pattern.match(stripped):
                skipping_source_section = True
                continue

            if skipping_source_section:
                starts_new_section = bool(re.match(r"^\s*(?:#{1,6}\s+|\*\*[^*]+\*\*)", line)) and not source_heading_pattern.match(stripped)
                if not starts_new_section:
                    continue
                skipping_source_section = False

            if source_line_pattern.match(stripped):
                continue
            output.append(line)

        return "\n".join(output).strip()

    @staticmethod
    def clean_answer_text(answer: str) -> str:
        return FinanceAssistant._normalize_response_markdown(
            FinanceAssistant._strip_inline_source_references(answer)
        )

    @staticmethod
    def _normalize_response_markdown(answer: str) -> str:
        """Clean common local-model formatting problems before Streamlit renders markdown."""

        lines: list[str] = []
        for line in answer.splitlines():
            stripped = line.strip()
            compact = re.sub(r"\s+", "", stripped)

            if re.fullmatch(
                r"C=?S0N\(d1\)-Ke\^\(?-?rT\)?N\(d2\)|C=S0N\(d1\)-Ke\^\(-rT\)N\(d2\)",
                compact,
                re.IGNORECASE,
            ):
                lines.append("$$C = S_0 N(d_1) - K e^{-rT} N(d_2)$$")
                continue

            if re.search(r"\bd1\s*=\s*\(ln\s*\(?S0/K\)?", stripped, re.IGNORECASE) and "d2" in stripped.lower():
                lines.extend(
                    [
                        "$$d_1 = \\frac{\\ln(S_0/K) + (r + \\sigma^2/2)T}{\\sigma\\sqrt{T}}$$",
                        "$$d_2 = d_1 - \\sigma\\sqrt{T}$$",
                    ]
                )
                continue

            if "$" in line or "\\" in line:
                lines.append(line)
                continue

            normalized = line
            normalized = re.sub(r"\bS0\b", r"$S_0$", normalized)
            normalized = re.sub(r"\bd1\b", r"$d_1$", normalized)
            normalized = re.sub(r"\bd2\b", r"$d_2$", normalized)
            normalized = re.sub(r"\bsigma\b", r"$\\sigma$", normalized, flags=re.IGNORECASE)
            lines.append(normalized)

        return "\n".join(lines).strip()

    @staticmethod
    def _looks_like_nonfinance_math(question: str, context: str) -> bool:
        question_text = question.lower()
        text = f"{question}\n{context}".lower()
        text = text.replace("Ã¢â‚¬â„¢", "'").replace("\u2019", "'").replace("Ã¢â€ â€™", "->").replace("\u2192", "->")
        math_terms = [
            "calculus",
            "lâ€™hopital",
            "l'hopital",
            "lhopital",
            "limit",
            "derivative",
            "sin x",
            "cos x",
            "xâ†’",
            "nâ†’âˆž",
            "advanced calculus",
            "x->",
            "n->",
            "infinity",
            "rates of growth",
        ]
        finance_question_terms = [
            "annual report",
            "balance sheet",
            "income statement",
            "liabilities",
            "assets",
            "cash flow",
            "financial health",
            "company health",
            "ratio",
            "debt",
            "equity",
            "liquidity",
            "profit",
            "revenue",
            "working capital",
            "npv",
            "wacc",
        ]
        math_notation_terms = [" lim ", " lim(", " indeterminate ", "f'(x)", "g'(x)"]
        question_has_math = any(term in question_text for term in math_terms if term != "limit") or any(
            term in f" {question_text} " for term in math_notation_terms
        )
        question_is_finance = any(term in question_text for term in finance_question_terms)
        if question_is_finance and not question_has_math:
            return False

        has_math_term = any(term in text for term in math_terms if term != "limit") or any(
            term in f" {text} " for term in math_notation_terms
        )
        return has_math_term and not (
            "personal financial statement" in text or "business financial statement" in text
        )

    @staticmethod
    def _form_section_hint(question: str, context: str) -> str:
        """Add exact field guidance for extracted PDF forms."""

        if "personal financial statement" not in context.lower():
            return ""

        normalized_lines = []
        for line in context.splitlines():
            cleaned = (
                line.strip()
                .replace("T otal", "Total")
                .replace("Y ou", "You")
                .replace("Lenderâ€™ s", "Lender's")
                .replace("ownerâ€™ s", "owner's")
            )
            if cleaned:
                normalized_lines.append(cleaned)

        def capture(start: str, end_terms: list[str]) -> list[str]:
            capturing = False
            captured: list[str] = []
            for line in normalized_lines:
                if start.lower() in line.lower():
                    capturing = True
                if capturing:
                    if captured and line.startswith("[Source"):
                        break
                    if captured and any(end.lower() in line.lower() for end in end_terms):
                        break
                    captured.append(line)
            return captured

        assets = capture("ASSETS", ["LIABILITIES"])
        liabilities = capture("LIABILITIES", ["Personal Financial Statement Schedules", "Schedule A"])
        schedules = capture("Personal Financial Statement Schedules", ["Schedule C", "Declarations"])

        question_lower = question.lower()
        selected: list[str] = []
        if "liabil" in question_lower or "owe" in question_lower:
            selected = liabilities
        elif "asset" in question_lower or "own" in question_lower:
            selected = assets
        elif "schedule" in question_lower:
            selected = schedules
        else:
            selected = assets + liabilities

        if not selected:
            return ""

        fields = "\n".join(f"- {line}" for line in selected[:25])
        return (
            "Form field extraction note:\n"
            "The retrieved PDF is a blank form. If the user asks what a section means or what to enter, "
            "answer by listing the exact visible fields from this extraction. Do not say the section is missing.\n"
            f"{fields}"
        )


def response_to_markdown(response: AssistantResponse) -> str:
    parts = [response.answer]
    if response.tool_results:
        parts.append("## Tool Results\n" + "\n\n".join(tool.to_markdown() for tool in response.tool_results))
    if response.sources:
        parts.append("## Sources\n" + "\n".join(f"- {source.citation()}" for source in response.sources))
    if response.trace:
        parts.append("## Agent Trace\n" + "\n".join(f"- {step.role}: {step.summary}" for step in response.trace))
    parts.append(f"## Runtime\nModel provider: `{response.model_provider}`")
    return "\n\n".join(parts)


def save_response_json(response: AssistantResponse, path: str) -> None:
    with open(path, "w", encoding="utf-8") as file:
        json.dump(response.to_dict(), file, indent=2)

