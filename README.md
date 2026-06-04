# Finance Docs Insights: Local Finance Document LLM

Finance Docs Insights is a local finance document assistant built for the GenAI course project. It combines prompt design, Retrieval-Augmented Generation (RAG), deterministic finance tools, a two-agent Researcher/Checker workflow, evaluation, safety rules, and an optional PEFT/LoRA demo.

The app is designed for:

- Company health analysis from uploaded reports.
- Finance study support for ratios, formulas, and concepts.
- Research paper explanation for students and postgraduate researchers.
- Grounded document Q&A with sources shown separately from the main answer.

It is educational software, not a financial advisor.

## Project Structure

```text
Finance_Doc_LLM/
  app.py                         Streamlit app
  src/
    agents.py                    Researcher/Checker workflow and assistant orchestration
    cli.py                       Command-line interface
    config.py                    Paths and runtime settings
    evaluation.py                Baseline vs full-system evaluation
    llm.py                       LangChain Ollama client plus offline fallback
    prompts.py                   System, mode, Researcher, and Checker prompts
    rag.py                       LangChain document loading, chunking, Chroma retrieval
    safety.py                    Finance safety and refusal rules
    tools.py                     Deterministic financial calculators
  data/
    sample_docs/                 Built-in finance demo corpus
    evaluation/test_questions.jsonl
  training/
    finance_lora_dataset.jsonl   Tiny finance instruction dataset
    run_lora_demo.py             Optional PEFT/LoRA demo
  scripts/
    setup_windows.bat           Creates .venv and installs core dependencies
    smoke_test.py                Verifies ingestion, retrieval, tools, and answer flow
    setup_ollama.ps1             Pulls local Ollama models
    run_app.bat                  Starts Streamlit without PowerShell policy issues
    run_app.ps1                  Starts Streamlit
    qdrant_snapshot_bridge.py    Optional Qdrant snapshot inspection/restore/export
    run_qdrant.bat               Optional local Qdrant launcher through Docker
  outputs/                       Evaluation and smoke-test outputs
```

## What It Uses

- Local LLM: Ollama with `llama3.2:3b` by default.
- Embeddings: Ollama `nomic-embed-text` or deterministic hash embeddings for smoke tests.
- Framework: LangChain.
- Vector database: Chroma through `langchain-chroma`.
- UI: Streamlit.
- Document formats: PDF, DOCX, TXT, Markdown, CSV.
- Image formats: PNG, JPG, JPEG, WEBP, BMP, TIF, TIFF with optional OCR.
- Finance tools: current ratio, debt-to-equity, gross margin, net profit margin, ROE, ROI, and NPV.
- Sample finance corpus: ratios, NPV, IRR, payback, WACC, valuation, cash flow, working capital, company health, advanced asset pricing, derivatives, risk management, fixed income, credit risk, and research-paper notes.

The implementation follows current LangChain patterns for RAG, document loaders, recursive splitting, Chroma, and Ollama integrations:

- [LangChain RAG guide](https://docs.langchain.com/oss/python/langchain/rag)
- [PyPDFLoader guide](https://docs.langchain.com/oss/python/integrations/document_loaders/pypdfloader/)
- [RecursiveCharacterTextSplitter guide](https://docs.langchain.com/oss/python/integrations/splitters/recursive_text_splitter)
- [ChatOllama reference](https://api.python.langchain.com/en/latest/ollama/chat_models/langchain_ollama.chat_models.ChatOllama.html)
- [Chroma vector store reference](https://api.python.langchain.com/en/latest/chroma/vectorstores/langchain_chroma.vectorstores.Chroma.html)

## Setup

Use Python 3.10 or newer.

Fast Windows setup:

```powershell
.\scripts\setup_windows.bat
```

Manual setup:

```powershell
cd "C:\Users\Moaz Khalid\Downloads\Nile University\GenAI\Project\Finance_Doc_LLM"
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Install Ollama from https://ollama.com, then pull local models:

```powershell
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

## Verify It Works

Run the dependency-free local smoke test first:

```powershell
python scripts\smoke_test.py --offline-demo
```

That test verifies:

- Sample document ingestion.
- Retrieval over the sample corpus.
- Current ratio tool execution.
- Researcher/Checker answer flow.
- JSON output written to `outputs/smoke_test_result.json`.

After installing dependencies and Ollama, run the same test without offline mode:

```powershell
python scripts\smoke_test.py
```

## Run the App

```powershell
.\scripts\run_app.bat
```

If you prefer the direct command:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.headless true --server.port 8501
```

If you want to use the PowerShell launcher instead, run it with execution-policy bypass:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_app.ps1
```

In the sidebar:

1. Choose a mode.
2. Click `Load sample finance docs` or upload your own documents/images.
3. If `data/external_financial_docs` contains exported filing chunks, click `Load exported financial docs`.
4. Choose the RAG, tools, and Checker pipeline options.
5. Choose a model profile.
6. Leave `Offline demo mode` off when Ollama is running, or turn it on only for deterministic fallback testing.
7. Ask a finance question.

Example questions:

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

## CLI Examples

```powershell
python -m src.cli --offline-demo ingest-samples --reset
python -m src.cli --offline-demo ask "Calculate debt-to-equity if debt is 1350 and equity is 1500." --mode "Finance Study Assistant"
python -m src.cli --offline-demo evaluate
```

## Using the Downloaded Financial Docs Snapshot

The file `financial_docs-6842273198355691-2025-12-30-17-57-38.snapshot` is a Qdrant collection snapshot, not a folder of PDFs. The project includes a bridge script so it can still become useful for this local Chroma/Ollama app.

This snapshot is optional. You do not need Qdrant or Docker to run Streamlit, load sample finance docs, upload PDFs/images, ask questions, run the smoke test, or present the main course project. Qdrant is only needed if you want to import the downloaded external financial-docs dataset.

Inspect the snapshot:

```powershell
python scripts\qdrant_snapshot_bridge.py inspect
```

Restore it into a running Qdrant server:

```powershell
python scripts\qdrant_snapshot_bridge.py restore --qdrant-url http://localhost:6333 --collection financial_docs
```

Export restored point payloads to markdown files that this app can ingest:

```powershell
python scripts\qdrant_snapshot_bridge.py export --qdrant-url http://localhost:6333 --collection financial_docs
```

Or do both steps after Qdrant is running:

```powershell
python scripts\qdrant_snapshot_bridge.py restore-export --qdrant-url http://localhost:6333 --collection financial_docs
```

The exported files are written to `data/external_financial_docs`. After export, open the app and click `Load exported financial docs` in the sidebar.

Inspired by the Multi-Agent Deep RAG repo, this project now also extracts SEC-style metadata such as company, filing type, fiscal year, fiscal quarter, content type, and page hints. Retrieval uses those filters as reranking signals, so questions like `Amazon Q3 2024 revenue` should prefer Amazon 10-Q 2024 Q3 chunks when that metadata exists.

If Qdrant is not running, restore/export will show a clear message instead of a long traceback. To start Qdrant with Docker:

```powershell
.\scripts\run_qdrant.bat
```

If Docker Desktop is installed but closed, the script will ask you to start Docker Desktop. If Docker is not available on a teammate's laptop, skip this section and use the built-in sample docs or normal uploads.

Then run:

```powershell
.\.venv\Scripts\python.exe scripts\qdrant_snapshot_bridge.py restore-export --qdrant-url http://localhost:6333 --collection financial_docs
```

## Optional Gemini API and LangSmith

The project works locally with Ollama/offline mode by default. Gemini and LangSmith are optional.

Install optional dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-gemini-langsmith.txt
```

Add a `.env` file in the project root:

```env
FIN_DOC_LLM_PROVIDER=gemini
FIN_DOC_LLM_CHAT_MODEL=gemini-2.5-flash
GOOGLE_API_KEY=your_google_api_key_here
```

Then choose `Gemini API` in the app's model profile selector.

For LangSmith tracing, add:

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT=Finance Docs Insights
```

Some LangChain environments still use the older variable names, so `.env.example` also includes `LANGCHAIN_TRACING_V2` and `LANGCHAIN_API_KEY`.

## Optional PEFT/LoRA Demo

The course requires fine-tuning or PEFT. This project includes a small finance instruction dataset and optional LoRA script.

Preview the dataset:

```powershell
python training\run_lora_demo.py
```

Install PEFT dependencies and run the tiny LoRA demo:

```powershell
python -m pip install -r requirements-peft.txt
python training\run_lora_demo.py --train --base-model sshleifer/tiny-gpt2
```

For a stronger final presentation, replace `sshleifer/tiny-gpt2` with a small local model that your laptop can run.

## Optional Image OCR

Image uploads are accepted by the app. If OCR is available, the image text is indexed like document text. If OCR is not available, the app stores an image metadata note and tells you OCR is needed before the visible content can be analyzed.

Install the Python OCR wrapper:

```powershell
python -m pip install -r requirements-ocr.txt
```

You also need the Tesseract OCR program installed on Windows and available on PATH.

## Model Profiles

The UI includes these local Ollama profiles:

- `Ollama fast`: `llama3.2:3b`.
- `Ollama finance balanced`: `qwen2.5:7b`.
- `Ollama long-context`: `llama3.1:8b`.
- `Gemini API`: optional cloud profile when `langchain-google-genai` and `GOOGLE_API_KEY` are configured.

You can edit the chat model, embedding model, embedding provider, and temperature from the sidebar.

## Safety

Finance Docs Insights refuses personalized investment advice, guaranteed predictions, illegal finance activity, and misuse of private financial data. It explains concepts and documents for education and analysis only.

## Preparing a Public GitHub Repo

Before publishing, keep generated and private files out of Git. The `.gitignore` excludes `.venv`, `.env`, uploaded documents, Chroma databases, Qdrant storage, exported external docs, model adapters, and `.snapshot` files.

Recommended flow:

```powershell
git status --short
python -m compileall app.py src scripts tests
python tests\test_financial_metadata.py
python -m src.cli --offline-demo evaluate
git add .gitignore .streamlit README.md FINAL_REPORT.md DEEP_RAG_INTEGRATION_GUIDE.md TEAM_HANDOFF_GUIDE.md SECURITY.md .github app.py src scripts tests data requirements*.txt training
git commit -m "Prepare Finance Docs Insights for public collaboration"
git remote add origin https://github.com/YOUR-ACCOUNT/YOUR-REPO.git
git push -u origin main
```

Do not commit `.env`, API keys, private uploads, `.venv`, `outputs`, `data/chroma_db`, `data/uploads`, `data/external_financial_docs`, or the Qdrant `.snapshot` file.

