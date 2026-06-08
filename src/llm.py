"""LangChain model client for Ollama and Gemini."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .config import DEFAULT_CHAT_MODEL, DEFAULT_LLM_PROVIDER, OLLAMA_BASE_URL, get_google_api_key


try:
    from langchain_ollama import ChatOllama

    LANGCHAIN_OLLAMA_AVAILABLE = True
except Exception:
    ChatOllama = None
    LANGCHAIN_OLLAMA_AVAILABLE = False

try:
    from langchain_google_genai import ChatGoogleGenerativeAI

    LANGCHAIN_GOOGLE_GENAI_AVAILABLE = True
except Exception:
    ChatGoogleGenerativeAI = None
    LANGCHAIN_GOOGLE_GENAI_AVAILABLE = False


@dataclass
class GenerationResult:
    text: str
    model_name: str
    provider: str


class LocalLLM:
    """Generate text with the configured real model provider."""

    def __init__(
        self,
        model_name: str = DEFAULT_CHAT_MODEL,
        provider_name: str = DEFAULT_LLM_PROVIDER,
        base_url: str = OLLAMA_BASE_URL,
        temperature: float = 0.2,
        prefer_ollama_gpu: bool = False,
    ) -> None:
        self.model_name = model_name
        self.provider_name = provider_name.lower().strip()
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.prefer_ollama_gpu = prefer_ollama_gpu
        self.chat: Any | None = None
        self.status_message = ""

        if self.provider_name == "gemini":
            self._init_gemini()
        else:
            self._init_ollama()

    @property
    def provider(self) -> str:
        if self.chat is None:
            return "model-unavailable"
        return f"langchain-{self.provider_name}"

    def _init_ollama(self) -> None:
        if not LANGCHAIN_OLLAMA_AVAILABLE:
            self.status_message = "langchain-ollama is not installed. Run `python -m pip install -r requirements.txt`."
            return
        if not self.is_ollama_running():
            self.status_message = f"Ollama is not reachable at {self.base_url}. Start Ollama and pull `{self.model_name}`."
            return
        self.provider_name = "ollama"
        self.chat = self._make_ollama_chat(self.model_name)
        if self.prefer_ollama_gpu:
            self.status_message = "Ollama GPU preference is enabled. Ollama will use GPU layers when supported."

    def _make_ollama_chat(self, model_name: str) -> Any:
        kwargs = {
            "model": model_name,
            "base_url": self.base_url,
            "temperature": self.temperature,
        }
        if self.prefer_ollama_gpu:
            kwargs["num_gpu"] = -1
        return ChatOllama(**kwargs)

    def _init_gemini(self) -> None:
        if not LANGCHAIN_GOOGLE_GENAI_AVAILABLE:
            self.status_message = "langchain-google-genai is not installed. Run `python -m pip install -r requirements.txt`."
            return
        google_api_key = get_google_api_key()
        if not google_api_key:
            self.status_message = "GOOGLE_API_KEY/GEMINI_API_KEY is not set in a private `.env` file."
            return

        self.provider_name = "gemini"
        try:
            self.chat = ChatGoogleGenerativeAI(model=self.model_name, temperature=self.temperature, api_key=google_api_key)
        except TypeError:
            try:
                self.chat = ChatGoogleGenerativeAI(
                    model=self.model_name,
                    temperature=self.temperature,
                    google_api_key=google_api_key,
                )
            except Exception as exc:
                self.status_message = f"Gemini initialization failed: {self._short_error(exc)}"
        except Exception as exc:
            self.status_message = f"Gemini initialization failed: {self._short_error(exc)}"

    def is_ollama_running(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=3) as response:
                return response.status == 200
        except (urllib.error.URLError, TimeoutError, OSError):
            return False

    def list_models(self) -> list[str]:
        try:
            with urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=3) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return [item["name"] for item in payload.get("models", [])]
        except Exception:
            return []

    def generate(self, system_prompt: str, user_prompt: str) -> GenerationResult:
        if self.chat is None:
            return GenerationResult(self._unavailable_message(), self.model_name, self.provider)

        try:
            message = self.chat.invoke([("system", system_prompt), ("human", user_prompt)])
            return GenerationResult(self._message_text(message), self.model_name, self.provider)
        except Exception as exc:
            self.status_message = f"{self.provider_name} call failed: {self._short_error(exc)}"
            return GenerationResult(self._unavailable_message(), self.model_name, self.provider)

    def _unavailable_message(self) -> str:
        details = self.status_message or "No model provider is available."
        return (
            "The selected model is not available, so I cannot generate a real model answer yet.\n\n"
            f"**Runtime Status**\n{details}\n\n"
            "**How To Fix**\n"
            "- For Ollama: start Ollama and pull `llama3.2:3b`.\n"
            "- For Gemini: set `GOOGLE_API_KEY` or `GEMINI_API_KEY` in a private `.env` file.\n"
            "- Then click `Apply runtime settings` in the sidebar."
        )

    @staticmethod
    def _short_error(exc: Exception) -> str:
        message = re.sub(r"\s+", " ", str(exc)).strip()
        if not message:
            return exc.__class__.__name__
        return message[:180]

    @staticmethod
    def _message_text(message: Any) -> str:
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
