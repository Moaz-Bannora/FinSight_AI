# Deep RAG Integration Guide

This project was improved using ideas from `laxmimerit/Multi-Agent-Deep-RAG` while keeping the local Streamlit/Ollama/Chroma structure intact.

## What Was Adopted

The reference repo uses a Deep RAG pipeline for SEC filings:

1. Extract PDFs into text, tables, and image descriptions.
2. Store everything as text so all content types are searchable.
3. Attach metadata such as company, filing type, fiscal year, fiscal quarter, content type, and page.
4. Use hybrid retrieval with dense vectors, sparse/BM25 signals, metadata filters, and reranking.
5. Let agents search, reflect, and answer from retrieved evidence.

Our project now adopts the local-friendly parts:

- Metadata extraction from user queries and file paths.
- Metadata-aware reranking in the existing Chroma pipeline.
- A Qdrant snapshot bridge for the downloaded `financial_docs` snapshot.
- A separate exported-docs folder that can be loaded from the app sidebar.

## New Files

### `src/financial_metadata.py`

Extracts SEC-style metadata:

- `company_name`: `amazon`, `apple`, `google`, `microsoft`, `tesla`, `nvidia`, `meta`
- `doc_type`: `10-k`, `10-q`, `8-k`
- `fiscal_year`: for example `2024`
- `fiscal_quarter`: `q1`, `q2`, `q3`, `q4`
- `content_type`: `text`, `table`, `image`, `image_description`
- `page`: inferred from filenames like `table_47_page_59.md`

It also avoids over-filtering comparison questions. For example, a query that mentions both Apple and Amazon will not force retrieval to only one company.

### `scripts/qdrant_snapshot_bridge.py`

Works with the downloaded `.snapshot` file.

Commands:

```powershell
python scripts\qdrant_snapshot_bridge.py inspect
python scripts\qdrant_snapshot_bridge.py status --qdrant-url http://localhost:6333
python scripts\qdrant_snapshot_bridge.py restore --qdrant-url http://localhost:6333 --collection financial_docs
python scripts\qdrant_snapshot_bridge.py export --qdrant-url http://localhost:6333 --collection financial_docs
python scripts\qdrant_snapshot_bridge.py restore-export --qdrant-url http://localhost:6333 --collection financial_docs
```

The `inspect` command works without Qdrant. The `status` command checks whether a Qdrant server is reachable. The restore/export commands need a running Qdrant server.

Start Qdrant with Docker:

```powershell
.\scripts\run_qdrant.bat
```

If Qdrant is not running, the bridge script now exits with a short explanation and the exact command to try, instead of printing a long connection traceback. If Docker Desktop is closed, the launcher explains that the external snapshot import is optional and that the main Streamlit app still works without Qdrant.

### `tests/test_financial_metadata.py`

Runnable metadata regression checks:

```powershell
python tests\test_financial_metadata.py
```

## Snapshot Meaning

The downloaded file:

```text
financial_docs-6842273198355691-2025-12-30-17-57-38.snapshot
```

is a Qdrant collection snapshot, not the original raw financial PDFs. It contains vector storage, sparse vector storage, payload storage, WAL files, and collection configuration. The inspected config shows:

- Dense vector size: `3072`
- Distance metric: `Cosine`
- Sparse vector field: `langchain-sparse`
- Payload stored on disk

Because the app currently uses Chroma, the snapshot needs to be restored to Qdrant first, then exported into markdown files under:

```text
data/external_financial_docs
```

After export, click `Load exported financial docs` in the Streamlit sidebar.

This snapshot workflow is optional. It is useful for importing the downloaded external financial-docs dataset, but it is not required for sample docs, uploaded files, image uploads, normal RAG, Ollama, Gemini, LangSmith, smoke tests, or the course demo.

## Why This Improves Answers

Before this change, retrieval mostly depended on semantic similarity and lexical overlap. Now queries like:

```text
Amazon Q3 2024 revenue
Apple 2024 annual report margins
Meta 10-K 2024 risk factors
```

can use metadata as reranking evidence. That makes the assistant more likely to retrieve the right company, filing type, fiscal period, content type, and page-level chunk.

## What Was Not Copied Directly

The reference repo uses Gemini, Qdrant hybrid mode, FastEmbed sparse embeddings, and an optional cross-encoder reranker. This project keeps Ollama and Chroma as the default local stack for course submission simplicity. The bridge script provides a path to use the Qdrant snapshot without making Qdrant mandatory for the app.
