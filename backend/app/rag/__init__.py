"""
RAG Module — Retrieval-Augmented Generation system.

This package provides a complete RAG pipeline for:
    • Loading and processing PDFs
    • Splitting documents into meaningful chunks
    • Creating multilingual embeddings
    • Storing embeddings in ChromaDB
    • Retrieving relevant context
    • Generating answers using Groq LLM

Usage:
    from app.rag.pipeline import RAGPipeline

    rag = RAGPipeline()
    await rag.ingest_pdf("document.pdf")
    result = await rag.query("What is disease X?", language="hi")
    print(result.answer)
"""

from .pipeline import RAGPipeline
from .models import RAGQueryResult, RAGConfig

__all__ = ["RAGPipeline", "RAGQueryResult", "RAGConfig"]
