# Finance Docs Insights Team Handoff Guide

This guide explains what is already built, how to run it, and how teammates should work on it without breaking the course project structure.

## Current Status

Finance Docs Insights is a working local finance document assistant. The main stack is:

- Streamlit UI in `app.py`
- LangChain orchestration in `src/`
- Ollama local chat model and embeddings by default
- Chroma local vector store by default
- Optional Gemini API profile
- Optional LangSmith tracing
- Optional Qdrant bridge only for the downloaded external financial-docs snapshot
- Optional PEFT/LoRA demo in `training/`

The main app does not require Qdrant, Docker, Gemini, LangSmith, or fine-tuning. Those are optional extensions.

## Fast Start For Windows

From the project folder:

```powershell
.\scripts\setup_windows.bat
```

Install Ollama, then:

```powershell
ollama pull llama3.2:3b
ollama pull nomic-embed-text
.\scripts\run_app.bat
```

Open:

```text
http://localhost:8501
```

Inside the app, click `Load sample finance docs` and ask a question such as:

```text
Explain Black-Scholes and show the formula.
```

## Verification Commands

Use these before pushing changes:

```powershell
.\.venv\Scripts\python.exe -m compileall app.py src scripts tests
.\.venv\Scripts\python.exe tests\test_financial_metadata.py
.\.venv\Scripts\python.exe -m src.cli --offline-demo evaluate
```

Optional app run check:

```powershell
.\scripts\run_app.bat
```

## What Each Area Does

`app.py`

Streamlit interface, upload controls, sidebar runtime settings, model profile selection, response rendering, and feedback display.

`src/agents.py`

Main assistant orchestration. It combines retrieval, finance tools, safety checks, direct answering, and the optional Checker agent.

`src/rag.py`

Document ingestion and retrieval. It loads PDFs, DOCX files, text files, markdown, CSV, and supported images. It chunks content, stores embeddings in Chroma, retrieves relevant chunks, and reranks them using text relevance plus finance metadata.

`src/financial_metadata.py`

Finance metadata helpers inspired by the Multi-Agent Deep RAG reference project. It extracts company, filing type, fiscal year, fiscal quarter, content type, and page hints from text, file names, and queries.

`src/llm.py`

Model interface. It supports Ollama by default, optional Gemini API when configured, and a deterministic offline fallback so tests and demos still run when a model is unavailable.

`src/model_profiles.py`

Runtime model profiles shown in the sidebar. Keep new models here so the UI can support multiple future models cleanly.

`src/prompts.py`

System prompts, mode-specific prompts, Researcher prompt, and Checker prompt. This is where answer style, citation behavior, examples, and finance safety wording are controlled.

`src/tools.py`

Deterministic finance calculators, including ratios, margins, ROI, ROE, and NPV. Prefer adding exact calculations here instead of asking the LLM to do arithmetic freely.

`src/safety.py`

Rules that prevent personalized investment advice, guaranteed predictions, illegal activity, and unsafe handling of private financial data.

`src/evaluation.py`

Offline evaluation utilities for comparing baseline and full pipeline outputs.

`src/cli.py`

Command-line entry point for ingestion, asking questions, and evaluation without opening Streamlit.

`data/sample_docs/`

Built-in finance corpus for demos and course presentation. Concepts are separated into focused files so retrieval can pull relevant chunks without loading one huge mixed document.

`data/evaluation/test_questions.jsonl`

Small evaluation set used by the offline evaluation command.

`scripts/smoke_test.py`

End-to-end smoke test covering ingestion, retrieval, tools, and answer generation.

`scripts/qdrant_snapshot_bridge.py`

Optional bridge for the downloaded `.snapshot` file. `inspect` works without Qdrant. `restore`, `export`, and `restore-export` require a running Qdrant server.

`scripts/run_qdrant.bat` and `scripts/run_qdrant.ps1`

Optional Docker launchers for Qdrant. If Docker Desktop is closed, they now explain that Qdrant is optional and that the Streamlit app still works without it.

`training/`

Optional PEFT/LoRA course demo. This is not required to run the main app.

`.streamlit/config.toml`

Streamlit visual/runtime configuration.

## Optional Qdrant Snapshot Workflow

The downloaded `financial_docs-...snapshot` file is a Qdrant database snapshot, not a folder of readable PDFs. It should stay out of Git.

To inspect it:

```powershell
.\.venv\Scripts\python.exe scripts\qdrant_snapshot_bridge.py inspect
```

To restore/export it, Docker Desktop must be running:

```powershell
.\scripts\run_qdrant.bat
.\.venv\Scripts\python.exe scripts\qdrant_snapshot_bridge.py restore-export --qdrant-url http://localhost:6333 --collection financial_docs
```

The exported markdown files go to `data/external_financial_docs`, which is ignored by Git. After export, open the app and click `Load exported financial docs`.

## Optional Gemini And LangSmith

Install:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-gemini-langsmith.txt
```

Create `.env` from `.env.example` and set:

```env
FIN_DOC_LLM_PROVIDER=gemini
GOOGLE_API_KEY=your_google_api_key_here
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT=Finance Docs Insights
```

Do not commit `.env`.

## Git Rules For The Team

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

Before a pull request:

```powershell
git status --short
.\.venv\Scripts\python.exe -m compileall app.py src scripts tests
.\.venv\Scripts\python.exe tests\test_financial_metadata.py
.\.venv\Scripts\python.exe -m src.cli --offline-demo evaluate
```

## Suggested Next Improvements

- Add a proper cross-encoder reranker for larger corpora.
- Add a real OCR install check for image-heavy finance forms.
- Add optional Qdrant native retrieval mode if the team wants hybrid dense/sparse search.
- Expand the evaluation set with more course-specific questions.
- Add more finance tools for duration, convexity, bond pricing, Black-Scholes, VaR, and CVaR.
