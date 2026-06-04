# Finance Docs Insights Final Report

## 1. Project Scenario

Finance Docs Insights is a local finance document analyzer and study guide. It helps finance students, postgraduate researchers, and junior analysts understand uploaded finance documents, explain finance concepts, calculate financial ratios, and produce grounded company or paper summaries.

The assistant is not designed as a trading bot, stock recommendation system, tax advisor, or legal advisor. It is an educational and analytical assistant.

## 2. Problem Definition

Finance documents are dense and often difficult for students or junior analysts to interpret. Annual reports, research papers, and lecture materials contain many formulas, tables, risks, assumptions, and technical terms. A normal LLM may explain these topics fluently, but it can hallucinate facts or miscalculate ratios.

The project addresses this question:

How can a local LLM assistant analyze finance documents in a grounded, safe, and calculation-aware way?

## 3. Target Users

Primary users:

- Undergraduate finance students
- Postgraduate business and finance researchers
- Accounting and finance learners
- Business analytics students
- Junior analysts

Secondary users:

- Non-technical users reading company reports
- Students preparing assignments and presentations

## 4. System Overview

The system combines:

- Prompt design
- RAG over local finance documents
- Local LLM inference through Ollama
- Deterministic finance tools
- Two-agent Researcher/Checker workflow
- Evaluation benchmark
- Safety and ethics rules
- Optional PEFT/LoRA demonstration

The implementation is local-first. It uses Ollama for model inference and Chroma for local vector storage.

The UI supports multiple model profiles so future models can be tested without changing the RAG, tool, agent, or evaluation modules.

## 5. Prompt Design

The prompt design is implemented in `src/prompts.py`.

The system prompt defines the assistant as a finance education and document-analysis assistant. It instructs the model to use retrieved evidence, avoid unsupported claims, rely on tool outputs for arithmetic, and include limitations.

The project also includes mode-specific prompts:

- Company Health Analysis
- Finance Study Assistant
- Research Paper Explainer
- General Document Q&A

This helps the assistant produce structured outputs that match user intent.

## 6. Retrieval-Augmented Generation

The RAG pipeline is implemented in `src/rag.py`.

Documents are loaded, split into chunks, embedded, stored, and retrieved. The intended final path uses LangChain integrations:

- `PyPDFLoader` for PDFs
- `Docx2txtLoader` for Word documents
- `TextLoader` for TXT, Markdown, and CSV files
- `RecursiveCharacterTextSplitter` for chunking
- `Chroma` for vector storage
- Ollama embeddings or deterministic hash embeddings

At question time, the assistant retrieves relevant chunks and passes them to the Researcher/Answerer agent. The final answer includes source references.

The improved retrieval layer also normalizes extracted text, preserves section metadata, uses finance-aware query expansion, and combines vector retrieval with keyword reranking. This helps with finance forms where exact labels such as assets, liabilities, schedules, and net worth must be retrieved accurately.

Image files can be uploaded. If OCR support is installed, image text is extracted and indexed. If OCR is unavailable, the system stores image metadata and explains the limitation.

## 7. Tools and Function Calling

Finance tools are implemented in `src/tools.py`.

The available deterministic tools are:

- Current ratio
- Debt-to-equity ratio
- Gross margin
- Net profit margin
- Return on equity
- Return on investment
- Net present value

These tools improve reliability because the LLM does not need to perform arithmetic from memory. The assistant detects calculation intent, extracts numbers, runs the tool, and sends the result to the agents.

## 8. Multi-Agent Setup

The multi-agent workflow is implemented in `src/agents.py`.

The Researcher/Answerer agent drafts a response using:

- User question
- Retrieved document context
- Tool outputs
- Mode instructions

The Checker agent reviews the draft for:

- Unsupported claims
- Calculation errors
- Missing citations
- Unsafe financial advice
- Missing limitations

The final answer is the Checker-reviewed version.

## 9. Fine-Tuning or PEFT

The course requirement is addressed with an optional PEFT/LoRA demonstration in `training/`.

The file `finance_lora_dataset.jsonl` contains small finance instruction examples covering ratio explanation, company health summaries, safe refusals, and research-paper explanation.

The script `run_lora_demo.py` can preview the dataset or run a tiny LoRA training demo after installing PEFT dependencies. This demonstrates how behavior could be adapted toward safer, more finance-specific responses.

## 10. Evaluation

Evaluation is implemented in `src/evaluation.py` using `data/evaluation/test_questions.jsonl`.

The evaluation compares:

- Baseline answer without full system support
- Full answer with RAG, tools, and Checker agent

Metrics include:

- Expected term coverage
- Whether a tool was used when expected
- Whether RAG sources were retrieved
- Answer preview for manual review

The evaluation output is saved to:

- `outputs/evaluation_results.json`
- `outputs/evaluation_report.md`

## 11. Ethics, Safety, and Limitations

The safety layer is implemented in `src/safety.py`.

The assistant refuses:

- Personalized investment advice
- Guaranteed profit predictions
- Illegal finance requests
- Tax evasion or hiding income
- Misuse of private financial data

The assistant includes a disclaimer for decision-sensitive outputs:

This assistant is for educational and analytical support only. It does not provide personalized investment, legal, tax, or financial advice.

Known limitations:

- The assistant can only ground answers in documents that were uploaded or indexed.
- Poorly extracted PDF text can hurt retrieval quality.
- Scanned PDFs need OCR before ingestion.
- Hash embeddings are for smoke tests only.
- PEFT demo is intentionally lightweight.

## 12. Conclusion

Finance Docs Insights satisfies the required GenAI project components in one coherent local system. It demonstrates prompt design, RAG, tool use, multi-agent checking, PEFT preparation, evaluation, and finance-domain safety. The final result is a working local MVP that can analyze sample documents immediately and can be extended with real uploaded finance documents and stronger local models.

