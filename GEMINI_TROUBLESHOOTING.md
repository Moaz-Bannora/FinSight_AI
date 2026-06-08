# Gemini Troubleshooting

This presentation fork has one Gemini profile and one hybrid profile that can use Gemini as the Checker agent.

## API Key

The key from Google AI Studio is the correct Gemini API key.

Use one of these names in a private `.env` file:

```env
GOOGLE_API_KEY=your_google_ai_studio_key_here
```

or:

```env
GEMINI_API_KEY=your_google_ai_studio_key_here
```

Prefer `GOOGLE_API_KEY` because LangChain commonly expects it.

Do not put a real key in `.env.example`.

## Setup Check

Install project dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Check local setup without printing the key:

```powershell
.\.venv\Scripts\python.exe scripts\check_gemini.py
```

Make a tiny live API call:

```powershell
.\.venv\Scripts\python.exe scripts\check_gemini.py --call
```

## In The App

Choose one of these profiles:

- `Gemini 3.1 Flash-Lite (cloud)`
- `Hybrid: Ollama 3B draft + Gemini check`

Then click `Apply runtime settings`.

If Gemini quota is exceeded, reduce `Evidence chunks`, turn off `Run Checker agent`, or switch to `Ollama Llama 3.2 3B (local)`.

## Image Analysis

The `Analyze uploaded charts/images with Gemini` toggle uses Gemini vision to create a searchable summary for uploaded finance charts, dashboards, tables, and screenshots. Keep it off when preserving Gemini quota matters.
