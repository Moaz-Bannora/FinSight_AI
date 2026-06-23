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
    SUPPORTED_EXTENSIONS,
    UPLOADS_DIR,
    ensure_project_dirs,
    gemini_env_status,
)
from src.llm import LANGCHAIN_GOOGLE_GENAI_AVAILABLE, LocalLLM
from src.market_data import YFINANCE_AVAILABLE
from src.model_profiles import MODEL_PROFILES, get_profile
from src.rag import FinanceRAG


ensure_project_dirs()


APP_NAME = "Finance Docs Insights"
MAX_UPLOAD_MB = 512
UPLOAD_TYPES = ["pdf", "docx", "txt", "md", "csv", "png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"]
VISIBLE_PROFILE_LABELS = list(MODEL_PROFILES)
DEFAULT_PROFILE_LABEL = "Local fast - Ollama Llama 3.2 3B"


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


def list_supported_files(directory: Path) -> list[Path]:
    """Return supported files in a stable order for repeatable batch indexing."""

    return sorted(
        [path for path in directory.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS],
        key=lambda path: str(path).lower(),
    )


def filter_files(paths: list[Path], query: str) -> list[Path]:
    """Filter paths by simple filename/path tokens entered in the sidebar."""

    tokens = [token.strip().lower() for token in query.split() if token.strip()]
    if not tokens:
        return paths
    return [path for path in paths if all(token in str(path).lower() for token in tokens)]


def get_assistant(
    model_name: str,
    llm_provider: str,
    offline_demo: bool,
    embedding_provider: str,
    embedding_model: str,
    temperature: float,
    prefer_ollama_gpu: bool = False,
    analyze_images: bool = False,
) -> FinanceAssistant:
    rag = FinanceRAG(
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
        analyze_images=analyze_images,
    )
    if llm_provider == "hybrid_local_gemini_checker":
        llm = LocalLLM(
            model_name=model_name,
            provider_name="ollama",
            offline_demo=offline_demo,
            temperature=temperature,
            prefer_ollama_gpu=prefer_ollama_gpu,
        )
        checker_llm = LocalLLM(
            model_name="gemini-3.1-flash-lite",
            provider_name="gemini",
            offline_demo=offline_demo,
            temperature=temperature,
            fallback_model_name=model_name,
            prefer_ollama_gpu=prefer_ollama_gpu,
        )
        return FinanceAssistant(rag=rag, llm=llm, checker_llm=checker_llm)

    llm = LocalLLM(
        model_name=model_name,
        provider_name=llm_provider,
        offline_demo=offline_demo,
        temperature=temperature,
        fallback_model_name=DEFAULT_CHAT_MODEL,
        prefer_ollama_gpu=prefer_ollama_gpu,
    )
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

if "external_docs_cursor" not in st.session_state:
    st.session_state.external_docs_cursor = 0

if "external_docs_last_filter" not in st.session_state:
    st.session_state.external_docs_last_filter = ""

if "image_analysis_enabled" not in st.session_state:
    st.session_state.image_analysis_enabled = False

if "prefer_ollama_gpu_enabled" not in st.session_state:
    st.session_state.prefer_ollama_gpu_enabled = False


with st.sidebar:
    st.title(APP_NAME)
    st.caption("Document RAG, finance tools, and optional market context.")

    with st.expander("1. Workflow", expanded=True):
        mode = st.selectbox(
            "Answer mode",
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
        use_rag = st.toggle(
            "Retrieve document evidence",
            value=True,
            help="Search indexed files and pass the most relevant chunks to the model.",
        )
        use_tools = st.toggle(
            "Use finance calculators",
            value=True,
            help="Run deterministic ratio and NPV tools when numbers are present.",
        )
        use_market_data = st.toggle(
            "Use Yahoo market data",
            value=False,
            help=(
                "Read-only external lookup for stock quotes and market metrics. "
                "Data may be delayed and is not investment advice."
            ),
        )
        if use_market_data and not YFINANCE_AVAILABLE:
            st.warning("Install `yfinance` from requirements.txt before using Yahoo market data.")
        use_checker = st.toggle(
            "Run Checker agent",
            value=True,
            help="Review the draft answer for unsupported claims, arithmetic issues, and safety wording.",
        )

    with st.expander("2. Documents and indexing", expanded=True):
        if st.button("Index sample finance docs", use_container_width=True):
            with st.spinner("Indexing sample documents..."):
                count = st.session_state.assistant.rag.ingest_directory(SAMPLE_DOCS_DIR, reset=True)
            st.session_state.ingested_files = ["sample_docs"]
            st.success(f"Loaded {count} chunks.")

        exported_docs = list_supported_files(EXTERNAL_DOCS_DIR)
        if exported_docs:
            st.markdown("**Exported financial docs**")
            external_filter = st.text_input(
                "Filter exported docs",
                value=st.session_state.external_docs_last_filter,
                placeholder="amazon 2024 10-q, apple, risk, table...",
                help="Optional. Matches words in exported filenames and folders before indexing.",
            )
            if external_filter != st.session_state.external_docs_last_filter:
                st.session_state.external_docs_last_filter = external_filter
                st.session_state.external_docs_cursor = 0

            filtered_docs = filter_files(exported_docs, external_filter)
            batch_size = st.selectbox(
                "External docs batch size",
                [25, 50, 100, 250, 500],
                index=1,
                help="Smaller batches are easier to cancel and safer for laptops. More files take longer to embed.",
            )
            reset_before_external = st.checkbox(
                "Reset vector store before first external batch",
                value=True,
                help="Keep enabled when you want the exported financial docs to replace previously indexed docs.",
            )

            if st.session_state.external_docs_cursor > len(filtered_docs):
                st.session_state.external_docs_cursor = 0

            start = st.session_state.external_docs_cursor
            end = min(start + batch_size, len(filtered_docs))
            next_batch = filtered_docs[start:end]
            st.caption(
                f"{len(filtered_docs)} matching files out of {len(exported_docs)} exported files. "
                f"Next batch: {start + 1 if next_batch else 0}-{end}."
            )

            col_index, col_reset = st.columns(2)
            with col_index:
                if st.button("Index next batch", use_container_width=True, disabled=not next_batch):
                    if start == 0 and reset_before_external:
                        st.session_state.assistant.rag.reset()
                    with st.spinner(f"Indexing {len(next_batch)} exported file(s)..."):
                        count = st.session_state.assistant.rag.ingest_files(next_batch)
                    st.session_state.external_docs_cursor = end
                    st.session_state.ingested_files = [
                        f"external_financial_docs batch {start + 1}-{end} of {len(filtered_docs)}"
                    ]
                    st.success(f"Indexed {count} chunks from {len(next_batch)} file(s).")
            with col_reset:
                if st.button("Reset external progress", use_container_width=True):
                    st.session_state.external_docs_cursor = 0
                    st.success("External indexing progress reset.")
        else:
            st.caption("No exported financial docs found yet.")

        uploaded_files = st.file_uploader(
            "Upload documents or images",
            type=UPLOAD_TYPES,
            accept_multiple_files=True,
        )

        if uploaded_files and st.button("Ingest uploads", use_container_width=True):
            try:
                st.session_state.assistant.rag.analyze_images = bool(st.session_state.image_analysis_enabled)
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

    with st.expander("3. Model profile", expanded=True):
        profile_label = st.selectbox(
            "Runtime profile",
            VISIBLE_PROFILE_LABELS,
            index=VISIBLE_PROFILE_LABELS.index(DEFAULT_PROFILE_LABEL),
        )
        profile = get_profile(profile_label)
        st.caption(profile.description)
        if profile.llm_provider in {"gemini", "hybrid_local_gemini_checker"}:
            gemini_status = gemini_env_status()
            if not LANGCHAIN_GOOGLE_GENAI_AVAILABLE:
                st.warning("Gemini package missing. Run `python -m pip install -r requirements.txt`.")
            elif not gemini_status["any_key_set"]:
                st.warning("Gemini key not found. Put `GOOGLE_API_KEY=...` in a private `.env` file.")
            else:
                st.success("Gemini package and local API key are configured.")
            if gemini_status["both_keys_set"]:
                st.caption("Both GOOGLE_API_KEY and GEMINI_API_KEY are set. The app uses GOOGLE_API_KEY first.")
            st.caption("Use `.env` for real keys. `.env.example` is only a safe template for GitHub.")

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

    with st.expander("4. Runtime options and status", expanded=False):
        offline_demo = False
        prefer_ollama_gpu = st.toggle(
            "Prefer Ollama GPU acceleration",
            value=False,
            help=(
                "Ollama normally auto-detects GPU. This passes a GPU-layer preference to Ollama when supported; "
                "it does not install GPU drivers."
            ),
            key="prefer_ollama_gpu_enabled",
        )
        analyze_images = st.toggle(
            "Analyze uploaded charts/images with Gemini",
            value=False,
            help=(
                "When a Gemini key is configured, uploaded images get a visual finance/chart summary indexed into RAG. "
                "Leave off to save Gemini quota."
            ),
            key="image_analysis_enabled",
        )

        if st.button("Apply runtime settings", use_container_width=True):
            st.session_state.assistant = get_assistant(
                model_name=model_name,
                llm_provider=profile.llm_provider,
                offline_demo=offline_demo,
                embedding_provider=embedding_provider,
                embedding_model=embedding_model,
                temperature=temperature,
                prefer_ollama_gpu=prefer_ollama_gpu,
                analyze_images=analyze_images,
            )
            st.success(f"Runtime: {st.session_state.assistant.provider_summary()}")

        st.caption(f"Provider: {st.session_state.assistant.provider_summary()}")
        if getattr(st.session_state.assistant.llm, "status_message", ""):
            st.caption(st.session_state.assistant.llm.status_message)
        if getattr(st.session_state.assistant, "checker_llm", None) is not st.session_state.assistant.llm:
            checker_status = getattr(st.session_state.assistant.checker_llm, "status_message", "")
            if checker_status:
                st.caption(f"Checker: {checker_status}")
        st.caption(f"RAG store: {'LangChain/Chroma' if st.session_state.assistant.rag.langchain_enabled else 'Fallback'}")


st.title(APP_NAME)
st.caption("Finance document intelligence workspace. Analytical support only, not personalized financial advice.")

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
        use_market_data,
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

