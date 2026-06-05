"""Non-secret Gemini setup checker for Finance Docs Insights."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(PROJECT_ROOT / ".env", override=True)
    except Exception:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Gemini API setup without printing secrets.")
    parser.add_argument("--call", action="store_true", help="Make a tiny live Gemini API call.")
    parser.add_argument("--model", default="gemini-3.1-flash-lite", help="Gemini model to test.")
    args = parser.parse_args()

    load_env()
    google_key = os.getenv("GOOGLE_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    key = google_key or gemini_key

    print(f".env exists: {(PROJECT_ROOT / '.env').exists()}")
    print(f"GOOGLE_API_KEY set: {bool(google_key)}")
    print(f"GEMINI_API_KEY set: {bool(gemini_key)}")
    if google_key and gemini_key:
        print("Both key names are set. The app uses GOOGLE_API_KEY first.")

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except Exception as exc:
        print(f"langchain-google-genai installed: False ({exc})")
        print("Install with: python -m pip install -r requirements.txt")
        raise SystemExit(1)

    print("langchain-google-genai installed: True")

    if not key:
        print("No Gemini key found. Add GOOGLE_API_KEY=your_key_here to a private .env file.")
        raise SystemExit(1)

    if not args.call:
        print("Local setup looks ready. Add --call to test the live Gemini API.")
        return

    try:
        chat = ChatGoogleGenerativeAI(model=args.model, temperature=0, api_key=key)
        response = chat.invoke("Reply with exactly: OK")
    except TypeError:
        chat = ChatGoogleGenerativeAI(model=args.model, temperature=0, google_api_key=key)
        response = chat.invoke("Reply with exactly: OK")
    except Exception as exc:
        print(f"Live Gemini call failed: {exc}")
        raise SystemExit(1)

    print(f"Live Gemini call succeeded with {args.model}: {_message_text(response)[:80]}")


def _message_text(message) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("text"):
                parts.append(str(item["text"]))
            elif isinstance(item, str):
                parts.append(item)
        if parts:
            return "\n".join(parts).strip()
    return str(content).strip()


if __name__ == "__main__":
    main()
