# Security Notes

Finance Docs Insights is intended for local educational use. Treat uploaded documents and API keys as private.

## Secrets

Use `.env` for local secrets. Never commit:

- `GOOGLE_API_KEY`
- `GEMINI_API_KEY`
- `LANGSMITH_API_KEY`
- `LANGCHAIN_API_KEY`
- passwords, tokens, private keys, or customer data

The repository includes `.env.example` only as a template.

## Documents And Runtime Data

The following folders are ignored because they may contain private or generated data:

- `data/uploads/`
- `data/chroma_db/`
- `data/external_financial_docs/`
- `outputs/`
- `.venv/`

Qdrant `.snapshot` files are also ignored. Keep large datasets and private filings outside Git unless the team explicitly decides to publish a sanitized dataset.

## Public Repo Checklist

Before publishing:

```powershell
git status --short --ignored
rg -n "api[_-]?key|secret|token|password|GOOGLE_API_KEY|GEMINI_API_KEY|LANGSMITH_API_KEY|LANGCHAIN_API_KEY" -S . --glob "!**/.venv/**" --glob "!outputs/**" --glob "!data/chroma_db/**" --glob "!data/uploads/**" --glob "!data/external_financial_docs/**"
.\.venv\Scripts\python.exe -m compileall app.py src scripts tests
.\.venv\Scripts\python.exe tests\test_financial_metadata.py
.\.venv\Scripts\python.exe -m src.cli --offline-demo evaluate
```

Expected secret-scan results should only show placeholders in documentation, `.env.example`, and code that reads environment variables.

## Finance Safety

The app is not a financial advisor. It should explain documents, formulas, and concepts, but it should not provide personalized investment advice, guaranteed predictions, illegal finance activity, or unsafe instructions for handling private financial data.
