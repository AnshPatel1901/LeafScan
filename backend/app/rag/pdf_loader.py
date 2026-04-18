"""
PDF Loader — loads and validates PDF files.

Supports:
    • PyPDF loader (pure Python)
    • Page extraction
    • Metadata extraction
    • Large file handling (up to 500+ pages)
"""

import logging
import os
from pathlib import Path
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


class PDFDocument:
    """Represents a loaded PDF document."""
    
    def __init__(self, filepath: str, filename: str):
        self.filepath = filepath
        self.filename = filename
        self.pages: List[str] = []
        self.metadata: dict = {}
        self._num_pages = 0
    
    @property
    def num_pages(self) -> int:
        """Get number of pages."""
        return self._num_pages
    
    def add_page(self, text: str, page_num: int) -> None:
        """Add a page to the document."""
        self.pages.append(text)
        self._num_pages = max(self._num_pages, page_num + 1)


class PDFLoader:
    """
    Loads PDF files and extracts text.
    
    Uses PyPDF for pure Python PDF parsing.
    """
    
    def __init__(self):
        self._import_pdf_library()
    
    def _import_pdf_library(self) -> None:
        """Import PDF library (PyPDF)."""
        try:
            from PyPDF2 import PdfReader
            self.PdfReader = PdfReader
        except ImportError:
            raise ImportError(
                "PyPDF2 not installed. Install with: pip install PyPDF2"
            )
    
    async def load(self, filepath: str, filename: str) -> PDFDocument:
        """
        Load a PDF file and extract text.
        
        Parameters
        ----------
        filepath : str
            Full path to the PDF file
        filename : str
            Original filename
        
        Returns
        -------
        PDFDocument
            Document object with pages
        
        Raises
        ------
        FileNotFoundError
            If PDF file not found
        ValueError
            If PDF is corrupted or unreadable
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"PDF file not found: {filepath}")
        
        if not filepath.lower().endswith('.pdf'):
            raise ValueError(f"File is not a PDF: {filepath}")
        
        try:
            doc = PDFDocument(filepath, filename)
            
            with open(filepath, 'rb') as f:
                reader = self.PdfReader(f)
                
                # Extract metadata
                metadata = reader.metadata
                if metadata:
                    doc.metadata = {
                        'title': metadata.get('/Title', ''),
                        'author': metadata.get('/Author', ''),
                        'subject': metadata.get('/Subject', ''),
                        'keywords': metadata.get('/Keywords', ''),
                    }
                
                # Extract pages
                num_pages = len(reader.pages)
                logger.info(
                    "Loading PDF: %s (%d pages)",
                    filename, num_pages
                )
                
                for page_num, page in enumerate(reader.pages):
                    try:
                        text = page.extract_text()
                        if text:
                            doc.add_page(text, page_num)
                        else:
                            logger.warning(
                                "Could not extract text from page %d of %s",
                                page_num + 1, filename
                            )
                    except Exception as e:
                        logger.warning(
                            "Error extracting page %d from %s: %s",
                            page_num + 1, filename, e
                        )
            
            logger.info(
                "Successfully loaded PDF: %s (%d pages extracted)",
                filename, doc.num_pages
            )
            return doc
        
        except Exception as exc:
            logger.exception("Failed to load PDF: %s", filepath)
            raise ValueError(f"Failed to load PDF: {exc}") from exc
    
    def validate_pdf(self, filepath: str) -> bool:
        """
        Check if file is a valid PDF.
        
        Parameters
        ----------
        filepath : str
            Path to the file
        
        Returns
        -------
        bool
            True if file is a valid PDF
        """
        if not filepath.lower().endswith('.pdf'):
            return False
        
        if not os.path.exists(filepath):
            return False
        
        try:
            with open(filepath, 'rb') as f:
                header = f.read(4)
                return header == b'%PDF'
        except Exception as e:
            logger.debug("PDF validation failed: %s", e)
            return False


def get_pdf_loader() -> PDFLoader:
    """Get or create PDF loader singleton."""
    return PDFLoader()
