# Call for Interested Developers

I'm interested in finance. My goal is to build a fully specialized local model that helps professionals automate and better understand their business without sacrificing their data privacy.

I also want to make academic finance education less tedious, and general financial knowledge more accessible for everyone.

**Development Areas:**

- Analyzing live market data using a local model or cloud AI models with API integration — yielding more structured and domain-accurate responses than general-purpose AI services.
- Fine-tuning and reviewing the model's output; with limited resources, there's only so much one person can do...
- Helping finance researchers and students at all academic levels genuinely understand finance concepts.

I'm open to new ideas and integrations within the finance context. If any of this interests you, open an issue, start a discussion, or reach out — collaboration is welcome at any level. This project is getting out of hand to do alone.

The repo is public and non-profit. Built for the field, not for revenue.

— Moaz

---

# Finance Docs Insights

Finance Docs Insights is a finance document intelligence workspace for analysts, students, founders, and finance teams. It combines local document RAG, deterministic finance calculators, optional cloud model checking, and read-only live market context — so users can understand financial documents faster without the assistant ever crossing into personalized investment advice.

The project is in active development. The current goal is to become a practical finance copilot for document review, concept explanation, valuation study, market context, and analyst-style workflows.



<img width="1906" height="930" alt="image" src="https://github.com/user-attachments/assets/64499cab-2dc4-4ae0-8fef-3807e7ce7d0b" />


<img width="1906" height="873" alt="image" src="https://github.com/user-attachments/assets/0bc37846-304a-439e-bdf6-3563766ef019" />

## Core Principles

- **Evidence first:** document answers should come from retrieved sources, not model memory.
- **Tools for numbers:** ratios, NPV, and market snapshots should be computed or fetched by tools, then explained by the model.
- **Local by default:** Ollama and Chroma keep the main workflow usable without mandatory cloud services.
- **Cloud when useful:** Gemini can be used for stronger checking and image understanding when configured.
- **No personalized advice:** the assistant explains, analyzes, and teaches — it does not tell users what to buy or sell.
- **Small valuable modules:** production value beats impressive but fragile integrations.

## What The App Can Do

- Upload and index finance PDFs, DOCX files, text files, markdown files, CSV files, and supported images.
- Ask grounded questions about uploaded reports, financial statements, forms, papers, and study notes.
- Explain finance concepts such as NPV, WACC, Black-Scholes, VaR/CVaR, CAPM, duration, convexity, credit risk, and working capital.
- Run deterministic finance calculators for current ratio, debt-to-equity, margins, ROE, ROI, and NPV.
- Optionally fetch read-only Yahoo Finance market snapshots for tickers when the user enables market data.
- Analyze company health using retrieved evidence, calculations, and a transparent educational heuristic.
- Use a Researcher/Checker workflow to draft and review answers.
- Show retrieved sources and tool results separately from the final answer.
- Optionally use Gemini vision for uploaded finance charts, tables, screenshots, and non-finance test images.

## Current Architecture

```text
Streamlit UI
  -> FinanceAssistant
     -> Safety guardrails
     -> RAG retrieval
        -> file loaders
        -> chunking and metadata inference
        -> Chroma local vector store
        -> semantic retrieval + lexical reranking
     -> Tool layer
        -> deterministic finance calculators
        -> Yahoo Finance market snapshot
     -> LLM layer
        -> Ollama local models
        -> optional Gemini models
        -> optional hybrid local draft + Gemini checker
     -> Researcher agent
     -> Checker agent
     -> Markdown/LaTeX response cleanup
```

## Project Structure

```text
Finance_Doc_LLM/
  app.py                         Streamlit application and workflow controls
  README.md                      Main production-development guide
  SECURITY.md                    Security, secrets, and public-repo rules
  requirements.txt               Core runtime dependencies
  requirements-ocr.txt           Optional OCR dependencies
  requirements-gemini-langsmith.txt
  requirements-peft.txt
  src/
    agents.py                    Safety, RAG, tools, Researcher/Checker orchestration
    cli.py                       Command-line interface
    config.py                    Paths, defaults, and environment loading
    evaluation.py                Baseline vs full-pipeline evaluation
    financial_metadata.py        Company, filing, period, content, and page metadata helpers
    llm.py                       Ollama, Gemini, hybrid provider wrapper
    market_data.py               Read-only Yahoo Finance market-data adapter
    model_profiles.py            Runtime model profiles
    prompts.py                   System, mode, Researcher, and Checker prompts
    rag.py                       File loading, chunking, Chroma indexing, retrieval, image ingestion
    safety.py                    Refusal and finance-safety rules
    tools.py                     Deterministic finance calculators and tool result rendering
    vision.py                    Optional Gemini image/chart summaries
  scripts/
    setup_windows.bat            Windows setup helper
    run_app.bat                  Windows app launcher
    run_app.ps1                  PowerShell app launcher
    setup_ollama.ps1             Pulls local Ollama models
    smoke_test.py                End-to-end smoke test
    check_gemini.py              Gemini setup checker
    verify_upload_extraction.py  Upload extraction helper
  data/
    sample_docs/                 Built-in finance reference corpus
    evaluation/test_questions.jsonl
  tests/
    test_financial_metadata.py
    test_market_data.py
  training/
    Fine_Tuning.ipynb            Experimental fine-tuning notebook
    finance_lora_dataset.jsonl
    PEFT_README.md
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

Recommended first run:

1. Click `Index sample finance docs`.
2. Keep document retrieval, finance calculators, and Checker agent enabled.
3. Select `Local fast - Ollama Llama 3.2 3B`.
4. Ask: `Explain Black-Scholes and show the formula.`

## Vector Store Standard

The production development path standardizes on **Chroma** for now.

Why Chroma stays:

- It runs locally without credentials.
- It integrates cleanly with LangChain.
- It supports persistent local stores.
- It supports metadata and multiple retrieval strategies.
- It keeps the development workflow much lighter than a required Docker/Qdrant setup.

The old Qdrant snapshot bridge has been removed from the production mainline — it added setup friction and slow ingestion without enough immediate product value. If a larger deployment later needs a managed or distributed vector database, that path should be introduced behind a retrieval interface once the core workflow is stable.

## Yahoo Finance Market Data

The app includes a read-only Yahoo Finance adapter through `src/market_data.py`.

What it does:

- Detects market-data intent: quote, stock price, market cap, P/E, beta, dividend, 52-week range.
- Detects clear ticker symbols like `$AAPL` or aliases like `Apple`.
- Fetches a compact snapshot using `yfinance`.
- Returns structured tool output with price, previous close, change percentage, market cap, P/E, beta, dividend yield, 52-week range, source, and timestamp when available.
- Caches results briefly to avoid repeated calls during a chat session.

What it does not do:

- It does not place trades.
- It does not recommend buying or selling.
- It does not guarantee real-time exchange accuracy.
- It does not replace professional market-data terminals.

Example questions:

```text
Use Yahoo market data to summarize AAPL.
What is the latest quote for $MSFT?
Give me market cap and P/E context for Nvidia.
Compare Tesla's current price with its previous close.
```

Enable `Use Yahoo market data` in the sidebar before asking these questions.

## Model Profiles

The sidebar model profiles are:

- `Local fast - Ollama Llama 3.2 3B`: fast local default for short document questions.
- `Local balanced - Ollama Qwen 2.5 7B`: stronger local reasoning if hardware allows.
- `Local long context - Ollama Llama 3.1 8B`: useful for longer reports.
- `Cloud reasoning - Gemini 3.5 Flash`: optional cloud model for stronger answers.
- `Cloud efficient - Gemini 3.1 Flash-Lite`: quota-friendlier Gemini option.
- `Hybrid quality check - Ollama draft + Gemini`: local draft with optional cloud checking.

Gemini requires the optional package and a private API key in `.env`. Do not put keys in `.env.example`.

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

The key from Google AI Studio is the Gemini API key. This project accepts either `GOOGLE_API_KEY` or `GEMINI_API_KEY` — use one, preferably `GOOGLE_API_KEY`.

Check setup without printing secrets:

```powershell
.\.venv\Scripts\python.exe scripts\check_gemini.py
```

Optional LangSmith tracing:

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT=Finance Docs Insights
```

## Optional Image OCR And Gemini Vision

Image uploads have two paths:

- OCR extracts visible text when Tesseract is installed.
- Gemini vision summarizes charts, tables, dashboards, screenshots, and other images when enabled.

Install OCR Python dependencies:

```powershell
python -m pip install -r requirements-ocr.txt
```

Tesseract itself must also be installed on Windows and available on PATH.

## CLI And Verification

CLI examples:

```powershell
.\.venv\Scripts\python.exe -m src.cli ingest-samples --reset
.\.venv\Scripts\python.exe -m src.cli ask "Calculate debt-to-equity if debt is 1350 and equity is 1500." --mode "Finance Study Assistant"
.\.venv\Scripts\python.exe -m src.cli evaluate
```

Before pushing changes:

```powershell
git status --short
.\.venv\Scripts\python.exe -m compileall app.py src scripts tests
.\.venv\Scripts\python.exe tests\test_financial_metadata.py
.\.venv\Scripts\python.exe tests\test_market_data.py
.\.venv\Scripts\python.exe -m src.cli evaluate
```

Optional smoke test:

```powershell
.\.venv\Scripts\python.exe scripts\smoke_test.py
```

## Core Example Questions

```text
What are the main factors affecting Nile Retail Holdings financial health?
Calculate the current ratio if current assets are 2500 and current liabilities are 1000.
Give me 3 examples related to NPV.
Explain WACC and show the formula.
How does the cash conversion cycle affect liquidity?
Explain Black-Scholes and the meaning of delta.
What is the difference between VaR and CVaR?
Explain panel regression in corporate finance research.
What risks are mentioned in the uploaded annual report excerpt?
Use Yahoo market data to summarize AAPL.
```

## Product Roadmap

Near-term improvements:

1. Incremental indexing with file hashes so unchanged files are skipped.
2. Better table extraction for statements and forms.
3. Structured answer objects before Markdown rendering.
4. Local retrieval logs for chunk scores, selected sources, latency, and tool calls.
5. More finance-specific evaluation cases.
6. Safer market-data prompts that clearly separate document evidence, live data, and general education.
7. Better image and chart analysis for financial dashboards and screenshots.

Later improvements:

1. Provider registry for Ollama, Gemini, OpenAI-compatible, and future local models.
2. MCP server wrapper for market data and other external read-only tools.
3. Portfolio and watchlist workspace with user-controlled local storage.
4. SEC filings ingestion and company timeline extraction.
5. More advanced valuation workflows, scenario analysis, and assumptions tracking.
6. Multimodal retrieval across text, tables, charts, images, and spreadsheets.

## Security And Data Boundaries

Do not commit:

- `.env`
- `.venv`
- `outputs`
- `data/chroma_db`
- `data/uploads`
- `data/external_financial_docs`
- private PDFs or customer documents
- model weights or adapter artifacts
- API keys, tokens, or screenshots containing secrets

Finance Docs Insights refuses personalized investment advice, guaranteed predictions, illegal finance activity, and misuse of private financial data. It explains concepts, analyzes documents, fetches read-only market context, and shows educational calculations with clear assumptions and stated limitations.
