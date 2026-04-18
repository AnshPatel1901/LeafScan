"""
RAG Pipeline — Retrieval-Augmented Generation orchestrator.

Coordinates:
    • PDF loading
    • Document chunking
    • Embedding generation
    • Vector storage
    • Semantic retrieval
    • LLM answer generation
"""

import logging
import os
import time
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from app.rag.models import RAGConfig, RAGQueryResult, RetrievedDocument
from app.rag.pdf_loader import PDFLoader, get_pdf_loader
from app.rag.chunking import TextChunker, Chunk
from app.rag.embeddings import EmbeddingsModel, get_embeddings
from app.rag.vector_store import ChromaVectorStore, get_vector_store
from app.rag.retriever import Retriever, RetrievalContext
from app.rag.llm import GroqLLM, get_groq_llm

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    Complete Retrieval-Augmented Generation pipeline.
    
    Workflow:
        1. Load PDF document
        2. Split into chunks
        3. Generate embeddings
        4. Store in vector database
        5. Accept user query
        6. Retrieve relevant documents
        7. Generate answer with LLM
    """
    
    def __init__(self, config: Optional[RAGConfig] = None):
        """
        Initialize RAG pipeline.
        
        Parameters
        ----------
        config : Optional[RAGConfig]
            Configuration (uses defaults if not provided)
        """
        self.config = config or RAGConfig()
        
        logger.info("Initializing RAG Pipeline | config=%s", self.config)
        
        # Initialize components
        self.pdf_loader = get_pdf_loader()
        self.chunker = TextChunker(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
        )
        self.embeddings = get_embeddings(self.config.embedding_model)
        self.vector_store = get_vector_store(self.config.vectordb_dir)
        self.retriever = Retriever(
            vector_store=self.vector_store,
            embeddings=self.embeddings,
            top_k=self.config.top_k_docs,
            fetch_k=self.config.fetch_k,
        )
        self.llm = get_groq_llm()
        
        # Create storage directories
        Path(self.config.documents_dir).mkdir(parents=True, exist_ok=True)
        Path(self.config.vectordb_dir).mkdir(parents=True, exist_ok=True)
        
        logger.info("RAG Pipeline initialized successfully")
    
    # ── Public API ─────────────────────────────────────────────────────────────
    
    async def ingest_pdf(self, pdf_path: str, filename: Optional[str] = None) -> dict:
        """
        Ingest a PDF document into the RAG system.
        
        Complete workflow:
            1. Load PDF
            2. Extract pages
            3. Chunk text
            4. Generate embeddings
            5. Store in vector DB
        
        Parameters
        ----------
        pdf_path : str
            Path to the PDF file
        filename : Optional[str]
            Document filename (uses basename if not provided)
        
        Returns
        -------
        dict
            Ingestion stats (pages, chunks, etc.)
        
        Raises
        ------
        FileNotFoundError
            If PDF not found
        ValueError
            If PDF is invalid or processing fails
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        filename = filename or os.path.basename(pdf_path)
        
        try:
            logger.info("Ingesting PDF | file=%s", filename)
            
            # Step 1: Load PDF
            pdf_doc = await self.pdf_loader.load(pdf_path, filename)
            logger.info("PDF loaded | pages=%d", pdf_doc.num_pages)
            
            # Step 2: Extract and chunk pages
            all_chunks: List[Chunk] = []
            
            for page_num, page_text in enumerate(pdf_doc.pages):
                chunks = self.chunker.chunk_document(
                    text=page_text,
                    page=page_num,
                    source=filename,
                )
                all_chunks.extend(chunks)
                logger.debug("Page %d chunked into %d chunks", page_num + 1, len(chunks))
            
            logger.info("Total chunks created: %d", len(all_chunks))
            
            if not all_chunks:
                raise ValueError("No chunks generated from PDF")
            
            # Step 3: Generate embeddings
            logger.info("Generating embeddings for %d chunks", len(all_chunks))
            chunk_texts = [chunk.content for chunk in all_chunks]
            embeddings = self.embeddings.embed_batch(chunk_texts)
            
            logger.info("Embeddings generated | shape=%s", embeddings.shape)
            
            # Step 4: Prepare metadata
            metadatas = [
                {
                    "source": chunk.source,
                    "page": chunk.page,
                    "chunk": chunk.chunk_num,
                }
                for chunk in all_chunks
            ]
            
            # Generate document IDs
            doc_ids = [
                f"{filename}_{chunk.page}_{chunk.chunk_num}"
                for chunk in all_chunks
            ]
            
            # Step 5: Store in vector database
            logger.info("Storing documents in vector database")
            await self.vector_store.add_documents(
                texts=chunk_texts,
                embeddings=embeddings.tolist(),
                metadatas=metadatas,
                ids=doc_ids,
            )
            
            # Get collection stats
            stats = self.vector_store.get_collection_stats()
            
            result = {
                "filename": filename,
                "pages": pdf_doc.num_pages,
                "chunks": len(all_chunks),
                "vector_db_count": stats.get("count", 0),
                "embedding_dim": self.embeddings.dimension,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            logger.info("Ingestion complete | %s", result)
            return result
        
        except Exception as e:
            logger.exception("PDF ingestion failed")
            raise RuntimeError(f"PDF ingestion failed: {e}") from e
    
    async def query(
        self,
        query_text: str,
        language: str = "en",
        use_sources: bool = True,
    ) -> RAGQueryResult:
        """
        Query the RAG system and get an answer.
        
        Pipeline:
            1. Embed query
            2. Retrieve relevant documents
            3. Prepare context
            4. Generate answer with LLM
        
        Parameters
        ----------
        query_text : str
            User question/query
        language : str
            Language for response (ISO 639-1 code)
        use_sources : bool
            Include source documents in response
        
        Returns
        -------
        RAGQueryResult
            Answer with supporting documents
        
        Raises
        ------
        ValueError
            If query is invalid
        RuntimeError
            If retrieval or generation fails
        """
        if not query_text or not query_text.strip():
            raise ValueError("Query cannot be empty")
        
        start_time = time.time()
        
        try:
            logger.info("RAG Query | query_len=%d | lang=%s", len(query_text), language)
            
            # Step 1: Retrieve documents
            retrieval_start = time.time()
            context = await self.retriever.retrieve(query_text, use_mmr=True)
            retrieval_time = (time.time() - retrieval_start) * 1000
            
            logger.info("Retrieved %d documents in %.0fms", len(context.documents), retrieval_time)
            
            if not context.documents:
                logger.warning("No documents retrieved for query")
                return RAGQueryResult(
                    query=query_text,
                    answer="I don't have information about this in the provided documents.",
                    language=language,
                    documents=[],
                    sources=[],
                    query_time_ms=retrieval_time,
                    generation_time_ms=0,
                )
            
            # Step 2: Build prompt
            formatted_context = context.format_for_prompt()
            prompt = self._build_query_prompt(
                query=query_text,
                context=formatted_context,
                language=language,
            )
            
            logger.debug("Prompt length: %d characters", len(prompt))
            
            # Step 3: Generate answer
            generation_start = time.time()
            answer = await self.llm.generate(prompt, language)
            generation_time = (time.time() - generation_start) * 1000
            
            logger.info("Answer generated in %.0fms | length=%d", generation_time, len(answer))
            
            # Step 4: Prepare result
            result = RAGQueryResult(
                query=query_text,
                answer=answer,
                language=language,
                documents=context.documents if use_sources else [],
                sources=context.source_list,
                query_time_ms=retrieval_time,
                generation_time_ms=generation_time,
            )
            
            logger.info(
                "RAG query complete | total_time=%.0fms",
                result.total_time_ms
            )
            
            return result
        
        except Exception as e:
            logger.exception("RAG query failed")
            raise RuntimeError(f"RAG query failed: {e}") from e
    
    # ── Utilities ──────────────────────────────────────────────────────────────
    
    def _build_query_prompt(
        self,
        query: str,
        context: str,
        language: str,
    ) -> str:
        """Build complete prompt for LLM."""
        lang_name = {
            "en": "English",
            "hi": "Hindi",
            "ta": "Tamil",
            "te": "Telugu",
            "mr": "Marathi",
            "bn": "Bengali",
            "gu": "Gujarati",
            "kn": "Kannada",
            "ml": "Malayalam",
            "pa": "Punjabi",
            "fr": "French",
            "es": "Spanish",
            "de": "German",
            "zh": "Chinese",
            "ar": "Arabic",
            "pt": "Portuguese",
            "it": "Italian",
            "ja": "Japanese",
            "ko": "Korean",
        }.get(language, "English")
        
        return f"""{context}

QUESTION: {query}

INSTRUCTIONS:
- Answer ONLY based on the provided context
- If the answer is not in the documents, say "I don't have information about this"
- Respond in {lang_name}
- Be concise and practical
- Do not hallucinate or add information not in the context
- Format your answer clearly with sections if needed

ANSWER:"""
    
    async def get_stats(self) -> dict:
        """Get RAG system statistics."""
        try:
            db_stats = self.vector_store.get_collection_stats()
            return {
                "vector_db": db_stats,
                "embedding_model": self.config.embedding_model,
                "groq_model": self.config.groq_model,
                "chunk_size": self.config.chunk_size,
                "chunk_overlap": self.config.chunk_overlap,
            }
        except Exception as e:
            logger.exception("Failed to get stats")
            return {"error": str(e)}
    
    async def reset(self) -> bool:
        """Reset the RAG system (delete all documents from vector DB)."""
        try:
            logger.warning("Resetting RAG system")
            await self.vector_store.delete_collection()
            logger.info("RAG system reset complete")
            return True
        except Exception as e:
            logger.exception("Failed to reset RAG system")
            return False


# Singleton instance
_rag_pipeline_instance: Optional[RAGPipeline] = None


def get_rag_pipeline(config: Optional[RAGConfig] = None) -> RAGPipeline:
    """Get or create RAG pipeline singleton."""
    global _rag_pipeline_instance
    if _rag_pipeline_instance is None:
        _rag_pipeline_instance = RAGPipeline(config)
    return _rag_pipeline_instance
