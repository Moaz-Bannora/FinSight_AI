"""Model profile presets for the presentation fork."""

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
    description: str


MODEL_PROFILES: dict[str, ModelProfile] = {
    "Ollama Llama 3.2 3B (local)": ModelProfile(
        label="Ollama Llama 3.2 3B (local)",
        llm_provider="ollama",
        chat_model="llama3.2:3b",
        embedding_model="nomic-embed-text",
        embedding_provider="ollama",
        temperature=0.2,
        description="Main local profile. Runs through Ollama and keeps the project usable without cloud generation.",
    ),
    "Gemini 3.1 Flash-Lite (cloud)": ModelProfile(
        label="Gemini 3.1 Flash-Lite (cloud)",
        llm_provider="gemini",
        chat_model="gemini-3.1-flash-lite",
        embedding_model="nomic-embed-text",
        embedding_provider="ollama",
        temperature=0.2,
        description="Cloud profile for faster Gemini answers when a private API key is configured.",
    ),
    "Hybrid: Ollama 3B draft + Gemini check": ModelProfile(
        label="Hybrid: Ollama 3B draft + Gemini check",
        llm_provider="hybrid_local_gemini_checker",
        chat_model="llama3.2:3b",
        embedding_model="nomic-embed-text",
        embedding_provider="ollama",
        temperature=0.2,
        description="Ollama drafts the answer locally, then Gemini Flash-Lite reviews it when configured.",
    ),
}


DEFAULT_PROFILE_LABEL = "Ollama Llama 3.2 3B (local)"


def get_profile(label: str) -> ModelProfile:
    return MODEL_PROFILES.get(label, MODEL_PROFILES[DEFAULT_PROFILE_LABEL])
