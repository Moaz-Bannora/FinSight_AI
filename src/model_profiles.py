"""Model profile presets for local and future model usage."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelProfile:
    label: str
    llm_provider: str
    chat_model: str
    embedding_model: str
    embedding_provider: str
    temperature: float
    offline_demo: bool
    description: str


MODEL_PROFILES: dict[str, ModelProfile] = {
    "Ollama fast": ModelProfile(
        label="Ollama fast",
        llm_provider="ollama",
        chat_model="llama3.2:3b",
        embedding_model="nomic-embed-text",
        embedding_provider="ollama",
        temperature=0.2,
        offline_demo=False,
        description="Fast local chat model for demos and short document questions.",
    ),
    "Ollama finance balanced": ModelProfile(
        label="Ollama finance balanced",
        llm_provider="ollama",
        chat_model="qwen2.5:7b",
        embedding_model="nomic-embed-text",
        embedding_provider="ollama",
        temperature=0.15,
        offline_demo=False,
        description="Better reasoning profile when your machine can run a 7B local model.",
    ),
    "Ollama long-context": ModelProfile(
        label="Ollama long-context",
        llm_provider="ollama",
        chat_model="llama3.1:8b",
        embedding_model="nomic-embed-text",
        embedding_provider="ollama",
        temperature=0.15,
        offline_demo=False,
        description="Useful for longer annual reports when hardware allows it.",
    ),
    "Gemini API": ModelProfile(
        label="Gemini API",
        llm_provider="gemini",
        chat_model="gemini-2.5-flash",
        embedding_model="nomic-embed-text",
        embedding_provider="ollama",
        temperature=0.2,
        offline_demo=False,
        description="Optional cloud LLM profile. Requires `langchain-google-genai` and `GOOGLE_API_KEY`.",
    ),
}


def get_profile(label: str) -> ModelProfile:
    return MODEL_PROFILES.get(label, MODEL_PROFILES["Ollama fast"])
