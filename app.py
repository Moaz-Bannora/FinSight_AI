"""Streamlit UI for Finance Docs Insights."""

from __future__ import annotations

import re
import time
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import streamlit as st

from src.agents import FinanceAssistant
from src.config import (
    DEFAULT_CHAT_MODEL,
    DEFAULT_EMBED_MODEL,
    EXTERNAL_DOCS_DIR,
    SAMPLE_DOCS_DIR,
    UPLOADS_DIR,
    ensure_project_dirs,
)
from src.llm import LocalLLM
from src.model_profiles import get_profile
from src.rag import FinanceRAG


ensure_project_dirs()


APP_NAME = "Finance Docs Insights"
MAX_UPLOAD_MB = 512
UPLOAD_TYPES = ["pdf", "docx", "txt", "md", "csv", "png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"]
VISIBLE_PROFILE_LABELS = [
    "Ollama fast",
    "Ollama finance balanced",
    "Ollama long-context",
    "Gemini API",
]
DEFAULT_PROFILE_LABEL = "Ollama fast"


def safe_filename(filename: str) -> str:
    """Return a filesystem-safe upload filename."""

    name = Path(filename).name
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "_", name).strip(" .")
    return cleaned or f"uploaded_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def save_uploaded_files(uploaded_files) -> list[Path]:
    """Persist Streamlit UploadedFile objects to the local uploads folder."""

    saved_paths: list[Path] = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for uploaded_file in uploaded_files:
        size_mb = uploaded_file.size / (1024 * 1024)
        if size_mb > MAX_UPLOAD_MB:
            raise ValueError(f"{uploaded_file.name} is {size_mb:.1f} MB, above the {MAX_UPLOAD_MB} MB limit.")

        target = UPLOADS_DIR / f"{timestamp}_{safe_filename(uploaded_file.name)}"
        target.write_bytes(uploaded_file.getbuffer())
        saved_paths.append(target)
    return saved_paths


def get_assistant(
    model_name: str,
    llm_provider: str,
    offline_demo: bool,
    embedding_provider: str,
    embedding_model: str,
    temperature: float,
) -> FinanceAssistant:
    rag = FinanceRAG(embedding_provider=embedding_provider, embedding_model=embedding_model)
    llm = LocalLLM(model_name=model_name, provider_name=llm_provider, offline_demo=offline_demo, temperature=temperature)
    return FinanceAssistant(rag=rag, llm=llm)


def show_processing_panel(slot, label: str) -> None:
    slot.markdown(
        f"""
        <div class="inline-processing" role="status" aria-live="polite">
          <span class="processing-spinner"></span>
          <span class="processing-copy">
            <span class="processing-label">{label}</span>
            <span class="processing-subline">Retrieving evidence, reading the file, and checking the answer</span>
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def clean_answer_for_display(answer: str) -> str:
    cleaner = getattr(FinanceAssistant, "clean_answer_text", None)
    if callable(cleaner):
        return cleaner(answer)
    return answer


def render_assistant_response(response) -> None:
    st.markdown(clean_answer_for_display(response.answer))

    if response.tool_results:
        with st.expander("Tool results"):
            for tool in response.tool_results:
                st.markdown(tool.to_markdown())

    if response.sources:
        with st.expander("Retrieved sources"):
            for source in response.sources:
                st.write(source.citation())
                st.caption(source.text[:900])

    with st.expander("Agent trace"):
        for step in response.trace:
            st.write(f"{step.role}: {step.summary}")


def append_assistant_response(response) -> None:
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response.answer,
            "sources": [source.citation() for source in response.sources],
            "trace": [f"{step.role}: {step.summary}" for step in response.trace],
        }
    )


st.set_page_config(
    page_title=APP_NAME,
    page_icon="FD",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      [data-testid="stDeployButton"],
      [data-testid="stAppDeployButton"],
      [data-testid="stStatusWidget"],
      [data-testid="stDecoration"],
      .stDeployButton,
      .stAppDeployButton,
      button[aria-label="Deploy"],
      button[title="Deploy"],
      a[href*="share.streamlit.io"] {
        display: none !important;
        visibility: hidden !important;
      }
      [data-testid="stToolbar"] [data-testid="stStatusWidget"],
      [data-testid="stToolbar"] [data-testid="stDeployButton"],
      [data-testid="stToolbar"] [data-testid="stAppDeployButton"] {
        display: none !important;
        visibility: hidden !important;
      }
      [data-testid="stSidebarHeader"] {
        min-height: 0 !important;
        height: 0 !important;
        padding: 0 !important;
      }
      [data-testid="stSidebarCollapseButton"],
      button[aria-label="Close sidebar"],
      button[aria-label="Open sidebar"] {
        transform: translateY(10px) !important;
      }
      [data-testid="stSidebarContent"] {
        padding-top: 0 !important;
      }
      .inline-processing {
        display: inline-flex;
        align-items: center;
        gap: 12px;
        max-width: min(620px, 100%);
        margin: 6px 0 14px 0;
        padding: 12px 14px;
        border: 1px solid rgba(23, 92, 70, 0.22);
        border-radius: 8px;
        background: #f7fbf8;
        color: #0b3d2e;
        box-shadow: 0 6px 18px rgba(13, 31, 24, 0.10);
        font-size: 0.92rem;
      }
      .processing-spinner {
        flex: 0 0 auto;
        width: 18px;
        height: 18px;
        border: 2px solid rgba(17, 88, 64, 0.22);
        border-top-color: #0f6b4f;
        border-radius: 999px;
        animation: finance-insights-spin 0.8s linear infinite;
      }
      .processing-copy {
        display: flex;
        flex-direction: column;
        gap: 2px;
        line-height: 1.25;
      }
      .processing-label {
        font-weight: 700;
      }
      .processing-subline {
        color: #52615b;
        font-size: 0.80rem;
      }
      @keyframes finance-insights-spin {
        to { transform: rotate(360deg); }
      }
      .runtime-note {
        color: #52615b;
        font-size: 0.82rem;
      }
      .stop-response button {
        border-color: rgba(167, 43, 43, 0.35) !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

if "messages" not in st.session_state:
    st.session_state.messages = []

if "executor" not in st.session_state:
    st.session_state.executor = ThreadPoolExecutor(max_workers=2)

if "pending_generation" not in st.session_state:
    st.session_state.pending_generation = None

if "assistant" not in st.session_state:
    default_profile = get_profile(DEFAULT_PROFILE_LABEL)
    st.session_state.assistant = get_assistant(
        default_profile.chat_model,
        llm_provider=default_profile.llm_provider,
        offline_demo=False,
        embedding_provider=default_profile.embedding_provider,
        embedding_model=default_profile.embedding_model,
        temperature=default_profile.temperature,
    )

if "ingested_files" not in st.session_state:
    st.session_state.ingested_files = []


with st.sidebar:
    st.title(APP_NAME)

    with st.expander("Answer setup", expanded=True):
        mode = st.selectbox(
            "Mode",
            [
                "Company Health Analysis",
                "Finance Study Assistant",
                "Research Paper Explainer",
                "General Document Q&A",
            ],
            index=3,
        )
        top_k = st.slider(
            "Evidence chunks",
            min_value=2,
            max_value=8,
            value=5,
            step=1,
            help=(
                "How many retrieved text chunks are sent to the model as evidence. "
                "Higher values give more context but can add noise and make answers slower."
            ),
        )
        use_rag = st.toggle("Use RAG", value=True)
        use_tools = st.toggle("Use finance tools", value=True)
        use_checker = st.toggle("Use Checker agent", value=True)

    with st.expander("Documents", expanded=True):
        if st.button("Load sample finance docs", use_container_width=True):
            with st.spinner("Indexing sample documents..."):
                count = st.session_state.assistant.rag.ingest_directory(SAMPLE_DOCS_DIR, reset=True)
            st.session_state.ingested_files = ["sample_docs"]
            st.success(f"Loaded {count} chunks.")

        exported_docs = [path for path in EXTERNAL_DOCS_DIR.rglob("*") if path.is_file()]
        if exported_docs and st.button("Load exported financial docs", use_container_width=True):
            with st.spinner("Indexing exported SEC-style financial documents..."):
                count = st.session_state.assistant.rag.ingest_directory(EXTERNAL_DOCS_DIR, reset=True)
            st.session_state.ingested_files = [f"external_financial_docs ({len(exported_docs)} files)"]
            st.success(f"Loaded {count} chunks.")
        elif not exported_docs:
            st.caption("No exported financial docs found yet.")

        uploaded_files = st.file_uploader(
            "Upload documents or images",
            type=UPLOAD_TYPES,
            accept_multiple_files=True,
        )

        if uploaded_files and st.button("Ingest uploads", use_container_width=True):
            try:
                with st.spinner("Saving uploaded files..."):
                    saved_paths = save_uploaded_files(uploaded_files)
                with st.spinner("Extracting, sectioning, and indexing..."):
                    count = st.session_state.assistant.rag.ingest_files(saved_paths)

                st.session_state.ingested_files = [path.name for path in saved_paths]
                if count > 0:
                    st.success(f"Ingested {count} chunks from {len(saved_paths)} file(s).")
                else:
                    st.warning("The file was saved, but no searchable chunks were indexed.")
            except Exception as exc:
                st.error(f"Upload ingestion failed: {exc}")
                st.info("For image text extraction, install OCR support with `requirements-ocr.txt` and Tesseract.")

        if st.session_state.ingested_files:
            st.markdown("**Indexed files**")
            for filename in st.session_state.ingested_files:
                st.caption(filename)

        if st.button("Clear vector store", use_container_width=True):
            st.session_state.assistant.rag.reset()
            st.session_state.messages = []
            st.session_state.ingested_files = []
            st.success("Cleared documents and chat.")

    with st.expander("Model settings", expanded=False):
        profile_label = st.selectbox(
            "Profile",
            VISIBLE_PROFILE_LABELS,
            index=VISIBLE_PROFILE_LABELS.index(DEFAULT_PROFILE_LABEL),
        )
        profile = get_profile(profile_label)
        st.caption(profile.description)

        profile_key = re.sub(r"[^A-Za-z0-9_]+", "_", profile_label.lower())
        model_name = st.text_input(
            "Chat model",
            value=profile.chat_model if not profile.offline_demo else DEFAULT_CHAT_MODEL,
            key=f"chat_model_{profile_key}",
        )
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=0.8,
            value=float(profile.temperature),
            step=0.05,
            help=(
                "Controls answer randomness. Lower values are more consistent and better for finance; "
                "higher values can be more creative but may drift."
            ),
            key=f"temperature_{profile_key}",
        )
        embedding_provider = st.selectbox(
            "Embeddings",
            ["hash", "ollama"],
            index=0 if profile.embedding_provider == "hash" else 1,
            key=f"embedding_provider_{profile_key}",
        )
        embedding_model = st.text_input(
            "Embedding model",
            value=profile.embedding_model if profile.embedding_model != "hash-384" else DEFAULT_EMBED_MODEL,
            key=f"embedding_model_{profile_key}",
        )

    st.divider()
    st.caption("Runtime")
    offline_demo = st.toggle("Offline demo mode", value=False, key=f"offline_demo_{profile_key}")

    if st.button("Apply runtime settings", use_container_width=True):
        st.session_state.assistant = get_assistant(
            model_name=model_name,
            llm_provider=profile.llm_provider,
            offline_demo=offline_demo,
            embedding_provider=embedding_provider,
            embedding_model=embedding_model,
            temperature=temperature,
        )
        st.success(f"Runtime: {st.session_state.assistant.llm.provider}")

    st.caption(f"Provider: {st.session_state.assistant.llm.provider}")
    if getattr(st.session_state.assistant.llm, "status_message", ""):
        st.caption(st.session_state.assistant.llm.status_message)
    st.caption(f"RAG store: {'LangChain/Chroma' if st.session_state.assistant.rag.langchain_enabled else 'Fallback'}")


st.title(APP_NAME)
st.caption("Local finance document analyzer and study guide. Educational use only, not personalized financial advice.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        content = (
            clean_answer_for_display(message["content"])
            if message["role"] == "assistant"
            else message["content"]
        )
        st.markdown(content)
        if message.get("sources"):
            with st.expander("Sources"):
                for source in message["sources"]:
                    st.write(source)
        if message.get("trace"):
            with st.expander("Agent trace"):
                for step in message["trace"]:
                    st.write(step)


is_generating = st.session_state.pending_generation is not None
question = st.chat_input(
    "Ask about a finance document, ratio, company health, research paper, or uploaded image...",
    disabled=is_generating,
)

if question and st.session_state.pending_generation is None:
    st.session_state.messages.append({"role": "user", "content": question})
    future = st.session_state.executor.submit(
        st.session_state.assistant.answer,
        question,
        mode,
        use_rag,
        use_tools,
        use_checker,
        top_k,
    )
    st.session_state.pending_generation = {
        "id": datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
        "future": future,
        "question": question,
    }
    st.rerun()

pending = st.session_state.pending_generation
if pending is not None:
    future: Future = pending["future"]
    with st.chat_message("assistant"):
        processing_slot = st.empty()
        show_processing_panel(processing_slot, "Reading sources and preparing answer")

        if st.button("Stop response", key=f"stop_{pending['id']}", type="secondary"):
            future.cancel()
            st.session_state.pending_generation = None
            processing_slot.empty()
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": "Response stopped before completion.",
                    "sources": [],
                    "trace": [],
                }
            )
            st.rerun()

        if future.done():
            processing_slot.empty()
            try:
                response = future.result()
            except Exception as exc:
                st.error(f"Answer generation failed: {exc}")
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": f"Answer generation failed: {exc}",
                        "sources": [],
                        "trace": [],
                    }
                )
            else:
                render_assistant_response(response)
                append_assistant_response(response)
            st.session_state.pending_generation = None
        else:
            time.sleep(0.5)
            st.rerun()

