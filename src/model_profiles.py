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
    "Local fast - Ollama Llama 3.2 3B": ModelProfile(
        label="Local fast - Ollama Llama 3.2 3B",
        llm_provider="ollama",
        chat_model="llama3.2:3b",
        embedding_model="nomic-embed-text",
        embedding_provider="ollama",
        temperature=0.2,
        offline_demo=False,
        description="Fast local chat model for demos and short document questions.",
    ),
    "Local balanced - Ollama Qwen 2.5 7B": ModelProfile(
        label="Local balanced - Ollama Qwen 2.5 7B",
        llm_provider="ollama",
        chat_model="qwen2.5:7b",
        embedding_model="nomic-embed-text",
        embedding_provider="ollama",
        temperature=0.15,
        offline_demo=False,
        description="Better reasoning profile when your machine can run a 7B local model.",
    ),
    "Local long context - Ollama Llama 3.1 8B": ModelProfile(
        label="Local long context - Ollama Llama 3.1 8B",
        llm_provider="ollama",
        chat_model="llama3.1:8b",
        embedding_model="nomic-embed-text",
        embedding_provider="ollama",
        temperature=0.15,
        offline_demo=False,
        description="Useful for longer annual reports when hardware allows it.",
    ),
    "Cloud reasoning - Gemini 3.5 Flash": ModelProfile(
        label="Cloud reasoning - Gemini 3.5 Flash",
        llm_provider="gemini",
        chat_model="gemini-3.5-flash",
        embedding_model="nomic-embed-text",
        embedding_provider="ollama",
        temperature=0.2,
        offline_demo=False,
        description="Optional cloud LLM profile. Requires `langchain-google-genai` and `GOOGLE_API_KEY`.",
    ),
    "Cloud efficient - Gemini 3.1 Flash-Lite": ModelProfile(
        label="Cloud efficient - Gemini 3.1 Flash-Lite",
        llm_provider="gemini",
        chat_model="gemini-3.1-flash-lite",
        embedding_model="nomic-embed-text",
        embedding_provider="ollama",
        temperature=0.2,
        offline_demo=False,
        description="Quota-friendlier Gemini profile for free-tier testing and short finance questions.",
    ),
    "Hybrid quality check - Ollama draft + Gemini": ModelProfile(
        label="Hybrid quality check - Ollama draft + Gemini",
        llm_provider="hybrid_local_gemini_checker",
        chat_model="llama3.2:3b",
        embedding_model="nomic-embed-text",
        embedding_provider="ollama",
        temperature=0.2,
        offline_demo=False,
        description="Local Ollama drafts the answer, then Gemini Flash-Lite checks it when available.",
    ),
}


PROFILE_ALIASES: dict[str, str] = {
    "Ollama fast": "Local fast - Ollama Llama 3.2 3B",
    "Ollama finance balanced": "Local balanced - Ollama Qwen 2.5 7B",
    "Ollama long-context": "Local long context - Ollama Llama 3.1 8B",
    "Gemini API": "Cloud reasoning - Gemini 3.5 Flash",
    "Gemini Flash-Lite": "Cloud efficient - Gemini 3.1 Flash-Lite",
    "Hybrid local + Gemini checker": "Hybrid quality check - Ollama draft + Gemini",
}


def get_profile(label: str) -> ModelProfile:
    canonical_label = PROFILE_ALIASES.get(label, label)
    return MODEL_PROFILES.get(canonical_label, MODEL_PROFILES["Local fast - Ollama Llama 3.2 3B"])
