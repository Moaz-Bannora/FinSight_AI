# Gemini And Qdrant Troubleshooting

This guide covers two optional features that are useful but not required for the main local app.

## Gemini API

The key from Google AI Studio is the right key.

In this project, `GOOGLE_API_KEY` and `GEMINI_API_KEY` are aliases for the same Gemini API key. Use only one. Prefer:

```env
GOOGLE_API_KEY=your_google_ai_studio_key_here
```

Put it in:

```text
.env
```

Do not put a real key in:

```text
.env.example
```

`.env.example` is committed to GitHub as a safe template. `.env` is ignored by Git and is loaded by the app.

### Gemini Setup Steps

1. Install dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

2. Create `.env` in the project root:

```env
FIN_DOC_LLM_PROVIDER=gemini
FIN_DOC_LLM_CHAT_MODEL=gemini-3.5-flash
GOOGLE_API_KEY=your_google_ai_studio_key_here
```

3. Check local setup without printing the key:

```powershell
.\.venv\Scripts\python.exe scripts\check_gemini.py
```

4. Test a tiny live API call:

```powershell
.\.venv\Scripts\python.exe scripts\check_gemini.py --call
```

5. In Streamlit, choose `Cloud reasoning - Gemini 3.5 Flash`, then click `Apply runtime settings`.

If Streamlit was already running when you edited `.env`, clicking `Apply runtime settings` should reload the key. Restarting Streamlit is still fine when in doubt.

### Free-Tier Friendly Model Choices

The sidebar includes:

- `Cloud reasoning - Gemini 3.5 Flash`: uses `gemini-3.5-flash`.
- `Cloud efficient - Gemini 3.1 Flash-Lite`: uses `gemini-3.1-flash-lite`, which is usually better for free-tier experimentation.
- `Hybrid quality check - Ollama draft + Gemini`: uses local Ollama for the main answer and Gemini 3.1 Flash-Lite only as the Checker agent.

If Gemini says quota or rate limit exceeded, switch to `Cloud efficient - Gemini 3.1 Flash-Lite`, reduce `Evidence chunks`, turn off `Run Checker agent`, or use the hybrid profile. The app also attempts an Ollama fallback when Gemini fails and Ollama is reachable.

### Ollama GPU Toggle

The `Prefer Ollama GPU acceleration` toggle asks Ollama to use GPU layers when supported. It does not install CUDA, ROCm, drivers, or a GPU-enabled Ollama build. Ollama often auto-detects GPU even when the toggle is off.

### Uploaded Finance Chart Images

The `Analyze uploaded charts/images with Gemini` toggle uses Gemini vision to create a concise, searchable summary for uploaded finance charts, tables, dashboards, and statement screenshots. Keep it off when preserving Gemini quota matters. OCR/metadata ingestion still works without it.

## Qdrant Snapshot Import

The Qdrant snapshot is not required for the app. It is only an optional way to import a larger external financial-docs corpus.

The slow part happens after export, when the app indexes exported markdown files into Chroma. Each file must be loaded, split into chunks, embedded, and saved locally.

### Recommended Demo Workflow

1. Start Qdrant:

```powershell
.\scripts\run_qdrant.bat
```

2. Restore the snapshot:

```powershell
.\.venv\Scripts\python.exe scripts\qdrant_snapshot_bridge.py restore --qdrant-url http://localhost:6333 --collection financial_docs
```

3. Export only a demo-sized subset:

```powershell
.\.venv\Scripts\python.exe scripts\qdrant_snapshot_bridge.py export --qdrant-url http://localhost:6333 --collection financial_docs --max-points 500
```

4. Open Streamlit and use the sidebar:

- Filter exported docs by filename/path, for example `amazon 2024 10-q`.
- Choose a small batch size, such as 25 or 50.
- Click `Index next batch`.

Avoid indexing thousands of exported files in one click on a laptop.

### If You Need The Whole Corpus

Use smaller repeated batches and keep Ollama running. Full-corpus indexing can take a long time because local embeddings are computed on your machine. It is normal for the first full index build to be much slower than asking questions afterward.

### Faster But Lower-Quality Preview

For quick UI testing, switch `Embeddings` to `hash` before indexing. This is fast and deterministic, but semantic retrieval quality is lower than Ollama `nomic-embed-text`.
