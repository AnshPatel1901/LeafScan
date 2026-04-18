"""
Data models and configuration for RAG system.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class RAGConfig:
    """Configuration for RAG pipeline."""
    
    # Document processing
    chunk_size: int = 1000
    chunk_overlap: int = 150
    
    # Retrieval
    top_k_docs: int = 6
    fetch_k: int = 12  # For MMR retrieval
    
    # Embeddings
    embedding_model: str = "paraphrase-multilingual-mpnet-base-v2"
    embedding_dimension: int = 768
    
    # LLM (Groq)
    groq_model: str = "llama-3.1-8b-versatile"
    groq_temperature: float = 0.3
    groq_max_tokens: int = 1024
    
    # Storage
    vectordb_dir: str = "uploads/rag/vectordb"
    documents_dir: str = "uploads/rag/documents"


@dataclass
class RetrievedDocument:
    """A document chunk retrieved from vector database."""
    
    content: str
    source: str  # filename or URL
    page: Optional[int] = None
    score: Optional[float] = None  # similarity score
    metadata: dict = field(default_factory=dict)


@dataclass
class RAGQueryResult:
    """Result of a RAG query."""
    
    query: str
    answer: str
    language: str
    documents: List[RetrievedDocument] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    confidence: Optional[float] = None
    query_time_ms: float = 0.0
    generation_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def total_time_ms(self) -> float:
        """Total time for query and generation."""
        return self.query_time_ms + self.generation_time_ms


@dataclass
class DocumentMetadata:
    """Metadata for ingested documents."""
    
    filename: str
    upload_time: datetime
    num_pages: int
    num_chunks: int
    language: Optional[str] = None
    metadata: dict = field(default_factory=dict)
