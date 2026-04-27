"""
RAG Service — PDF ingestion, embedding, and semantic retrieval.

Pipeline:
  1. Load PDF pages via PyPDFLoader
  2. Chunk with RecursiveCharacterTextSplitter (1200/150)
  3. Embed locally with HuggingFace all-MiniLM-L6-v2 (no API key, no quota)
  4. Persist chunks in ChromaDB (disk-backed)
  5. Retrieve via MMR (max marginal relevance) for diverse results

Embedding note
--------------
Gemini embedding code is preserved below in comments.
Switch back by setting USE_LOCAL_EMBEDDINGS = False and providing GEMINI_API_KEY.
Local embeddings use sentence-transformers/all-MiniLM-L6-v2 (384-dim, CPU-friendly).
They are stored in a separate ChromaDB collection ("leafscan_kb_local") so that
existing Gemini-embedded vectors are never overwritten.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Embedding strategy toggle
#   True  → local HuggingFace (offline, no quota, default)
#   False → Gemini API        (requires GEMINI_API_KEY, hits 429 on large PDFs)
# ---------------------------------------------------------------------------
USE_LOCAL_EMBEDDINGS = True

# Local HuggingFace model — 384-dim, CPU-friendly, ~90 MB download on first run
LOCAL_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Separate ChromaDB collections so Gemini & local vectors never mix
CHROMA_COLLECTION_LOCAL = "leafscan_kb_local"    # HuggingFace (active)
CHROMA_COLLECTION_GEMINI = "leafscan_knowledge_base"  # Gemini (preserved, inactive)

# Use the local collection while USE_LOCAL_EMBEDDINGS is True
CHROMA_COLLECTION = CHROMA_COLLECTION_LOCAL if USE_LOCAL_EMBEDDINGS else CHROMA_COLLECTION_GEMINI

DOCS_INDEX_FILENAME = "documents_index.json"

# Default PDF auto-indexed when the knowledge base is empty.
# Set to None to disable auto-indexing.
DEFAULT_PDF_NAME = "Plant-Pathogens-Principles-of-Plant-Pathology.pdf"

# ---------------------------------------------------------------------------
# Lazy imports — heavy libs loaded only when first request arrives so that
# startup is not blocked if the packages are being installed.
# ---------------------------------------------------------------------------

def _load_langchain():
    from langchain_community.document_loaders import PyPDFLoader  # noqa: PLC0415
    from langchain_text_splitters import RecursiveCharacterTextSplitter  # noqa: PLC0415
    return PyPDFLoader, RecursiveCharacterTextSplitter


def _load_chroma():
    try:
        from langchain_chroma import Chroma  # noqa: PLC0415
    except ImportError:
        from langchain_community.vectorstores import Chroma  # noqa: PLC0415
    return Chroma


def _load_embeddings_local():
    """
    Local HuggingFace embeddings — fully offline, no API key, no quota limits.
    Model: sentence-transformers/all-MiniLM-L6-v2 (384-dim, CPU-friendly).
    Downloaded once to the HuggingFace cache (~90 MB), reused on every restart.

    Uses langchain-huggingface (not langchain-community) to avoid:
      - LangChainDeprecationWarning on the old import path
      - Keras 3 incompatibility triggered by the transformers TF backend check
    """
    try:
        # Preferred: langchain-huggingface package (no Keras/TF dependency)
        from langchain_huggingface import HuggingFaceEmbeddings  # noqa: PLC0415
    except ImportError:
        # Fallback if langchain-huggingface is not installed yet
        from langchain_community.embeddings import HuggingFaceEmbeddings  # noqa: PLC0415

    return HuggingFaceEmbeddings(
        model_name=LOCAL_EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


# ---------------------------------------------------------------------------
# COMMENTED OUT — Gemini embeddings
# Uncomment and set USE_LOCAL_EMBEDDINGS = False to switch back.
# Requires a valid GEMINI_API_KEY and is subject to quota limits (429 errors
# on large PDFs with the free tier).
# ---------------------------------------------------------------------------
# def _load_embeddings_gemini(api_key: str, model: str):
#     from langchain_google_genai import GoogleGenerativeAIEmbeddings  # noqa: PLC0415
#     return GoogleGenerativeAIEmbeddings(
#         model=model,
#         google_api_key=api_key,
#     )


# ---------------------------------------------------------------------------
# RAGService
# ---------------------------------------------------------------------------


class RAGService:
    """
    Manages the full RAG pipeline: PDF ingestion → embedding → ChromaDB → MMR retrieval.

    Thread-safety note: ChromaDB is used synchronously.  The service is
    instantiated once (singleton) and reused across async request handlers.
    CPU-bound embed/index calls are fast enough not to block the event loop
    significantly for typical document sizes.
    """

    def __init__(self) -> None:
        self._vector_db_dir = settings.RAG_VECTOR_DB_DIR
        self._upload_dir = settings.RAG_UPLOAD_DIR
        self._chunk_size = settings.RAG_CHUNK_SIZE
        self._chunk_overlap = settings.RAG_CHUNK_OVERLAP
        self._top_k = settings.RAG_TOP_K_DOCS
        self._fetch_k = settings.RAG_FETCH_K

        Path(self._vector_db_dir).mkdir(parents=True, exist_ok=True)
        Path(self._upload_dir).mkdir(parents=True, exist_ok=True)

        self._docs_meta_path = Path(self._vector_db_dir) / DOCS_INDEX_FILENAME
        self._documents_index: Dict[str, Any] = self._load_documents_index()

        self._embeddings = None
        self._vectorstore = None
        self._text_splitter = None
        self._initialized = False

        logger.info(
            "RAGService created | vector_db=%s | %d docs in index",
            self._vector_db_dir,
            len(self._documents_index),
        )

    # ── Lazy initialisation ───────────────────────────────────────────────────

    def _ensure_initialized(self) -> None:
        """
        Lazy-load heavy dependencies on first use.

        Embedding strategy (controlled by USE_LOCAL_EMBEDDINGS at module top):
          True  → HuggingFace all-MiniLM-L6-v2 (local, no quota)   ← ACTIVE
          False → Google Gemini gemini-embedding-001 (API, quota)   ← COMMENTED OUT
        """
        if self._initialized:
            return

        _, RecursiveCharacterTextSplitter = _load_langchain()
        Chroma = _load_chroma()

        # ── Active: local HuggingFace embeddings ─────────────────────────────
        self._embeddings = _load_embeddings_local()

        # ── Commented out: Gemini embeddings ─────────────────────────────────
        # Uncomment the block below and set USE_LOCAL_EMBEDDINGS = False to
        # switch back to Gemini.  Also requires a valid GEMINI_API_KEY in .env.
        #
        # if not settings.GEMINI_API_KEY:
        #     raise RuntimeError("GEMINI_API_KEY is not configured")
        # self._embeddings = _load_embeddings_gemini(
        #     api_key=settings.GEMINI_API_KEY,
        #     model=settings.GEMINI_EMBEDDING_MODEL,
        # )
        # ─────────────────────────────────────────────────────────────────────

        self._vectorstore = Chroma(
            collection_name=CHROMA_COLLECTION,
            embedding_function=self._embeddings,
            persist_directory=self._vector_db_dir,
        )

        self._text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
        )

        self._initialized = True
        logger.info(
            "RAGService initialized | embedding=%s | collection=%s | chroma=%s",
            LOCAL_EMBEDDING_MODEL if USE_LOCAL_EMBEDDINGS else settings.GEMINI_EMBEDDING_MODEL,
            CHROMA_COLLECTION,
            self._vector_db_dir,
        )

        # Auto-index the default PDF if the knowledge base is still empty
        self._auto_index_default_pdf()

    # ── Default PDF auto-indexing ─────────────────────────────────────────────

    def _auto_index_default_pdf(self) -> None:
        """
        Index the default PDF when the knowledge base is empty.

        Search order:
          1. DEFAULT_PDF_NAME in RAG_UPLOAD_DIR (exact filename match)
          2. Any *.pdf file in RAG_UPLOAD_DIR (first found)

        Does nothing if:
          - DEFAULT_PDF_NAME is None / falsy
          - Knowledge base already has indexed documents
          - No PDF files are found in the upload directory
        """
        if not DEFAULT_PDF_NAME:
            return
        if self._documents_index:
            logger.debug("Knowledge base already has documents — skipping default PDF auto-index")
            return

        upload_dir = Path(self._upload_dir)

        # Try exact name first, then any PDF
        candidates = [upload_dir / DEFAULT_PDF_NAME] + sorted(upload_dir.glob("*.pdf"))
        pdf_path: Optional[Path] = None
        for c in candidates:
            if c.exists() and c.is_file():
                pdf_path = c
                break

        if pdf_path is None:
            logger.info(
                "Default PDF '%s' not found in %s — upload a PDF to enable the chatbot",
                DEFAULT_PDF_NAME,
                upload_dir,
            )
            return

        logger.info("Auto-indexing default PDF: %s", pdf_path.name)
        try:
            doc_name = pdf_path.stem  # filename without extension
            self.load_and_index_pdf(str(pdf_path), doc_name)
            logger.info("Default PDF indexed successfully: %s", pdf_path.name)
        except Exception as exc:
            logger.warning("Auto-indexing default PDF failed (non-fatal): %s", exc)

    # ── Documents index (JSON on disk) ────────────────────────────────────────

    def _load_documents_index(self) -> Dict[str, Any]:
        if self._docs_meta_path.exists():
            try:
                with open(self._docs_meta_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                logger.warning("Corrupt documents index — starting fresh")
        return {}

    def _save_documents_index(self) -> None:
        with open(self._docs_meta_path, "w", encoding="utf-8") as f:
            json.dump(self._documents_index, f, indent=2)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _file_sha256(file_path: str) -> str:
        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(65536), b""):
                sha.update(block)
        return sha.hexdigest()

    # ── Public API ────────────────────────────────────────────────────────────

    def load_and_index_pdf(self, pdf_path: str, document_name: str) -> Dict[str, Any]:
        """
        Load, chunk, embed, and persist a PDF into ChromaDB.

        If the same file (by SHA-256) was already indexed, return the cached
        metadata without re-processing.

        Args:
            pdf_path:      Absolute path to the PDF on disk.
            document_name: Human-readable name shown in the UI / citations.

        Returns:
            Dict with keys: id, name, pages, chunks, file_path.
        """
        self._ensure_initialized()

        file_hash = self._file_sha256(pdf_path)

        if file_hash in self._documents_index:
            logger.info("Document already indexed: %s (hash=%s)", document_name, file_hash[:8])
            return self._documents_index[file_hash]

        logger.info("Indexing PDF: %s", document_name)

        PyPDFLoader, _ = _load_langchain()
        loader = PyPDFLoader(pdf_path)
        pages = loader.load()
        logger.info("Loaded %d page(s) from %s", len(pages), document_name)

        chunks = self._text_splitter.split_documents(pages)
        logger.info("Split into %d chunk(s)", len(chunks))

        doc_id = file_hash[:16]
        for idx, chunk in enumerate(chunks):
            chunk.metadata.update({
                "doc_id": doc_id,
                "source": document_name,
                "chunk_index": idx,
            })

        # Batch embed — larger batches are fine with local embeddings (no API quota).
        # Reduce BATCH to 50 when switching back to Gemini to avoid 429 errors.
        BATCH = 100
        for start in range(0, len(chunks), BATCH):
            batch = chunks[start: start + BATCH]
            self._vectorstore.add_documents(batch)
            logger.debug(
                "Indexed batch %d/%d",
                start // BATCH + 1,
                (len(chunks) + BATCH - 1) // BATCH,
            )

        doc_info: Dict[str, Any] = {
            "id": doc_id,
            "name": document_name,
            "file_path": pdf_path,
            "hash": file_hash,
            "pages": len(pages),
            "chunks": len(chunks),
        }
        self._documents_index[file_hash] = doc_info
        self._save_documents_index()

        logger.info(
            "Indexed '%s': %d pages, %d chunks → doc_id=%s",
            document_name, len(pages), len(chunks), doc_id,
        )
        return doc_info

    def search(
        self,
        query: str,
        k: Optional[int] = None,
        fetch_k: Optional[int] = None,
    ) -> List[Any]:
        """
        MMR semantic search over the knowledge base.

        Args:
            query:   User query string.
            k:       Number of final documents to return.
            fetch_k: Candidate pool size for MMR re-ranking.

        Returns:
            List of LangChain Document objects (page_content + metadata).
        """
        self._ensure_initialized()

        k = k or self._top_k
        fetch_k = fetch_k or self._fetch_k

        if not self._documents_index:
            logger.info("Vector store has no indexed documents — returning empty results")
            return []

        try:
            retriever = self._vectorstore.as_retriever(
                search_type="mmr",
                search_kwargs={"k": k, "fetch_k": fetch_k, "lambda_mult": 0.5},
            )
            docs = retriever.invoke(query)
            logger.debug("MMR search returned %d docs for query: %s", len(docs), query[:60])
            return docs
        except Exception as exc:
            logger.error("RAG search failed: %s", exc, exc_info=True)
            return []

    def list_documents(self) -> List[Dict[str, Any]]:
        """Return metadata for all indexed documents."""
        return list(self._documents_index.values())

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        for info in self._documents_index.values():
            if info["id"] == doc_id:
                return info
        return None

    def delete_document(self, doc_id: str) -> bool:
        """
        Remove a document's chunks from ChromaDB and from the index.

        Returns True if the document was found and deleted.
        """
        self._ensure_initialized()

        target_hash: Optional[str] = None
        for file_hash, info in self._documents_index.items():
            if info["id"] == doc_id:
                target_hash = file_hash
                break

        if target_hash is None:
            return False

        # Delete from ChromaDB by metadata filter
        try:
            col = self._vectorstore._collection  # chromadb internal
            col.delete(where={"doc_id": doc_id})
            logger.info("Deleted %s from ChromaDB", doc_id)
        except Exception as exc:
            logger.warning("ChromaDB delete warning (non-fatal): %s", exc)

        # Also delete the file from disk if it exists
        info = self._documents_index.pop(target_hash)
        file_path = info.get("file_path", "")
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError as exc:
                logger.warning("Could not delete file %s: %s", file_path, exc)

        self._save_documents_index()
        return True

    def is_ready(self) -> bool:
        """True when at least one document has been indexed."""
        return len(self._documents_index) > 0

    def health(self) -> Dict[str, Any]:
        """Return a health/status dict for the /health endpoint."""
        active_embedding = (
            LOCAL_EMBEDDING_MODEL if USE_LOCAL_EMBEDDINGS
            else settings.GEMINI_EMBEDDING_MODEL
        )
        return {
            "initialized": self._initialized,
            "documents_indexed": len(self._documents_index),
            "vector_db_dir": self._vector_db_dir,
            "upload_dir": self._upload_dir,
            "embedding_model": active_embedding,
            "groq_model": settings.GROQ_RAG_MODEL,
        }


# ── Module-level singleton ─────────────────────────────────────────────────────

_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
