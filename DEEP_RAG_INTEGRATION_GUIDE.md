# Deep RAG Notes For The Presentation Fork

This fork keeps only the Deep RAG ideas that are useful for a simple local presentation.

## What Deep RAG Means Here

Finance documents are not plain paragraphs. They include:

- Sections
- Tables
- Ratios
- Company names
- Time periods
- Filing/report hints
- Page-level evidence
- Chart or image summaries

The project improves basic RAG by attaching metadata to chunks and using that metadata during retrieval.

## What This Fork Keeps

- Focused finance sample documents in `data/sample_docs/`.
- Query/source metadata extraction in `src/financial_metadata.py`.
- Metadata-aware reranking in `src/rag.py`.
- Researcher/Checker agent flow in `src/agents.py`.
- Optional Gemini image summaries in `src/vision.py`.

## Retrieval Flow

```text
Sample docs or uploaded files
  -> loader
  -> text or image-summary extraction
  -> chunking
  -> metadata inference
  -> Chroma vector store
  -> query metadata inference
  -> similarity retrieval
  -> metadata-aware reranking
  -> answer context
```

## Metadata Examples

A question like:

```text
Explain Black-Scholes and delta
```

can retrieve option-pricing chunks.

A question like:

```text
What are Nile Retail's liquidity risks?
```

can prefer chunks related to company health, liquidity, working capital, and risk factors.

## Why This Is Enough For Presentation

The goal of this fork is clarity:

- Chroma is the only vector store.
- Streamlit is the only app interface.
- Sample docs and uploads are the only document sources.
- Model choices are limited to three profiles.

That keeps the project easy to install, explain, and demonstrate.
