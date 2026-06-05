# Finance Docs Insights

Finance Docs Insights is a local finance document assistant for the GenAI course project. It combines Streamlit, LangChain, Chroma, Ollama, deterministic finance calculators, optional Gemini models, image understanding, and a two-agent Researcher/Checker workflow.

The project is designed for educational finance analysis, not personalized investment advice.

## Main Documentation

Use these three files as the primary project guides:

- `README.md`: setup, run guide, architecture, file purposes, team workflow, and improvement roadmap.
- `DEEP_RAG_INTEGRATION_GUIDE.md`: how the Multi-Agent Deep RAG reference ideas map into this local project and the optional Qdrant snapshot workflow.
- `YAHOO_MCP_INTEGRATION_GUIDE.md`: planned Yahoo Finance MCP integration, tool design, safety rules, and how it can improve market-data questions.

Supplemental files:

- `GEMINI_QDRANT_TROUBLESHOOTING.md`: focused fixes for Gemini keys, quota, Qdrant, and image/GPU toggles.
- `SECURITY.md`: public-repo security and secret handling notes.

## What The App Can Do

- Answer questions from uploaded finance PDFs, DOCX files, text files, markdown files, CSV files, and supported images.
- Explain finance concepts such as NPV, WACC, Black-Scholes, VaR/CVaR, CAPM, duration, convexity, and working capital.
- Analyze company health using retrieved evidence plus deterministic ratio tools.
- Explain research papers and postgraduate finance concepts.
- Keep sources out of the middle of the answer and show them in separate expanders.
- Use local Ollama models by default, with optional Gemini cloud profiles.
- Use Gemini vision to summarize uploaded chart or image files when enabled.
- Import a downloaded Qdrant financial-docs snapshot into local markdown exports, then index those exports in safer batches.

## Recommended Architecture

The current architecture is intentionally modular:

```text
Streamlit UI
  -> FinanceAssistant orchestrator
     -> Safety rules
     -> RAG retriever
        -> loaders, chunking, metadata inference, Chroma store
     -> Finance tools
     -> LLM provider
        -> Ollama, Gemini, hybrid local/cloud, offline fallback
     -> Checker agent
```

Crucial architecture improvements that are worth doing next:

1. Provider registry: keep all model providers, model IDs, fallbacks, and availability checks in one registry instead of spreading provider logic across UI and LLM code.
2. Retrieval pipeline abstraction: make retrieval stages explicit: load, parse, chunk, embed, store, retrieve, rerank, compress, cite. This makes future Qdrant, BM25, cross-encoder reranking, and table-aware retrieval easier.
3. Incremental indexing: store file hashes and skip unchanged files. This will reduce slow re-indexing for large exported financial-doc batches.
4. Background ingestion queue: move long upload/indexing tasks out of the main Streamlit run loop, with progress, cancellation, and resumable batches.
5. Tool router: separate deterministic calculators, document retrieval, image analysis, and future MCP market-data tools behind one controlled routing layer.
6. Evaluation gates: expand `data/evaluation/test_questions.jsonl` and require retrieval/source, arithmetic, safety, and image checks before each public push.
7. Observability: keep optional LangSmith tracing, but also add local structured logs for retrieval scores, selected chunks, model provider, tokens, latency, and tool calls.
8. Security boundary for external tools: any MCP or live market-data tool should be read-only, rate-limited, logged, and clearly labeled as external data.
9. Better table/form extraction: add table-aware PDF parsing for statements and finance forms instead of relying only on flattened PDF text.
10. Stronger answer contracts: use typed response sections internally, then render clean Markdown/LaTeX in the UI.

## Project Structure

```text
Finance_Doc_LLM/
  app.py                         Streamlit app and sidebar workflow
  README.md                      Main setup, architecture, and team handoff
  DEEP_RAG_INTEGRATION_GUIDE.md  Deep RAG reference and Qdrant bridge guide
  YAHOO_MCP_INTEGRATION_GUIDE.md Yahoo Finance MCP integration plan
  GEMINI_QDRANT_TROUBLESHOOTING.md
  SECURITY.md
  src/
    agents.py                    Researcher/Checker workflow and assistant orchestration
    cli.py                       Command-line interface
    config.py                    Paths and environment settings
    evaluation.py                Baseline vs full-system evaluation
    financial_metadata.py        Company, filing, period, content, and page metadata helpers
    llm.py                       Ollama, Gemini, hybrid fallback, and offline responder
    model_profiles.py            Sidebar model profiles and backward-compatible aliases
    prompts.py                   System, mode, Researcher, and Checker prompts
    rag.py                       Loading, chunking, Chroma indexing, retrieval, image ingestion
    safety.py                    Refusal and finance-safety rules
    tools.py                     Deterministic finance calculators
    vision.py                    Optional Gemini image/chart summaries
  scripts/
    setup_windows.bat            Creates `.venv` and installs dependencies
    run_app.bat                  Starts Streamlit on Windows
    run_app.ps1                  PowerShell Streamlit launcher
    setup_ollama.ps1             Pulls local Ollama models
    smoke_test.py                End-to-end smoke test
    check_gemini.py              Non-secret Gemini setup checker
    qdrant_snapshot_bridge.py    Optional Qdrant snapshot inspect/restore/export
    run_qdrant.bat/.ps1          Optional Docker Qdrant launcher
    verify_upload_extraction.py  Upload extraction check helper
  data/
    sample_docs/                 Built-in finance demo corpus
    evaluation/test_questions.jsonl
  tests/
    test_financial_metadata.py
  training/
    finance_lora_dataset.jsonl
    run_lora_demo.py
```

## Setup

Use Python 3.10 or newer. On Windows, from the project folder:

```powershell
.\scripts\setup_windows.bat
```

Manual setup:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Install Ollama from `https://ollama.com`, then pull the default local models:

```powershell
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

## Run The App

```powershell
.\scripts\run_app.bat
```

Direct command:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.headless true --server.port 8501
```

Open:

```text
http://localhost:8501
```

Recommended first demo:

1. Click `Index sample finance docs`.
2. Keep `Retrieve document evidence`, `Use finance calculators`, and `Run Checker agent` enabled.
3. Use `Local fast - Ollama Llama 3.2 3B` first.
4. Ask: `Explain Black-Scholes and show the formula.`

## Model Profiles

The sidebar model profiles are:

- `Local fast - Ollama Llama 3.2 3B`: fast local default for demos and short document questions.
- `Local balanced - Ollama Qwen 2.5 7B`: better local reasoning if the machine can run a 7B model.
- `Local long context - Ollama Llama 3.1 8B`: useful for longer reports when hardware allows it.
- `Cloud reasoning - Gemini 3.5 Flash`: optional stronger Gemini profile.
- `Cloud efficient - Gemini 3.1 Flash-Lite`: lower-latency, quota-friendlier Gemini profile.
- `Hybrid quality check - Ollama draft + Gemini`: local Ollama drafts, Gemini Flash-Lite checks when available.

Gemini free-tier limits are per project and model-specific. If quota is hit, use Flash-Lite, reduce evidence chunks, disable the Checker agent, or use the hybrid profile.

Low GPU utilization does not always mean the app is ignoring the GPU. PDF parsing, OCR, Chroma indexing, Streamlit, Python orchestration, and some embedding work are CPU-heavy. Local model generation is the stage most likely to benefit from Ollama GPU offload.

## Optional Gemini And LangSmith

Install optional dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-gemini-langsmith.txt
```

Create a private `.env` file:

```env
FIN_DOC_LLM_PROVIDER=gemini
FIN_DOC_LLM_CHAT_MODEL=gemini-3.5-flash
GOOGLE_API_KEY=your_google_ai_studio_key_here
```

The key from Google AI Studio is the Gemini API key. This project accepts either `GOOGLE_API_KEY` or `GEMINI_API_KEY`; use only one, preferably `GOOGLE_API_KEY`.

Check setup without printing secrets:

```powershell
.\.venv\Scripts\python.exe scripts\check_gemini.py
```

Make a tiny live call:

```powershell
.\.venv\Scripts\python.exe scripts\check_gemini.py --call
```

Optional LangSmith tracing:

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT=Finance Docs Insights
```

## Optional Qdrant Snapshot

The downloaded `financial_docs-...snapshot` file is a Qdrant collection snapshot, not raw PDFs. The app does not require it.

Inspect:

```powershell
.\.venv\Scripts\python.exe scripts\qdrant_snapshot_bridge.py inspect
```

If Docker Desktop is running, start Qdrant:

```powershell
.\scripts\run_qdrant.bat
```

Restore and export a manageable demo subset:

```powershell
.\.venv\Scripts\python.exe scripts\qdrant_snapshot_bridge.py restore --qdrant-url http://localhost:6333 --collection financial_docs
.\.venv\Scripts\python.exe scripts\qdrant_snapshot_bridge.py export --qdrant-url http://localhost:6333 --collection financial_docs --max-points 500
```

The exported markdown files go to `data/external_financial_docs`, which is ignored by Git. In the app, filter exported docs and index them in small batches.

## Optional Image OCR And Gemini Vision

Image uploads are supported. There are two different image paths:

- OCR: extracts visible text from images if Tesseract is installed.
- Gemini vision: creates a concise visual summary for uploaded charts/images when the sidebar toggle is enabled and a Gemini key is configured.

Install OCR Python dependencies:

```powershell
python -m pip install -r requirements-ocr.txt
```

Tesseract itself must also be installed on Windows and available on PATH.

## CLI And Verification

CLI examples:

```powershell
.\.venv\Scripts\python.exe -m src.cli --offline-demo ingest-samples --reset
.\.venv\Scripts\python.exe -m src.cli --offline-demo ask "Calculate debt-to-equity if debt is 1350 and equity is 1500." --mode "Finance Study Assistant"
.\.venv\Scripts\python.exe -m src.cli --offline-demo evaluate
```

Before pushing changes:

```powershell
git status --short
.\.venv\Scripts\python.exe -m compileall app.py src scripts tests
.\.venv\Scripts\python.exe tests\test_financial_metadata.py
.\.venv\Scripts\python.exe -m src.cli --offline-demo evaluate
```

Optional smoke test:

```powershell
.\.venv\Scripts\python.exe scripts\smoke_test.py --offline-demo
```

## Example Questions

```text
What are the main factors affecting Nile Retail Holdings financial health?
Calculate the current ratio if current assets are 2500 and current liabilities are 1000.
Give me 3 examples related to NPV.
Explain WACC and show the formula.
How does the cash conversion cycle affect liquidity?
Explain Black-Scholes and the meaning of delta.
What is the difference between VaR and CVaR?
Explain panel regression in corporate finance research.
Explain the research objective, methodology, and main findings of the working capital paper.
What risks are mentioned in the uploaded annual report excerpt?
```

## Team Handoff

The main app works without Qdrant, Docker, Gemini, LangSmith, or fine-tuning. Those are optional extensions.

Commit source, docs, tests, sample docs, and requirements.

Do not commit:

- `.env`
- `.venv`
- `outputs`
- `data/chroma_db`
- `data/uploads`
- `data/external_financial_docs`
- Qdrant `.snapshot` files
- private PDFs or customer documents
- model adapter weights

When adding features:

- Put model/provider changes in `src/model_profiles.py` and `src/llm.py`.
- Put deterministic calculations in `src/tools.py`.
- Put retrieval changes in `src/rag.py` and metadata changes in `src/financial_metadata.py`.
- Put prompt style changes in `src/prompts.py`.
- Keep the UI in `app.py` thin and focused on workflow controls.
- Add tests when retrieval, metadata, safety, or calculation behavior changes.

## Safety

Finance Docs Insights refuses personalized investment advice, guaranteed predictions, illegal finance activity, and misuse of private financial data. It can explain finance concepts, analyze uploaded documents, and show educational calculations with assumptions and limitations.
