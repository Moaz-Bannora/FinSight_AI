# Deep RAG Reference Integration Guide

This guide explains how Finance Docs Insights uses ideas from `laxmimerit/Multi-Agent-Deep-RAG` while keeping the submitted project local, understandable, and runnable on another machine.

The reference direction is valuable because financial filings are mixed documents: text, tables, page structure, images, metadata, dates, companies, and numerical facts all matter. A simple "split text and embed" pipeline often retrieves the wrong chunk when the corpus grows.

## Core Ideas From The Reference Direction

The Deep RAG style is useful for finance because it emphasizes:

1. Structure-aware extraction from financial documents.
2. Storing text, tables, and image descriptions as searchable chunks.
3. Metadata such as company, filing type, fiscal year, fiscal quarter, content type, and page.
4. Hybrid retrieval signals, not only dense vector similarity.
5. Reranking and validation before final answer generation.
6. Multi-agent workflows where a researcher retrieves and drafts, then a checker verifies.

## What This Project Adopted

Finance Docs Insights adopted the local-friendly pieces:

- Query and source metadata extraction in `src/financial_metadata.py`.
- Metadata-aware reranking in `src/rag.py`.
- Focused sample finance concept files in `data/sample_docs/`.
- Optional Gemini vision summaries for uploaded images in `src/vision.py`.
- Researcher/Checker workflow in `src/agents.py`.
- Qdrant snapshot inspection, restore, and export through `scripts/qdrant_snapshot_bridge.py`.
- Batch indexing controls in the Streamlit sidebar, so large exported corpora can be loaded gradually.

## What Was Not Copied Directly

The project intentionally does not require the full reference stack by default.

Not mandatory for the submitted app:

- Qdrant as the primary vector database.
- Docker.
- Gemini.
- Sparse vector search.
- Cross-encoder reranking.
- Full table extraction pipeline.
- A LangGraph graph runtime.
- A separate backend server.

Why: the course project must be easy to run locally. Chroma, Ollama, Streamlit, sample docs, uploads, and offline tests already demonstrate the core workflow without extra infrastructure.

## Current Retrieval Flow

```text
File upload or sample docs
  -> loader
  -> text/table/image-note extraction
  -> chunking
  -> metadata inference
  -> embeddings
  -> Chroma storage
  -> query metadata inference
  -> similarity retrieval
  -> metadata-aware reranking
  -> formatted context for the Researcher
```

Important files:

- `src/rag.py`: ingestion, chunking, vector storage, retrieval, source formatting.
- `src/financial_metadata.py`: company, filing, period, content type, and page inference.
- `src/agents.py`: Researcher/Checker answer flow.
- `src/vision.py`: optional image/chart summaries.
- `tests/test_financial_metadata.py`: regression checks for metadata behavior.

## Qdrant Snapshot Workflow

The downloaded file:

```text
financial_docs-6842273198355691-2025-12-30-17-57-38.snapshot
```

is a Qdrant collection snapshot, not raw PDFs. It should stay out of Git.

Inspect it without Qdrant:

```powershell
.\.venv\Scripts\python.exe scripts\qdrant_snapshot_bridge.py inspect
```

Start Qdrant with Docker:

```powershell
.\scripts\run_qdrant.bat
```

Restore and export:

```powershell
.\.venv\Scripts\python.exe scripts\qdrant_snapshot_bridge.py restore --qdrant-url http://localhost:6333 --collection financial_docs
.\.venv\Scripts\python.exe scripts\qdrant_snapshot_bridge.py export --qdrant-url http://localhost:6333 --collection financial_docs --max-points 500
```

The exported markdown files go to:

```text
data/external_financial_docs
```

That folder is ignored by Git. After export, use the app sidebar:

1. Filter exported docs by path words, such as `amazon 2024 10-q`.
2. Choose a batch size such as 25 or 50.
3. Click `Index next batch`.
4. Repeat only when more coverage is needed.

Avoid indexing thousands of exported files in one click on a laptop. Every file must be loaded, split, embedded, and written into Chroma.

## How Metadata Improves Retrieval

Example query:

```text
Amazon Q3 2024 revenue
```

The metadata helper can infer:

```text
company_name = amazon
fiscal_quarter = q3
fiscal_year = 2024
doc_type = 10-q
```

Retrieved chunks matching those fields receive a reranking bonus. Chunks that clearly mismatch can receive a penalty. This keeps retrieval focused without hard-filtering too aggressively.

The metadata logic also avoids over-filtering comparison questions. If the user asks about both Apple and Amazon, the retrieval should not force a single company.

## What To Improve Next

Best next Deep RAG upgrades:

1. Incremental indexing with file hashes so unchanged exports are skipped.
2. Table-aware extraction for income statements, balance sheets, and cash-flow tables.
3. Optional BM25 or sparse retrieval in addition to dense embeddings.
4. Cross-encoder reranking for large corpora.
5. Context compression to reduce noisy chunks before the LLM sees them.
6. Query planning for multi-hop questions, such as comparing two companies or two periods.
7. Structured source objects with page, table, company, filing, and date shown in the UI.
8. Larger evaluation set based on filings, formulas, tables, forms, and chart images.

## Why We Keep Chroma As Default

Chroma is simple to install and runs locally with the app. Qdrant is stronger for larger corpora and hybrid retrieval, but it adds Docker/server setup. For the submitted project, the best balance is:

- Chroma by default.
- Qdrant only as an optional import bridge.
- Deep RAG concepts adopted where they improve retrieval without making setup fragile.

## Demo Guidance

For a reliable class demo:

1. Use sample docs first.
2. Show that advanced concepts are split into focused files.
3. Ask a concept question such as `Explain Black-Scholes and delta`.
4. Upload one PDF or image and ingest it.
5. If showing the snapshot, export only a small subset and index in batches.
6. Mention that the full Deep RAG path is an extension, not a requirement for running the app.

## References

- Reference repo: https://github.com/laxmimerit/Multi-Agent-Deep-RAG
- LangChain RAG guide: https://docs.langchain.com/oss/python/langchain/rag
- Chroma integration: https://python.langchain.com/docs/integrations/vectorstores/chroma/
- Qdrant documentation: https://qdrant.tech/documentation/
