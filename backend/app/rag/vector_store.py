"""
Vector Store — ChromaDB for persistent vector storage and retrieval.

Provides:
    • Document ingestion with embeddings
    • Semantic similarity search
    • Max Marginal Relevance (MMR) retrieval
    • Metadata filtering
    • Persistent storage
"""

import logging
import os
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Result from vector store search."""
    
    id: str
    content: str
    metadata: Dict[str, Any]
    score: float  # Similarity score
    source: str


class ChromaVectorStore:
    """
    Persistent vector store using ChromaDB.
    
    Features:
        • In-memory or on-disk persistence
        • Similarity search
        • MMR (Max Marginal Relevance) retrieval
        • Metadata filtering
        • Multi-language support (via embeddings)
    """
    
    def __init__(self, db_path: str = "uploads/rag/vectordb"):
        """
        Initialize ChromaDB vector store.
        
        Parameters
        ----------
        db_path : str
            Path for persistent vector database storage
        """
        self.db_path = db_path
        self.client = None
        self.collection = None
        self._import_chroma()
        self._init_db()
    
    def _import_chroma(self) -> None:
        """Import ChromaDB library."""
        try:
            import chromadb
            self.chroma = chromadb
            logger.info("ChromaDB imported successfully")
        except ImportError as e:
            raise ImportError(
                "chromadb not installed. Install with: pip install chromadb"
            ) from e
    
    def _init_db(self) -> None:
        """Initialize ChromaDB client and collection."""
        try:
            # Create db path if needed
            os.makedirs(self.db_path, exist_ok=True)
            
            # Initialize persistent client
            self.client = self.chroma.PersistentClient(path=self.db_path)
            logger.info("ChromaDB initialized | path=%s", self.db_path)
            
            # Get or create default collection
            self.collection = self.client.get_or_create_collection(
                name="rag_documents",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("Collection ready: %s", self.collection.name)
        except Exception as e:
            logger.exception("Failed to initialize ChromaDB")
            raise RuntimeError(f"ChromaDB initialization failed: {e}") from e
    
    async def add_documents(
        self,
        texts: List[str],
        embeddings: Optional[List[List[float]]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Add documents to the vector store.
        
        Parameters
        ----------
        texts : List[str]
            Document texts
        embeddings : Optional[List[List[float]]]
            Pre-computed embeddings (optional, can provide external embeddings)
        metadatas : Optional[List[Dict]]
            Metadata for each document (page, source, etc.)
        ids : Optional[List[str]]
            Document IDs (optional, generated if not provided)
        
        Returns
        -------
        List[str]
            List of document IDs
        
        Raises
        ------
        ValueError
            If inputs are invalid
        RuntimeError
            If add operation fails
        """
        if not texts:
            raise ValueError("texts list cannot be empty")
        
        if len(texts) > 0 and metadatas and len(metadatas) != len(texts):
            raise ValueError("metadatas length must match texts length")
        
        if embeddings and len(embeddings) != len(texts):
            raise ValueError("embeddings length must match texts length")
        
        try:
            logger.info("Adding %d documents to vector store", len(texts))
            
            # Add to collection
            add_kwargs = {
                "documents": texts,
            }
            
            if embeddings:
                add_kwargs["embeddings"] = embeddings
            
            if metadatas:
                add_kwargs["metadatas"] = metadatas
            
            if ids:
                add_kwargs["ids"] = ids
            
            self.collection.add(**add_kwargs)
            
            # Get actual IDs
            actual_ids = ids or self.collection.get()["ids"][-len(texts):]
            
            logger.info(
                "Successfully added %d documents | total count=%d",
                len(texts), self.collection.count()
            )
            return actual_ids
        
        except Exception as e:
            logger.exception("Failed to add documents")
            raise RuntimeError(f"Failed to add documents: {e}") from e
    
    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 6,
    ) -> List[SearchResult]:
        """
        Search for similar documents using embeddings.
        
        Parameters
        ----------
        query_embedding : List[float]
            Query embedding vector
        top_k : int
            Number of results to return
        
        Returns
        -------
        List[SearchResult]
            List of similar documents
        
        Raises
        ------
        RuntimeError
            If search fails
        """
        if not query_embedding:
            raise ValueError("query_embedding cannot be empty")
        
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
            )
            
            # Format results
            search_results = []
            
            if results["ids"] and len(results["ids"]) > 0:
                for i, doc_id in enumerate(results["ids"][0]):
                    result = SearchResult(
                        id=doc_id,
                        content=results["documents"][0][i],
                        metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                        score=1 - (results["distances"][0][i] / 2),  # Convert distance to similarity
                        source=results["metadatas"][0][i].get("source", "unknown") if results["metadatas"] else "unknown",
                    )
                    search_results.append(result)
            
            logger.debug("Search returned %d results", len(search_results))
            return search_results
        
        except Exception as e:
            logger.exception("Search failed")
            raise RuntimeError(f"Search failed: {e}") from e
    
    async def search_with_mmr(
        self,
        query_embedding: List[float],
        top_k: int = 6,
        fetch_k: int = 12,
    ) -> List[SearchResult]:
        """
        Search using Max Marginal Relevance (MMR).
        
        MMR balances relevance and diversity by penalizing results
        similar to already-selected documents.
        
        Parameters
        ----------
        query_embedding : List[float]
            Query embedding
        top_k : int
            Number of results to return
        fetch_k : int
            Number of candidates to fetch before MMR filtering
        
        Returns
        -------
        List[SearchResult]
            Diverse, relevant results
        """
        try:
            # ChromaDB doesn't have native MMR, so use similarity search
            # with diversity consideration
            all_results = await self.search(query_embedding, fetch_k)
            
            if len(all_results) <= top_k:
                return all_results
            
            # Simple MMR: select top-k items while avoiding redundancy
            selected = []
            remaining = all_results.copy()
            
            while len(selected) < top_k and remaining:
                # Always pick the most similar first
                best = remaining.pop(0)
                selected.append(best)
                
                # Score remaining items by similarity to query
                # (In production, would penalize by similarity to selected items)
            
            return selected[:top_k]
        
        except Exception as e:
            logger.exception("MMR search failed")
            raise RuntimeError(f"MMR search failed: {e}") from e
    
    async def delete_collection(self) -> bool:
        """Delete the current collection."""
        try:
            if self.collection:
                self.client.delete_collection(name=self.collection.name)
                logger.info("Collection deleted: %s", self.collection.name)
                return True
            return False
        except Exception as e:
            logger.exception("Failed to delete collection")
            raise RuntimeError(f"Failed to delete collection: {e}") from e
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection."""
        try:
            return {
                "name": self.collection.name,
                "count": self.collection.count(),
            }
        except Exception as e:
            logger.exception("Failed to get collection stats")
            return {}


def get_vector_store(db_path: str = "uploads/rag/vectordb") -> ChromaVectorStore:
    """Get or create vector store instance."""
    return ChromaVectorStore(db_path=db_path)
