# Finance Docs Insights: Presentation Fork

This fork is a simplified presentation version of Finance Docs Insights. The original main project stays unchanged. This fork removes deterministic offline-demo answers, reduces the model selector to three real profiles, and keeps the code easier to explain during a course presentation.

Finance Docs Insights is a local finance document assistant. It uses Streamlit, LangChain, Chroma, Ollama, optional Gemini, deterministic finance calculators, document retrieval, image ingestion, and a Researcher/Checker agent flow.

It is educational software, not a financial advisor.

## What Was Simplified In This Fork

- Removed the deterministic offline fallback responder.
- Removed the `Offline demo mode` UI toggle.
- Kept only three model profiles:
  - `Ollama Llama 3.2 3B (local)`
  - `Gemini 3.1 Flash-Lite (cloud)`
  - `Hybrid: Ollama 3B draft + Gemini check`
- Removed the future Yahoo MCP planning guide from this fork.
- Kept the main RAG, finance tools, uploads, image analysis, and metadata-aware Deep RAG ideas.

If no real model is available, the app now explains what is missing instead of generating a fake demo answer.

## Main User Flow

1. Run the Streamlit app.
2. Index the sample finance docs or upload your own PDF/image.
3. Choose a mode:
   - Company Health Analysis
   - Finance Study Assistant
   - Research Paper Explainer
   - General Document Q&A
4. Keep document retrieval, finance calculators, and the Checker agent enabled.
5. Choose one of the three model profiles.
6. Ask a finance/document question.

## Architecture

```text
Streamlit UI
  -> FinanceAssistant
     -> safety check
     -> RAG retrieval from Chroma
        -> loaders
        -> chunking
        -> metadata inference
        -> reranking
     -> finance calculators
     -> Researcher LLM
     -> optional Checker LLM
     -> clean answer, tool results, sources, trace
```

The important idea is that the model does not answer alone. It receives:

- The user question.
- Relevant retrieved chunks from indexed files.
- Deterministic finance tool outputs when calculations are needed.
- Safety instructions.
- Checker feedback when enabled.

## Project Files

```text
app.py                         Streamlit UI and runtime controls
src/agents.py                  Main assistant orchestration
src/rag.py                     Document loading, chunking, Chroma retrieval
src/financial_metadata.py      Company, filing, year, quarter, content metadata
src/llm.py                     Real Ollama/Gemini provider wrapper
src/model_profiles.py          The three presentation model profiles
src/prompts.py                 System, mode, Researcher, and Checker prompts
src/tools.py                   Finance calculators
src/safety.py                  Refusal and safety rules
src/vision.py                  Optional Gemini image/chart summary
scripts/check_gemini.py        Gemini setup checker
DEEP_RAG_INTEGRATION_GUIDE.md  Local Deep RAG notes
GEMINI_TROUBLESHOOTING.md
SECURITY.md
```

## Setup

Use Python 3.10 or newer.

```powershell
.\scripts\setup_windows.bat
```

Install Ollama from `https://ollama.com`, then pull:

```powershell
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

## Run

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

## Gemini Setup

Gemini is optional. Create a private `.env` file:

```env
GOOGLE_API_KEY=your_google_ai_studio_key_here
```

Then verify:

```powershell
.\.venv\Scripts\python.exe scripts\check_gemini.py
.\.venv\Scripts\python.exe scripts\check_gemini.py --call
```

Do not commit `.env`.

## Model Profiles

### Ollama Llama 3.2 3B (local)

Default presentation profile. It runs locally through Ollama and keeps document analysis private on the machine.

### Gemini 3.1 Flash-Lite (cloud)

Uses Gemini Flash-Lite through the API. It is useful when you want faster cloud answers and have a configured API key.

### Hybrid: Ollama 3B draft + Gemini check

The local Ollama model writes the main answer. Gemini Flash-Lite acts as the Checker agent when configured. This is useful for explaining multi-agent behavior without making every call fully cloud-based.

## Verification

These checks do not require committing private data:

```powershell
.\.venv\Scripts\python.exe -m compileall app.py src scripts tests
.\.venv\Scripts\python.exe tests\test_financial_metadata.py
```

Live-model checks:

```powershell
.\.venv\Scripts\python.exe scripts\smoke_test.py
.\.venv\Scripts\python.exe -m src.cli evaluate
```

The live-model checks require either Ollama or Gemini to be configured.

## Example Questions

```text
Explain Black-Scholes and show the formula.
Give me 3 examples related to NPV.
What are the main factors affecting Nile Retail Holdings financial health?
Calculate the current ratio if current assets are 2500 and current liabilities are 1000.
Explain the research objective, methodology, and main findings of the working capital paper.
What can you understand from this uploaded finance form?
```

## What To Present

- The app is not just a chatbot. It combines RAG, tools, prompts, safety, and model profiles.
- RAG grounds answers in uploaded/sample documents.
- Finance calculators prevent the model from guessing arithmetic.
- The Checker agent reviews the answer before display.
- Gemini image analysis can summarize uploaded finance chart images when enabled.
- Deep RAG ideas appear through metadata extraction and reranking, while Chroma stays the default local vector store.

## Git Notes

This is a separate presentation fork branch/worktree. The main branch remains unchanged.

Do not commit:

- `.env`
- `.venv`
- `outputs`
- `data/chroma_db`
- `data/uploads`
- private PDFs or private customer documents
