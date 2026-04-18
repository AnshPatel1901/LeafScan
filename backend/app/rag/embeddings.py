"""
Embeddings — generates multilingual embeddings for text chunks.

Uses the 'paraphrase-multilingual-mpnet-base-v2' model from Sentence Transformers.
Supports 50+ languages and can embed text up to 384 tokens.
"""

import logging
from typing import List, Optional
import numpy as np

logger = logging.getLogger(__name__)

# Default embedding dimension (768 for paraphrase-multilingual-mpnet-base-v2)
DEFAULT_EMBEDDING_DIM = 768


class EmbeddingsModel:
    """
    Multilingual embeddings using Sentence Transformers.
    
    Model: paraphrase-multilingual-mpnet-base-v2
    - 768-dimensional embeddings
    - Supports 50+ languages
    - Purpose: semantic search, clustering, recommendation
    """
    
    def __init__(self, model_name: str = "paraphrase-multilingual-mpnet-base-v2"):
        """
        Initialize embeddings model.
        
        Parameters
        ----------
        model_name : str
            HuggingFace model identifier
        """
        self.model_name = model_name
        self.model = None
        self.embedding_dim = DEFAULT_EMBEDDING_DIM
        self._load_model()
    
    def _load_model(self) -> None:
        """Load the embeddings model from HuggingFace."""
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading embeddings model: %s", self.model_name)
            self.model = SentenceTransformer(self.model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info("Model loaded successfully | dim=%d", self.embedding_dim)
        except ImportError as e:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            ) from e
        except Exception as e:
            logger.exception("Failed to load embeddings model")
            raise RuntimeError(f"Failed to load model {self.model_name}: {e}") from e
    
    def embed(self, text: str) -> Optional[np.ndarray]:
        """
        Generate embedding for a single text.
        
        Parameters
        ----------
        text : str
            Text to embed
        
        Returns
        -------
        Optional[np.ndarray]
            1D array of shape (768,) or None if text is empty
        """
        if not text or not text.strip():
            return None
        
        try:
            # Truncate very long text (model has max length)
            text = text[:512]  # Approximate max for this model
            
            embedding = self.model.encode(text, convert_to_numpy=True)
            
            # Ensure correct shape
            if embedding.ndim == 1:
                embedding = embedding.reshape(1, -1)[0]
            
            return embedding
        except Exception as e:
            logger.exception("Failed to generate embedding for text")
            raise RuntimeError(f"Embedding generation failed: {e}") from e
    
    def embed_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for multiple texts.
        
        Parameters
        ----------
        texts : List[str]
            List of texts to embed
        batch_size : int
            Number of texts to process at once
        
        Returns
        -------
        np.ndarray
            2D array of shape (len(texts), 768)
        
        Raises
        ------
        ValueError
            If texts list is empty
        RuntimeError
            If embedding generation fails
        """
        if not texts:
            raise ValueError("texts list cannot be empty")
        
        try:
            logger.debug("Generating embeddings for %d texts", len(texts))
            embeddings = self.model.encode(
                texts,
                convert_to_numpy=True,
                batch_size=batch_size,
                show_progress_bar=len(texts) > 100,
            )
            
            # Ensure correct shape
            if embeddings.ndim == 1:
                embeddings = embeddings.reshape(1, -1)
            
            logger.debug(
                "Generated embeddings | shape=%s",
                embeddings.shape
            )
            return embeddings
        except Exception as e:
            logger.exception("Failed to generate batch embeddings")
            raise RuntimeError(f"Batch embedding generation failed: {e}") from e
    
    def embed_query(self, query: str) -> Optional[np.ndarray]:
        """
        Generate embedding for a query (same as embed but with query context).
        
        Parameters
        ----------
        query : str
            Query text
        
        Returns
        -------
        Optional[np.ndarray]
            1D array of shape (768,)
        """
        return self.embed(query)
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self.embedding_dim
    
    @staticmethod
    def supported_languages() -> List[str]:
        """
        Get list of supported languages.
        
        The paraphrase-multilingual-mpnet-base-v2 model supports 50+ languages.
        Common ones: en, es, fr, de, it, pt, nl, ru, zh, ja, ko, ar, hi, th, vi
        """
        return [
            "en", "es", "fr", "de", "it", "pt", "nl", "ru", "zh", "ja", "ko",
            "ar", "hi", "th", "vi", "pl", "tr", "el", "hu", "cs", "sk", "ro",
            "sv", "da", "fi", "no", "bg", "hr", "et", "lt", "lv", "uk", "he",
            "fa", "ur", "id", "ms", "tl", "ta", "te", "kn", "ml", "mr", "pa"
        ]


# Singleton instance
_embeddings_instance: Optional[EmbeddingsModel] = None


def get_embeddings(model_name: str = "paraphrase-multilingual-mpnet-base-v2") -> EmbeddingsModel:
    """Get or create embeddings model singleton."""
    global _embeddings_instance
    if _embeddings_instance is None:
        _embeddings_instance = EmbeddingsModel(model_name)
    return _embeddings_instance
