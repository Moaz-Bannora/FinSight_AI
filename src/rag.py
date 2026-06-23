"""LangChain-first RAG pipeline with a dependency-free fallback."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .financial_metadata import (
    extract_query_filters,
    infer_financial_metadata,
    metadata_filter_score,
    sanitize_metadata,
)
from .config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DEFAULT_EMBED_MODEL,
    DEFAULT_TOP_K,
    IMAGE_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
    VECTORSTORE_DIR,
)
from .vision import analyze_finance_image


try:
    from langchain_chroma import Chroma
    from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader
    from langchain_core.documents import Document
    from langchain_ollama import OllamaEmbeddings
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    LANGCHAIN_AVAILABLE = True
except Exception:
    Chroma = None
    Docx2txtLoader = None
    PyPDFLoader = None
    TextLoader = None
    Document = None
    OllamaEmbeddings = None
    RecursiveCharacterTextSplitter = None
    LANGCHAIN_AVAILABLE = False


@dataclass
class RetrievedChunk:
    text: str
    source: str
    page: int | None = None
    chunk_id: int | None = None
    score: float | None = None
    section: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def citation(self) -> str:
        page = f", page {self.page}" if self.page is not None else ""
        chunk = f", chunk {self.chunk_id}" if self.chunk_id is not None else ""
        section = f", {self.section}" if self.section else ""
        return f"{Path(self.source).name}{page}{chunk}{section}"


class LocalHashEmbeddings:
    """Small deterministic embedding model for offline smoke tests.

    This is not meant to replace semantic embeddings for the final demo. It keeps
    the project runnable on machines that have not installed Ollama embedding
    models or sentence-transformers yet.
    """

    def __init__(self, dimensions: int = 384):
        self.dimensions = dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_]+", text.lower())
        for token in tokens:
            digest = hashlib.md5(token.encode("utf-8")).hexdigest()
            index = int(digest[:8], 16) % self.dimensions
            sign = 1.0 if int(digest[8:10], 16) % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


class FinanceRAG:
    """Document ingestion, chunking, vector indexing, and retrieval."""

    def __init__(
        self,
        persist_dir: Path | str = VECTORSTORE_DIR,
        embedding_provider: str = "hash",
        embedding_model: str = DEFAULT_EMBED_MODEL,
        top_k: int = DEFAULT_TOP_K,
        analyze_images: bool = False,
        image_analysis_model: str = "gemini-3.1-flash-lite",
    ) -> None:
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.embedding_provider = embedding_provider
        self.embedding_model = embedding_model
        self.top_k = top_k
        self.analyze_images = analyze_images
        self.image_analysis_model = image_analysis_model
        self.vectorstore: Any | None = None
        self.fallback_chunks: list[RetrievedChunk] = []

        if LANGCHAIN_AVAILABLE:
            self.embeddings = self._build_embeddings()
            try:
                self.vectorstore = Chroma(
                    collection_name=self._collection_name(),
                    embedding_function=self.embeddings,
                    persist_directory=str(self.persist_dir),
                )
            except Exception:
                self.vectorstore = None
        else:
            self.embeddings = LocalHashEmbeddings()

    @property
    def langchain_enabled(self) -> bool:
        return bool(LANGCHAIN_AVAILABLE and self.vectorstore is not None)

    def _build_embeddings(self) -> Any:
        if self.embedding_provider == "ollama" and OllamaEmbeddings is not None:
            try:
                return OllamaEmbeddings(model=self.embedding_model)
            except Exception:
                return LocalHashEmbeddings()
        return LocalHashEmbeddings()

    def _collection_name(self) -> str:
        if self.embedding_provider == "ollama":
            suffix = re.sub(r"[^a-zA-Z0-9_]+", "_", self.embedding_model).strip("_").lower()
            return f"finance_documents_ollama_{suffix or 'default'}"
        dimensions = getattr(getattr(self, "embeddings", None), "dimensions", 384)
        return f"finance_documents_hash_{dimensions}"

    def reset(self) -> None:
        """Clear the vector store or fallback in-memory index."""

        self.fallback_chunks = []
        if self.langchain_enabled:
            try:
                self.vectorstore.delete_collection()
            except Exception:
                pass
            self.vectorstore = Chroma(
                collection_name=self._collection_name(),
                embedding_function=self.embeddings,
                persist_directory=str(self.persist_dir),
            )

    def ingest_directory(self, directory: Path | str, reset: bool = False) -> int:
        directory = Path(directory)
        if reset:
            self.reset()
        files = [path for path in directory.rglob("*") if path.suffix.lower() in SUPPORTED_EXTENSIONS]
        return self.ingest_files(files)

    def ingest_files(self, files: Iterable[Path | str]) -> int:
        documents = []
        fallback_chunks: list[RetrievedChunk] = []

        for file in files:
            file_path = Path(file)
            if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            try:
                loaded = self._load_file(file_path)
            except Exception as exc:
                raise RuntimeError(f"Could not load {file_path.name}: {exc}") from exc
            if LANGCHAIN_AVAILABLE and Document is not None:
                documents.extend(loaded)
            else:
                for item in loaded:
                    fallback_chunks.extend(self._fallback_split(item["page_content"], item["metadata"]))

        if LANGCHAIN_AVAILABLE and documents:
            chunks = self._split_langchain_documents(documents)
            for idx, chunk in enumerate(chunks):
                chunk.metadata["chunk_id"] = idx
                chunk.metadata["section"] = self._detect_section(chunk.page_content, chunk.metadata.get("section"))
            if self.langchain_enabled:
                ids = [self._stable_chunk_id(chunk) for chunk in chunks]
                try:
                    self.vectorstore.add_documents(chunks, ids=ids)
                except Exception as exc:
                    if "dimension" not in str(exc).lower():
                        raise
                    self.reset()
                    self.vectorstore.add_documents(chunks, ids=ids)
                return len(chunks)
            for chunk in chunks:
                metadata = sanitize_metadata(dict(chunk.metadata))
                fallback_chunks.append(
                    RetrievedChunk(
                        text=chunk.page_content,
                        source=str(metadata.get("source", "unknown")),
                        page=metadata.get("page"),
                        chunk_id=metadata.get("chunk_id"),
                        section=str(metadata.get("section")) if metadata.get("section") else None,
                        metadata=metadata,
                    )
                )

        self.fallback_chunks.extend(fallback_chunks)
        return len(fallback_chunks)

    def _load_file(self, file_path: Path) -> list[Any]:
        suffix = file_path.suffix.lower()
        if suffix in IMAGE_EXTENSIONS:
            return self._load_image_file(file_path)

        if LANGCHAIN_AVAILABLE and Document is not None:
            try:
                if suffix == ".pdf" and PyPDFLoader is not None:
                    docs = PyPDFLoader(str(file_path)).load()
                    return self._normalize_documents(self._require_text(docs, file_path))
                if suffix == ".docx" and Docx2txtLoader is not None:
                    docs = Docx2txtLoader(str(file_path)).load()
                    return self._normalize_documents(self._require_text(docs, file_path))
                if suffix in {".txt", ".md", ".csv"} and TextLoader is not None:
                    docs = TextLoader(str(file_path), encoding="utf-8").load()
                    return self._normalize_documents(self._require_text(docs, file_path))
            except Exception as exc:
                if suffix in {".pdf", ".docx"}:
                    raise ValueError(
                        "text extraction failed. The file may be encrypted, corrupted, or scanned without OCR."
                    ) from exc

        text = file_path.read_text(encoding="utf-8", errors="ignore")
        if not text.strip():
            raise ValueError("no extractable text was found.")
        text = self._normalize_text(text)
        metadata = self._enrich_metadata({"source": str(file_path), "section": self._detect_section(text)}, text)
        return [self._make_document(text, metadata)]

    @staticmethod
    def _require_text(documents: list[Any], file_path: Path) -> list[Any]:
        if not documents or not any(getattr(doc, "page_content", "").strip() for doc in documents):
            raise ValueError(f"{file_path.name} did not contain extractable text.")
        return documents

    def _load_image_file(self, file_path: Path) -> list[Any]:
        metadata: dict[str, Any] = {
            "source": str(file_path),
            "file_type": "image",
            "section": "Image OCR",
        }
        ocr_text = ""
        vision_text = ""
        status = "metadata_only"

        try:
            from PIL import Image

            with Image.open(file_path) as image:
                metadata["image_width"] = image.width
                metadata["image_height"] = image.height
                metadata["image_mode"] = image.mode
                try:
                    import pytesseract

                    ocr_text = pytesseract.image_to_string(image).strip()
                    status = "ocr_text" if ocr_text else "ocr_empty"
                except Exception as exc:
                    metadata["ocr_error"] = str(exc)
                    status = "ocr_unavailable"
        except Exception as exc:
            metadata["image_error"] = str(exc)

        vision_status = ""
        if self.analyze_images:
            vision_text, vision_status = analyze_finance_image(file_path, self.image_analysis_model)
            metadata["vision_status"] = vision_status

        methods = [status]
        if vision_status:
            methods.append(vision_status)
        metadata["extraction_method"] = "+".join(methods)

        text_parts = [f"Image upload: {file_path.name}"]
        if ocr_text:
            text_parts.append(f"Image OCR text:\n\n{self._normalize_text(ocr_text)}")
        if vision_text:
            text_parts.append(f"Gemini visual finance/chart summary:\n\n{self._normalize_text(vision_text)}")

        if len(text_parts) > 1:
            text = "\n\n".join(text_parts)
        else:
            text = (
                f"Image upload: {file_path.name}\n"
                f"OCR status: {status}. Install Tesseract OCR and requirements-ocr.txt to extract text from images.\n"
                "The image can still be tracked as an uploaded file. "
                "Enable Gemini image analysis in the sidebar to index a visual chart/finance summary."
            )
        return [self._make_document(text, self._enrich_metadata(metadata, text))]

    def _make_document(self, text: str, metadata: dict[str, Any]) -> Any:
        if LANGCHAIN_AVAILABLE and Document is not None:
            return Document(page_content=text, metadata=metadata)
        return {"page_content": text, "metadata": metadata}

    def _normalize_documents(self, documents: list[Any]) -> list[Any]:
        normalized = []
        for document in documents:
            text = self._normalize_text(getattr(document, "page_content", ""))
            metadata = dict(getattr(document, "metadata", {}) or {})
            metadata["section"] = self._detect_section(text, metadata.get("section"))
            metadata = self._enrich_metadata(metadata, text)
            normalized.append(self._make_document(text, metadata))
        return normalized

    def _enrich_metadata(self, metadata: dict[str, Any], text: str) -> dict[str, Any]:
        inferred = infer_financial_metadata(metadata.get("source"), text)
        enriched = dict(metadata)
        for key, value in inferred.items():
            if value is not None and enriched.get(key) in {None, ""}:
                enriched[key] = value
        return sanitize_metadata(enriched)

    @staticmethod
    def _normalize_text(text: str) -> str:
        replacements = {
            "T otal": "Total",
            "Y ou": "You",
            "Y es": "Yes",
            "N o": "No",
            "Lender’ s": "Lender's",
            "owner’ s": "owner's",
            "guarantor’ s": "guarantor's",
            "Lâ€™Hopital": "L'Hopital",
            "Lâ€™HOPITAL": "L'Hopital",
            "â†’": "->",
            "âˆž": "infinity",
            "\uf0a8": "",
        }
        cleaned = text
        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    @staticmethod
    def _detect_section(text: str, fallback: str | None = None) -> str | None:
        headings = [
            "Personal Financial Statement",
            "ASSETS",
            "LIABILITIES",
            "Schedule A",
            "Schedule B",
            "Schedule C",
            "Schedule D",
            "Schedule E",
            "Declarations",
            "Authorization",
            "Business Information",
            "Liquidity",
            "Solvency and Leverage",
            "Profitability",
            "Strategic Risks",
            "Methodology",
            "Main Findings",
            "L'Hopital's Rule and rates of growth",
            "L'Hopital's Rule",
            "Running times of algorithms",
            "Important ideas and useful facts",
            "Examples and explanations",
            "Warning",
        ]
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines[:25]:
            normalized = re.sub(r"\s+", " ", line).strip().lower()
            for heading in headings:
                heading_lower = heading.lower()
                if normalized == heading_lower:
                    return heading
                if heading in {"ASSETS", "LIABILITIES"} and normalized.startswith(f"{heading_lower} "):
                    return heading
                if heading not in {"ASSETS", "LIABILITIES"} and normalized.startswith(heading_lower):
                    return heading
        return fallback

    def _split_langchain_documents(self, documents: list[Any]) -> list[Any]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        return splitter.split_documents(documents)

    def _fallback_split(self, text: str, metadata: dict[str, Any]) -> list[RetrievedChunk]:
        words = text.split()
        step = max(1, CHUNK_SIZE - CHUNK_OVERLAP)
        chunks: list[RetrievedChunk] = []
        chunk_index = 0
        for start in range(0, len(words), step):
            chunk_words = words[start : start + CHUNK_SIZE]
            if not chunk_words:
                continue
            chunks.append(
                RetrievedChunk(
                    text=" ".join(chunk_words),
                    source=str(metadata.get("source", "unknown")),
                    page=metadata.get("page"),
                    chunk_id=chunk_index,
                    section=metadata.get("section"),
                    metadata=sanitize_metadata(metadata),
                )
            )
            chunk_index += 1
        return chunks

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        k = top_k or self.top_k
        filters = extract_query_filters(query)
        search_query = self._expand_finance_query(query)
        if self.langchain_enabled:
            try:
                docs = self.vectorstore.similarity_search_with_score(search_query, k=max(k, 12))
                chunks = [
                    RetrievedChunk(
                        text=doc.page_content,
                        source=str(doc.metadata.get("source", "unknown")),
                        page=doc.metadata.get("page"),
                        chunk_id=doc.metadata.get("chunk_id"),
                        score=score,
                        section=doc.metadata.get("section"),
                        metadata=sanitize_metadata(dict(doc.metadata)),
                    )
                    for doc, score in docs
                ]
                chunks.extend(self._collection_keyword_candidates(search_query, limit=max(k * 4, 16)))
                return self._lexical_rerank(search_query, self._dedupe_chunks(chunks), k, filters=filters)
            except Exception:
                docs = self.vectorstore.similarity_search(search_query, k=max(k, 12))
                chunks = [
                    RetrievedChunk(
                        text=doc.page_content,
                        source=str(doc.metadata.get("source", "unknown")),
                        page=doc.metadata.get("page"),
                        chunk_id=doc.metadata.get("chunk_id"),
                        section=doc.metadata.get("section"),
                        metadata=sanitize_metadata(dict(doc.metadata)),
                    )
                    for doc in docs
                ]
                chunks.extend(self._collection_keyword_candidates(search_query, limit=max(k * 4, 16)))
                return self._lexical_rerank(search_query, self._dedupe_chunks(chunks), k, filters=filters)

        return self._fallback_retrieve(search_query, k, filters=filters)

    @staticmethod
    def _stable_chunk_id(chunk: Any) -> str:
        metadata = getattr(chunk, "metadata", {}) or {}
        raw = "|".join(
            [
                str(metadata.get("source", "")),
                str(metadata.get("page", "")),
                str(metadata.get("chunk_id", "")),
                getattr(chunk, "page_content", ""),
            ]
        )
        return hashlib.md5(raw.encode("utf-8", errors="ignore")).hexdigest()

    def _collection_keyword_candidates(self, query: str, limit: int) -> list[RetrievedChunk]:
        if not self.langchain_enabled:
            return []
        try:
            payload = self.vectorstore._collection.get(include=["documents", "metadatas"])
        except Exception:
            return []

        documents = payload.get("documents", []) or []
        metadatas = payload.get("metadatas", []) or []
        chunks = [
            RetrievedChunk(
                text=document or "",
                source=str((metadata or {}).get("source", "unknown")),
                page=(metadata or {}).get("page"),
                chunk_id=(metadata or {}).get("chunk_id"),
                section=(metadata or {}).get("section"),
                metadata=sanitize_metadata(dict(metadata or {})),
            )
            for document, metadata in zip(documents, metadatas)
            if document
        ]
        return self._lexical_rerank(query, chunks, limit)

    @staticmethod
    def _dedupe_chunks(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        seen: set[tuple[str, int | None, int | None, str]] = set()
        deduped: list[RetrievedChunk] = []
        for chunk in chunks:
            key = (chunk.source, chunk.page, chunk.chunk_id, chunk.text[:200])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(chunk)
        return deduped

    def _lexical_rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        k: int,
        filters: dict[str, str] | None = None,
    ) -> list[RetrievedChunk]:
        query_terms = self._content_terms(query)
        ranked = []
        for chunk in chunks:
            chunk_terms = self._content_terms(f"{chunk.text} {chunk.source}")
            overlap = len(query_terms & chunk_terms)
            lexical_score = overlap / (len(query_terms) or 1)
            phrase_bonus = self._phrase_bonus(query, chunk.text)
            metadata_bonus = metadata_filter_score(filters or {}, chunk.metadata)
            section_bonus = 0.1 if chunk.section and chunk.section.lower() in query.lower() else 0.0
            distance_penalty = 0.0 if chunk.score is None else min(float(chunk.score), 10.0) * 0.001
            ranked.append((lexical_score + phrase_bonus + metadata_bonus + section_bonus - distance_penalty, chunk))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [chunk for _, chunk in ranked[:k]]

    @staticmethod
    def _phrase_bonus(query: str, text: str) -> float:
        normalized_query = re.sub(r"\s+", " ", query.lower())
        normalized_text = re.sub(r"\s+", " ", text.lower())
        bonus = 0.0
        phrases = [
            "personal financial statement",
            "nile retail",
            "nile retail holdings",
            "liabilities",
            "what you owe",
            "assets",
            "what you own",
            "credit cards",
            "revolving loans",
            "current ratio",
            "debt-to-equity",
            "cash conversion cycle",
            "black-scholes",
            "black scholes",
            "option pricing",
            "greeks",
            "delta",
            "implied volatility",
            "var",
            "cvar",
            "duration",
            "convexity",
            "credit spread",
            "stochastic discount factor",
            "capital asset pricing model",
            "factor models",
            "event study",
            "panel regression",
            "advanced calculus",
            "l'hopital",
            "l'hopital's rule",
            "rates of growth",
            "running times of algorithms",
            "derivative",
            "sin x",
            "calculus",
        ]
        for phrase in phrases:
            if phrase in normalized_query and phrase in normalized_text:
                bonus += 0.2
        return min(bonus, 0.8)

    @staticmethod
    def _expand_finance_query(query: str) -> str:
        lowered = query.lower()
        additions: list[str] = []
        if "personal financial statement" in lowered:
            additions.extend(["assets", "liabilities", "net worth", "schedules", "owner guarantor"])
        if "liabil" in lowered or "owe" in lowered:
            additions.extend(
                [
                    "accounts bills due",
                    "credit cards revolving loans",
                    "installment other loans",
                    "mortgages home equity loans",
                    "total liabilities",
                    "net worth",
                ]
            )
        if "asset" in lowered or "own" in lowered:
            additions.extend(
                [
                    "cash stocks bonds retirement accounts real estate automobiles other assets",
                    "estimated value of business total assets",
                ]
            )
        if "company health" in lowered or "financial health" in lowered:
            additions.extend(["profitability liquidity solvency leverage cash flow debt margin risk working capital"])
        if "nile retail" in lowered:
            additions.extend(["Nile Retail Holdings annual report revenue gross margin inventory debt online orders store network"])
        if "research" in lowered or "paper" in lowered:
            additions.extend(["objective research question methodology variables findings limitations sample"])
        if "image" in lowered or "screenshot" in lowered:
            additions.extend(["ocr extracted text image upload"])
        if "black-scholes" in lowered or "black scholes" in lowered or "option" in lowered:
            additions.extend(["Black-Scholes option pricing European call put greeks delta d1 d2 volatility"])
        if "var" in lowered or "cvar" in lowered:
            additions.extend(["value at risk conditional value at risk tail loss expected shortfall"])
        if "duration" in lowered or "convexity" in lowered:
            additions.extend(["bond duration convexity yield price sensitivity fixed income"])
        if "credit spread" in lowered:
            additions.extend(["default risk liquidity spread stress testing credit risk"])
        if "capm" in lowered or "factor" in lowered:
            additions.extend(["capital asset pricing model beta factor models fama french"])
        math_terms = [
            "calculus",
            "l'hopital",
            "lhopital",
            "lim ",
            "derivative",
            "sin x",
            "rates of growth",
        ]
        if any(term in lowered for term in math_terms):
            additions.extend(
                [
                    "advanced calculus",
                    "L'Hopital's Rule",
                    "0/0 form",
                    "infinity form",
                    "limits derivatives",
                    "rates of growth",
                    "running times of algorithms",
                    "sin x over x",
                ]
            )
        return " ".join([query, *additions]).strip()

    @staticmethod
    def _content_terms(text: str) -> set[str]:
        stopwords = {
            "the",
            "and",
            "are",
            "for",
            "from",
            "with",
            "what",
            "does",
            "this",
            "that",
            "main",
            "explain",
            "calculate",
            "financial",
            "finance",
        }
        return {
            token
            for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_]+", text.lower())
            if token not in stopwords and len(token) > 2
        }

    def _fallback_retrieve(self, query: str, k: int, filters: dict[str, str] | None = None) -> list[RetrievedChunk]:
        query_terms = self._content_terms(query)
        ranked = []
        for chunk in self.fallback_chunks:
            terms = self._content_terms(f"{chunk.text} {chunk.source}")
            overlap = len(query_terms & terms)
            score = overlap / (len(query_terms) or 1)
            score += self._phrase_bonus(query, chunk.text)
            score += metadata_filter_score(filters or {}, chunk.metadata)
            ranked.append((score, chunk))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [
            RetrievedChunk(item.text, item.source, item.page, item.chunk_id, score, item.section, item.metadata)
            for score, item in ranked[:k]
            if score > 0
        ]


def format_context(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "No relevant document context was retrieved."

    parts = []
    for index, chunk in enumerate(chunks, start=1):
        parts.append(f"[Source {index}: {chunk.citation()}]\n{chunk.text}")
    return "\n\n".join(parts)


def sources_to_json(chunks: list[RetrievedChunk]) -> str:
    return json.dumps(
        [
            {
                "source": chunk.source,
                "page": chunk.page,
                "chunk_id": chunk.chunk_id,
                "section": chunk.section,
                "score": chunk.score,
                "metadata": chunk.metadata,
            }
            for chunk in chunks
        ],
        indent=2,
    )
