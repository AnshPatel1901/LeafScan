"""
Text Chunking — splits documents into meaningful chunks.

Uses RecursiveCharacterTextSplitter for intelligent chunking
that respects sentence and paragraph boundaries.
"""

import logging
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a text chunk."""
    
    content: str
    page: int
    chunk_num: int
    source: str  # filename
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TextChunker:
    """
    Splits documents into meaningful chunks.
    
    Uses recursive splitting with configurable size and overlap.
    Respects separators: paragraphs → sentences → words → characters.
    """
    
    # Separators for recursive splitting (in order of preference)
    SEPARATORS = [
        "\n\n",      # Paragraph boundaries
        "\n",        # Line boundaries
        ". ",        # Sentence boundaries
        "! ",
        "? ",
        " ",         # Word boundaries
        "",          # Character-level fallback
    ]
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 150):
        """
        Initialize chunker.
        
        Parameters
        ----------
        chunk_size : int
            Target size of each chunk (in characters)
        chunk_overlap : int
            Overlap between consecutive chunks for context
        """
        if chunk_size < 100:
            raise ValueError("chunk_size must be at least 100")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def split_text(self, text: str) -> List[str]:
        """
        Split text into chunks using recursive splitting.
        
        Parameters
        ----------
        text : str
            Text to split
        
        Returns
        -------
        List[str]
            List of text chunks
        """
        if not text:
            return []
        
        return self._split_recursive(text, self.SEPARATORS)
    
    def _split_recursive(self, text: str, separators: List[str]) -> List[str]:
        """Recursively split text using separators."""
        final_chunks = []
        separator = separators[-1]
        
        for i, _sep in enumerate(separators):
            if _sep in text:
                separator = _sep
                break
        
        if separator:
            splits = text.split(separator)
        else:
            splits = [text]
        
        # Filter out empty strings
        good_splits = [s for s in splits if s.strip()]
        
        # Merge splits if needed
        if not good_splits:
            return []
        
        merged_splits = self._merge_splits(good_splits, separator)
        
        # Now recursively merge
        final_chunks = []
        separator = separators[-1]
        
        for split in merged_splits:
            if len(split) < self.chunk_size:
                final_chunks.append(split)
            else:
                # This split is too large, need to split further
                if final_chunks:
                    # Merge with previous if possible
                    merged_text = self._merge_splits(
                        final_chunks + [split], separator
                    )
                    if len(merged_text) > 1:
                        final_chunks = merged_text[:-1]
                        final_chunks.append(merged_text[-1])
                    else:
                        final_chunks = merged_text
                else:
                    # Try next separator
                    other_splits = self._split_recursive(split, separators[separators.index(separator) + 1:])
                    final_chunks.extend(other_splits)
        
        return final_chunks
    
    def _merge_splits(self, splits: List[str], separator: str) -> List[str]:
        """Merge splits into chunks of appropriate size."""
        separator_len = len(separator)
        good_chunks = []
        current_chunk = ""
        
        for split in splits:
            split_len = len(split)
            
            if len(current_chunk) + split_len + separator_len <= self.chunk_size:
                # Add to current chunk
                if current_chunk:
                    current_chunk += separator + split
                else:
                    current_chunk = split
            else:
                # Current chunk is full, save it and start new one
                if current_chunk:
                    good_chunks.append(current_chunk)
                
                # Check if single split is too large
                if split_len > self.chunk_size:
                    # Can't split further with this separator, keep as is
                    good_chunks.append(split)
                    current_chunk = ""
                else:
                    current_chunk = split
        
        # Add remaining chunk
        if current_chunk:
            good_chunks.append(current_chunk)
        
        return good_chunks
    
    def chunk_document(
        self,
        text: str,
        page: int = 0,
        source: str = "unknown",
    ) -> List[Chunk]:
        """
        Create Chunk objects from document text.
        
        Parameters
        ----------
        text : str
            Document text to chunk
        page : int
            Page number (for multi-page documents)
        source : str
            Source filename
        
        Returns
        -------
        List[Chunk]
            List of Chunk objects
        """
        splits = self.split_text(text)
        
        chunks = []
        for i, split in enumerate(splits):
            chunk = Chunk(
                content=split,
                page=page,
                chunk_num=i,
                source=source,
                metadata={
                    "page": page,
                    "chunk": i,
                    "source": source,
                }
            )
            chunks.append(chunk)
        
        return chunks


def get_chunker(chunk_size: int = 1000, chunk_overlap: int = 150) -> TextChunker:
    """Get a text chunker instance."""
    return TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
