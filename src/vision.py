"""Optional Gemini vision support for uploaded finance images."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from .config import get_google_api_key


try:
    from langchain_core.messages import HumanMessage
    from langchain_google_genai import ChatGoogleGenerativeAI

    VISION_AVAILABLE = True
except Exception:
    HumanMessage = None
    ChatGoogleGenerativeAI = None
    VISION_AVAILABLE = False


def analyze_finance_image(file_path: Path, model_name: str = "gemini-3.1-flash-lite") -> tuple[str, str]:
    """Return a concise finance/chart description for an uploaded image."""

    if not VISION_AVAILABLE:
        return "", "vision_package_unavailable"

    api_key = get_google_api_key()
    if not api_key:
        return "", "vision_key_missing"

    mime_type = mimetypes.guess_type(file_path.name)[0] or "image/png"
    image_b64 = base64.b64encode(file_path.read_bytes()).decode("ascii")
    prompt = (
        "Analyze this uploaded finance-related image for a document assistant. "
        "If it is a chart, table, statement screenshot, dashboard, or financial form, extract the visible title, "
        "axes or labels, series names, numeric values, trends, outliers, and cautious financial insights. "
        "If it is not finance-related, briefly describe what is visible. "
        "Do not give personalized investment advice. Keep the answer concise and evidence-based."
    )

    content = [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": f"data:{mime_type};base64,{image_b64}"},
    ]

    try:
        chat = ChatGoogleGenerativeAI(model=model_name, temperature=0.1, api_key=api_key)
        response = chat.invoke([HumanMessage(content=content)])
    except TypeError:
        chat = ChatGoogleGenerativeAI(model=model_name, temperature=0.1, google_api_key=api_key)
        response = chat.invoke([HumanMessage(content=content)])
    except Exception as exc:
        return "", f"vision_failed: {str(exc)[:160]}"

    summary = _message_text(response)
    return summary, "vision_summary" if summary else "vision_empty"


def _message_text(message) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(str(text))
            elif isinstance(item, str):
                parts.append(item)
        if parts:
            return "\n".join(parts).strip()
    return str(content).strip()
