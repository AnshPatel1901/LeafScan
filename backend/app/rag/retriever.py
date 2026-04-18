"""
Retriever — semantic search and context retrieval.

Combines:
    • Vector similarity search
    • MMR (Max Marginal Relevance)
    • Metadata filtering
    • Context window management
"""

import logging
from typing import List, Optional
from dataclasses import dataclass

from app.rag.models import RetrievedDocument
from app.rag.vector_store import ChromaVectorStore, SearchResult
from app.rag.embeddings import EmbeddingsModel

logger = logging.getLogger(__name__)


@dataclass
class RetrievalContext:
    """Context prepared for LLM."""
    
    query: str
    documents: List[RetrievedDocument]
    combined_context: str  # All documents combined
    source_list: List[str]  # Unique sources
    
    def format_for_prompt(self) -> str:
        """Format context for LLM prompt."""
        lines = [
            "CONTEXT FROM DOCUMENTS:",
            "=" * 50,
        ]
        
        for i, doc in enumerate(self.documents, 1):
            header = f"[Doc {i}: {doc.source}"
            if doc.page is not None:
                header += f" (page {doc.page + 1})"
            header += "]"
            lines.append(header)
            lines.append(doc.content)
            lines.append("-" * 40)
        
        return "\n".join(lines)


class Retriever:
    """
    Retrieves relevant documents for a query.
    
    Uses semantic search with optional MMR for diversity.
    """
    
    def __init__(
        self,
        vector_store: ChromaVectorStore,
        embeddings: EmbeddingsModel,
        top_k: int = 6,
        fetch_k: int = 12,
    ):
        """
        Initialize retriever.
        
        Parameters
        ----------
        vector_store : ChromaVectorStore
            Vector database instance
        embeddings : EmbeddingsModel
            Embeddings model for encoding queries
        top_k : int
            Number of documents to retrieve
        fetch_k : int
            Number of candidates for MMR filtering
        """
        self.vector_store = vector_store
        self.embeddings = embeddings
        self.top_k = top_k
        self.fetch_k = fetch_k
    
    async def retrieve(
        self,
        query: str,
        use_mmr: bool = True,
    ) -> RetrievalContext:
        """
        Retrieve relevant documents for a query.
        
        Parameters
        ----------
        query : str
            User query/question
        use_mmr : bool
            Use MMR for diverse results (default: True)
        
        Returns
        -------
        RetrievalContext
            Documents and formatted context
        
        Raises
        ------
        RuntimeError
            If retrieval fails
        """
        if not query or not query.strip():
            raise ValueError("query cannot be empty")
        
        try:
            # Embed the query
            logger.debug("Encoding query: %s", query[:50])
            query_embedding = self.embeddings.embed(query)
            
            if query_embedding is None:
                raise RuntimeError("Failed to encode query")
            
            # Search vector store
            if use_mmr:
                logger.debug("Using MMR retrieval")
                search_results = await self.vector_store.search_with_mmr(
                    query_embedding=query_embedding.tolist(),
                    top_k=self.top_k,
                    fetch_k=self.fetch_k,
                )
            else:
                logger.debug("Using similarity search")
                search_results = await self.vector_store.search(
                    query_embedding=query_embedding.tolist(),
                    top_k=self.top_k,
                )
            
            # Convert to RetrievedDocument objects
            documents = []
            sources = set()
            
            for result in search_results:
                doc = RetrievedDocument(
                    content=result.content,
                    source=result.source,
                    page=result.metadata.get("page", None),
                    score=result.score,
                    metadata=result.metadata,
                )
                documents.append(doc)
                sources.add(result.source)
            
            # Combine context
            combined_context = self._combine_documents(documents)
            
            logger.info(
                "Retrieved %d documents from %d sources",
                len(documents), len(sources)
            )
            
            context = RetrievalContext(
                query=query,
                documents=documents,
                combined_context=combined_context,
                source_list=sorted(list(sources)),
            )
            
            return context
        
        except Exception as e:
            logger.exception("Retrieval failed")
            raise RuntimeError(f"Retrieval failed: {e}") from e
    
    @staticmethod
    def _combine_documents(documents: List[RetrievedDocument]) -> str:
        """Combine multiple documents into a single context string."""
        parts = []
        
        for i, doc in enumerate(documents, 1):
            source_info = f"[Source {i}: {doc.source}"
            if doc.page is not None:
                source_info += f", page {doc.page + 1}"
            if doc.score is not None:
                source_info += f", relevance: {doc.score:.2%}"
            source_info += "]"
            
            parts.append(source_info)
            parts.append(doc.content)
            parts.append("")  # Empty line for readability
        
        return "\n".join(parts).strip()


def get_retriever(
    vector_store: ChromaVectorStore,
    embeddings: EmbeddingsModel,
    top_k: int = 6,
    fetch_k: int = 12,
) -> Retriever:
    """Get retriever instance."""
    return Retriever(
        vector_store=vector_store,
        embeddings=embeddings,
        top_k=top_k,
        fetch_k=fetch_k,
    )
