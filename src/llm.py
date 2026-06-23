"""Local LLM client with Ollama support and deterministic offline fallback."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .config import DEFAULT_CHAT_MODEL, DEFAULT_LLM_PROVIDER, OLLAMA_BASE_URL, get_google_api_key, offline_demo_enabled


try:
    from langchain_ollama import ChatOllama

    LANGCHAIN_OLLAMA_AVAILABLE = True
except Exception:
    ChatOllama = None
    LANGCHAIN_OLLAMA_AVAILABLE = False

try:
    from langchain_google_genai import ChatGoogleGenerativeAI

    LANGCHAIN_GOOGLE_GENAI_AVAILABLE = True
except Exception:
    ChatGoogleGenerativeAI = None
    LANGCHAIN_GOOGLE_GENAI_AVAILABLE = False


@dataclass
class GenerationResult:
    text: str
    model_name: str
    provider: str


class OfflineFinanceResponder:
    """Small deterministic responder used for smoke tests and fallback demos."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        question = self._extract("QUESTION", user_prompt) or self._last_nonempty_line(user_prompt)
        context = self._extract("RETRIEVED CONTEXT", user_prompt)
        tools = self._extract("TOOL OUTPUTS", user_prompt)
        if tools.strip().lower().startswith("no tool output"):
            tools = ""

        is_checker_call = "you are the checker agent" in system_prompt.lower() or "FINAL CHECKED ANSWER" in user_prompt
        if is_checker_call:
            draft = self._extract("DRAFT ANSWER", user_prompt) or user_prompt
            return self._clean_checker_response(draft)

        if self._asks_for_npv_examples(question):
            return self._npv_examples_answer(question)
        if "Company Health Analysis" in user_prompt or "Company Health Analyzer" in user_prompt:
            return self._company_health_answer(question, context, tools)
        if "Research Paper Explainer" in user_prompt:
            return self._paper_answer(question, context)
        if "Finance Study Assistant" in user_prompt:
            return self._study_answer(question, context, tools)
        return self._general_answer(question, context, tools)

    @staticmethod
    def _extract(label: str, text: str) -> str:
        pattern = rf"{re.escape(label)}:\n(.*?)(?:\n[A-Z][A-Z ]+:\n|\Z)"
        match = re.search(pattern, text, flags=re.DOTALL)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _last_nonempty_line(text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return lines[-1] if lines else ""

    @staticmethod
    def _extract_key_sentences(context: str, limit: int = 3, question: str = "") -> list[str]:
        if not context or context.startswith("No relevant"):
            return []
        sentences = re.split(r"(?<=[.!?])\s+", context.replace("\n", " "))
        selected = []
        keywords = [
            "revenue",
            "profit",
            "margin",
            "cash",
            "debt",
            "risk",
            "liquidity",
            "methodology",
            "sample",
            "finding",
            "npv",
            "roe",
        ]
        question_terms = {
            token
            for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]+", question.lower())
            if len(token) > 2 and token not in {"the", "and", "for", "what", "explain"}
        }
        concept_keywords: list[str] = []
        lowered_question = question.lower()
        if "black-scholes" in lowered_question or "black scholes" in lowered_question or "option" in lowered_question:
            concept_keywords.extend(["black-scholes", "black scholes", "option", "call", "put", "delta", "volatility"])
        if "var" in lowered_question or "cvar" in lowered_question:
            concept_keywords.extend(["value at risk", "conditional value at risk", "tail", "loss"])
        if "duration" in lowered_question or "convexity" in lowered_question:
            concept_keywords.extend(["duration", "convexity", "bond", "yield"])
        if "credit spread" in lowered_question:
            concept_keywords.extend(["credit spread", "default", "liquidity", "stress"])

        for sentence in sentences:
            lowered_sentence = sentence.lower()
            matches_question = bool(question_terms & set(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]+", lowered_sentence)))
            matches_concept = any(keyword in lowered_sentence for keyword in concept_keywords)
            if matches_concept or matches_question or any(keyword in lowered_sentence for keyword in keywords):
                selected.append(sentence.strip())
            if len(selected) >= limit:
                break
        return selected or [sentence.strip() for sentence in sentences[:limit] if sentence.strip()]

    def _general_answer(self, question: str, context: str, tools: str) -> str:
        if "form field extraction note:" in context.lower():
            return self._form_field_answer(context, tools)
        if "image upload:" in context.lower() and "ocr status:" in context.lower():
            return self._image_upload_answer(context)
        if self._looks_like_math_document(question, context):
            return self._math_document_answer(context)

        evidence = self._extract_key_sentences(context, question=question)
        answer = f"**Direct Answer**\n{self._educational_answer(question)}"
        if tools:
            answer += f"\n\n**Calculation Used**\n{tools.strip()}"
        if evidence:
            answer += "\n\n**Evidence Summary**\n" + "\n".join(f"- {item}" for item in evidence)
        else:
            answer += "\n\n**Evidence Summary**\nNo strong document evidence was retrieved for this question."
        answer += "\n\n**Limitations**\nThis answer is based on the available local documents and deterministic calculations."
        return answer

    @staticmethod
    def _asks_for_npv_examples(question: str) -> bool:
        lowered = question.lower()
        return ("npv" in lowered or "net present value" in lowered) and any(
            word in lowered for word in ["example", "examples", "scenario", "scenarios", "practice"]
        )

    @staticmethod
    def _requested_example_count(question: str, default: int = 3) -> int:
        match = re.search(r"\b(\d{1,2})\b", question)
        if not match:
            return default
        return max(1, min(int(match.group(1)), 8))

    def _npv_examples_answer(self, question: str) -> str:
        count = self._requested_example_count(question, default=3)
        examples = [
            (
                "Equipment purchase",
                "A company pays USD 10,000 today for equipment expected to generate USD 4,000 per year for three years at a 10% discount rate.",
                r"NPV=-10{,}000+\frac{4{,}000}{1.10}+\frac{4{,}000}{1.10^2}+\frac{4{,}000}{1.10^3}",
                "The result is about USD -52.59, so the project is almost break-even but slightly value-destroying under these assumptions.",
            ),
            (
                "Software project",
                "A team invests USD 8,000 today and expects cash inflows of USD 3,500, USD 3,500, and USD 3,000 over the next three years at a 9% discount rate.",
                r"NPV=-8{,}000+\frac{3{,}500}{1.09}+\frac{3{,}500}{1.09^2}+\frac{3{,}000}{1.09^3}",
                "The result is about USD 473.44, so the project creates value if the cash-flow assumptions are realistic.",
            ),
            (
                "Store expansion",
                "A store expansion costs USD 25,000 today and is expected to produce USD 9,000 per year for four years at a 12% discount rate.",
                r"NPV=-25{,}000+\sum_{t=1}^{4}\frac{9{,}000}{(1.12)^t}",
                "The result is about USD 2,336.14, so the expansion looks financially attractive before considering strategic and execution risk.",
            ),
            (
                "Marketing campaign",
                "A campaign costs USD 5,000 today and is expected to add USD 2,000, USD 2,500, and USD 2,500 over three years at an 11% discount rate.",
                r"NPV=-5{,}000+\frac{2{,}000}{1.11}+\frac{2{,}500}{1.11^2}+\frac{2{,}500}{1.11^3}",
                "The result is about USD 658.84, so it may be worthwhile if the projected incremental sales are credible.",
            ),
        ]
        selected = examples[:count]
        body = []
        for index, (title, scenario, equation, interpretation) in enumerate(selected, start=1):
            body.append(
                f"**Generated Example {index}: {title}**\n"
                f"- Scenario: {scenario}\n"
                f"- Equation: $${equation}$$\n"
                f"- Interpretation: {interpretation}"
            )
        return (
            "**Direct Answer**\n"
            f"Here are {len(selected)} generated educational NPV examples. They are not taken from uploaded documents.\n\n"
            "**NPV Formula**\n"
            r"$$NPV=\sum_{t=0}^{n}\frac{CF_t}{(1+r)^t}$$"
            "\n\n"
            + "\n\n".join(body)
            + "\n\n**Limitation**\n"
            "These examples are simplified for learning. Real NPV analysis depends on forecast quality, discount-rate choice, taxes, inflation, risk, and alternative uses of capital."
        )

    @staticmethod
    def _looks_like_math_document(question: str, context: str) -> bool:
        question_text = question.lower()
        text = f"{question}\n{context}".lower()
        text = text.replace("â€™", "'").replace("\u2019", "'").replace("â†’", "->").replace("\u2192", "->")
        finance_question_terms = [
            "finance",
            "financial",
            "black-scholes",
            "black scholes",
            "option",
            "greek",
            "delta",
            "npv",
            "irr",
            "capm",
            "portfolio",
            "bond",
            "duration",
            "convexity",
            "var",
            "cvar",
            "credit spread",
            "stochastic discount factor",
            "asset pricing",
        ]
        if any(term in question_text for term in finance_question_terms):
            return False

        strong_terms = [
            "calculus",
            "l'hopital",
            "lhopital",
            "derivative",
            "sin x",
            "cos x",
            "rates of growth",
            "running times of algorithms",
            "lim x",
            "lim n",
        ]
        question_math = any(term in question_text for term in strong_terms) or bool(
            re.search(r"\blim\b|\bindeterminate\b|f'\(x\)|g'\(x\)", question_text)
        )
        context_math = any(term in text for term in strong_terms) or bool(
            re.search(r"\blim\b|\bindeterminate\b|f'\(x\)|g'\(x\)", text)
        )
        return (question_math or context_math) and "personal financial statement" not in text

    @staticmethod
    def _math_document_answer(context: str) -> str:
        normalized = context.replace("â€™", "'").replace("\u2019", "'")
        evidence_items: list[str] = []
        equation_items: list[str] = []
        fragments = re.split(r"(?<=[.!?])\s+|\n+", normalized)
        equation_markers = [
            "f'(x)",
            "g'(x)",
            "sin x",
            "cos x",
            "x ->",
            "n ->",
            "0/0",
            "infinity",
            "rates of growth",
        ]
        idea_markers = ["l'hopital", "advanced calculus", "rates of growth", "running times", "algorithm"]

        for fragment in fragments:
            item = re.sub(r"\s+", " ", fragment).strip()
            if not item or item.startswith("[Source"):
                continue
            lowered = item.lower().replace("â†’", "->").replace("\u2192", "->")
            has_equation_marker = any(marker in lowered for marker in equation_markers) or bool(
                re.search(r"\blim\b", lowered)
            )
            if has_equation_marker and len(item) > 18:
                equation_items.append(item)
            if any(marker in lowered for marker in idea_markers) and len(item) > 12:
                evidence_items.append(item)

        if not evidence_items:
            evidence_items = [
                item
                for item in (re.sub(r"\s+", " ", part).strip() for part in fragments)
                if item and not item.startswith("[Source")
            ][:4]

        topic = "The retrieved text is from advanced calculus notes, mainly about L'Hopital's Rule and rates of growth."
        if any("running times" in item.lower() or "algorithm" in item.lower() for item in evidence_items):
            topic += " It also connects growth rates with algorithm running-time comparison."

        lowered_context = normalized.lower()
        if "l'hopital" in lowered_context and not any("derivative-ratio" in item for item in equation_items):
            equation_items.insert(
                0,
                "Readable interpretation: for 0/0 or infinity/infinity forms, the notes compare "
                "lim f(x)/g(x) with lim f'(x)/g'(x) when the derivative-ratio limit exists.",
            )

        equation_text = (
            "\n".join(f"- {item}" for item in equation_items[:6])
            if equation_items
            else "- The extracted text indicates calculus notation, but the equation formatting is too flattened to quote confidently."
        )
        evidence_text = "\n".join(f"- {item}" for item in evidence_items[:6])

        return (
            "**Document Topic**\n"
            f"{topic}\n\n"
            "**Main Ideas**\n"
            "- The notes describe when L'Hopital's Rule can be used for indeterminate limit forms.\n"
            "- They compare growth rates by looking at limits of ratios.\n"
            "- They include examples where formulas are simplified before interpreting the limit.\n\n"
            "**Important Equations or Notation Found**\n"
            f"{equation_text}\n\n"
            "**Evidence Summary**\n"
            f"{evidence_text}\n\n"
            "**Extraction Limitations**\n"
            "PDF text extraction can flatten mathematical notation, line breaks, superscripts, and arrows. "
            "The answer above is based on the readable extracted text, not a visual proof reconstruction."
        )

    @staticmethod
    def _form_field_answer(context: str, tools: str) -> str:
        marker = "form field extraction note:"
        note = context[context.lower().index(marker) + len(marker) :]
        fields = [line[2:].strip() for line in note.splitlines() if line.strip().startswith("- ")]
        cleaned_fields = []
        for field in fields:
            if field.startswith("[Source") or field.startswith("FORM FIELD"):
                continue
            cleaned_fields.append(field)
        field_text = "\n".join(f"- {field}" for field in cleaned_fields[:20])
        return (
            "**Direct Answer**\n"
            "This part of the PDF is asking you to fill in the visible fields from the Personal Financial Statement form section.\n\n"
            "**Fields Shown in the Document**\n"
            f"{field_text}\n\n"
            "**How to Use It**\n"
            "Enter the dollar amount for each line that applies, then calculate the total for the section. "
            "Use the referenced schedules when the form asks for extra detail.\n\n"
            "**Limitation**\n"
            "This explains the form fields from the uploaded document; it does not decide what your actual financial values are."
        )

    @staticmethod
    def _image_upload_answer(context: str) -> str:
        lines = [line.strip() for line in context.splitlines() if line.strip()]
        image_lines = [line for line in lines if line.lower().startswith(("image upload:", "ocr status:", "image ocr text"))]
        extracted_text = [
            line
            for line in lines
            if not line.startswith("[Source") and not line.lower().startswith(("image upload:", "ocr status:"))
        ]
        if any("ocr_unavailable" in line.lower() or "metadata_only" in line.lower() for line in image_lines):
            return (
                "**Direct Answer**\n"
                "The image file was uploaded and indexed, but its visible text could not be extracted yet because OCR is not available.\n\n"
                "**What To Do**\n"
                "Install Tesseract OCR and `requirements-ocr.txt`, then re-upload or re-ingest the image so the assistant can search and answer from the image text.\n\n"
                "**Evidence Summary**\n"
                + "\n".join(f"- {line}" for line in image_lines[:5])
            )
        return (
            "**Direct Answer**\n"
            "The image upload contains OCR-extracted text. I can answer from that extracted text.\n\n"
            "**Evidence Summary**\n"
            + "\n".join(f"- {line}" for line in extracted_text[:8])
        )

    def _study_answer(self, question: str, context: str, tools: str) -> str:
        evidence = self._extract_key_sentences(context, question=question)
        lowered_question = question.lower()
        if "black-scholes" in lowered_question or "black scholes" in lowered_question:
            formula_text = (
                "$$C = S_0N(d_1)-Ke^{-rT}N(d_2)$$\n\n"
                "$$d_1=\\frac{\\ln(S_0/K)+(r+\\sigma^2/2)T}{\\sigma\\sqrt{T}}, "
                "\\quad d_2=d_1-\\sigma\\sqrt{T}$$"
            )
            answer = (
                "**Simple Explanation**\n"
                "Black-Scholes estimates the theoretical price of a European option from the current stock price, "
                "strike price, time to maturity, risk-free rate, and volatility.\n\n"
                "**Technical Definition**\n"
                "For a European call option, the model values the expected payoff under risk-neutral pricing. "
                "The terms $N(d_1)$ and $N(d_2)$ use the standard normal cumulative distribution.\n\n"
                "**Formula or Example**\n"
                f"{formula_text}\n\n"
                "**How to Interpret It**\n"
                "$S_0$ is the current underlying price, $K$ is the strike, $r$ is the risk-free rate, "
                "$T$ is time to maturity, and $\\sigma$ is volatility. Higher volatility usually increases option value.\n\n"
                "**Common Mistakes**\n"
                "- Applying it to American options without adjustment.\n"
                "- Treating volatility as known and constant.\n"
                "- Ignoring dividends, transaction costs, liquidity, and volatility smiles.\n\n"
                "**Quick Quiz Question**\n"
                "If volatility rises while other inputs stay the same, what usually happens to the value of a European call option?"
            )
            if evidence:
                answer += "\n\n**Evidence Summary**\n" + "\n".join(f"- {item}" for item in evidence[:2])
            return answer

        answer = (
            "**Simple Explanation**\n"
            f"{self._educational_answer(question)}\n\n"
            "**Technical Definition**\n"
            "The concept should be interpreted using its formula, business context, and comparison period or peer group.\n\n"
            "**Formula or Example**\n"
            f"{tools.strip() if tools else 'Use the relevant finance formula and verify arithmetic with the calculator tools.'}\n\n"
            "**How to Interpret It**\n"
            "A single ratio rarely proves health by itself. Combine it with profitability, liquidity, leverage, cash flow, and risk evidence.\n\n"
            "**Common Mistakes**\n"
            "- Treating one ratio as a final decision.\n- Ignoring industry differences.\n- Mixing values from different time periods.\n\n"
            "**Quick Quiz Question**\n"
            "Why can a company have positive profit but still face liquidity pressure?"
        )
        if evidence:
            answer += "\n\n**Evidence Summary**\n" + "\n".join(f"- {item}" for item in evidence)
        return answer

    def _company_health_answer(self, question: str, context: str, tools: str) -> str:
        evidence = self._extract_key_sentences(context, limit=8, question=question)
        evidence = [item for item in evidence if self._is_company_health_evidence(item)]
        lowered = context.lower()
        positives = [item for item in evidence if any(word in item.lower() for word in ["growth", "positive", "improved", "strong"])]
        risks = [item for item in evidence if any(word in item.lower() for word in ["risk", "pressure", "debt", "decline", "uncertainty"])]
        if "revenue growth" in lowered and not any("revenue growth" in item.lower() for item in positives):
            positives.append("Revenue growth is a positive factor in the retrieved company evidence.")
        if "gross margin declined" in lowered and not any("margin" in item.lower() for item in risks):
            risks.append("Gross margin declined, which signals margin pressure.")
        if "inventory growth" in lowered and not any("inventory" in item.lower() for item in risks):
            risks.append("Inventory growth created working capital pressure.")
        if "debt" in lowered and not any("debt" in item.lower() for item in risks):
            risks.append("Debt and debt service are risk factors to monitor.")
        if "risk" in lowered and not any("risk" in item.lower() for item in risks):
            risks.append("The retrieved document includes risk factors that should limit confidence in the health assessment.")
        answer = (
            "**Executive Summary**\n"
            "The company should be assessed across profitability, liquidity, leverage, cash flow, operating performance, and risk disclosures.\n\n"
            "**Educational Company Health Score**\n"
            "Use the score produced by the tool layer when ratio values are available. Without complete statements, treat the assessment as preliminary.\n\n"
            "**Key Positive Factors**\n"
            + ("\n".join(f"- {item}" for item in positives) if positives else "- No strong positive factors were retrieved.")
            + "\n\n**Key Risk Factors**\n"
            + ("\n".join(f"- {item}" for item in risks) if risks else "- No strong risk factors were retrieved.")
            + "\n\n**Ratio Insights**\n"
            + (tools.strip() if tools else "No ratio tool was triggered from the question. Ask with numbers to calculate current ratio, debt-to-equity, margins, ROE, ROI, or NPV.")
            + "\n\n**Suggested Improvement Areas**\n"
            "- Strengthen cash conversion and working capital discipline.\n- Monitor leverage and interest burden.\n- Protect margins through cost control and pricing review.\n\n"
            "**Evidence Summary**\n"
            + ("\n".join(f"- {item}" for item in evidence) if evidence else "No strong document evidence was retrieved.")
        )
        return answer

    @staticmethod
    def _is_company_health_evidence(item: str) -> bool:
        lowered = item.lower()
        concept_noise = [
            "capital asset pricing model",
            "stochastic discount factor",
            "black-scholes",
            "merton structural",
            "duration",
            "convexity",
            "event study",
            "panel gmm",
            "option greeks",
        ]
        if any(term in lowered for term in concept_noise):
            return False
        return True

    def _paper_answer(self, question: str, context: str) -> str:
        evidence = self._extract_key_sentences(context, limit=5, question=question)
        evidence_text = "\n".join(f"- {item}" for item in evidence) if evidence else "No strong paper evidence was retrieved."
        lowered = context.lower()
        objective = (
            "The paper studies working capital management and profitability in emerging market retail firms."
            if "working capital" in lowered
            else "Identify the finance problem studied by the paper and why it matters."
        )
        method = (
            "The methodology is panel regression with firm fixed effects and robust standard errors."
            if "panel regression" in lowered
            else "Extract the sample, dependent variable, independent variables, controls, and empirical method from the paper."
        )
        findings = (
            "The main finding is that a shorter cash conversion cycle is associated with higher return on assets, with inventory days showing a strong negative relationship with profitability."
            if "cash conversion cycle" in lowered or "return on assets" in lowered
            else evidence_text
        )
        return (
            "**Paper Objective**\n"
            f"{objective}\n\n"
            "**Research Question**\nUse the abstract, introduction, and hypothesis section to state the core question.\n\n"
            "**Data, Variables, and Methodology**\n"
            f"{method}\n\n"
            "**Main Findings**\n"
            f"{findings}\n\n"
            "**Evidence Summary**\n"
            f"{evidence_text}\n\n"
            "**Practical Meaning**\nTranslate findings into plain language, while keeping the limits of the study visible.\n\n"
            "**Limitations**\nCheck sample scope, time period, omitted variables, and whether the results are correlational or causal.\n\n"
            "**Literature Review Use**\nUse this paper to support a specific argument, compare methods, or identify a research gap."
        )

    @staticmethod
    def _educational_answer(question: str) -> str:
        lowered = question.lower()
        if "current ratio" in lowered or "liquidity" in lowered:
            return "The current ratio measures short-term liquidity by comparing current assets with current liabilities."
        if "debt" in lowered and "equity" in lowered:
            return "Debt-to-equity measures financial leverage by comparing creditor financing with shareholder financing."
        if "gross margin" in lowered:
            return "Gross margin shows how much revenue remains after direct production or service costs."
        if "net margin" in lowered or "profit margin" in lowered:
            return "Net profit margin shows the share of revenue left as profit after all expenses."
        if "roe" in lowered or "return on equity" in lowered:
            return "ROE measures how efficiently a company generates profit from shareholder equity."
        if "npv" in lowered or "net present value" in lowered:
            return r"NPV discounts expected cash flows to today's value using $NPV=\sum_{t=0}^{n}\frac{CF_t}{(1+r)^t}$ to judge whether a project creates value."
        if "wacc" in lowered or "weighted average cost of capital" in lowered:
            return r"WACC estimates the blended required return for debt and equity financing: $WACC=\frac{E}{D+E}R_e+\frac{D}{D+E}R_d(1-T)$."
        if "black-scholes" in lowered or "black scholes" in lowered:
            return (
                "Black-Scholes prices European options using the stock price, strike, time, risk-free rate, "
                "and volatility.\n\n"
                r"$$C = S_0N(d_1)-Ke^{-rT}N(d_2)$$"
                "\n\n"
                r"$$d_1=\frac{\ln(S_0/K)+(r+\sigma^2/2)T}{\sigma\sqrt{T}}, \quad d_2=d_1-\sigma\sqrt{T}$$"
            )
        if "delta" in lowered and ("option" in lowered or "black" in lowered):
            return r"Option delta measures sensitivity of option value to the underlying asset price; for a Black-Scholes European call, $\Delta=N(d_1)$."
        if "var" in lowered and "cvar" in lowered:
            return r"VaR estimates a loss threshold at a confidence level, while CVaR estimates expected loss beyond that threshold: $CVaR_\alpha=E[L\mid L\ge VaR_\alpha]$."
        if "capm" in lowered:
            return r"CAPM links expected return to systematic market risk: $E(R_i)=R_f+\beta_i(E(R_m)-R_f)$."
        if "panel regression" in lowered:
            return r"Panel regression uses observations across firms and time, often with firm and time fixed effects: $Y_{i,t}=\alpha_i+\gamma_t+\beta X_{i,t}+\epsilon_{i,t}$."
        if "gmm" in lowered or "generalized method of moments" in lowered:
            return r"GMM estimates parameters by matching theoretical moment conditions to sample moments: $\hat{\theta}=\arg\min_\theta \bar{g}(\theta)^\top W\bar{g}(\theta)$."
        if "duration" in lowered and "convexity" in lowered:
            return r"Duration approximates bond price sensitivity to yield, while convexity improves the estimate for larger yield changes: $\frac{\Delta P}{P}\approx-D_{mod}\Delta y+\frac{1}{2}Convexity(\Delta y)^2$."
        return "A grounded finance answer should combine document evidence, formulas, assumptions, and limitations."

    @staticmethod
    def _clean_checker_response(draft: str) -> str:
        return draft.strip()


class LocalLLM:
    """Generate text with Ollama/Gemini through LangChain, or fallback offline."""

    def __init__(
        self,
        model_name: str = DEFAULT_CHAT_MODEL,
        provider_name: str = DEFAULT_LLM_PROVIDER,
        base_url: str = OLLAMA_BASE_URL,
        temperature: float = 0.2,
        offline_demo: bool | None = None,
        fallback_model_name: str = DEFAULT_CHAT_MODEL,
        fallback_to_ollama: bool = True,
        prefer_ollama_gpu: bool = False,
    ) -> None:
        self.model_name = model_name
        self.provider_name = provider_name.lower().strip()
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.offline_demo = offline_demo_enabled() if offline_demo is None else offline_demo
        self.fallback_model_name = fallback_model_name
        self.fallback_to_ollama = fallback_to_ollama
        self.prefer_ollama_gpu = prefer_ollama_gpu
        self.offline = OfflineFinanceResponder()
        self.chat: Any | None = None
        self.fallback_chat: Any | None = None
        self.status_message = ""

        if self.offline_demo:
            self.status_message = "Offline demo mode is enabled."
        elif self.provider_name == "gemini":
            self._init_gemini()
            self._init_fallback_ollama()
        else:
            self._init_ollama()

    @property
    def provider(self) -> str:
        if self.chat is not None:
            return f"langchain-{self.provider_name}"
        if self.fallback_chat is not None:
            return "langchain-ollama-fallback"
        return "offline-deterministic"

    def _init_ollama(self) -> None:
        if not LANGCHAIN_OLLAMA_AVAILABLE:
            self.status_message = "langchain-ollama is not installed; using offline fallback."
            return
        if not self.is_ollama_running():
            self.status_message = f"Ollama is not reachable at {self.base_url}; using offline fallback."
            return
        self.provider_name = "ollama"
        self.chat = self._make_ollama_chat(self.model_name)
        if self.prefer_ollama_gpu:
            self.status_message = "Ollama GPU preference is enabled. Ollama will use GPU layers when supported."

    def _make_ollama_chat(self, model_name: str) -> Any:
        kwargs = {
            "model": model_name,
            "base_url": self.base_url,
            "temperature": self.temperature,
        }
        if self.prefer_ollama_gpu:
            kwargs["num_gpu"] = -1
        return ChatOllama(**kwargs)

    def _init_fallback_ollama(self) -> None:
        if not self.fallback_to_ollama or self.fallback_chat is not None:
            return
        if not LANGCHAIN_OLLAMA_AVAILABLE or not self.is_ollama_running():
            return
        try:
            self.fallback_chat = self._make_ollama_chat(self.fallback_model_name)
            fallback_note = f"Ollama fallback ready: {self.fallback_model_name}."
            self.status_message = f"{self.status_message} {fallback_note}".strip()
        except Exception:
            self.fallback_chat = None

    def _init_gemini(self) -> None:
        if not LANGCHAIN_GOOGLE_GENAI_AVAILABLE:
            self.status_message = "langchain-google-genai is not installed; using offline fallback."
            return
        google_api_key = get_google_api_key()
        if not google_api_key:
            self.status_message = "GOOGLE_API_KEY/GEMINI_API_KEY is not set; using offline fallback."
            return
        self.provider_name = "gemini"
        try:
            self.chat = ChatGoogleGenerativeAI(model=self.model_name, temperature=self.temperature, api_key=google_api_key)
        except TypeError:
            try:
                self.chat = ChatGoogleGenerativeAI(
                    model=self.model_name,
                    temperature=self.temperature,
                    google_api_key=google_api_key,
                )
            except Exception as exc:
                self.status_message = f"Gemini initialization failed: {exc}; using offline fallback."
        except Exception as exc:
            self.status_message = f"Gemini initialization failed: {exc}; using offline fallback."

    def is_ollama_running(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=3) as response:
                return response.status == 200
        except (urllib.error.URLError, TimeoutError, OSError):
            return False

    def list_models(self) -> list[str]:
        try:
            with urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=3) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return [item["name"] for item in payload.get("models", [])]
        except Exception:
            return []

    def generate(self, system_prompt: str, user_prompt: str) -> GenerationResult:
        if self.chat is not None:
            try:
                message = self.chat.invoke([("system", system_prompt), ("human", user_prompt)])
                return GenerationResult(self._message_text(message), self.model_name, self.provider)
            except Exception as exc:
                if self.fallback_chat is not None:
                    short_error = self._short_error(exc)
                    self.status_message = f"{self.provider_name} call failed ({short_error}); used Ollama fallback."
                    message = self.fallback_chat.invoke([("system", system_prompt), ("human", user_prompt)])
                    return GenerationResult(self._message_text(message), self.fallback_model_name, "langchain-ollama-fallback")
                self.status_message = f"{self.provider_name} call failed ({self._short_error(exc)}); using offline fallback."

        if self.fallback_chat is not None:
            message = self.fallback_chat.invoke([("system", system_prompt), ("human", user_prompt)])
            return GenerationResult(
                self._message_text(message),
                self.fallback_model_name,
                "langchain-ollama-fallback",
            )

        return GenerationResult(
            self.offline.generate(system_prompt, user_prompt),
            "offline-demo",
            self.provider,
        )

    @staticmethod
    def _short_error(exc: Exception) -> str:
        message = re.sub(r"\s+", " ", str(exc)).strip()
        if not message:
            return exc.__class__.__name__
        return message[:180]

    @staticmethod
    def _message_text(message: Any) -> str:
        content = getattr(message, "content", message)
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if text:
                        parts.append(str(text))
                elif isinstance(item, str):
                    parts.append(item)
            if parts:
                return "\n".join(parts).strip()
        return str(content).strip()
